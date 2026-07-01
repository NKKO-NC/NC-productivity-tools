# Productivity Tools

A bilingual public repo for small, practical tools.

This repository is organized around tools instead of implementation language, so each tool can grow on its own while still sharing a consistent homepage, styling, and language toggle.

## Current Focus

- Build lightweight browser-based tools
- Keep every tool easy to open on GitHub Pages or locally
- Support both Traditional Chinese and English

## Structure

```text
assets/
  css/                  Shared styles
  js/                   Shared scripts
docs/
  repo-structure.md     Repo conventions and growth notes
tools/
  excel-column-helper/  First shipped tool
index.html              Homepage and category guide
```

## First Tool

- `Excel Column Helper`
  Convert Excel column letters such as `A`, `Z`, or `XFD` into their numeric positions and browse a range.

## Next Step

When we add a new tool, the minimum set should be:

- `tools/<tool-slug>/index.html`
- `tools/<tool-slug>/app.js`
- `tools/<tool-slug>/README.md`

Then add one card on the homepage so users can discover it by function.
