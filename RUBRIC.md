# Course rubric coverage

Source: the supplied two-page **SDN-Socket Programming - Jackfruit Mini Project** guidelines. D1 is 15 marks and D2 is 25 marks. This table maps deliverables to implementation and evidence; it is not a score awarded by the evaluator.

## Mandatory requirements

| Requirement | Deliverable |
|---|---|
| Low-level TCP or UDP, as assigned | TCP sockets in `auth_server.py`, `client.py`, `protected_service.py`, `controller_client.py` and `net_protocol.py` |
| Appropriate client/server components | Two client hosts, authentication server and protected service; [architecture](README.md#architecture) |
| Multiple communicating nodes/clients | h1/h2 topology; bounded threaded servers; five concurrent login/token/logout scenario |
| Mininet deployment and tests | Four hosts, one OVS switch, management link; recorded real Ubuntu live runs |
| Socket application affects SDN | Successful login -> signed ALLOW -> confirmed flow; logout/expiry -> REVOKE |
| Controlled complete environment | Mininet + OpenFlow 1.3 + OS-Ken + TCP servers in the same Ubuntu VM |
| Source/configuration/tests/reproduction | [SETUP.md](SETUP.md), [DEMO.md](DEMO.md), compact tests and [extended toolkit](verification/README.md) |
| GitHub and complete documentation | This repository, [implementation explanation](IMPLEMENTATION.md), results and raw benchmark CSV |

## D1: 15 marks

| Component | Marks | What is implemented | Where to verify |
|---|---:|---|---|
| Problem Understanding & Architecture | 2 | Objectives, host/port diagram, communication sequence, expected default-deny behavior | [README](README.md), [implementation](IMPLEMENTATION.md) |
| TCP/UDP Socket Implementation | 4 | Real TCP request/reply, newline framing, concurrent workers, bounded input/deadlines, error replies | `tests/test_protocol.py`; `tests/test_application.py`, including `test_client_and_demo_over_real_tcp` |
| Mininet + SDN Implementation | 4 | Four hosts, OpenFlow 1.3 switch, functional controller, priorities 200/100/0 | `topology.py`; `tests/test_controller.py`; live topology and flow snapshots |
| Socket-SDN Integration | 3 | Credential decision changes source-specific network permission; switch barrier/error handling | `auth_server.login`, `controller.apply_allow`; live login/service/logout and active/expired flow checks |
| Initial Testing & Demo | 2 | Startup, healthy service, blocked host, successful client, blocked after logout | [DEMO steps 1-5](DEMO.md); recorded Mininet rehearsal |

## D2: 25 marks

| Component | Marks | What is implemented | Where to verify |
|---|---:|---|---|
| Complete Application Functionality | 4 | Valid/invalid login, unique IP-bound sessions, same-IP sharing, logout, expiry, concurrency and logs | `tests/test_application.py`; [DEMO](DEMO.md) |
| Dynamic SDN Functionality | 6 | Application-triggered finite grants and strict revocation; default deny; reconnect clears owned old grants | `tests/test_controller.py`; active priority-200 rule then absence after logout/expiry |
| Challenging Scenario / Robustness | 4 | Unauthorized access, 3-failure lockout/recovery, controller outage, malformed/slow input and retryable revocation | Demo lockout/outage; compact tests; extended regression/live toolkit |
| Performance Evaluation & Comparison | 5 | 20 dynamic + 20 static trials, separate login/service metrics, raw samples, mean/median, retained outliers and limitations | [BENCHMARK.md](BENCHMARK.md), [raw CSV](data/performance_results_current.csv), [summary](data/PERFORMANCE.md), [chart](data/performance-comparison.svg) |
| Documentation, Final Demo & Viva | 6 | Setup, architecture, exact protocol, important functions, demo, tests/results, explanation questions | [SETUP](SETUP.md), [IMPLEMENTATION](IMPLEMENTATION.md), [DEMO](DEMO.md), [RESULTS](RESULTS.md); individual explanation remains part of assessment |

The examples in the dynamic-SDN and robustness rubric are alternatives, not a requirement to add every routing, load-balancing or congestion feature. This assigned project implements dynamic access filtering; unauthorized access and controller failure are its meaningful challenging scenarios.

## Evidence and final handoff

The unchanged runtime passed **27 compact tests, 75 extended regression tests, 80 normal live checkpoint verdicts, 122 extended live checkpoint verdicts**, and an automated CLI rehearsal on 29 October 2026. Live counts overlap. The raw 40-row benchmark belongs to that runtime manifest. See [RESULTS.md](RESULTS.md) for provenance, environment and precise limitations.

The repository checker verifies the runtime hashes, toolkit CRC/runtime copies, CSV identity and local documentation links. It does not run Mininet or award rubric marks. The 31 October edits improve documentation, presentation and repository verification; a handoff rehearsal of the updated instructions is requested separately from the VM's Codex. Earlier recorded validation remains dated 29 October.
