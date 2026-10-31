# Run the project in Ubuntu

Use the existing validated VM when possible. Windows hosts the VM; the socket applications, Mininet, Open vSwitch and controller run **inside Ubuntu**. Leave the original project and controller environment in place as backups.

## Existing VM

The validated checkout is `/home/akash/sdn-final-simplified-20261029`. Its `.venv311` points to the working Python 3.11 controller environment. No reinstall is needed. Go to [DEMO.md](DEMO.md).

For a new copy of this repository, choose a separate folder:

```bash
git clone https://github.com/Akash-1271/sdn-authentication-access-control.git
cd sdn-authentication-access-control
```

If using the existing VM's controller environment, create the link only in this NEW checkout, and only if `.venv311` is absent:

```bash
test -e /home/akash/sdn-final-simplified-20261029/.venv311/bin/osken-manager
ln -s /home/akash/sdn-final-simplified-20261029/.venv311 .venv311
```

The demo's `cd` lines refer to the original validated path. For another checkout, replace those lines with your own path. Commands run from the project root; the private key path may remain the same on this VM. For a different user, change `/home/akash/` to that user's home path in both controller and auth-server commands.

## A fresh machine

This is an environment recipe, not a claim that a fresh installation has been tested. The recorded working environment is in [RESULTS.md](RESULTS.md). Prefer the course Mininet VM or follow the [official Mininet installation options](https://mininet.org/download/).

On an Ubuntu release with the packages available, the package route is:

```bash
sudo apt-get update
sudo apt-get install mininet openvswitch-switch git python3-venv python3-pip
sudo systemctl start openvswitch-switch
```

Mininet must import under the system Python used for the topology. The controller uses a separate environment; this project was validated with Python 3.11 and OS-Ken 3.1.1. Once Python 3.11 is available, run from the checkout:

```bash
python3.11 -m venv .venv311
.venv311/bin/python -m pip install -r requirements.txt
.venv311/bin/python -m pip check
```

Do not replace system Python to obtain Python 3.11. A venv does not contain Mininet automatically; use system `python3` for `topology.py` and the live runner, and `.venv311` for OS-Ken and controller tests.

## Check before the demonstration

In an Ubuntu shell at the checkout root:

```bash
python3 -c 'from mininet.net import Mininet; print("Mininet import OK")'
ovs-vsctl --version
.venv311/bin/python -c 'import os_ken; print("OS-Ken import OK")'
.venv311/bin/python -m pip check
PYTHONDONTWRITEBYTECODE=1 .venv311/bin/python -B -m unittest discover -s tests -v
python3 -B verification/check_project.py
```

The full compact suite should report **27 tests, zero skips**. A run without OS-Ken skips 8 controller tests and is only a partial check.

Inspect resource conflicts before starting:

```bash
sudo ovs-vsctl br-exists s1; echo "bridge status=$?"
ip link show ctrlroot0
ip link show ctrlovs0
ss -ltn '( sport = :6653 or sport = :9999 or sport = :9000 or sport = :8080 )'
```

Bridge status 2 means absent; 0 means present. A different exit code needs investigation. The two named interfaces should be absent and there should be no listeners on those four ports. If resources exist, stop the demo that owns them normally. Do not use broad cleanup or delete someone else's bridge.

## Configuration and private state

| Setting | Default / meaning |
|---|---|
| `SDN_CONTROL_SECRET_FILE` | Required on controller and auth server; same private key file |
| `AUTH_LEASE_SECONDS` | 60; login permission lifetime, accepted range 1..3600 |
| `AUTH_LOCKOUT_SECONDS` | 60; temporary source-IP lockout after 3 wrong passwords |
| `AUTH_LOG_FILE` | `security.log`; demo puts it under `logs/` |
| OpenFlow endpoint | Ubuntu loopback `127.0.0.1:6653` |
| Signed control endpoint | `10.0.0.254:9999`; accepted peer `10.0.0.3` |
| Authentication / service | `10.0.0.3:9000` / `10.0.0.4:8080` |

Generate the random key with `control_security.py --generate-key PATH`; [DEMO.md](DEMO.md) gives the exact commands. Generation refuses to overwrite an existing file. Key loading requires a private regular file, refuses symlinks, and validates its format. Keep the key outside the checkout.

Only the trusted lab accounts in `auth_server.py` are public demo credentials. Never put a real password or control key in GitHub. These examples are a classroom network policy demonstration, not an Internet-facing authentication service.
