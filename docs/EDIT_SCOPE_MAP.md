# L-One 主站编辑范围地图

本地图依据仓库在 `8e88ca41ad5c7b584a742e8c6dc26bc3420d721c`
的真实结构编制。具体任务仍须进一步缩小到明确文件和代码区域。

| 区域 | 真实路径 | 内容 | 默认保护级别 |
| --- | --- | --- | --- |
| 主站页面 | `index.html` | 首页、Works、Notes、About、路由及内嵌样式/脚本 | 谨慎编辑 |
| 动效图书馆 | `motion-library.html`、`motion-library.css`、`motion-library.js`、`motion-library-data.json` | 独立页面、样式、交互和数据 | 谨慎编辑 |
| 素材库前端 | `materials/` | 素材页面、样式、脚本、公开地址配置和清单 | 谨慎编辑；`config.json` 受保护 |
| 作品数据 | `assets/works/index.json`、`assets/works/*/metadata.json` | 作品索引与结构化正文 | 谨慎编辑 |
| 媒体资产 | `assets/`、`assets/works/*/*.{jpg,webp,png}` | 背景、封面和作品图片 | 禁止自动批量修改 |
| 静态构建/审计 | `scripts/` | Motion Library 生成、迁移和全站审计 | 谨慎编辑 |
| 后端业务 | `server/materials-service/app/` | FastAPI、认证、内容、数据库、任务队列和管理页 | 受保护 |
| 数据与迁移 | `server/materials-service/app/database.py`、`migrations.py`、内容仓库代码及生产数据 | SQLite 模型、迁移和发布数据 | 受保护；生产数据禁止自动修改 |
| 部署 | `server/materials-service/nginx/`、`systemd/`、服务器实际配置、EdgeOne、DNS | Nginx、systemd、HTTPS 和部署 | 受保护 |
| 测试 | `server/materials-service/tests/`、`scripts/*audit*` | 后端与静态站审计 | 普通编辑，但须与任务绑定 |
| 文档 | `README.md`、`SITE_STATUS.md`、`TASK_GUARDRAILS.md`、`docs/` | 状态、设计、计划和协作记录 | 普通或谨慎编辑 |
| Git 与秘密 | `.git/`、凭据、Token、私钥、生产环境变量 | 历史与访问权限 | 禁止自动修改/入库 |

保护等级定义：

- **普通编辑**：用户明确提出任务后可以编辑。
- **谨慎编辑**：编辑前必须评估依赖、渲染或运行影响。
- **受保护**：必须取得用户对目标和范围的明确授权。
- **禁止自动修改**：AI 不得自行变更。

## 每轮任务声明

```text
任务编号：
执行设备：
任务目标：
允许修改的文件：
允许修改的代码区域：
只读参考文件：
明确禁止修改的文件：
预计影响范围：
测试方式：
回滚方式：
```

未列入“允许修改”的文件默认只读。发现必须扩围时，先停止、列出新增文件和原因，
等待用户确认后再更新任务范围。
## 本轮范围：B-20260728-00

- 执行设备：B
- 目标：建立多设备协作制度并验证最小 Git/部署闭环。
- 允许新增：`AGENTS.md`、`docs/MULTI_DEVICE_WORKFLOW.md`、
  `docs/EDIT_SCOPE_MAP.md`、`docs/CURRENT_HANDOFF.md`、
  `docs/VERSIONING_RULES.md`。
- 只读参考：仓库内其余全部文件和公开网站。
- 禁止修改：所有网站 HTML、CSS、JavaScript、Python、API、数据库、素材、
  依赖、锁定文件、部署和域名配置。
- 可见影响：网站页面、文案、样式和功能应完全不变；只新增协作文档。
- 测试：仓库审计、网站文件哈希不变、静态站审计、后端测试和正式域名抽查。
- 回滚：对本轮单一文档 commit 执行 `git revert`。
