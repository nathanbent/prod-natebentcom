---
title: 'VXLAN Between a FortiGate and Proxmox, Part 3: Automating It With Terraform'
date: 2026-06-30T01:00:00Z
author: "Nate"
# weight: 1
# aliases: ["/first"]
tags: ["Terraform", "VXLAN", "EVPN", "FortiGate", "Proxmox", "SDN", "IaC", "Automation", "Homelab"]
categories: ["Networking", "Automation"]
series: ["Proxmox SDN"]
series_order: 3
showToc: true
TocOpen: false
draft: false
hidemeta: false
comments: false
description: "Taking the hand-built FortiGate and Proxmox EVPN fabric and reproducing it entirely in code, one Terraform workspace driving both platforms, with every wall I hit along the way written down so you do not have to hit them too."
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

## Where this picks up

By the end of [part 2](/posts/vxlan-between-a-fortigate-and-proxmox-part-2-evpn/) I had a working EVPN/VXLAN fabric: a three node Proxmox cluster and a FortiGate sharing overlay segments, with the FortiGate as the anycast gateway for each. Every bit of it was built by hand, CLI on the FortiGate and GUI clicks on the Proxmox SDN. That works, but each new segment is the same five object dance on the FortiGate and the same clicking on Proxmox, and the two platforms have to agree on a set of numbers (the VNI, the route target) that are easy to fat finger. Part 2 was one long lesson in what happens when those numbers drift.

So this post is the obvious next move: reproduce the whole thing in code, one Terraform workspace driving both platforms, so a segment is a few lines of config and one command instead of a hand built ritual across two systems. It is a long one, because the happy path is short and the interesting part is the pile of walls I hit getting there. Those are the reason to read on.

A note on scope: everything here uses real, current provider versions (`bpg/proxmox` and `fortinetdev/fortios`) against Proxmox VE 9.x and a FortiGate on FortiOS 7.6. Your field names and behavior may differ by version, and the single most useful habit in this whole post is learning to read the real schema off your own infrastructure rather than trusting any example, including this one.

## Terraform in one section, if you come from Ansible

If your automation background is Ansible, there is a mental model shift worth making first. Ansible is procedural: run this sequence of steps against a host. Terraform is declarative: here is the set of things that should exist, you work out the difference from reality and close the gap. The rough division of labor is that Terraform manages the existence and shape of infrastructure (VMs, networks, DNS records, SDN objects) and Ansible configures what lives inside them. They are a pipeline, not rivals. Terraform makes the VM exist, Ansible installs and configures it.

Five concepts and you can follow the rest of this post. A provider is a plugin that talks to one system's API (I use two, one for Proxmox and one for the FortiGate). A resource is one managed object. State is the file Terraform keeps of what it believes it created, so it can tell new from changed from deleted. The plan/apply loop is the safety model: `terraform plan` shows the diff without touching anything, `terraform apply` executes it after you confirm. And `for_each` loops a resource over a map, which is how a pile of near identical segments becomes one block plus a data structure.

## The design: one map, both platforms

The whole point is a single source of truth. Every segment is defined once, and both the FortiGate route target and the Proxmox VNet tag are computed from the same number, so they cannot drift:

```hcl
locals {
  asn = 65001
  segments = {
    seg_a = { vni = 4241, subnet = "10.20.41.0/24", gw = "10.20.41.1" }
    seg_b = { vni = 4242, subnet = "10.20.42.0/24", gw = "10.20.42.1" }
    seg_c = { vni = 4130, subnet = "10.20.30.0/24", gw = "10.20.30.1" }
  }
}
```

The FortiGate route target becomes `"${local.asn}:${each.value.vni}"`. The Proxmox tag becomes `each.value.vni`. One number, one place. The whole "mind your tags because the tag is the route target" failure class from part 2 becomes structurally impossible, because there is only one tag to mind and everything derives from it.

## Install and project setup

On a Debian/Ubuntu host (I used my Ansible control node, which is a sensible home for IaC):

```bash
wget -O- https://apt.releases.hashicorp.com/gpg | \
  sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] \
https://apt.releases.hashicorp.com $(lsb_release -cs) main" | \
  sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install -y terraform
terraform version
```

Then a project directory with a providers file and an init:

```hcl
# versions.tf
terraform {
  required_version = ">= 1.5"
  required_providers {
    fortios = { source = "fortinetdev/fortios" }
    proxmox = { source = "bpg/proxmox" }
  }
}
```

```bash
terraform init
```

`init` downloads both plugins and writes `.terraform.lock.hcl` (commit that, it pins provider versions). Set up gitignore right away so secrets and state never leak, because state holds secrets in plaintext:

> [!CAUTION]
> Terraform state is not encrypted. Your FortiGate token, your Proxmox token, and anything else sensitive sit in `terraform.tfstate` in the clear. Gitignore `*.tfstate` and `*.tfvars` *before* your first `apply`, not after you spot them in `git status`.

```bash
cat > .gitignore << 'EOF'
*.tfstate
*.tfstate.*
*.tfvars
.terraform/
crash.log
EOF
git init
```

## Credentials, and where they go

Two API tokens, one per platform. Declare the variables (safe to commit, they are just names), then put the actual secrets in a `.tfvars` file that gitignore excludes:

```hcl
# variables.tf   (note: one argument per line inside a block, see gotchas)
variable "fgt_host"     { type = string }
variable "fgt_token"    { type = string
                          sensitive = true }
variable "pve_endpoint" { type = string }
variable "pve_token"    { type = string
                          sensitive = true }
```

```hcl
# providers.tf
provider "fortios" {
  hostname = var.fgt_host     # host:port together, see the admin-port gotcha
  token    = var.fgt_token
  insecure = true
}
provider "proxmox" {
  endpoint  = var.pve_endpoint
  api_token = var.pve_token
  insecure  = true
}
```

The secrets file (`secrets.auto.tfvars`, loaded automatically, gitignored) holds the real values. Before doing anything else, confirm git is ignoring it:

```bash
git status   # secrets.auto.tfvars must NOT appear
```

If it shows up, stop and fix gitignore first. That check is the whole point.

## The workflow that carried the entire project

Here is the single most important technique, and it is the reason this project worked despite me repeatedly guessing field names wrong: import an existing object first, read its real schema, then write config to match. Do not write resources blind from documentation or memory. Import the real thing, ask Terraform to show you what it actually looks like, and reconcile against that.

The loop:

```bash
# 1. write a minimal resource block matching an existing object
# 2. import the real object into that block
terraform import <resource_type>.<name> <object_id>
# 3. read the actual schema Terraform recorded
terraform state show <resource_type>.<name>
# 4. rewrite your config to match, then confirm no drift
terraform plan     # goal: "No changes"
```

That "No changes" after import is the goal. It proves your config mirrors reality, so from then on Terraform only changes what you ask it to. I used this loop for every single resource type, on both platforms, and every time it saved me from schema guesswork. When a plan surprised me, the fix was always to import and read, not to guess harder.

## The Proxmox side

Importing an existing VNet was the first real step. The minimal block plus import:

```hcl
resource "proxmox_sdn_vnet" "seg_c" {
  id    = "segC"
  zone  = "evpnProd"
  tag   = 4130
  alias = "vm general"
}
```

```bash
terraform import proxmox_sdn_vnet.seg_c segC
terraform state show proxmox_sdn_vnet.seg_c    # reveals: alias, id, tag, zone
terraform plan                                  # No changes
```

Then the payoff, collapsing individual resources into a `for_each` map so one block manages every segment:

```hcl
locals {
  vnets = {
    segA = { tag = 4241, alias = "dmz gateway" }
    segB = { tag = 4242, alias = "dmz services" }
    segC = { tag = 4130, alias = "vm general" }
  }
}

resource "proxmox_sdn_vnet" "evpn" {
  for_each = local.vnets
  id       = each.key
  zone     = "evpnProd"
  tag      = each.value.tag
  alias    = each.value.alias
}
```

Migrating from a single hardcoded resource to a `for_each` map means the resource address changes, so you forget the old one from state (without deleting the real object) and re-import under the new addresses:

```bash
terraform state rm proxmox_sdn_vnet.seg_c      # stops tracking, does NOT delete
terraform import 'proxmox_sdn_vnet.evpn["segC"]' segC
terraform import 'proxmox_sdn_vnet.evpn["segA"]' segA
terraform import 'proxmox_sdn_vnet.evpn["segB"]' segB
terraform plan                                  # No changes across all three
```

## Creating something from nothing

Importing is reconciliation. To actually feel Terraform work, you want a create. A fresh demo VNet:

```hcl
resource "proxmox_sdn_vnet" "demo" {
  id    = "tfDemo"
  zone  = "evpnProd"
  tag   = 4099
  alias = "terraform demo segment"
}
```

```bash
terraform plan     # 2 to add (or 1, depending), 0 to change, 0 to destroy
terraform apply    # type yes
```

After apply, Proxmox stages SDN changes until applied, the equivalent of the "Apply" button. From a node:

```bash
pvesh set /cluster/sdn
pvesh get /cluster/sdn/vnets --output-format json | grep tfDemo
```

That is the "it did something" moment: a network segment that exists because you ran a command.

The demo VM (cloned from a cloud-init template, attached to the VNet Terraform just made):

```hcl
resource "proxmox_virtual_environment_vm" "demo" {
  name      = "tf-demo-vm"
  node_name = "pve-1"

  clone {
    vm_id = 9000       # your cloud-init template's VMID
    full  = true
  }

  agent  { enabled = false }   # see the agent-hang gotcha

  cpu {
    cores = 2
    type  = "host"             # see the CPU-drift gotcha
  }

  memory { dedicated = 2048 }

  disk {
    datastore_id = "local-zfs"
    interface    = "scsi0"
    size         = 20
  }

  network_device {
    bridge = proxmox_sdn_vnet.demo.id   # attaches to the Terraform-made VNet
  }

  initialization {
    datastore_id = "local-zfs"          # see the local-lvm gotcha
    ip_config {
      ipv4 {
        address = "172.31.99.50/24"
        gateway = "172.31.99.1"
      }
    }
  }
}
```

The line that matters is `bridge = proxmox_sdn_vnet.demo.id`. That is a live dependency reference: Terraform knows the VM's NIC needs the VNet, orders creation correctly, and wires the machine onto the network in the same apply.

## The FortiGate side, and the schema discovery that made it painless

This is where the single source of truth payoff lives, and where the import first habit earned its keep hardest. Rather than guess the FortiGate provider's schema, I imported my existing hand built segment's three objects to read their exact structure, then templated the new segment from them.

The EVPN instance schema turned out to use nested blocks for the route targets, which I would have gotten wrong by guessing:

```hcl
resource "fortios_system_evpn" "demo" {
  fosid           = 99
  rd              = "10.0.50.1:4099"
  arp_suppression = "disable"

  import_rt { route_target = "65001:4099" }
  export_rt { route_target = "65001:4099" }
}
```

The VXLAN interface, note `ip_version` is required and `evpn_id` references the instance above:

```hcl
resource "fortios_system_vxlan" "demo" {
  name       = "tfDemo"
  interface  = "v.230|pve-mgmt"
  vni        = 4099
  ip_version = "ipv4-unicast"
  evpn_id    = fortios_system_evpn.demo.fosid
}
```

The L3 gateway interface, where `ip` is a space separated "address mask" string:

```hcl
resource "fortios_system_interface" "demo" {
  name        = "tfDemo"
  vdom        = "root"
  type        = "vxlan"
  interface   = "v.230|pve-mgmt"
  ip          = "172.31.99.1 255.255.255.0"
  allowaccess = "ping"
}
```

The discovery commands that made these correct on the first real try:

```bash
terraform import fortios_system_vxlan.seg_c srv-vm_gen
terraform state show fortios_system_vxlan.seg_c
terraform import fortios_system_evpn.seg_c 30
terraform state show fortios_system_evpn.seg_c
terraform import fortios_system_interface.seg_c srv-vm_gen
terraform state show fortios_system_interface.seg_c
```

A word on those imports: they adopt your real production objects into state. Once you have read the schema, remove them from state (`terraform state rm ...`) so Terraform is not managing production segments you only imported to learn from. The knowledge is already baked into your new resource blocks.

## The gotchas, in the order I hit them

Every one of these cost me time, and none of them is on the happy path. This is the section I wish I had read first.

### Schema field names are not what you assume

I guessed wrong repeatedly. Proxmox VNets use `id`, not `name`. Proxmox subnets use `cidr`, not `subnet`. The fix every time was the import-then-`state show` loop. Stop guessing, read the real schema. If a plan errors with "unsupported argument" or "missing required argument," the object's actual schema (via `terraform state show` on an imported example) is authoritative for your provider version in a way no documentation is.

### HCL block syntax is one argument per line

This errored me immediately:

```hcl
variable "x" { type = string, sensitive = true }   # WRONG
```

HCL does not allow comma separated arguments on one line inside a block. Each argument gets its own line. A small thing that stops you cold at the first `plan`.

### The Proxmox token format is more than the secret

The token string is `user@realm!tokenname=secret`, one `!`, one `=`. The Proxmox UI presents the field in a way that makes it very easy to copy a `tokenid=` label into the value, which fails auth with a 401. If you see a 401, check that your token string is exactly identity, then `!`, then the token's name, then `=`, then the secret UUID, with no stray label text.

### Privilege separation silently strips token permissions

A Proxmox API token created with privilege separation on (the default) has no permissions of its own, even if its user does, until you grant the token itself a role. A 403 right after a working 401-fix is this. Either disable privsep at creation or grant the token an ACL directly.

### Permissions accrue one wall at a time

I built the token's permission set by hitting each 403 in turn, which is honestly a fine way to arrive at a tight least-privilege ACL. The walls, in order: SDN read/write, then VM clone, then storage. The roles that cleared them:

```bash
pveum acl modify /sdn     -token 'tf@pve!name' -role PVESDNAdmin
pveum acl modify /vms     -token 'tf@pve!name' -role PVEVMAdmin
pveum acl modify /storage -token 'tf@pve!name' -role PVEDatastoreUser
```

A Terraform service account that manages VMs and SDN needs roles on `/sdn`, `/vms`, and `/storage` at minimum. You discover the exact set empirically by watching which 403 comes next.

### The default cloud-init datastore may not exist

The VM resource defaulted the cloud-init drive to `local-lvm`, which does not exist on my nodes, so the clone succeeded and then failed writing cloud-init with `storage 'local-lvm' does not exist`. Pin it explicitly with `datastore_id` inside the `initialization` block. There are actually three placements to control: the main disk, the cloud-init drive, and the node. Set all the ones that matter.

### CPU type drifts back to qemu64

The VM resource defaults CPU type to `qemu64`. My template used `host`. Since my config specified no CPU type, Terraform assumed its default and wanted to "correct" the running VM back to `qemu64` on every plan, perpetual drift. Worse, `qemu64` is a generic model that broke the guest agent. Fix: set the CPU type explicitly. `host` for best performance on a pinned VM, or `x86-64-v2-AES` for a migration safe baseline across mixed hardware.

### The guest agent wait can hang for its full timeout

With `agent { enabled = true }`, Terraform waits for the QEMU guest agent to report before considering the VM created. If the template lacks a running agent (or the CPU type broke it), it spins until the timeout. For a demo, `agent { enabled = false }` lets apply complete as soon as the VM is cloned and started, and since you set the IP statically via cloud-init, you already know the address.

### The FortiGate provider hangs on a non-default admin port

This one cost the most, because it failed with no useful error. The provider hung indefinitely during provider configuration, then eventually died with "Plugin did not respond." The cause: my FortiGate serves admin HTTPS on a non-standard port (10443), and everything was trying 443, where nothing listens. The debugging path is worth memorizing:

```bash
ping -c2 <fgt-ip>                                   # reachable?
ping -M do -s 1472 -c2 <fgt-ip>                      # rule out MTU (1500 DF)
curl -k -m5 https://<fgt-ip>/api/v2/monitor/system/status        # 443
curl -k -m5 https://<fgt-ip>:10443/api/v2/monitor/system/status  # the real admin port
```

Ping works but HTTPS times out is the signature. Rule out MTU with a don't-fragment ping at 1472 bytes (if a full 1500 frame passes, MTU is fine). Then check the FortiGate's `admin-sport`. The fix is to fold the port into the provider's `hostname`: `fgt_host = "<ip>:10443"`. The provider has no separate `port` argument.

Always put a timeout (`-m5`) on connectivity tests. Terraform waited forever; curl with a timeout gives you an answer in five seconds.

### Creating a VXLAN auto-creates its interface, so you import it, not create it

Creating a `fortios_system_vxlan` object causes the FortiGate to auto-create a matching `system interface` of the same name. So when Terraform tried to create the `fortios_system_interface` for the gateway, it collided with the auto-made one and returned a 500 Internal Server Error. The fix is to import that auto-created interface into the resource, then apply, so Terraform modifies it (adding the IP and allowaccess) instead of creating:

```bash
terraform import fortios_system_interface.demo tfDemo
terraform apply    # now a modify: sets ip + allowaccess on the existing interface
```

### The one that actually broke traffic: a competing anycast gateway

This was the subtle one, and the best lesson of the whole exercise. After every object existed and the FortiGate had learned the VM's MAC over EVPN, the VM still could not ping its gateway. A sniffer on the FortiGate's segment interface showed nothing arriving at all.

The cause: I had defined a `proxmox_sdn_subnet` with `gateway = "172.31.99.1"`. That told Proxmox to create its own anycast gateway for `.1` on the local bridge. Meanwhile the FortiGate also held `.1`. So the VM resolved its gateway to the local Proxmox bridge and its traffic terminated there, never crossing VXLAN to the FortiGate.

The tell was comparing the demo segment's subnet to a working production segment:

```bash
pvesh get /cluster/sdn/vnets/tfDemo/subnets --output-format json   # had a gateway
pvesh get /cluster/sdn/vnets/segC/subnets   --output-format json   # []  (no subnet!)
```

My working production segments have no Proxmox side subnet at all. The gateway lives only on the FortiGate. Terraform, by "helpfully" letting me define a complete subnet with a gateway, created a second competing gateway that my hand built segments never had. The fix was to remove the subnet resource entirely:

```bash
# delete the proxmox_sdn_subnet resource from the config, then:
terraform apply           # destroys just the subnet
pvesh set /cluster/sdn    # drop the local gateway
```

After that, the VM's gateway ARP was no longer answered locally, so it flooded across VXLAN, reached the FortiGate, and the gateway answered. Traffic crossed the overlay.

> [!INSIGHT]
> Reproducing a working config faithfully sometimes means leaving something out. The tooling's pull toward completeness, a subnet resource that will happily take a gateway, is exactly what diverged the automated version from the proven one. The subnet block looked like completeness. It was the bug.

## Verifying it worked, end to end

Once the FortiGate side existed and the competing gateway was gone, the checks that confirm a fully working segment:

```bash
# FortiGate: did it learn the VM's MAC over EVPN?
diagnose sys vxlan fdb list tfDemo

# FortiGate: did it resolve the VM's IP once traffic flowed?
diagnose ip arp list | grep 172.31.99

# FortiGate: watch ARP arrive live while the VM pings
diagnose sniffer packet tfDemo 'arp' 4

# Proxmox node: is the VNI active with the FortiGate as a remote VTEP?
vtysh -c "show evpn vni" | grep 4099
vtysh -c "show bgp l2vpn evpn" | grep -A3 4099

# The VM itself
ip route          # default via the gateway
ip addr show eth0 # correct IP and MTU
ping 172.31.99.1  # the payoff
```

That final ping is a VM Terraform cloned, on a VNet Terraform created, reaching a gateway Terraform configured on the FortiGate, across the overlay. Both platforms, one workspace, one `apply`.

## Teardown, the other half of it

Because it is all declared, removing it is one command that unwinds everything in dependency order:

```bash
terraform destroy    # review the plan, confirm it only removes the demo objects
```

Always read the destroy plan as carefully as the apply plan. It should remove exactly the demo objects (VM, VNet, FortiGate EVPN/VXLAN/interface) and touch nothing else. That habit is what keeps infrastructure as code from ever nuking something you cared about.

## Takeaways

A few things I would tell myself before starting.

The import-then-`state show` loop is the whole game. Never guess a schema. Import a real example, read it, template from it. This one habit dissolved every field-name problem on both providers.

Provider defaults are opinions, not neutral. The `qemu64` CPU, the `local-lvm` datastore, the competing subnet gateway, all were provider defaults or convenient looking options that diverged from what actually worked. Match your proven config exactly, including its omissions.

Read every plan, especially destroys. The plan is the safety model. A ten second read of a diff is what stands between you and an accidental change to production.

Least privilege is discoverable. Building the API token's permissions one 403 at a time is not elegant, but it arrives at a genuinely tight ACL that grants exactly what is used.

And the real prize, the reason this was worth it: the segment is now a few lines of data in one map, and both the FortiGate and Proxmox halves are generated from the same numbers. The route-target-versus-tag drift that cost me an evening in part 2 cannot happen anymore, because there is one number in one place. The next step from here is obvious: make that map itself come from a source of truth like NetBox, so declaring a segment is a single act that renders both platforms and documents itself. That is where this goes next.

From "what can I do with Proxmox SDN" to a hand built EVPN fabric to the whole thing reproducible from code across two platforms. The automation did not replace understanding it, it required understanding it first, which is the right order to do this in.

## References and further reading

- [bpg/proxmox provider documentation](https://registry.terraform.io/providers/bpg/proxmox/latest/docs) - the Proxmox provider, its SDN resources, and the token/SSH setup
- [bpg/proxmox: SDN EVPN zone resource](https://bpg.sh/docs/resources/virtual_environment_sdn_zone_evpn/) - the EVPN zone schema (and a note on the short vs long resource naming)
- [fortinetdev/fortios provider documentation](https://registry.terraform.io/providers/fortinetdev/fortios/latest/docs) - the FortiGate provider and its `system_evpn` / `system_vxlan` / `system_interface` resources
- [VXLAN with MP-BGP EVPN (FortiOS Administration Guide)](https://docs.fortinet.com/document/fortigate/8.0.0/administration-guide/52499/vxlan-with-mp-bgp-evpn) - the FortiGate objects this post automates
- [Proxmox VE: Software-Defined Network](https://pve.proxmox.com/pve-docs/chapter-pvesdn.html) - the SDN concepts behind the resources
