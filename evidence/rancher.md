# Rancher Evidence

## Verified local Rancher startup

Rancher was started locally on 2026-10-31 beside the existing kind cluster:

```bash
docker pull rancher/rancher:latest
docker run -d --name rancher --restart=unless-stopped --privileged \
  --network kind -p 8081:80 -p 8443:443 rancher/rancher:latest
curl -k https://localhost:8443/ping
# pong
docker ps --filter name=rancher
# rancher ... Up ... 0.0.0.0:8443->443/tcp
```

The self-signed Rancher UI is available at `https://localhost:8443`. The
bootstrap password is generated in the container logs and is intentionally not
recorded in Git.

The application cluster remains the existing kind cluster. The API and database
deployment and its `kubectl` evidence are recorded in
[kubernetes.md](./kubernetes.md).

## Equivalent Rancher workflow

1. Import or register the kind/cloud cluster in Rancher.
2. Open **Cluster Explorer** and select the `minipay` namespace.
3. Inspect `minipay-api` and `minipay-db` workloads, replica readiness,
   resource requests/limits, and pod restart counts.
4. Open a pod's **Logs** tab to inspect API request IDs and database errors.
5. Inspect the API workload's **Environment** view. Confirm ConfigMap values
   are non-sensitive and Secret values are not exposed in screenshots.
6. Use **Scale** on `minipay-api` or select **Redeploy** after loading a new
   image. Confirm rollout completion and readiness.
7. Use the namespace and workload metrics views to inspect CPU, memory, and
   pod health.

The Rancher server startup was verified, but importing the existing kind
cluster and collecting UI screenshots was not completed in this environment.
Therefore the following is documented as the exact remaining workflow rather
than claimed as completed evidence.

## Remaining UI workflow

1. Open `https://localhost:8443`, accept the self-signed certificate, and use
   the one-time bootstrap password from `docker logs rancher`.
2. Set a new local admin password and configure the server URL reachable by the
   kind cluster.
3. Use **Cluster Management > Import Existing > Generic**, then run Rancher's
   generated `kubectl apply` command with the `kind-minipay` context.
4. Wait for the imported cluster to become **Active**.
5. Capture redacted screenshots for the cluster/workload view, pod status and
   logs, ConfigMap/Secret references (never values), scaling or redeploy, and
   CPU/memory health.

The same deployment and operational actions are reproducible through
`kubectl`; no secret values or bootstrap credentials are committed here.
