# Minikube

minikube config set memory 4016
minikube config set cpus 4

This can be used to run aci-monitoring-stack locally  however by default minikube only provide access locally. If you know what you are doing you can install NGINX on the host running minikube to provide access to your service. 

For example:

```shell
grafana:
  enable: true
  service:
    enabled: true
    type: NodePort
    NodePort: 9000


global
	log /dev/log	local0
	log /dev/log	local1 notice
	chroot /var/lib/haproxy
	stats socket /run/haproxy/admin.sock mode 660 level admin expose-fd listeners
	stats timeout 30s
	user haproxy
	group haproxy
	daemon

	# Default SSL material locations
	ca-base /etc/ssl/certs
	crt-base /etc/ssl/private

	# See: https://ssl-config.mozilla.org/#server=haproxy&server-version=2.0.3&config=intermediate
        ssl-default-bind-ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384
        ssl-default-bind-ciphersuites TLS_AES_128_GCM_SHA256:TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256
        ssl-default-bind-options ssl-min-ver TLSv1.2 no-tls-tickets

defaults
	log	global
	mode	http
	option	httplog
	option	dontlognull
        timeout connect 5000
        timeout client  50000
        timeout server  50000
	errorfile 400 /etc/haproxy/errors/400.http
	errorfile 403 /etc/haproxy/errors/403.http
	errorfile 408 /etc/haproxy/errors/408.http
	errorfile 500 /etc/haproxy/errors/500.http
	errorfile 502 /etc/haproxy/errors/502.http
	errorfile 503 /etc/haproxy/errors/503.http
	errorfile 504 /etc/haproxy/errors/504.http

frontend grafana
    bind 172.16.0.14:443 ssl crt /etc/ssl/private/grafana.pem
    default_backend grafana

backend grafana
    balance roundrobin
    server grafana 192.168.49.2:30000  check maxconn 20

frontend promtail-site1
    bind 172.16.0.14:1511
    default_backend promtail-site1

backend promtail-site1
    balance roundrobin
    server promtail 192.168.49.2:30001  check maxconn 20

frontend promtail-site2
    bind 172.16.0.14:1512
    default_backend promtail-site2

backend promtail-site2
    balance roundrobin
    server promtail 192.168.49.2:30002  check maxconn 20

frontend promtail-site3
    bind 172.16.0.14:1513
    default_backend promtail-site3

backend promtail-site3
    balance roundrobin
    server promtail 192.168.49.2:30003  check maxconn 20
```

## minikube/podman wrong CNI Version

If minikube dosen't start and complains about the wrong CNI version for bridge open /etc/cni/net.d/11-crio-ipv4-bridge.conflist and set "cniVersion": "0.4.0" from 1.0.0

## Prometheus does not install under minikube/podman 

Log into minikube with minikube ssh.
Run sudo vi /etc/containers/registries.conf.
Add unqualified-search-registries = ["docker.io", "quay.io"].
Restart minikube with minikube stop && minikube start.

