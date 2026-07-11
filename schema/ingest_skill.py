"""
Ingest Skill — 知识吞吐与冲突检测 Schema

定义 Ingest Agent 使用的 Prompt 模板、输出解析器和状态转移逻辑。
"""

# ============================================================
# 1. 知识提取 Prompt
# ============================================================

EXTRACT_ENTITIES_PROMPT = """你是一位资深 AI 知识架构师。请分析以下文档，完成以下任务：

## 输入文档
{source_content}

## 已有知识库实体列表
{existing_entities}

## 任务
1. **提取核心技术实体**：从文档中识别出核心的技术概念、算法、模型、框架等实体
2. **判断新旧关系**：检查每个实体是否已存在于知识库中
3. **提取关系链接**：识别实体之间的依赖、引用、扩展等关系

## 输出格式（JSON）
```json
{{
    "entities": [
        {{
            "name": "实体名称",
            "is_new": true/false,
            "summary": "实体的一句话总结",
            "key_points": ["要点1", "要点2"],
            "related_entities": ["关联实体1", "关联实体2"],
            "relationship_type": "依赖/扩展/并列/替代"
        }}
    ],
    "conflict_flags": [
        {{
            "entity": "实体名称",
            "description": "与现有知识冲突的描述"
        }}
    ],
    "source_metadata": {{
        "title": "文档标题",
        "type": "论文/博客/代码",
        "key_findings": ["发现1", "发现2"]
    }}
}}
```

请严格输出 JSON 格式，不要包含其他文字。
"""

# ============================================================
# 2. 知识融合 Prompt
# ============================================================

MERGE_KNOWLEDGE_PROMPT = """你是一位 AI 知识库编辑专家。请将新知识融合到现有的 Markdown 知识页面中。

## 现有页面内容
```markdown
{existing_page}
```

## 需要融合的新知识
{new_knowledge}

## 融合规则
1. **保留原有内容**：不要删除已有的有效信息
2. **增量补充**：将新知识有机地插入到合适的位置
3. **更新指标**：如果新论文更新了旧算法的指标数据，更新并标注 `[Updated]`
4. **标记冲突**：如果新旧知识存在矛盾，保留双方观点并添加 `[Conflict-Flag]`
5. **强化链接**：确保页面中的 `[[wikilinks]]` 双向链接完整且准确
6. **保持格式**：维持原有的 Markdown 层级结构和风格

## 输出
请直接输出融合后的完整 Markdown 页面内容，不要包含其他文字。
"""

# ============================================================
# 3. 新页面生成 Prompt
# ============================================================

CREATE_PAGE_PROMPT = """你是一位 AI 知识库写作者。请根据以下提取的知识，创建一个全新的 Markdown 知识页面。

## 实体名称
{entity_name}

## 知识内容
{knowledge_content}

## 关联实体
{related_entities}

## 写作要求
1. 使用 Markdown 格式，包含标题、摘要、核心要点、详细说明
2. 所有关联实体使用 `[[wikilinks]]` 格式标注双向链接
3. 包含代码示例（如果有）
4. 包含参考文献来源
5. 结构清晰，便于后续增量更新

## 输出
请直接输出完整的 Markdown 页面内容。
"""

# ============================================================
# 4. 图索引更新 Schema
# ============================================================

GRAPH_INDEX_SCHEMA = {
    "type": "object",
    "properties": {
        "nodes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "label": {"type": "string"},
                    "type": {"type": "string", "enum": ["concept", "algorithm", "paper", "code"]}
                }
            }
        },
        "edges": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "source": {"type": "string"},
                    "target": {"type": "string"},
                    "relation": {"type": "string"}
                }
            }
        }
    }
}

# ============================================================
# 5. 状态机定义
# ============================================================

INGEST_STATES = [
    "init",
    "extracting",      # 正在提取实体
    "comparing",       # 正在对比已有知识
    "merging",         # 正在融合知识
    "creating_new",    # 正在创建新页面
    "updating_graph",  # 正在更新图索引
    "completed",       # 完成
    "failed"           # 失败
]

INGEST_TRANSITIONS = {
    "init": "extracting",
    "extracting": "comparing",
    "comparing": "merging",   # 如果有现有实体
    "comparing": "creating_new",  # 如果是全新实体
    "merging": "updating_graph",
    "creating_new": "updating_graph",
    "updating_graph": "completed"
}
