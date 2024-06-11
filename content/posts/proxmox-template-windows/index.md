---
title: 'Proxmox Template Windows'
date: 2024-04-09T23:18:41Z
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

## Setup

## Steps



1. Download the iso from Microsoft (ex: Windows Server 2022 is 4.7 GB)

2. Create a VM, mount iso and install Windows; during setup use the virtio ISO to install drivers (Balloon, NetKVM, and vioscsi). This guide can be applied for Windows Server OS too https://pve.proxmox.com/wiki/Windows_10_guest_best_practices

3. After reboot, enter Audit Mode by pressing Ctrl+Shift+F3

4. Install missing drivers, Windows Updates, and make any other changes you want included in this Template

4.1 (optional) run Disk Cleanup and delete any unnecessary files to make the OS image as small as possible

5. reboot Windows

6. In the System Preparation Tool window, choose “Enter OOBE”, leave Generalize unchecked (to keep the drivers) and Shutdown Options- Shutdown

7. Click OK, wait for Sysprep to run and shutdown

8. Back in Proxmox web gui, click More and Convert to Template



## References and resources
