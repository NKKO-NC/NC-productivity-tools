# Release Flow

## Branches

- `main`: production source
- `engineering-preview`: long-lived preview source
- `preview-*`: temporary engineering validation branches

## Published URLs

- Production root stays at the site root.
- Preview builds are published under `/preview/`.
- Current preview tool URL: `/preview/excel-column-helper/`

## Deployment model

The repository uses a GitHub Pages Actions workflow instead of branch-only publishing.

- Push to `main`: publish the production site root and, when available, also keep the latest `engineering-preview` content under `/preview/`.
- Push to `engineering-preview` or `preview-*`: publish the current branch as `/preview/` while keeping production root sourced from `main`.

This keeps production and preview available on the same Pages site without splitting into multiple repositories.
