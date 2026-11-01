# Optional extended verification toolkit

The main project has 11 runtime Python modules and 3 compact test files. This archive retains the larger regression/integration tooling used to verify it. It is separate supporting test code, not extra application functionality.

Extract validation-toolkit.zip into a NEW directory outside the application checkout. The archive includes copies of the exact validated runtime so the original test imports and runner paths remain reproducible. Compare those files against the files mapping in `<application-checkout>/candidate-runtime-manifest.json`, using the actual path to your application checkout; the manifest is not inside the extracted toolkit. Do not modify or overwrite the original fallback.

On the tested Ubuntu VM, create a .venv311 link in the new validation directory to the existing working controller environment, without reinstalling packages. From that directory:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv311/bin/python -B -m unittest discover -v
sudo env PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B audit_live.py --output-dir /tmp/sdn-validation-UNIQUE
```

Replace UNIQUE with an unused directory name. Check existing bridges/interfaces/listeners first and stop your own demonstration normally. Never use the stale-removal flag or broad cleanup. The live runner creates an owned Mininet topology, runs checks, measures 20 dynamic and 20 static trials, and cleans up its resources. Add --master for the extended run with a different fresh output directory. Keep generated keys/logs outside GitHub.

Candidate runtime passed fresh Ubuntu validation; actual counts and limitations are in ../RESULTS.md. Compact tests remain directly available in ../tests/. This toolkit includes the documented synthetic CSV fixture, bounded thread-event wait and startup-wait repair; application deadlines were unchanged.

## Repository checks

The [1 November Ubuntu follow-up](UBUNTU-20261101.md) records a verification-only outage scheduling repair: probes now account for the installed grant's age instead of assuming a fresh 60 seconds after controller stop. The original 75 regression tests are unchanged and passed again; the corrected real Mininet audit passed 81 checkpoints. Application runtime copies remain byte-identical.

From the application root, `python3 -B verification/check_project.py` checks source hashes, exact toolkit runtime copies, archive integrity, the retained benchmark and local Markdown links. It uses only Python's standard library and does not create a topology.

GitHub's `Project checks` workflow runs that checker and both isolated test suites on Ubuntu/Python 3.11, treating skipped tests as a failed gate. This is separate from privileged Mininet live validation. [SETUP.md](../SETUP.md) explains the two Python environments.

`plot_results.py` regenerates `data/performance-comparison.svg` from the retained CSV. It is optional reporting code and requires matplotlib in a separate plotting environment; it is not an application dependency. For example, create an unrelated plotting venv, install matplotlib there, and use its Python to run `verification/plot_results.py` from the checkout root. Source measurements are read-only; the figure is regenerated.
