---
title: 'Ansible & Network Engineers, Pt. I'
date: 2024-01-13T15:18:50-06:00
# weight: 1
# aliases: ["/first"]
tags: ["Ansible", "Network Engineer", "Cisco", "Aruba AOS-S"]
categories: ["Experiences", "Thoughts"]
author: "Nate"
# author: ["Me", "You"] # multiple authors
showToc: true
TocOpen: false
draft: false
hidemeta: false
comments: false
description: "Playing with Ansible in a network setting"
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

I have been trying to gather my thoughts about using Ansible as a network engineer for a while now; but I've never found a good perspective to tell the story through.  Even to begin to summarize how useful Ansible can be in a network setting can be a daunting task; my ongoing Obsidian web of notes seems to grow exponentially the more I explore.

## Intro and context

Since I have to start somewhere, I think that covering the basic framework of how I use Ansible, and some of the most common tasks that I have been able to automate and speed up over time.

For example, I recently worked on a project where we were establishing standards conformance in an environment of roughly 100 switches.  Traditionally, in order to check things like SNMP communities, Syslogging servers and the like, you'd have to log in to each switch individually.


Using Ansible, we were able to programmatically make sure that each switch matched those standards.  As Ansible works though it's playbook of activities, it will report back as a success or a failure, making tracking extremely simple.

## Setting up the environment

The environment for Ansible is mostly contained in the inventory files that you keep, containing the devices that will be configuring.

A simple `inventory.yaml` file that I used recently looked like this;

```yaml
[SwitchGroup1]
[ios]
ios01 ansible_host=ios-01.example.net
ios02 ansible_host=ios-02.example.net
ios03 ansible_host=ios-03.example.net

[ios:vars]
ansible_become=yes
ansible_become_method=enable
ansible_network_os=cisco.ios.ios
ansible_user=my_ios_user
ansible_password=my_ios_password

```

## Basic example tasks

For my example task of ensuring SNMP settings are correct"
``` yaml
blah blah blah
blah blah blah
blah blah blah
```


## Some thoughts on Ansible's place in my toolbox

Ansible has become one of my more used deployment methods; it's incredibly versatile in terms of what it can do, and what platforms it can interact with.

I've found that Ansible is excellent, and worry-free, for more simple programmatic tasks, where each switch is going to have a matching configuration.  Tasks that require compliance with a standard make the most sense; for example most organizations will want to have the same SNMP communties, syslog servers, logging parameters across their devices. 

## References and further reading
[Ansible documentation for Cisco IOS](https://docs.ansible.com/ansible/latest/collections/cisco/ios/index.html)
