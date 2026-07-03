# Preview Delivery Checklist / 預覽交付清單

## Purpose / 用途

When a test push is sent for review, the reviewer should not need to open GitHub and search manually.

之後只要有預覽版要驗收，我們就主動附上可直接點的連結。

## Required Links For Every Preview Push / 每次預覽推送必附連結

### For `engineering-preview`

Always include these links in the handoff message:

- Preview PWA: `https://nkko-nc.github.io/NC-productivity-tools/preview/excel-column-helper/`
- Production site: `https://nkko-nc.github.io/NC-productivity-tools/`
- Actions runs: `https://github.com/NKKO-NC/NC-productivity-tools/actions`
- Compare view: `https://github.com/NKKO-NC/NC-productivity-tools/compare/main...engineering-preview`

If a PR exists, also include:

- Pull request link: `https://github.com/NKKO-NC/NC-productivity-tools/pulls`

### For `preview-*` branches

These branches are validation-only branches.

Always include:

- Branch compare link
- Actions run link

Do not present them as public preview URLs unless a real public deploy exists.

## Standard Handoff Format / 標準交付格式

Use this structure when a preview is ready:

```md
預覽已更新，請直接用下面連結驗收：

- 預覽 PWA：<preview-url>
- 正式站：<production-url>
- Actions：<actions-url>
- PR：<pull-request-url>
- 比較頁：<compare-url>
```

## Release Sequence / 發布順序

1. Develop on `engineering-preview`.
2. Push and wait for Actions to pass.
3. Send the preview links directly in the handoff message.
4. After review is approved, merge into `main`.
5. Send the production link after the `main` deploy completes.

## Production Handoff / 正式發布後回報

After `main` is deployed, include:

- Production site: `https://nkko-nc.github.io/NC-productivity-tools/`
- Actions runs: `https://github.com/NKKO-NC/NC-productivity-tools/actions`
- Merged PR or commit link
