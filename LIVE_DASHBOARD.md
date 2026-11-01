# Watch the real project

This optional local dashboard reads the running project's OVS flow table, packet counters, authentication log and a chosen saved measurement CSV. It does not simulate successful logins, install rules, generate traffic or replace the terminal demonstration. The 11 application modules are unchanged.

## Live view — inside Ubuntu

Keep the normal two demonstration terminals running. Open a third Ubuntu terminal/tab for the viewer. Use system Python; it requires only the standard library and the existing OVS commands.

From the checkout containing `tools/live_dashboard.py`, run:

```bash
sudo /usr/bin/python3 -B tools/live_dashboard.py --auth-log /home/akash/sdn-rubric-ready-20261031/logs/security.log --csv data/performance_results_current.csv
```

Use the actual `AUTH_LOG_FILE` path selected when starting your auth server. A missing log is reported as unavailable rather than creating a file. The CSV above is the retained 29 October batch; choose a fresh complete benchmark CSV with `--csv PATH` to show its actual results instead. Its values update after a complete valid file is saved, not during unfinished trials.

In **Firefox inside Ubuntu**, open **http://127.0.0.1:8765**. Windows localhost is a different machine; this command does not expose a network service to Windows. Port 8765 must be free; choose `--port 8766` if occupied. Enter a sudo password yourself if prompted.

The viewer uses sudo only to read OVS. It serves two fixed GET routes on loopback and has no command, upload or file-selection endpoint. It accepts no remote bind address. Stop it with Ctrl+C in its terminal; this does not stop your project. Existing validated fallback directories do not need to be changed: the viewer can run from a separate checkout while reading the explicitly selected candidate log.

## What to show

1. Start the normal topology, controller and servers following [DEMO.md](DEMO.md), substituting the verified candidate directory `/home/akash/sdn-rubric-ready-20261031` for the old example path. Confirm protected-service self-access in Mininet.
2. Open the viewer. The switch table should show priority-100 drop, with no h1 grant. Both host labels describe rules for the service, not a reachability test.
3. In the Mininet terminal, run `h1 python3 -B demo_checks.py expiry > logs/expiry-demo.log 2>&1 &`. This holds a real finite grant long enough to observe. Check its log as described in DEMO.md.
4. Watch the real priority-200 h1 rule, estimated remaining lifetime and packet counters appear. The login event comes from the actual auth log. Ordinary `client.py` logs out quickly, so a two-second poll may miss its short-lived rule; the event log can still show it.
5. Wait for the probe to finish. The grant disappears; a deny rule remains. Corroborate denial with service self-access and the Mininet flow dump. A dashboard rule is not proof that a request succeeded or failed.
6. Run the remaining demo scenarios normally. View events for logout, expiry and lockout. Stop the viewer, then cleanly stop the original demo using its documented procedure.

## Read the labels accurately

- **Live**: polls the real OVS switch every two seconds. Missing switch/permission/command errors mean unknown status, never successful denial.
- **Observed host grants**: source-IP allow rules, not number of active tokens or users. Same-IP sessions share permission.
- **Packets**: counters in currently installed rules; they reset on replacement and do not count login attempts or application requests.
- **Lease left**: hard timeout minus observed flow duration at sample time. It is an estimate, not the auth server's in-memory expiry clock.
- **Listeners**: root namespace ports 6653/9999 only; presence does not prove controller health. Auth/service listeners are in Mininet namespaces and are not claimed healthy by this display.
- **Events**: recognized log history; usernames, tokens and arbitrary fields are omitted. Reusing an old log shows old events too. The observer does not inspect session dictionaries.
- **Measurements**: actual saved CSV values; not live latency probes. Login/control time is separate from service transaction time. Retained and fresh measurements remain separate.

## Recorded preview — Windows or Ubuntu

For a returned evidence folder, choose one actual saved flow dump, its log and its fresh CSV:

```text
python -B tools/live_dashboard.py --flow-snapshot PATH_TO_RETURN/evidence/demo/active-default-expiry-flows.txt --auth-log PATH_TO_RETURN/evidence/demo-service-logs/security.log --csv PATH_TO_RETURN/new-measurements/fresh-performance.csv
```

Replace `PATH_TO_RETURN` with the extracted return's actual path. In Windows use quoted absolute paths if they contain spaces. Open http://127.0.0.1:8765 in that machine's browser. This mode executes no OVS or live-system commands and prominently says **RECORDED EVIDENCE**. The chosen flow snapshot, historical log and completed CSV are independent sources, not a synchronized replay. Its sample timestamp is the time the files were read, not the original experiment time.

## Verification and scope

```bash
python3 -B -m unittest discover -s tools/tests -v
```

Seven observer tests cover rule interpretation, invalid rules, field sanitization, recorded-mode isolation, unavailable-switch handling, read-only commands and HTTP restrictions. They are separate from the original 27 compact and 75 regression tests. HTTP/recorded display can be checked on Windows; real OVS polling and live visual changes still require an Ubuntu run. No additional application feature or rubric credit is claimed for the viewer.
