"""Optional read-only local viewer; no controller calls or topology changes."""
import argparse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import subprocess
import sys
import threading
import time
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from summarize_performance import inspect_results

MAX_FILE = 1024 * 1024
EVENTS = {"LOGIN_SUCCESS", "LOGIN_FAILURE", "IP_LOCKOUT", "IP_LOCKOUT_EXPIRED",
          "ACCESS_UPDATED", "ACCESS_UPDATE_UNCONFIRMED"}


def parse_flows(text):
    """Reject unfamiliar protected-service rules rather than infer broad access."""
    rules = []
    for line in text.splitlines():
        if " actions=" not in line:
            continue
        fields, actions = line.split(" actions=", 1)
        values = dict(re.findall(r"\b([a-z_]+)=([^,\s]+)", fields))
        if not {"priority", "n_packets", "n_bytes"} <= values.keys():
            continue
        try:
            priority = int(values["priority"])
            if not (re.search(r"(?:^|[,\s])tcp(?:,|\s|$)", fields)
                    and values.get("nw_dst") == "10.0.0.4"
                    and values.get("tp_dst") == "8080"):
                continue
            source = values.get("nw_src")
            matches = [field.strip() for field in fields[fields.index("priority="):].split(",")]
            expected = {f"priority={priority}", "tcp", "nw_dst=10.0.0.4", "tp_dst=8080"}
            if source:
                expected.add(f"nw_src={source}")
            if values.get("table") != "0" or set(matches) != expected or len(matches) != len(expected):
                raise ValueError("Unsupported service-rule table or match restrictions")
            if priority == 200 and source in {"10.0.0.1", "10.0.0.2"} and actions == "NORMAL":
                kind = "allow"
            elif priority == 100 and not source and actions == "drop":
                kind = "deny"
            else:
                raise ValueError("Unsupported protected-service policy")
            duration = float(values.get("duration", "0s").removesuffix("s"))
            timeout = int(values.get("hard_timeout", "0"))
            rules.append(dict(kind=kind, source=source, priority=priority,
                              packets=int(values["n_packets"]), bytes=int(values["n_bytes"]),
                              hard_timeout=timeout,
                              remaining_s=round(max(0, timeout - duration), 1) if timeout else None))
        except (ValueError, OverflowError) as exc:
            raise ValueError("Cannot interpret the protected-service policy safely") from exc
    return rules


def read_tail(path):
    with path.open("rb") as handle:
        handle.seek(0, 2)
        size = handle.tell()
        handle.seek(max(0, size - 32768))
        data = handle.read(32768)
    if size > 32768:
        data = data.partition(b"\n")[2]
    return data.decode("utf-8", errors="replace")


def parse_events(text):
    """Never send raw log lines, usernames, tokens or arbitrary fields to the page."""
    ip = r"client_ip=(?P<source>10\.0\.0\.[12])"
    patterns = {
        "LOGIN_SUCCESS": ip,
        "LOGIN_FAILURE": ip + r" count=(?P<count>\d{1,6})",
        "IP_LOCKOUT": ip + r" seconds=(?P<seconds>\d{1,6})",
        "IP_LOCKOUT_EXPIRED": ip,
        "ACCESS_UPDATED": r"reason=(?P<reason>LOGOUT|EXPIRED|ALLOW_FAILED) " + ip + r" remaining_sessions=(?P<remaining_sessions>\d{1,6})",
        "ACCESS_UPDATE_UNCONFIRMED": r"reason=(?P<reason>LOGOUT|EXPIRED|ALLOW_FAILED) " + ip,
    }
    events = []
    for line in text.splitlines():
        match = re.match(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d,\d+) (?:INFO|WARNING|ERROR) ([A-Z_]+)\b(.*)$", line)
        if not match or match[2] not in EVENTS:
            continue
        # The suffix is written by the server after any untrusted username.
        suffix = re.search(r"(?:^|\s)" + patterns[match[2]] + r"$", match[3])
        if not suffix:
            continue
        item = dict(time=match[1], event=match[2])
        for field, value in suffix.groupdict().items():
            item[field] = int(value) if field in {"count", "remaining_sessions", "seconds"} else value
        events.append(item)
    return events[-18:][::-1]


def command(argv):
    try:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=3, check=False)
        return result.returncode == 0, result.stdout[:MAX_FILE]
    except (OSError, subprocess.TimeoutExpired):
        return False, ""


class Collector:
    def __init__(self, auth_log=None, csv=None, flow_snapshot=None):
        self.auth_log, self.csv, self.flow_snapshot = auth_log, csv, flow_snapshot
        self.lock = threading.Lock()
        self.cached, self.checked_at = None, 0

    def snapshot(self):
        # Multiple browser tabs cannot launch simultaneous OVS polls.
        with self.lock:
            if self.cached and time.monotonic() - self.checked_at < 1.5:
                return self.cached
            state = dict(mode="recorded" if self.flow_snapshot else "live",
                         sampled_at=datetime.now(timezone.utc).isoformat(),
                         switch_ok=False, rules=[], listeners=None,
                         events=[], events_status="not configured", performance=None,
                         performance_status="not configured", errors=[])
            if self.flow_snapshot:
                try:
                    if self.flow_snapshot.stat().st_size > MAX_FILE:
                        raise ValueError("snapshot too large")
                    flow_text = self.flow_snapshot.read_text(encoding="utf-8")
                    state["recorded_file"] = self.flow_snapshot.name
                    state["recorded_modified_at"] = datetime.fromtimestamp(
                        self.flow_snapshot.stat().st_mtime, timezone.utc).isoformat()
                    ok = "OFPST_FLOW reply" in flow_text
                except (OSError, ValueError, UnicodeError):
                    ok, flow_text = False, ""
            else:
                ok, flow_text = command(["ovs-ofctl", "-O", "OpenFlow13", "dump-flows", "s1"])
                ok = ok and "OFPST_FLOW reply" in flow_text
                sockets_ok, sockets = command(["ss", "-H", "-ltn"])
                if sockets_ok:
                    addresses = [line.split()[3] for line in sockets.splitlines() if len(line.split()) >= 4]
                    state["listeners"] = {str(p): any(a.rsplit(":", 1)[-1] == str(p) for a in addresses)
                                          for p in (6653, 9999)}
            try:
                state["rules"] = parse_flows(flow_text) if ok else []
            except ValueError:
                ok = False
                state["errors"].append("Unrecognized service rules: policy is unknown; compare the full OVS table.")
            state["switch_ok"] = ok
            if not ok:
                if not state["errors"]:
                    state["errors"].append("Switch unavailable: check that s1 exists and this viewer can read OVS.")
            if self.auth_log:
                try:
                    state["events"] = parse_events(read_tail(self.auth_log))
                    state["events_status"] = "file read; historical events, not current sessions"
                except OSError:
                    state["events_status"] = "file unavailable"
            if self.csv:
                try:
                    if self.csv.stat().st_size > MAX_FILE:
                        raise ValueError("CSV too large")
                    state["performance"] = inspect_results(self.csv)
                    state["performance_file"] = self.csv.name
                    state["performance_status"] = "saved measurements; not a live benchmark"
                except (OSError, ValueError, KeyError, UnicodeError):
                    state["performance_status"] = "CSV unavailable or invalid"
            self.cached, self.checked_at = state, time.monotonic()
            return state


def handler_for(collector):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            port = self.server.server_port
            if self.headers.get("Host") not in {f"127.0.0.1:{port}", f"localhost:{port}"}:
                self.send_error(403)
                return
            path = urlsplit(self.path).path
            if path == "/api/state":
                content = json.dumps(collector.snapshot(), allow_nan=False).encode()
                mime = "application/json"
            elif path == "/":
                content = (Path(__file__).with_name("dashboard.html")).read_bytes()
                mime = "text/html; charset=utf-8"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(content)

        def log_message(self, *_args):
            pass
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--auth-log", type=Path, help="Explicit auth server security.log path")
    parser.add_argument("--csv", type=Path, help="Explicit saved benchmark CSV path")
    parser.add_argument("--flow-snapshot", type=Path, help="Recorded OVS dump; disables all live commands")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("Choose a port from 1024 to 65535")
    collector = Collector(args.auth_log, args.csv, args.flow_snapshot)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler_for(collector))
    server.daemon_threads = True
    print(f"Open http://127.0.0.1:{args.port} in this machine's browser. Ctrl+C stops only the viewer.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
