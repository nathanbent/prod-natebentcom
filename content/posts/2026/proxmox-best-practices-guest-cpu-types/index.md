---
title: "Proxmox Best Practices - Guest CPU Types"
date: 2026-05-04T01:00:00Z
author: "Nate"
# weight: 1
# aliases: ["/first"]
tags: ["Proxmox", "Virtualization", "KVM", "Homelab"]
categories: ["Proxmox"]
series: ["Proxmox Best Practices"]
series_order: 1
showToc: true
TocOpen: false
draft: false
hidemeta: false
comments: false
description: "How I pick a Proxmox VM CPU type: host versus the x86-64-vN virtual types, the Spectre and Meltdown flags those types quietly leave off, and why host is usually the wrong default on Windows."
summary: "How I pick a Proxmox VM CPU type: host versus the x86-64-vN virtual types, the Spectre and Meltdown flags those types quietly leave off, and why host is usually the wrong default on Windows."
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

Every time I build a VM on the Proxmox cluster I hit the same menu, and for a while I overthought it. The Processor dropdown offers `host`, a stack of `x86-64-vN` types, a long list of named models like `Broadwell-noTSX-IBRS` or `EPYC-Milan`, and whatever custom models I have defined. Most guides frame the choice as stability versus performance, and that framing is exactly the part I had wrong in my head at first.

The lever is not stability versus performance. It is portability versus CPU feature exposure.

Feature exposure is how many host CPU flags (AVX2, AES-NI, AVX-512, and so on) the guest can see and use. More flags means feature-heavy code runs faster, and `host` hands the guest everything the physical CPU has. Portability is whether a running VM can live-migrate to another node. A VM that advertises a flag to its guest and then lands on a host without that flag does not degrade gracefully: the QEMU process stops. The fixed virtual types exist to advertise a stable, lowest-common feature set so the VM boots and migrates identically everywhere.

So a VM set to `host` is not less stable on its home node. It is just non-portable. That is the real cost, and once I framed it that way the rest fell out of one question per VM.

> [!INSIGHT]
> The Proxmox CPU type menu is not a stability versus performance slider. It is a portability versus feature-exposure trade. `host` gives the guest every flag the physical CPU has and gives up live migration. The `x86-64-vN` types give up flags to stay migratable.

## The one question

Does this VM need to move between nodes, or does it need to squeeze the host CPU? Everything below is downstream of that. The short version of how I answer it:

Single node, or a VM already pinned to one node by PCI passthrough or hard affinity, gets `host`. Migration is already off the table, so I take the free flags. That holds for Linux; Windows is a different story, which is the whole reason this post exists.

A VM that needs cluster-wide live migration gets the lowest CPU generation common to every node, either as an `x86-64-vN` level or a named model of that generation.

A migration domain with mixed Intel and AMD forces the vendor-neutral `x86-64-vN` types. Named vendor models will not cross vendors, and Proxmox is explicit that live migration between Intel and AMD hosts has no guarantee of working at all.

## The options

### host

Exposes the exact flags of the physical CPU. Maximum feature exposure, best Linux performance for anything that uses modern instruction sets. The cost is that it breaks live migration to any node with a different CPU or microcode: if a required flag is missing on the target, QEMU aborts. I use it for single-node hosts, a genuinely homogeneous cluster (identical CPU and microcode on every node), or a VM that is already unmovable because of passthrough.

### The x86-64-vN virtual types

Vendor-neutral, defined jointly by AMD, Intel, Red Hat, and SUSE in 2020, and they work on both Intel and AMD hosts. This is the migration-safe family.

| Type | Compatible with (min CPU) | Flags added over the previous level |
|------|---------------------------|-------------------------------------|
| `kvm64` (x86-64-v1) | Intel Pentium 4+, AMD Phenom+ | baseline (Pentium 4 level, poor perf) |
| `x86-64-v2` | Intel Nehalem+, AMD Opteron G3+ | cx16, lahf-lm, popcnt, pni, sse4.1, sse4.2, ssse3 |
| `x86-64-v2-AES` | Intel Westmere+, AMD Opteron G4+ | aes |
| `x86-64-v3` | Intel Haswell+, AMD EPYC (Naples)+ | avx, avx2, bmi1, bmi2, f16c, fma, movbe, xsave |
| `x86-64-v4` | Intel Skylake+, AMD EPYC Genoa (v4)+ | avx512f, avx512bw, avx512cd, avx512dq, avx512vl |

Two things about that table are worth holding onto. The backend and CLI default is `kvm64`, but the GUI default for a new VM is `x86-64-v2-AES`. That matters because a VM created from a script or the CLI can quietly land on `kvm64` while one clicked together in the web UI gets `v2-AES`. And do not treat `kvm64` as the safe default: some modern distros, CentOS and RHEL 9 for example, are built for `x86-64-v2` as a minimum and will not boot on `kvm64`. The sane floor is `v2-AES`. For migration, pick the highest level your weakest node supports.

### Named vendor models

Specific microarchitectures, more granular than the `vN` levels, and a named model may expose a flag a `vN` level does not. They are vendor-locked: an Intel model will not migrate to an AMD host, or the reverse. Models with an `-IBRS` or `-IBPB` suffix already carry the relevant Spectre v2 control flag. I reach for these on a same-vendor cluster where I want a specific generation's flags and still want migration, choosing the lowest generation present in the cluster.

### Custom models

You can define a reusable base plus flag toggles under Datacenter, Custom CPU Models (backed by `/etc/pve/virtual-guest/cpu-models.conf`), then reference it from a VM as `custom-<name>`:

```
cpu-model: avx
    flags +avx;+avx2
    phys-bits host
    hidden 0
    hv-vendor-id proxmox
    reported-model kvm64
```

`reported-model` controls what the guest thinks it is running on. `phys-bits host` matches the host's address bits but breaks migration to hosts with a different value. Access is ACL-gated per model at `/mapping/cpu/<name>`: `Mapping.Use` is required to assign a model to a VM, and that check is enforced on create, update, and clone, so someone who can clone a VM that uses a custom model still needs `Mapping.Use` on it. These earn their place when you want one documented, cluster-wide profile reused across many VMs.

## The security dimension nobody puts on the menu

Here is the part that is easy to miss. The `x86-64-vN` virtual types do not enable the Spectre and Meltdown mitigation flags by default. `host` inherits whatever the physical CPU exposes, so the migration-safe path silently gives those up unless you add them back. Two things have to be true for any of these flags to help: the host CPU has to support and propagate the feature (current microcode), and the guest OS has to be patched to use it.

For Intel guests: `pcid` reduces the Meltdown and KPTI performance hit, it is cheap, so add it. `spec-ctrl` covers Spectre v1 and v2 where retpolines are not enough; it is included in `-IBRS` models and needs adding explicitly otherwise. `ssbd` is the Spectre v4 fix, never included by default, always explicit.

For AMD guests: `ibpb` covers Spectre v1 and v2, included in `-IBPB` models, add otherwise. `amd-ssbd` is the Spectre v4 fix with higher performance than `virt-ssbd`. Expose `virt-ssbd` as well, because some kernels only understand that one, and it has to be set explicitly even with `host` since it is a virtual flag that does not exist on physical AMD CPUs. `amd-no-ssb` tells newer silicon it is not vulnerable to v4, and it is mutually exclusive with the two `ssbd` flags.

To see what the host actually exposes:

```
for f in /sys/devices/system/cpu/vulnerabilities/*; do echo "${f##*/} -" $(cat "$f"); done
grep ' pcid ' /proc/cpuinfo
```

A migration-safe Intel base with the mitigations added back looks like this:

```
cpu: x86-64-v3,flags=+pcid;+spec-ctrl;+ssbd
```

## Why Windows is different

On Linux, `host` does what you expect: more flags, more performance, no penalty. On Windows it frequently makes things slower, and for a while that made no sense to me. Native has to beat emulated, right? Not here.

When the CPU type is `host`, QEMU passes the physical CPU's security flags into the guest, including `md_clear` (the MDS mitigation) and `flush_l1d` (the L1TF mitigation). Windows sees those flags and switches on its own in-guest mitigations, the VERW and L1D flushes on transitions. The result is a large jump in memory read latency and, in bad cases, a guest that visibly stutters with the vCPUs pegged. The `x86-64-vN` types and most named models do not pass `md_clear` or `flush_l1d`, so Windows never turns those mitigations on and the penalty never appears. This is a community finding rather than official CPU-type documentation, but it is well corroborated on the forums and it matches what I have seen.

There is a second effect stacked on top. With `host`, Windows can decide it is running on real hardware and enable virtualization-based security, which pulls in nested virtualization inside the VM, which hurts again. `msinfo32` will tell you whether Windows thinks it is virtualized and whether VBS is on.

> [!CAUTION]
> On Windows guests, `host` is often slower than `x86-64-v3`, not faster, and it fails silently: no error, just high CPU and sluggish memory latency. Passing `md_clear` and `flush_l1d` makes Windows enable its own in-guest MDS and L1TF mitigations. The `x86-64-vN` types leave those flags off, so the penalty never triggers.

Net effect: on Windows, `x86-64-v3` is frequently both faster and migratable than `host`. Older Windows Server barely touches the newer instruction extensions anyway, so the flags `host` adds rarely pay for the mitigation cost they trigger. That is why I default Windows guests to `x86-64-v3`, with `x86-64-v2-AES` as the conservative fallback for older or mixed-low clusters.

One caveat I want to be careful about, because it gets oversold:

> [!WARNING]
> "Switching off host loses no security, the mitigations still run at the hypervisor level" is only half true. Cross-VM and host-to-guest isolation are handled by the Proxmox kernel regardless of guest CPU type. What you actually give up is the guest's own intra-VM MDS and L1TF protection: process-to-process and kernel-to-user side-channel hardening inside that Windows VM. Fine for a single-tenant VM running trusted code. Weigh it deliberately for a multi-user RDS host or anything running untrusted workloads.

It is also worth being honest that the `vN` types get their safety purely by not exposing the flags, so `v3` is not inherently more secure than `host` with `md_clear` stripped. It does the same thing by omission.

Applying a CPU type change needs a full shutdown and start. A reboot from inside Windows is not enough to renegotiate the vCPU. I confirm the change with `Get-SpeculationControlSettings`: on `host` the mitigations report active, on `v3` they report inactive because the flags are absent.

### When host is genuinely required

Reach for `host`, or explicit flag exposure, when a feature demands it, not for raw speed:

Nested virtualization inside the guest (WSL2, Hyper-V, Docker Desktop, Android emulators, or Windows VBS and HVCI that you actually want on). GPU or PCI passthrough, and anti-cheat that inspects CPU identity. Software that needs an instruction set your `vN` floor does not carry.

In those cases the VM is usually pinned already, since passthrough kills migration, so `host` costs nothing extra on the portability axis. On Windows, accept that the mitigation penalty rides along; if VBS is the goal, that penalty is the feature. A couple of Windows-on-recent-Intel specifics live here: if Hyper-V or VBS hangs at boot under `host` or `max`, `level=30` is the known workaround (x86_64 only, silently ignored elsewhere). And `cet-ss` and `cet-ibt` are disabled by default for Windows 11 machine types because they currently break boot for guests with VBS, so only re-enable them per VM if a workload needs them.

## The supporting knobs

Sockets times cores is total vCPUs, and the split is mostly irrelevant for performance. Set sockets for software licensing if that matters, otherwise one socket, or match NUMA nodes. Overcommit is safe: total vCPUs across all VMs can exceed physical cores, and the host schedules them like any multithreaded load. Proxmox will not let a single VM exceed the physical core count.

On multi-socket hosts, enable NUMA so guest memory and vCPUs land local to a socket instead of spread across the memory bus. It is also required to hot-plug cores or RAM. When enabled, set the VM's socket count to the number of host NUMA nodes. Check with `numactl --hardware | grep available`, where more than one node means the host is NUMA.

For resource control there are three knobs. `cpulimit` is a hard cap on host CPU time in whole-core units (1.0 is one core, 4.0 is four); set it equal to the total core count to guarantee a VM never exceeds its vCPUs, since peripheral and IO threads can otherwise push it slightly over. `cpuunits` is relative scheduler weight, default 100 (or 1024 on legacy cgroup v1); a VM at 200 gets twice the CPU bandwidth of one at 100 under contention, so it is priority, not a cap. `affinity` pins vCPUs to specific host cores in `taskset` list format, for example `0-1,8-11`; it is useful for latency-sensitive or NUMA-pinned workloads, at the cost of maintenance and the risk of lopsided utilization, and it is explicitly not a security boundary.

vCPU hot-plug is newer and more fragile than the alternatives, so I prefer resource limits unless I truly need it. Max pluggable is always sockets times cores, and `vcpus` sets how many are plugged at start. It is Linux only, a kernel newer than 4.7 is recommended, and you need a udev rule to online new CPUs automatically.

A few Windows extras I keep in mind regardless of CPU type: install the VirtIO drivers from the virtio-win ISO at build time (and consider pinning a known-good virtio-win release rather than always taking the newest), leave the machine version pinned (it is automatic for Windows, because Windows reacts badly to virtual-hardware changes even across cold boots), and set `balloon: 0` on anything critical, since the Windows balloon driver is not built in and can slow the guest.

## Profiles I actually use

These assume the migratable profiles are ones I want to keep freely live-migratable across the cluster. If a given VM is pinned, I treat it as the specialized profile instead.

General Linux, portability first:

```
cpu: x86-64-v2-AES,flags=+pcid;+spec-ctrl;+ssbd
numa: 1
```

Raise the base to `x86-64-v3` if every node is Haswell or newer, which picks up AVX2. The AMD variant is `flags=+ibpb;+amd-ssbd;+virt-ssbd`.

Specialized Linux, features first and pinned:

```
cpu: host
numa: 1
affinity: <cores for the target socket>
```

This is the local-AI and GPU-passthrough pattern. Passthrough already blocks migration, so `host` costs nothing. Pin `affinity` and memory to the socket that owns the GPU or NIC. On AMD with `host`, still add `+virt-ssbd` explicitly. One nuance: on some Intel server parts, heavy AVX-512 lowers all-core clocks, so more flags is not unconditionally faster for mixed workloads. Benchmark the real workload rather than assuming `v4` or `host` wins.

General Windows, my default for almost every Windows VM:

```
cpu: x86-64-v3
numa: 1
balloon: 0
```

Do not add `md_clear` or `flush_l1d`; leaving them off is the whole point on Windows. Leave the machine version pinned. Applying the change needs a full shutdown and start, after which I confirm with `Get-SpeculationControlSettings` that the mitigations went inactive.

Specialized Windows, only when a feature forces `host`:

```
cpu: host,flags=+pcid;+spec-ctrl;+ssbd
numa: 1
affinity: <cores for the target socket>
```

Only when the feature list above applies. If you just want speed, `x86-64-v3` is almost always faster on Windows. Add `level=30` if Hyper-V or VBS hangs at boot on recent Intel, and re-enable `cet-ss;cet-ibt` per VM only if a VBS workload needs them. If performance is unacceptable and you do not need the guest's own MDS and L1TF protection, a custom model can strip `md_clear` while keeping other host flags, but weigh that intra-guest trade first.

## My cluster

A cluster that spans Dell generations mixes CPU capability levels. As a worked example from my setup: an R730xd (13th gen, Broadwell-era Xeon E5 v3 and v4) supports up to `x86-64-v3`, while an XC740xd (14th gen R740 base, Skylake-SP and Cascade Lake) additionally supports `x86-64-v4` with AVX-512. The migration-safe ceiling for the whole cluster is therefore the lower of the two, `x86-64-v3`. Only VMs pinned to the Skylake-class node can safely use `host` or `v4` and see AVX-512.

So the action is simple: run `lscpu` on every node, set the house default to the highest `vN` level the weakest node supports, and reserve `host` for pinned, passthrough, or single-node VMs.

## Decision checklist

1. Windows guest? Default to `x86-64-v3` (fallback `x86-64-v2-AES`), even on a single node, because `host` triggers the mitigation penalty. Only use `host` if a feature forces it.
2. Linux guest, pinned by passthrough or hard affinity, or on a single-node host? Use `host`. Linux has no mitigation penalty, so take the free flags.
3. Needs cluster-wide live migration? Mixed Intel and AMD goes to `x86-64-vN` at the lowest common level. Single vendor goes to `x86-64-vN` at the lowest common level, or a named model of the lowest generation for extra flags.
4. Linux only: add mitigation flags unless you used `host` and confirmed the host already exposes them. Intel `+pcid;+spec-ctrl;+ssbd`, AMD `+ibpb;+amd-ssbd;+virt-ssbd`.
5. Multi-socket host: set `numa: 1`, sockets equal to NUMA node count.
6. Windows extras: VirtIO ISO at build time, leave the machine version pinned, `balloon: 0` if critical, `level=30` if Hyper-V boot fails on recent Intel with `host`, BIOS power profile to max performance.
7. Noisy-neighbor risk: `cpulimit` for a hard cap and `cpuunits` for priority.
8. After any CPU type change: full shutdown and start, not a guest reboot.

## Quick reference

```bash
# Set CPU type
qm set <vmid> --cpu host
qm set <vmid> --cpu x86-64-v3
qm set <vmid> --cpu x86-64-v3,flags=+pcid;+spec-ctrl;+ssbd
qm set <vmid> --cpu custom-<name>

# NUMA and affinity
qm set <vmid> --numa 1
qm set <vmid> --affinity 0-1,8-11

# Resource control
qm set <vmid> --cpulimit 4        # cap at 4 cores of host time
qm set <vmid> --cpuunits 200      # 2x scheduler weight vs default 100

# Host capability checks
lscpu
numactl --hardware | grep available
grep ' pcid ' /proc/cpuinfo
for f in /sys/devices/system/cpu/vulnerabilities/*; do echo "${f##*/} -" $(cat "$f"); done
```

Inside a Windows guest, to compare the mitigation state before and after a change:

```powershell
Install-Module -Name SpeculationControl -Force
Get-SpeculationControlSettings   # compare host vs x86-64-v3
msinfo32.exe                     # VBS state, and whether Windows sees it is a VM
```

VM config lives at `/etc/pve/qemu-server/<vmid>.conf`, and custom models at `/etc/pve/virtual-guest/cpu-models.conf`.

## References and further reading

- Proxmox VE admin guide, QEMU/KVM chapter (CPU type, flags, resource limits, NUMA): <https://pve.proxmox.com/pve-docs/chapter-qm.html#qm_cpu>
- Meltdown and Spectre CPU flags section of that chapter: <https://pve.proxmox.com/pve-docs/chapter-qm.html#qm_meltdown_spectre>
- List of AMD and Intel CPU types as defined in QEMU: <https://pve.proxmox.com/pve-docs/pve-admin-guide.html#chapter_qm_vcpu_list>
- Manual: cpu-models.conf, for custom CPU models: <https://pve.proxmox.com/wiki/Manual:_cpu-models.conf>
- Proxmox forum thread identifying `md_clear` and `flush_l1d` as the Windows performance trigger: <https://forum.proxmox.com/threads/help-about-cpu-type.132652/>
