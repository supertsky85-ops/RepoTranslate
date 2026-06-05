# RepoTranslate

深度分析 GitHub 仓库的工具。输入一个 GitHub 地址，自动生成包含技术栈、文档质量、版本演进、项目架构、代码活跃度和贡献者分析的完整报告。

## 快速开始

```bash
# 1. 创建虚拟环境
python -m venv .venv
source .venv/Scripts/activate   # Windows
# source .venv/bin/activate     # macOS / Linux

# 2. 安装依赖
pip install fastapi uvicorn httpx pydantic-settings aiosqlite jinja2 python-multipart

# 3. 配置 GitHub Token（可选但强烈推荐）
# 编辑 .env，填入你的 Token：
#   GITHUB_TOKEN=ghp_xxxxxxxxxxxx
# 不配 Token 只能 60次/小时，配了 5000次/小时

# 4. 启动
uvicorn app.main:app --reload --host 127.0.0.1 --port 9000
```

浏览器打开 `http://127.0.0.1:9000/`，输入 GitHub 仓库地址即可。

---

## 项目架构

```
app/
├── main.py              # FastAPI 入口，应用工厂 + 生命周期管理
├── core/
│   ├── config.py        # 配置管理（pydantic-settings，读取 .env）
│   ├── constants.py     # URL 解析正则、API 常量
│   ├── exceptions.py    # 自定义异常体系
│   └── dependencies.py  # FastAPI 依赖注入
├── models/
│   ├── github.py        # GitHub API 数据模型（RepoInfo 等）
│   ├── analysis.py      # 分析管道模型（AnalysisContext → AnalyzerOutput → AnalysisResult）
│   └── request.py       # 请求模型
├── services/
│   ├── github_client.py # 异步 GitHub API 封装（httpx），8 个 API 方法
│   ├── url_parser.py    # URL 解析与校验（支持 4 种 GitHub URL 格式）
│   ├── token_manager.py # Token 持久化（文件 + 环境变量）
│   └── report_renderer.py # 纯 Python HTML 报告生成器
├── analyzers/           # 分析器插件系统
│   ├── base.py          # BaseAnalyzer 抽象基类（插件契约）
│   ├── registry.py      # AnalyzerRegistry（注册/运行/聚合）
│   ├── basic_stats.py   # 仓库健康度（Stars、活跃度、许可证、成熟度）
│   ├── readme_summary.py # README 深度分析（简介、安装、示例、章节、链接）
│   ├── tech_stack.py    # 技术栈检测（97 种文件 → 技术映射）
│   ├── architecture.py  # 架构推断（10 种模式识别）
│   ├── code_quality.py  # 代码活跃度（提交频率、Issue 解决率）
│   ├── contributors.py  # 贡献者分析（Bus Factor、核心团队）
│   └── roadmap.py       # 版本路线（Release 历史、发布节奏）
├── api/router.py        # REST API（/api/health, /api/repo/validate 等）
└── web/
    ├── router.py        # 页面路由（/、/analyze、/settings）
    ├── templates/       # Jinja2 模板
    └── static/          # CSS + htmx.js
```

### 架构分层

```
┌── 展示层 ─────────────────────────────────────┐
│  Web Router (htmx + Jinja2)  │  API Router (JSON) │
└──────────────────┬───────────────────────────┘
                   │
┌── 服务层 ───────┼───────────────────────────┐
│  url_parser  │  github_client  │  report_renderer │
└──────────────────┬───────────────────────────┘
                   │
┌── 分析器层 ─────┼───────────────────────────┐
│  BaseAnalyzer → 7 个分析器插件               │
│  按 order 属性排序执行，互不依赖               │
└──────────────────┬───────────────────────────┘
                   │
┌── 基础设施层 ───┼───────────────────────────┐
│  GitHub REST API (httpx)                     │
└──────────────────────────────────────────────┘
```

---

## 数据流

一次分析请求的完整数据流：

```
用户输入 URL
    │
    ▼
url_parser.parse()         # 解析 → {owner, repo}
    │
    ▼
github_client.get_repo()   # 获取仓库元数据
    │
    ▼
asyncio.gather (并行请求)
    ├── get_readme()        → ReadmeAnalyzer
    ├── get_languages()     → TechStackAnalyzer
    ├── get_repo_tree()     → TechStack + Architecture
    ├── get_commits()       → CodeQualityAnalyzer
    ├── get_issues()        → CodeQualityAnalyzer
    ├── get_contributors()  → ContributorAnalyzer
    └── get_releases()      → RoadmapAnalyzer
    │
    ▼
registry.run_all(context)   # 7 个分析器依次执行
    │
    ▼
report_renderer.render()    # 生成 HTML 报告
    │
    ▼
返回给浏览器
```

---

## 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| Web 框架 | FastAPI | 异步路由、依赖注入、自动 OpenAPI 文档 |
| ASGI 服务器 | Uvicorn | 生产级异步服务器，支持热重载 |
| HTTP 客户端 | httpx | 异步调用 GitHub REST API，连接池复用 |
| 前端 | htmx + Jinja2 | 无 JS 框架，服务器渲染 HTML 片段 |
| 配置 | pydantic-settings | .env 加载 + 类型校验 |
| 数据模型 | Pydantic v2 | 全链路类型安全（API → 分析 → 渲染） |

---

## 分析器插件系统

新增分析器只需 3 步，无需修改任何现有代码：

```python
# 1. 创建文件 app/analyzers/my_analyzer.py
from app.analyzers.base import BaseAnalyzer
from app.models.analysis import AnalysisContext, AnalyzerOutput

class MyAnalyzer(BaseAnalyzer):
    analyzer_id = "my_analyzer"
    display_name = "我的分析器"
    order = 70  # 执行顺序，越小越先执行

    async def analyze(self, context: AnalysisContext) -> AnalyzerOutput:
        # context 包含所有预取的 GitHub 数据
        # 不要在这里调用 GitHub API
        return AnalyzerOutput(
            analyzer_id=self.analyzer_id,
            display_name=self.display_name,
            summary="分析结果摘要",
            details={"key": "value"},
            recommendations=["改进建议"],
        )

# 2. 在 app/web/router.py 中注册
from app.analyzers.my_analyzer import MyAnalyzer
_analyzer_registry.register(MyAnalyzer())

# 3. 完成！分析器会自动运行并出现在报告中
```

---

## 关键技术实现

### 1. 并行 API 请求

```python
# app/web/router.py
# 使用 asyncio.gather 同时发起 7 个 GitHub API 请求
readme_data, langs, tree, commits, issues, contribs, releases = \
    await asyncio.gather(
        client.get_readme(owner, repo),
        client.get_languages(owner, repo),
        client.get_repo_tree(owner, repo, branch, recursive=True),
        client.get_commits(owner, repo),
        client.get_issues(owner, repo),
        client.get_contributors(owner, repo),
        client.get_releases(owner, repo),
        return_exceptions=True,  # 单个失败不影响其他
    )
```

### 2. URL 解析

```python
# app/services/url_parser.py
# 正则匹配 4 种 GitHub URL 格式
GITHUB_URL_PATTERNS = [
    r"^https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?/?$",
    r"^https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/tree/",
    r"^https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/blob/",
    r"^git@github\.com:(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?$",
]
```

### 3. 技术栈检测

```python
# app/analyzers/tech_stack.py
# 97 种文件名 → 技术映射表
LANG_CONFIGS = {
    "package.json": "Node.js (npm)",
    "requirements.txt": "Python (pip)",
    "Dockerfile": "Docker",
    ".github/workflows": "GitHub Actions",
    # ... 共 97 项
}
# 遍历仓库目录树，匹配已知配置文件
```

### 4. README 深度提取

```python
# app/analyzers/readme_summary.py
# 1. 解码 base64 → Markdown 文本
# 2. 用正则提取标题、徽章、图片、链接
# 3. 识别"安装"、"使用"相关章节并提取代码块
# 4. 提取第一段有效文字作为项目简介
```

### 5. 纯 Python HTML 渲染

```python
# app/services/report_renderer.py
# 不使用 Jinja2 模板，纯 Python 字符串拼接生成 HTML
# 优势：无条件渲染，所有模块必定出现，空值显示原因
def render_report(result, repo_data, auth_status):
    html = _repo_card(repo_data)
    html += _section_core_tech(tech, readme)
    html += _section_tech_stack(tech)
    html += _section_readme(readme)
    # ...
    return html
```

---

## 遇到的问题与解决

| 问题 | 原因 | 解决 |
|------|------|------|
| 所有模块显示"暂无数据" | GitHub API 限速（60次/小时） | 配置 Personal Access Token → 5000次/小时 |
| 技术栈检测不到工具 | 目录树未递归获取 | `get_repo_tree(recursive=True)` |
| 点按钮没反应 | htmx loading 动画 CSS 选择器错误 | 修复 `.htmx-request.htmx-indicator` 选择器 |
| README 章节数太少 | 正则未匹配 query string 后的 `.svg` | 扩展 badge 正则匹配 `shields.io` 关键词 |
| Starlette 模板崩溃 | `TemplateResponse` API 签名变更 | Starlette 1.2+ 改为 `TemplateResponse(request, name, context)` |
| 端口被占用杀不掉 | Windows TCP 僵尸 socket | 换用 9000 端口 |
