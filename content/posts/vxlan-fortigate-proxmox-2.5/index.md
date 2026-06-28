---
title: "VXLAN Between a FortiGate and Proxmox, Part 2.5: A Security Aside"
date: 2026-06-25T01:00:00Z
author: Nate
weight: 1
tags:
  - VXLAN
  - EVPN
  - BGP
  - FortiGate
  - Proxmox
  - Security
  - Microsegmentation
  - Homelab
categories:
  - Networking
  - Security
series: ["Proxmox SDN"]
showToc: true
TocOpen: false
draft: false
hidemeta: false
comments: false
description: What this overlay actually buys you on the security side, beyond writing firewall policies, plus an honest list of what it does not buy you, and an FAQ on VXLAN and EVPN versus plain VLANs.
summary: What this overlay actually buys you on the security side, beyond writing firewall policies, plus an honest list of what it does not buy you, and an FAQ on VXLAN and EVPN versus plain VLANs.
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

## The thing that actually makes this interesting

The fun of this setup was never VXLAN for its own sake. It is that the FortiGate is the **only** router for every overlay segment, which means traffic I normally cannot see gets inspected like everything else. That sentence is the whole security story, so it is worth unpacking before anything else.

A quick disclaimer up front, because it is the most common misconception: VXLAN is not a security feature. It does not encrypt anything, it does not authenticate anything, and an overlay is not inherently safer than a VLAN. What the overlay gives you is an **architecture** in which certain strong patterns become cheap and natural. The security comes from the patterns, not the encapsulation. The rest of this post is those patterns, then an honest list of what the overlay does not do for you.

## The core win: the firewall is the only road

In a traditional setup, the moment a Layer 3 switch does inter VLAN routing, that east-west traffic never touches your firewall. Two VLANs that share a routing switch can talk all day and your NGFW sees none of it.

In this overlay, the anycast gateway for every segment lives on the FortiGate. There is no other router. So any traffic between two overlay segments is, by construction, forced across the firewall to be routed. That is not a policy you remember to write, it is a property of the topology. East-west becomes north-south, and everything the FortiGate does to north-south traffic now applies to traffic that used to be invisible.

Concretely, that means the full NGFW stack runs on inter segment flows: IPS, application control, antivirus, web filtering, and SSL inspection where you choose to enable it. The overlay's software switch interface is just an interface to the FortiGate, so security profiles attach to it exactly like a physical port. Deep packet inspection on east-west traffic, with no span ports and no extra hardware, is the headline benefit.

## Cheap segments means real microsegmentation

The second win is economic. Adding a segment here is a new VNI, a new EVPN instance, a new software switch, and a VNet on the Proxmox side. No physical recabling, no switch VLAN plumbing, no touching the BGP peering. The marginal cost of one more segment is near zero.

When segments are that cheap, you stop rationing them. Instead of a handful of broad VLANs because each one was annoying to stand up, you can carve fine grained zones: one per application tier, one per trust level, a dedicated quarantine segment, a segment that only ever talks to the gateway. The overlay does not make you microsegment, but it removes the friction that usually stops people from bothering. Granular segmentation that is forced through an inspecting gateway is a genuinely strong posture, and it is the thing this setup makes practical rather than theoretical.

## Controls inside a single segment

Forcing inter segment traffic through the firewall handles east-west between zones. But hosts inside one segment still share a broadcast domain and can talk directly. A few options tighten that:

- **Port isolation.** Proxmox VNets have an isolate ports flag that prevents guests on the same segment from talking to each other directly, allowing them only to reach the bridge, which is the gateway. That is private VLAN style behavior, and combined with the next item it forces even same segment traffic up to the firewall.
- **A default deny segment firewall.** The VNet level firewall can drop by default and permit only traffic to and from the gateway. With that in place, two VMs on the same segment cannot reach each other without their traffic hairpinning through the FortiGate, where policy and inspection apply. You have effectively pushed the inspection boundary down to the individual host.
- **ARP suppression.** This was already enabled for control plane reasons, and it has a pleasant side effect. Because the gateway answers ARP from what the control plane learned rather than from flood and learn, there is less broadcast noise and a smaller surface for ARP based shenanigans within the segment.

## Visibility, not just enforcement

Enforcement gets the attention, but the logging is half the value. Because every inter segment session is a FortiGate session, it shows up in FortiView and exports to your log analyzer like any other flow. Inter VLAN routing on a switch gives you no session record at all. Here you get per session east-west logging for free, which is the difference between "I think those zones are isolated" and "I can show you every flow that crossed between them." For incident response and for simply understanding what your lab actually talks to, that record is worth as much as the blocking.

A nice operational extra: because segment membership is defined in software, by which VNet a guest's interface attaches to, you can build a dedicated isolation segment and move a suspect VM's interface into it, or drive that with dynamic policy. Quarantine becomes a software action rather than a trip to a switch.

## The honest part: what the overlay does not give you

Every pattern above is real, but so are these, and skipping them would be malpractice.

**No data plane encryption.** VXLAN wraps frames in UDP, it does not protect them. Within a site, encapsulated traffic on the underlay is effectively cleartext to anyone who can see it. The cross-site stretch in this design is private only because it rides an IPsec tunnel underneath, not because of anything VXLAN does. If you need confidentiality on a path, that has to come from the underlay.

**The underlay is now a high value target.** All your segments collapse onto one transport network carrying the VXLAN traffic. Anyone with a foothold on that underlay can potentially observe a lot, and because VXLAN has no authentication, a host that knows a VNI and the destination port can attempt to inject frames into a segment. Treat the transport VLAN as sensitive. Do not put untrusted hosts on it, and lock down what can reach it.

**The hypervisor became a segmentation boundary.** With VLANs, the switch enforces which port is in which VLAN. Here, the Proxmox host decides which guest sits on which segment, and the FortiGate trusts the VNI it receives. That means a compromised hypervisor can bridge segments that are supposed to be separate. The host, its SDN config, and its API access are now security relevant in a way a dumb access switch never was. Scope the API token you automate with, and patch the hosts like the trust anchors they have become.

**A route target typo can merge segments that should be isolated.** This is the one that should make you sit up. In part 2, a mismatched route target silently broke connectivity. Flip that: if two segments accidentally share a route target, EVPN will happily import each other's routes and **merge two broadcast domains that were supposed to be isolated**. The same mechanic that failed closed when it mismatched fails open when it overlaps. So "mind your tags" is not only a connectivity rule, it is an isolation control. Your route target scheme is part of your security boundary, and it deserves the same review you would give a firewall rule. This is the strongest argument for generating the route targets from a single source of truth rather than typing them, which is exactly where the automation post is headed.

## A hardening checklist

Pulling the defensive measures into one place:

- **Authenticate every BGP session, including the peer group.** It is easy to set passwords on your obvious tunnel neighbors and forget the peer group that your hypervisors join. An unauthenticated EVPN session is a path for a rogue peer to inject routes. Put a password on the group too.
- **Cap routes per peer.** A maximum EVPN prefix limit on each neighbor protects you from a misbehaving or compromised VTEP flooding the control plane with MAC routes. It is a cheap denial of service guardrail.
- **Scope BGP to the underlay only.** Match peers from the transport subnet and nowhere else, so the control plane is not reachable from segments it serves.
- **Keep learn from traffic disabled.** With both ends speaking EVPN, leave the data plane learning off so the control plane is the only source of truth. That removes a data plane injection path.
- **Lean on EVPN's own anti spoofing.** EVPN tracks MAC mobility with sequence numbers and can detect a duplicate MAC appearing behind two VTEPs, which is exactly the signature of spoofing or a misconfiguration. Know it is there and watch for the alerts.
- **Protect the underlay and the hypervisors** as the trust anchors they now are, and treat the route target scheme as a reviewed isolation control.

## FAQ: VXLAN and EVPN versus plain VLANs

**Is this more secure than VLANs?**
Not by itself. The security comes from forcing traffic through an inspecting gateway and from cheap, granular segmentation, both of which a firewall on a stick with VLANs can also do. The overlay makes the many segments, all inspected, physical switch independent pattern cheap and stretchable. That is the difference, not the encapsulation.

**Does VXLAN encrypt my traffic?**
No. Zero data plane encryption. Cross-site privacy in this design comes from the IPsec tunnel underneath. Same site, it is cleartext encapsulated.

**Can someone sniff or join my VXLAN?**
On the underlay, potentially yes, because VXLAN has no authentication. The fix is to protect the transport network and authenticate the EVPN control plane. EVPN means a rogue static endpoint will not receive routes, but the data plane itself is not something you can authenticate.

**Do I still need VLANs?**
Almost certainly. The underlay is still physical ports and VLANs. The overlay rides on top of it. They are complementary, not a choice between the two.

**When should I just use a VLAN instead?**
When a segment lives on one switch or one site and does not need to stretch, and you are not chasing the firewall as only router pattern, a VLAN is simpler and has less to break. Do not put everything in an overlay. Reach for VXLAN where it buys something specific: stretching Layer 2 across sites, forcing all routing through the firewall, frequent segment churn, or workload mobility.

**Is EVPN more secure than static VXLAN?**
It is more controllable. EVPN adds a control plane you can authenticate, filter, and rate limit, and it floods far less, which shrinks the broadcast surface. But that same control plane is new attack surface: a compromised host can advertise routes, so you accept it with authentication and prefix limits. Net, EVPN gives you more security knobs and more to secure. For a static two endpoint test, plain VXLAN is fine. For anything that grows, EVPN's controllability is worth the added surface.

**What about the 4094 VLAN limit versus 16 million VNIs?**
True, and almost never the reason a homelab reaches for VXLAN. The 24 bit VNI space matters at cloud scale. For most of us the real reasons are decoupling from the physical switch and stretching Layer 2 over a routed underlay, not running out of VLAN IDs.

## The takeaway

The overlay did not hand me security. It handed me an architecture where the strong patterns are the easy ones: the firewall is the only router so east-west gets inspected, segments are cheap so microsegmentation is realistic, and every cross zone flow is logged because it is a firewall session. In exchange I picked up new responsibilities, an unauthenticated data plane to wrap, an underlay to guard, hypervisors that are now trust boundaries, and a route target scheme that is quietly part of my isolation model. Worth it, as long as you go in knowing which half of the deal is the work.
