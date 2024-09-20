# Minikube

This can be used to run aci-monitoring-stack locally (say on your laptop).

By default, minikube only provide access locally and this is an issue for logs ingestion however for a lab you can configure HAProxy to expose you Minikube instance over the Host IP Address. This implies that you should configure all your External Services as `NodePort` and configure HAProxy to send the traffic to the correct `NodePort`

I have configured minikube with 4GB or RAM and 4 CPU and that was plenty to monitor a small 10 switch ACI Fabric. 

```shell
minikube config set memory 4016
minikube config set cpus 4
```

Example HPProxy Config

```shell
frontend grafana
    # Here I am doing SSL Termination
    bind <HostIP>:443 ssl crt /etc/ssl/private/grafana.pem
    default_backend grafana

backend grafana
    balance roundrobin
    server grafana <minikubeIP>:30000  check

frontend promtail-site1
    mode tcp
    bind <HostIP>:1511
    default_backend promtail-site1

backend promtail-site1
    mode tcp
    balance roundrobin
    server promtail <minikubeIP>:30001  check

frontend promtail-site2
    mode tcp
    bind <HostIP>:1512
    default_backend promtail-site2

backend promtail-site2
    mode tcp
    balance roundrobin
    server promtail <minikubeIP>:30002  check

frontend promtail-site3
    mode tcp
    bind <HostIP>:1513
    default_backend promtail-site3

backend promtail-site3
    mode tcp
    balance roundrobin
    server promtail <minikubeIP>:30003  check
```


# Troubleshooting

While installing Minikube I hit the following issues:

## minikube/podman wrong CNI Version
See https://github.com/kubernetes/minikube/issues/17754
For me this fixed it:
```
#sudo apt list --all-versions podman
podman/jammy-updates,jammy-security,now 3.4.4+ds1-1ubuntu1.22.04.2 amd64 [installed]  <=== Seems is bad
podman/jammy 3.4.4+ds1-1ubuntu1 amd64

#sudo apt install podman=3.4.4+ds1-1ubuntu1
Reading package lists... Done
```
## Prometheus does not install under minikube/podman 

Log into minikube with `minikube ssh`.


```shell
sudo vi /etc/containers/registries.conf
```

`unqualified-search-registries = ["docker.io", "quay.io"]`

Restart minikube
```shell
minikube stop && minikube start
```

>
