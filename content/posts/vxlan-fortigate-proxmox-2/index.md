---
title: 'VXLAN Between a FortiGate and Proxmox, Part 2: EVPN'
date: 2026-06-23T21:14:00Z
author: "Nate"
weight: 1
# aliases: ["/first"]
tags: ["VXLAN", "EVPN", "BGP", "FortiGate", "Proxmox", "SDN", "Homelab"]
categories: ["Networking"]
#series: ["No-Series"]
showToc: true
TocOpen: false
draft: false
hidemeta: false
comments: false
description: "Swapping the static VXLAN peer list for a BGP EVPN control plane across a FortiGate and a three node Proxmox cluster, and every place the two platforms tripped me up by disagreeing on what to state versus what to derive."
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

## Recap, and the problem with where we left off

In [part 1](https://natebent.com/posts/vxlan-fortigate-proxmox-1/) I convinced a FortiGate and a Proxmox cluster to form a working VXLAN segment with nothing more than matching VNI, port, and a static list of peer addresses. That works, but it has a built in tax: every VTEP has to list every other VTEP. Adding a host means editing the peer list on every existing box, and the only way a VTEP learns which MAC lives behind which remote VTEP is to flood unknown traffic everywhere and watch the replies.

At a handful of nodes that is fine. The point where it stops being fine is exactly the problem EVPN solves: a BGP control plane that distributes reachability so you stop hand listing peers and stop flooding to learn. This post is the swap from static VXLAN to EVPN, first on a single node to isolate the new moving part, then out to a three node cluster. The data plane (the actual VXLAN encapsulation on the wire) does not change at all. Only the way VTEPs find each other and learn MACs changes.

The reason this writeup exists is that nearly every wall I hit came from one root cause, and naming it up front will save you the evening it cost me.

## What EVPN actually gives you

Three things, none of which a single node test can demonstrate, which is worth saying because on one node EVPN looks like pure extra work for the same ping:

- **Adding a VTEP becomes a one box operation.** A new node announces itself over BGP and everyone learns it, instead of you editing N peer lists.
- **Flooding mostly stops.** MACs are pre distributed as routes, so the gateway can answer ARP locally instead of flooding it across the link to the other site.
- **The gateway can live everywhere at once.** An anycast gateway puts the same gateway IP and MAC on every VTEP, so a VM is routed by whatever box it sits on and can migrate between nodes without re ARPing. Static VXLAN structurally cannot do this.

> The anycast gateway is the piece that makes live migration actually clean. Normally a gateway is one box, so when a VM moves to another node its first hop still lives back on the original one, and every routed packet has to trombone back across the overlay just to get out. An anycast gateway makes that distance disappear: the same gateway IP and MAC are live on every VTEP, so the first hop is always whatever node the VM is currently sitting on. The VM can land anywhere in the fabric and route locally, with nothing to relearn.
>
> The mechanism is that the guest ARPs its gateway once and caches gateway-IP to gateway-MAC, and that entry never goes stale because the MAC is local on every node. It is the same idea as anycasting a public DNS resolver, except the nearest instance is always the machine you happen to be on. Static VXLAN cannot fake this: in flood and learn a MAC lives behind one remote VTEP at a time, so the same gateway MAC on every node just looks like one MAC frantically moving around, a duplicate rather than a gateway. It takes the EVPN control plane to declare that this MAC is meant to be everywhere at once, which is most of why EVPN earns its place here.

The routes that carry all of this come in types, and three matter here. Type 3 (inclusive multicast) is VTEP auto discovery, the literal replacement for the static peer list. Type 2 (MAC/IP) is MAC distribution, which kills flood and learn. Type 5 (IP prefix) is L3 routing between subnets, which is the anycast and mobility story for later.

## The single node config

Sanitized parameters:

| Item | Value |
| --- | --- |
| BGP ASN (both ends, so iBGP) | 65001 |
| Segment VNI | 4099 |
| Overlay subnet | 172.31.99.0/24 |
| Overlay gateway (anycast) | 172.31.99.1 |
| FortiGate VTEP / underlay IP | 10.0.50.1 |
| Proxmox VTEP / underlay IP | 10.0.50.11 |

### FortiGate

Structurally this is the part 1 VXLAN block with the static `remote-ip` removed, plus an EVPN instance and a BGP stanza. The EVPN instance carries the route distinguisher and route targets. The VXLAN links to it by `evpn-id`. BGP carries the routes.

```
config system evpn
    edit 1
        set rd "10.0.50.1:4099"
        set import-rt "65001:4099"
        set export-rt "65001:4099"
        set arp-suppression enable
    next
end

config system vxlan
    edit "vxlan-evpn"
        set interface "lan"
        set vni 4099
        set evpn-id 1
    next
end

config system interface
    edit "vxlan-evpn"
        set ip 172.31.99.1 255.255.255.0
        set allowaccess ping
    next
end

config router bgp
    set as 65001
    set router-id 10.0.50.1
    set ibgp-multipath enable
    config neighbor
        edit "10.0.50.11"
            set next-hop-self enable
            set next-hop-self-vpnv4 enable
            set soft-reconfiguration enable
            set soft-reconfiguration-evpn enable
            set remote-as 65001
        next
    end
end
```

### Proxmox

FRR does the heavy lifting behind the GUI:

```
apt update && apt install frr frr-pythontools
systemctl enable --now frr
```

Then under Datacenter, SDN: add an EVPN **Controller** (ASN 65001, peers listing both VTEPs), an EVPN **Zone** (with a VRF VXLAN ID, see below), a **VNet** with tag 4099 in that zone, and a **Subnet** on the VNet with gateway 172.31.99.1. Apply.

## The gotchas, in the order I hit them

Each of these is the "stated versus derived" mismatch wearing a different hat.

### The phantom enable command

My first instinct on the FortiGate BGP neighbor was to look for something like `set l2vpn-evpn enable`. It does not exist. That is the FRR and Cisco way of activating the EVPN address family per neighbor, and it is exactly what Proxmox uses under the hood. The FortiGate has no explicit per neighbor EVPN toggle. EVPN advertisement turns on implicitly the moment you have a `config system evpn` instance bound to a VXLAN by `evpn-id`. The neighbor just needs ordinary iBGP settings plus the EVPN friendly knobs above. Proxmox states activation explicitly, the FortiGate derives it from the instance binding. Same outcome, opposite style, and I burned time hunting a keyword that was never there.

### The route target must match your real ASN

This is the big one. I had copied an EVPN instance from an earlier example that used ASN 65000 as a placeholder, but the real box runs 65001. So the FortiGate was importing and exporting `65000:4099`, while Proxmox, deriving its route target as `ASN:VNI`, was using `65001:4099`. The BGP session was Established, EVPN negotiated, the FortiGate even announced its routes, and absolutely nothing imported. The route target is the matching key, and Proxmox derives it from a value you do not type, so any drift between your hand typed FortiGate RT and your actual ASN silently breaks import. Fixing both RTs to `65001:4099` made accepted prefixes start climbing immediately.

### The route distinguisher is per VTEP

In the same block, my RD was set to the Proxmox node's address. The RD only needs to be unique per advertising VTEP, so the FortiGate's RD should be based on **its own** IP, `10.0.50.1:4099`. If two VTEPs advertise the same RD you get route distinction collisions stacked on top of whatever else is wrong. RD is for uniqueness, RT is for matching. They are easy to conflate because they look alike, but they do different jobs.

### Software switch, not an IP on the bare VXLAN interface

When I added a second segment later, I shortcut it by putting an IP directly on the VXLAN interface instead of dropping the VXLAN into a software switch and putting the IP on the switch interface. It did not learn MACs and the gateway did not behave. The working pattern is: VXLAN interface with no IP goes into a `config system switch-interface`, and the IP, `ip-local-learning`, and `arp-suppression` live on that switch interface. A bare VXLAN interface with an IP does not participate in the bridge domain learning the same way, so type 2 routes never populate. The segment looks like it exists but nothing talks.

That `ip-local-learning enable` is not optional, by the way. It is what lets the FortiGate advertise host MAC/IP as type 2 routes, and `arp-suppression` depends on it.

### The tag IS the route target

This was the capstone, and the cleanest illustration of the whole theme. On a later segment, traffic would not pass. Everything was Established. The cause was a one digit slip in the Proxmox VNet tag. Because Proxmox derives the route target straight from the tag, a tag typo is silently a route target mismatch. There is no separate place to get it wrong and no warning, because the tag and the RT are the same number expressed once. The lesson reduces to four words: mind your tags. On the FortiGate you type the RT, on Proxmox you set a tag and the RT falls out of it, and the two only meet if they are the same value.

### One more, the VRF VXLAN ID

The EVPN zone wants a VRF VXLAN ID, which is a separate VNI used for the L3 routing interconnect between your segments, not for any segment itself. In `show evpn vni` you can see it: each segment shows up as type L2, and this one extra VNI shows up as type L3, one per VRF. It just has to be a valid VNI that does not collide with any segment VNI. Pick something memorable and outside your segment range (I used 4000) so the L3 line is instantly recognizable later. The number is arbitrary, the separation is the point.

## Proving it worked

Once the route targets matched, the Proxmox side told the whole story. `show bgp l2vpn evpn` showed the FortiGate's type 3 route imported with the matching RT, which means the FortiGate auto discovered as a VTEP with no static peer list anywhere. That single imported route is the entire point of the exercise. `show evpn vni` showed the segment as an active L2 VNI with one remote VTEP, learned purely from BGP. And the Proxmox side was already advertising a type 2 route for a real VM MAC, so MAC distribution was flowing both ways.

The commands worth banking, FortiGate then Proxmox:

```
get router info bgp neighbors <peer>     # L2VPN EVPN: accepted/announced counts
get l2vpn evpn table
diagnose sys vxlan fdb list <vxlan-name>
```

```
vtysh -c "show bgp l2vpn evpn summary"
vtysh -c "show bgp l2vpn evpn"
vtysh -c "show evpn vni"
```

If the EVPN family is Established but accepted prefixes sit at zero, that is the "stated versus derived" mismatch every time. Read the `RT:` line on the routes and compare it to what you typed.

## Scaling to three nodes

Two deltas, both small, because the model already scales.

First, BGP discovery. Instead of hand defining each Proxmox node as a neighbor, the FortiGate can match a subnet range and drop matching peers into a peer group with shared settings. New hosts in that subnet form sessions automatically, which is the EVPN philosophy applied to the BGP layer itself: stop enumerating peers. All three nodes came up Established this way with no per node neighbor config.

Second, multiple segments over one session. Each additional segment is its own EVPN instance plus its own VXLAN plus its own software switch on the FortiGate, and its own VNet on Proxmox, all riding the **same** BGP session. You never touch BGP to add a segment. That is the payoff restated: segments scale by adding objects, the peering never grows. The mental model that holds it together is that the VNI is the segment, the EVPN instance is that segment's identity in BGP, the route target is the matching key, and one BGP session carries all of them.

The capability that only appears at multiple nodes is the anycast gateway. With the same gateway IP live on every VTEP, a VM can move between nodes and keep using the same gateway because it is local wherever it lands. That is the concrete reason the whole EVPN detour pays for itself, and it is invisible on one node.

## Adding more segments

Once the first segment works, this is where the EVPN setup starts paying off, because a new segment is cheap. It is the same five objects keyed on a new VNI, and the BGP session never grows. Here are three segments instead of one:

| Segment | VNI / Proxmox tag | Route target | Overlay subnet  | Anycast gateway |
| ------- | ----------------- | ------------ | --------------- | --------------- |
| servers | 4099              | 65001:4099   | 172.31.99.0/24  | 172.31.99.1     |
| clients | 4100              | 65001:4100   | 172.31.100.0/24 | 172.31.100.1    |
| iot     | 4101              | 65001:4101   | 172.31.101.0/24 | 172.31.101.1    |

On the FortiGate that is three EVPN instances, three VXLANs, three software switches, and three switch IPs. I have renamed the first segment's objects to sit alongside its siblings, but it is the same VNI 4099 segment from above:

```
config system evpn
    edit 1
        set rd "10.0.50.1:4099"
        set import-rt "65001:4099"
        set export-rt "65001:4099"
        set ip-local-learning enable
        set arp-suppression enable
    next
    edit 2
        set rd "10.0.50.1:4100"
        set import-rt "65001:4100"
        set export-rt "65001:4100"
        set ip-local-learning enable
        set arp-suppression enable
    next
    edit 3
        set rd "10.0.50.1:4101"
        set import-rt "65001:4101"
        set export-rt "65001:4101"
        set ip-local-learning enable
        set arp-suppression enable
    next
end

config system vxlan
    edit "vxlan-srv"
        set interface "lan"
        set vni 4099
        set evpn-id 1
    next
    edit "vxlan-dmz"
        set interface "lan"
        set vni 4100
        set evpn-id 2
    next
    edit "vxlan-iot"
        set interface "lan"
        set vni 4101
        set evpn-id 3
    next
end

config system interface
    edit "vxlan-srv"
        set ip 172.31.99.1 255.255.255.0
        set allowaccess ping
    next
    edit "vxlan-dmz"
        set ip 172.31.100.1 255.255.255.0
        set allowaccess ping
    next
    edit "vxlan-iot"
        set ip 172.31.101.1 255.255.255.0
        set allowaccess ping
    next
end
```

The BGP stanza does not change at all. Same neighbor (or peer group once you are at cluster scale), same single session, now carrying all three segments' routes. That is the entire payoff: you add objects, never peers.

Proxmox is even less work, because the controller and zone already exist. Add two more VNets to the same EVPN zone, tagged 4100 and 4101, give each its own subnet and gateway, and Apply. Three VNets, one zone:

| VNet | Zone      | Tag (VNI) | Subnet          | Gateway      |
| ---- | --------- | --------- | --------------- | ------------ |
| srv  | evpn-zone | 4099      | 172.31.99.0/24  | 172.31.99.1  |
| cli  | evpn-zone | 4100      | 172.31.100.0/24 | 172.31.100.1 |
| iot  | evpn-zone | 4101      | 172.31.101.0/24 | 172.31.101.1 |

Notice that the route target on the FortiGate and the tag on Proxmox are the same number in both tables, the VNI, just typed on one side and derived on the other. Keeping three segments straight is really just keeping one number lined up across both platforms three times. Which, as the next section's failure mode shows, is exactly where a typo hides.

## Where this goes next

Everything above is hand typed, and every segment is the identical five object pattern keyed on one VNI, which is exactly the shape that begs to be looped. The next post is automating it: defining the segment list once as data and letting Terraform render both the FortiGate objects and the Proxmox SDN objects, with the route target and the tag both computed from the same number so the "mind your tags" failure mode becomes structurally impossible.

The order matters though. Build it by hand first, hit these walls, understand every object and how it fails. Then codify the pattern you now actually understand. Automating before you understand it just gives you a black box that deploys broken configs instantly. Having earned the mental model the hard way is the right moment to hand the typing to a tool.

For now, the result stands on its own: a FortiGate and a three node Proxmox cluster running a shared EVPN fabric, multiple stretched segments over a single BGP session, with an anycast gateway across all of it. Not a toy, and not much config once you stop fighting the seam between two platforms that say the same thing in different words.

## References and further reading

- [VXLAN with MP-BGP EVPN (FortiOS Administration Guide)](https://docs.fortinet.com/document/fortigate/8.0.0/administration-guide/52499/vxlan-with-mp-bgp-evpn) - the FortiGate VXLAN object and software switch pattern
- [Proxmox VE: Software-Defined Network](https://pve.proxmox.com/pve-docs/chapter-pvesdn.html) - SDN zones, VNets, and the VXLAN peer list