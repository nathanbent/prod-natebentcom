---
title: 'TrueNAS, iSCSI and Windows'
date: 2024-06-05T22:19:11Z
author: "Nate"
weight: 1
# aliases: ["/first"]
tags: ["Truenas", "Proxmox", "Gaming"]
categories: ["Experiences", "Projects"]
series: ["Virtual Gaming PC"]
showToc: true
TocOpen: false
draft: false
hidemeta: false
comments: false
description: "Setting iSCSI up with TrueNAS and Windows"
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
## Creating and Connecting to an iSCSI Share in TrueNAS and Windows 11

As part of the trying to build out my virtualized gaming PC, I wanted to expand the VM past what was directly attached to it.  To try to see what would get me the best performance, I set up both a standard Samba share, and then an iSCSI share. 

## Part 1: Creating an iSCSI Share in TrueNAS

**Step 1: Log in to TrueNAS**
1. Open your web browser and navigate to the TrueNAS web interface.
2. Log in with your credentials.

**Step 2: Create a ZFS Volume**
1. Go to **Storage** > **Pools**.
2. Click on the three dots next to your pool and select **Add Zvol**.
3. Name your Zvol, set the desired size, and click **Save**.

**Step 3: Configure iSCSI**
1. Navigate to **Sharing** > **Block (iSCSI)**.
2. Click on **Portals** and then **Add**. Here, you can specify the IP address to bind the iSCSI service. Click **Save**.

**Step 4: Create an iSCSI Initiator**
1. Go to **Initiators** and click **Add**.
2. You can specify the allowed initiators (client machines) by their IQNs or use wildcards. Click **Save**.

**Step 5: Create an Authorized Access**
1. Navigate to **Authorized Access** and click **Add**.
2. Enter your desired username and password for iSCSI access. Click **Save**.

**Step 6: Create an iSCSI Target**
1. Go to **Targets** and click **Add**.
2. Name your target and link it to the portal and initiator groups you created. Click **Save**.

**Step 7: Create an Extent**
1. Navigate to **Extents** and click **Add**.
2. Name your extent and select **Device** as the extent type.
3. Choose the Zvol you created earlier and click **Save**.

**Step 8: Associate Target and Extent**
1. Go to **Associated Targets** and click **Add**.
2. Select the target and the extent you created. Click **Save**.

#### Part 2: Connecting to the iSCSI Share from Windows 11

**Step 1: Open iSCSI Initiator**
1. Press `Win + S`, type "iSCSI Initiator," and open it.
2. If prompted to start the service, click **Yes**.

**Step 2: Connect to the iSCSI Target**
1. Under the **Targets** tab, enter the IP address of your TrueNAS server and click **Quick Connect**.
2. The iSCSI target should appear in the Discovered Targets list. Click **Connect**.

**Step 3: Log On to the Target**
1. Select the target and click **Log on**.
2. If you configured authentication, click **Advanced** and enter your credentials.
3. Click **OK** to log on to the target.

**Step 4: Initialize and Format the iSCSI Disk**
1. Open **Disk Management** (Press `Win + X` and select **Disk Management**).
2. You should see a new uninitialized disk. Right-click on it and select **Initialize Disk**.
3. Choose either MBR or GPT and click **OK**.
4. Right-click on the unallocated space and select **New Simple Volume**.
5. Follow the wizard to format the disk and assign it a drive letter.

Once the process is complete, you will have a new iSCSI drive accessible from your Windows 11 machine, providing you with the additional storage capacity offered by your TrueNAS server.

Setting up an iSCSI share can seem complex, but following these steps ensures a smooth and successful configuration. Enjoy your expanded storage capabilities!
