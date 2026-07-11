"""
Streamlit 前端交互看板 — LLM Wiki 知识管理系统 UI

提供直观的 Web 界面来：
1. 上传/输入文档并触发知识编译
2. 检索知识库并查看回答
3. 运行审计并查看报告
4. 浏览知识图谱
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime

import streamlit as st
import requests

# 确保可以导入 core 包
sys.path.insert(0, str(Path(__file__).parent))

from core.ingest_agent import IngestAgent
from core.query_agent import QueryAgent
from core.lint_agent import LintAgent

# ============================================================
# 页面配置
# ============================================================

st.set_page_config(
    page_title="LLM Wiki — 自演进知识管理系统",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# 初始化 Agent（会话级缓存）
# ============================================================

VAULT_PATH = Path(__file__).parent / "wiki_vault"

@st.cache_resource
def init_agents():
    return {
        "ingest": IngestAgent(vault_path=str(VAULT_PATH)),
        "query": QueryAgent(vault_path=str(VAULT_PATH)),
        "lint": LintAgent(vault_path=str(VAULT_PATH)),
    }

agents = init_agents()
ingest_agent = agents["ingest"]
query_agent = agents["query"]
lint_agent = agents["lint"]


# ============================================================
# 辅助函数
# ============================================================

def format_timestamp(ts):
    """格式化时间戳"""
    try:
        dt = datetime.fromisoformat(ts)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return ts

def get_wiki_stats():
    """获取知识库统计信息"""
    topics = query_agent.list_topics()
    ingest_status = ingest_agent.get_status()
    query_stats = query_agent.get_stats()
    return {
        "topics": topics,
        "topic_count": len(topics),
        "ingest": ingest_status,
        "query": query_stats,
    }


# ============================================================
# 侧边栏
# ============================================================

st.sidebar.title("🧠 LLM Wiki")
st.sidebar.markdown("*自演进知识管理系统*")
st.sidebar.markdown("---")

# 导航
page = st.sidebar.radio(
    "导航",
    ["📊 仪表盘", "📥 知识摄入", "🔍 知识检索", "🔎 知识审计", "🌐 知识图谱", "📄 页面浏览"],
)

st.sidebar.markdown("---")

# 显示知识库概览
stats = get_wiki_stats()
st.sidebar.metric("📚 知识页面数", stats["topic_count"])
st.sidebar.metric("🔗 图节点数", stats["query"].get("total_nodes", 0))
st.sidebar.metric("🔀 图边数", stats["query"].get("total_edges", 0))

st.sidebar.markdown("---")
st.sidebar.caption(f"💡 基于 Karpathy Knowledge Compilation 范式")
st.sidebar.caption(f"⚡ 图拓扑检索 · [[Wikilinks]] · 增量编译")


# ============================================================
# 页面: 仪表盘
# ============================================================

def render_dashboard():
    st.title("📊 系统仪表盘")
    st.markdown("---")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📚 知识页面", stats["topic_count"])
    with col2:
        st.metric("🔗 图节点", stats["query"].get("total_nodes", 0))
    with col3:
        st.metric("🔀 图边", stats["query"].get("total_edges", 0))
    with col4:
        density = stats["query"].get("graph_density", 0)
        st.metric("📊 图密度", f"{density:.4f}")

    st.markdown("---")

    # 系统架构图
    st.subheader("🏗️ 系统架构")
    st.markdown("""
    ```
    [ 📥 多源异构输入: 论文 / 代码 / 博客 ]
                        ↓
    ┌──────────────────────────────────────────────┐
    │ 1. Raw Sources 层 (无损原生数据存储)           │
    └──────────────────────────────────────────────┘
    ↓ [Ingest Pipeline]
    ┌──────────────────────────────────────────────┐
    │ 2. Wiki 编译层 (Markdown 拓扑知识网络)         │
    │    ├── pages/ (实体节点 + [[wikilinks]])       │
    │    └── index_graph.json (全局图索引)           │
    └──────────────────────────────────────────────┘
    ↓ ↑ [Query & Lint Engine]
    ┌──────────────────────────────────────────────┐
    │ 3. Schema 规约层 (Skill 定义与路由)            │
    │    ├── Ingest Skill: 冲突消解、增量编译        │
    │    ├── Query Skill: PageRank 图检索           │
    │    └── Lint Skill: 死链修复、幻觉纠偏          │
    └──────────────────────────────────────────────┘
    ```
    """)

    # 核心能力
    st.subheader("🔥 核心技术亮点")
    col1, col2 = st.columns(2)
    with col1:
        st.info("**Schema 驱动的增量编译**\n\n新文档自动与现有知识融合，不会重复创建词条。冲突自动标记 `[Conflict-Flag]`。")
        st.success("**基于 [[Wikilinks]] 的图增强检索**\n\n利用 Wiki 页面间的拓扑链接和 PageRank 算法进行关联推荐与知识路径发现。")
    with col2:
        st.warning("**语法树感知对齐**\n\n确保函数定义、逻辑闭环和原理解释始终在同一个编译语境中，绝不发生传统 RAG 的文本硬截断。")
        st.error("**Lint 链接审计**\n\n自动检测死链、孤立节点，为被引用但缺失的实体创建 Stub 占位页面。")


# ============================================================
# 页面: 知识摄入
# ============================================================

def render_ingest():
    st.title("📥 知识摄入")
    st.markdown("将原始文档编译为结构化的 Wiki 知识网络")

    tab1, tab2, tab3 = st.tabs(["📄 上传文件", "✏️ 手动输入", "📂 批量摄入"])

    # Tab 1: 上传文件
    with tab1:
        st.subheader("上传文档文件")
        uploaded_file = st.file_uploader(
            "选择文件 (支持 .txt, .md, .pdf, .py, .java, .js, .ts)",
            type=["txt", "md", "pdf", "py", "java", "js", "ts"],
        )

        if uploaded_file is not None:
            if st.button("🚀 开始编译", key="ingest_file_btn"):
                with st.spinner("正在编译知识..."):
                    # 保存到 raw_sources
                    raw_path = Path(__file__).parent / "raw_sources" / uploaded_file.name
                    raw_path.write_bytes(uploaded_file.getvalue())
                    # 执行摄入
                    result = ingest_agent.ingest(str(raw_path))

                if result["status"] == "success":
                    st.success(f"✅ 知识编译完成！处理了 {result['entities_processed']} 个实体")

                    for r in result.get("results", []):
                        icon = "🆕" if r["action"] == "created" else "🔄"
                        st.markdown(f"- {icon} **`{r['entity']}`**: {r['action']}")

                    if result.get("conflicts"):
                        st.warning("⚠️ 检测到以下冲突：")
                        for c in result["conflicts"]:
                            st.markdown(f"- ⚡ `{c['entity']}`: {c.get('description', '')}")

                    st.info(f"📊 累计统计: 🆕 新建 {result['stats']['pages_created']} | 🔄 更新 {result['stats']['pages_updated']} | ⚡ 冲突 {result['stats']['conflicts_detected']}")
                else:
                    st.error(f"❌ 编译失败: {result.get('error', '未知错误')}")

    # Tab 2: 手动输入
    with tab2:
        st.subheader("手动输入知识内容")
        title = st.text_input("文档标题", placeholder="例如: Transformer 架构详解")
        content = st.text_area(
            "文档内容 (支持 Markdown 格式)",
            height=300,
            placeholder="在此粘贴或输入文档内容...",
        )

        if st.button("🚀 开始编译", key="ingest_text_btn") and title and content:
            with st.spinner("正在编译知识..."):
                # 保存到 raw_sources
                safe_title = "".join(c if c.isalnum() or c in " _-" else "_" for c in title)
                temp_file = Path(__file__).parent / "raw_sources" / f"{safe_title}_{datetime.now().strftime('%Y%m%d%H%M%S')}.md"
                temp_file.write_text(content, encoding="utf-8")
                result = ingest_agent.ingest(str(temp_file))

            if result["status"] == "success":
                st.success(f"✅ 知识编译完成！")
                for r in result.get("results", []):
                    icon = "🆕" if r["action"] == "created" else "🔄"
                    st.markdown(f"- {icon} **`{r['entity']}`**: {r['action']}")
            else:
                st.error(f"❌ 编译失败: {result.get('error', '未知错误')}")

    # Tab 3: 批量摄入
    with tab3:
        st.subheader("批量摄入文档目录")
        dir_path = st.text_input(
            "文档目录路径",
            placeholder="例如: D:/papers",
            value=str(Path(__file__).parent / "raw_sources"),
        )

        if st.button("🚀 批量编译", key="ingest_dir_btn"):
            with st.spinner("正在批量编译知识..."):
                results = ingest_agent.ingest_directory(dir_path)

            success_count = sum(1 for r in results if r["result"].get("status") == "success")
            st.success(f"✅ 批量编译完成！{success_count}/{len(results)} 个文件成功")

            for r in results:
                status_icon = "✅" if r["result"].get("status") == "success" else "❌"
                entities = r["result"].get("entities_processed", 0)
                st.markdown(f"- {status_icon} **{r['file']}**: 处理 {entities} 个实体")


# ============================================================
# 页面: 知识检索
# ============================================================

def render_query():
    st.title("🔍 知识检索")
    st.markdown("基于 Wiki 图拓扑的 PageRank 增强检索")

    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("💬 输入你的问题", placeholder="例如: 什么是 Transformer？")
    with col2:
        top_n = st.slider("Top-N 结果", min_value=1, max_value=10, value=5)

    col1, col2 = st.columns([1, 1])
    with col1:
        search_btn = st.button("🔍 检索知识", use_container_width=True)
    with col2:
        answer_btn = st.button("💡 生成回答", use_container_width=True)

    if search_btn and query:
        with st.spinner("正在检索知识..."):
            result = query_agent.search(query, top_n=top_n)

        if result.get("error"):
            st.warning(f"⚠️ {result['error']}")
        else:
            st.success(f"✅ 找到 {len(result.get('found_entities', []))} 个相关实体")

            # 显示匹配实体
            if result.get("found_entities"):
                st.subheader("🎯 匹配实体")
                st.markdown("、".join(f"`{e}`" for e in result["found_entities"]))

            # 显示图路径
            if result.get("graph_paths"):
                st.subheader("🛤️ 知识图谱路径")
                for path in result["graph_paths"][:5]:
                    st.markdown(f"- {path['from']} → ... → {path['to']}: `{path['path']}`")

            # 显示结果页面
            if result.get("pages_used"):
                st.subheader(f"📄 相关页面 (Top-{len(result['pages_used'])})")
                for p in result["pages_used"]:
                    with st.expander(f"📄 {p['name']} (得分: {p['score']:.4f})"):
                        page_content = query_agent._read_page(p["name"])
                        if page_content:
                            st.markdown(page_content)
                        else:
                            st.info("页面内容为空")

            # 显示推荐
            if result.get("related_recommendations"):
                st.subheader("💡 推荐探索")
                cols = st.columns(len(result["related_recommendations"][:3]))
                for i, rec in enumerate(result["related_recommendations"][:3]):
                    with cols[i]:
                        st.info(f"**{rec['name']}**\n\n得分: {rec['score']:.4f}")

    if answer_btn and query:
        with st.spinner("正在生成回答..."):
            result = query_agent.search_with_answer(query, top_n=top_n)

        if result.get("error"):
            st.warning(f"⚠️ {result['error']}")
        else:
            st.subheader("💡 回答")
            answer = result.get("answer", "")
            st.markdown(answer)

            with st.expander("📚 查看检索来源"):
                for p in result.get("pages_used", []):
                    st.markdown(f"- `{p['name']}` (得分: {p['score']:.4f})")


# ============================================================
# 页面: 知识审计
# ============================================================

def render_lint():
    st.title("🔎 知识审计")
    st.markdown("知识网络健康检查 — 死链检测 · 冲突发现 · 幻觉识别 · 自动修复")

    col1, col2 = st.columns([2, 1])
    with col1:
        auto_fix = st.checkbox("🔧 启用自动修复", value=True, help="自动为被引用但缺失的页面创建 Stub")
    with col2:
        run_btn = st.button("🚀 运行完整审计", use_container_width=True, type="primary")

    if run_btn:
        with st.spinner("正在审计知识库..."):
            progress_bar = st.progress(0)
            report = lint_agent.run_full_audit(auto_fix=auto_fix)
            progress_bar.progress(100)

        # 评分卡片
        scores = report.get("scores", {})
        st.subheader("📊 健康评分")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📚 知识完整性", f"{scores.get('completeness', 0)}/100")
        with col2:
            st.metric("🔗 链接健康度", f"{scores.get('link_health', 0)}/100")
        with col3:
            st.metric("⚖️ 知识一致性", f"{scores.get('consistency', 0)}/100")

        st.markdown("---")

        # 死链
        broken = report.get("broken_links", [])
        with st.expander(f"🔗 死链报告 ({len(broken)} 个)", expanded=len(broken) > 0):
            if broken:
                for b in broken[:20]:
                    st.markdown(f"- ❌ `{b['source_page']}` → `[[{b['broken_target']}]]`")
                if len(broken) > 20:
                    st.info(f"... 还有 {len(broken) - 20} 个死链未显示")
            else:
                st.success("✅ 未发现死链")

        # 孤立节点
        orphans = report.get("orphan_pages", [])
        with st.expander(f"🏝️ 孤立节点报告 ({len(orphans)} 个)", expanded=len(orphans) > 0):
            if orphans:
                for p in orphans[:20]:
                    st.markdown(f"- 🏝️ `{p}`")
                if len(orphans) > 20:
                    st.info(f"... 还有 {len(orphans) - 20} 个孤立节点未显示")
            else:
                st.success("✅ 无孤立节点")

        # 冲突
        conflicts = report.get("conflicts", [])
        with st.expander(f"⚡ 冲突报告 ({len(conflicts)} 个)", expanded=len(conflicts) > 0):
            if conflicts:
                for c in conflicts[:10]:
                    st.markdown(f"- ⚡ `{c.get('page_a', '?')}` ↔ `{c.get('page_b', '?')}`: {c.get('description', '')[:200]}")
            else:
                st.success("✅ 未发现知识冲突")

        # 幻觉
        hallucinations = report.get("hallucinations", [])
        with st.expander(f"👻 幻觉报告 ({len(hallucinations)} 个)", expanded=len(hallucinations) > 0):
            if hallucinations:
                for h in hallucinations[:10]:
                    st.markdown(f"- 👻 `{h.get('page', '?')}`: {h.get('content', '')[:150]}")
            else:
                st.success("✅ 未发现幻觉内容")

        # 自动修复
        fixes = report.get("auto_fixes", [])
        if fixes:
            st.subheader("🔧 自动修复操作")
            for f in fixes:
                st.markdown(f"- ✅ {f.get('description', '')}")

        # 摘要
        st.markdown("---")
        st.subheader("📋 审计摘要")
        st.info(report.get("summary", ""))

    # 显示上次审计报告
    else:
        report = lint_agent.get_report()
        if "error" not in report:
            st.info(f"📋 上次审计时间: {report.get('timestamp', '未知')}")
            scores = report.get("scores", {})
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("完整性", f"{scores.get('completeness', 0)}/100")
            with col2:
                st.metric("链接健康度", f"{scores.get('link_health', 0)}/100")
            with col3:
                st.metric("一致性", f"{scores.get('consistency', 0)}/100")
        else:
            st.info("💡 尚未运行审计，点击上方按钮开始首次审计")


# ============================================================
# 页面: 知识图谱
# ============================================================

def render_graph():
    st.title("🌐 知识图谱")
    st.markdown("Wiki 知识网络的拓扑结构可视化")

    graph_file = VAULT_PATH / "index_graph.json"
    if not graph_file.exists():
        st.warning("⚠️ 知识图谱为空，请先摄入一些文档")
        return

    data = json.loads(graph_file.read_text(encoding="utf-8"))
    nodes = data.get("nodes", [])
    edges = data.get("edges", [])

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📌 节点", len(nodes))
    with col2:
        st.metric("🔗 边", len(edges))
    with col3:
        st.metric("📊 密度", f"{2 * len(edges) / max(1, len(nodes) * (len(nodes) - 1)):.4f}" if len(nodes) > 1 else "N/A")

    st.markdown("---")

    if nodes:
        st.subheader("知识图谱数据")

        # 节点列表
        with st.expander("📌 节点列表", expanded=False):
            for n in nodes:
                st.markdown(f"- **{n['id']}** ({n.get('type', 'concept')})")

        # 边列表
        with st.expander("🔗 边列表", expanded=False):
            for e in edges[:50]:
                st.markdown(f"- `{e['source']}` → `{e['target']}` ({e.get('relation', 'references')})")
            if len(edges) > 50:
                st.info(f"... 还有 {len(edges) - 50} 条边未显示")

        # 力导向图（使用 Mermaid）
        st.subheader("🌐 知识图谱可视化")
        mermaid_code = "graph TD\n"
        for e in edges[:30]:  # 限制显示数量
            mermaid_code += f"    {e['source']} --> {e['target']}\n"
        
        if len(edges) > 30:
            mermaid_code += f"    %% ... 还有 {len(edges) - 30} 条边未显示\n"

        st.markdown(f"```mermaid\n{mermaid_code}\n```")
    else:
        st.info("知识图谱为空")


# ============================================================
# 页面: 页面浏览
# ============================================================

def render_pages():
    st.title("📄 页面浏览")
    st.markdown("浏览知识库中的所有 Markdown 页面")

    topics = query_agent.list_topics()

    if not topics:
        st.warning("⚠️ 知识库为空，请先在「知识摄入」页面添加文档")
        return

    # 选择页面
    selected = st.selectbox("选择要查看的页面", topics)

    if selected:
        page_content = query_agent._read_page(selected)
        if page_content:
            st.markdown("---")
            st.markdown(page_content)

            # 提取并显示 wikilinks
            import re
            links = re.findall(r'\[\[(.*?)\]\]', page_content)
            if links:
                st.markdown("---")
                st.subheader("🔗 页面中的双向链接")
                for link in links:
                    link_name = link.split("|")[0].strip()
                    st.markdown(f"- `[[{link}]]`")
        else:
            st.error(f"无法读取页面 '{selected}'")


# ============================================================
# 路由
# ============================================================

if page == "📊 仪表盘":
    render_dashboard()
elif page == "📥 知识摄入":
    render_ingest()
elif page == "🔍 知识检索":
    render_query()
elif page == "🔎 知识审计":
    render_lint()
elif page == "🌐 知识图谱":
    render_graph()
elif page == "📄 页面浏览":
    render_pages()

# ============================================================
# 页脚
# ============================================================

st.markdown("---")
st.caption(
    "🧠 LLM Wiki — 基于 Karpathy Knowledge Compilation 范式 | "
    "🔄 增量编译 · 图增强检索 · 链接审计 | "
    f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}"
)
