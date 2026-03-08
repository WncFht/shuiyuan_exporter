# shuiyuan_exporter

这个项目用于把上海交通大学饮水思源论坛（Shuiyuan Forum）的帖子导出为本地 Markdown 文档，并尽量把图片、附件、音频、视频链接补全到可访问或可离线保存的形式。

## 项目现在是怎么工作的

导出主流程现在已经收敛到 `shuiyuan_cache/export/` 包内，大致分成 5 步：

1. `raw_markdown.py` 优先从 `cache/raw/topics/<topic_id>/pages/raw/` 读取整帖原始 Markdown，缺失时才补抓。
2. `shuiyuan_cache/export/image_handler.py` 优先复用 `cache/media/images/` 中的图片，并把 `upload://...` 替换成 `./images/...`。
3. `shuiyuan_cache/export/attachments_handler.py` 把附件链接替换成论坛上的真实 URL。
4. `shuiyuan_cache/export/video_handler.py` 把视频链接替换成真实 URL。
5. `shuiyuan_cache/export/audio_handler.py` 把音频链接替换成真实 URL。

当前推荐的导出 CLI 是 `shuiyuan_cache/cli/export_cli.py`；根目录 `main.py` 仅保留为兼容入口。

它依赖的核心接口形态大概是：

- `https://shuiyuan.sjtu.edu.cn/t/topic/<topic_id>.json`
- `https://shuiyuan.sjtu.edu.cn/t/<topic_id>.json?page=<page_no>`
- `https://shuiyuan.sjtu.edu.cn/raw/<topic_id>?page=<page_no>`
- `https://shuiyuan.sjtu.edu.cn/raw/<topic_id>/<post_number>`

认证方式非常简单：直接带浏览器里的 `Cookie` 请求论坛页面，不走账号密码登录流程。

这点对后续做 skill 很重要：如果你后面想做“访问 shuiyuan 并抓取帖子”的 skill，可以直接复用这里的请求方式和帖子解析流程，不一定要复用 CLI 交互。

## 环境要求

- macOS / Linux / Windows
- Python 3.12（当前仓库按 3.12 使用）
- `uv`

## 用 `uv` 管理依赖

这个仓库已经改成 `uv` 项目了，推荐直接这样用。

### 1. 安装 `uv`

如果你是 mac，可以直接：

```bash
brew install uv
```

### 2. 进入项目目录

```bash
cd /Users/fanghaotian/Desktop/src/shuiyuan_exporter
```

### 3. 准备 Python 和虚拟环境

```bash
uv python install 3.12
uv sync
```

执行后会创建：

- `.venv/`：虚拟环境
- `uv.lock`：锁文件

## 准备 Cookie

脚本需要登录后的论坛 Cookie。

### 获取方式

1. 用浏览器打开饮水思源并确保你已经登录。
2. 打开开发者工具（通常按 `F12`）。
3. 在 `Network` 面板随便点开一个请求。
4. 找到请求头里的 `Cookie`。
5. 把完整 Cookie 字符串复制出来。

### 保存方式

在项目根目录创建 `cookies.txt`，内容就是完整 Cookie，一行即可：

```text
_cookie_name=value; another_cookie=value; ...
```

脚本启动后也可以直接粘贴 Cookie；如果想复用 `cookies.txt` 里上一次保存的结果，输入 `!!!` 即可。

## 推荐认证方式：独立浏览器 profile + `auth.json`

如果你后面准备长期做本地缓存、批量抓取或者 skill，推荐不要手工复制 Cookie，而是使用项目内置的认证管理命令：

```bash
uv run python -m shuiyuan_cache.cli.auth_cli setup
```

默认行为：

- 会启动一个**独立的 Edge 浏览器 profile**（不会直接动你平时日常使用的浏览器配置）
- 你在打开的窗口里手动登录饮水思源
- 回到终端按一次回车
- 项目会自动保存：
  - `cache/auth/browser_profile/`：独立浏览器 profile
  - `cache/auth/auth.json`：Playwright `storageState`
  - `cookies.txt`：导出的当前可复用 Cookie

你也可以查看当前认证状态：

```bash
uv run python -m shuiyuan_cache.cli.auth_cli status
```

如果后面只是想基于同一个 profile 重新导出最新登录态：

```bash
uv run python -m shuiyuan_cache.cli.auth_cli refresh
```

说明：

- 在 mac 上默认使用已安装的 **Microsoft Edge** 作为自动化浏览器
- 如果你不想用 Edge，也可以改成：

```bash
uv run python -m shuiyuan_cache.cli.auth_cli setup --browser chromium
```

- `sync_cli` 现在会优先读取 `cache/auth/auth.json` 中保存的 Cookie；只有没有可用登录态时，才回退到 `cookies.txt`

## 推荐工作流（当前实现）

如果你后面准备把这套东西继续发展成 skill，当前最推荐的实际使用顺序是：

```text
auth -> sync -> query/summary -> export
```

也就是：

1. 先用 `auth_cli` 建立长期可复用登录态；
2. 再用 `sync_cli` 把 topic 同步到本地缓存；
3. 优先用 `query_cli` / `summary_cli` 在本地分析；
4. 最后按需用 `export_cli` 生成 Markdown。

相比直接“每次导出都重新联网抓”，这更适合后续做批量分析和 skill。

## 快速开始

### 交互模式

```bash
uv run python -m shuiyuan_cache.cli.export_cli
```

然后按提示：

1. 输入 Cookie，或者输入 `!!!` 使用 `cookies.txt` 中已有的 Cookie
2. 输入帖子编号，例如 `75214`

例如这个帖子：

```text
https://shuiyuan.sjtu.edu.cn/t/topic/75214
```

你只需要输入：

```text
75214
```

### 非交互批量模式

如果你已经把 Cookie 放进 `cookies.txt`，最方便的是直接：

```bash
uv run python -m shuiyuan_cache.cli.export_cli -n -b 75214
```

其中：

- `-n`：不再询问 Cookie，直接使用 `cookies.txt`
- `-b`：批量导出后面的一个或多个帖子编号

多个帖子：

```bash
uv run python -m shuiyuan_cache.cli.export_cli -n -b 75214 276006 123456
```

## 开发校验

如果你也会继续维护这个仓库，建议把 `pre-commit` 打开：

```bash
uv sync --group dev
uv run pre-commit install
uv run pre-commit run --all-files
```

当前配置会做这些事：

- 基础文件检查：YAML / TOML / merge conflict / 大文件 / 末尾空白
- Python 自动升级：`pyupgrade --py312-plus`
- Python 静态检查与自动修复：`ruff --fix`
- Python 格式化：`ruff format`

这些 hook 主要覆盖：

- `shuiyuan_cache/`
- `main.py`
- `test.py`

`cache/`、`posts/`、`.venv/` 不会进入 hook 主流程。

## 常用命令

### 查看帮助

```bash
uv run python -m shuiyuan_cache.cli.export_cli --help
```

### 交互式选择内置列表

```bash
uv run python -m shuiyuan_cache.cli.export_cli -l
```

说明：

- 这个模式会弹出终端菜单；在 mac 上请尽量用 Terminal 或 iTerm 运行
- 它同样会使用你当前输入或保存的 Cookie

### 清理无意义的导出结果

如果因为 Cookie 失效导出了登录页，比如出现 `SJTU Single Sign On.md`，可以执行：

```bash
uv run python -m shuiyuan_cache.cli.export_cli -c
```

### 做简单性能统计

```bash
uv run python -m shuiyuan_cache.cli.export_cli -s
```

### 运行辅助测试脚本

```bash
uv run python test.py -t
```

## 输出目录

默认输出到：

```text
./posts/
```

每个帖子会生成一个独立目录，例如：

```text
posts/75214/
```

目录里通常包含：

- 一个导出的 Markdown 文件
- `images/` 图片目录（如果帖子里有图片）

## mac 上我建议你这样跑

如果你现在只是想先跑通整个项目，建议按这个顺序：

```bash
cd /Users/fanghaotian/Desktop/src/shuiyuan_exporter
uv sync
printf '%s\n' '把你的完整Cookie粘到这里' > cookies.txt
uv run python -m shuiyuan_cache.cli.export_cli -n -b 75214
```

如果能在 `posts/75214/` 下看到 Markdown 和图片目录，就说明整个流程已经跑通了。

## 常见问题

### 为什么一定要 Cookie？

因为论坛内容访问依赖登录态；没有 Cookie，脚本拿到的很可能只是登录页或者不完整内容。

### Cookie 怎么看是不是失效了？

如果导出的文件名类似 `SJTU Single Sign On.md`，通常就是 Cookie 过期了。更新 `cookies.txt` 后重新运行即可。

### 这个脚本快吗？

原 README 中提到，拉取一个约 3800 帖子、100MB 图片的主题大约需要 10 秒；实际速度还是取决于网络、Cookie 状态、论坛限流和本地磁盘写入。

### 会不会请求太频繁？

有这个可能。项目已经通过分页和缓存减少了一部分请求，但大帖子的请求量仍然不小，批量抓取时要注意节奏。

### 为什么不直接输入 jAccount 账号密码？

原作者明确考虑过这个方向，但通常会引入 Selenium 或其他浏览器自动化依赖，整体复杂度会明显上升，所以当前方案选择直接复用浏览器 Cookie。

## 对后续做 skill 的启发

如果你后面要做一个“抓取 Shuiyuan 帖子”的 skill，我建议优先拆下面这几层：

1. **认证层**：读取并注入 Cookie。
2. **帖子元数据层**：拿到标题、页数、`posts_count`。
3. **原始内容层**：抓 `raw` Markdown。
4. **媒体解析层**：根据 `cooked` HTML 把图片/附件/音视频补成真实链接。
5. **输出层**：决定是保存为 Markdown、返回 JSON，还是写进 notebook / note。

当前仓库最值得复用的模块是：

- `shuiyuan_cache/fetch/`
- `shuiyuan_cache/sync/`
- `shuiyuan_cache/analysis/`
- `shuiyuan_cache/export/raw_markdown.py`
- `shuiyuan_cache/export/topic_exporter.py`
- `shuiyuan_cache/export/media_rewrite.py`
- `shuiyuan_cache/export/compat.py`

## 兼容旧方式

如果你暂时还想沿用旧方式，`requirements.txt` 仍然保留；但后续建议优先使用 `uv sync` 和 `uv run ...`。


兼容说明：如果你确实还想沿用旧命令，`uv run python main.py ...` 仍然可用，但推荐优先使用 `uv run python -m shuiyuan_cache.cli.export_cli ...`。
