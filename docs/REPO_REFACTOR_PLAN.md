# 仓库重构计划

## 目标

把当前仓库从“根目录脚本 + `shuiyuan_cache` 新内核并存”的过渡态，逐步收敛为：

- `shuiyuan_cache/` 作为主包
- 根目录只保留兼容入口和项目元信息
- 后续 skill、同步、分析、导出都围绕同一套认证 / 抓取 / 存储能力构建

## 当前状态

目前仓库有两套能力：

1. **旧导出链路**
   - 根目录 `main.py`
   - 根目录 `utils.py`
   - 根目录 `image_handler.py` / `attachments_handler.py` / `audio_handler.py` / `video_handler.py`
   - 目标是把帖子导出为 Markdown，并补全图片、附件、音视频

2. **新缓存分析链路**
   - `shuiyuan_cache/`
   - 已有认证、同步、SQLite 缓存、inspect/query/summary
   - 目标是支持增量同步、本地缓存和后续 skill

## 本轮已完成

第一轮重构已经完成以下工作：

- 新建 `shuiyuan_cache/export/`
- 将旧导出链路迁入包内：
  - `shuiyuan_cache/export/legacy_export.py`
  - `shuiyuan_cache/export/compat.py`
  - `shuiyuan_cache/export/constants.py`
  - `shuiyuan_cache/export/image_handler.py`
  - `shuiyuan_cache/export/attachments_handler.py`
  - `shuiyuan_cache/export/audio_handler.py`
  - `shuiyuan_cache/export/video_handler.py`
  - `shuiyuan_cache/export/quality_list.py`
- 新增包内 CLI：
  - `shuiyuan_cache/cli/export_cli.py`
- 根目录旧文件改成兼容转发层：
  - `main.py`
  - `utils.py`
  - `constant.py`
  - `image_handler.py`
  - `attachments_handler.py`
  - `audio_handler.py`
  - `video_handler.py`
  - `quality_list.py`
- 旧导出链路的认证已统一改为：
  - 优先 `cache/auth/auth.json`
  - 回退 `cookies.txt`

## 为什么这样做

这样做有几个好处：

- **不破坏现有使用方式**：`uv run python main.py ...` 仍然可用
- **代码主线归拢到包内**：后续继续演进时，不用再维护两套散落逻辑
- **认证统一**：旧导出和新同步都能复用同一套 profile / storage state
- **为后续 skill 做准备**：导出能力已经成为包内模块，可以继续服务化、结构化

## 下一步建议

### Phase A：导出层去脚本化

目标：把 `legacy_export.py` 从“大脚本”继续拆成服务层。

建议拆成：

- `shuiyuan_cache/export/topic_exporter.py`
  - 统一导出入口
- `shuiyuan_cache/export/raw_markdown.py`
  - 拉取 raw 页面并拼接 Markdown
- `shuiyuan_cache/export/media_rewrite.py`
  - 图片、附件、音视频链接替换
- `shuiyuan_cache/export/export_models.py`
  - 导出阶段的数据结构

### Phase B：导出层接入缓存层

目标：减少旧导出链路里对论坛的重复抓取，优先复用本地缓存。

建议策略：

- 优先从 `cache/raw/topics/<topic_id>/` 读取已同步内容
- 仅当本地缺失时，再补抓网络数据
- 导出与同步彻底解耦：
  - `sync_cli` 负责更新缓存
  - `export_cli` 负责把缓存转换成可阅读产物

### Phase C：面向 skill 的结构化导出

目标：从 Markdown 导出进一步升级为“适合检索和分析的结构化格式”。

建议优先支持：

- topic-level JSON 包
- post-level JSONL
- 每个 post 带：
  - 文本
  - 作者
  - 时间
  - 图片路径
  - 引用关系
  - 附件 / 音视频 URL

## 近期优先顺序

建议接下来按这个顺序做：

1. 导出层去脚本化
2. 导出优先复用缓存层
3. 设计 skill 接口
4. 再考虑是否给项目改总包名

## 关于总包名

当前先保留 `shuiyuan_cache` 这个名字是合理的。

原因：

- 现在最成熟、最稳定的能力确实是“本地缓存 + 同步 + 查询”
- 如果现在马上改成 `shuiyuan`，改动面会很大
- 更合适的时机是：导出层和 skill 接口也稳定后，再决定是否统一命名
