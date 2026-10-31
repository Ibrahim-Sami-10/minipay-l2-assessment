# Rancher Evidence

The available assessment environment used kind and `kubectl`; a Rancher server
was not available to deploy within the time window. The Kubernetes deployment
and operational checks are therefore recorded in
[kubernetes.md](./kubernetes.md), with equivalent Rancher procedures below.

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

The same operations were performed with `kubectl` and documented as
reproducible commands because Rancher was unavailable.
