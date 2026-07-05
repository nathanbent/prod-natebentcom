---
title: 'iDRAC Fan Control'
date: 2024-09-25T11:54:26-05:00
author: "Nate"
# weight: 1
# aliases: ["/first"]
tags: ["iDRAC"]
categories: ["Experiences"]
#series: ["No-Series"]
showToc: true
TocOpen: false
draft: false
hidemeta: false
comments: false
description: "Basic iDRAC fan control with ipmitool, and why it stops working on newer firmware"
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

## Context

I run a couple of Dell PowerEdge boxes in the homelab, and out of the box they are loud. Dell's thermal algorithm is tuned for a datacenter, so it errs hard toward cooling, which is exactly the wrong tradeoff for a room I actually sit in. The good news is that iDRAC exposes IPMI (the Intelligent Platform Management Interface), and with `ipmitool` you can talk to the BMC directly and set the fan speed yourself, either over the network or locally on the box.

This is the basic version: install the tool, confirm you can reach the BMC, read the fans, and set them. One thing up front, because it will save you some frustration: Dell has since walked this back on newer firmware, and I get into that at the end.

## Installing ipmitool

`ipmitool` is in most distro repos:

```bash
sudo apt install ipmitool   # For Debian/Ubuntu
sudo yum install ipmitool   # For RHEL/CentOS
```

If you are talking to the BMC over the network, you also need IPMI over LAN turned on. That lives in the iDRAC UI under iDRAC Settings > Connectivity > Network > IPMI Settings.

> [!TIP]
> If you are running `ipmitool` from the server itself, use the local interface (`-I open`) instead of `-I lanplus`. It skips the credentials, and more to the point it means you are not exposing iDRAC's IPMI stack to your LAN. An old BMC IPMI implementation is not something I want reachable from the network if I can help it.

## Confirming you can reach the BMC

Over the network you pass `-H` for the BMC address, `-U` for the user, and `-P` for the password. The quickest way to confirm you are actually talking to the thing is a full sensor dump:

```
ipmitool -I lanplus -H <BMC-IP> -U <username> -P <password> sdr
```

That returns the sensor data records: fans, temperatures, and voltages. If real numbers come back, you are connected.

## Reading the current fan speeds

Before you change anything, look at what the fans are doing so you have a baseline to compare against:

```bash
ipmitool -I lanplus -H <BMC-IP> -U <username> -P <password> sensor list | grep -i fan
```

That lists every fan and its current RPM.

## Setting the fans

Manual control is two switches and a speed command. The switch is the part I had wrong in my head at first:

> [!INSIGHT]
> `raw 0x30 0x30 0x01 0x00` turns manual control on, and `0x30 0x30 0x01 0x01` turns it back off. The `0x00`/`0x01` reads backwards from what you would guess: `0x00` hands control to you, and `0x01` hands it back to Dell's automatic algorithm.

Replace `<BMC-IP>`, `<username>`, and `<password>` in all of these.

Enable manual fan control:
`ipmitool -I lanplus -H <BMC-IP> -U <username> -P <password> raw 0x30 0x30 0x01 0x00`

Hand the fans back to Dell's automatic control:
`ipmitool -I lanplus -H <BMC-IP> -U <username> -P <password> raw 0x30 0x30 0x01 0x01`

Set a specific fan speed:
`ipmitool -I lanplus -H <BMC-IP> -U <username> -P <password> raw 0x30 0x30 0x02 0xff <fan-speed>`

Breaking out that last one: `0xff` applies the command to all fans, and `<fan-speed>` is the speed as a hex percentage. The values you will actually reach for:

| Fan speed | Hex value |
|-----------|-----------|
| 10% | `0x0A` |
| 20% | `0x14` |
| 30% | `0x1E` |
| 50% | `0x32` |
| 100% | `0x64` |

Putting it together, to enable manual control and drop the fans to 30%:

```bash
ipmitool -I lanplus -H <BMC-IP> -U <username> -P <password> raw 0x30 0x30 0x01 0x00
ipmitool -I lanplus -H <BMC-IP> -U <username> -P <password> raw 0x30 0x30 0x02 0xff 0x1E
```

## What changed on newer iDRAC

If you run the commands above and get `Insufficient privilege level` back, this is why. On 14th-gen PowerEdge (iDRAC 9), Dell removed access to these raw commands in firmware 3.34.34.34. It was deliberate: the raw command bypasses their multi-vector cooling algorithm, and a Dell engineer confirmed on the community forums that after enough support escalations they cut it off. Firmware 3.30.30.30 is the last version that still honors the commands, which is why the downgrade path below lands there.

The rejection looks like this:

```
Unable to send RAW command (channel=0x0 netfn=0x30 lun=0x0 cmd=0x30 rsp=0xd4): Insufficient privilege level
```

On current firmware the sanctioned knobs are the fan speed offset and minimum fan speed, under Configuration > System Settings > Hardware Settings > Fans in the iDRAC UI, or the matching `system.thermalsettings` objects through racadm. The catch is that they only let you push fan speeds up from the baseline, not force them quiet, so for a noise problem they do not really help. That is the whole reason people bother downgrading.

Dell's reasoning is fair enough, honestly: plenty of people (me included) will happily set a fan too low and cook something, then act surprised. It is still frustrating if you are running these in a room where noise matters.

> [!CAUTION]
> This downgrade path only works if your iDRAC can still roll back that far. Per Dell KB RAC0181, once a 14G server installs the June 2024 firmware (7.00.00.172), or a 15G server installs 7.10.50.00, it can no longer be downgraded to 4.40.10.00 or older. If your box has already taken that update, the route down to 3.30.30.30 is closed and no ipmitool trick reopens it. Check where you are before you count on this.

There is a downgrade path that worked for me ([from this Reddit thread](https://www.reddit.com/r/homelab/comments/t9pa13/dell_poweredge_fan_control_with_ipmitool/)):

`7.00.00.00 -> 6.10.80.00 -> 6.00.02.00 -> 5.10.50.00 -> 5.00.00.00 -> 4.40.40.00 -> 4.40.10.00 -> 4.00.00.00 -> 3.30.30.30`

Obviously YMMV, and I don't take any responsibility for anything good or bad that happens.

## References and further reading
- [Dell KB RAC0181: iDRAC9 firmware downgrade failures on 14G/15G servers](https://www.dell.com/support/kbdoc/en-us/000225924/rac0181-idrac9-firmware-downgrade-failures-on-14-15g-poweredge-servers)
- [Dell Community: "Dell ENG is taking away fan speed control" (where Dell confirmed the 3.34.34.34 change)](https://www.dell.com/community/en/conversations/poweredge-hardware-general/dell-eng-is-taking-away-fan-speed-control-away-from-users-idrac-3343434/647f8593f4ccf8a8de47aa9b)
- [Dell: Modifying thermal settings using RACADM](https://www.dell.com/support/manuals/en-us/idrac9-lifecycle-controller-v3.3-series/idrac9_3.36.36.36_ug/modifying-thermal-settings-using-racadm)
- [Reddit: Dell PowerEdge fan control with ipmitool (the downgrade thread)](https://www.reddit.com/r/homelab/comments/t9pa13/dell_poweredge_fan_control_with_ipmitool/)
- [Reddit: PowerEdge G13 fan control issues, a quick guide](https://www.reddit.com/r/homelab/comments/u1bwl2/poweredge_g13_fan_control_issues_a_quick_guide/)
