"""Read-only source, archive, measurement and documentation consistency checks."""
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from summarize_performance import inspect_results


def check():
    manifest = json.loads((ROOT / "candidate-runtime-manifest.json").read_text())
    measured = json.loads((ROOT / "data/runtime_source_manifest.json").read_text())
    if manifest["files"] != measured["files"]:
        raise ValueError("Candidate and measured runtime mappings differ")
    for name, expected in manifest["files"].items():
        digest = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        if digest != expected:
            raise ValueError(f"Runtime differs from measured source: {name}")
    print(f"PASS: {len(manifest['files'])} runtime/configuration hashes")

    with zipfile.ZipFile(ROOT / "verification/validation-toolkit.zip") as toolkit:
        if toolkit.testzip() is not None:
            raise ValueError("Verification archive CRC failure")
        for name, expected in manifest["files"].items():
            if hashlib.sha256(toolkit.read(name)).hexdigest() != expected:
                raise ValueError(f"Toolkit runtime mismatch: {name}")
    print("PASS: toolkit CRC and exact runtime copies")

    result = inspect_results(ROOT / "data/performance_results_current.csv")
    summary = (ROOT / "data/PERFORMANCE.md").read_text(encoding="utf-8")
    if result["sha256"] not in summary:
        raise ValueError("CSV identity does not match the recorded summary")
    for metric in result["metrics"]:
        if f"{metric['mean']:.4f}" not in summary or f"{metric['median']:.4f}" not in summary:
            raise ValueError("CSV statistics do not match the recorded summary")
    print(f"PASS: {result['rows']} unique benchmark trials and recorded statistics")

    links = 0
    for source in ROOT.rglob("*.md"):
        if any(part.startswith(".") for part in source.relative_to(ROOT).parts):
            continue
        text = source.read_text(encoding="utf-8")
        for target in re.findall(r"!?\[[^\]]*\]\(([^\s)]+)\)", text):
            url = urlsplit(target)
            if url.scheme or url.netloc or not url.path:
                continue
            path = source.parent / unquote(url.path)
            if not path.exists():
                raise ValueError(f"Broken local link in {source.name}: {target}")
            links += 1
    print(f"PASS: {links} local documentation links")
    print("Repository consistency passed. This does not execute Mininet or replace live tests.")


if __name__ == "__main__":
    try:
        check()
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
