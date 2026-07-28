# L-One 主站 AI 协作规则

本文件适用于 Codex、Claude Code、Cursor 及其他自动化编码工具。仓库以 GitHub
`macabyavaha7-sys/L-One-main-site` 为唯一中央版本，生产分支为 `main`。

## 开始任务前

1. 依次完整阅读本文件、`TASK_GUARDRAILS.md`、`SITE_STATUS.md`、
   `docs/MULTI_DEVICE_WORKFLOW.md`、`docs/EDIT_SCOPE_MAP.md`、
   `docs/CURRENT_HANDOFF.md` 和 `docs/VERSIONING_RULES.md`。
2. 执行 `git status --short --branch`。工作区不干净时先确认变更来源，不得覆盖。
3. 执行 `git fetch --all --prune` 和 `git pull --ff-only origin main`。
4. 查看最近 10 次提交并记录任务开始时的完整 commit ID。
5. 按 `docs/EDIT_SCOPE_MAP.md` 声明任务编号、设备、目标、允许修改文件、
   只读文件、禁止修改文件、影响范围、测试与回滚方式。
6. 未列入“允许修改”的文件一律只读。需要扩围时先停止并取得用户确认。

## 修改规则

- 只修改本轮明确授权的文件和代码区域，保留原编码、换行、目录及命名风格。
- 不进行全项目格式化、编码或换行转换、文件重命名、目录迁移、依赖升级、
  清理或无关重构。
- 登录认证、秘密和令牌、权限、数据库迁移、管理 API、生产环境变量、
  腾讯云部署、域名及仓库权限属于受保护区域，必须得到用户明确授权。
- `.git/`、真实秘密文件、生产数据库、服务器数据与备份禁止自动修改。
- 不把密码、Token、SSH 私钥、云密钥或预览链接中的秘密写入仓库、日志和页面。
- 不使用 `git reset --hard`、`git clean -fd`、`git clean -fdx`、
  `git push --force`、`git push --force-with-lease`、`git rebase --onto`、
  `git filter-branch` 或 `git filter-repo`。
- 发生冲突时停止自动处理，报告冲突文件、位置、两端差异、影响和建议方案。

## 验证与提交

1. 运行与任务相符的测试，至少运行 `node scripts/site-audit.js`；后端变更还要运行
   对应的 Python 测试。确认关键页面可打开且控制台无新增错误。
2. 依次检查 `git diff`、`git status --short`、敏感信息和任务外文件。
3. 仅用 `git add <明确路径>` 或 `git add -p` 精确暂存；禁止 `git add .` 和
   `git add -A`。
4. 检查 `git diff --cached`，确认提交只包含本轮授权内容。
5. 推送前执行 `git fetch origin`，检查 `git log --oneline HEAD..origin/main`
   和工作区状态。远程前进时停止直接推送，安全同步并重新测试。
6. 推送后核对 GitHub commit、EdgeOne 部署 commit、正式域名和关键页面。
7. 完成前更新 `docs/CURRENT_HANDOFF.md`；无法访问腾讯云控制台时必须明确标记
   “未验证”，不得声称部署成功。

异常回滚优先使用 `git revert <commit>` 创建可审计的新提交，禁止重写历史。
