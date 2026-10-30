# INCIDENT-002 – Application Unavailable After Deployment

**Priority:** P1  
**Reported by:** Implementation Team  
**Status:** Resolved

---

## 1. Observations and Reproduction Steps
Following deployment of the starter Kubernetes manifest (`starter/kubernetes/broken-api.yaml`), Client Operations reported a complete service outage. External traffic directed to the application was rejected with HTTP 502 / TCP connection refused errors.

### Reproduction Verification:
1. Manifest applied: `kubectl apply -f starter/kubernetes/broken-api.yaml`
2. Inspection of Pod status:
   ``` console
   $ kubectl get pods -n minipay
   NAME                           READY   STATUS    RESTARTS   AGE
   minipay-api-7b897984f9-2wtxq   0/1     Running   0          45s
   minipay-api-7b897984f9-xk8z2   0/1     Running   0          45s
