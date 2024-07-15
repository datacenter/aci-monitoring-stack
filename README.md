aci-monitoring-stack - Open Source Monitoring for Cisco ACI
------------

# Overview

Harness the power of open source to efficiently monitor your Cisco ACI environment with the ACI-Monitoring-Stack. This lightweight, yet robust, monitoring solution combines top-tier open source tools, each contributing unique capabilities to ensure comprehensive visibility into your ACI infrastructure.

The ACI-Monitoring-Stack integrates the following key components:

- Grafana: The leading open-source analytics and visualization platform. Grafana allows you to create dynamic dashboards that provide real-time insights into your network's performance, health, and metrics. With its user-friendly interface, you can easily visualize and correlate data across your ACI fabric, enabling quicker diagnostics and informed decision-making.

- Prometheus: A powerful open-source monitoring and alerting toolkit. Prometheus excels in collecting and storing metrics in a time-series database, allowing for flexible queries and real-time alerting. Its seamless integration with Grafana ensures that your monitoring stack provides a detailed and up-to-date view of your ACI environment.

- Loki: Designed for efficiently aggregating and querying logs from your entire ACI ecosystem. Loki complements Prometheus by focusing on log aggregation, providing a unified stack for metrics and logs. Its integration with Grafana enables you to correlate log data with metrics and create a holistic monitoring experience.

- ACI-Exporter: A custom-built exporter that serves as the bridge between your Cisco ACI environment and the Prometheus monitoring ecosystem. The ACI-Exporter translates ACI-specific metrics into a format that Prometheus can ingest, ensuring that all crucial data points are captured and monitored effectively.

- Pre-configured ACI data collections queries, alerts, and dashboards (Work In Progress): The ACI-Monitoring-Stack provides a solid foundation for monitoring an ACI fabric with its pre-defined queries, dashboards, and alerts. While these tools are crafted based on best practices to offer immediate insights into network performance, they are not exhaustive. The strength of the ACI-Monitoring-Stack lies in its community-driven approach. Users are invited to contribute their expertise by providing feedback, sharing custom solutions, and helping enhance the stack. Your input helps to refine and expand the stack's capabilities, ensuring it remains a relevant and powerful tool for network monitoring.

# Your Stack

```mermaid
flowchart-elk
  subgraph ACI Monitoring Stack
    G["Grafana"]
    P[("Prometheus")]
    L["Loki"]
    PT["Promtail"]
    AM["Alertmanager"]
    A["ACI Exporter"]
    G--"PromQL"-->P
    G--"LogQL"-->L
    P-->AM
    PT-->L
    P--"Service Discovery"-->A
  end
  subgraph ACI
    S["Switches"]
    APIC["APIC"]
  end
  A--"API Queries"-->S
  A--"API Queries"-->APIC
  S--"Syslog"-->PT
  APIC--"Syslog"-->PT
  U["User"]
  N["Notifications (Mail/Webex etc...)"]
  U-->G
  AM-->N
```
