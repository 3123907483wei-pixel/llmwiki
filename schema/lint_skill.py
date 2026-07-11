"""
Lint Skill — Wiki 链接审计与健康检查 Schema

定义 Lint Agent 的审计规则、报告格式和自动修复策略。
"""

# ============================================================
# 1. 死链检测规则
# ============================================================

BROKEN_LINK_PATTERN = r"\[\[(.*?)\]\]"

# ============================================================
# 2. 冲突检测 Prompt
# ============================================================

CONFLICT_DETECTION_PROMPT = """你是一位知识库一致性审计专家。请比较以下两个知识页面，找出其中存在矛盾或冲突的陈述。

## 页面 A: {page_a_title}
```markdown
{page_a_content}
```

## 页面 B: {page_b_title}
```markdown
{page_b_content}
```

## 检查维度
1. **数据指标冲突**：同一指标的不同数值（如模型准确率、参数量）
2. **时间线冲突**：事件或发现的先后顺序矛盾
3. **定义冲突**：同一术语的不同定义或解释
4. **主张冲突**：关于同一主题的相互矛盾的主张

## 输出格式（JSON）
```json
{{
    "conflicts": [
        {{
            "type": "数据指标/时间线/定义/主张",
            "severity": "high/medium/low",
            "page_a_statement": "页面 A 中的相关陈述",
            "page_b_statement": "页面 B 中的相关陈述",
            "description": "冲突的详细描述",
            "suggestion": "解决建议"
        }}
    ],
    "no_conflicts": false
}}
```

如果没有发现冲突，设置 "no_conflicts": true。
请严格输出 JSON 格式。
"""

# ============================================================
# 3. 幻觉检测 Prompt
# ============================================================

HALLUCINATION_DETECTION_PROMPT = """你是一位知识库质量审核员。请检查以下 Markdown 页面，识别其中可能存在的"幻觉"内容——即没有事实依据的、虚构的或过度推测的陈述。

## 页面内容
```markdown
{page_content}
```

## 检查重点
1. **虚假引用**：引用了不存在的论文、作者或研究成果
2. **过度推测**：将推测性内容表述为确定事实
3. **数据不一致**：内部数据矛盾或与常识明显不符
4. **来源不明**：重要声明没有任何出处或引用

## 输出格式（JSON）
```json
{{
    "hallucinations": [
        {{
            "severity": "high/medium/low",
            "location": "问题所在的段落或章节",
            "content": "有问题的原文",
            "issue_type": "虚假引用/过度推测/数据不一致/来源不明",
            "explanation": "为什么认为这是幻觉",
            "fix_suggestion": "修复建议"
        }}
    ],
    "overall_quality_score": 0-100,
    "no_issues_found": false
}}
```

请严格输出 JSON 格式。
"""

# ============================================================
# 4. 孤立节点检测规则
# ============================================================

ORPHAN_PAGE_THRESHOLD = 0  # 被引用次数 <= 此值视为孤立节点

# ============================================================
# 5. 审计报告格式
# ============================================================

LINT_REPORT_TEMPLATE = """# 🔍 Lint 审计报告

**审计时间**: {timestamp}
**知识库规模**: {total_pages} 个页面, {total_links} 条链接

---

## 📊 总体评分
- **知识完整性**: {completeness_score}/100
- **链接健康度**: {link_health_score}/100
- **一致性评分**: {consistency_score}/100

---

## 🔗 死链报告 ({broken_count} 个)
{broken_links_section}

---

## 🏝️ 孤立节点报告 ({orphan_count} 个)
{orphan_pages_section}

---

## ⚡ 冲突检测报告 ({conflict_count} 个)
{conflicts_section}

---

## 👻 幻觉检测报告 ({hallucination_count} 个)
{hallucinations_section}

---

## ✅ 自动修复操作
{auto_fix_section}
"""

# ============================================================
# 6. 自动修复规则
# ============================================================

AUTO_FIX_RULES = {
    "remove_broken_link": {
        "description": "删除指向不存在页面的 [[wikilinks]]",
        "enabled": True
    },
    "create_stub_page": {
        "description": "为被引用但不存在页面创建桩页面（Stub）",
        "enabled": True,
        "stub_template": """# {entity_name}

> ⚠️ 此页面为自动生成的桩页面（Stub），等待内容填充。

## 被以下页面引用
{referenced_by}

---

*此页面由 Lint Agent 于 {date} 自动创建*
"""
    },
    "reorganize_orphans": {
        "description": "将孤立节点添加到 index 或关联页面",
        "enabled": False
    }
}

# ============================================================
# 7. 状态机定义
# ============================================================

LINT_STATES = [
    "init",
    "scanning_links",       # 扫描链接
    "detecting_conflicts",  # 检测冲突
    "detecting_hallucinations",  # 检测幻觉
    "finding_orphans",      # 寻找孤立节点
    "auto_fixing",          # 自动修复
    "generating_report",    # 生成报告
    "completed"
]

LINT_TRANSITIONS = {
    "init": "scanning_links",
    "scanning_links": "detecting_conflicts",
    "detecting_conflicts": "detecting_hallucinations",
    "detecting_hallucinations": "finding_orphans",
    "finding_orphans": "auto_fixing",
    "auto_fixing": "generating_report",
    "generating_report": "completed"
}
