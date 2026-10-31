# MiniPay Setup and Validation

## Prerequisites

- Docker Engine and Docker Compose
- Python 3.11+
- `pip`
- PostgreSQL client tools (`psql`) for database initialization
- Playwright and its Chromium browser for UI tests
- `kubectl` and kind for the Kubernetes workflow

## Local Compose deployment

From the repository root:

```bash
cp .env.example .env
# Replace both placeholder values in .env with local-only values.
docker compose up -d --build
until curl -fsS http://localhost:8080/health >/dev/null; do sleep 2; done
```

The database volume is persistent. On a new volume, Compose automatically
initializes the schema and application tables from the mounted SQL files. Load
the synthetic seed data once:

```bash
python database/generate_data.py > /tmp/minipay-seed.sql
docker compose exec -T db psql -U minipay -d minipay < /tmp/minipay-seed.sql
```

If the database volume was already created before the SQL mounts were added,
recreate it only when its data can be discarded:

```bash
docker compose down -v
docker compose up -d --build
```

Verify the service:

```bash
curl -fsS http://localhost:8080/health
./scripts/health_check.sh
```

The API uses `API_KEY` in `.env`. The test fixtures accept either `API_KEY` or
`MINIPAY_API_KEY`, so the test command can be run directly after sourcing `.env`.

## Git workflow

Work was developed in small commits on `main`, with the assessment submission
marked by the annotated `submission-v1.0` tag. The final branch should be pushed
with its tag using `git push origin main --follow-tags`.

## Tests

Install the application and test dependencies:

```bash
python -m pip install -r app/requirements.txt -r python/requirements.txt
python -m playwright install --with-deps chromium
```

Run unit tests:

```bash
pytest -q python/tests
```

Run API and UI tests against the running Compose environment:

```bash
set -a; . ./.env; set +a
pytest -q tests/api tests/ui
```

Run the support utility:

```bash
export MINIPAY_API_URL=http://localhost:8080
export MINIPAY_API_KEY="$API_KEY"
python python/support_tool.py --transaction TXN00000123
python python/support_tool.py --health --json
```

## Kubernetes deployment

Create a kind cluster, build/load the image, create local secrets, and apply
manifests:

```bash
kind create cluster --name minipay
docker build -t minipay-api:latest ./app
kind load docker-image minipay-api:latest --name minipay
kubectl apply -f kubernetes/00-namespace.yaml
kubectl apply -f kubernetes/01-config-secrets.yaml
kubectl create secret generic minipay-secrets -n minipay \
  --from-literal=POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
  --from-literal=API_KEY="$API_KEY" --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f kubernetes/02-database.yaml
kubectl apply -f kubernetes/03-api.yaml
kubectl rollout status deployment/minipay-api -n minipay
```

For a fresh Kubernetes database, load `schema.sql`, `app_extras.sql`, and the
generated seed file with `kubectl exec` after the database pod is ready. Do not
commit the generated seed, local `.env`, or real Secret values.

## Cleanup

```bash
docker compose down
# Add -v only when intentionally deleting the local PostgreSQL volume.
kind delete cluster --name minipay
```
