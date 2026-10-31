# Linux Evidence

**Host:** codespaces-1d8eee
**Environment:** GitHub Codespaces, Ubuntu 24.04.5 LTS
**Date of capture:** 2026-10-31

## 1. OS and kernel

```console
$ uname -a
Linux codespaces-1d8eee 6.8.0-1064-azure #72~22.04.1-Ubuntu SMP Wed Jul 22 23:39:45 UTC 2026 x86_64 x86_64 x86_64 GNU/Linux
```

## 2. CPU, memory and disk

```console
$ free -h && df -h / && lscpu | grep "Model name"
               total        used        free      shared  buff/cache   available
Mem:            15Gi       4.4Gi       262Mi       117Mi        11Gi        11Gi
Swap:             0B          0B          0B
Filesystem      Size  Used Avail Use% Mounted on
overlay          32G   17G   14G  55% /
Model name:    AMD EPYC 7763 64-Core Processor
```

The root filesystem is 55% used. Most of that space is Docker images and kind cluster storage, not the project folder (see section 5).

## 3. Listening ports and processes

```console
$ ss -tulpn
Netid   State     Recv-Q    Send-Q   Local Address:Port   Peer Address:PortProcess
udp     UNCONN    0         0   127.0.0.53%lo:53          0.0.0.0:*
udp     UNCONN    0         0 10.0.0.138%eth0:68          0.0.0.0:*
tcp     LISTEN    0         4096       127.0.0.1:13005       0.0.0.0:*
tcp     LISTEN    0         4096       127.0.0.1:36945       0.0.0.0:*
tcp     LISTEN    0         4096       127.0.0.1:12563       0.0.0.0:*
tcp     LISTEN    0         4096         0.0.0.0:5432        0.0.0.0:*
tcp     LISTEN    0         4096       127.0.0.1:40711       0.0.0.0:*
tcp     LISTEN    0         4096         0.0.0.0:8080        0.0.0.0:*
tcp     LISTEN    0         4096   127.0.0.53%lo:53          0.0.0.0:*
tcp     LISTEN    0         4096       127.0.0.1:9080        0.0.0.0:* users:(("kubectl",pid=91295,fd=8))
tcp     LISTEN    0         512       127.0.0.1:16635       0.0.0.0:*
tcp     LISTEN    0         512       127.0.0.1:16634       0.0.0.0:*
tcp     LISTEN    0         512       127.0.0.1:16636       0.0.0.0:*
tcp     LISTEN    0         511       127.0.0.1:34457       0.0.0.0:* users:(("MainThread",pid=1352,fd=29))
tcp     LISTEN    0         128         0.0.0.0:2000        0.0.0.0:*
tcp     LISTEN    0         511       127.0.0.1:34615       0.0.0.0:* users:(("MainThread",pid=1271,fd=21))
tcp     LISTEN    0         128         0.0.0.0:2222        0.0.0.0:*
tcp     LISTEN    0         4096       127.0.0.1:44817       0.0.0.0:*
tcp     LISTEN    0         512           [::1]:16634          [::]:*
tcp     LISTEN    0         512           [::1]:16635          [::]:*
tcp     LISTEN    0         512           [::1]:16636          [::]:*
tcp     LISTEN    0         4096           [::1]:9080           [::]:* users:(("kubectl",pid=91295,fd=9))
tcp     LISTEN    0         4096            [::]:5432           [::]:*
tcp     LISTEN    0         4096            [::]:8080           [::]:*
tcp     LISTEN    0         128            [::]:2000           [::]:*
tcp     LISTEN    0         128            [::]:2222           [::]:*
```

Notes:

- **8080 and 5432** are the Docker Compose API and PostgreSQL containers.
- **9080** is `kubectl port-forward`, which forwards to the API inside the kind cluster. Port 8080 was already taken, so 9080 was used.
- **2222** is the Codespaces SSH service.
- Ports with no process name are owned by root or by VS Code/Codespace services. Their owners are not shown without `sudo`. Docker's proxy processes are root-owned, which is why they show no name.

## 4. Highest memory processes

```console
$ ps aux --sort=-%mem | head -n 6
USER         PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
codespa+    1337  2.4  4.5 20757080 747724 ?     Sl   07:49   3:20 /vscode/bin/linux-x64/.../node --type=extensionHost ...
root       69043  3.2  1.6 1519076 265584 ?      Ssl  09:25   1:18 kube-apiserver --advertise-address=172.19.0.2 ...
codespa+    1271  0.2  1.1 1833720 185584 ?      Sl   07:49   0:18 .../node .../out/server-main.js ...
codespa+   57374  0.0  0.9 1675704 149552 ?      Sl   09:10   0:02 .../node .../extensions/redhat.vscode-yaml-2.0.0/dist/languageserver.js ...
codespa+    1352  0.0  0.8 18556824 140148 ?     Sl   07:49   0:02 .../node .../out/bootstrap-fork --type=agentHost ...
```

Command lines are shortened with `...` for readability. RSS is in KB, so 747724 KB is about 730 MB.

The largest process is the VS Code extension host, at about 730 MB. The `kube-apiserver` process (about 265 MB) shows that the kind cluster's control plane runs on this host.

## 5. Disk usage by directory

```console
$ du -sh /workspaces/minipay-l2-assessment/* 2>/dev/null | sort -hr | head -n 5
96K     /workspaces/minipay-l2-assessment/tests
96K     /workspaces/minipay-l2-assessment/python
60K     /workspaces/minipay-l2-assessment/sql
40K     /workspaces/minipay-l2-assessment/app
28K     /workspaces/minipay-l2-assessment/requirements
```

The project itself is under 1 MB. The 17G used in section 2 comes from Docker images and cluster storage, which live outside the project folder.

## 6. Connectivity check

```console
$ curl -Is https://github.com | head -n 1
HTTP/2 200
```

The HTTPS request to GitHub returned `200`. This shows that the hostname resolved, the TCP connection and TLS handshake succeeded, and the server responded.

## 7. Health check script

```console
$ ./scripts/health_check.sh
=== MiniPay System Health Check ===
Target Base URL: http://localhost:8080
Timestamp: 2026-10-31T10:07:37Z
-----------------------------------
1. Checking API process liveness (/health/live)... OK (HTTP 200)
2. Checking database connectivity (/health)... OK (Database UP)
3. Container runtime status:
SERVICE   STATUS                 PORTS
api       Up 2 hours             0.0.0.0:8080->8080/tcp, [::]:8080->8080/tcp
db        Up 2 hours (healthy)   0.0.0.0:5432->5432/tcp, [::]:5432->5432/tcp
-----------------------------------
ALL HEALTH CHECKS PASSED
exit code: 0
```

This run checked the Docker Compose stack on port 8080. The script exits with a non-zero code if the container status check fails.

## 8. Incident investigation approach

**High CPU:** find the busy process or thread with `top` or `ps`. If PostgreSQL is busy, check `pg_stat_activity` for slow or full-scan queries. If the API is busy, check the worker count and profile the process.

**Low disk space:** check `df -h` for the full filesystem, then `du` to find the largest directories. Clean up unused Docker images and volumes, and check for deleted files that still hold space open (`lsof +L1`).

**Unreachable API:** check that the port is listening (`ss -tulpn`) and that the container is running (`docker compose ps`). Test the API locally with `curl`. If it works locally, the problem is outside the app, such as port mapping or firewall rules. If it's refused, read the container logs.

**Repeatedly terminating process:** check the exit code and whether the process was killed for memory (OOM). In Kubernetes, use `kubectl describe pod`. With Docker, use `docker inspect`.
