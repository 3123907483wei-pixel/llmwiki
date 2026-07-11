"""
Query Agent — 基于 Wiki 图拓扑的 PageRank 增强检索

核心职责：
1. 从 index_graph.json 加载图拓扑并构建 NetworkX 图
2. 根据用户查询关键词匹配初始实体节点
3. 运行个性化 PageRank（Personalized PageRank）计算关联度
4. 读取 Top-N 相关页面的 Markdown 内容
5. 组装上下文并调用 LLM 生成带引用的回答
"""

import os
import re
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from difflib import SequenceMatcher


class QueryAgent:
    """知识检索 Agent — 基于 Wiki 图拓扑的 PageRank 增强检索"""

    def __init__(self, vault_path: str = "./wiki_vault", llm_api_func=None):
        """
        初始化 Query Agent

        Args:
            vault_path: Wiki 知识库根目录
            llm_api_func: LLM API 调用函数（可选，用于答案合成）
        """
        self.vault_path = Path(vault_path)
        self.pages_path = self.vault_path / "pages"
        self.graph_file = self.vault_path / "index_graph.json"
        self.llm_api = llm_api_func

        # NetworkX 图对象（延迟加载）
        self.G = None
        self._graph_loaded = False

        # 缓存
        self._page_cache: Dict[str, str] = {}
        self._node_list: List[str] = []

    # ============================================================
    # 公开接口
    # ============================================================

    def search(self, query: str, top_n: int = 5, damping_factor: float = 0.85) -> Dict:
        """
        执行知识检索

        Args:
            query: 用户查询字符串
            top_n: 返回的 Top-N 相关页面数
            damping_factor: PageRank 阻尼系数

        Returns:
            包含检索结果和上下文的字典
        """
        # 1. 确保图已加载
        self._ensure_graph_loaded()

        if not self.G or self.G.number_of_nodes() == 0:
            return {
                "query": query,
                "found_entities": [],
                "context": "",
                "graph_paths": [],
                "related_recommendations": [],
                "pages_used": [],
                "error": "知识库为空，请先摄入文档",
            }

        # 2. 匹配初始实体节点
        matched_entities = self._match_entities(query)
        if not matched_entities:
            return {
                "query": query,
                "found_entities": [],
                "context": "",
                "graph_paths": [],
                "related_recommendations": [],
                "pages_used": [],
                "error": f"未找到与 '{query}' 相关的知识实体",
            }

        # 3. 运行个性化 PageRank
        scored_nodes = self._personalized_pagerank(matched_entities, damping_factor)

        # 4. 获取 Top-N 页面内容
        top_nodes = scored_nodes[:top_n]
        context_parts = []
        pages_used = []

        for node_name, score in top_nodes:
            content = self._read_page(node_name)
            if content:
                context_parts.append(f"## 📄 {node_name}\n> 关联得分: {score:.4f}\n\n{content}")
                pages_used.append({"name": node_name, "score": score})

        # 5. 发现图路径
        graph_paths = self._find_graph_paths(matched_entities, top_nodes)

        # 6. 相关推荐（基于 PageRank 结果中未选中的节点）
        related = [{"name": n, "score": s} for n, s in scored_nodes[top_n:top_n + 5]]

        context = "\n\n---\n\n".join(context_parts)

        return {
            "query": query,
            "found_entities": matched_entities,
            "context": context,
            "graph_paths": graph_paths,
            "related_recommendations": related,
            "pages_used": pages_used,
            "error": None,
        }

    def search_with_answer(self, query: str, top_n: int = 5) -> Dict:
        """
        检索知识并生成自然语言回答（需要 LLM API）

        Args:
            query: 用户查询
            top_n: 检索的页面数

        Returns:
            包含检索结果和 LLM 回答的字典
        """
        result = self.search(query, top_n=top_n)

        if result["error"]:
            return result

        if self.llm_api and result["context"]:
            from schema.query_skill import ANSWER_SYNTHESIS_PROMPT
            prompt = ANSWER_SYNTHESIS_PROMPT.format(
                wiki_context=result["context"][:12000],
                graph_paths=json.dumps(result["graph_paths"], ensure_ascii=False, indent=2),
                user_query=query,
            )
            answer = self.llm_api(prompt)
            result["answer"] = answer
        else:
            # 无 LLM 时返回上下文摘要
            result["answer"] = self._generate_summary_answer(result)

        return result

    def list_topics(self) -> List[str]:
        """列出知识库中所有可用的主题"""
        self._ensure_graph_loaded()
        if self._node_list:
            return sorted(self._node_list)
        return self._list_pages()

    def get_stats(self) -> Dict:
        """获取知识库统计信息"""
        import networkx as nx

        self._ensure_graph_loaded()
        if self.G:
            return {
                "total_nodes": self.G.number_of_nodes(),
                "total_edges": self.G.number_of_edges(),
                "total_pages": len(self._list_pages()),
                "graph_density": nx.density(self.G) if self.G else 0,
            }
        return {
            "total_nodes": 0,
            "total_edges": 0,
            "total_pages": len(self._list_pages()),
            "graph_density": 0,
        }

    # ============================================================
    # 内部方法
    # ============================================================

    def _ensure_graph_loaded(self):
        """确保图拓扑已加载"""
        if not self._graph_loaded:
            self._load_graph()

    def _load_graph(self):
        """从 index_graph.json 加载图拓扑"""
        import networkx as nx

        self.G = nx.DiGraph()

        if self.graph_file.exists():
            try:
                data = json.loads(self.graph_file.read_text(encoding="utf-8"))
                for node in data.get("nodes", []):
                    self.G.add_node(node["id"], **{k: v for k, v in node.items() if k != "id"})
                for edge in data.get("edges", []):
                    self.G.add_edge(edge["source"], edge["target"], relation=edge.get("relation", "references"))
            except Exception as e:
                print(f"⚠️  加载图索引失败: {e}")

        # 如果图为空，尝试从 pages 目录重建
        if self.G.number_of_nodes() == 0:
            self._rebuild_graph_from_pages()

        self._node_list = list(self.G.nodes)
        self._graph_loaded = True

    def _rebuild_graph_from_pages(self):
        """从 pages 目录中的 wikilinks 重建图"""
        import networkx as nx

        for md_file in self.pages_path.glob("*.md"):
            entity = md_file.stem
            self.G.add_node(entity)
            content = md_file.read_text(encoding="utf-8")
            links = re.findall(r'\[\[(.*?)\]\]', content)
            for target in links:
                target = target.split("|")[0].strip()
                if target:
                    self.G.add_node(target)
                    self.G.add_edge(entity, target, relation="references")

    def _list_pages(self) -> List[str]:
        """列出 pages 目录中的所有 Markdown 文件"""
        if not self.pages_path.exists():
            return []
        return sorted([f.stem for f in self.pages_path.glob("*.md")])

    def _match_entities(self, query: str) -> List[str]:
        """
        将用户查询匹配到知识库中的实体

        使用多策略匹配:
        1. 精确匹配
        2. 子串匹配
        3. 模糊匹配（SequenceMatcher）
        """
        query_lower = query.lower()
        all_nodes = self._node_list
        matched = set()

        # 策略 1: 精确匹配（大小写不敏感）
        for node in all_nodes:
            if node.lower() == query_lower:
                matched.add(node)

        # 策略 2: 子串匹配
        query_words = set(re.findall(r'[a-zA-Z_]\w*', query_lower))
        for node in all_nodes:
            node_lower = node.lower()
            if node_lower in query_lower or query_lower in node_lower:
                matched.add(node)
            # 检查查询词是否包含节点名
            for word in query_words:
                if word == node_lower or (len(word) > 3 and word in node_lower):
                    matched.add(node)

        # 策略 3: 模糊匹配（对短查询）
        if not matched and len(query) > 2:
            for node in all_nodes:
                ratio = SequenceMatcher(None, query_lower, node.lower()).ratio()
                if ratio > 0.6:
                    matched.add(node)

        return list(matched)

    def _personalized_pagerank(self, seed_entities: List[str], damping: float = 0.85) -> List[Tuple[str, float]]:
        """
        运行个性化 PageRank（Personalized PageRank）

        以匹配到的实体为起点，计算全图节点与查询的相关性得分
        """
        import networkx as nx

        if not seed_entities:
            return []

        # 构建个性化向量：种子节点获得非零权重
        personalization = {node: 0.0 for node in self.G.nodes}

        # 确保种子节点存在于图中
        valid_seeds = [s for s in seed_entities if s in personalization]
        if not valid_seeds:
            # 如果种子不在图中，用所有节点
            return sorted(
                [(n, 1.0 / max(1, self.G.number_of_nodes())) for n in self.G.nodes],
                key=lambda x: x[1],
                reverse=True,
            )

        seed_weight = 1.0 / len(valid_seeds)
        for seed in valid_seeds:
            personalization[seed] = seed_weight

        try:
            scores = nx.pagerank(
                self.G,
                personalization=personalization,
                alpha=damping,
                max_iter=100,
                tol=1e-6,
            )
        except Exception:
            # 如果 PageRank 失败，回退到度中心性
            scores = dict(self.G.degree())

        # 按得分降序排列
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_scores

    def _read_page(self, entity_name: str) -> Optional[str]:
        """读取实体页面的 Markdown 内容"""
        if entity_name in self._page_cache:
            return self._page_cache[entity_name]

        page_file = self.pages_path / f"{entity_name}.md"
        if page_file.exists():
            content = page_file.read_text(encoding="utf-8")
            self._page_cache[entity_name] = content
            return content
        return None

    def _find_graph_paths(self, seed_entities: List[str], top_nodes: List[Tuple[str, float]]) -> List[Dict]:
        """发现种子实体到结果实体之间的图路径"""
        import networkx as nx

        paths = []
        for node_name, _ in top_nodes:
            node_paths = []
            for seed in seed_entities:
                if seed != node_name:
                    try:
                        path = nx.shortest_path(self.G, source=seed, target=node_name)
                        node_paths.append({"from": seed, "to": node_name, "path": " → ".join(path)})
                    except (nx.NetworkXNoPath, nx.NodeNotFound):
                        pass
            if node_paths:
                paths.extend(node_paths)
        return paths

    def _generate_summary_answer(self, result: Dict) -> str:
        """当 LLM 不可用时，生成基于模板的摘要回答"""
        entities = result.get("found_entities", [])
        pages_used = result.get("pages_used", [])

        answer = f"## 📖 检索结果\n\n"
        answer += f"**查询**: {result['query']}\n\n"
        answer += f"**匹配实体**: {', '.join(f'`{e}`' for e in entities)}\n\n"

        if pages_used:
            answer += "### 相关页面（按相关性排序）\n"
            for p in pages_used:
                answer += f"- `{p['name']}` (得分: {p['score']:.4f})\n"

        recs = result.get("related_recommendations", [])
        if recs:
            answer += "\n### 推荐探索\n"
            for r in recs[:3]:
                answer += f"- `{r['name']}`\n"

        return answer


# ============================================================
# 便捷函数
# ============================================================

def create_query_agent(vault_path: str = "./wiki_vault", llm_api_func=None) -> QueryAgent:
    """创建并返回一个配置好的 Query Agent 实例"""
    return QueryAgent(vault_path=vault_path, llm_api_func=llm_api_func)
