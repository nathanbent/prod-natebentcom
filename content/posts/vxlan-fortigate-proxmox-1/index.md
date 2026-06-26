---
title: VXLAN Between a FortiGate and Proxmox
date: 2026-06-21T01:00:00Z
author: Nate
weight: 1
tags:
  - VXLAN
  - FortiGate
  - Proxmox
  - SDN
  - Homelab
categories:
  - Networking
series: ["Proxmox Software-Defined Networking"]
showToc: true
TocOpen: false
draft: false
hidemeta: false
comments: false
description: Standing up a single stretched Layer 2 segment between a FortiGate and a Proxmox host using unicast VXLAN, and proving the data plane before adding any complexity.
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

## Why VXLAN

I already run VLANs through my core switch to carve up the lab, and that works well enough. What I wanted to play with was decoupling a segment from the physical switch entirely. VXLAN does that by wrapping the guest's Layer 2 frame inside a UDP packet (destination port 4789 by default) and shipping it to whatever VXLAN Tunnel Endpoint (VTEP) holds the other end. To a VM the bridge looks like any other bridge, but the "wire" underneath it is now an IP path I control instead of a switchport.

The longer term goal is to stretch a single segment across two sites joined by an IPsec tunnel, with the FortiGate acting as the gateway and inspection point for that overlay, all without re-cabling anything or touching switch VLAN config. Before any of that, though, I wanted to answer one small question: will a FortiGate and a Proxmox host actually form a working VXLAN segment between them? This post is just that feasibility test.

The FortiGate is on FortiOS 7.6 branch (7.6.7 as of writing) and the Proxmox host is on the 9.2 branch (9.3.2 as of writing).

## Scoping the test

The one decision I made up front was to keep the IPsec tunnel out of version 1. If I stand both VTEPs up on the same underlay subnet and it fails, I know the problem is the VXLAN interop itself and not the tunnel or some MTU issue out across the internet. Once frames pass locally, moving a peer address to the far side of the tunnel later is a one line change.

So the test is the smallest thing that proves the data plane: one stretched segment, the FortiGate as the gateway, and a Proxmox VM pinging that gateway across VXLAN.

Parameters, all sanitized:

| Item | Value |
| --- | --- |
| VNI | 4099 |
| UDP port | 4789 |
| FortiGate underlay IP (VTEP source) | 10.0.50.1 |
| Proxmox underlay IP (VTEP source) | 10.0.50.11 |
| Overlay subnet (the stretched segment) | 172.31.99.0/24 |
| Overlay gateway (on the FortiGate) | 172.31.99.1 |
| Test VM | 172.31.99.10 |
| Overlay MTU | 1450 |

## FortiGate side

Create the VXLAN interface, drop it into a software switch, and give the switch the gateway IP. The VXLAN object's `interface` is the underlay egress, and that interface's IP becomes the VTEP source.

```FortiOS
config system vxlan
    edit "vxlan-poc"
        set interface "lan"
        set vni 4099
        set dstport 4789
        set remote-ip "10.0.50.11"
    next
end

config system interface
    edit "vxlan-poc"
        set ip 172.31.99.1 255.255.255.0
        set allowaccess ping
        set mtu-override enable
        set mtu 1450
    next
end
```

You do not need a firewall policy just to ping the gateway, since that is local-in traffic governed by `allowaccess`. A policy only comes into play once overlay traffic needs to leave the software switch headed for something else.

## Proxmox side

Under Datacenter, then SDN:

1. Zones, Add, VXLAN. Peers Address List: `10.0.50.11,10.0.50.1` (both VTEPs). MTU `1450`.
2. VNets, Add. Tag `4099`, assigned to that zone.
3. Apply the pending changes from the SDN overview.
4. Attach a test VM's NIC to the new VNet bridge, and inside the guest set `172.31.99.10/24` with gateway `172.31.99.1`.

## Verifying

From the VM, `ping 172.31.99.1`. If that comes back, the interop is proven.

On the FortiGate I watched the forwarding table and the encapsulated packets go by:

```
diagnose sys vxlan fdb list vxlan-poc
diagnose sniffer packet lan 'udp port 4789' 4
```

On Proxmox the same flows show up mirrored:

```
bridge fdb show | grep vxlan
tcpdump -ni <underlay-iface> udp port 4789
```

Once the ping worked, I confirmed large frames survive with `ping -M do -s 1400` from the VM. A same subnet test will happily pass small pings even with the MTU set wrong, so this step matters before you trust the segment. (If you skip it, the MTU mismatch waits to bite you later, much more confusingly, the first time real traffic tries to push full size frames.)

## Adding more hosts

This was the part I had wrong in my head at first. For more VTEPs on the same segment, you do not create additional VXLAN interfaces. One VNI is one segment. You just add every remote VTEP to the single interface's `remote-ip`, which is a list:

```
config system vxlan
    edit "vxlan-poc"
        set interface "lan"
        set vni 4099
        set dstport 4789
        set remote-ip "10.0.50.11" "10.0.50.21" "10.0.50.31"
    next
end
```

This is head-end replication: for any broadcast, unknown unicast, or multicast frame, the FortiGate makes a copy and unicasts one to each listed peer. You only add more VXLAN interfaces when you want more segments (VNI 4100, 4101, and so on). Hosts scale the peer list. Segments scale the interface count.

The bookkeeping detail to watch is that every VTEP lists every other VTEP, and each one leaves itself out. If the FortiGate's VTEP is 10.0.50.1, then it lists .11, .21, .31, while host .11 lists .1, .21, .31, and so on.

Proxmox flips that convention. The SDN VXLAN zone's Peers Address List wants all VTEPs including the local node, and Proxmox works out which one is itself. So every Proxmox node gets the same identical list. That asymmetry, FortiGate excludes self and Proxmox includes self, is the one thing that looks like a mismatch when you are eyeballing both configs side by side.

## Why not multicast

The FortiGate can do multicast mode VXLAN, where each VNI maps to a multicast group and the underlay handles replication, so new VTEPs just join the group instead of being listed. That sounds ideal for a growing cluster, but it is a dead end for this topology, for two reasons.

First, the Proxmox SDN VXLAN plugin is unicast only. The zone takes a peer list and nothing else, so there is no multicast group for a FortiGate in multicast mode to interop with. The moment Proxmox is involved, you are locked to unicast.

Second, even setting Proxmox aside, multicast would not cross the IPsec tunnel to the second site without building multicast over IPsec with PIM, which is far more work than maintaining a peer list. Within a single local subnet multicast can flood without PIM, but that convenience disappears the instant the segment has to reach a remote node.

So for a mixed FortiGate and Proxmox setup spanning two sites, unicast head-end replication is the realistic and fully interoperable path.

## Where this goes next

Unicast head-end replication is the flood and learn model, with every VTEP listing every other VTEP. At single digit scale that is easy to maintain by hand. The point where it starts to hurt is exactly the problem EVPN solves: a BGP control plane distributes MAC and IP reachability, so you stop hand listing peers and stop flooding to learn. The FortiGate speaks MP-BGP EVPN and Proxmox has EVPN zones via FRR, so both ends interop there too.

Proving the data plane first with static unicast is not wasted effort, though. When I do move to EVPN, any breakage is isolated to the control plane (BGP sessions, route targets, the EVPN route types) rather than the VXLAN encapsulation itself. Debugging one layer at a time beats debugging both at once.

That is the next post. For now, the feasibility question is answered: a FortiGate and a Proxmox host will form a working VXLAN segment with nothing more than matching VNI, port, and peer addresses.

## References and further reading

- [VXLAN with MP-BGP EVPN (FortiOS Administration Guide)](https://docs.fortinet.com/document/fortigate/8.0.0/administration-guide/52499/vxlan-with-mp-bgp-evpn) - the FortiGate VXLAN object and software switch pattern
- [Proxmox VE: Software-Defined Network](https://pve.proxmox.com/pve-docs/chapter-pvesdn.html) - SDN zones, VNets, and the VXLAN peer list
- [RFC 7348 - Virtual eXtensible Local Area Network (VXLAN)](https://datatracker.ietf.org/doc/html/rfc7348) - the encapsulation itself, if you want the wire format
