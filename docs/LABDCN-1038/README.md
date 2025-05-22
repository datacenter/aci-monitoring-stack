# LABDCN-1038: Open Source Monitoring for Cisco ACI

This section contains specific instruction on how to run the *LABDCN-1038* Walk In Lab for Cisco Live San Diego 2025. 

## Task 1 - Getting Familiar with the ACI Monitoring Stack

If this is your first time learning about the ACI monitoring stack you should start with the [Overview](overview.md) that provides an overview of the Stack Architecture.
You do not need to deep dive in the details, unless you want to, but is good to have a generic understanding of the components used in the Stack.

Next head over the [Demo Environment](../demo-environment.md) documentation, as you read this section explore the dashboard that are available in the Demo Environment.

## Task 2 - Create a Dashboard

[Lab1](../labs/lab1.md): In this lab we are going to re-built the ACI Fault Dashboard

## Task 3 - Explore The Logs

[Lab2](../labs/lab2.md): In this lab we are going to use `Explore` to visualize the Logs Received by our ACI fabrics. 

## Task 4 - Explore the ACI Configs

The ACI Monitoring Stack introduced a new feature in its last release that automatically generates a Config Snapshot every 15 minutes (by default) and seamlessly loads it into a Graph Database. This allow the user to then query the ACI config directly from Grafana.

[Lab3](../labs/lab3.md)