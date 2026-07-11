"""
Ingest Agent — 知识摄入与增量编译

核心职责：
1. 解析多源文档（PDF/TXT/MD/代码），提取文字内容
2. 调用 LLM 提取核心技术实体并识别关系
3. 与已有知识库比对，执行知识融合或新建页面
4. 建立 [[wikilinks]] 双向链接
5. 更新全局图拓扑索引
"""

import os
import re
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple


class IngestAgent:
    """知识摄入编译器 — 将原始文档编译为结构化的 Wiki 知识网络"""

    def __init__(self, vault_path: str = "./wiki_vault", llm_api_func=None):
        """
        初始化 Ingest Agent

        Args:
            vault_path: Wiki 知识库根目录
            llm_api_func: LLM API 调用函数，接收 prompt 返回响应文本
                         若为 None，则使用模拟模式（用于演示/测试）
        """
        self.vault_path = Path(vault_path)
        self.pages_path = self.vault_path / "pages"
        self.raw_path = Path("./raw_sources")
        self.llm_api = llm_api_func

        # 确保目录存在
        self.pages_path.mkdir(parents=True, exist_ok=True)
        self.raw_path.mkdir(parents=True, exist_ok=True)

        self.state = "init"
        self.stats = {
            "pages_created": 0,
            "pages_updated": 0,
            "links_added": 0,
            "conflicts_detected": 0,
        }

    # ============================================================
    # 公开接口
    # ============================================================

    def ingest(self, file_path: str) -> Dict:
        """
        摄入单个文档：解析 → 提取 → 融合 → 索引

        Args:
            file_path: 源文档路径（PDF/TXT/MD）

        Returns:
            包含摄入结果的字典
        """
        self.state = "extracting"
        source_path = Path(file_path)

        # 1. 复制源文件到 raw_sources
        raw_dest = self._archive_source(source_path)

        # 2. 读取并解析文档内容
        source_content = self._read_source(source_path)
        if not source_content.strip():
            return {"status": "failed", "error": "Empty source content"}

        # 3. 获取已有知识库实体列表
        existing_entities = self._list_existing_entities()

        # 4. 调用 LLM 提取实体（或使用模拟）
        self.state = "comparing"
        extraction = self._extract_entities(source_content, existing_entities)

        if not extraction or "entities" not in extraction:
            return {"status": "failed", "error": "Entity extraction failed"}

        # 5. 对每个实体执行编译（新建或融合）
        self.state = "merging"
        results = []
        for entity in extraction.get("entities", []):
            result = self._compile_entity(entity, source_content)
            results.append(result)

        # 6. 更新全局图索引
        self.state = "updating_graph"
        self._build_graph_index()

        # 7. 记录变更日志
        self._append_to_log(extraction, results)

        self.state = "completed"
        return {
            "status": "success",
            "source": str(raw_dest),
            "entities_processed": len(extraction.get("entities", [])),
            "results": results,
            "stats": self.stats,
            "conflicts": extraction.get("conflict_flags", []),
        }

    def ingest_directory(self, dir_path: str) -> List[Dict]:
        """
        批量摄入目录中的所有文档

        Args:
            dir_path: 包含源文档的目录

        Returns:
            每个文档的摄入结果列表
        """
        dir_path = Path(dir_path)
        results = []
        supported_extensions = {".txt", ".md", ".pdf", ".py", ".java", ".js", ".ts", ".json"}

        for file_path in sorted(dir_path.glob("*")):
            if file_path.suffix.lower() in supported_extensions:
                print(f"📄 正在摄入: {file_path.name}")
                result = self.ingest(str(file_path))
                results.append({"file": file_path.name, "result": result})

        return results

    def get_status(self) -> Dict:
        """获取 Agent 当前状态和统计信息"""
        return {
            "state": self.state,
            "stats": self.stats,
            "total_pages": len(self._list_existing_entities()),
            "vault_path": str(self.vault_path),
        }

    # ============================================================
    # 内部方法
    # ============================================================

    def _archive_source(self, source_path: Path) -> Path:
        """将源文件复制到 raw_sources 目录"""
        dest = self.raw_path / source_path.name
        # 避免重名覆盖
        if dest.exists():
            stem = dest.stem
            suffix = dest.suffix
            dest = self.raw_path / f"{stem}_{datetime.now().strftime('%Y%m%d%H%M%S')}{suffix}"

        try:
            content = source_path.read_bytes()
            dest.write_bytes(content)
        except Exception:
            # 如果无法读取（如 PDF 需要特殊处理），尝试读文本
            try:
                content = source_path.read_text(encoding="utf-8")
                dest.write_text(content, encoding="utf-8")
            except Exception:
                pass

        return dest

    def _read_source(self, source_path: Path) -> str:
        """读取源文档内容"""
        ext = source_path.suffix.lower()

        try:
            if ext == ".pdf":
                return self._read_pdf(source_path)
            else:
                return source_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            print(f"⚠️  读取文件失败 {source_path.name}: {e}")
            return ""

    def _read_pdf(self, pdf_path: Path) -> str:
        """使用 PyMuPDF 读取 PDF（如果可用）；否则回退到基础读取"""
        try:
            import fitz  # PyMuPDF
            text = []
            doc = fitz.open(str(pdf_path))
            for page_num, page in enumerate(doc):
                text.append(f"--- 第 {page_num + 1} 页 ---\n{page.get_text()}")
            doc.close()
            return "\n".join(text)
        except ImportError:
            # 回退：尝试 pdfminer
            try:
                from pdfminer.high_level import extract_text
                return extract_text(str(pdf_path))
            except ImportError:
                return f"[PDF 文件: {pdf_path.name}，请安装 PyMuPDF 或 pdfminer.six 以提取文本]"

    def _list_existing_entities(self) -> List[str]:
        """列出知识库中已有的实体（页面文件名）"""
        if not self.pages_path.exists():
            return []
        return sorted([f.stem for f in self.pages_path.glob("*.md")])

    def _extract_entities(self, content: str, existing_entities: List[str]) -> Optional[Dict]:
        """调用 LLM 提取实体，或使用模拟提取"""
        if self.llm_api:
            # 使用真实的 LLM API
            from schema.ingest_skill import EXTRACT_ENTITIES_PROMPT
            prompt = EXTRACT_ENTITIES_PROMPT.format(
                source_content=content[:8000],  # 限制上下文长度
                existing_entities=json.dumps(existing_entities, ensure_ascii=False),
            )
            response = self.llm_api(prompt)
            try:
                # 尝试从响应中提取 JSON
                json_match = re.search(r"```json\n(.*?)\n```", response, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group(1))
                return json.loads(response)
            except json.JSONDecodeError:
                print("⚠️  LLM 响应解析失败，使用模拟提取")
                return self._simulate_extraction(content, existing_entities)
        else:
            # 模拟提取（演示模式）
            return self._simulate_extraction(content, existing_entities)

    def _simulate_extraction(self, content: str, existing_entities: List[str]) -> Dict:
        """模拟 LLM 实体提取（用于演示/测试）"""
        # 从内容中提取可能的实体名（简单的关键词提取）
        words = re.findall(r'\b[A-Z][a-z]*(?:[A-Z][a-z]*)*\b', content)
        # 过滤常见词
        stop_words = {'The', 'This', 'That', 'These', 'Those', 'We', 'Our', 'Their'}
        candidates = [w for w in words if w not in stop_words and len(w) > 3]
        # 去重并按频率排序
        from collections import Counter
        freq = Counter(candidates)
        top_candidates = [w for w, _ in freq.most_common(10)]

        entities = []
        for i, name in enumerate(top_candidates[:5]):
            is_new = name not in existing_entities
            entities.append({
                "name": name,
                "is_new": is_new,
                "summary": f"关于 {name} 的核心技术概念",
                "key_points": [f"{name} 的关键特性", f"{name} 的应用场景"],
                "related_entities": [c for c in top_candidates[:5] if c != name][:3],
                "relationship_type": "依赖",
            })

        return {
            "entities": entities,
            "conflict_flags": [],
            "source_metadata": {
                "title": "Auto-detected Document",
                "type": "unknown",
                "key_findings": [f"检测到 {len(entities)} 个潜在实体"],
            },
        }

    def _compile_entity(self, entity: Dict, source_content: str) -> Dict:
        """编译单个实体：新建页面或融合到现有页面"""
        entity_name = entity["name"]
        target_file = self.pages_path / f"{entity_name}.md"

        if entity["is_new"]:
            # 创建新页面
            page_content = self._generate_new_page(entity)
            with open(target_file, "w", encoding="utf-8") as f:
                f.write(page_content)
            self.stats["pages_created"] += 1
            return {"entity": entity_name, "action": "created"}
        else:
            # 融合到现有页面
            if target_file.exists():
                existing_content = target_file.read_text(encoding="utf-8")
                merged_content = self._merge_knowledge(existing_content, entity, source_content)
                with open(target_file, "w", encoding="utf-8") as f:
                    f.write(merged_content)
                self.stats["pages_updated"] += 1
                return {"entity": entity_name, "action": "merged"}
            else:
                # 存在列表中但文件不存在，创建之
                page_content = self._generate_new_page(entity)
                with open(target_file, "w", encoding="utf-8") as f:
                    f.write(page_content)
                self.stats["pages_created"] += 1
                return {"entity": entity_name, "action": "created"}

    def _generate_new_page(self, entity: Dict) -> str:
        """生成新的 Markdown 知识页面"""
        entity_name = entity["name"]
        summary = entity.get("summary", "")
        key_points = entity.get("key_points", [])
        related = entity.get("related_entities", [])

        # 构建 wikilinks
        related_links = ", ".join(f"[[{r}]]" for r in related)
        key_points_bullets = "\n".join(f"* {p}" for p in key_points)

        # 生成内容摘要哈希作为内容标识
        content_hash = hashlib.md5(
            (entity_name + summary + str(datetime.now())).encode()
        ).hexdigest()[:8]

        page = f"""# {entity_name}

> {summary}
>
> *最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M')} | 内容 ID: {content_hash}*

---

## 概述

{entity_name} 是 AI/ML 领域的重要概念。

## 核心要点

{key_points_bullets}

## 关联概念

{related_links}

## 详细说明

{entity_name} 的相关技术细节将在后续更新中逐步补充。

## 参考文献

* 来源: LLM Wiki 知识编译系统 — 自动生成
* 编译时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}

---

*此页面由 Ingest Agent 自动编译生成*
"""
        return page

    def _merge_knowledge(self, existing: str, entity: Dict, source_content: str) -> str:
        """将新知识融合到现有 Markdown 页面"""
        entity_name = entity["name"]

        if self.llm_api:
            # 使用 LLM 进行智能融合
            from schema.ingest_skill import MERGE_KNOWLEDGE_PROMPT
            prompt = MERGE_KNOWLEDGE_PROMPT.format(
                existing_page=existing,
                new_knowledge=json.dumps(entity, ensure_ascii=False, indent=2),
            )
            merged = self.llm_api(prompt)
            if merged and len(merged) > 50:
                return merged

        # 回退：基于规则的融合
        return self._rule_based_merge(existing, entity)

    def _rule_based_merge(self, existing: str, entity: Dict) -> str:
        """基于规则的简单融合（当 LLM 不可用时）"""
        entity_name = entity["name"]
        key_points = entity.get("key_points", [])
        related = entity.get("related_entities", [])

        # 添加更新标记
        update_note = (
            f"\n\n---\n"
            f"## 🔄 增量更新 ({datetime.now().strftime('%Y-%m-%d %H:%M')})\n\n"
            f"### 新增要点\n"
        )
        for point in key_points:
            update_note += f"* [Updated] {point}\n"

        if related:
            update_note += f"\n### 新增关联\n"
            for rel in related:
                rel_link = f"[[{rel}]]"
                if rel_link not in existing:
                    update_note += f"* 关联: {rel_link}\n"

        update_note += f"\n*此更新由 Ingest Agent 自动执行*\n"

        return existing + update_note

    def _build_graph_index(self):
        """从所有 Wiki 页面重建全局图拓扑索引"""
        graph_file = self.vault_path / "index_graph.json"
        nodes = []
        edges = []

        # 扫描所有页面，提取 wikilinks
        for md_file in sorted(self.pages_path.glob("*.md")):
            entity_name = md_file.stem
            nodes.append({
                "id": entity_name,
                "label": entity_name,
                "type": "concept",
            })

            content = md_file.read_text(encoding="utf-8")
            # 提取 [[wikilinks]]
            links = re.findall(r'\[\[(.*?)\]\]', content)
            for target in links:
                target = target.split("|")[0].strip()  # 处理 [[target|alias]] 格式
                if target and target != entity_name:
                    edges.append({
                        "source": entity_name,
                        "target": target,
                        "relation": "references",
                    })
                    self.stats["links_added"] = len(edges)

        index_data = {
            "metadata": {
                "version": "1.0",
                "updated_at": datetime.now().isoformat(),
                "node_count": len(nodes),
                "edge_count": len(edges),
            },
            "nodes": nodes,
            "edges": edges,
        }

        with open(graph_file, "w", encoding="utf-8") as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)

    def _append_to_log(self, extraction: Dict, results: List[Dict]):
        """将变更记录追加到变更日志"""
        log_file = self.vault_path / "change_log.md"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        log_entry = f"\n## {timestamp}\n"
        log_entry += f"- 摄入来源: {extraction.get('source_metadata', {}).get('title', '未知')}\n"
        log_entry += f"- 处理实体数: {len(results)}\n"
        for r in results:
            action_emoji = "🆕" if r["action"] == "created" else "🔄"
            log_entry += f"  - {action_emoji} `{r['entity']}`: {r['action']}\n"

        conflicts = extraction.get("conflict_flags", [])
        if conflicts:
            log_entry += f"- ⚠️ 检测到 {len(conflicts)} 个潜在冲突\n"
            for c in conflicts:
                log_entry += f"  - ⚡ `{c['entity']}`: {c.get('description', '')}\n"

        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_entry)


# ============================================================
# 便捷函数
# ============================================================

def create_ingest_agent(vault_path: str = "./wiki_vault", llm_api_func=None) -> IngestAgent:
    """创建并返回一个配置好的 Ingest Agent 实例"""
    return IngestAgent(vault_path=vault_path, llm_api_func=llm_api_func)
