# L-One Main Site Status

更新时间：2026-06-03

## 项目位置

- 本地项目目录：`D:\L-One Lab\03_独立项目\L-One-main-site`
- GitHub 仓库：`https://github.com/macabyavaha7-sys/L-One-main-site`
- 默认分支：`main`
- 当前内容上线提交：`e9224d2 Add expanded works archive`
- 当前 EdgeOne 状态：GitHub 已同步；EdgeOne 预览域名仍返回旧部署，需要在腾讯云 EdgeOne 控制台确认构建记录或手动重新部署。

## 当前部署状态

- 主站部署平台：腾讯云 EdgeOne Pages
- 部署来源：GitHub 仓库 `macabyavaha7-sys/L-One-main-site`
- 部署分支：`main`
- 当前站点形态：单文件静态 HTML
- 当前主入口：`index.html`
- 构建命令：无
- 安装命令：无
- 输出目录：`/`
- EdgeOne 应根据 GitHub `main` 分支更新自动重新部署；若预览域名未更新，需要在控制台手动重新部署。
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
      jiangfu-railway/
        cover.jpg
        metadata.json
      shunyi-kamakura/
        cover.webp
        image-01.webp ... image-13.webp
        metadata.json
  scripts/
    site-audit.js
  index.html
  README.md
  SITE_STATUS.md
  TASK_GUARDRAILS.md
```

## 已上线 / 待部署内容

### 已接入作品

- 《首钢园｜永定河畔的微凉惬意》：`#work-shougang`，18 张图片。
- 《去废弃铁轨上拍个照｜将府公园》：`#work-jiangfu-railway`，视频作品，站内封面 + 小红书原视频入口。
- 《油画院 | 东五环的安静角落》：`#work-youhuayuan`，18 张图片。
- 《白塔寺 | 夜晚的北京胡同》：`#work-baitasi`，8 张图片。
- 《顺义“小镰仓”？ | 劝慎来，但有惊喜》：`#work-shunyi-kamakura`，13 张图片。
- 已接入作品总数：14 条，其中图文 4 条、视频 10 条。

当前作品索引：`assets/works/index.json`

当前图片策略：本批作品图片仍随主站提交到 GitHub，并由 EdgeOne Pages 部署为站内静态资源。视频作品只归档封面、正文和原视频入口；小红书带签名临时视频流不作为站内长期播放地址。后续成批素材、课件、视频、ZIP、PDF 应优先放轻量服务器或 COS。

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
- 腾讯云 EdgeOne Pages 应根据 GitHub 仓库自动重新部署；若未自动更新，由本“网站上线”对话负责提醒到控制台手动重新部署。

## 最近变更

- 2026-06-03：修复 Works 近期推荐栏 active 标题被左侧容器裁切、视觉上贴近封面的问题：将 active 标题定位从右侧边缘收回到左侧安全区，并限制 spotlight 标题宽度，保证标题与右侧封面之间保留可见间距。同步增强 `scripts/site-audit.js`，增加推荐栏标题宽度和 active 标题安全位置检查。作品详情页正文、图片、metadata 未改动。
- 2026-06-02：纠正 Works 改版范围：恢复具体分类页沿用原有卡片网格逻辑，只在 `全部分类` 视图的筛选条下方新增 `works-spotlight` 置顶交互模块；`图文`、`视频`、`文章` 分类继续按同级卡片列表展示。同步更新 `scripts/site-audit.js`，要求 Works 过滤器只扫描 `.works-board [data-work-type]`，并禁止旧的整页 selector 实现回流。作品详情页正文、图片、metadata 未改动。
- 2026-06-02：调整 Works 页面结构：`works-spotlight` 改为 Works 首页固定顶部近期推荐栏，按作品在原平台的 `publishedAt` 倒序展示最近 5 条；分类栏移到推荐栏下方，仅保留 `图片`、`视频`、`文章` 三项；移除旧的静态首栏 featured 卡片，首钢园回到常规三列作品合集。同步收窄移动端标题换行规则，并更新 `scripts/site-audit.js` 检查推荐栏顺序、三项分类和禁止旧静态首栏回流。作品详情页正文、图片、metadata 未改动。
- 2026-06-01：修复 Works 分类筛选稳定性问题：此前 `.works-board.is-filtered .work-featured` 覆盖了 `hidden` 状态，导致视频筛选页误显示首钢园图文作品；现已增加 `.works-board.is-filtered .work-featured[hidden]` / `.work-card[hidden]` 保护规则，并在 `scripts/site-audit.js` 中检查每个作品入口的 `data-work-type` 必须匹配 metadata。`TASK_GUARDRAILS.md` 新增“作品类型是硬边界”限制：视频页不得出现图文，图文页不得出现视频。
- 2026-06-01：批量新增 9 条小红书视频作品：《一口叹气！好看的地方就是藏着不给看》《环球影城 | 年度总结篇2/3【吃喝】》《环球影城 | 一年去二十多次的总结篇1/3》《环球影城 | 一年去二十多次的总结篇3/3》《解放双手的小配件 | 运动相机》《如果你也在大望路上班 | 别在公司附近溜达》《北环影万圣节 | 证明我胆儿小的时候到了》《798艺术区 | 能把故事画墙上的地方》《在西五环 | 藏着一条绝美的旧铁路》；每条视频独立存储 metadata 和封面，接入 Works 视频分类与对应详情页。
- 2026-06-01：新增第一条视频作品《去废弃铁轨上拍个照｜将府公园》：从小红书链接抓取标题、正文、标签、发布时间、封面和视频元数据，独立存储到 `assets/works/jiangfu-railway/metadata.json`，封面存储为 `assets/works/jiangfu-railway/cover.jpg`；Works 页面接入 `视频` 分类卡片和 `#work-jiangfu-railway` 详情页。由于小红书视频流为带签名临时 CDN 地址，当前详情页先使用站内封面 + 小红书原视频入口，不把临时视频流作为长期站内播放器。
- 2026-06-01：调整 Works 页面分类视图层级：`全部分类` 保留主推荐作品 + 二级作品卡片结构；切换到 `图文`、`视频`、`文章` 时，作品统一降级为同级卡片网格展示，避免具体分类页继续出现一级/二级推荐关系。
- 2026-06-01：执行上线同步流程，新增 3 篇作品与作品索引已推送到 GitHub，最新提交为 `692ad95 Add new works to main site`；GitHub 远端已验证作品路由和新增图片资源可访问，EdgeOne 预览域名暂未切换到最新部署，需要在腾讯云控制台重新部署或等待构建记录更新。
- 2026-06-01：验证轻量服务器 IP 素材仓库逻辑，`http://62.234.73.162/health.txt` 返回 200，根目录索引返回 200，证明未来可作为 `static.l-one.asia` 的临时素材承载入口。
- 2026-06-01：修复 Works 页面新增作品展示问题：分类筛选已接入真实 `data-filter` / `data-work-type` 交互，三篇新增作品恢复为完整信息卡片，四个作品详情页中文 UI 乱码已清理，并保留横向相册与图片预览功能。
- 2026-06-01：批量归档 3 条小红书图文作品：《油画院 | 东五环的安静角落》《白塔寺 | 夜晚的北京胡同》《顺义“小镰仓”？ | 劝慎来，但有惊喜》；每篇作品独立存储 metadata、封面和图片组，并接入 Works 页面与独立详情页路由。
- 2026-06-01：新增 `assets/works/index.json` 作为作品总索引，统一记录每篇作品的 ID、slug、标题、封面、metadata 路径和图片数量，避免后续批量调用时混淆。
- 2026-06-01：搭建腾讯云轻量服务器临时素材仓库，Nginx 指向 `/www/l-one-static`，公网健康检查 `http://62.234.73.162/health.txt` 已通过。
- 2026-06-01：首钢园图片从外部防盗链地址改为站内静态资源路径，并提交 `assets/works/shougang/image-01.webp` 至 `image-18.webp`。
- 2026-05-31：新增第一条作品详情页 `#work-shougang`，接入《首钢园｜永定河畔的微凉惬意》。
- 2026-05-29：腾讯云 EdgeOne Pages 预览部署成功。

## 下一步建议

1. 进入腾讯云 EdgeOne 项目控制台，确认最新部署提交是否为 `692ad95`；如果不是，点“重新部署”。
2. 新作品若只是少量图片，可先走 GitHub + EdgeOne；若素材较多，优先测试上传到轻量服务器素材仓库。
3. 备案通过后绑定 `l-one.asia` 和 `static.l-one.asia`。
4. 素材量超过轻量服务器适合范围后，迁移到腾讯云 COS/对象存储。
