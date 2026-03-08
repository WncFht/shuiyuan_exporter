# Phase 1 执行规格（实施前冻结稿）

版本：`v0.1`  
状态：历史执行规格稿（主链路已实现，当前运行请优先参考 `docs/RUNBOOK.md`）  
依赖文档：`TECHNICAL_PLAN.md`、`docs/SYSTEM_DESIGN.md`、`docs/SCHEMA_AND_API.md`

## 1. 目标

Phase 1 的唯一目标是：

> **把当前“导出脚本”迈出的第一步，变成“可持久缓存 topic 原始数据并建立本地索引”的系统雏形。**

换句话说，Phase 1 不是要一次性做完全部分析能力，而是先把“缓存与同步底座”打牢。

---

## 2. 本阶段必做

本阶段必须完成：

1. 新建独立的缓存子模块，不破坏现有导出器用法
2. 能同步单个 topic 的 `topic.json`
3. 能同步单个 topic 的分页 `json` 与 `raw`
4. 能将原始页面稳定落盘
5. 能初始化 SQLite
6. 能把 topic / post 基础信息写入 SQLite
7. 能记录 `sync_state`
8. 能提供最小可用 CLI：`sync_cli`
9. 能在后续为图片处理预留接口

---

## 3. 本阶段不做

本阶段不做：

- 大规模目录迁移
- 替换现有 `main.py`
- 完整 related topics 逻辑
- 完整 summary 逻辑
- OCR
- 向量检索
- 多 topic 并发复杂调度

---

## 4. 实现策略

### 4.1 与现有导出器共存

Phase 1 代码必须遵循：

- 不破坏当前 `main.py` 的导出功能
- 不影响当前 `uv run python main.py ...` 用法
- 新能力以新模块和新 CLI 形式落地

### 4.2 优先建设“可重建”的原始缓存

即使某些 post 字段还不完整，也必须优先保证：

- 原始页面数据已落盘
- 后续可以基于原始页面重建结构化数据

### 4.3 优先让 SQLite 可查询

哪怕第一阶段查询能力还简单，也要优先让 topic/post 能在数据库中稳定存在。

---

## 5. 最小目录变更

Phase 1 允许新增：

```text
docs/
shuiyuan_cache/
```

其中 `shuiyuan_cache/` 第一阶段建议至少包含：

```text
shuiyuan_cache/
  __init__.py
  core/
  fetch/
  store/
  cli/
```

Phase 1 不要求一次把 `normalize/analysis/render/skill` 全建完，但目录预留是允许的。

---

## 6. 最小 CLI 规格

第一阶段只要求完成一个命令：

```bash
uv run python -m shuiyuan_cache.cli.sync_cli 351551
```

支持参数建议：

- `--mode full|incremental|refresh-tail`
- `--cache-root <path>`
- `--cookie-path <path>`
- `--no-images`

预期输出至少包括：

- 正在同步的 topic id
- title
- 抓取页数
- 写入 post 数
- 状态（success / partial / failed）

---

## 7. 数据写入要求

### 7.1 文件系统

必须落盘：

- `topic.json`
- `pages/json/*.json`
- `pages/raw/*.md`
- `sync_state.json`

### 7.2 SQLite

至少写入：

- `topics`
- `posts`
- `sync_state`

`media` 可以先建表并预留写入接口，但如果图片下载要放到下一个小步提交，也可以接受。

---

## 8. 验证要求

Phase 1 完成后，至少要能验证：

1. 一个 topic 首次同步成功
2. 再次同步同一 topic 不会完全重复抓取
3. SQLite 中能看到 topic 和 post
4. 本地文件缓存路径符合约定
5. `sync_state.json` 与数据库状态一致或基本一致

---

## 9. Git 执行要求

本阶段代码建议至少拆成 2~4 个提交：

1. `Add cache schema and interface docs`
2. `Add cache foundation package and path/session helpers`
3. `Add topic sync flow with raw/json file cache`
4. `Persist synced topic and posts into SQLite`

如果实现过程中发现边界变化，必须同步修正文档再提交。

---

## 10. 开始实现的判断标准

只有当下面这些问题已经明确后，才建议真正开始写 Phase 1 代码：

- 接受 `shuiyuan_cache/` 作为新模块根目录
- 接受 `SQLite + 文件缓存`
- 接受 `Markdown` 不再作为主存储
- 接受先做 topic/post 级缓存，再逐步补图片和分析

---

## 11. 一句话总结

Phase 1 不是要“把新系统全部做完”，而是要先完成：

> **能把 topic 可靠地同步到本地，并且为之后的检索、分析、图片理解、skill 封装打下稳定底座。**
