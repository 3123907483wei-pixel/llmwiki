# LLM Wiki: A Knowledge Compilation & Graph-Augmented Retrieval System

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Architecture](https://img.shields.io/badge/Architecture-Schema--Driven-orange.svg)]()
[![Design Pattern](https://img.shields.io/badge/Design%20Pattern-Karpathy%20LLM%20Wiki-green.svg)]()

> 基于 Andrej Karpathy 提出的 **LLM Wiki 知识编译（Knowledge Compilation）** 范式实现的知识编译与图增强检索系统。本项目面向结构化知识管理场景，通过大模型将异构、碎片化的前沿 AI 技术文档（论文、代码、博客）**增量编译**为人类可读、可双向链接、可用 Git 版本控制的结构化 Markdown 知识网络，并利用 Wiki 拓扑链接与 PageRank 图检索增强知识关联能力。

---

## 💡 设计动机

* **传统文档管理的局限**：在个人或团队的知识管理场景中，文档散落在不同文件中，概念间的关系需要人工维护，跨文档引用难以追踪和验证。
* **LLM Wiki 的思路**：引入一个**中间编译层（Markdown Wiki）**。当新数据进来时，Agent 辅助用户将其融入现有的知识网络中，自动建立双向链接（Wikilinks `[[topic]]`）、生成概念摘要、记录潜在的信息冲突，帮助用户构建和维护结构化的知识库。

---

## 🛠️ 系统架构设计 (System Architecture)

系统严格遵循 **三层解耦架构** 设计，通过规约（Schema）与 Skill 驱动 Agent 的核心生命周期：
```
[ 📥 多源异构输入: 论文 / 代码 / 博客 ]
                        ↓
┌──────────────────────────────────────────────┐
│ 1. Raw Sources 层 (raw_sources/)             │
│    (原始文档归档与元数据追踪)                   │
└──────────────────────────────────────────────┘
↓ [Ingest Pipeline]
┌──────────────────────────────────────────────┐
│ 2. Wiki 编译层 (wiki_vault/)                 │
│    ├── pages/ (实体节点，包含 [[wikilinks]])   │
│    └── index_graph.json (全局图拓扑索引)      │
└──────────────────────────────────────────────┘
↓ ↑ [Lint & Query Engine]
┌──────────────────────────────────────────────┐
│ 3. Schema 规约层 (schema/ + core/)           │
│    ├── 📥 Ingest: 实体抽取、知识融合          │
│    ├── 🔍 Query: PageRank 拓扑检索           │
│    └── 🔎 Lint: 死链检测、冲突记录、审计报告  │
└──────────────────────────────────────────────┘
```


---

## 🔧 核心能力

### 1. Schema 驱动的增量编译流水线 (Incremental Ingest)
* **做法**：利用大模型辅助实体提取。每当引入新的技术文档时，`IngestAgent` 提取文档中的技术实体（Entities），并与本地 Wiki 已有实体进行比对。
* **效果**：对于新实体，自动创建知识页面；对于已有实体，将新信息增量追加到现有页面，并对发现的潜在矛盾处添加 `[Conflict-Flag]` 标记供用户审查。
* **代码**：`core/ingest_agent.py` — 支持 PDF/TXT/MD/代码文件解析、LLM 实体提取、知识合并、图索引更新、变更日志记录。

### 2. 基于 `[[Wikilinks]]` 的图增强检索 (Graph-Augmented Query)
* **做法**：利用编译阶段建立的 `[[wikilinks]]` 构建实体关系拓扑图，在检索时通过 **Personalized PageRank** 在图上计算各节点与查询关键词的相关性得分。
* **效果**：基于已建立的结构化链接进行关联推荐和路径发现，增强检索结果的知识关联性。对于超出已有实体范围的开放语义查询，可扩展混合检索方式（如结合 BM25/向量检索）。
* **代码**：`core/query_agent.py` — 多策略实体匹配、NetworkX PageRank、图路径发现、上下文组装。

### 3. 知识网络审计与健康检查 (Lint & Audit)
* **做法**：`LintAgent` 像代码静态分析工具一样扫描整个 Wiki 目录，检查引用完整性。
* **效果**：自动发现并报告死链（`[[wikilinks]]` 指向不存在的页面）、孤立节点（从未被引用的页面），并可为被引用但缺失的实体自动创建 Stub 页面。输出结构化的审计报告和健康评分。
* **代码**：`core/lint_agent.py` — 死链检测、孤立节点检测、Stub 自动创建、审计报告生成。

---

## 📦 技术栈 (Tech Stack)

| 层级 | 技术 | 用途 |
|------|------|------|
| **核心语言** | Python 3.10+ | 全部 Agent 和业务逻辑 |
| **图算法** | NetworkX | PageRank、最短路径、图拓扑分析 |
| **后端 API** | FastAPI + Uvicorn | RESTful API 服务 |
| **前端看板** | Streamlit | 可视化管理界面 |
| **知识存储** | Markdown + JSON + Git | 零依赖、人类可读、版本可控 |
| **LLM 引擎** | 可插拔（DeepSeek/Qwen/OpenAI） | 实体提取、知识融合、冲突检测 |

---

## 📂 项目目录结构（实际实现）

```text
d:\llmwiki/
├── core/                          # 核心 Agent 实现
│   ├── __init__.py                # 包初始化
│   ├── ingest_agent.py            # 📥 知识摄入编译器
│   ├── query_agent.py             # 🔍 PageRank 图检索引擎
│   └── lint_agent.py              # 🔎 知识网络审计器
├── schema/                        # Schema 规约层
│   ├── __init__.py
│   ├── ingest_skill.py            # 摄入 Prompt 模板与状态机
│   ├── query_skill.py             # 检索策略与合成 Prompt
│   └── lint_skill.py              # 审计规则与报告格式
├── raw_sources/                   # 原始文档存储
├── wiki_vault/                    # 编译后的知识库
│   ├── pages/                     # Markdown 知识页面 (6个)
│   │   ├── Transformer.md         # → [[Attention]], [[GPT]], [[BERT]], [[LLM]]
│   │   ├── Attention.md           # → [[Transformer]], [[GPT]], [[BERT]]
│   │   ├── GPT.md                 # → [[Transformer]], [[LLM]], [[BERT]]
│   │   ├── BERT.md                # → [[Transformer]], [[GPT]], [[LLM]]
│   │   ├── LLM.md                 # → [[Transformer]], [[GPT]], [[BERT]]
│   │   └── Self-Attention.md      # (Lint 自动创建的 Stub)
│   ├── index_graph.json           # 全局图拓扑索引
│   ├── change_log.md              # 变更日志
│   ├── lint_report.json           # 审计报告 (JSON)
│   └── lint_report.md             # 审计报告 (Markdown)
├── app.py                         # Streamlit 前端交互看板 (6 个功能页)
├── server.py                      # FastAPI 后端 API 服务 (12 个接口)
├── verify.py                      # 系统验证脚本
├── requirements.txt               # Python 依赖
├── readme.md                      # 项目说明文档
└── develop.md                     # 开发实现说明
```

---

## 🚀 快速开始

### 1. 环境准备

```bash
cd d:\llmwiki
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. 运行验证

```bash
python verify.py
```

预期输出：
```
==================================================
  LLM Wiki 系统完整性验证
==================================================
✅ 知识图谱: 6 节点, 50 条边
✅ 图检索: PageRank 路径漫游正常
✅ 知识审计: 健康评分 100/100
```

### 3. 启动交互看板

```bash
streamlit run app.py
```

浏览器打开 http://localhost:8501，包含 6 个功能页：

| 页面 | 功能 |
|------|------|
| 📊 **仪表盘** | 系统架构概览、知识库统计、核心技术亮点 |
| 📥 **知识摄入** | 上传文档 → Ingest Agent 自动编译成 Wiki |
| 🔍 **知识检索** | 输入问题 → PageRank 图检索 → 展示结果 |
| 🔎 **知识审计** | 运行 Lint → 死链/冲突/幻觉报告 |
| 🌐 **知识图谱** | Mermaid 可视化知识拓扑图 |
| 📄 **页面浏览** | 浏览所有 Wiki 页面内容 |

### 4. 启动 API 服务

```bash
python server.py
# 服务运行在 http://localhost:8000
# API 文档: http://localhost:8000/docs
```

---

## 🌐 API 接口文档

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/status` | 系统状态 |
| `POST` | `/api/ingest/file` | 上传文件并摄入 |
| `POST` | `/api/ingest/text` | 摄入文本内容 |
| `POST` | `/api/ingest/directory` | 批量摄入目录 |
| `POST` | `/api/query/search` | 知识检索 |
| `POST` | `/api/query/answer` | 检索并生成回答 |
| `GET` | `/api/query/topics` | 列出所有主题 |
| `POST` | `/api/lint/run` | 运行审计 |
| `GET` | `/api/lint/report` | 获取审计报告 |
| `GET` | `/api/wiki/pages` | 列出所有页面 |
| `GET` | `/api/wiki/page/{name}` | 获取页面内容 |
| `GET` | `/api/wiki/graph` | 获取知识图谱数据 |

---

## ✅ 系统验证结果

```
=== 1. 构建知识图谱索引 ===
   节点数: 6
   边数: 50
   节点: Attention, BERT, GPT, LLM, Self-Attention, Transformer

=== 2. 测试知识检索 ===
   搜索 "Transformer" → 匹配实体: ['Transformer']
   相关页面: Attention (得分最高), Transformer, BERT
   图路径: Transformer → Attention, Transformer → BERT

=== 3. 测试知识审计 ===
   完整性评分: 100/100
   链接健康度: 100/100
   一致性评分: 100/100
   死链: 0 | 孤立节点: 0 | 自动修复: 0
```