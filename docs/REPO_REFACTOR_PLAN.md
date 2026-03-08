# 仓库重构计划

## 目标

把仓库收敛为：

- `shuiyuan_cache/` 作为唯一主包
- 根目录只保留少量项目入口和元信息
- 认证、同步、分析、导出、后续 skill 都围绕同一套包内能力构建

## 当前状态

当前已经完成两轮收口：

1. 旧导出链路已经迁入 `shuiyuan_cache/export/`
2. 根目录大部分历史脚本文件已经删除
3. 根目录只保留 `main.py` 作为兼容入口
4. 认证已经统一为：优先 `cache/auth/auth.json`，回退 `cookies.txt`

## 已完成内容

### 第一轮

- 新建 `shuiyuan_cache/export/`
- 将旧导出链路搬入包内
- 新增 `shuiyuan_cache/cli/export_cli.py`
- 保留根目录兼容入口

### 第二轮

- 将导出大脚本继续拆分为：
  - `shuiyuan_cache/export/raw_markdown.py`
  - `shuiyuan_cache/export/media_rewrite.py`
  - `shuiyuan_cache/export/topic_exporter.py`
  - `shuiyuan_cache/export/export_models.py`
  - `shuiyuan_cache/export/cli_support.py`
- `shuiyuan_cache/export/legacy_export.py` 变为薄入口
- 删除根目录无必要的旧兼容文件：
  - `utils.py`
  - `constant.py`
  - `image_handler.py`
  - `attachments_handler.py`
  - `audio_handler.py`
  - `video_handler.py`
  - `quality_list.py`

## 现在的推荐用法

- 同步缓存：`uv run python -m shuiyuan_cache.cli.sync_cli ...`
- 查询缓存：`uv run python -m shuiyuan_cache.cli.query_cli ...`
- 摘要分析：`uv run python -m shuiyuan_cache.cli.summary_cli ...`
- 导出 Markdown：`uv run python -m shuiyuan_cache.cli.export_cli ...`
- 认证管理：`uv run python -m shuiyuan_cache.cli.auth_cli ...`

`main.py` 仍然保留，但仅作为兼容入口。

## 下一步建议

### Phase B：导出优先复用缓存层

目标：减少导出阶段的重复网络抓取。

建议策略：

- 优先从 `cache/raw/topics/<topic_id>/` 读取已同步内容
- 仅在本地缺失时再补抓网络
- 明确区分：
  - `sync_cli` 负责更新缓存
  - `export_cli` 负责把缓存转换成阅读产物

### Phase C：面向 skill 的结构化导出

目标：导出不再只面向 Markdown，而是面向后续 LLM / skill 使用。

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

1. 导出优先复用缓存层
2. 设计 skill 接口
3. 结构化导出格式
4. 再考虑是否统一总包名
