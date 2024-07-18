# Development Guide

## Creating/Editing Dashboards

Assuming the data required is available (see the [Data Collection](#data-collection) section) you can develop or modify Grafana Dashboard directly in the UI. 
Once you are happy with the result you can copy-paste the JSON model in a new file (or update an existing one) and place it in the [dashboards](../charts/aci-monitoring-stack/dashboards) folder. 
The Helm chart creates a new [ConfigMap](../charts/aci-monitoring-stack/templates/grafana-configmap-dashboards.yaml) for each file in the dashboards folder and mounts it into the Grafana Container.
The ConfigMap name is the Filename without the extension. 

For example the `fabric-wide-capacity.json` file creates a ConfigMap called `fabric-wide-capacity-dashboard`


## Data Collection

Data is currently collected in two ways:

- Syslog Ingestion: The ACI Side Config "decides" what to send and assuming the correct logging level is selected you can then build the dashboards in grafana using Loki as a data source. You can take a look at the `Contract Drops Logs` dashboard for inspiration. 

- [aci-exporter](https://github.com/opsdis/aci-exporter) Queries: which queries and how the data is collected is highly customizable.

### aci-exporter and Prometheus

The general idea is to use aci-exporter to convert ACI Rest API Calls in the Prometheus exposition format.

The exporter also have the capability to directly scrape individual switches using the aci-exporter inbuilt http based service discovery. Doing direct spine and leaf queries is typical useful in large fabrics, where doing all api calls through the APIC can put a high load on the APIC and result in high response time.

**Note:** In the context of this HELM Chart a query **MUST** be executed against a switch if possible. Any code submission that does not adhere to this convention will not be accepted. 

#### aci-exporter Quick Start

Before working on aci-exporter, Prometheus and Grafana at the same time I strongly suggest to take a look at the [aci-exporter](https://github.com/opsdis/aci-exporter) git repo and understand how it works and how is configured. 

Here a complete example to get you started (you need to [install go](https://go.dev/doc/install))

- Clone the Repo and Compile the exporter
```bash
git clone https://github.com/opsdis/aci-exporter.git
go build -o build/aci-exporter  *.go
```
- Create a basic config file for you ACI Fabric

```yaml
fabrics:
  fab1:
    username: foo
    password: bar
    apic:
      - https://apic1
      - https://apic2
```
- The aci-exporter will, by default, load the queries it can execute from the `config.d` directory. For now, we don't want that so we can start the exporter with this command that will just load the bare minimum config to access the fabric.

```bash
./build/aci-exporter -config fab1.yaml -config_dir /dev/null
{"level":"info","msg":"Configuration directory do not exist - stat /home/cisco/aci-exporter/dev/null: no such file or directory","time":"2024-07-18T14:17:59+10:00"}
{"fabric":"fab1","level":"info","msg":"Configured fabric","time":"2024-07-18T14:17:59+10:00"}
{"config_file":"/home/cisco/aci-exporter/fab1.yaml","level":"info","msg":"aci-exporter starting","port":9643,"read_timeout":0,"time":"2024-07-18T14:17:59+10:00","version":"undefined","write_timeout":0}
```

- Now aci-exporter is running on our host on port 9643, let's try a Service Discovery just run an HTTP request against the `/sd` URL.

``` bash
curl http://aci-exporter-ip:9643/sd

[
    {
        "targets": [
            "fab1#10.67.185.106"
        ],
        "labels": {
            "__meta_aci_exporter_fabric": "fab1",
            "__meta_address": "10.0.0.1",
            "__meta_dn": "topology/pod-1/node-1/sys",
            "__meta_fabricDomain": "ACI Fabric1",
            "__meta_fabricId": "1",
            "__meta_id": "1",
            "__meta_inbMgmtAddr": "192.168.68.2",
            "__meta_name": "fab1-apic1",
            "__meta_nameAlias": "",
            "__meta_nodeType": "unspecified",
            "__meta_oobMgmtAddr": "10.67.185.106",
            "__meta_podId": "1",
            "__meta_role": "controller",
            "__meta_serial": "WZP233907GX",
            "__meta_siteId": "0",
            "__meta_state": "in-service",
            "__meta_version": "6.1(1a)"
        }
    },
    === SNIP ===
]
```

This should return a list with all the Controllers and Switches in your fabric and is what Prometheus uses for its own service discovery.
Now let's try to build a query to check the `interface operation state and speed`.

- The ACI Class we can use for this query is `ethpmPhysIf`
- This class is available both on the APIC and on the Switches: we will run this query **against the switches** because it is the core principle for this HELM chart, and it scales better.
- *Tip:* If you use Visual Studio Code you can install the `Thunder Client` to test API Calls.

Every switch will return one `ethpmPhysIf` object for every interface. An example is provided below:
```yaml
{
    "ethpmPhysIf": {
    "attributes": {
        "accessVlan": "unknown",
        "allowedVlans": "",
        "backplaneMac": "00:DE:FB:21:37:E2",
        "bundleBupId": "2",
        "bundleIndex": "unspecified",
        "cfgAccessVlan": "unknown",
        "cfgNativeVlan": "unknown",
        "childAction": "",
        "currErrIndex": "4294967295",
        "diags": "none",
        "dn": "sys/phys-[eth1/34]/phys",
        "encap": "3",
        "errDisTimerRunning": "no",
        "errVlanStatusHt": "0",
        "errVlans": "",
        "hwBdId": "0",
        "hwResourceId": "0",
        "intfT": "phy",
        "iod": "38",
        "lastErrors": "0",
        "lastLinkStChg": "2024-07-10T00:50:13.841+00:00",
        "media": "2",
        "modTs": "never",
        "monPolDn": "uni/infra/moninfra-default",
        "nativeVlan": "unknown",
        "numOfSI": "0",
        "operBitset": "3-4",
        "operDceMode": "edge",
        "operDuplex": "full",
        "operEEERxWkTime": "0",
        "operEEEState": "not-applicable",
        "operEEETxWkTime": "0",
        "operErrDisQual": "none",
        "operFecMode": "disable-fec",
        "operFlowCtrl": "0",
        "operMdix": "auto",
        "operMode": "trunk",
        "operModeDetail": "unknown",
        "operPhyEnSt": "unknown",
        "operRouterMac": "00:00:00:00:00:00",
        "operSpeed": "10G",
        "operSt": "up",
        "operStQual": "none",
        "operStQualCode": "0",
        "operVlans": "",
        "osSum": "failed",
        "portCfgWaitFlags": "0",
        "primaryVlan": "vlan-1",
        "resetCtr": "1",
        "siList": "",
        "status": "",
        "txT": "unknown",
        "usage": "discovery",
        "userCfgdFlags": "1",
        "vdcId": "1"
        }
    }
}
```

Of all the various properties of `ethpmPhysIf` we need only 3:

- `operSpeed`: The speed
- `operSt`: If the port is UP/Down
- `dn`: We use the content of the `dn` to extract two lables:
    - `interface_type`: Physical, Port-Channel etc...
    - `interface`: The interface name, i.e. Eth1/1

With these infos we can create 2 metrics that I am going to call: 

- `interface_oper_speed`
- `interface_oper_state`

Both metrics will be labeled with the`interface_type` and `interface` (name). However, we are faced with an issue... Prometheus can only ingest numbers, so we can't just pass `40G` or `up` as a valid metric. 

Thankfully one of the many aci-exporter capabilities is to perform `value_transform` so we can write something like this:

```yaml 
value_transform:
    'unknown': 0
    '100M': 100000000
    '1G': 1000000000
    '10G': 10000000000
    '25G': 25000000000
    '40G': 40000000000
    '100G': 100000000000
    '400G': 400000000000

value_transform:
    'unknown': 0
    'down': 1
    'up': 2
    'link-up': 3
```
To convert text to numbers and allow Prometheus to ingest this data.

Lastly we need to also extract the `labels` from the `dn`. The format for this specific class is always something similar to `"sys/phys-[eth1/34]/phys"` to do this aci-exporter employs RegEx, below an example:

```yaml
labels:
    # The field in the json used to parse the labels from
    - property_name: ethpmPhysIf.attributes.dn
    regex: "^sys/(?P<interface_type>[a-z]+)-\\[(?P<interface>[^\\]]+)\\]/"
```
This named RegEx will create 2 new labels `interface_type` and `interface` and map them to the interface ID and Type. If you want to experiment with RegEx you can use https://regex101.com/, just select `Golang` also since the aci-exporter config is in yaml some character needs to be double escapade (`\\`). 

Putting all together a `class_queries` will look like this:
```yaml
class_queries:
  # This is the name of the query. A query can generate multiple metrics.
  node_interface_info:
    # Interface speed and status
    class_name: ethpmPhysIf
    metrics:
      # The name of the metrics without prefix and unit
      - name: interface_oper_speed
        value_name: ethpmPhysIf.attributes.operSpeed
        unit: bps
        type: gauge
        help: The current operational speed of the interface, in bits per second.
        value_transform:
          'unknown': 0
          '100M': 100000000
          '1G': 1000000000
          '10G': 10000000000
          '25G': 25000000000
          '40G': 40000000000
          '100G': 100000000000
          '400G': 400000000000
      - name: interface_oper_state
        # The field in the json that is used as the metric value, qualified path (gjson) under imdata
        value_name: ethpmPhysIf.attributes.operSt
        # Type
        type: gauge
        # Help text without prefix of metrics name
        help: The current operational state of the interface. (0=unknown, 1=down, 2=up, 3=link-up)
        # A string to float64 transform table of the value
        value_transform:
          'unknown': 0
          'down': 1
          'up': 2
          'link-up': 3
    # The labels to extract as regex
    labels:
      # The field in the json used to parse the labels from
      - property_name: ethpmPhysIf.attributes.dn
        regex: "^sys/(?P<interface_type>[a-z]+)-\\[(?P<interface>[^\\]]+)\\]/"
```

Now Copy/Paste this into the config file.

Based on the service discovery we executed before we have all the required infos to run a query against a switch, the aci-exporter URL has the following format:

`/probe?target=<__meta_aci_exporter_fabric>&node=<__meta_inbMgmtAddr|__meta_oobMgmtAddr>&queries=<query1,query2,etc>`
Here an example:

```bash
curl "http://aci-exporter-ip:9643/probe?target=fab1&node=192.168.68.8&queries=node_interface_info"
# HELP aci_interface_oper_speed_bps The current operational speed of the interface, in bits per second.
# TYPE aci_interface_oper_speed_bps gauge
aci_interface_oper_speed_bps{fabric="fab1",interface="eth1/1",interface_type="phys"} 1e+11
aci_interface_oper_speed_bps{fabric="fab1",interface="eth1/2",interface_type="phys"} 1e+11
aci_interface_oper_speed_bps{fabric="fab1",interface="eth1/3",interface_type="phys"} 4e+11

# HELP aci_interface_oper_state The current operational state of the interface. (0=unknown, 1=down, 2=up, 3=link-up)
# TYPE aci_interface_oper_state gauge
aci_interface_oper_state{fabric="fab1",interface="eth1/1",interface_type="phys"} 2
aci_interface_oper_state{fabric="fab1",interface="eth1/2",interface_type="phys"} 2
aci_interface_oper_state{fabric="fab1",interface="eth1/3",interface_type="phys"} 1

# HELP aci_scrape_duration_seconds The duration, in seconds, of the last scrape of the fabric
# TYPE aci_scrape_duration_seconds gauge
aci_scrape_duration_seconds{fabric="fab1"} 0.038120213
# HELP aci_up The connection state 1=UP, 0=DOWN
# TYPE aci_up gauge
aci_up{fabric="fab1"} 1
```

What happens with the ACI Monitoring Stack is that Prometheus executes queries against aci-exporter.

### Adding New Queries

ACI Monitoring Stack comes pre-configured with a lot of queries and are all located in the [config.d](../charts/aci-monitoring-stack/config.d) folder. The majority of these queries are directed against the switches and are pre-pended with the `node` keyword however it is not aci-exporter that decides where to send the queries. This is based on the URL used by Prometheus, check the [ScrapeConfigs](../charts/aci-monitoring-stack/templates/prometheus/configmap-config.yaml).  

You will see there are 2 type of scrape configs:
- *-aci-exporter-**apics**: This will execute queries against the APICs
- *-aci-exporter-**switches**: This will execute queries against the individual switches.

Selection between APIC or Switches is done by using different re-labeling configs for Prometheus. Most likely you won't need to change the re-labeling config.

To add a new query follow these steps:

- Develop a new aci-exporter query and test is with `curl` to ensure it returns the expected data
- Add the query to one of the files in the [config.d](../charts/aci-monitoring-stack/config.d) folder or create a new file if your query dosen't belong to any of the existing categoris. 
- add the query name in the `queries` list of the APIC or Switches inside the [ScrapeConfigs](../charts/aci-monitoring-stack/templates/prometheus/configmap-config.yaml).  

Below a scrape config example: 
```yaml
- job_name: {{ $k }}-aci-exporter-apics
scrape_interval: 5m
scrape_timeout: 4m
metrics_path: /probe
params:
    # List of the queries to execute at the fabric level. They need to match the aci-exporter config
    # DO NOT INSERT SPACES and use \ for next line or aci-exporter will not be able to parse the queries
    queries:
    - "health,fabric_node_info,max_capacity,max_global_pctags,\
        vlans,static_binding_info,node_count,object_count,\
        ps_power_usage,apic_hw_sensors,controller_topsystem"
```

