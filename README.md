# SDN Authentication and Dynamic Access Control

**TCP login → temporary network access → logout or automatic expiry**

Python sockets · Mininet · Open vSwitch · OpenFlow 1.3 · OS-Ken

[Setup](SETUP.md) · [Demo](DEMO.md) · [Understand the code](IMPLEMENTATION.md) · [Rubric coverage](RUBRIC.md) · [Results](RESULTS.md)

> Validated in Ubuntu on 29 October 2026: 27 compact and 75 original regression tests passed without skips, followed by real Mininet checks and an automated demo rehearsal. Both earlier projects remain available unchanged.

This repository contains the final course project. Its [development history](RESULTS.md#development-and-commit-history) records the import of the previously validated edition.

## What it does

A host must authenticate before reaching a protected TCP service. A successful login asks the SDN controller to allow that host's IP for 60 seconds. Logout or expiry removes access. Multiple clients can log in, and three incorrect passwords temporarily lock that source IP.

## Architecture

```mermaid
flowchart TB
    C["OS-Ken controller<br/>OpenFlow 127.0.0.1:6653<br/>Commands 10.0.0.254:9999"]
    S["s1 — Open vSwitch"]
    H1["h1: 10.0.0.1"]
    H2["h2: 10.0.0.2"]
    A["h_auth: 10.0.0.3:9000"]
    P["h_srv: 10.0.0.4:8080"]
    H1 --- S
    H2 --- S
    A --- S
    P --- S
    C -. OpenFlow .-> S
    A -. Signed ALLOW / REVOKE .-> C
```

Solid lines are network links; dashed arrows are logical control connections. Both h1 and h2 can authenticate. A management link connects the controller to the emulated LAN at 10.0.0.254.

1. The switch initially blocks TCP access to 10.0.0.4:8080.
2. A client sends a newline-terminated JSON login to the authentication server.
3. The server checks credentials and requests a signed ALLOW for the observed source IP.
4. The controller installs a finite rule and checks the switch's acknowledgement/errors.
5. The server returns an IP-bound session token. The host can access the service.
6. Logout or expiry triggers REVOKE. Another active session on the same IP retains access.

| Priority | Traffic | Action |
|---:|---|---|
| 200 | Authenticated source → protected service | Temporary allow |
| 100 | Other sources → protected service | Drop |
| 0 | Other traffic, including ARP and ping | Normal forwarding |

## Five main files

| File | Responsibility |
|---|---|
| topology.py | Four Mininet hosts, one switch and the management link |
| auth_server.py | Credentials, sessions, lockout, expiry and access changes |
| controller.py | Signed command verification and OpenFlow rules |
| client.py | Login, service request and logout |
| protected_service.py | TCP service protected by the switch |

Supporting code: controller_client.py sends ALLOW/REVOKE; control_security.py handles HMAC/key checks; net_protocol.py shares TCP framing, request/reply and threaded serving. demo_checks.py holds demo scenarios. performance_test.py and summarize_performance.py measure and summarize results. The tests/ directory has three test modules.

## Run in Ubuntu

On the existing VM, use `/home/akash/sdn-final-simplified-20261029`. Follow [DEMO.md](DEMO.md) for exact startup, key configuration and cleanup. Startup order is **topology → controller → servers → client**.

On a new, already provisioned Ubuntu machine, install Mininet/OVS and make Mininet available to system Python. Create a dedicated controller environment:

```bash
git clone https://github.com/Akash-1271/sdn-authentication-access-control.git
cd sdn-authentication-access-control
python3.11 -m venv .venv311
.venv311/bin/python -m pip install -r requirements.txt
.venv311/bin/python -m pip check
PYTHONDONTWRITEBYTECODE=1 .venv311/bin/python -B -m unittest discover -s tests -v
```

[SETUP.md](SETUP.md) distinguishes system Python for Mininet from the controller environment, explains fresh-checkout paths, and provides dependency and resource checks. [DEMO.md](DEMO.md) uses two Ubuntu terminals and labels every command by its destination.

The controller and auth server require the same private 0600 key through SDN_CONTROL_SECRET_FILE. Generate it outside the repository using control_security.py --generate-key PATH. Demo accounts alice/123 and bob/456 are public lab accounts.

AUTH_LEASE_SECONDS and AUTH_LOCKOUT_SECONDS default to 60. AUTH_LOG_FILE selects the authentication/access log. TCP messages have size and deadline limits. Worker threads accept concurrent clients; one state lock coordinates session changes with switch updates.

## Evaluation and scope

Compare service transaction time for 20 dynamic and 20 static trials. Report login/control overhead separately. Keep all raw samples, mean, median and outliers. The [previous validated results](data/reference-20261026/PERFORMANCE.md) are reference measurements; the fresh final-source batch is in [data/PERFORMANCE.md](data/PERFORMANCE.md).

![All 40 measured service transactions, with mean and median](data/performance-comparison.svg)

The dynamic service median was **2.5200 ms**, versus **0.9955 ms** for static access in this VM batch. Three long dynamic trials raise its mean to **154.8531 ms**; they remain in the data. The purpose of dynamic control is temporary authenticated access, not a claim of faster service. See the [measurement method and repeat commands](BENCHMARK.md).

HMAC authenticates control requests but does not encrypt them. This trusted lab uses plaintext demo credentials/tokens, volatile sessions and source-IP permissions. Users on one host share network access. No IP/ARP anti-spoofing is implemented. Existing grants can survive controller failure until their hard timeout; failed revocations are retryable. A client timeout leaves the login outcome uncertain: a temporary grant may have been installed even if its token was not received.

The project covers TCP authentication, concurrency, sessions/timeouts, dynamic SDN policies, logs, unauthorized-access tests, robustness and baseline evaluation. [RESULTS.md](RESULTS.md) maps requirements to evidence. Extended regression/live tooling is retained under [verification/](verification/README.md).

## Latest verification and optional live view

The [1 November Ubuntu verification](verification/UBUNTU-20261101.md) passed 27 compact tests, 75 original regression tests, 81 real Mininet checkpoints and the updated automated demonstration. Its [new 20+20 measurement batch](data/validation-20261101/PERFORMANCE.md) is separate from the retained chart above. The application runtime is unchanged; an optional verification helper now accounts for an aged grant during controller-outage tests.

The optional [network observatory](LIVE_DASHBOARD.md) displays actual switch grants/counters and recognized authentication-log events while the project runs. It is a read-only local viewer, separate from the 11 application modules. A recorded-file mode is clearly labelled and never presented as live VM data.

## What to explain

Start with [one successful request](IMPLEMENTATION.md#one-successful-request), then the five central files, the priority 200/100/0 rules, and what changes on logout or expiry. The implementation guide includes exact message examples, important functions and short questions tied to the code.

AI assistance is permitted for this course. Explain the actual implementation and the tests you have observed; use [the code reading checklist](IMPLEMENTATION.md#code-reading-checklist) to prepare. Commit dates describe publication/import work, not an invented development timeline.
