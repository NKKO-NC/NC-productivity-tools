# Release Flow

## Branches

- `main`: production source
- `engineering-preview`: long-lived preview source
- `preview-*`: temporary engineering validation branches

## Published URLs

- Production root stays at the site root.
- Preview builds are exposed under `/preview/`.
- Current preview tool URL: `/preview/excel-column-helper/`

## Deployment model

The repository uses a GitHub Pages Actions workflow instead of branch-only publishing.

- Push to `main`: publish the production site root and also package the selected preview branch into `/preview/`.
- Push to `engineering-preview`: run a validation build, then trigger a `main`-based Pages deploy so the public `/preview/` path refreshes without merging into production.
- Push to `preview-*`: run validation builds only. These branches do not publish publicly.

## Why This Shape

GitHub Pages does not provide a public same-repo branch preview deployment flow for arbitrary non-`main` branches in this setup. To keep one repository and one public Pages site:

- `main` remains the only branch that performs the real Pages deployment.
- `engineering-preview` stays reviewable and can still refresh the public `/preview/` area through a `main` workflow dispatch.

This keeps production and preview available on the same Pages site without splitting into multiple repositories.

## Handoff Rule

When a preview build is ready, send the review links directly instead of asking the reviewer to locate them manually.
See [preview-delivery-checklist.md](./preview-delivery-checklist.md).
