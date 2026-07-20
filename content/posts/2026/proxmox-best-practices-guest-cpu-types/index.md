---
title: "Proxmox Best Practices - Guest CPU Types"
date: 2026-06-04T01:00:00Z
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
description: "How I pick a Proxmox VM CPU type: host versus the x86-64-vN virtual types, the OS floors that make the choice for you, the Spectre and Meltdown flags those types quietly leave off, and why host is usually the wrong default on Windows."
summary: "How I pick a Proxmox VM CPU type: host versus the x86-64-vN virtual types, the OS floors that make the choice for you, the Spectre and Meltdown flags those types quietly leave off, and why host is usually the wrong default on Windows."
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

Feature exposure is how many host CPU flags (AVX2, AES-NI, AVX-512, and so on) the guest can see and use. More flags means feature-heavy code runs faster, and `host` hands the guest everything the physical CPU has. Portability is whether a running VM can live-migrate to another node. A VM that advertises a flag to its guest and then tries to land on a host without that flag does not degrade gracefully: the migration fails.

So a VM set to `host` is not less stable on its home node. It is just non-portable. That is the real cost, and once I framed it that way the rest fell out of one question per VM.

> [!INSIGHT]
> The Proxmox CPU type menu is not a stability versus performance slider. It is a portability versus feature-exposure trade. `host` gives the guest every flag the physical CPU has and gives up live migration. The `x86-64-vN` types give up flags to stay migratable.

There is one thing that outranks that trade entirely, though, and I want it up front because it decides the floor before anything else gets a vote: modern operating systems now refuse to boot below a given level. That section comes first.

## The floors that decide it for you

The `x86-64-vN` levels are a psABI specification defined jointly by AMD, Intel, Red Hat, and SUSE in 2020. Distributions and Microsoft have started compiling against them, which means the level is no longer only a performance knob. It is an install requirement.

| Guest OS | Minimum level |
|----------|---------------|
| Windows Server 2016 / 2019 / 2022, Windows 10 | v1 (but see AES below) |
| Windows 11 (all), Windows Server 2025 | **v2** (hard requirement: SSE4.2 and POPCNT) |
| RHEL 9, Rocky 9, AlmaLinux 9, CentOS Stream 9 | **v2** |
| RHEL 10, Rocky 10, AlmaLinux 10, CentOS Stream 10 | **v3** |
| Debian, Ubuntu, Arch, openSUSE (current) | v1, but ship v3-optimized paths |

Windows 11 24H2 and Server 2025 will not install or boot without SSE4.2 and POPCNT. That is not a slow boot, it is a hard stop. RHEL 10 and its rebuilds moved the baseline again to v3.

That second row is the one worth planning around. If you standardize the cluster on `x86-64-v2-AES` today because it is the GUI default and it feels conservative, you have a wall coming the first time someone tries to build a Rocky 10 VM. Standardizing on `x86-64-v3` is not a performance preference. On any cluster where every node is Haswell or newer, it is the forward-compatible floor.

> [!CAUTION]
> `kvm64` is not a safe default, it is a broken one. RHEL 9 and its rebuilds will not boot on it, and RHEL 10 will not boot on `x86-64-v2` either. Yet `kvm64` is still the backend and CLI default, so a VM created by script or Terraform lands there while one clicked together in the web UI gets `x86-64-v2-AES`. Check what your automation actually emits.

## The one question

With the floor established, the remaining choice is one question per VM. Does this VM need to move between nodes, or does it need to squeeze the host CPU? Everything below is downstream of that. The short version of how I answer it:

Single node, or a VM already pinned to one node by PCI passthrough or hard affinity, gets `host`. Migration is already off the table, so I take the free flags. That holds for Linux; Windows is a different story, which is the whole reason this post exists.

A VM that needs cluster-wide live migration gets the highest level common to every node, either as an `x86-64-vN` level or a named model of that generation.

A migration domain with mixed Intel and AMD forces the vendor-neutral `x86-64-vN` types. Named vendor models will not cross vendors, and Proxmox is explicit that live migration between Intel and AMD hosts has no guarantee of working at all.

## The options

### host

Exposes the exact flags of the physical CPU. Maximum feature exposure, best Linux performance for anything that uses modern instruction sets. The cost is that it breaks live migration to any node with a different CPU or microcode.

The failure mode is worth understanding precisely, because it is asymmetric and that is how it catches people. Migrating a `host` VM from an older node to a newer one usually works, since every flag the guest knows about is present on the target. Migrating back does not. The VM started on Haswell, moved happily to Skylake, picked up nothing new (the CPU model was fixed at boot), and still cannot return because Proxmox will not let it land somewhere the original flag set is not guaranteed. In practice you discover this during maintenance, when you need to evacuate the newer node and the VM has nowhere to go but a cold boot.

> [!WARNING]
> Microcode counts as part of the CPU definition. Two physically identical servers can diverge if a microcode update rolled out to one and not the other, and `host` migration between them will start failing with no hardware change. Keep microcode and `intel-microcode`/`amd64-microcode` package versions in lockstep across nodes, or do not use `host` on anything that needs to move.

I use `host` for single-node hosts, a genuinely homogeneous cluster (identical CPU and identical microcode on every node), or a VM that is already unmovable because of passthrough.

### max

Worth naming because it shows up in forum threads and in the QEMU docs. `max` is every flag the host exposes plus everything QEMU can emulate in software. It is strictly worse than `host` for portability and it can enable emulated features that are slow. I have never had a reason to use it outside of testing whether a guest will boot with a given flag present.

### The x86-64-vN virtual types

Vendor-neutral, and they work on both Intel and AMD hosts. This is the migration-safe family.

| Type | Compatible with (min CPU) | Flags added over the previous level |
|------|---------------------------|-------------------------------------|
| `kvm64` | Intel Pentium 4+, AMD Phenom+ | QEMU baseline, roughly Pentium 4 class. Not formally x86-64-v1 |
| `x86-64-v2` | Intel Nehalem+, AMD Opteron G3+ | cx16, lahf-lm, popcnt, pni, sse4.1, sse4.2, ssse3 |
| `x86-64-v2-AES` | Intel Westmere+, AMD Opteron G4+ | aes |
| `x86-64-v3` | Intel Haswell+, AMD EPYC (Naples)+ | avx, avx2, bmi1, bmi2, f16c, fma, movbe, xsave |
| `x86-64-v4` | Intel Skylake-SP+, AMD EPYC Genoa+ | avx512f, avx512bw, avx512cd, avx512dq, avx512vl |

`kvm64` gets its own row rather than being labelled v1 because it is a QEMU invention that predates the psABI levels, not the first rung of the same ladder. Treating it as "v1" implies a symmetry that is not there.

The `x86-64-v2-AES` row is the one that deserves more than a table cell. AES-NI was never made part of any psABI level, which is why Proxmox had to invent a non-standard name for it. That means bare `x86-64-v2` runs BitLocker, SMB3 encryption, LUKS, dm-crypt, WireGuard, IPsec, and every TLS termination point in software. The hit there is far larger than anything the v2 versus v3 versus v4 choice produces on its own. If you need a v2-class floor, use `v2-AES`. There is no scenario I have found where bare `x86-64-v2` is the right answer. Both `v3` and `v4` include AES, so the problem disappears above that line.

> [!INSIGHT]
> v4 is not simply "v3 with more." On Skylake-SP and Cascade Lake, sustained AVX-512 work drops the core into a lower frequency license and pulls all-core clocks down noticeably, and it does so per physical core, so a single AVX-512-heavy VM affects the neighbours sharing that core. Intel improved this from Ice Lake onward and dropped AVX-512 from consumer parts entirely. On a mixed or older cluster, v4 costs you migration and gains you almost nothing outside HPC, video encode, and numeric libraries.

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

`reported-model` controls what the guest thinks it is running on. `phys-bits host` matches the host's physical address bits rather than the default 40 bits, which you need for guests with more than 1TB of RAM or with large-BAR passthrough devices; it also breaks migration to hosts with a different value, so set it only when a VM actually requires it. Access is ACL-gated per model at `/mapping/cpu/<name>`: `Mapping.Use` is required to assign a model to a VM, and that check is enforced on create, update, and clone, so someone who can clone a VM that uses a custom model still needs `Mapping.Use` on it. These earn their place when you want one documented, cluster-wide profile reused across many VMs.

## The security dimension nobody puts on the menu

Here is the part that is easy to miss. The `x86-64-vN` virtual types do not enable the Spectre and Meltdown mitigation flags by default. `host` inherits whatever the physical CPU exposes, so the migration-safe path silently gives those up unless you add them back. Two things have to be true for any of these flags to help: the host CPU has to support and propagate the feature (current microcode), and the guest OS has to be patched and configured to use it.

The flags are not one bundle, and this matters for the Windows section below.

For Intel guests:

- `pcid` is a **performance** flag, not a mitigation. It reduces the TLB flush overhead that KPTI imposes. It costs nothing, triggers nothing in the guest, and should be on essentially every Intel VM regardless of OS.
- `spec-ctrl` exposes IBRS and IBPB for Spectre v2 where retpolines are not enough. Included in `-IBRS` models, explicit otherwise. This one has a runtime cost when the guest uses it.
- `ssbd` is the Spectre v4 fix, never included by default, always explicit, also carries a runtime cost.

For AMD guests:

- `ibpb` covers Spectre v1 and v2, included in `-IBPB` models, add otherwise.
- `amd-ssbd` is the Spectre v4 fix with better performance than `virt-ssbd`.
- `virt-ssbd` should be exposed as well, because some kernels only understand that one. It has to be set explicitly even with `host`, since it is a virtual flag that does not exist on physical AMD CPUs.
- `amd-no-ssb` tells newer silicon it is not vulnerable to v4, and it is mutually exclusive with the two `ssbd` flags.

To see what the host actually exposes:

```bash
for f in /sys/devices/system/cpu/vulnerabilities/*; do echo "${f##*/} -" $(cat "$f"); done
grep ' pcid ' /proc/cpuinfo
```

A migration-safe Intel base with the mitigations added back looks like this:

```
cpu: x86-64-v3,flags=+pcid;+spec-ctrl;+ssbd
```

### Nested virtualization needs vmx

One flag that is not in any `vN` level and comes up constantly: `vmx` on Intel, `svm` on AMD. Without it the guest cannot run Hyper-V, WSL2, Docker Desktop's Hyper-V backend, VBS/HVCI, the Android emulator, or a nested Proxmox. The usual advice is "use `host`," but you do not have to give up migration for it:

```
cpu: x86-64-v3,flags=+pcid;+vmx
```

The host module also needs nesting enabled (`kvm_intel nested=1` or `kvm_amd nested=1`, check with `cat /sys/module/kvm_intel/parameters/nested`). Note that nested virt itself blocks live migration on some Proxmox versions regardless of CPU type, so verify on your version before you count on it.

## Why Windows is different

On Linux, `host` does what you expect: more flags, more performance, no penalty. On Windows it frequently makes things slower, and for a while that made no sense to me. Native has to beat emulated, right? Not here.

When the CPU type is `host`, QEMU passes the physical CPU's security flags into the guest, including `md_clear` (the MDS mitigation) and `flush_l1d` (the L1TF mitigation). If the guest then enables its own in-guest mitigations, it starts doing VERW and L1D flushes on transitions. The result is a large jump in memory read latency and, in bad cases, a guest that visibly stutters with the vCPUs pegged. The `x86-64-vN` types and most named models do not pass `md_clear` or `flush_l1d`, so Windows never turns those mitigations on and the penalty never appears.

That "if the guest then enables" is doing real work in that sentence, and it explains why forum reports of this are inconsistent:

> [!CAUTION]
> Client Windows (10 and 11) enables speculative execution mitigations by default. **Windows Server has them disabled by default** and requires `FeatureSettingsOverride` and `FeatureSettingsOverrideMask` under `HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management` to turn them on. So the `host` penalty should hit a Windows 11 guest hard and may not reproduce at all on a stock Server 2022 VM that nobody has touched. Check `Get-SpeculationControlSettings` in your own guest before assuming which case you are in.

That registry behaviour also gives you a third option the CPU menu does not: keep `host` for a feature you actually need, and control the mitigation state from inside the guest rather than by starving the vCPU of flags. It is the more precise instrument, and it is auditable, which the CPU-type approach is not.

There is a second effect stacked on top of the flags. With `host`, Windows can decide it is running on real hardware and enable virtualization-based security, which pulls in nested virtualization inside the VM, which hurts again. `msinfo32` will tell you whether Windows thinks it is virtualized and whether VBS is on.

Net effect: on Windows, `x86-64-v3` is frequently both faster and migratable than `host`. Older Windows Server barely touches the newer instruction extensions anyway, so the flags `host` adds rarely pay for the mitigation cost they can trigger. That is why I default Windows guests to `x86-64-v3`, with `x86-64-v2-AES` as the conservative fallback for older or mixed-low clusters.

Two caveats I want to be careful about, because both get oversold.

> [!WARNING]
> "Switching off host loses no security, the mitigations still run at the hypervisor level" is only half true. Cross-VM and host-to-guest isolation are handled by the Proxmox kernel regardless of guest CPU type. What you actually give up is the guest's own intra-VM MDS and L1TF protection: process-to-process and kernel-to-user side-channel hardening inside that Windows VM. Fine for a single-tenant VM running trusted code. Weigh it deliberately for a multi-user RDS host or anything running untrusted workloads.

The `vN` types also get their safety purely by not exposing the flags, so `v3` is not inherently more secure than `host` with `md_clear` stripped. It does the same thing by omission, which means it is doing it silently and without leaving a record of the decision anywhere except the VM config.

Applying a CPU type change needs a full shutdown and start. A reboot from inside Windows is not enough to renegotiate the vCPU. I confirm the change with `Get-SpeculationControlSettings`: on `host` the mitigations report active, on `v3` they report inactive because the flags are absent.

### When host is genuinely required

Reach for `host`, or explicit flag exposure, when a feature demands it, not for raw speed:

Nested virtualization inside the guest, though as noted above `+vmx` usually gets you there without giving up the whole flag set. GPU or PCI passthrough, and anti-cheat that inspects CPU identity. Software that needs an instruction set your `vN` floor does not carry.

In those cases the VM is usually pinned already, since passthrough kills migration, so `host` costs nothing extra on the portability axis. On Windows, accept that the mitigation penalty may ride along; if VBS is the goal, that penalty is the feature. A couple of Windows-on-recent-Intel specifics live here: if Hyper-V or VBS hangs at boot under `host` or `max`, `level=30` is the known workaround (x86_64 only, silently ignored elsewhere). And `cet-ss` and `cet-ibt` are disabled by default for Windows 11 machine types because they currently break boot for guests with VBS, so only re-enable them per VM if a workload needs them.

## Verifying what the guest actually sees

Host-side checks tell you what is available. Guest-side checks tell you what landed, and those are the ones that catch a config that did not apply.

On a Linux guest, modern glibc will print the psABI levels the loader has detected:

```bash
/lib/ld-linux-x86-64.so.2 --help | grep -A6 'Subdirectories of glibc-hwcaps'
```

Anything listed as supported is a level the guest can actually use. `lscpu` gives you the raw flag list for anything more specific, and `grep -o 'avx512[a-z]*' /proc/cpuinfo | sort -u` is a quick v4 check.

On a Windows guest:

```powershell
Install-Module -Name SpeculationControl -Force
Get-SpeculationControlSettings   # compare host vs x86-64-v3
msinfo32.exe                     # VBS state, and whether Windows sees it is a VM
Get-ComputerInfo | Select-Object HyperVisorPresent, DeviceGuard*
```

## The supporting knobs

Sockets times cores is total vCPUs, and the split is mostly irrelevant for performance. Set sockets for software licensing if that matters, otherwise one socket, or match NUMA nodes. Overcommit is safe: total vCPUs across all VMs can exceed physical cores, and the host schedules them like any multithreaded load. Proxmox will not let a single VM exceed the physical core count.

On multi-socket hosts, enable NUMA so guest memory and vCPUs land local to a socket instead of spread across the memory bus. It is also required to hot-plug cores or RAM. When enabled, set the VM's socket count to the number of host NUMA nodes. Check with `numactl --hardware | grep available`, where more than one node means the host is NUMA.

For resource control there are three knobs. `cpulimit` is a hard cap on host CPU time in whole-core units (1.0 is one core, 4.0 is four); set it equal to the total core count to guarantee a VM never exceeds its vCPUs, since peripheral and IO threads can otherwise push it slightly over. `cpuunits` is relative scheduler weight, valid range 1 to 10000 under cgroup v2 with a default of 100 (2 to 262144 with a default of 1024 on legacy cgroup v1); a VM at 200 gets twice the CPU bandwidth of one at 100 under contention, so it is priority, not a cap. `affinity` pins vCPUs to specific host cores in `taskset` list format, for example `0-1,8-11`; it is useful for latency-sensitive or NUMA-pinned workloads, at the cost of maintenance and the risk of lopsided utilization, and it is explicitly not a security boundary.

vCPU hot-plug is newer and more fragile than the alternatives, so I prefer resource limits unless I truly need it. Max pluggable is always sockets times cores, and `vcpus` sets how many are plugged at start. It is Linux only, a kernel newer than 4.7 is recommended, and you need a udev rule to online new CPUs automatically.

A few Windows extras I keep in mind regardless of CPU type. Install the VirtIO drivers from the virtio-win ISO at build time, and consider pinning a known-good virtio-win release rather than always taking the newest. Leave the machine version pinned; it is automatic for Windows, because Windows reacts badly to virtual-hardware changes even across cold boots. Set `balloon: 0` on anything critical, since the Windows balloon driver is not built in and can slow the guest. And the Hyper-V enlightenments (`hv_relaxed`, `hv_spinlocks`, `hv_vapic`, and friends) are driven by the VM's `ostype`, not by the CPU type, so setting `ostype` correctly is what gets you those; you do not need to hand-tune them and changing CPU type does not disturb them.

## Enforcing a default

There is no datacenter-wide setting for a default CPU type. The GUI default for a new VM is `x86-64-v2-AES` and the backend/CLI default is `kvm64`, and neither is configurable from the web UI. So "set the house default" has to be enforced somewhere else:

- **Templates.** Set the CPU type once on the template, clone from it, done. Simplest option and it survives the GUI path.
- **Terraform** (`bpg/proxmox` or `telmate/proxmox`). Put `cpu { type = "x86-64-v3" }` in the module defaults so nothing can be built without it.
- **Ansible** against the API, or a post-create hook, for anything already deployed.
- **An audit one-liner** for drift, since none of the above catches a VM someone built by hand:

```bash
for f in /etc/pve/qemu-server/*.conf; do
  printf '%s\t%s\n' "$(basename "$f" .conf)" "$(grep -E '^cpu:' "$f" || echo 'cpu: (default kvm64)')"
done
```

Run that across the cluster and you will find the `kvm64` VMs you did not know you had.

## Profiles I actually use

These assume the migratable profiles are ones I want to keep freely live-migratable across the cluster. If a given VM is pinned, I treat it as the specialized profile instead.

General Linux, portability first:

```
cpu: x86-64-v3,flags=+pcid;+spec-ctrl;+ssbd
numa: 1
```

Drop to `x86-64-v2-AES` only if a node predates Haswell, and accept that RHEL 10 and its rebuilds will not run there. The AMD variant is `flags=+ibpb;+amd-ssbd;+virt-ssbd`.

Specialized Linux, features first and pinned:

```
cpu: host
numa: 1
affinity: <cores for the target socket>
```

This is the local-AI and GPU-passthrough pattern. Passthrough already blocks migration, so `host` costs nothing. Pin `affinity` and memory to the socket that owns the GPU or NIC. On AMD with `host`, still add `+virt-ssbd` explicitly. And remember the AVX-512 frequency licensing note above: on Skylake-SP class parts, more flags is not unconditionally faster for mixed workloads. Benchmark the real workload rather than assuming `v4` or `host` wins.

General Windows, my default for almost every Windows VM:

```
cpu: x86-64-v3,flags=+pcid
numa: 1
balloon: 0
```

`+pcid` is the one flag I do add on Windows, because it is pure performance and triggers nothing in the guest. What I deliberately leave off is `md_clear` and `flush_l1d`; that omission is the whole point here. Whether to also add `+spec-ctrl;+ssbd` is a real decision rather than a default: add them for a multi-user RDS host or anything running untrusted code, leave them off for a single-tenant appliance VM. Leave the machine version pinned. Applying the change needs a full shutdown and start, after which I confirm with `Get-SpeculationControlSettings` that the state is what I intended.

Specialized Windows, only when a feature forces `host`:

```
cpu: host,flags=+pcid;+spec-ctrl;+ssbd
numa: 1
affinity: <cores for the target socket>
```

Only when the feature list above applies. If you just want speed, `x86-64-v3` is almost always faster on Windows. Add `level=30` if Hyper-V or VBS hangs at boot on recent Intel, and re-enable `cet-ss;cet-ibt` per VM only if a VBS workload needs them. If performance is unacceptable and you do not need the guest's own MDS and L1TF protection, you have two levers: a custom model that strips `md_clear` while keeping other host flags, or the `FeatureSettingsOverride` registry values inside the guest. I prefer the registry route because it is visible from inside the VM and shows up in a security audit, where a stripped CPU flag does not.

Nested virt on a migratable Windows VM:

```
cpu: x86-64-v3,flags=+pcid;+vmx
numa: 1
balloon: 0
```

## My cluster

A cluster that spans generations mixes CPU capability levels, and mine spans four:

| Node | CPU | Microarch | Threads | Max level |
|------|-----|-----------|---------|-----------|
| 1 | 2x Xeon Gold 6148 | Skylake-SP | 80 | **v4** |
| 2 | 2x Xeon E5-2695 v4 | Broadwell-EP | 72 | v3 |
| 3 | 2x Xeon E5-2690 v3 | Haswell-EP | 48 | v3 |
| 4 | i7-8700 | Coffee Lake | 12 | v3 |

The migration-safe ceiling for the whole cluster is v3, set by three of the four nodes. Only VMs pinned to the Skylake node can use `host` or `v4` and see AVX-512, and given the frequency licensing behaviour on that generation, I have not yet found a workload where that was worth losing HA failover for.

The more interesting part is that those three v3 nodes are not identical inside v3, which is the concrete argument for setting `x86-64-v3` explicitly rather than reaching for a named model or `host`:

- Haswell lacks ADX, RDSEED, and PREFETCHW that Broadwell has.
- Coffee Lake adds CLFLUSHOPT, XSAVEC, XGETBV1, and UMIP that neither Xeon has.
- Skylake-SP adds all of the above plus the AVX-512 set.

Migration only works safely from fewer features to more, never the reverse. Setting `x86-64-v3` normalizes the mask in both directions so a VM can move anywhere, which a named model like `Broadwell-noTSX-IBRS` would not give me here (it would strand VMs on the Haswell node).

The i7 also illustrates something the CPU type discussion does not cover: it is v3-capable and therefore fully in the migration domain, but it has 12 threads, no ECC, one socket, and a UHD 630 iGPU. CPU level is not the binding constraint on what runs there. It gets the Quick Sync transcode VM and light always-on services, and nothing stateful, and none of that is a CPU-type decision.

So the action is simple: run `lscpu` on every node, set the house default to the highest `vN` level the weakest node supports, enforce it in your templates or Terraform rather than trusting the GUI, and reserve `host` for pinned, passthrough, or single-node VMs.

## Decision checklist

1. **Check the floor first.** Windows 11 or Server 2025 means v2 minimum. RHEL/Rocky/Alma 10 means v3 minimum. If a floor applies, it is not negotiable and the rest of the checklist works within it.
2. **Never bare `x86-64-v2`.** Use `x86-64-v2-AES` so AES-NI reaches the guest. Never `kvm64` on a modern OS.
3. **Windows guest?** Default to `x86-64-v3,flags=+pcid`, even on a single node, because `host` can trigger the mitigation penalty. Only use `host` if a feature forces it. Decide `+spec-ctrl;+ssbd` per VM based on whether the guest runs untrusted or multi-tenant workloads.
4. **Linux guest, pinned by passthrough or hard affinity, or on a single-node host?** Use `host`. Linux has no equivalent mitigation trap, so take the free flags.
5. **Needs cluster-wide live migration?** Mixed Intel and AMD goes to `x86-64-vN` at the highest common level. Single vendor goes to the same, or a named model of the lowest generation present if you need extra flags.
6. **Add mitigation flags** unless you used `host` and confirmed the host already exposes them. Intel `+pcid;+spec-ctrl;+ssbd`, AMD `+ibpb;+amd-ssbd;+virt-ssbd`. On Windows, `+pcid` is free; the other two are a deliberate choice.
7. **Nested virt?** `+vmx` (Intel) or `+svm` (AMD) plus host module nesting, rather than jumping to `host`.
8. **Multi-socket host:** `numa: 1`, sockets equal to NUMA node count.
9. **Windows extras:** VirtIO ISO at build time, machine version pinned, `balloon: 0` if critical, correct `ostype` for enlightenments, `level=30` if Hyper-V boot fails on recent Intel with `host`, BIOS power profile to max performance.
10. **Noisy-neighbour risk:** `cpulimit` for a hard cap, `cpuunits` for priority.
11. **Enforce the default** in templates or Terraform, and audit `/etc/pve/qemu-server/*.conf` for drift.
12. **After any CPU type change:** full shutdown and start, not a guest reboot. Then verify from inside the guest.

## Quick reference

```bash
# Set CPU type
qm set <vmid> --cpu host
qm set <vmid> --cpu x86-64-v3
qm set <vmid> --cpu x86-64-v3,flags=+pcid;+spec-ctrl;+ssbd
qm set <vmid> --cpu x86-64-v3,flags=+pcid;+vmx        # nested virt, still migratable
qm set <vmid> --cpu custom-<name>

# NUMA and affinity
qm set <vmid> --numa 1
qm set <vmid> --affinity 0-1,8-11

# Resource control
qm set <vmid> --cpulimit 4        # cap at 4 cores of host time
qm set <vmid> --cpuunits 200      # 2x scheduler weight vs default 100

# Host capability checks
lscpu
qm cpu list                       # models this node offers
numactl --hardware | grep available
grep ' pcid ' /proc/cpuinfo
cat /sys/module/kvm_intel/parameters/nested
for f in /sys/devices/system/cpu/vulnerabilities/*; do echo "${f##*/} -" $(cat "$f"); done

# Audit CPU type across all VMs on a node
for f in /etc/pve/qemu-server/*.conf; do
  printf '%s\t%s\n' "$(basename "$f" .conf)" "$(grep -E '^cpu:' "$f" || echo 'cpu: (default kvm64)')"
done
```

Inside a Linux guest:

```bash
/lib/ld-linux-x86-64.so.2 --help | grep -A6 'Subdirectories of glibc-hwcaps'
lscpu
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
- The x86-64 psABI microarchitecture levels: <https://gitlab.com/x86-psABIs/x86-64-ABI>
- Red Hat on the RHEL 10 x86-64-v3 baseline: <https://developers.redhat.com/articles/2024/01/02/rhel-10-plans-x86-64-v3-microarchitecture-requirement>
- Microsoft guidance on enabling speculative execution mitigations on Windows Server: <https://support.microsoft.com/en-us/topic/kb4072698>
