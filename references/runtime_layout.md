# Runtime Layout

skill 仓库本身应尽量保持“只放代码与文档”，运行时数据默认放在独立目录中。

## 1. 默认根目录

默认 runtime 根目录：

```text
~/.local/share/shuiyuan-cache-skill/
```

默认派生路径：

```text
~/.local/share/shuiyuan-cache-skill/
  cache/
  exports/
  cookies.txt
```

## 2. 路径覆盖优先级

优先级从高到低：

1. CLI 参数，例如 `--cache-root`、`--cookie-path`、`--export-root`
2. 环境变量
3. 内置默认值

支持的环境变量：

- `SHUIYUAN_SKILL_HOME`
- `SHUIYUAN_CACHE_ROOT`
- `SHUIYUAN_COOKIE_PATH`
- `SHUIYUAN_EXPORT_ROOT`

## 3. 认证存储位置

主认证文件：

```text
~/.local/share/shuiyuan-cache-skill/cache/auth/auth.json
```

独立浏览器 profile：

```text
~/.local/share/shuiyuan-cache-skill/cache/auth/browser_profile/
```

回退 cookie 文件：

```text
~/.local/share/shuiyuan-cache-skill/cookies.txt
```

注意：`cookies.txt` 保存的是一整条 HTTP `Cookie` header 字符串，不是 Netscape cookie-jar 文件。

运行时认证优先级：

1. 先读 `cache/auth/auth.json`
2. 如果没有可用登录态，再回退到 `cookies.txt`

实际含义：

- `auth.json` 是主认证产物
- `browser_profile/` 用于后续刷新 `auth.json`
- `cookies.txt` 只是兼容和回退手段

## 4. 缓存目录结构

默认 cache 根目录：

```text
~/.local/share/shuiyuan-cache-skill/cache/
```

当前推荐理解成两层：

- `raw/topics/`：真正的 topic 级同步产物
- `raw/post_refs/`：导出 / 引用解析阶段按需抓取的单帖 raw 缓存

完整示意：

```text
cache/
  auth/
    auth.json
    browser_profile/
  db/
    shuiyuan.sqlite
  media/
    images/
      <bucket>/
        <media_key>.<ext>
  raw/
    topics/
      <topic_id>/
        topic.json
        sync_state.json
        pages/
          json/
            0001.json
            0002.json
          raw/
            0001.md
            0002.md
    post_refs/
      <topic_id>/
        000001.raw.md
        000169.raw.md
```

各部分含义：

- `db/shuiyuan.sqlite`：供 inspect / query / summarize 使用的结构化数据库
- `raw/topics/<topic_id>/topic.json`：topic 级元数据
- `raw/topics/<topic_id>/sync_state.json`：同步状态与高水位
- `raw/topics/<topic_id>/pages/json/*.json`：分页 JSON 响应缓存
- `raw/topics/<topic_id>/pages/raw/*.md`：分页 raw markdown 缓存
- `raw/post_refs/<topic_id>/*.raw.md`：按需抓取的单帖 raw，常由引用解析、附件/音视频重写触发
- `media/images/<bucket>/...`：跨 topic 共享的去重图片缓存

### 为什么现在这样更合理

你之前看到的这类目录：

```text
cache/raw/topics/22338/
  posts/013781.raw.md
```

之所以会让人觉得“脏”，是因为它看起来像一个 topic 已经同步了一半，但实际上它只是导出时为了取某一楼的原始 raw 而临时补抓的结果。

现在这些单帖缓存已经被明确迁到：

```text
cache/raw/post_refs/<topic_id>/
```

所以：

- `raw/topics/` 只保留真正的 topic 同步结构
- `raw/post_refs/` 单独承接引用楼层缓存

## 5. 导出目录结构

默认导出根目录：

```text
~/.local/share/shuiyuan-cache-skill/exports/
```

正常结构：

```text
exports/
  <topic_id>/
    <topic_id> <title>.md
    images/
      <image-file>
      <image-file>
```

例如：

```text
exports/
  456491/
    456491 AI “养龙虾” 走红，官方提示：警惕Openclaw安全风险.md
    images/
  187803/
    187803 A股每日复盘.md
    images/
```

当前行为说明：

- 每个 topic 一个目录
- 主 Markdown 文件直接放在该目录下
- 图片导出到 `<topic_id>/images/`
- 附件、视频、音频当前主要仍是重写为远程链接，而不是全部本地化复制

## 6. 为什么 `exports/` 里会有奇怪目录

如果你看到：

```text
exports/https:/shuiyuan.sjtu.edu.cn/t/topic/187803/
```

这不是当前预期结构，而是旧版本 URL 归一化 bug 留下的历史目录。

原因是：

- 以前导出时，完整 URL 曾经被直接当成目录名使用
- 现在这个问题已经修复
- 新导出应进入 `exports/<topic_id>/`

也就是说：

- `exports/187803/` 是正常目录
- `exports/https:/...` 是历史遗留目录

## 7. 清理建议

通常应该保留：

- `cache/auth/auth.json`
- `cache/auth/browser_profile/`
- `cache/db/shuiyuan.sqlite`
- `cache/raw/topics/`
- `cache/raw/post_refs/`
- `cache/media/images/`

通常可以清理：

- `exports/https:/...` 这样的 URL 形目录
- 中途中断后留下的半成品导出目录
- 不再需要的单个 `exports/<topic_id>/`

注意：

- 删除 `exports/<topic_id>/` 不会删除原始缓存
- 删除后可以随时重新导出
