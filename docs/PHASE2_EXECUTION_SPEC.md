# Phase 2 执行规格（待批准后实施）

版本：`v0.1`  
状态：执行前冻结稿  
依赖文档：`docs/PHASE2_QUERY_ANALYSIS_DESIGN.md`

## 1. 执行目标

Phase 2 只做一件事：

> **把当前的“可同步缓存”系统，推进成“可在本地查、可检查状态、可做基础摘要”的系统。**

---

## 2. 本阶段交付物

本阶段交付物建议限定为：

1. `inspect` 服务
2. `query` 服务
3. `summary` 基础服务
4. `inspect_cli`
5. `query_cli`
6. `summary_cli`
7. 必要的 SQLite 索引补强
8. 相关文档更新

---

## 3. 本阶段不交付

为了控制范围，本阶段不交付：

- OCR
- related topics 远端联动
- 复杂长报告输出
- 图像理解
- 多 topic 聚合
- 旧 `main.py` 的重构替换

---

## 4. 任务拆分建议

建议拆成以下小步：

### Step 1：Inspect 能力

内容：

- 新建 inspect service
- 汇总 topic、sync_state、raw 页面、json 页面、media 数量
- 增加 `inspect_cli`

完成标准：

- 对一个已同步 topic 能看到完整状态

### Step 2：查询底座

内容：

- 封装 posts 查询 SQL
- 接入 FTS keyword 查询
- 支持 `author / only_op / date / has_images`

完成标准：

- 能稳定查出楼层列表

### Step 3：图片上下文拼装

内容：

- 联表 `media`
- 为 query item 附上图片路径
- 增加结果截断策略

完成标准：

- 带图帖子能返回可用图片路径

### Step 4：基础摘要

内容：

- 汇总统计
- 关键楼层抽取
- 生成结构化摘要对象
- 增加 `summary_cli`

完成标准：

- 能给出 topic 的本地基础摘要

### Step 5：真实 topic 验证

内容：

- 使用已同步 topic 验证 inspect/query/summary
- 至少验证一个短帖、一个长帖、一个带图帖

完成标准：

- 不联网情况下也能完成查询和摘要

---

## 5. 建议的 Git 拆分

建议至少拆成以下提交：

1. `Add topic inspect service and CLI`
2. `Add local post query service with FTS filters`
3. `Attach image context to topic query results`
4. `Add basic topic summary service and CLI`
5. `Update docs for phase-2 query and analysis flow`

这样每一步都更容易回滚和 review。

---

## 6. 验证清单

### 6.1 Inspect

- `inspect_cli` 能正确识别 topic 是否已同步
- 能识别 `topic.json` / `sync_state.json` 是否存在
- 能统计 raw/json 页数

### 6.2 Query

- `--keyword`
- `--author`
- `--only-op`
- `--date-from --date-to`
- `--has-images`
- `--limit`

这些组合都至少要做一次验证。

### 6.3 Summary

- 全 topic 摘要
- `only_op` 摘要
- `recent_days` 摘要

---

## 7. 冻结点

在你批准之前，本阶段只允许：

- 写文档
- 调整任务拆分
- 明确接口契约

不开始实际 Phase 2 代码实现。

---

## 8. 一句话总结

Phase 2 的执行重点是：

> **先把“本地缓存已经可查可看可概览”这条链路打通，再继续更复杂的分析和 skill 封装。**
