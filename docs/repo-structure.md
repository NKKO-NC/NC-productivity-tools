# Repo Structure Notes / 倉庫結構說明

## Goal / 目標

This repo is meant to stay simple in the short term while still being clean enough for public maintenance in the medium term.
這個 repo 會保持短期可快速擴充，同時維持中期公開維護所需的清晰度。

## Principles / 原則

- Organize by tool, not by language
- Use the homepage as a product guide
- Keep shared code in `assets/`
- Keep each tool self-contained
- Treat bilingual copy as a first-class requirement
- Mark each tool with visible tech tags and platform limits
- Default deployment path is GitHub Pages + PWA

## Recommended Tool Layout / 建議結構

```text
tools/
  tool-slug/
    index.html
    app.js
    README.md
```

## Why This Structure Works / 為什麼這樣設計

- New tools can be added without touching old tool internals
- Shared layout and language logic stay centralized
- Public visitors can understand the repo quickly
- GitHub Pages deployment remains straightforward
- PWA capabilities can be layered on without changing every tool architecture

## Future Upgrades / 後續升級

- Add a shared tool metadata file if the homepage becomes data-driven
- Add test coverage for pure logic utilities
- Add a contribution guide when outside collaborators join
- Re-evaluate deployment if tools need native windows or deeper desktop integration
