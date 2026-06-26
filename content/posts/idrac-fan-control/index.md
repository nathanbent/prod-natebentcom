---
title: 'iDRAC Fan Control'
date: 2024-09-25T11:54:26-05:00
author: "Nate"
weight: 1
# aliases: ["/first"]
tags: ["iDRAC"]
categories: ["Experiences"]
#series: ["No-Series"]
showToc: true
TocOpen: false
draft: false
hidemeta: false
comments: false
description: "Basic iDRAC fan control via impitool"
canonicalURL: "https://canonical.url/to/page"
disableHLJS: true # to disable highlightjs
disableShare: true
hideSummary: false
searchHidden: true
ShowReadingTime: true
ShowBreadCrumbs: true
ShowPostNavLinks: true
ShowWordCount: true
ShowRssButtonInSectionTermList: true
UseHugoToc: true
cover:
    image: "<image path/url>" # image path/url
    alt: "<alt text>" # alt text
    caption: "<text>" # display caption under cover
    relative: false # when using page bundles set this to true
    hidden: true # only hide on current single page
editPost:
    disaled: true
    URL: "https://github.com/<path_to_repo>/content"
    Text: "Suggest Changes" # edit text
    appendFilePath: true # to append file path to Edit link
---

## Concept

Managing server fan speed is crucial for maintaining an optimal balance between cooling efficiency and noise levels, especially in environments where temperature control and acoustics are important. Dell servers, like many other enterprise-grade hardware, come equipped with Intelligent Platform Management Interface (IPMI) capabilities. With the help of ipmi-tools, we can access and control various hardware components of the server, including fan speed, remotely or locally, without needing direct access to the operating system.

Here, I will walk through some of the basics of how you can control the fan speed of your iDRAC-enabled Dell servers.

## Steps involved

### Step 1: Install impitools & enable IPMI access on device
You will need to install `ipmitool`

```bash
sudo apt install ipmitool   # For Debian/Ubuntu
sudo yum install ipmitool   # For RHEL/CentOS
```

### Step 2: Verify IPMI Access
First, verify that you can communicate with the IPMI interface using the `ipmitool` command. If you're accessing a remote server, you’ll use the -H flag for the server’s IP address, the -U flag for the username, and the -P flag for the password.

Run the following command to check IPMI connection and get a system status overview:

`ipmitool -I lanplus -H <BMC-IP> -U <username> -P <password> sdr`

This should return sensor data, including fan speeds, temperatures, and voltages.

### Step 3: Check Current Fan Speed
To view the current fan speed, use the following command:

bash
Copy code
ipmitool -I lanplus -H <BMC-IP> -U <username> -P <password> sensor list | grep -i fan
This will display all the fans in your system along with their current RPM (revolutions per minute). Understanding the current fan speeds will help when making adjustments later.

## Commands to copy

> Replace `<BMC-IP>`, `<username>`, `<password>`


Enable manual fan control: `ipmitool -I lanplus -H <BMC-IP> -U <username> -P <password> raw 0x30 0x30 0x01 0x00`

Disable manual fan control: `ipmitool -I lanplus -H <BMC-IP> -U <username> -P <password> raw 0x30 0x30 0x01 0x01`

Set a specific fan speed: `ipmitool -I lanplus -H <BMC-IP> -U <username> -P <password> raw 0x30 0x30 0x02 0xff <fan-speed>`

> To break this command out;
>   - The `0xff` indicates that this command applies to all fans
>   - The `<fan-speed>` indicates the fan speed (in hexadecimal)

Some examples of specific fan speed commands:

Set fan speed to 10%: `ipmitool -I lanplus -H <BMC-IP> -U <username> -P <password> raw 0x30 0x30 0x02 0xff 0x0A`

Set fan speed to 20%: `ipmitool -I lanplus -H <BMC-IP> -U <username> -P <password> raw 0x30 0x30 0x02 0xff 0x14`

Set fan speed to 30%: `ipmitool -I lanplus -H <BMC-IP> -U <username> -P <password> raw 0x30 0x30 0x02 0xff 0x1E`

Set fan speed to 50%: `ipmitool -I lanplus -H <BMC-IP> -U <username> -P <password> raw 0x30 0x30 0x02 0xff 0x32`

Set fan speed to 100%: `ipmitool -I lanplus -H <BMC-IP> -U <username> -P <password> raw 0x30 0x30 0x02 0xff 0x64`

To enable fan control and set the speed to 30%:
```bash
ipmitool -I lanplus -H <BMC-IP> -U <username> -P <password> raw 0x30 0x30 0x01 0x00
ipmitool -I lanplus -H <BMC-IP> -U <username> -P <password> raw 0x30 0x30 0x02 0xff 0x1E
```

## Some notes about recent-ish iDRAC updates

After iDRAC 9 version3.30.30.30, fan control has been disabled by Dell.  Some forum posts [here](https://www.dell.com/community/en/conversations/poweredge-hardware-general/dell-eng-is-taking-away-fan-speed-control-away-from-users-idrac-3343434/647f8593f4ccf8a8de47aa9b) on Dell's support page indicate that this was done to prevent inadvertant damage to servers from people like me doing stuff like this.  This is both a fair point, but also somewhat frustrating for those of us running these in more acoustically-sensitive environments.

There is a downgrade path that worked for me ([from this Reddit thread](https://www.reddit.com/r/homelab/comments/t9pa13/dell_poweredge_fan_control_with_ipmitool/)):
`7.00.00.00 -> 6.10.80.00 -> 6.00.02.00 -> 5.10.50.00 -> 5.00.00.00 -> 4.40.40.00 -> 4.40.10.00 -> 4.00.00.00 -> 3.30.30.30`

Though obviously YMMV, and I don't take any responsibility for anything good/bad that happens.

## References and further reading
- [Reddit thread about iDRAC downgrading](https://www.reddit.com/r/homelab/comments/t9pa13/dell_poweredge_fan_control_with_ipmitool/)
- [PowerEdge G13 Fan Control - Reddit](https://www.reddit.com/r/homelab/comments/u1bwl2/poweredge_g13_fan_control_issues_a_quick_guide/)