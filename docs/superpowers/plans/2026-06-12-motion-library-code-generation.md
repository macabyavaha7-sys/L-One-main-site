# Motion Library Code Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 64 个文字动效重建为结构化数据驱动、独立命名空间、支持两种网页复制版本的代码库。

**Architecture:** 使用一次性迁移脚本从现有页面提取每个效果的结构、专属规则和关键帧，写入 JSON 数据；使用生成器从 JSON 更新页面代码区。独立审查脚本验证数量、命名空间、依赖隔离和输出完整性。

**Tech Stack:** 静态 HTML、CSS、JavaScript、Node.js 标准库。

---

### Task 1: 建立失败审查

- [ ] 创建 `scripts/audit-motion-library.js`
- [ ] 验证当前页面因重复总样式而失败

### Task 2: 建立结构化数据

- [ ] 创建迁移脚本提取 64 个效果
- [ ] 写入 `motion-library-data.json`
- [ ] 验证扫描线只保留自身规则和关键帧

### Task 3: 建立统一生成器

- [ ] 创建 `scripts/build-motion-library.js`
- [ ] 为每项生成独立 HTML 和嵌入组件
- [ ] 批量更新 64 个卡片代码区

### Task 4: 更新页面交互

- [ ] 增加代码版本切换按钮
- [ ] 复制当前选中版本
- [ ] 保留删除、恢复和计数效果

### Task 5: 验证

- [ ] 运行 Motion Library 审查
- [ ] 运行主站审查
- [ ] 浏览器检查桌面和移动端
- [ ] 更新 `SITE_STATUS.md`

