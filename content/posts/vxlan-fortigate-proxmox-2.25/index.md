---
title: "VXLAN Performance on a FortiGate 70F: The Software Switching Tax"
date: 2026-06-25T01:00:00Z
author: Nate
weight: 1
tags:
  - VXLAN
  - EVPN
  - FortiGate
  - Proxmox
  - SDN
  - Performance
  - NP7
  - Homelab
categories:
  - Networking
showToc: true
TocOpen: false
draft: false
hidemeta: false
comments: false
description: Measuring the throughput cost of VXLAN on a small FortiGate with no VXLAN offload, by A/B testing the same VM over an overlay segment versus a plain VLAN, and tracing the ceiling back to the silicon.
canonicalURL: https://canonical.url/to/page
disableHLJS: true
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
  image: <image path/url>
  alt: <alt text>
  caption: <text>
  relative: false
  hidden: true
editPost:
  disaled: true
  URL: https://github.com/<path_to_repo>/content
  Text: Suggest Changes
  appendFilePath: true
---

## The setup, and the question

A while back I built an EVPN/VXLAN overlay between a FortiGate and a three node Proxmox cluster. The overlay segments come out of Proxmox SDN (an EVPN zone with a handful of VNets), and the FortiGate plays anycast gateway for them. I wrote up the build itself in a separate post; this one is only about the thing I wanted to know once it was actually working: what does all that encapsulation cost me in throughput?

Short version, on a small FortiGate it costs more than I expected. And the reason turned out to be more interesting than "overlays have overhead." On this class of hardware VXLAN is switched in software, on the CPU, not on the network processor. Here is the test and the numbers that show it.

## The test

I wanted the cleanest A/B I could manage, so I changed exactly one thing. Same VM, same iperf3 server, same FortiGate, same everything. The only variable is the path the VM's traffic takes:

- Run 1: the VM sits on a VXLAN overlay segment (a Proxmox SDN VNet, gateway on the FortiGate).
- Run 2: the same VM, moved to a plain VLAN that also has its SVI on the FortiGate.

Both paths route through the same box to the same destination, so if the overlay costs anything, this isolates it. The test itself was nothing fancy:

```
iperf3 -c <server> -t 10
```

## The numbers

VXLAN overlay segment:

```
[ ID] Interval           Transfer     Bitrate         Retr
[  5]   0.00-10.00  sec   654 MBytes   548 Mbits/sec  179   sender
[  5]   0.00-10.00  sec   651 MBytes   546 Mbits/sec        receiver
```

Across several runs this sat in a tight band, roughly 525 to 548 Mbit/sec, always with a steady trickle of retransmits, somewhere between 150 and 300 per run.

Same VM, plain VLAN:

```
[ ID] Interval           Transfer     Bitrate         Retr
[  5]   0.00-10.00  sec  1.09 GBytes   935 Mbits/sec  109   sender
[  5]   0.00-10.00  sec  1.09 GBytes   934 Mbits/sec        receiver
```

935 Mbit/sec, which is line rate for the single gigabit path to that server. Clean, stable, and far fewer retransmits.

So the plain VLAN saturates the link, and the VXLAN path cannot even get close to the link ceiling because something pins it around 540 first. That something is the FortiGate's CPU, and you can watch it happen.

## Watching the CPU give it away

The numbers point at a CPU ceiling, and a couple of minutes on the box confirms it. The trick is just to watch what the firewall is doing during each transfer.

On the VLAN run, the CPU stays flat. Plain L2/L3 forwarding gets offloaded to the network processor and is effectively free, so the flow runs straight into the gigabit link limit and stops there.

On the VXLAN run, a CPU core jumps for the entire length of the transfer and drops back the instant iperf stops. That is the encapsulation and decapsulation work happening in software, one packet at a time.

A few commands make this concrete rather than a vibe:

```
get system performance status
diagnose sys top 2 20
```

`get system performance status` gives you the per core CPU load while the test runs; you will see one core climb on the overlay test and stay quiet on the VLAN test. `diagnose sys top` shows you which processes are eating it.

If you want to confirm it at the session level instead of by CPU, pull the flow out of the session table and look at whether it is offloaded:

```
diagnose sys session filter dport 5201
diagnose sys session list
```

On the VLAN flow the session carries the NP offload state (an `npu_state` value and an `npu info` block with the offloaded flags set). On the VXLAN flow it does not; the kernel is handling it, which is exactly why a core is pegged.

That same software datapath filling up under load is what produces the steady retransmits on the overlay path. It is not a wiring problem and it is not MTU (more on that below), it is the soft path saturating and dropping.

## The hardware, and why this is expected

This is a FortiGate 70F:

```
Model name: FortiGate-70F
ASIC version: SOC4
CPU: ARMv8
Number of CPUs: 8
RAM: 3773 MB
Network Card chipset: FortiASIC NP6XLITE Adapter (rev.)
```

The line that matters is the NP6XLite, and here is the part that took me a second to actually internalize. The "XLite" naming makes it sound like a newer, trimmed down processor, but NP6XLite is NP6 generation silicon. It is a component of Fortinet's SOC4. The NP6 family (NP6, NP6XLite, NP6Lite) offloads the usual IPv4/IPv6 forwarding, IPsec, CAPWAP and multicast, but VXLAN is not on that list. There is no hardware VXLAN datapath on this box at all, so every encapsulated packet is a CPU operation. That is the ceiling the iperf numbers and the pegged core are both showing.

VXLAN offload arrived with the NP7 generation. NP7 explicitly offloads VXLAN (and VXLAN over IPsec). And, worth stating clearly because I had this slightly wrong at first: the NP7Lite parts offload VXLAN too. The 50G/70G/90G/120G/200G class boxes run NP7Lite and will fast path VXLAN. There is even a Fortinet KB about a VXLAN over NP7Lite session bug, which you can only have if the thing is being offloaded in the first place.

So the real tell when you are shopping is generational, not "Lite versus not." It breaks down like this:

- NP6 family (NP6, NP6XLite, NP6Lite): no VXLAN offload. Software switched, CPU bound. The 70F lives here.
- NP7 family (NP7 and NP7Lite): VXLAN offload available.

The trap is specifically the NP6XLite, because the name pattern matches to the NP7Lite era when it does not belong to it. Do not read "XLite" as "small NP7." Check the FortiOS hardware acceleration guide's offload tables for the actual processor in your model, and confirm it on your own box, rather than trusting a marketing datasheet blurb, which varies in what it bothers to spell out.

> One caveat so this does not get over-applied: offload is both platform and configuration dependent. Even on hardware that can offload VXLAN, the moment you put UTM inspection on the flow (IPS, AV, SSL inspection) it goes back to the CPU, because inspection cannot run on the NP. There is also a `vxlan-offload` toggle, and on NP7 the `learn-from-traffic` setting on the VXLAN interface quietly controls whether the overlay gets hardware accelerated at all. So "does my box offload VXLAN" is really two questions: can the silicon do it, and does my config let it stay offloaded. Watch the CPU and check the session flags either way.

## An MTU aside, because it hid all of this at first

Before any of the above made sense, the overlay was doing about 9 Mbit/sec, not 540, and iperf would push a short burst and then collapse to zero. That was not the CPU. That was a textbook MTU black hole: the guest NIC was still at 1500 while the overlay path is 1450, so the moment TCP grew its segments past the small stuff, the full size frames got silently dropped. Dropping the guest NIC to 1450 fixed it and uncovered the real 540 ceiling sitting underneath.

The part worth keeping, because it is the actual diagnostic, is what came next. Once it was working, I bumped the overlay MTU up to 8950 (the underlay is jumbo) and the throughput changed by basically nothing. If per packet overhead had been the limiter, bigger frames would have bought me a lot. They bought me nothing, which is what tells you the ceiling is a fixed per flow cost (the CPU) and not a per packet one.

## So what do you actually do with this

None of this is a bug to fix. It is the platform being honest about its limits, and the right move is to design around them instead of fighting them:

- Put traffic on the overlay that actually benefits from being there: segmentation, inspected east-west, stretched or mobile segments, the anycast gateway. None of that is throughput bound, and a few hundred Mbit is plenty for it.
- Keep the bulk, throughput sensitive stuff (storage, backups, replication) on plain VLANs, where the NP offloads ordinary forwarding and hands you line rate. My iSCSI was already on a VLAN, which it turns out is exactly right, for exactly this reason.
- If you genuinely need line rate inspected VXLAN, buy into the NP7 generation and confirm VXLAN offload for that specific model in the hardware acceleration guide. Do not assume a newer or bigger model number gets you there, and definitely do not let an "XLite" lull you.

The overlay's flexibility is real and worth having. On small hardware it just comes with a throughput price, and now that price has a number: about 540 Mbit/sec of software switched VXLAN on a 70F, against 935 on a plain offloaded VLAN. Same box, same VM.

## References and further reading

- [Network processors (NP7, NP7Lite, NP6, NP6XLite, and NP6Lite)](https://docs.fortinet.com/document/fortigate/7.6.6/hardware-acceleration/575471/network-processors-np7-np7lite-np6-np6xlite-and-np6lite) - the offload feature matrix per processor
- [FortiGate 200G and 201G fast path architecture](https://docs.fortinet.com/document/fortigate/7.6.6/hardware-acceleration/793766/fortigate-200g-and-201g-fast-path-architecture) - example of an NP7Lite platform
- [How to enable NP7 hardware offloading for VXLAN over EVPN traffic](https://community.fortinet.com/fortigate-3/technical-tip-how-to-enable-np7-hardware-offloading-for-vxlan-over-evpn-traffic-225075) - the `learn-from-traffic` behavior
- [`vxlan-offload {disable | enable}`](https://docs.fortinet.com/document/fortigate/7.6.2/hardware-acceleration/961613/vxlan-offload-disable-enable) - the per interface offload toggle
- [TCP session over VXLAN stalls after being offloaded to NP7/NP7Lite](https://community.fortinet.com/fortigate-3/technical-tip-tcp-session-over-vxlan-stalls-after-being-accepted-and-offloaded-to-np7-np7lite-225046) - confirmation that NP7Lite does offload VXLAN