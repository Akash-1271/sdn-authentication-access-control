# Understand the code you demonstrate

The project answers one question: **can a successful socket login change what a host is allowed to access in the network?** Yes: the auth server requests an OpenFlow allow rule; logout or expiry removes permission.

## One successful request

```mermaid
sequenceDiagram
    participant H as h1 / client.py
    participant A as h_auth / auth_server.py
    participant C as OS-Ken / controller.py
    participant S as s1 / Open vSwitch
    participant P as h_srv / protected_service.py
    H->>A: TCP LOGIN JSON + newline
    A->>A: Check credentials and lockout
    A->>C: Connect; receive challenge; send signed ALLOW
    C->>S: FlowMod: priority 200, source h1, timeout 60
    C->>S: Barrier request
    S-->>C: Barrier reply (errors checked separately)
    C-->>A: OK
    A-->>H: Login success + session token
    H->>S: TCP GET_SECRET to h_srv:8080
    S->>P: Forward matching allowed traffic
    P-->>H: ACCESS GRANTED: Demo protected data
    H->>A: LOGOUT with session token
    A->>C: Signed REVOKE (if no other same-IP session)
    C->>S: Delete this source's grant; confirm
    A-->>H: Logout success
```

The controller does not carry application data. It programs the switch; service traffic goes through the switch to the service.

## The five central files

| File | Functions worth reading | What to explain |
|---|---|---|
| [topology.py](topology.py) | `AuthenticationTopology.build`, `setup_controller_link`, `run` | Creates four host namespaces and one OVS switch; connects the Ubuntu root namespace through a management veth pair; `finally` stops owned resources. |
| [auth_server.py](auth_server.py) | `handle_client`, `handle_request`, `login`, `logout`, `end_session`, `expire_once` | Reads a TCP request, checks credentials, coordinates the session dictionary and switch update, and removes expired sessions. |
| [controller.py](controller.py) | `switch_features_handler`, `handle_control_client`, `apply_allow`, `apply_revoke`, `_update_rules`, `_wait_for_switch` | Installs the baseline policy, authenticates commands, sends OpenFlow updates and checks confirmation. |
| [client.py](client.py) | `send_auth_request`, `access_protected_service`, `main` | Logs in, asks for protected data, and attempts logout in `finally`. |
| [protected_service.py](protected_service.py) | `handle_client`, `main` | Listens on TCP 8080 and responds to `GET_SECRET`; the network enforces host access. |

## TCP and the application protocol

TCP delivers a byte stream. One `recv()` is not guaranteed to contain one complete message. [net_protocol.py](net_protocol.py) accumulates bytes until a newline, with a maximum length and an overall deadline. Each connection carries one request and one reply, then closes. Extra coalesced frames are not another request on that connection.

Client to auth server:

```json
{"action":"LOGIN","username":"alice","password":"123"}
```

Every transmitted message ends in `\n`. Success has `ok: true`, `session_id`, `username`, `message` and `lease_seconds`; failure has `ok: false` and `error`. For logout:

```json
{"action":"LOGOUT","session_id":"<token received from login>"}
```

The placeholder is not a usable token. The service protocol is text: `GET_SECRET\n` receives `ACCESS GRANTED: Demo protected data\n`. An unknown service command receives an error. JSON parsing rejects duplicate field names, invalid numeric constants and malformed input.

We use TCP for reliable ordered request/reply exchange; the application must still handle timeouts and incomplete messages. UDP is not required for this TCP project. We use low-level `socket.socket`, `bind`, `listen`, `accept`, `recv`, `sendall` and `create_connection`, rather than HTTP or a web framework.

## Concurrency and state

`serve_threaded()` accepts connections and starts a worker thread for each accepted client, up to 32 active workers. Excess connections get a bounded busy response. Slow input has a total deadline, so sending occasional bytes cannot keep a worker forever.

The auth server's `sessions` maps a random token to username, observed source IP and a monotonic expiry time. The client cannot choose its trusted IP in the JSON. `failed_attempts` and `locked_until` track source-IP lockout.

`transition_lock` protects **both state and the associated switch update**. Threads can handle separate connections, but login/logout/expiry transitions are serialized to prevent inconsistent permissions. This is a correctness choice and can limit throughput; it is not a claim of fully parallel authorization.

Two tokens from one IP share one network grant. Logging out one token must preserve any other active same-IP session. `end_session()` reissues a grant for the longest remaining session, or revokes when none remain. Its lease is rounded up to whole OpenFlow seconds. Session expiry starts before the controller exchange, so application expiry and the switch's hard timeout are related bounds, not perfectly synchronized clocks.

## What the switch actually matches

| Priority | Match | Action |
|---:|---|---|
| 200 | IPv4, TCP, authenticated source IP, destination `10.0.0.4`, destination port 8080 | `NORMAL`, with a finite hard timeout |
| 100 | IPv4, TCP, destination `10.0.0.4`, destination port 8080 | Drop |
| 0 | Other traffic | `NORMAL` |

The highest matching priority wins. ARP, ping and authentication traffic remain possible under the priority-0 rule. Therefore a successful ping does not prove protected-service access. `NORMAL` uses OVS's ordinary switching action; this project is policy control, not custom shortest-path routing.

Rules owned by this application carry a cookie. REVOKE uses a strict match, priority and cookie so it removes the intended grant without flushing other policies. On switch reconnect the controller clears its own old grants and reinstalls the baseline.

## Control security and switch confirmation

[controller_client.py](controller_client.py) connects to the controller's command port. [control_security.py](control_security.py) signs commands using HMAC-SHA256 and a shared private key. The controller first sends a fresh per-connection challenge. The signed envelope contains the version, timestamp, nonce, command and MAC. A request captured on one connection cannot simply be replayed against another challenge.

The controller additionally checks the connecting peer IP, target service and lease range. An example command **inside the signed envelope** is `ALLOW 10.0.0.1 10.0.0.4 8080 60`. Sending that raw string to the port is insufficient.

OpenFlow updates are asynchronous. The controller associates flow transaction IDs with the pending operation, sends a barrier and waits for its matching reply while checking related error events. A barrier reply alone does not prove a flow was valid. A failed ALLOW triggers best-effort rollback. A failed logout preserves the session so revocation can be retried.

HMAC provides request integrity/authentication, not encryption. Control replies are not signed. The trusted lab uses plaintext public demo credentials and IP-level permission. It does not implement TLS, persistent accounts, IP/ARP anti-spoofing or isolation between users sharing a host.

## Failure cases worth understanding

| Case | Expected response |
|---|---|
| Wrong password | Login rejected; third consecutive failure temporarily locks that source IP. |
| Unauthenticated service request | Service transaction times out; corroborate with service self-access and the deny/no-grant flow table. A timeout alone is inconclusive. |
| Logout / normal expiry | Remove this session's permission, retaining other same-IP sessions as needed. |
| Controller unavailable | New login is rejected; existing grants can survive until their finite hard timeout. |
| Revocation cannot be confirmed | Report failure and retain the session for retry; expiry sweep retries as well. |
| Client authentication timeout | Outcome unknown: the grant may have completed without its token reaching the client. Inspect flows and let outstanding operations/leases settle. |

## Performance and tests

[performance_test.py](performance_test.py) measures 20 dynamic and 20 static service transactions. It separates login/control time from service transaction time and records only after successful dynamic logout. [summarize_performance.py](summarize_performance.py) validates the CSV, checks mode/trial IDs and reports all observations. [BENCHMARK.md](BENCHMARK.md) explains the baseline and measurements.

The three compact test files cover protocol/deadlines/HMAC, application sessions and real local TCP exchanges, and OpenFlow messages with a fake datapath. A local TCP test mocks SDN calls; it cannot prove real OVS enforcement. The separate Mininet live runner supplies that evidence. See [RUBRIC.md](RUBRIC.md).

## Questions tied to this implementation

- **Why authenticate if the server could just check a password?** The learning goal is to connect an application decision to network enforcement: unauthenticated hosts cannot establish the protected service transaction.
- **Why a token if rules use an IP?** The token identifies a login for logout; the switch permission belongs to its observed source IP. Tokens are not sent to the protected service.
- **Why both expiry sweep and hard timeout?** The sweep manages session state and retries control updates; hard timeout bounds the installed grant independently of the auth process.
- **Why is static access faster here?** It has no login/control step and this ordered VM batch has long dynamic service outliers. The experiment does not isolate their cause or establish a universal speed difference.
- **What if the controller stops?** New grants fail. Existing permissions are finite, but an outage does not revoke them instantly.

## Code reading checklist

Read one file at a time: client -> auth server -> controller -> topology -> service. For each important function, explain its inputs, main work, output and failure path. Then trace a login and logout through the sequence diagram. Finally practise the rule table and the failure table above.

It is accurate to say: "I used AI assistance for implementation and review. I can explain the final request flow, important functions, network rules and validation." Only claim to have personally understood or tested a part after you have done so.
