---
title: 'Creating Ubuntu Templates with Cloud-Init in Proxmox'
date: 2024-04-09T23:20:01Z
author: "Nate"
weight: 1
# aliases: ["/first"]
tags: ["Untagged"]
categories: ["Proxmox", "Ubuntu", "Cloud-Init"]
#series: ["No-Series"]
showToc: true
TocOpen: false
draft: false
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
    hidden: true # only hide on current single page
editPost:
    disaled: true
    URL: "https://github.com/<path_to_repo>/content"
    Text: "Suggest Changes" # edit text
    appendFilePath: true # to append file path to Edit link
---

## Context
This project has been a culmination of a few projects coalescing together at the same time: I've been wanting to play with Cloud-Init in a local environment for a little while now, and I've been finding myself spinning up more and more VMs to test some networking automation.

After a couple of nights of tweaking, I've found myself feeling really enjoying the amount of time I saved compared to manually creating VMs, and I wanted to summarize up my thoughts here.

## Setup

As of writing, I am running Proxmox 8.2 and using Ubuntu 22.04.  This should be much the same across other Ubuntu distros, I imagine I'll try it on Ubuntu 24.04 fairly soon.

## Steps

1. Create a VM in Proxmox
   This is very similar with a normal VM, with a few differences:
   - I use a higher VM number to help organize
   - Select `Do not use any media` on the OS page
   - Enable QEMU Agent
   - Delete the SCSI0 disk that is automatically created
2. Add a Cloud-Init device to the VM
   - Select the storage
3. Go to the Cloud-Init page for the VM and configure some default settings:
   - User
   - Password
   - DNS domain
   - DNS servers
   - SSH public key
   - IP addressing
4. SSH or use the console to download the Ubuntu cloud image using `wget`
   - **[Ubuntu 22.04](https://cloud-images.ubuntu.com/releases/jammy/release/?ref=tcude.net)**

``` bash
wget https://cloud-images.ubuntu.com/releases/jammy/release/ubuntu-22.04-server-cloudimg-amd64.img 

```

- More coming soon!

5. 



## References and resources

- [Cloud-Init Support | Proxmox Wiki](https://pve.proxmox.com/wiki/Cloud-Init_Support)
- [Creating a VM Template in Proxmox | tcude.net](https://tcude.net/creating-a-vm-template-in-proxmox/)
- GitHub
