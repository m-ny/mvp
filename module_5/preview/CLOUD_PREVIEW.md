# 公开链接（GitHub Pages）— 20 人卡片预览

仓库已推送后，按下面做一次，即可得到 **所有人可访问的 HTTPS 链接**（约 1–2 分钟部署）。

## 1. 打开仓库设置

在 GitHub 打开 **`m-ny/mvp`** → **Settings** → **Pages**。

- **Build and deployment** → **Source** 选 **GitHub Actions**（不要选 “Deploy from a branch” 的旧方式，除非你知道自己在做什么）。

## 2. 新建工作流

**Actions** → **New workflow** → **set up a workflow yourself** → 把下面整段 YAML 粘贴进去 → 文件名保存为  
`.github/workflows/github-pages-preview.yml` → **Commit directly to main**。

（若你从本机 `git pull` 后已有 `.github/workflows/github-pages-preview.yml`，可跳过粘贴，直接 push 该文件；需要 PAT 勾选 **`workflow`** 权限。）

```yaml
name: GitHub Pages — M5 Preview

on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages-m5-preview
  cancel-in-progress: true

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/configure-pages@v5
      - uses: actions/upload-pages-artifact@v3
        with:
          path: module_5/preview
      - id: deployment
        uses: actions/deploy-pages@v4
```

## 3. 触发部署

在 **Actions** 里打开 **“GitHub Pages — M5 Preview”**，点 **Run workflow**，或再随便改个小文件 push 到 `main`。

## 4. 最终网址（项目站）

一般为：

**`https://m-ny.github.io/mvp/`**

（若组织/仓库名不同，把 `m-ny` 和 `mvp` 换成你的 `owner` 和 `repo`。）

首次启用 Pages 后，若 404，等 1–2 分钟再刷新；在 **Settings → Pages** 里也会显示 **Visit site** 链接。

---

**说明**：公开页会发布 **`module_5/preview`** 目录里的静态文件（含已提交的 `preview_data.json`）。不要在该目录放密钥；若不想公开某批数据，勿把敏感 `preview_data.json` 提交进 Git。
