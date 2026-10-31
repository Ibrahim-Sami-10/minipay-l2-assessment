# INCIDENT-002 – Application Unavailable After Deployment

**Priority:** P1
**Reported by:** Implementation Team
**Status:** Resolved

---

## 1. Observations and Reproduction Steps

Following deployment of the starter Kubernetes manifest (`starter/kubernetes/broken-api.yaml`), the implementation team reported that the application was unavailable. External traffic directed to the application was rejected with HTTP 502 and TCP connection refused errors.

**Method:** the defects below were identified by static analysis of the starter manifest, meaning by reading the file and checking it against the Pod labels, the container port and the Kubernetes schema. **The starter manifest was not applied to the cluster for this write-up**, so no live pod status is claimed for it.

Defects found in `starter/kubernetes/broken-api.yaml`:

- `image: YOUR_IMAGE_HERE` is a placeholder, so the image cannot be pulled.
- The readiness probe targets port `8081` and path `/health`, but the container listens on `8080`.
- The Service selector is `app: minipay-backend`, but the Pod labels are `app: minipay-api`, so the Service has no endpoints.
- The Service `targetPort` is `8081`, but the container listens on `8080`.
- Environment variables `DB_NAME`, `DB_USER`, `DB_PASSWORD` and `API_KEY` are missing (`DB_PORT` is also missing).
- No CPU or memory `requests` or `limits` are set.
- The manifest contains no PostgreSQL Deployment, Service or PersistentVolumeClaim.

## 2. Evidence

The defect list in section 1 is the evidence from static analysis. The corrected manifests are in `kubernetes/`, and the findings table is in `investigation/kubernetes-findings.md`.

## 3. Root Causes

1. **Service-to-Pod label mismatch:** the Service selected `app: minipay-backend`, which matches no Pods, so it had zero endpoints and nothing received traffic.
2. **Port mismatch:** the Service forwarded to `targetPort: 8081`, but the container listened on `8080`, so connections to the Pod were refused.
3. **Failing readiness probe:** the probe checked port `8081`, so the kubelet kept Pods out of `Ready`. A Pod that is not Ready is removed from Service endpoints, which compounds the label mismatch.
4. **Incomplete runtime configuration:** the missing database and API key variables would prevent the application from authenticating to PostgreSQL and checking API keys, even after the networking was fixed.
5. **Unusable image reference:** the placeholder image meant the Pod could not start at all.

## 4. Corrective Action

The broken configuration was replaced with structured manifests in `kubernetes/`:

- `00-namespace.yaml`: dedicated `minipay` namespace.
- `01-config-secrets.yaml`: `minipay-config` ConfigMap (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`) and `minipay-secrets` Secret template (`POSTGRES_PASSWORD`, `API_KEY`). The file holds placeholders only.
- `02-database.yaml`: PostgreSQL 16 Deployment with a `minipay-db-data` PersistentVolumeClaim (1Gi) and a `minipay-db` Service on port 5432.
- `03-api.yaml`:
  - `image: minipay-api:latest` with `imagePullPolicy: IfNotPresent`. The image was built locally and loaded into kind with `kind load docker-image minipay-api:latest --name minipay`.
  - Readiness and liveness probes on `/health/live`, port `8080`.
  - Service selector `app: minipay-api`, `targetPort: 8080`.
  - CPU requests `100m` and limits `500m`; memory requests `128Mi` and limits `256Mi`.
  - All required environment variables, read from the ConfigMap and Secret.

## 5. Validation

Validation was run against the corrected manifests in the kind cluster.

```console
$ kubectl get pods -n minipay
NAME                           READY   STATUS    RESTARTS   AGE
minipay-api-7786788fdf-krjw5   1/1     Running   0          69s
minipay-api-7786788fdf-ktnkz   1/1     Running   0          63s
minipay-db-d8558c6df-nxkss     1/1     Running   0          3m40s

$ curl -s http://localhost:9080/health
{"database":"up","status":"ok"}

$ curl -s -H "X-API-Key: $MINIPAY_API_KEY" http://localhost:9080/api/payments/TXN00000123
{"transaction_ref":"TXN00000123","id":123,"customer_id":503,"amount":"44872.64","status":"SUCCESS", ...}
```

```console
$ kubectl get endpoints minipay-api -n minipay
NAME          ENDPOINTS                     AGE
minipay-api   10.244.0.10:8080,10.244.0.11:8080   12m
```

## 6. Preventive Controls

- **CI manifest validation:** run `kubectl apply --dry-run=client -f kubernetes/` and `kubeconform` in CI, so schema errors fail the build before deployment.
- **Label and port linting:** use `kube-linter` or a policy engine such as Kyverno or OPA to check that Service selectors and `targetPort` values match Pod labels and `containerPort` declarations.
- **Post-deployment smoke gate:** run `scripts/health_check.sh` against the deployed service before a rollout is marked complete.
- **Probe review:** keep readiness and liveness probes on the same port as the container, and document that `/health/live` does not depend on the database.
