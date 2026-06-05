"""Report renderer — pure Python HTML generation. No Jinja2.

All UI text in Chinese. Every empty field explains WHY it's empty.
"""

from app.models.analysis import AnalysisResult

# Tech category names → 中文
CAT_ZH = {
    "Language / Runtime": "语言 / 运行时",
    "Package Manager": "包管理器",
    "Framework": "框架",
    "Build / Bundler": "构建 / 打包工具",
    "Testing": "测试框架",
    "Lint / Format": "代码检查 / 格式化",
    "Container / Infra": "容器 / 基础设施",
    "CI / CD": "CI / CD 流水线",
    "Other": "其他工具",
}

# ═══════════════════════════════════════════════════════════

def render_report(result: AnalysisResult, repo_data: dict, auth_status: str = "") -> str:
    outputs = {o.analyzer_id: o for o in result.outputs}

    html = _repo_card(repo_data)
    html += '<div class="analysis-section"><h3 class="section-title">项目分析报告</h3>'
    html += '<p class="section-desc">以下从技术栈、文档质量、版本演进、架构、活跃度和贡献者六个维度对该仓库进行深度分析。</p>'

    if auth_status == "unauthenticated":
        html += '<div class="auth-warn">当前未配置 GitHub Token，API 限额仅为 <strong>60 次/小时</strong>，很快就会耗尽。请前往 <a href="/settings">设置页</a> 配置 Token 以获得 5000 次/小时。</div>'

    # Core tech learning guide (placed first for prominence)
    html += _section_core_tech(outputs.get("tech_stack"), outputs.get("readme_summary"))
    html += _section_tech_stack(outputs.get("tech_stack"))
    html += _section_readme(outputs.get("readme_summary"))
    html += _section_roadmap(outputs.get("roadmap"))
    html += _section_architecture(outputs.get("architecture"))
    html += _section_overview(outputs.get("basic_stats"))
    html += _section_code_quality(outputs.get("code_quality"))
    html += _section_contributors(outputs.get("contributors"))
    html += "</div>"
    return html


def _card(title: str, body: str, icon: str = "") -> str:
    prefix = f'<span class="card-icon">{icon}</span>' if icon else ""
    return f'<div class="info-card"><h4>{prefix}{title}</h4>{body}</div>'


def _empty(reason: str) -> str:
    return f'<div class="empty-note">原因：{reason}</div>'


def _tip(text: str) -> str:
    return f'<div class="tip-note">建议：{text}</div>'


# ═══════════════════════════════════════════════════════════
# SECTION 0: CORE TECH LEARNING GUIDE
# ═══════════════════════════════════════════════════════════

def _section_core_tech(tech, readme) -> str:
    """Extract core technologies as a learning guide for developers."""
    if tech is None:
        return ""

    d = tech.details
    langs = d.get("languages", [])
    categories = d.get("categories", {})
    detected = d.get("detected", [])

    # Read README tech mentions
    readme_techs = []
    if readme and readme.details.get("tech_requirements"):
        readme_techs = readme.details["tech_requirements"]

    if not langs and not detected:
        return ""

    # Build the learning guide
    body = '<p class="card-intro">如果你想学习或参与这个项目，以下是需要掌握的核心技术，按学习优先级排列：</p>'

    # 1. Primary languages (must learn first)
    if langs:
        main_langs = [l["name"] for l in langs[:3] if l["bytes"] > 0]
        if main_langs:
            body += '<div class="learn-section"><div class="learn-label">第一优先级：编程语言</div>'
            body += '<p class="learn-desc">这是项目的核心语言，必须首先掌握。</p>'
            body += '<div class="learn-tags">'
            for lang in main_langs:
                body += f'<span class="learn-tag primary">{lang}</span>'
            body += '</div></div>'

    # 2. Build / Package tools
    build_tools = categories.get("Build / Bundler", []) + categories.get("Package Manager", [])
    if build_tools:
        body += '<div class="learn-section"><div class="learn-label">第二优先级：构建与包管理</div>'
        body += '<p class="learn-desc">了解项目的构建系统和依赖管理方式。</p>'
        body += '<div class="learn-tags">'
        for t in build_tools:
            body += f'<span class="learn-tag secondary">{t}</span>'
        body += '</div></div>'

    # 3. Frameworks
    frameworks = categories.get("Framework", [])
    if frameworks:
        body += '<div class="learn-section"><div class="learn-label">第三优先级：框架</div>'
        body += '<p class="learn-desc">项目使用的主要框架，决定了代码的组织方式和设计模式。</p>'
        body += '<div class="learn-tags">'
        for fw in frameworks:
            body += f'<span class="learn-tag framework">{fw}</span>'
        body += '</div></div>'

    # 4. Testing
    tests = categories.get("Testing", [])
    if tests:
        body += '<div class="learn-section"><div class="learn-label">第四优先级：测试框架</div>'
        body += '<p class="learn-desc">掌握测试工具，才能安全地修改代码并验证功能。</p>'
        body += '<div class="learn-tags">'
        for t in tests:
            body += f'<span class="learn-tag testing">{t}</span>'
        body += '</div></div>'

    # 5. Lint & CI
    lint_ci = categories.get("Lint / Format", []) + categories.get("CI / CD", [])
    if lint_ci:
        body += '<div class="learn-section"><div class="learn-label">第五优先级：代码质量 & CI/CD</div>'
        body += '<p class="learn-desc">了解项目的代码规范和持续集成流程，这是专业开发的必备技能。</p>'
        body += '<div class="learn-tags">'
        for t in lint_ci:
            body += f'<span class="learn-tag infra">{t}</span>'
        body += '</div></div>'

    # 6. Container & Infra
    infra = categories.get("Container / Infra", [])
    if infra:
        body += '<div class="learn-section"><div class="learn-label">进阶：容器与基础设施</div>'
        body += '<p class="learn-desc">了解项目的部署方式和基础设施配置。</p>'
        body += '<div class="learn-tags">'
        for t in infra:
            body += f'<span class="learn-tag infra">{t}</span>'
        body += '</div></div>'

    # README mentions
    if readme_techs:
        body += '<div class="learn-section"><div class="learn-label">README 中明确提到的技术</div>'
        body += '<div class="learn-tags">'
        for t in readme_techs:
            body += f'<span class="learn-tag mentioned">{t}</span>'
        body += '</div></div>'

    # Learning summary
    body += '<div class="learn-summary">'
    body += '<p>学习建议：<strong>从上到下逐步学习</strong>，先掌握编程语言基础，再了解构建工具和框架，最后深入测试和 CI/CD。'
    body += '每掌握一层，你就离贡献代码更近一步。</p>'
    body += '</div>'

    return _card("核心技术提炼（学习指南）", body, "🎯")


# ═══════════════════════════════════════════════════════════
# SECTION 1: TECH STACK
# ═══════════════════════════════════════════════════════════

def _section_tech_stack(tech) -> str:
    if tech is None:
        return _card("技术栈", _empty("分析器未能获取技术栈数据，可能是 GitHub API 请求失败"), "🔧")

    d = tech.details
    body = ""

    # Summary
    if tech.summary:
        body += f'<p class="card-summary">{tech.summary}</p>'

    body += '<p class="card-intro">以下是根据仓库文件结构和 GitHub 语言统计自动检测到的技术栈信息：</p>'

    # Languages
    langs = d.get("languages", [])
    if langs:
        total = sum(l["bytes"] for l in langs if l["bytes"] > 0)
        if total > 0:
            body += '<div class="lang-bars"><div class="sections-label">编程语言分布（按代码量比例）</div>'
            for lang in langs[:8]:
                if lang["bytes"] > 0:
                    pct = round(lang["bytes"] / total * 100, 1)
                    body += f'<div class="lang-bar"><span class="lang-name">{lang["name"]}</span><div class="lang-track"><div class="lang-fill" style="width:{pct}%"></div></div><span class="lang-pct">{pct}%</span></div>'
            body += '</div>'
    else:
        body += _empty("GitHub 未返回该仓库的语言统计数据，仓库可能为空或语言检测尚未完成")

    # Categories
    categories = d.get("categories", {})
    if categories:
        has_any = any(v for v in categories.values())
        if has_any:
            body += '<div class="tech-categories">'
            for cat_name, items in categories.items():
                if items:
                    zh_name = CAT_ZH.get(cat_name, cat_name)
                    tags = "".join(f'<span class="tech-tag">{t}</span>' for t in items)
                    body += f'<div class="tech-cat"><span class="cat-label">{zh_name}</span><div class="cat-tags">{tags}</div></div>'
            body += '</div>'

    # All detected
    detected = d.get("detected", [])
    if detected:
        tags = "".join(f'<span class="tech-tag">{t}</span>' for t in detected)
        body += f'<div class="tech-all"><div class="sections-label">全部检测到的技术工具（共 {len(detected)} 项）</div><div class="cat-tags">{tags}</div></div>'

    if tech.recommendations:
        recs = "".join(f'<div class="rec-item">建议：{r}</div>' for r in tech.recommendations)
        body += f'<div class="recommendations"><div class="rec-title">改进建议</div>{recs}</div>'

    return _card("技术栈", body, "🔧")


# ═══════════════════════════════════════════════════════════
# SECTION 2: README
# ═══════════════════════════════════════════════════════════

def _section_readme(readme) -> str:
    if readme is None:
        return _card("README 文档分析", _empty("分析器未能获取 README 数据，可能是 GitHub API 请求失败"), "📖")
    if readme.score == 0 and "No README" in (readme.summary or ""):
        return _card("README 文档分析", _empty("该仓库没有 README.md 文件。README 是开源项目的第一张名片，强烈建议添加"), "📖")

    d = readme.details
    body = ""

    if readme.summary:
        body += f'<p class="card-summary">文档概况：{readme.summary}</p>'

    if d.get("preview"):
        body += f'<div class="readme-preview"><div class="preview-label">项目简介（从 README 自动提取）</div><div class="preview-text">{d["preview"]}</div></div>'
    else:
        body += _empty("无法从 README 中提取项目简介段落，文档可能主要由代码块或链接组成")

    if d.get("tech_requirements"):
        tags = "".join(f'<span class="tech-tag">{t}</span>' for t in d["tech_requirements"])
        body += f'<div class="readme-tech"><span class="sections-label">README 中提及的技术要求：</span>{tags}</div>'

    if d.get("install_text"):
        body += f'<div class="readme-install"><div class="sections-label">如何安装（从 README 提取）</div><pre class="install-box">{d["install_text"]}</pre></div>'
    else:
        body += _empty("README 中未找到明确的安装步骤")

    if d.get("usage_text"):
        body += f'<div class="readme-install"><div class="sections-label">如何使用（从 README 提取）</div><pre class="install-box">{d["usage_text"]}</pre></div>'
    else:
        body += _empty("README 中未找到明确的使用示例")

    examples = d.get("examples", [])
    if examples:
        body += '<div class="readme-code"><div class="sections-label">README 中的代码示例</div>'
        for ex in examples[:3]:
            body += f'<pre class="code-box"><span class="code-lang">{ex["lang"]}</span>{ex["code"]}</pre>'
        body += '</div>'

    links = d.get("links", [])
    if links:
        body += '<div class="readme-links"><div class="sections-label">README 中的外部链接</div><div class="links-list">'
        for link in links[:10]:
            body += f'<a href="{link["url"]}" target="_blank" class="ext-link">{link["label"]}</a>'
        body += '</div></div>'

    sections = d.get("sections", [])
    if sections:
        chips = "".join(f'<span class="section-chip">{s}</span>' for s in sections)
        body += f'<div class="readme-sections"><div class="sections-label">文档结构（共 {len(sections)} 个章节标题）</div><div class="sections-list">{chips}</div></div>'
    else:
        body += _empty("README 中未检测到 Markdown 章节标题（# ## ### 格式）")

    if readme.recommendations:
        recs = "".join(f'<div class="rec-item">建议：{r}</div>' for r in readme.recommendations)
        body += f'<div class="recommendations"><div class="rec-title">改进建议</div>{recs}</div>'

    return _card("README 文档分析", body, "📖")


# ═══════════════════════════════════════════════════════════
# SECTION 3: ROADMAP
# ═══════════════════════════════════════════════════════════

def _section_roadmap(roadmap) -> str:
    if roadmap is None:
        return _card("版本与演进路线", _empty("分析器未能获取 Release 数据，可能是 GitHub API 请求失败"), "🗺️")

    d = roadmap.details
    timeline = d.get("timeline", [])

    if not timeline:
        return _card("版本与演进路线",
            '<p class="card-intro">该项目未通过 GitHub Releases 发布版本，可能采用了以下方式之一：</p>'
            '<ul class="reason-list"><li>持续发布（CD），每次合并即自动部署，不手动打 Release</li>'
            '<li>使用 Git Tag 管理版本但不发布 GitHub Release</li>'
            '<li>项目处于早期阶段，尚未建立版本发布流程</li></ul>', "🗺️")

    body = f'<p class="card-summary">{roadmap.summary}</p>' if roadmap.summary else ""
    body += '<p class="card-intro">以下版本时间线展示了该项目的发布节奏和演进历程：</p>'

    dots = "".join(f'<div class="timeline-dot"></div><span class="timeline-ver">{v}</span>' for v in timeline)
    body += f'<div class="roadmap-timeline"><div class="sections-label">版本演进时间线（从新到旧）</div><div class="timeline-track">{dots}</div></div>'

    releases = d.get("releases", [])
    if releases:
        body += '<div class="sections-label" style="margin-top:16px">最近发布的版本详情</div><div class="release-list">'
        for rel in releases[:5]:
            body += f'<div class="release-item"><strong>{rel["tag"]}</strong><span class="release-date">{rel["date"]}</span>'
            if rel.get("summary"):
                body += f'<p class="release-summary">{rel["summary"][:200]}</p>'
            body += '</div>'
        body += '</div>'

    return _card("版本与演进路线", body, "🗺️")


# ═══════════════════════════════════════════════════════════
# SECTION 4: ARCHITECTURE
# ═══════════════════════════════════════════════════════════

def _section_architecture(arch) -> str:
    if arch is None:
        return _card("项目架构", _empty("分析器未能获取架构数据，可能是 GitHub API 请求失败"), "🏗️")

    d = arch.details
    body = ""

    if arch.summary:
        body += f'<p class="card-summary">{arch.summary}</p>'

    body += '<p class="card-intro">通过分析仓库的顶层目录结构，推断出以下项目架构信息：</p>'

    if d.get("diagram"):
        body += f'<div class="arch-diagram"><div class="sections-label">顶层目录结构</div><pre class="diagram-box">{d["diagram"]}</pre></div>'
    else:
        body += _empty("无法获取仓库目录结构，API 返回为空")

    if d.get("arch_description"):
        body += f'<div class="arch-summary"><p>{d["arch_description"]}</p></div>'

    if arch.recommendations:
        recs = "".join(f'<div class="rec-item">建议：{r}</div>' for r in arch.recommendations)
        body += f'<div class="recommendations"><div class="rec-title">改进建议</div>{recs}</div>'

    return _card("项目架构", body, "🏗️")


# ═══════════════════════════════════════════════════════════
# SECTION 5: OVERVIEW
# ═══════════════════════════════════════════════════════════

def _section_overview(basic) -> str:
    if basic is None:
        return _card("仓库概况", _empty("分析器未能获取仓库基础数据，可能是 GitHub API 请求失败"), "📋")
    body = f'<p class="card-summary">{basic.summary}</p>' if basic.summary else ""
    if basic.recommendations:
        recs = "".join(f'<div class="rec-item">建议：{r}</div>' for r in basic.recommendations)
        body += f'<div class="recommendations"><div class="rec-title">改进建议</div>{recs}</div>'
    return _card("仓库概况", body, "📋")


# ═══════════════════════════════════════════════════════════
# SECTION 6: CODE ACTIVITY
# ═══════════════════════════════════════════════════════════

def _section_code_quality(quality) -> str:
    if quality is None:
        return _card("代码活跃度", _empty("分析器未能获取提交和 Issue 数据，可能是 GitHub API 请求失败或数据不可用"), "📊")

    body = ""
    if quality.summary:
        body += f'<p class="card-summary">{quality.summary}</p>'

    body += '<p class="card-intro">通过分析最近 100 条提交记录和 Issue 状态，评估该项目的开发活跃程度：</p>'

    d = quality.details
    if d.get("commits_per_day") is not None and d["commits_per_day"] > 0:
        body += f'<p class="stat-line">近 30 天平均提交频率：<strong>{d["commits_per_day"]} 次/天</strong></p>'
    if d.get("resolution_rate") is not None:
        body += f'<p class="stat-line">Issue 解决率：<strong>{d["resolution_rate"]:.0%}</strong>（{d.get("closed_issues", 0)}/{d.get("total_issues", 0)} 已关闭）</p>'

    if quality.recommendations:
        recs = "".join(f'<div class="rec-item">建议：{r}</div>' for r in quality.recommendations)
        body += f'<div class="recommendations"><div class="rec-title">改进建议</div>{recs}</div>'

    return _card("代码活跃度", body, "📊")


# ═══════════════════════════════════════════════════════════
# SECTION 7: CONTRIBUTORS
# ═══════════════════════════════════════════════════════════

def _section_contributors(contrib) -> str:
    if contrib is None:
        return _card("贡献者分析", _empty("分析器未能获取贡献者数据，可能是 GitHub API 请求失败"), "👥")

    d = contrib.details
    body = ""

    if contrib.summary:
        body += f'<p class="card-summary">{contrib.summary}</p>'

    body += '<p class="card-intro">以下是根据 Git 提交记录统计的核心贡献者及其贡献量：</p>'

    top = d.get("top_contributors", [])
    if top:
        body += '<div class="contributor-section"><div class="sections-label">核心贡献者（按提交次数排序）</div><div class="contributor-row">'
        for c in top[:8]:
            body += f'<div class="contributor-avatar" title="{c["login"]}：{c["contributions"]} 次提交"><img src="{c["avatar"]}&s=48" alt="{c["login"]}" width="40" height="40" loading="lazy"><span class="contributor-name">{c["login"]}</span></div>'
        body += '</div></div>'
    else:
        body += _empty("无法获取贡献者列表，该仓库可能没有公开贡献者数据")

    bus = d.get("bus_factor")
    if bus:
        body += f'<p class="stat-line" style="margin-top:12px">核心维护者人数（Bus Factor）：<strong>{bus}</strong> 人 — {"社区活跃度高，不依赖单一开发者" if bus >= 5 else "存在一定风险，建议增加核心维护者" if bus >= 2 else "风险较高，项目高度依赖个人"}</p>'

    if contrib.recommendations:
        recs = "".join(f'<div class="rec-item">建议：{r}</div>' for r in contrib.recommendations)
        body += f'<div class="recommendations"><div class="rec-title">改进建议</div>{recs}</div>'

    return _card("贡献者分析", body, "👥")


# ═══════════════════════════════════════════════════════════
# REPO CARD
# ═══════════════════════════════════════════════════════════

def _repo_card(repo: dict) -> str:
    lic = repo.get("license")
    lic_name = lic.get("spdx_id", lic.get("key", "")) if lic and lic.get("key") != "none" else ""
    desc = repo.get('description') or '（该仓库未填写描述信息）'
    lang = repo.get('language')
    topics_html = "".join(f'<span class="topic-tag">{t}</span>' for t in repo.get("topics", []) or [])

    return f"""<div class="repo-card" id="repo-card">
    <div class="repo-header">
        <div class="repo-identity">
            <h2><a href="{repo.get('html_url','')}" target="_blank">{repo.get('full_name','')}</a></h2>
            <p class="repo-description">{desc}</p>
        </div>
        {f'<span class="license-badge">{lic_name}</span>' if lic_name else '<span class="license-badge no-license">无许可证</span>'}
    </div>
    <div class="stats-grid">
        <div class="stat-item"><span class="stat-icon">⭐</span><span class="stat-value">{repo.get('stargazers_count',0)}</span><span class="stat-label">收藏数</span></div>
        <div class="stat-item"><span class="stat-icon">🍴</span><span class="stat-value">{repo.get('forks_count',0)}</span><span class="stat-label">复刻数</span></div>
        <div class="stat-item"><span class="stat-icon">⚠️</span><span class="stat-value">{repo.get('open_issues_count',0)}</span><span class="stat-label">待解决问题</span></div>
        <div class="stat-item"><span class="stat-icon">👀</span><span class="stat-value">{repo.get('watchers_count',0)}</span><span class="stat-label">关注者</span></div>
        <div class="stat-item"><span class="stat-icon">📏</span><span class="stat-value">{repo.get('size',0)//1024}MB</span><span class="stat-label">仓库大小</span></div>
    </div>
    <div class="repo-meta">
        {f'<span class="meta-item"><span class="lang-dot lang-{lang.lower()}"></span>主要语言：{lang}</span>' if lang else ''}
        <span class="meta-item">创建于 {(repo.get("created_at","") or "")[:10]}</span>
        <span class="meta-item">最近更新 {(repo.get("updated_at","") or "")[:10]}</span>
        <span class="meta-item">默认分支：{repo.get('default_branch','')}</span>
    </div>
    {f'<div class="topics"><span class="sections-label">仓库标签：</span>{topics_html}</div>' if topics_html else ''}
    {f'<div class="homepage-link">项目主页：<a href="{repo.get("homepage")}" target="_blank">{repo.get("homepage")}</a></div>' if repo.get('homepage') else ''}
</div>"""
