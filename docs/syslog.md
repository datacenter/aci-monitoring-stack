# Cisco ACI Syslog Configuration Guide

Follow these steps to configure Syslog for Cisco Application Centric Infrastructure (ACI):

## 1. Access the APIC Management Console
- Open a web browser and navigate to the management IP address of your Application Policy Infrastructure Controller (APIC).
- Log in with your credentials.

## 2. Navigate to the Syslog Policy Configuration
- Click on the `Admin` menu at the top.
- Select `External Data Collectors`
- Choose `Monitoring Destinations`, then `Syslog`.

## 3. Add a Syslog Server
- Right Click on the `Syslog` folder and add a new Syslog server.
- Enter the name for the Syslog server policy.
  - Format: Enhanced Log
  - Admin Stat: Enabled4
- Click Next to configure the `Remote Destination`
  - Click on `+`:
    - Hostname: The promtail Service IP Address. 
    - Port: The promtail Port IP Address. 
    - Name: a name 
    - Admin State: Enabled 
    - Severity: Informational (this is required to get contract drop logs)
    - Management EPG: Select the management EPG to source the messages from

## 4 Configure Monitoring Policies

Syslog monitoring policies can be configured at different scopes:
-  Fabric > Fabric Policies > Policies > Monitoring > Default > Callhome/Smart Callhome/SNMP/Syslog/TACACS > Syslog
-  Fabric > Access Policies > Policies > Monitoring > Default > Callhome/Smart Callhome/SNMP/Syslog > Syslog
-  Tenant > Policies > Monitoring > Default > Callhome/Smart Callhome/SNMP/Syslog > Syslog
   -  If you want to have a common policy for all your tenants you can configure the policy under the `common` tenant and will be applied to all your tenants
For each of the above scopes repeat the following:
  - Select Syslog and click on `+`
  - Name: a name
  - Min Severity: Information (Choose based on your needs)
    - For ACI Contract Deny Logs the Min severity for the `Access Policies` MUST BE Information
  - Include: Select All the Options
  - Dest Group: Select the Destiantion group created in the previous step.

### Enabling the sending of ACL/Contract Log entries as SYSLOG events

The enable ACI to send Contract Permit/Deny log messages change the default syslog policy from `alerts` to `information`. To do so go to:
- Fabric > Fabric Policies > Policies > Monitoring > Common Policy > Syslog Message Policy > default
- From `Facility Filters` deouble click on `default` and set the `Severity` to `information`

*Warning*: ACI Contract Deny Logs is limited to 500 Messages/s per switch aci-monitoring-stack

## 4. Apply the Syslog Policy to an Administrative Domain (Tenant)
- Navigate to `Tenants` on the top menu.
- Select the tenant to which you wish to apply the Syslog policy.
- Within the tenant, go to `Monitoring Policies`.
- Choose `Common Policy` and then `Logging`.
- Associate the Syslog server policy with the tenant by selecting it from the list.
- Apply the policy to the desired EPGs (Endpoint Groups), applications, or ACI constructs.
