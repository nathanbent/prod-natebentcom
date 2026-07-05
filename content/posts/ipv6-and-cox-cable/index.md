---
title: "IPv6 at Home: Prefix Delegation with Cox, FortiGate, and an Aging Brocade Core"
date: 2024-12-15T01:00:00Z
author: "Nate"
# weight: 1
# aliases: ["/first"]
tags: ["ipv6", "networking", "fortigate", "brocade", "homelab"]
categories: ["HomeLab"]
#series: ["No-Series"]
showToc: true
TocOpen: false
draft: true
hidemeta: false
comments: false
description: "Desc. Text"
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
    thumb: true
    hiddenInSingle: true   # never show it stacked atop the article
    hiddenInList: false    # but do show it as the list thumbnail
editPost:
    disaled: true
    URL: "https://github.com/<path_to_repo>/content"
    Text: "Suggest Changes" # edit text
    appendFilePath: true # to append file path to Edit link
---

Cox gets a lot of criticism, and most of it's earned. But there's one thing they do right that a lot of ISPs still don't: they hand out a full **/56 IPv6 prefix** via DHCPv6 Prefix Delegation (DHCPv6-PD). That's 256 individual /64 subnets, which is more than enough for a homelab, however sprawling it gets. This post walks through how I'm using that /56 today, why part of my network still requires manual intervention, and what I want to fix down the road.

If you've never worked with IPv6 prefix delegation before, this should also work as a decent introduction to the concept.

## A Very Quick Primer on IPv6
Here's a standalone primer you can slot in wherever it fits:

---

IPv4 gives us roughly 4.3 billion addresses, a number that felt inexhaustible in 1981 and turned out to be laughably small once every phone, laptop, doorbell, and light bulb wanted one. We've spent the last two decades patching around that shortage with NAT — Network Address Translation — which lets dozens or thousands of devices share a single public IP by having a router quietly rewrite packet headers as traffic passes through. It works, but it comes with a cost: NAT breaks the original end-to-end model of the internet, where every device could reach every other device directly. Anything that needs true bidirectional connectivity (VoIP, peer-to-peer apps, some VPN configurations) ends up needing workarounds like STUN, TURN, or port forwarding just to punch through.

IPv6 was designed specifically to make that shortage — and the NAT workaround — unnecessary. Instead of 32-bit addresses, IPv6 uses 128 bits, which sounds like a modest upgrade until you realize what it means numerically: roughly 340 undecillion addresses, or enough to assign a unique address to every grain of sand on Earth several times over. The practical effect is that NAT stops being a requirement. Every device on your network can have its own globally routable address and reach the internet directly, no translation layer involved.

That single change ripples into how IPv6 networks are actually built. Rather than your ISP handing you one address to share, they hand you a **prefix** — a block of addresses you subnet yourself. Cox, for example, delegates a /56 to my FortiGate, which is 256 individual /64 networks to divide up however I like. This is done through DHCPv6 Prefix Delegation (DHCPv6-PD), where your router requests a prefix and the ISP's infrastructure hands one back, the same way DHCP hands out a single IPv4 lease, just at a much larger scale.

Address configuration also works differently day to day. IPv4 devices almost universally get their address via DHCP. IPv6 supports that too, but it also supports SLAAC (Stateless Address Autoconfiguration), where a device can construct its own address just by listening to router advertisements on the local network and combining the announced prefix with its own interface identifier — no DHCP server required at all. Two flags control how much a device relies on this: the "Managed" flag tells hosts to go get full configuration from DHCPv6, and the "Other" flag tells hosts to keep using SLAAC for addressing but still pull other details (like DNS servers) from DHCPv6. Networks often run both simultaneously and let the flags sort out the division of labor.

The /64 boundary is another IPv6-specific convention worth internalizing. In IPv4 you might run a /29 for a tiny point-to-point link or a /22 for a large user segment, sizing subnets tightly around however many hosts you actually have. IPv6 throws that scarcity mindset out entirely — /64 is the standard subnet size almost everywhere, regardless of whether that segment will ever hold more than a handful of devices, because SLAAC's addressing math is built around a 64-bit network portion and a 64-bit host portion. A single /64 contains more addresses than the entire IPv4 address space combined, so there's no meaningful reason to subnet it any tighter.

None of this is a wholesale replacement of IPv4 thinking, though — a lot carries over directly. Routing protocols like OSPF still work the same way conceptually, just with an IPv6-specific version (OSPFv3) running alongside the IPv4 one. VLANs, trunking, and switch fundamentals don't change at all. The real shift is philosophical: IPv4 network design is an exercise in conserving a scarce resource, while IPv6 design assumes abundance and instead focuses on keeping addressing logically organized, since running out of space is no longer the constraint you're solving for.


## The Quick Version of DHCPv6-PD

If you're coming from an IPv4 mindset, prefix delegation feels backwards at first. With IPv4, your router gets **one address** from your ISP and then NATs everything behind it. With IPv6, there's no NAT in the intended design — every device is supposed to get its own globally routable address. To make that possible, your ISP doesn't hand you a single address; it hands you a **block of addresses** (a prefix) that you're free to subnet however you like.

A DHCPv6-PD exchange has a few pieces worth knowing:

- **PD client** — the device that requests a prefix from upstream. My FortiGate is the client toward Cox.
- **PD server** — the device delegating prefixes to something downstream. My FortiGate also acts as a PD server internally, though only in a limited sense (more below).
- **IAID (Identity Association ID)** — an identifier tied to a specific delegation request. If you have multiple WAN interfaces or want multiple independent delegations, the IAID is how the client and server keep them straight.
- **Prefix hint** — the client can ask for a specific size, like `::/56`. The server isn't obligated to honor it, but Cox does.

## My Setup

**WAN side (Cox-facing):**

```
config system interface
    edit "WAN-LACP"
        set mode dhcp
        set type aggregate
        set member "wan2" "wan1"
        set role wan
        config ipv6
            set ip6-mode dhcp
            set dhcp6-prefix-delegation enable
            config dhcp6-iapd-list
                edit 46
                next
                edit 1
                    set prefix-hint ::/56
                next
            end
        end
    next
end
```

The FortiGate's WAN is a 2-member LACP aggregate (`wan1`, `wan2`) sitting on Cox's DOCSIS handoff. `dhcp6-prefix-delegation enable` turns on the PD client behavior, and the `prefix-hint ::/56` tells Cox's DHCPv6 server what size I'd like. Cox honors it every time.

**LAN side (internal transit toward the Brocade):**

```
config system interface
    edit "LAN-LACP"
        set ip 192.168.255.254 255.255.255.252
        set type aggregate
        set member "internal1" "internal2" "internal3" "internal4" "internal5"
        config ipv6
            set ip6-mode delegated
            set ip6-send-adv enable
            set ip6-manage-flag enable
            set ip6-other-flag enable
            set ip6-delegated-prefix-iaid 1
            set ip6-upstream-interface "WAN-LACP"
            set ip6-subnet ::1/64
        end
    next
end
```

This is the interesting part. `ip6-mode delegated` means this interface doesn't get a static IPv6 address — instead it carves an address out of whatever prefix was delegated on `WAN-LACP` (referenced by `ip6-delegated-prefix-iaid 1`, matching the IAID from the WAN config). `ip6-subnet ::1/64` says "take the first /64 out of my delegation and use `::1` as this interface's address within it." That resolves to something like `2001:db8:1234:b200::1/64` given my current /56.

The `ip6-manage-flag` and `ip6-other-flag` settings control SLAAC behavior on this segment — they tell downstream routers "don't just self-assign an address, go ask a DHCPv6 server for configuration too." This matters because this interface isn't really serving end hosts; it's my OSPF transit link to the Brocade core.

**Routing glue (OSPFv3):**

```
config router ospf6
    set default-information-originate always
    config area
        edit 0.0.0.0
        next
    end
    config ospf6-interface
        edit "LAN-LACP"
            set interface "LAN-LACP"
            set priority 255
        next
    end
    config redistribute "connected"
        set status enable
    end
end
```

`default-information-originate always` means the FortiGate injects an IPv6 default route into OSPFv3 regardless of whether it technically has one of its own — useful since I want to guarantee every internal router has a path out, even during a rekey. `redistribute connected` pushes locally-attached subnets (including any DMZ IPv6 segments living directly on the FortiGate) into OSPF as well.

## The Brocade: Where the Automation Stops

My core switch is a Brocade ICX 6610 — old, but stacked with 10/40GbE that I'm still using almost entirely. It runs OSPFv3 just fine and happily learns routes and the default route from the FortiGate. What it **can't** do is act as a DHCPv6-PD client. There's no mechanism for it to say "hey FortiGate, delegate me a sub-block and I'll configure my own interfaces from it."

That means every VLAN interface (`ve X`) that needs a real IPv6 address has one **manually assigned**, like this:

```
interface ve 665
 ipv6 address 2001:db8:1234:b200::2/64
 ipv6 ospf area 0.0.0.0
 ipv6 ospf active
!
interface ve 2
 ipv6 address 2001:db8:1234:b202::1/64
!
interface ve 20
 ipv6 address 2001:db8:1234:b214::1/64
!
```

Each of these was carved out of the /56 using an [IPv6 subnet calculator](https://www.site24x7.com/tools/ipv6-subnetcalculator.html), keeping the last hex digit of the third block roughly aligned with the equivalent IPv4 VLAN ID for my own sanity (VLAN 2 → `...b202`, VLAN 20 → `...b214`, etc). It's a little goofy, but it means I can eyeball a `ve` interface's IPv6 address and immediately know which VLAN it belongs to.

**The problem:** I don't get a static /56 from Cox. Every time I swap FortiGates — which happens periodically since I source them from decommissioned units at work — I get a brand new one. IPv4 doesn't care; DHCP just hands out a new address and life goes on. IPv6 means going back into the Brocade and manually updating every single `ve` interface with the new prefix.

## What I've Done About It (So Far)

Since the subnetting logic is fixed — same offsets, same structure, every time — I wrote a small Python script that takes my new first `/64` (which becomes "subnet #1" by convention) and calculates any subnet index from there, the same way the site24x7 calculator does, but scriptable and instant. It turns a "go re-derive eight subnets by hand" task into a few seconds of copy-paste. It doesn't touch the Brocade directly yet, but it removes the annoying part of the manual process.

## What I Actually Want: Full Automation

The real fix is a script that:

1. Pulls the current delegated /56 from the FortiGate (via its REST API — `GET /api/v2/monitor/system/interface` or similar, filtered for `LAN-LACP`)
2. Recalculates every `ve` interface's expected IPv6 address using the same fixed offsets I already use
3. Diffs that against the Brocade's current running config
4. Pushes the delta via SSH (Paramiko + a scripted CLI session, since the ICX doesn't have a modern API)

This is entirely doable — the FortiGate API is well documented and the Brocade will accept scripted SSH config changes without complaint. It's just a project I haven't sat down and built yet.

## The Longer-Term Fix

The actual root cause is that the Brocade 6610, however capable it still is for raw switching throughput, is old enough that it predates widespread DHCPv6-PD client support on this class of hardware. Modern L3 switches and routers (Arista, Juniper EX, even MikroTik) support acting as a PD client, which would let this whole process happen automatically end to end — Cox delegates to the FortiGate, the FortiGate re-delegates or forwards it, and the Brocade (or whatever replaces it) reconfigures itself.

That's a "someday" project. Replacing a switch with this much 10/40GbE density in active use isn't a small undertaking, and the 6610 has been rock solid otherwise. For now, scripting the delta is the pragmatic path.

## Useful Debug Commands

A few commands I lean on when troubleshooting this setup:

**FortiGate:**
```
diagnose ipv6 address list
get router info6 ospf neighbor
get router info6 routing-table ospf
diagnose debug application dhcp6c -1
diagnose debug enable
```

**Brocade ICX:**
```
show ipv6 interface brief
show ipv6 route
show ipv6 ospf neighbor
show ipv6 ospf database
```

The FortiGate's `dhcp6c` debug output is particularly useful right after a FortiGate swap — it shows the actual PD exchange with Cox in real time, including the prefix that comes back, which saves you from guessing whether the delay is DHCPv6-PD related or an OSPF adjacency problem further downstream.

## Closing Thoughts

None of this is exotic — DHCPv6-PD is a mature, well-supported standard, and the FortiGate side of my setup handles it without any fuss. The friction is entirely a hardware-generation problem on the Brocade side. If you're building something similar and shopping for core switching gear, "DHCPv6-PD client support" is worth putting on your checklist early, because retrofitting automation around a switch that can't do it is a lot more work than just picking one that can.
