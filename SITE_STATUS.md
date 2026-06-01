# L-One Main Site Status

更新时间：2026-06-01

## 项目位置

- 本地项目目录：`D:\L-One Lab\03_独立项目\L-One-main-site`
- GitHub 仓库：`https://github.com/macabyavaha7-sys/L-One-main-site`
- 默认分支：`main`
- 当前线上同步提交：`472b59b Serve Shougang images from site assets`

## 当前部署状态

- 主站部署平台：腾讯云 EdgeOne Pages
- 部署来源：GitHub 仓库 `macabyavaha7-sys/L-One-main-site`
- 部署分支：`main`
- 当前站点形态：单文件静态 HTML
- 当前主入口：`index.html`
- 构建命令：无
- 安装命令：无
- 输出目录：`/`
- EdgeOne 会根据 GitHub `main` 分支更新自动重新部署。
- EdgeOne 预览链接可用于测试，但带 `eo_token` 的预览链接不适合作为正式公开链接传播。

## 域名状态

- 正式域名：`l-one.asia`
- 备案状态：首次备案，管局审核中。
- 域名相关任务暂停，等待备案审核完成后继续。
- 后续计划：主站绑定 `l-one.asia`，素材仓库绑定 `static.l-one.asia`。

## 当前文件结构

```text
/
  assets/
    works/
      index.json
      shougang/
        cover.webp
        image-01.webp ... image-18.webp
        metadata.json
      youhuayuan/
        cover.webp
        image-01.webp ... image-18.webp
        metadata.json
      baitasi/
        cover.webp
        image-01.webp ... image-08.webp
        metadata.json
      shunyi-kamakura/
        cover.webp
        image-01.webp ... image-13.webp
        metadata.json
  index.html
  README.md
  SITE_STATUS.md
```

## 已上线内容

### 首钢园作品详情

- 作品标题：《首钢园｜永定河畔的微凉惬意》
- 页面路由：`#work-shougang`
- 内容来源：小红书图文归档
- 已接入内容：标题、摘要、标签、正文、18 张图片、图片预览层、左右切换按钮。
- 当前图片策略：首钢园图片已随主站一起提交到 GitHub，并由 EdgeOne Pages 部署为站内静态资源。
- 当前图片路径示例：`assets/works/shougang/image-01.webp`

### 新增图文作品详情

- 作品标题：《油画院 | 东五环的安静角落》
  - 页面路由：`#work-youhuayuan`
  - 内容来源：小红书图文归档
  - 已接入内容：标题、摘要、标签、正文、18 张图片、图片预览层、左右切换按钮。
- 作品标题：《白塔寺 | 夜晚的北京胡同》
  - 页面路由：`#work-baitasi`
  - 内容来源：小红书图文归档
  - 已接入内容：标题、摘要、标签、正文、8 张图片、图片预览层、左右切换按钮。
- 作品标题：《顺义“小镰仓”？ | 劝慎来，但有惊喜》
  - 页面路由：`#work-shunyi-kamakura`
  - 内容来源：小红书图文归档
  - 已接入内容：标题、摘要、标签、正文、13 张图片、图片预览层、左右切换按钮。

## 素材仓库规划

### 临时素材仓库

当前已在腾讯云轻量服务器上搭建 L-One 临时素材仓库：

- 服务器公网 IP：`62.234.73.162`
- 服务软件：Nginx
- 服务器素材根目录：`/www/l-one-static`
- 公网健康检查：`http://62.234.73.162/health.txt`
- 当前验证结果：公网可访问，返回 `L-One static storage is running.`

服务器目录规划：

```text
/www/l-one-static/
  works/        作品图片、作品素材
  articles/     文章配图
  skills/       技能包、Markdown、提示词、代码片段
  downloads/    可下载文件、ZIP、PDF
  course/       课件、课程相关素材
```

当前使用原则：

- GitHub 只放网站代码、页面、JSON、MD 和少量必要图片。
- 成批图片、PDF、ZIP、课件、素材包优先放轻量服务器或后续 COS。
- 视频成片优先使用外部平台链接。
- 需要站内播放或下载的短视频、课件、素材包，先放轻量服务器临时仓库。
- 未来备案完成后，把 `http://62.234.73.162/` 替换为 `https://static.l-one.asia/`。

## 内容与素材规则

### 完整作品内容

公众号长文、图文笔记、视频号、小红书、B 站、抖音、完整视频笔记等内容，优先使用外部平台链接或嵌入。若需要站内归档，可同步标题、摘要、封面、正文、标签和必要图片到本站。

### 素材库 / 资料库 / 技能仓库

参考图片、分镜参考短片、排版参考、调色参考、教程文件、Markdown 笔记、代码片段、技能包、可下载模板等，不应长期堆在 GitHub。第一阶段使用轻量服务器 40G 云硬盘作为素材空间；未来素材量变大后迁移到 COS/对象存储。

## 跨对话协作规则

其他“网站内部搭建”对话在执行前必须读取：

`D:\L-One Lab\03_独立项目\L-One-main-site\SITE_STATUS.md`

执行边界文件：

`D:\L-One Lab\03_独立项目\L-One-main-site\TASK_GUARDRAILS.md`

更新规则：

- 只修改 D 盘项目目录内的文件。
- 不再把主站项目写入 C 盘。
- 修改前先读取本状态文件，确认最新线上状态。
- 修改前必须明确本次任务的目标、可修改范围、不可修改范围、预期可见结果和验证门槛。
- 修改完成后更新本文件的“更新时间”和“最近变更”。
- 修改完成后将变化同步到 GitHub 仓库。
- 腾讯云 EdgeOne Pages 会根据 GitHub 仓库自动重新部署。

## 最近变更
- 2026-06-01：修复首钢园作品来源平台、作品类型和页面标签的真实乱码问题，统一可见分隔符为 `·`；强化 `scripts/site-audit.js`，新增对 `??`、`???`、`�`、错误标签分隔符、作品元数据字段和正文完整性的检查；新增 `TASK_GUARDRAILS.md`，明确每次任务的可修改范围、不可修改范围和交付验证门槛。
- 2026-06-01：恢复《首钢园｜永定河畔的微凉惬意》完整小红书原始正文（410 字），移除详情页正文区多余横线，新增 `scripts/site-audit.js` 作为交付前审查脚本，检查原文长度、禁止文案、乱码、路由和 JS 语法。
- 2026-06-01：修复作品详情页正文区展示规则，删除“原文内容”标题、“原始内容入口”卡片和归档说明，单篇作品页仅保留原始标题、原始图片、原始笔记正文和必要作品元数据。
- 2026-06-01：修复 Works 页面新增作品展示问题：分类筛选已接入真实 data-filter / data-work-type 交互，三篇新增作品恢复为完整信息卡片，四个作品详情页中文 UI 乱码已清理，并保留横向相册与图片预览功能。

- 2026-06-01：批量归档 3 条小红书图文作品：《油画院 | 东五环的安静角落》《白塔寺 | 夜晚的北京胡同》《顺义“小镰仓”？ | 劝慎来，但有惊喜》；每篇作品独立存储 metadata、封面和图片组，并接入 Works 页面与独立详情页路由。
- 2026-06-01：新增 `assets/works/index.json` 作为作品总索引，统一记录每篇作品的 ID、slug、标题、封面、metadata 路径和图片数量，避免后续批量调用时混淆。
- 2026-06-01：搭建腾讯云轻量服务器临时素材仓库，Nginx 指向 `/www/l-one-static`，公网健康检查 `http://62.234.73.162/health.txt` 已通过。
- 2026-06-01：首钢园图片从外部防盗链地址改为站内静态资源路径，并提交 `assets/works/shougang/image-01.webp` 至 `image-18.webp`。
- 2026-06-01：修复 `assets/works/shougang/metadata.json`，恢复为可解析 JSON。
- 2026-06-01：确认 GitHub `main` 分支已同步到提交 `472b59b`。
- 2026-05-31：优化首钢园详情页图片浏览体验，支持横向相册、左右切换、全屏预览、Esc 关闭和方向键浏览。
- 2026-05-31：新增第一条作品详情页 `#work-shougang`，接入《首钢园｜永定河畔的微凉惬意》。
- 2026-05-31：调整主导航为 `Recent / Works / Skills / About`，新增 `Works / 作品归档` 页面。
- 2026-05-30：创建跨对话维护状态文件。
- 2026-05-29：将 `index.html` 和 `README.md` 上传到 GitHub 仓库。
- 2026-05-29：腾讯云 EdgeOne Pages 预览部署成功。

## 下一步建议

1. 其他对话继续进行网站内部版式和内容优化。
2. 新作品若只是少量图片，可先走 GitHub + EdgeOne；若素材较多，优先测试上传到轻量服务器素材仓库。
3. 备案通过后绑定 `l-one.asia` 和 `static.l-one.asia`。
4. 素材量超过轻量服务器适合范围后，迁移到腾讯云 COS/对象存储。
