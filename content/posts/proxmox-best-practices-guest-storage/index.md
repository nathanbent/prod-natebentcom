---
title: "Proxmox Best Practices - Guest Storage"
date: 2026-05-11T01:00:00Z
author: "Nate"
weight: 1
# aliases: ["/first"]
tags: ["Proxmox", "ZFS", "Storage", "Homelab", "Virtualization"]
categories: ["Virtualization"]
series: ["Proxmox Best Practices"]
showToc: true
TocOpen: false
draft: false
hidemeta: false
comments: false
description: "How I set cache, aio, iothread, and discard on Proxmox VMs, decided by how each VM is used rather than the OS inside it, plus the ZFS foundations that keep those choices safe to leave alone for years."
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

## Why this post exists

Every time I built a new VM I found myself re-litigating the same disk settings: cache mode, aio, whether iothread was worth it, discard on or off. The answers are scattered across forum threads, half of them stale, and a fair number of them wrong for the storage I actually run. So I sat down and worked out a set of defaults I could stop thinking about, then validated them against my own cluster.

This is that reference. The one idea it all hangs on:

> [!INSIGHT]
> The right disk settings are decided by how a VM is *used*, not by the OS inside it. Two questions settle almost everything: can this VM move to another host, and what kind of storage is under it? Answer those and the rest falls out.

I validated everything below against my own three-node cluster. The version baseline matters more than usual here, because io_uring fallback behavior, ZFS Direct I/O, and ARC defaults are all version-dependent. If you are far from this baseline, re-check the assumptions flagged at the end.

### Validated against

| Component | Version |
|---|---|
| Proxmox VE | 9.2.4 |
| Kernel | 7.0.14-2-pve |
| pve-qemu-kvm | 11.0.2 |
| qemu-server | 9.1.18 |
| OpenZFS | 2.4.3 |

Two consequences worth stating up front. First, this kernel and QEMU are well past the era where io_uring had rough edges on iSCSI and LVM, so io_uring is safe as a universal default. Second, OpenZFS gained Direct I/O in the 2.3 line, so on a plain file `cache=none` now actually honors `O_DIRECT` instead of the older behavior of quietly failing the open. That last point has a catch that bit an assumption I had, and I get into it below.

## The short version

Everything here collapses to two storage lanes and a small set of universal guest settings.

The shared, HA lane is network iSCSI. Any VM that must be able to move between nodes, whether HA-managed or just live-migratable, lives here. Mobility forces `cache=none` for coherency and `aio=io_uring` for safety. No writeback, ever, because host page cache is per-node and is not coherent across a migration.

The pinned, local lane is local ZFS (or a local dir). Any VM tied to specific hardware through GPU or other PCIe passthrough is pinned here and cannot live-migrate anyway. On ZFS this is still `cache=none` plus `io_uring`, because ARC is already the cache. The only place writeback is ever correct is a pinned, disposable VM on a non-ZFS local disk.

Universal settings, every VM, both lanes, both OSes:

- SCSI controller: `virtio-scsi-single`
- `iothread=1`
- `cache=none` (the default; do not override except the one documented writeback case)
- `aio=io_uring` (the default; only consider `native` on pinned raw-block disks, never on ZFS or qcow2)
- `discard=on`
- `ssd=1` (SSD emulation) on any SSD-backed tier
- Guest agent installed; balloon off for anything memory-sensitive (domain controllers, AI boxes)

## Cache: why none, and the one exception

Proxmox cache modes are combinations of `O_DIRECT` and `O_DSYNC` semantics. The practical summary:

| Mode | Host page cache | Data-loss risk on host crash | Use |
|---|---|---|---|
| `none` (default) | Bypassed (`O_DIRECT`); guest write cache reported present | Low; guest flushes go to storage | Everything here |
| `writeback` | Used for read and write | In-flight async writes lost on power loss | Narrow: pinned, disposable, non-ZFS |
| `writethrough` | Used for read; writes sync | Low, but slow writes | Rare |
| `directsync` | Bypassed; writes sync | Lowest; slowest | Guests that never flush; rarely needed |
| `writeback (unsafe)` | Used; ignores guest flushes | Total | Throwaway and templating only |

### Why none wins on ZFS

With `cache=none`, QEMU opens the disk with `O_DIRECT` and the Linux host page cache is not used. On ZFS, reads are served from ARC and async writes buffer in the ZFS dirty cache, which flushes on its own timer (about 5 seconds by default). Sync and flush writes are honored and go to the ZIL or SLOG. ZFS is, in effect, already doing writeback-style buffering internally, and doing it safely.

Turning on `writeback` stacks the host page cache on top of ARC and the ZFS dirty cache. The same data then lives in the guest, the host page cache, and ARC at once. That inflates RAM usage, and the kernel will happily fill free memory with page cache and start swapping. On ZFS, writeback is a straight loss with added crash risk for no gain.

Here is the catch I mentioned, and the part I had wrong in my head at first. Direct I/O in OpenZFS is a dataset feature, and it does not apply to zvols:

> [!QUOTE] OpenZFS, zfsprops(7)
> Direct I/O is "not supported with zvols." So on a zvol, `cache=none` never bypasses ARC. It bypasses the host page cache, and ARC does the caching, which is exactly what you want anyway.

So for the great majority of VMs here, which sit on zvols under `zfspool` storage, `cache=none` was always the right call and its behavior has not changed. Where Direct I/O actually matters is a raw or qcow2 file sitting on a ZFS *dataset*, and that is the one place the 2.3 change fixes an old headache. More on that in the Windows template example.

### Why none wins on shared iSCSI

Two reasons. The backing store here is a TrueNAS box, which is itself ZFS with its own ARC and ZIL, so writeback at the QEMU layer would double-cache across the network for zero gain. More importantly, writeback holds data in per-node host page cache, which is not coherent across a live migration.

> [!CAUTION]
> Any cache mode other than `none` on storage a VM can migrate across is a known corruption vector. The host page cache is per-node, nothing keeps it coherent across a live migration, and nothing warns you. It works fine right up until a migration eats a VM. Mobile VMs stay on `none`, full stop.

### The one legitimate writeback case

The official Windows guest best-practices guidance does suggest writeback for performance, and a hardware RAID controller with a battery or PLP-backed cache handles writeback fine. Both assume storage with no other caching layer underneath. In a ZFS-heavy environment that describes exactly one situation: a pinned (passthrough) VM whose disk sits on a plain non-ZFS local device (an ext4 or LVM dir store, or a dedicated passed-through SSD), holding disposable data where losing a few seconds of in-flight writes on a crash is an annoyance, not a loss. A Parsec or VDI gaming VM is the textbook fit. On a disk like that, `writeback` (or even `writeback (unsafe)` for a pure scratch disk) is correct. The moment that disk is on ZFS, revert to `none`.

## aio: why io_uring, and when native or threads

`aio` selects the async I/O submission path. The headline benchmark finding: `native` and `io_uring` land within a few percent of each other, `native` has a slight edge at QD1 latency, and `io_uring` degrades a little less gracefully only under extreme load. So `native` looks marginally better on paper, but it comes with a hard constraint.

`aio=native` may only be used on unbuffered, `O_DIRECT`, raw block storage with `cache=none`. If anything in the I/O path can block on submission, `native` blocks the whole submission syscall. That rules it out for:

- ZFS (copy-on-write, can block) : use `io_uring`
- qcow2 (metadata lookups block) : use `io_uring`
- thin LVM (virtual-to-physical metadata) : use `io_uring`

`aio=native` is only safe on directly-mapped raw block: a raw iSCSI LUN, thick LVM with no overlay, NVMe, or Ceph and RBD, always with `cache=none`.

Here is why this environment uses `io_uring` everywhere anyway. The shared iSCSI storage is thick LVM, which on its own would tolerate `native`. But it has snapshot-as-volume-chain enabled, and that layers a qcow2 overlay on top of the LV whenever a snapshot exists, including during every PBS backup run. Once the active image is qcow2, `native` blocks. So `io_uring` is the correct, durable choice for the iSCSI lane, and this qcow2-in-the-chain behavior during backups is a very plausible cause of the intermittent iSCSI I/O oddities I chased a while back. For local ZFS, `io_uring` is mandatory regardless.

`aio=threads` is the traditional pairing with `cache=writeback` (buffered, non-`O_DIRECT`). It is valid but generally slower than `io_uring`, which also supports buffered I/O. For the one writeback VM, `io_uring` is fine and slightly faster; `threads` is acceptable and harmless. Go with `io_uring`.

## The four-quadrant matrix

The OS quadrants still govern guest-side tuning: drivers, balloon, cluster size. Storage placement collapses to the two lanes, generalized on shared iSCSI and passthrough on local.

| Setting | Generalized Linux (DNS, Zabbix, Caddy, Ansible, code-server) | Specialty Linux (AI, other passthrough) | Generalized Windows (DC, PKI) | Specialty Windows (VDI, Parsec) |
|---|---|---|---|---|
| Lane / storage | Shared iSCSI (HA) | Local ZFS SSD (pinned) | Shared iSCSI (HA) | Local, non-ZFS pinned |
| Controller | virtio-scsi-single | virtio-scsi-single | virtio-scsi-single | virtio-scsi-single |
| iothread | 1 | 1 | 1 | 1 |
| cache | none | none | none | writeback (only if non-ZFS local and disposable) |
| aio | io_uring | io_uring | io_uring | io_uring (or threads) |
| discard | on | on | on | on |
| ssd | 1 | 1 | 1 | 1 |
| balloon | ok | off | off | off |
| Notes | Already the fleet default | Align data disks | Fixed RAM, virtio drivers | Writeback only if backing is non-ZFS; this box is on ZFS, so none |

### Real examples from the cluster

I have genericized the hostnames and VM IDs below, but the configs and the deltas I found are the real ones.

Generalized Linux, `app-01` (201) and `app-02` (202). Already correct: `virtio-scsi-single`, `iothread=1`, `discard=on`, `ssd=1`, inheriting `cache=none` and `aio=io_uring`. No changes. These are the reference implementation for the lane. One of them runs the same [code-server setup I wrote up separately](https://natebent.com/posts/self-hosting-codeserver/), which is a good example of the generalized Linux profile in practice.

Specialty Linux, `ai-01` (701). Core is correct: on the `SSD-r10` ZFS pool, `cache=none` and `io_uring` inherited, `balloon=0`, NUMA-pinned, GPU passthrough. One delta: `scsi0` has `discard=on,ssd=1` but the `scsi2` 256G data disk had neither. Align it:

```bash
qm set 701 --scsi2 SSD-r10:vm-701-disk-1,discard=on,ssd=1,iothread=1
```

For large sequential model storage, a bigger `volblocksize` (64K to 128K) on that disk's zvol would compress better and read faster than the 16K default. That requires recreating the zvol, which I cover under ZFS Foundations.

Generalized Windows, domain controllers and PKI (prescriptive; I do not have a live example captured). Same as generalized Linux plus Windows guest tuning: `bios=ovmf`, `machine=q35`, the VirtIO SCSI driver loaded at install, qemu-guest-agent, and fixed RAM with balloon off (AD and a CA behave poorly under memory pressure). Do not apply the generic Windows writeback advice here: this data is integrity-critical and lives on shared iSCSI, so `cache=none` is mandatory.

Specialty Windows, `win11-gpu-template` (1903), my Windows 11 template. On `local` dir storage (a `.raw` file), GPU passthrough, `ostype=win11`, and it was running `aio=threads,cache=writeback,discard=on,ssd=1`. This is the case that caught me. `local` on this node turned out to be a ZFS dataset (`rpool/var-lib-vz`), so despite the VM being pinned and disposable, the writeback branch does not apply: the `.raw` sits on ZFS, and writeback just double-caches on top of ARC. The correct config is `cache=none` plus `aio=io_uring`:

```bash
qm set 1903 --scsi0 local:1903/vm-1903-disk-1.raw,aio=io_uring,cache=none,discard=on,ssd=1,iothread=1
```

Because this is the template for the whole quadrant, test-boot after the change; every future clone inherits it.

Why it was `threads` plus `writeback` originally: on older OpenZFS, `cache=none` on a *file* on a ZFS dataset failed to open with `O_DIRECT` (the classic `could not open disk image`), and buffered I/O via `writeback` and `threads` was the working fallback. OpenZFS 2.3 added Direct I/O on files, and 2.4.3 here has it, so `O_DIRECT` on a file opens cleanly and the workaround is no longer needed. If `O_DIRECT` is still somehow rejected, do the architecturally correct thing instead: VM disks on ZFS belong on zvols (`zfspool` storage), not raw files on dir storage. Migrating this disk to a zvol-backed store (or the node's `local-ssd-2tb-qvo` thin-LVM pool) gives native `cache=none` plus `io_uring` with no caveats, and puts the box cleanly in the local ZFS pinned lane. Worth noting, since Direct I/O does not touch zvols, moving to a zvol is not about `O_DIRECT` at all; it just sidesteps the whole file-on-dataset problem.

## ZFS foundations

Guest disk settings sit on top of these. Getting them wrong causes slow, invisible degradation over months, which is exactly why they belong in any storage doc you intend to trust.

### Current state

- ashift=12 (4K sectors) on all pools. Correct for these drives, and since ashift is immutable it is locked in well.
- volblocksize=16K on all zvols (the PVE 8.1+ default). All pools are mirrors or striped mirrors, so there is no RAIDZ parity-padding penalty; 16K is an efficient general default here.
- compression=lz4 everywhere. Keep it; it is effectively free and often a net throughput gain.
- sync=standard everywhere. Correct. It honors guest flushes and batches async writes via the transaction group. Do not set `sync=disabled` (unsafe) or `sync=always` (slow) as a blanket policy.
- logbias=latency, ARC c_max=64G on 251G RAM (currently around 28G). Healthy and deliberate, and well clear of the PVE default 10% cap.

### volblocksize alignment

`volblocksize` sets the ZFS record size for a zvol and cannot be changed in place; it is fixed at creation, so changing it means creating a new disk. Alignment guidance:

- General Linux guests (ext4, xfs): the 16K default is fine. Leave it.
- Windows guests: NTFS defaults to 4K clusters. A 4K guest write against a 16K zvol block forces a 16K read-modify-write, up to 4x write amplification on small random writes. Mitigations, in order of preference: format Windows *data* volumes with 16K or 64K NTFS clusters to match or exceed volblocksize; or leave the OS volume default and accept the modest overhead (SSD plus lz4 make it tolerable). Do not lose sleep over this on the SSD tiers, but do care about it for write-heavy Windows workloads.
- Large sequential data (AI models, media): a 64K to 128K volblocksize compresses better and streams faster than 16K. Worth doing on dedicated data zvols, not OS disks.

### Storage-level thin provisioning

`local-zfs-hdd-8tb-r10` has `sparse 1` (thin). `local-zfs-ssd-8tb-r10` does not, so new disks there are created thick with a `refreservation`, which blunts thin provisioning and discard reclaim on the best pool. Add it (affects new disks only):

```bash
# via GUI: Datacenter > Storage > local-zfs-ssd-8tb-r10 > Thin provision = yes
# existing thick disks stay thick until recreated
```

### TRIM

`autotrim=off` on all pools. The guest discard chain (`fstrim` to `discard=on` to the zvol) frees blocks inside ZFS, but nothing TRIMs the physical SSDs unless autotrim is on or a scheduled trim runs. I prefer a scheduled monthly trim over `autotrim=on`, since scheduled trim avoids the latency spikes continuous autotrim can cause:

```bash
# monthly zpool trim via systemd timer (create on each node with SSD pools)
systemctl enable --now zfs-trim-monthly@local-zfs-sas-ssd-r10.timer   # if using a template unit
# or a simple cron: 0 3 1 * *  /sbin/zpool trim local-zfs-sas-ssd-r10
```

### SLOG note

The 8TB HDD pool's SLOG is a consumer SSD with no power-loss protection. A SLOG without PLP can lose the in-flight sync writes it exists to protect on a power event. That is acceptable for a homelab, but it is a known weak point: an enterprise PLP SSD (or the enterprise SAS SSDs already in the box) would be the upgrade path. On UPS, the practical risk narrows to kernel panics and hardware faults.

## Guest-side checklists

### Linux

- VirtIO SCSI single controller, `iothread=1`, `discard=on`.
- Enable periodic TRIM inside the guest: `systemctl enable --now fstrim.timer`.
- Modern ext4 and xfs honor barriers and flushes by default; nothing to do.
- qemu-guest-agent installed and running (`agent: 1`) for clean quiesce, backup, and shutdown.

### Windows

- `bios=ovmf`, `machine=q35`, TPM as needed.
- Load the VirtIO SCSI driver from the virtio-win ISO during install; install the full virtio guest tools plus qemu-guest-agent afterward.
- `ssd=1` so Windows treats the disk as SSD (disables scheduled defrag, enables Retrim). `discard=on` so UNMAP reaches the backend.
- Balloon off with fixed RAM on infrastructure (DCs, CA). The balloon driver can cause slowdowns and memory pressure that AD and PKI dislike.
- Where volblocksize matters (write-heavy data volumes), format NTFS with a 16K or larger cluster size.

## Health and hygiene findings

These sit outside the per-VM settings. Ordered by urgency:

1. `local-zfs-hdd-3tb-mirror` is around 94% full and doubles as the PBS datastore. ZFS write performance and fragmentation degrade sharply past roughly 80 to 85% full. This undermines everything on that pool regardless of VM settings. Reclaim space or relocate the PBS datastore first.
2. No physical TRIM scheduled (autotrim off, no `zpool trim` timer). Add a monthly scheduled trim on the SSD pools.
3. `local-zfs-ssd-8tb-r10` missing `sparse 1`. New disks on the best pool are thick. Enable thin provisioning; convert existing thick disks opportunistically.
4. Consumer non-PLP SLOG on the 8TB pool. Document the risk; plan a PLP replacement.
5. Cosmetic: `recordsize=16K` set at the SSD pool root is inert for zvols (it governs file datasets, not volumes). Harmless, noted so it is not mistaken for VM tuning.

## What to re-verify when things change

This doc is durable, not eternal. Re-check these when the environment shifts:

- On a PVE major upgrade: confirm the default `aio` is still `io_uring` and that no new io_uring or storage fallback was introduced. Re-read the qemu-server changelog for disk-default changes, and confirm the ARC default cap has not moved under you.
- On an OpenZFS major upgrade: re-check Direct I/O behavior and any change to the default `volblocksize` for newly created disks.
- If the TrueNAS or iSCSI fabric is rebuilt (say, proper 10GbE): re-confirm whether the presentation is still thick LVM with snapshot-as-volume-chain. If it ever becomes thin, `native` was already ruled out, but re-verify `io_uring` is still the default. If you move to a non-ZFS SAN with BBU cache, the writeback calculus changes for pinned VMs on it.
- If any pinned Windows VM moves onto ZFS: drop writeback back to `cache=none`.
- If you add a dedicated SLOG or L2ARC, or change ashift on a rebuild: revisit the sync and volblocksize notes.

## Quick reference

```
Universal:      scsihw=virtio-scsi-single  iothread=1  discard=on  ssd=1
Shared iSCSI:   cache=none  aio=io_uring                 (HA / mobile)
Local ZFS:      cache=none  aio=io_uring                 (pinned)
Local non-ZFS,  cache=writeback  aio=io_uring            (pinned + disposable ONLY)
 disposable:
Never:          aio=native on ZFS/qcow2/thin-LVM; writeback on ZFS or shared/mobile
Windows infra:  balloon off, fixed RAM, virtio drivers
```

## References and further reading

- Proxmox, [Storage: LVM (snapshots as volume chains)](https://pve.proxmox.com/wiki/Storage:_LVM). Confirms that snapshot-as-volume-chain layers qcow2 on top of the LV, which is what rules out `aio=native` on the iSCSI lane during snapshots and backups.
- OpenZFS, [zfsprops(7)](https://openzfs.github.io/openzfs-docs/man/master/7/zfsprops.7.html). The `direct`, `sync`, and volume properties, including that Direct I/O bypasses ARC on datasets and is not supported on zvols.
- OpenZFS, [2.4.0 release notes](https://github.com/openzfs/zfs/releases). The Direct I/O line and the uncached-I/O fallback behavior referenced above.
- Proxmox, [Proxmox VE 9.2 release notes](https://pve.proxmox.com/wiki/Roadmap). The version baseline this doc was validated against (kernel 7.0, QEMU 11.0, ZFS 2.4).
