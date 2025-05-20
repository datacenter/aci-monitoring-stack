
# Stack Deployment

The main Deployment workflow will consist in two steps:

- Configuration preparation for Stack components:
  - ACI-exporter
  - Prometheus and alertmanager
  - Grafana
  - Syslog-ng
  - Promtail
- Deployment using HELM

Warning: If you are installing on OpenShift you will need a few additional steps. Refer to the [OpenShift Section](#openshift)

## Pre Requisites
- Familiarity with Kubernetes: This installation guide is intended to assist with the setup of the ACI Monitoring stack and assumes prior familiarity with Kubernetes; it is not designed to provide instruction on Kubernetes itself.
- A Kubernetes Cluster: Currently the stack has been tested on `Upstream Kubernetes 1.30.x` `Minikube` and `k3s`
  - Persistent Volumes: A total 10G should be plenty for a small/demo environment. Many storage provisioner support Volume expansion so should be easy to increase this post installation.
  - Ability to expose services for:
      - Access to the `Grafana`, `Prometheus` and `Alertmanager` dashboards: This will be ideally achieved via an `Ingress Controller`
        - (Optional) Wildcard DNS Entries for the ingress controller domain.
      - Syslog ingestion from ACI: Since the syslog can be sent via `UDP` or `TCP` it is required to expose these service directly via either a `NodePort` or a `LoadBalancer` service Type
  - Cluster Compute Resources: This stack has been tested against a 500 node ACI fabric and was consuming roughly 8GB of RAM, CPU resources didn't seem to play a major role and any modern CPU should suffice.
  - 1 Dedicated Namespace per instance: One Instance can monitor at least 500 switches.
    - This is not strictly required but is suggested to keep the HELM configuration simple so the default K8s service names can be re-used see the [Config Preparation](#config-preparation) section for more details.
- Helm: This stack is distributed as a helm chart and relies on 3rd party helm charts as well
- Connectivity from your Kubernetes Cluster to ACI either over Out Of Band or In Band

## Installation

## Config Preparation

The ACI Monitoring Stack is a combination of several [Charts](charts/aci-monitoring-stack/charts), if you are familiar with Helm you are aware of the struggle to propagate dynamic values to sub-charts. For example, it is not possible to pass to a sub-chart the name of a service in a dynamic way. 

In order to simplify the user experience the `chart` comes with a few pre-configured parameters that are populated in the configurations of the various sub-charts. 

For example the aci-exporter Service Name is pre-configured as `aci-exporter-svc` and this value is then passed to Prometheus as service Discovery URL.

All these values can be customized and if you need to you can refer to the [Values](../charts/aci-monitoring-stack/values.yaml) file.

*Note:* This is the first HELM char `camrossi` created, and he is sure it can be improved. If you have suggestions they are extremely welcome! :) 

### aci-exporter

The aci-exporter is the bridge between your Cisco ACI environment and the `Prometheus` monitoring ecosystem, for it to works it needs to know:
- `fabrics`: A list of fabrics and how to connect to the APICs.
  - Requires a **ReadOnly** **Admin** User
- `service_discovery`: Select if devices are reachable via Out Of Band (`oobMgmtAddr`) or InBand (`inbMgmtAddr`). 

*Note:* The switches are auto-discovered.

This is done by setting the following Values in Helm:

```yaml
aci_exporter:
  # Profiles for different fabrics
  fabrics:
    fab1:
      username: <username>
      password: <password>
      apic:
        - https://IP1
        - https://IP2
        - https://IP3
      # service_discovery oobMgmtAddr|inbMgmtAddr
      service_discovery: oobMgmtAddr
    fab2:
      username: <username>
      password: <password>
      apic:
        - https://IP1
        - https://IP2
        - https://IP3
      # service_discovery oobMgmtAddr|inbMgmtAddr
      service_discovery: inbMgmtAddr
```
### Prometheus and Alertmanager

Prometheus is installed via its [own Chart](https://github.com/prometheus-community/helm-charts/tree/main/charts/prometheus) the options you need to set are:

- The `ingress` config and the baseURL: These most likely are the same URL which can access `prometheus` and `alertmanager`
- Persistent Volume Capacity
- (Optional) `retentionSize`: this is only needed if you want to limit the retention by size. Keep in mind that if you run out of disk space Prometheus WILL stop working. 
- (Optional) alertmanager `route`: these are used to send notifications via Mail/Webex etc... the complete syntax is available [Here](https://prometheus.io/docs/alerting/latest/configuration/#receiver-integration-settings) 
Below an example:
```yaml
prometheus:
  server:
    ingress:
      enabled: true
      ingressClassName: "traefik"
      hosts:
        - aci-exporter-prom.apps.c1.cam.ciscolabs.com
    baseURL: "http://aci-exporter-prom.apps.c1.cam.ciscolabs.com"
    service:
      retentionSize: 5GB
    persistentVolume:
      accessModes: ["ReadWriteOnce"]
      size: 5Gi

  alertmanager:
    baseURL: "http://aci-exporter-alertmanager.apps.c1.cam.ciscolabs.com"
    ingress:
      enabled: true
      ingressClassName: "traefik"
      hosts:
        - host: aci-exporter-alertmanager.apps.c1.cam.ciscolabs.com
          paths:
            - path: /
              pathType: ImplementationSpecific
    config:
      route:
        group_by: ['alertname']
        group_interval: 30s
        repeat_interval: 30s
        group_wait: 30s
        receiver: 'webex'
      receivers:
        - name: webex
          webex_configs:
            - send_resolved: false
              api_url: "https://webexapis.com/v1/messages"
              room_id: "<room_id>"
              http_config:
                authorization:
                  credentials: "<credentials>"
```

If you use Webex here some [config steps](webex.md) for you!

### Grafana

`Grafana` is installed via its [own Chart](https://github.com/grafana/helm-charts/tree/main/charts/grafana) the main options you need to set are:

- The `ingress` config: External URL which can access Grafana.
- Persistent Volume Capacity
- (Optional) `adminPassword`: If not set will be auto generated and can be found in the `grafana` secret
- (Optional) `viewers_can_edit`: This allows users with a `view only` role to modify the dashboards and access `Explorer` to execute queries against `Pormetheus` and `Loki`. However, the user will not be able to save any changes.
- (Optional) `deploymentStrategy`: if Grafana `Persistent Volume` is of type `ReadWriteOnce` rolling updates will get stuck as the new pod cannot start before the old one releases the PVC. Setting `deploymentStrategy.type` to `Recreate` destroy the original pod before starting the new one.

Below an example:

```yaml
grafana:
  grafana.ini:
    users:
      viewers_can_edit: "True"
  adminPassword: <adminPassword>
  deploymentStrategy:
    type: Recreate
  ingress:
    ingressClassName: "traefik"
    enabled: true
    hosts:
      - aci-exporter-grafana.apps.c1.cam.ciscolabs.com
  persistence:
    enabled: true
    size: 2Gi
```
### Syslog config

The syslog config is the most complicated part as it relies on 3 components (`promtail`, `loki` and `syslog-ng`) with their own individual configs. Furthermore, there are two issues we need to overcome:

- The Syslog messages don't contain the ACI Fabric name: to be able to distinguish the messaged from one fabric to another the only solution is to use dedicated `external services` with unique `IP:Port` pair per Fabric.
- Until ACI 6.1 we need `syslog-ng` between `ACI` and `Promtail` to convert from RFC 3164 to 5424
  *Note*: Promtail 3.1.0 adds support for RFC 3164 however this **DOES NOT** work for Cisco Switches and still requires syslog-ng. syslog-ng `syslog-parser` has extensive logic to handle all the complexities (and inconsistencies) of RFC 3164 messages.

### Loki

Loki is deployed with the [Simple Scalable](https://grafana.com/docs/loki/latest/get-started/deployment-modes/#simple-scalable) Profile and is composed of a `backend`, `read` and `write` deployment with a replica of 3.

The `backend` and `write` deployments requires persistent volumes. This chart is pre-configured to allocate 2Gi Volumes for each deployment (a total of 6 PVC will be created):
- `3 x data-loki-backend-X`
- `3 x data-loki-write-X`

The PVC Size can be easily changed if required.

Loki also requires an `Object Store`. This chart is pre-configured to deploy [minio](https://min.io/). *Note:* Currently [Loki Chart](https://github.com/grafana/loki/tree/main/production/helm/loki) is deploying a very old version of `Minio` and there is a [PR open](https://github.com/grafana/loki/pull/11409) to address this already.

Loki also support `chunks-cache` via `memcached`. The default config allocates 8G of memory. I have decreased this to 1G by default.

If you want to change any of these parameters check the `loki` section in the [Values](charts/aci-monitoring-stack/values.yaml) file.

Assuming the default parameters are acceptable the only required config for loki is to set the `rulerConfig.external_url` to point to the Grafana `ingress` URL

```yaml
loki: 
  loki:
    rulerConfig:
      external_url: http://aci-exporter-grafana.apps.c1.cam.ciscolabs.com
```

### Promtail and Syslog-ng

These two components are tightly coupled together.

- `Syslog-ng` translates logs from RFC 3164 to RFC 5424 and forwards them to `Promtail`. 
- `Promtail` is ingesting logs in RFC 5424 format and forwards them to `Loki`. 

`Promtail` is pre-configured with:

- Deployment Mode with 1 replica
- Loki Push Gateway url: `loki-gateway` This is the Loki Gateway K8s service name. 
- Auto generated `scrapeConfigs` that will map a Fabric to a `IP:Port` Pair. 

These setting can be easily changed if required check the `Promtail` section in the [Values](charts/aci-monitoring-stack/values.yaml) file for more details.

`Syslog-ng` is pre-configured with:
- Deployment Mode with 1 replica

If you are happy with my defaults the only configs required are setting the `extraPorts` for `Loki` and `services` for `Syslog-ng`. You will need one entry per fabric and the ports needs to "match", see the diagram below for a visual representation.

`Syslog-ng` is only needed for ACI < 6.1

Below a diagram of what is our goal for an ACI 6.1 fabric and an ACI 5.2 one.
```mermaid
flowchart-elk LR
  subgraph K8s Cluster
    subgraph Promtail
      PT1513["TCP:1513 label:fab1"]
      PT1514["TCP:1514 label:fab2"]
    end
    subgraph Syslog-ng
    SL["UDP:1514"]
    end
    F1SVC["LoadBalancerIP TCP:1513"]
    F2SVC["LoadBalancerIP UDP:1514"]

    F1SVC --> PT1513
    F2SVC --> SL
  end
  subgraph ACI
  ACI61["ACI Fab1 Ver. 6.1"] --> F1SVC
  ACI52["ACI Fab2 Ver. 5.2"] --> F2SVC
  end
  SL --> PT1514

```

The above architecture can be achieved with the following config:

- `name`: This will set the `fabric` labels for the logs received by Loki
- `containerPort`: The port the container listen to. This is mapping a logs stream to a fabric
- `service.type`: I would suggest to set this to either `NodePort` or `LoadBalancer`. Regardless this IP allocated MUST be reachable by all the Fabric Nodes. 
- `service.port`: The port the `LoadBalancer` service is listening to, this will be the port you set into the ACI Syslog config.
- `service.nodePort`: The port the `NodePort` service is listening to, this will be the port you set into the ACI Syslog config.

```yaml
promtail:
  extraPorts:
    fab1:
      name: fab1
      containerPort: 1513
      service:
        type: LoadBalancer
        port: 1513
    fab2:
      name: fab2
      containerPort: 1516
      service:
        type: ClusterIP

syslog:
  services:
    fab2:
        name: fab2
        containerPort: 1516
        protocol: UDP
        service:
          type: LoadBalancer
          port: 1516
```

### ACI Syslog Config
If you need a reminder on how to configure ACI Syslog take a look [Here](syslog.md)

### Config Exporter

The config exporter feature requires 3 components:

- backup2graph: This has been developed specifically for this use case and is packaged in this repo.
- Memgraph: Deployed with the Memgraph Chart
- kniepdennis-neo4j-datasource: This is a Grafana datasource plugin. I had to generate a patched version to address a few issues. Until my [PR](https://github.com/denniskniep/grafana-datasource-plugin-neo4j/pull/38) is accepted:  it will be required to run this as un unsigned plugin. You can download it locally from here: [kniepdennis-neo4j-datasource-2.0.0.zip](../apps/neo4j-datasource/kniepdennis-neo4j-datasource-2.0.0.zip), place it on a webserver and add the `URL` in the field below:
  ```yaml
  grafana:
    enable: true
    grafana.ini:
      plugins:
        allow_loading_unsigned_plugins: "kniepdennis-neo4j-datasource"
    plugins:
      - `URL`;kniepdennis-neo4j-datasource
  ```

You will also need to provide `memgraph` with some persistent storage for example this can be done like this:
  ```yaml
  memgraph:
    enabled: true
    storageClass: 
      name: memgraph
      provisioner: "driver.longhorn.io"
  ```
## Example Config for 4 Fabrics
Here you can see an [Example Config for 4 Fabrics](4-fabric-example.yaml)

# Chart Deployment

Once the configuration file is generated i.e.: `aci-mon-stack-config.yaml` Helm can be used to deploy the stack:

```shell
helm repo add aci-monitoring-stack https://datacenter.github.io/aci-monitoring-stack
helm repo update
helm -n aci-mon-stack upgrade --install --create-namespace aci-mon-stack aci-monitoring-stack/aci-monitoring-stack -f aci-mon-stack-config.yaml
```

# OpenShift:

Openshift adds on top of Kubernetes a lof of security features and by default will only allow rootless containers to run. This is problematic as most containers that works on Kubernetes needs to be re-created to work on OpenShift. Memgraph, syslog-ng will all not run by default, ideally I would just use the `privileged` scc however his doesen't work as I need to share a PVC between pods. 

This requires the SELinux policy to be set as `MustRunAs` See: https://access.redhat.com/solutions/6746451 for more details.

To circumvent this issue I am creating a new `SecurityContextConstraints` that allows:
- Pods to run with `anyuid`
- Pods to run as privileged
- Set the SELinux policy to be  `MustRunAs`

I then create a `ServiceAccount`, `Cluster Role` and `Cluster Role Binding` to bind it all together and use it for all the PODs. This is perhaps not ideal but I am no OpenShift security expert. I am open to receive feedback and PR on this! :) 

All these objects are defined in the [Openshift](../charts/aci-monitoring-stack/templates/openshift) folder and are created only if the we detect deploying on OpenShift.
However the helm value file will need to define a `global.serviceAccountName:` and also pass it to the various sub-charts. Check out the [openshift](example-openshift.yaml) example and look where I use the `priviledgedServiceAccountName` yaml anchor to see where you need to set this config. 

## Loki and OpenShift Object Store

Now that the PODs are running we need to create the required object store buckets for our cluster.
If you do not have Ceph installed you can use Minio as per standard K8s but if you have Ceph we can ise it directly!

1) First we start by enabling the `cephBuckets` flag, this will have the [cephBuckets](../charts/aci-monitoring-stack/templates/openshift/buckets.yaml) created.
```yaml
loki:
  cephBuckets:
    enabled: true
    bucketName: &bucketName loki-bucket
    storageClassName: ocs-storagecluster-ceph-rgw
    endpoint: &bucketEndpoint rook-ceph-rgw-ocs-storagecluster-cephobjectstore.openshift-storage.svc:443
```

2) We need to tell all the various components to use the created buckets and associated credentials and explicitly disable minio. Please notice that I am using YAML anchor so yo u should be able to set all the parameters in the previous section and just copy paste what is below

```yaml
loki:
  loki:
    storage:
      bucketNames:
        admin: *bucketName
        chunks: *bucketName
        ruler: *bucketName
      object_store: null
      s3:
        endpoint: *bucketEndpoint
        insecure: true
      type: s3
      use_thanos_objstore: true
    # Yes this needs to be repeated twice... 
    storage_config:
      aws:
        bucketnames: *bucketName
        endpoint: *bucketEndpoint
        insecure: false
        http_config:
          insecure_skip_verify: true
        s3forcepathstyle: true
  backend:
    extraEnvFrom:
      - secretRef:
          name: *bucketName
  write:
    extraEnvFrom:
      - secretRef:
          name: *bucketName
  read:
    extraEnvFrom:
      - secretRef:
          name: *bucketName
  # I use CephFS for the storage, so I don't need to set this
  minio:
    enabled: false
```

3) Lastly Furthermore we need to tell loki the Cluster DNS is not the usual one by setting:
```yaml
loki:
  global:
    dnsService: "dns-default"
    dnsNamespace: "openshift-dns"
```

A complete config can be found here: [example-openshift](example-openshift.yaml)