# Kubernetes Deployment Evidence

**Environment:** GitHub Codespaces (Ubuntu 24.04), kind cluster `minipay`
**Namespace:** `minipay`

## 1. Cluster setup

`kind` was installed manually, then the cluster was created:

```console
$ kind create cluster --name minipay
```

Manifests were validated with the client-side dry run:

```console
$ kubectl apply --dry-run=client -f kubernetes/03-api.yaml
deployment.apps/minipay-api created (dry run)
service/minipay-api created (dry run)
```

## 2. Deployment

Resources were applied in this order: namespace, ConfigMap and Secret, database, API.

The API image was built locally and loaded into kind, because kind cannot see the host's Docker images:

```console
$ docker build -t minipay-api:latest ./app
$ kind load docker-image minipay-api:latest --name minipay
$ kubectl rollout restart deployment/minipay-api -n minipay
```

Pod state after the rollout:

```console
$ kubectl get pods -n minipay
NAME                           READY   STATUS    RESTARTS   AGE
minipay-api-7786788fdf-krjw5   1/1     Running   0          69s
minipay-api-7786788fdf-ktnkz   1/1     Running   0          63s
minipay-db-d8558c6df-nxkss     1/1     Running   0          3m40s
```

## 3. Database initialisation

The schema, extension tables and seed data were loaded into the database pod:

```console
$ kubectl exec -n minipay deploy/minipay-db -- psql -U postgres -d minipay -c "\dt"
 callbacks, customers, idempotency_keys, transactions   (4 tables)

$ kubectl exec ... -c "SELECT (SELECT COUNT(*) FROM customers) AS customers, (SELECT COUNT(*) FROM transactions) AS transactions;"
 customers | transactions
-----------+--------------
      1000 |        50000
```

The seed file was produced with `python3 database/generate_data.py > /tmp/seed.sql` and copied in with `kubectl cp`.

## 4. Verification through the cluster

The API was reached with `kubectl port-forward -n minipay svc/minipay-api 9080:80`. Local port 8080 was already used by Docker Compose, so 9080 was used instead.

Health check:

```console
$ curl -s http://localhost:9080/health
{"database":"up","status":"ok"}
```

Transaction lookup with a valid key:

```console
$ curl -s -H "X-API-Key: $MINIPAY_API_KEY" http://localhost:9080/api/payments/TXN00000123
{"transaction_ref":"TXN00000123","id":123,"customer_id":503,"amount":"44872.64","status":"SUCCESS", ...}
```

Authentication check with no key:

```console
$ curl -i http://localhost:9080/api/payments/TXN00000123
HTTP/1.1 401 UNAUTHORIZED
{"error":{"code":"unauthorized","message":"Missing or invalid X-API-Key header", ...}}
```

## 5. Issues found and fixed during deployment

| #   | Symptom                         | Cause                                                                                       | Fix                                                                                                 |
| --- | ------------------------------- | ------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| 1   | `ErrImagePull` on API pods      | Image existed only in host Docker, not in kind                                              | `kind load docker-image`                                                                            |
| 2   | `role "minipay" does not exist` | Cluster used `DB_USER=postgres` from the ConfigMap, not `minipay`                           | Used the `postgres` role for loading; the ConfigMap is still `postgres` (see note below)            |
| 3   | `401 unauthorized` on valid key | Secret still held the placeholder `replace_with_api_key`                                    | Secret recreated from `.env`; length check confirmed both values are 20 characters                  |
| 4   | `500 internal_error`            | Postgres rejected the API's password (`password authentication failed for user "postgres"`) | The volume kept the placeholder password. Fixed with `ALTER USER postgres PASSWORD` set from `.env` |

**Lesson:** Postgres stores its password when the data volume is first created. Changing the Kubernetes Secret later does not change the password inside the database, so both must be updated together.

## 6. Known differences from Docker Compose

- `DB_USER` is `postgres` in the Kubernetes ConfigMap, but `minipay` in `docker-compose.yml`. Both work, but the environments are not identical.
- The database password was set to the real value after initialisation, not before. For a fresh deployment, set the Secret before the database is first created.
- Secrets are not in git. `kubernetes/01-config-secrets.yaml` contains placeholders only, and the real values live in `.env`, which is git-ignored.
