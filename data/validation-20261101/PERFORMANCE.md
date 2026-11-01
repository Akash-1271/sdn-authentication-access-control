# Performance evaluation

Batch label: 1 November 2026 Ubuntu verification; runtime SHA256 a65454260fecde78bead6593957a274d29a637d6c1b9ceb747db74b6d4a888bf

Input SHA-256: `6c79a67a632d57558e5ad27b7ce5636071b037c56180b4a39ceef344ab2f2588`

Validated rows: 40. All observations retained.

| Mode | Metric (ms) | Trials | Mean | Median | Minimum | Maximum |
|---|---|---:|---:|---:|---:|---:|
| dynamic | login_ms | 20 | 185.4283 | 114.5965 | 50.5740 | 1502.5450 |
| dynamic | service_rtt_ms | 20 | 28.0545 | 19.5570 | 2.7400 | 131.0360 |
| dynamic | login_to_access_ms | 20 | 213.5018 | 129.1485 | 55.0650 | 1633.6050 |
| static | service_rtt_ms | 20 | 15.6674 | 12.2735 | 2.2610 | 66.0480 |

Service transaction time includes TCP connection setup and application response.
Compare service_rtt_ms across modes. Static login/total fields are not applicable.
Login/control and login-to-access measure additional dynamic authorization work.
A mean or median from one ordered VM batch does not establish a general speed advantage.
The caller-provided batch label is not proof of the tested source version; retain its manifest.

## Observations over 100 ms (retained, not discarded)

- dynamic, trial 1, login_ms: 1502.545 ms
- dynamic, trial 1, service_rtt_ms: 131.036 ms
- dynamic, trial 1, login_to_access_ms: 1633.605 ms
- dynamic, trial 2, login_ms: 215.212 ms
- dynamic, trial 2, login_to_access_ms: 240.247 ms
- dynamic, trial 3, login_ms: 150.162 ms
- dynamic, trial 3, login_to_access_ms: 174.151 ms
- dynamic, trial 4, login_ms: 208.738 ms
- dynamic, trial 4, login_to_access_ms: 289.336 ms
- dynamic, trial 5, login_ms: 192.386 ms
- dynamic, trial 5, login_to_access_ms: 251.908 ms
- dynamic, trial 6, login_ms: 162.402 ms
- dynamic, trial 6, login_to_access_ms: 175.603 ms
- dynamic, trial 7, login_ms: 139.388 ms
- dynamic, trial 7, login_to_access_ms: 168.725 ms
- dynamic, trial 9, login_ms: 111.659 ms
- dynamic, trial 9, login_to_access_ms: 120.364 ms
- dynamic, trial 10, login_ms: 117.534 ms
- dynamic, trial 10, login_to_access_ms: 137.933 ms
- dynamic, trial 11, login_ms: 168.182 ms
- dynamic, trial 11, login_to_access_ms: 194.225 ms
- dynamic, trial 15, login_ms: 136.108 ms
- dynamic, trial 15, login_to_access_ms: 145.893 ms
- dynamic, trial 17, login_to_access_ms: 117.526 ms
