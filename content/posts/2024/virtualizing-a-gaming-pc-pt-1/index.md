---
title: 'Virtualizing a Gaming PC, Pt. 1'
date: 2024-02-18T00:36:46Z
author: "Nate"
# weight: 1
# aliases: ["/first"]
tags: ["Untagged"]
categories: ["Uncategorized"]
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
    hidden: true # only hide on current single page
editPost:
    disaled: true
    URL: "https://github.com/<path_to_repo>/content"
    Text: "Suggest Changes" # edit text
    appendFilePath: true # to append file path to Edit link
---

## Context

My son loves to play Minecraft with me, but I only have one Gaming PC.  I do, however, have a Proxmox server with a GPU, and plenty of available compute resources available.

## Setup

Getting the GPU passed through to Proxmox is the most complicated part, and there are two paths you can take:
- Passing the PCI port that the GPU uses through to the host, effectively passing the GPU through
- Virtualizing the GPU and dividing the resources among multiple VMs.

I've opted for the first, most basic option for now.  Mostly because the 1650 Super that I'm using isn't the most powerful card, and I want to take the simplest path first to validate my ideas.

## GPUs & Proxmox

Proxmox needs a few tweaks to make it ready to passthrough GPUs, though the process is fairly similar to passing through other PCI devices.  Basically, the process is like this:

1. Allowing IOMMU in the grub.cfg
2. Blacklist drivers
3. Init modules
4. Set up Windows VM

> Code Examples


## References and Resources
- Proxmox Wiki - PCI Passthrough
