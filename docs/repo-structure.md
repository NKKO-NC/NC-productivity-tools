# Repo Structure Notes

## Goal

This repo is meant to stay simple in the short term while still being clean enough for public maintenance in the medium term.

## Principles

- Organize by tool, not by language
- Use the homepage as a product guide
- Keep shared code in `assets/`
- Keep each tool self-contained
- Treat bilingual copy as a first-class requirement

## Recommended Tool Layout

```text
tools/
  tool-slug/
    index.html
    app.js
    README.md
```

## Why This Structure Works

- New tools can be added without touching old tool internals
- Shared layout and language logic stay centralized
- Public visitors can understand the repo quickly
- GitHub Pages deployment remains straightforward

## Future Upgrades

- Add a shared tool metadata file if the homepage becomes data-driven
- Add test coverage for pure logic utilities
- Add a contribution guide when outside collaborators join
