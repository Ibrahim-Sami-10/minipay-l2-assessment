# Kubernetes Starter Manifest Findings & Analysis

This document details the configuration defects identified in `starter/kubernetes/broken-api.yaml` that contributed to **INCIDENT-002 (P1: Application Unavailable After Deployment)**, along with the operational remediations applied in `kubernetes/03-api.yaml`.

---

## Identified Defects Summary

| # | Component | Defect | Impact | Resolution |
|---|---|---|---|---|
| **1** | Deployment (`readinessProbe`) | Probes port `8081` instead of `8080` | Readiness probe fails (`connection refused`). Pod is marked unready (`0/1 READY`), blocking traffic ingress. | Correct `port` to `8080`. Point path to `/health/live` to decouple container readiness from external DB dependency. |
| **2** | Service (`spec.selector`) | Selects `app: minipay-backend` while pods are labeled `app: minipay-api` | Kubernetes Service creates 0 endpoints (`Endpoints: <none>`). Traffic routed to the Service drops immediately. | Update selector to `app: minipay-api` to match the Pod template labels. |
| **3** | Service (`spec.ports.targetPort`) | Target port set to `8081` instead of `8080` | Requests forwarded from cluster port 80 hit closed port 8081 inside the container, returning TCP connection refused. | Set `targetPort: 8080` matching the container port. |
| **4** | Deployment (`spec.template.spec.containers[0].env`) | Missing `DB_NAME`, `DB_USER`, `DB_PASSWORD`, and `API_KEY` | Flask application fails on startup or cannot authenticate against the PostgreSQL database. | Configure `ConfigMap` for non-sensitive values (`DB_NAME`, `DB_USER`, `DB_PORT`) and `Secret` for sensitive credentials (`DB_PASSWORD`, `API_KEY`). |
| **5** | Deployment (`spec.template.spec.containers[0].image`) | Placeholder `YOUR_IMAGE_HERE` | Kubelet cannot pull the image, resulting in `ErrImagePull` or `ImagePullBackOff`. | Provide real container image tag or local build reference (`minipay-api:latest`). |
| **6** | Deployment (`resources`) | Missing CPU/Memory requests and limits | Unbounded resource consumption risks Node starvation, noisy neighbor issues, and eviction under memory pressure. | Add explicit `requests` (`cpu: 100m`, `memory: 128Mi`) and `limits` (`cpu: 500m`, `memory: 256Mi`). |

---

## Detailed Investigation & Reproduction Notes

### 1. Readiness Probe Port Mismatch
- **Manifest snippet:**
  ```yaml
  readinessProbe:
    httpGet:
      path: /health
      port: 8081
