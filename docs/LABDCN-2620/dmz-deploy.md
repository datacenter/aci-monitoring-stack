# Overview 

In this lab we are going to deploy the ACI Monitoring Stack in the DMZ environment. The DMZ environment is already pre-configured with a K8s cluster that provides:

- An ingress controller to expose services via HTTPS
- Persistent Storage

## Connect to the Kubernetes Cluster

The first step consist into SSHing into the Linux server where we are going to deploy the stack. 
The VPN and SSH details are present in the eXpo portal. 

## Review the Config

After you have connected to the linux server move to the `aci-mon-stack-values` directory.

```shell
➜  ~ cd aci-mon-stack-values
➜  aci-mon-stack-values
```

Depending on your `<PODID>` inspect the `aci-mon-stack-values-pod-<PODID>.yaml` file for example `pod1` contains this

```yaml
aci_exporter:
  # Defines 3 ACI fabric to probe with their credentials 
  fabrics:
    site1:
      apic:
      - https://<IP>
      password: <PASS>
      service_discovery: oobMgmtAddr
      username: aci-exporter
    site2:
      apic:
      - https://<IP>
      password: <PASS>
      service_discovery: oobMgmtAddr
      username: aci-exporter
    site3:
      apic:
      - https://<IP>
      password: <PASS>
      service_discovery: oobMgmtAddr
      username: aci-exporter
# Enable Grafana
grafana:
    # Enable Grafana Ingress controller over the grafana.pod1.apps.minikube.dmz URL
  ingress:
    enabled: true
    hosts:
      - grafana.pod1.apps.minikube.dmz
  adminPassword: <PASS>
  defaultDashboardsEnabled: false
  deploymentStrategy:
    type: Recreate
  enable: true
  # Allocate 200Mi for grafana storage
  persistence:
    enabled: true
    size: 200Mi
  service:
    enabled: true
    type: ClusterIP
prometheus:
    # Enable prometheus Ingress controller over the prom.pod1.apps.minikube.dmz URL
  server:
    ingress:
      enabled: true
      hosts:
        - prom.pod1.apps.minikube.dmz
    baseURL: "http://prom.pod1.apps.minikube.dmz"
    
    # Allocate 200Mi for prometheus storage
    persistentVolume:
      accessModes:
      - ReadWriteOnce
      size: 200Mi
    service:
      retentionSize: 200Mi
  alertmanager:
    # Allocate 200Mi for alertmanager storage
    persistence:
      size: 200Mi
    baseURL: "http://alertmanager.pod1.apps.minikube.dmz"

    # Enable alertmanager Ingress controller over the prom.pod1.apps.minikube.dmz URL
    ingress:
      enabled: true
      hosts:
        - host: alertmanager.pod1.apps.minikube.dmz
          paths:
            - path: /
              pathType: ImplementationSpecific

# For this lab I am not enabling Syslog collection 
loki:
  enabled: false
promtail:
  enabled: false
syslog:
  enabled: false
```

In order to deploy your stack we first need to have the HELM repository configured, to do so execute the following:

```shell
helm repo add aci-monitoring-stack https://datacenter.github.io/aci-monitoring-stack
helm repo update
```

If you get a message stating `"aci-monitoring-stack" already exists with the same configuration, skipping` it simply means you are not the first student of the day.

Next we can deploy the stack with this single line, please **be careful** to use replace <PODID> with your PODID

```
helm -n pod-<PODID>-aci-monitoring-stack upgrade --install --create-namespace pod-<PODID>-aci-monitoring-stack aci-monitoring-stack/aci-monitoring-stack -f aci-mon-stack-values-pod-<PODID>.yaml
```

Now you can check with kubectl and see if your POD are deployed in this below example `<PODID> == 2`

```

➜  aci-mon-stack-values kubectl -n pod-2-aci-monitoring-stack get pod
NAME                                                           READY   STATUS    RESTARTS   AGE
pod-2-aci-monitoring-stack-aci-exporter-f7dfdc997-bswv2        1/1     Running   0          10m
pod-2-aci-monitoring-stack-alertmanager-0                      1/1     Running   0          10m
pod-2-aci-monitoring-stack-grafana-7f766c95cd-khxnc            3/3     Running   0          10m
pod-2-aci-monitoring-stack-prometheus-server-5867fb886-jxs66   2/2     Running   0          10m
```

This should also have created the required `Ingress` routes

```
➜  aci-mon-stack-values kubectl -n pod-2-aci-monitoring-stack get ingress
NAME                                           CLASS     HOSTS                                 ADDRESS        PORTS   AGE
pod-2-aci-monitoring-stack-alertmanager        traefik   alertmanager.pod2.apps.minikube.dmz   172.16.0.210   80      11m
pod-2-aci-monitoring-stack-grafana             traefik   grafana.pod2.apps.minikube.dmz        172.16.0.210   80      11m
pod-2-aci-monitoring-stack-prometheus-server   traefik   prom.pod2.apps.minikube.dmz           172.16.0.210   80      11m
```

You should now be able to access the Grafana UI from your browser, you **MUST use HTTPS** as the connections are terminated on a reverse proxy. All the URL will be in the format of 
`https://grafana.pod<PODID>.apps.minikube.dmz`


