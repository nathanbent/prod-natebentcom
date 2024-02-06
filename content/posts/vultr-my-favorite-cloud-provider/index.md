---
title: 'Vultr, My Favorite Cloud Provider'
date: 2024-02-04T20:53:42-06:00
author: "Nate"
# weight: 1
# aliases: ["/first"]
tags: ["Cloud", "Vultr", "HomeLab"]
categories: ["Experiences"]
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
There are a huge amount of Cloud providers, and much has been written about the ongoing shift towards the various offerings from Microsoft, Amazon, Google and so on.

The largest Cloud providers have a huge amount to offer, but my best experiences have all been with a somewhat smaller provider called [Vultr](https://vultr.com).

## My setup
I have a few services on Vultr that are almost always provisioned;
Compute:
- A production VM that I use for Cloud-based services such as
	- Storage for ongoing projects
	- Remote access to various resources
	- Hosting for files
- A testing VM that I use for testing things I need, or want to use, before they go into production.
- A connections focused VM that serves as an IPsec endpoint for tunnels between my home and other Cloud providers.
Storage:
- I use a 200Gb HDD blockshare for long-term backups.  I really appreciate that Vultr offers HDD block storage options; it's much cheaper than the nVME options that most other providers are using.  For document storage and longer-term backupsm this is perfect.

## What I like

- A phenomenal variety of well-priced services.
	- Specifically, I really like the ability to create HDD block storage and attach it.  IMHO, for longer term storage there isn't really a benefit to using SSD/NVMe storage.  Linode and Oracle only allow for NVMe blockstorage additions, and Vultr's pricing is consistent/better than what I've gotten from AWS.
- The most local datacenter.  I am located in the Midwest, and Vultr's datacenter in Dallas has been extremely performant for me.
	- Linode also has a datacenter in Dallas, but it doesn't yet offer any VPC services (so I typically use Chicago for Linode services that require VPC)
- Their selection of OS's is comparable with the major providers, and they allow ISO uploading for what isn't already there.


## What I don't like
- I have had some weirdness with their newer VPC2.0 offering.  Namely, I haven't been able to use it for routing traffic through my IPsec tunnel, so I keep the origional VPC connected for that.
  - Getting decent speeds through Samba/NFS took some tuning over VPC2.0, but 

- VPC1.0 connection speeds are fairly low; typically around 400Mbps in iperf3 testing.
  - Because of this I use VPC2.0 for stuff like SMB shares, and VPC1.0 for IPsec traffic.


## References and resources
- [Vultr.com](https://vultr.com)
- [Vultr Docs](https//docs.vultr.com)

