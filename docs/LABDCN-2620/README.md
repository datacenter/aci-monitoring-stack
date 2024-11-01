# LABDCN-2620: Open Source Monitoring for Cisco ACI

This section contains specific instruction on how to run the *LABDCN-2620* Walk In Lab for Cisco Live APJC 2024. 
All the tasks aside the last one can be run without VPN access to the DMZ. 
DMZ credentials will be available from the eXpo portal. 


## Task 1 - Getting Familiar with the ACI Monitoring Stack

If this is your first time learning about the ACI monitoring stack you should start with the [Overview](overview.md) that provides an overview of the Stack Architecture.
You do not need to deep dive in the details, unless you want to, but is good to have a generic understanding of the components used in the Stack.

Next head over the [Demo Environment](../demo-environment.md) documentation, as you read this section explore the dashboard that are available in the Demo Environment.

## Task 2 - Create a Dashboard

[Lab1](../labs/lab1.md): In this lab we are going to re-built the ACI Fault Dashboard

## Task 3 - Explore The Logs

[Lab2](../labs/lab2.md): In this lab we are going to use `Explore` to visualize the Logs Received by our ACI fabrics. 

## Task 4 - Deploy the Monitoring Stack (Requires VPN Access)

The ACI Monitoring Stack can be deployed on any Kubernetes cluster. For this lab, I am providing a pre-configured Kubernetes environment where no major configuration will be required. 

Before proceeding with this tasks I'd suggest you familiarize yourself by reading the [Deployment](../deployment.md) which contains the details on how to setup the ACI Monitoring Stack from scratch however for this Task you should follow the [DMZ Deployment](dmz-deploy.md) instructions.