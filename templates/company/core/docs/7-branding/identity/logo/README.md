---
title: Logo
status: draft
date: {{DATE}}
related: [../README.md]
style: guide
---


# Logo

<!-- To write at step 6 (Brand: look). Answers readiness RB-21. Delete this comment when the section is written. -->

The founder brings the logo as a PNG made elsewhere: flat colours on a transparent background, at least 1000 pixels
on its short side. It is traced into SVG, recoloured with the palette for the light and dark versions, checked
against the PNG, and exported as a favicon and app icons. The [brand board](../board.md) shows it all.

What the founder brings, in `source/` (these PNGs are committed, because every version is made from them):

| File | Use |
| --- | --- |
| `logo.png` | the logo for light backgrounds |
| `logo-dark.png` | the logo for dark backgrounds; without it, it is made from the palette |
| `mark.png` | optional: a square mark for the favicon and app icons, when the logo is wide |

What is made from them (do not edit these; they are made again from the PNGs and the palette):

| File | Use |
| --- | --- |
| `logo.svg`, `logo-dark.svg` | the logo on light and dark backgrounds |
| `mark.svg`, `mark-dark.svg` | the square mark, when there is one |
| `favicon.svg`, `favicon.ico` | the browser tab |
| `icon-192.png`, `icon-512.png` | app icons |
| `trace.json` | how faithful each version is, and anything that needs a decision |
| `trace-light.png`, `trace-dark.png` | where a version differs from the PNG, when it does |
