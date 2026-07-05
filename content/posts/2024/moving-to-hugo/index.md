---
title: 'Moving to Hugo!'
date: 2024-01-01T17:26:18-06:00
author: "Nate"
# weight: 1
# aliases: ["/first"]
tags: ["Untagged"]
categories: ["Uncategorized"]
series: ["Testing"]
series_order: 1
showToc: true
TocOpen: false
draft: false
hidemeta: false
comments: false
description: "After 20+ years of Wordpress, I'm moving to Hugo!"
summary: "After 20+ years of Wordpress, I'm moving to Hugo!"
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
# cover:
#     image: "<image path/url>" # image path/url
#     alt: "<alt text>" # alt text
#     caption: "<text>" # display caption under cover
#     relative: false # when using page bundles set this to true
#     thumb: true
#     hiddenInSingle: true   # never show it stacked atop the article
#     hiddenInList: false    # but do show it as the list thumbnail
editPost:
    disaled: true
    URL: "https://github.com/<path_to_repo>/content"
    Text: "Suggest Changes" # edit text
    appendFilePath: true # to append file path to Edit link
---
# Moving to Hugo!


Over the last few months, I have been playing around with moving my website from Wordpress where it has lived in one form or another since around 2004.  When I first installed it, I believe I was really just looking for some software to run on my newly hacked together LAMP server; I never imagined I would use it for so long.

## Testing


> A plain quote — stays blue, no label.

> [!NOTE]
> Blue, with a "Note" label and info icon.

> [!WARNING]
> Amber.

> [!CAUTION]
> Red.

> [!INSIGHT]
> The xfrm interface has to exist *before* strongSwan can bind the tunnel to it — which is the kind of ordering detail that costs you an afternoon.

> [!TIP]
> Talk to your computers like this "beep boop beep beep"

> [!IMPORTANT]
> Vote in your local elections

> IDK this is just something

> [!QUOTE] Neil Breen
> Network processor NP7 - Fortinet’s breakthrough SPU NP7 works in line with FortiOS functions to deliver:

> [!QUOTE]
> Network processor NP7 - Fortinet’s breakthrough SPU NP7 works in line with FortiOS functions to deliver:

Having used Wordpress for so long, I have gotten extremely familiar with what I liked, but also what I disliked.  To summarize,

**My reasons for changing are myriad, but a few of the main draws include:**

- A static site is *much easier* to work with, and less to worry about

- When I would write something in Wordpress, I would spend more time tweaking the rest of the site to comply.

- I want a longer-term project to spend my time on, and re-designing my web prescence seemed like a good start.

- I was bored, and wanted to try something new.

With all that in mind, the start of the New Year seemed as good a time as any to launch it, and here we are.

Even with those grandest of intentions, it was not without some growing pains.  Moving from a dynamic CMS to a static site generator like Hugo is a pretty large undertaking, and even though I feel like I have a fairly good start, there's a lot of work remaining.

That said, I'm working on bringing some of the my favorite posts from my old iterations of this site over, and will hopefully get a good method down.

## Code blocks

```bash
# a long line to test horizontal scroll behavior inside the code box
ip link add xfrm0 type xfrm dev eth0 if_id 42 && ip link set xfrm0 up && echo "tunnel bound"
```

```yaml
params:
  ShowWordCount: true
  editPost:
    URL: "https://github.com/<repo>/content"
```

```
plain fenced block with no language — should show no label but still copy
```

## Tables

| VNI    | Route-Target   | IP Address      |
|--------|----------------|-----------------|
| 10100  | 65000:10100    | 10.1.0.1/24     |
| 10200  | 65000:10200    | 10.2.0.1/24     |
| 100100 | 65000:100100   | 10.100.0.1/24   |

## Heading level two (accent + left bar)

### Heading level three (accent, no bar)

#### Heading level four (should NOT be accent-colored)

## Footnotes

A sentence with a footnote[^1] and another[^long].

[^1]: A short one.
[^long]: A longer one with `inline code` and a [link](https://gohugo.io/) —
    both should style correctly, and the ↩ should jump back with a brief
    accent flash on the reference.

## Code and other stuff

Some prose with `inline code`, a [link](https://gohugo.io/), **bold**, and *italic*.

1. Ordered item
2. Ordered item
   - nested unordered
   - nested unordered

Term
: A definition-list entry (your `.post-content > dl` measure rule).

---

## Images

{{<figure src="images/test.svg" alt="SVG diagram" caption="SVG branch — served untouched; check it zooms to a real size in the lightbox, not zero.">}}

{{<figure src="images/test.png" alt="Raster screenshot" caption="PNG branch — inspect for WebP srcset, then open the lightbox and confirm the caption + Download full image link.">}}



## Hugo References

- [Hugo Website](https://gohugo.io/)

- [Hugo Documentation](https://gohugo.io/documentation/)
