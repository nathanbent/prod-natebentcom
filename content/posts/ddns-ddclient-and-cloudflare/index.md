---
title: 'DDNS, ddclient and Cloudflare'
date: 2024-02-03T20:52:13-06:00
weight: 1
# aliases: ["/first"]
tags: ["Docker", "DDNS", "Cloudflare"]
categories: ["Experiences"]
author: "Nate"
# author: ["Me", "You"] # multiple authors
showToc: true
TocOpen: false
draft: false
hidemeta: false
comments: false
description: "Setting DDNS up on Cloudflare can be a little tricky, this is my experience with it"
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
#    image: https://i.ibb.co/K0HVPBd/paper-mod-profilemode.png # image path/url
#    alt: "<alt text>" # alt text
#    caption: "<text>" # display caption under cover
#    relative: false # when using page bundles set this to true
#    hidden: false # only hide on current single page
#
    linkFullImages: true
editPost:
    disaled: true
    URL: "https://github.com/<path_to_repo>/content"
    Text: "Suggest Changes" # edit text
    appendFilePath: true # to append file path to Edit link
---

## Context

[DDNS](https://en.wikipedia.org/wiki/Dynamic_DNS) allows for the dynamic update of DNS entries and attributes - what a fitting name.  This can be an extremely valuable resource for professionals and homelabbers who need to deal with dynamically assigned IP addresses in keeping things connected.

I personally use [Cloudflare](https://www.cloudflare.com/) as a DNS proxy for my various domains, which used to be managed by [Google Domains](https://domains.google.com/) until they [sold that business](https://domains.squarespace.com/google-domains) to [Squarespace](https://domains.squarespace.com/); I've since been moving everything to [Porkbun](https://porkbun.com/).  

Recently, I wanted to organize all of my Cloud and on-prem resources better, and decided to use a singular domain name to help organize everything.  I wanted to be sure that the subdomains I would be assigning out through A records would always be accurate, and thus my project began.

## Setup

To update the DNS A records, there are a few simple things that will need to be setup.

1. There will need to be an [A record](https://www.cloudflare.com/learning/dns/dns-records/dns-a-record/_) in Cloudflare for ddclient to update
2. ddclient will need authentication into Cloudflare using an [API token](https://developers.cloudflare.com/fundamentals/api/get-started/create-token/)
3. ddclient will need to check it's own IP address to compare

Creating the `A record` is straightforward, opening DNS and then Records will allow you to create away.

Authenticating ddclient into Cloudflare is a little trickier, I prefer to create an API key that has read/write access to the domain zone in Cloudflare.  This can be accomplished under Profile -> API Keys, and then by following the wizard.

Finally, ddclient will need some way to check it's own IP and see if the records need updated.  Oddly enough, this seems to be the hardest service to keep consistently working.  There are dozens of  decent to great DDNS services out there that have been around, and yet IP checking services disappear with the winds.  Go figure.

Because I have a number of VMs running among the different cloud providers, running ddclient in a docker container works wonderfully.  Once I install docker and docker compose, I'm easily able to use basically the same two files to keep every VM host updated.

***It should be noted*** that without a pre-made config/ddclient.conf file, the ddclient container will download a default one.  This needs to be altered slightly to work. 

## My docker-compose.yml and ddclient.conf

**docker-compose.yml**

```yaml
## docker-compose.yml
---
services:
  ddclient:
    image: lscr.io/linuxserver/ddclient:latest
    container_name: ddclient
    environment:
      - PUID=<UID>
      - PGID=<GID>
      - TZ=UTC
    volumes:
      - ./config:/config
    restart: unless-stopped
```

**config/ddclient.conf**

```yaml
## ddclient.conf
use=web
web=dynamicdns.park-your-domain.com/getip
web-skip='Current IP Address'
protocol=cloudflare, \
zone=domain.tld, \
ttl=1, \
login=token, \
password=<api-token> \
test-subdomain.domain.tld

```

Once everything has been loaded into place, running `sudo docker compose pull && sudo docker compose up -d` will get it running.  ddclient can be configured to log externally, though I used [Portainer](https://www.portainer.io/) to view the logs and troubleshoot along the way.

## Troubleshooting

I ran into several errors this most recent go-round, as well as before.

`Failure to get IPv4 address`

At some point, the default `use web` option to get the public IP stopped working for me.  Adding the specific web address seems to have mostly fixed it for good; we'll see.

`Failure to communicate with Cloudflare's API`

I had some difficulties in working with the Cloudflare DDNS API as it exists in the default configuation that downloads with 


## References and Resources

- [ddclient website](https://ddclient.net/)
- [ddclient github](https://github.com/ddclient/ddclient)
- [LinuxServer's ddclient github](https://github.com/linuxserver/docker-ddclient)
