"""
Lint Agent — 知识网络的链接审计与健康检查

核心职责：
1. 死链检测：扫描 [[wikilinks]]，发现指向不存在页面的引用
2. 孤立节点检测：发现没有被任何页面引用的页面
3. 冲突检测：对比不同页面的同一概念，发现矛盾陈述
4. Stub 创建：为被引用但缺失的页面自动创建占位页面
5. 生成审计报告与健康评分
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from collections import defaultdict


class LintAgent:
    """知识库审计 Agent — 确保知识网络的健康与一致性"""

    def __init__(self, vault_path: str = "./wiki_vault", llm_api_func=None):
        """
        初始化 Lint Agent

        Args:
            vault_path: Wiki 知识库根目录
            llm_api_func: LLM API 调用函数（可选，用于智能冲突/幻觉检测）
        """
        self.vault_path = Path(vault_path)
        self.pages_path = self.vault_path / "pages"
        self.graph_file = self.vault_path / "index_graph.json"
        self.llm_api = llm_api_func

        # 审计结果缓存
        self._broken_links: List[Dict] = []
        self._orphan_pages: List[str] = []
        self._conflicts: List[Dict] = []
        self._hallucinations: List[Dict] = []
        self._auto_fixes: List[Dict] = []

    # ============================================================
    # 公开接口
    # ============================================================

    def run_full_audit(self, auto_fix: bool = True) -> Dict:
        """
        执行完整的知识库审计

        Args:
            auto_fix: 是否自动修复可修复的问题

        Returns:
            包含审计结果的字典
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "vault_path": str(self.vault_path),
            "total_pages": 0,
            "total_links": 0,
            "broken_links": [],
            "orphan_pages": [],
            "conflicts": [],
            "hallucinations": [],
            "auto_fixes": [],
            "scores": {
                "completeness": 0,
                "link_health": 0,
                "consistency": 0,
            },
            "summary": "",
        }

        # 1. 扫描死链
        print("🔗 正在扫描死链...")
        self._broken_links = self.scan_broken_links()
        report["broken_links"] = self._broken_links

        # 2. 检测孤立节点
        print("🏝️ 正在检测孤立节点...")
        self._orphan_pages = self.scan_orphan_pages()
        report["orphan_pages"] = self._orphan_pages

        # 3. 检测冲突
        print("⚡ 正在检测知识冲突...")
        self._conflicts = self.detect_conflicts()
        report["conflicts"] = self._conflicts

        # 4. 检测幻觉
        print("👻 正在检测幻觉...")
        self._hallucinations = self.detect_hallucinations()
        report["hallucinations"] = self._hallucinations

        # 5. 自动修复
        if auto_fix:
            print("🔧 正在执行自动修复...")
            self._auto_fixes = self.auto_fix()
            report["auto_fixes"] = self._auto_fixes

        # 6. 计算评分
        report["total_pages"] = self._count_pages()
        report["total_links"] = self._count_total_links()
        report["scores"] = self._calculate_scores()

        # 7. 生成摘要
        report["summary"] = self._generate_summary(report)

        # 8. 保存审计报告
        self._save_report(report)

        return report

    def scan_broken_links(self) -> List[Dict]:
        """
        扫描所有页面，检测指向不存在页面的 [[wikilinks]]

        Returns:
            死链列表
        """
        all_pages = self._get_all_page_names()
        broken = []

        for md_file in sorted(self.pages_path.glob("*.md")):
            content = md_file.read_text(encoding="utf-8")
            links = re.findall(r'\[\[(.*?)\]\]', content)

            for link in links:
                # 处理 [[target|alias]] 格式
                target = link.split("|")[0].strip()
                if target and target not in all_pages:
                    broken.append({
                        "source_file": md_file.name,
                        "source_page": md_file.stem,
                        "broken_target": target,
                        "full_link": f"[[{link}]]",
                        "severity": "high",
                    })

        return broken

    def scan_orphan_pages(self) -> List[str]:
        """
        检测没有被任何其他页面引用的孤立页面

        Returns:
            孤立页面名称列表
        """
        all_pages = self._get_all_page_names()
        if not all_pages:
            return []

        # 统计每个页面被引用的次数
        reference_count = defaultdict(int)

        for md_file in self.pages_path.glob("*.md"):
            content = md_file.read_text(encoding="utf-8")
            links = re.findall(r'\[\[(.*?)\]\]', content)
            for link in links:
                target = link.split("|")[0].strip()
                if target in all_pages:
                    reference_count[target] += 1

        # 没有被任何页面引用的即为孤立节点
        orphans = [p for p in all_pages if reference_count[p] == 0]

        # 排除 index 页面和自动生成的 stub 页面
        orphans = [p for p in orphans if p.lower() not in ("index", "changelog", "change_log")]

        return orphans

    def detect_conflicts(self) -> List[Dict]:
        """
        检测不同页面之间的知识冲突

        使用 LLM 进行智能冲突检测，或使用基于规则的简单检测

        Returns:
            冲突列表
        """
        all_pages = self._get_all_page_names()
        conflicts = []

        if len(all_pages) < 2:
            return conflicts

        if self.llm_api:
            # 使用 LLM 进行智能冲突检测
            from schema.lint_skill import CONFLICT_DETECTION_PROMPT

            # 对每一对页面进行冲突检测（限制对数避免 OOM）
            pairs_checked = 0
            max_pairs = 20

            for i in range(len(all_pages)):
                for j in range(i + 1, len(all_pages)):
                    if pairs_checked >= max_pairs:
                        break
                    pairs_checked += 1

                    page_a = all_pages[i]
                    page_b = all_pages[j]
                    content_a = self._read_page_content(page_a)
                    content_b = self._read_page_content(page_b)

                    if not content_a or not content_b:
                        continue

                    prompt = CONFLICT_DETECTION_PROMPT.format(
                        page_a_title=page_a,
                        page_a_content=content_a[:2000],
                        page_b_title=page_b,
                        page_b_content=content_b[:2000],
                    )
                    response = self.llm_api(prompt)
                    try:
                        json_match = re.search(r"```json\n(.*?)\n```", response, re.DOTALL)
                        if json_match:
                            result = json.loads(json_match.group(1))
                        else:
                            result = json.loads(response)

                        if not result.get("no_conflicts", True):
                            for c in result.get("conflicts", []):
                                c["page_a"] = page_a
                                c["page_b"] = page_b
                                conflicts.append(c)
                    except json.JSONDecodeError:
                        pass
        else:
            # 基于规则的冲突检测
            conflicts = self._rule_based_conflict_detection(all_pages)

        return conflicts

    def detect_hallucinations(self) -> List[Dict]:
        """
        检测页面中的幻觉内容

        Returns:
            幻觉内容列表
        """
        hallucinations = []
        all_pages = self._get_all_page_names()

        if self.llm_api:
            from schema.lint_skill import HALLUCINATION_DETECTION_PROMPT

            for page_name in all_pages[:10]:  # 限制检测数量
                content = self._read_page_content(page_name)
                if not content or len(content) < 100:
                    continue

                prompt = HALLUCINATION_DETECTION_PROMPT.format(page_content=content[:3000])
                response = self.llm_api(prompt)

                try:
                    json_match = re.search(r"```json\n(.*?)\n```", response, re.DOTALL)
                    if json_match:
                        result = json.loads(json_match.group(1))
                    else:
                        result = json.loads(response)

                    if not result.get("no_issues_found", True):
                        for h in result.get("hallucinations", []):
                            h["page"] = page_name
                            hallucinations.append(h)
                except json.JSONDecodeError:
                    pass
        else:
            # 基于规则的幻觉检测（检查常见的幻觉模式）
            hallucinations = self._rule_based_hallucination_detection(all_pages)

        return hallucinations

    def auto_fix(self) -> List[Dict]:
        """
        自动修复可修复的问题

        Returns:
            修复操作列表
        """
        fixes = []

        # 修复 1: 为被引用但不存在的页面创建 Stub
        fixes.extend(self._fix_broken_links_with_stubs())

        return fixes

    def get_report(self) -> Dict:
        """获取最近一次审计的结果"""
        report_file = self.vault_path / "lint_report.json"
        if report_file.exists():
            return json.loads(report_file.read_text(encoding="utf-8"))
        return {"error": "尚未运行审计"}

    # ============================================================
    # 内部方法
    # ============================================================

    def _get_all_page_names(self) -> List[str]:
        """获取所有页面的名称列表"""
        if not self.pages_path.exists():
            return []
        return sorted([f.stem for f in self.pages_path.glob("*.md")])

    def _count_pages(self) -> int:
        """统计页面总数"""
        return len(self._get_all_page_names())

    def _count_total_links(self) -> int:
        """统计链接总数"""
        total = 0
        for md_file in self.pages_path.glob("*.md"):
            content = md_file.read_text(encoding="utf-8")
            total += len(re.findall(r'\[\[(.*?)\]\]', content))
        return total

    def _read_page_content(self, page_name: str) -> Optional[str]:
        """读取页面内容"""
        page_file = self.pages_path / f"{page_name}.md"
        if page_file.exists():
            return page_file.read_text(encoding="utf-8")
        return None

    def _rule_based_conflict_detection(self, all_pages: List[str]) -> List[Dict]:
        """基于规则的冲突检测"""
        conflicts = []

        # 检查是否有同名但内容不同的实体（通过内容长度和哈希简单判断）
        # 这里主要用于演示，实际冲突检测依赖 LLM
        for page in all_pages:
            content = self._read_page_content(page)
            if content and "[Conflict-Flag]" in content:
                conflicts.append({
                    "type": "手动标记冲突",
                    "severity": "medium",
                    "page_a": page,
                    "page_b": "未知",
                    "description": f"页面 '{page}' 包含手动标记的冲突标志 [Conflict-Flag]",
                    "suggestion": "请人工审查并解决此冲突",
                })

        return conflicts

    def _rule_based_hallucination_detection(self, all_pages: List[str]) -> List[Dict]:
        """基于规则的幻觉检测"""
        hallucinations = []

        for page in all_pages:
            content = self._read_page_content(page)

            # 检查模式：过度使用模糊表述
            vague_patterns = [
                (r'据称[^，。]*?(?:可能|或许|大概)', "过度推测"),
                (r'(?:据说|传闻|有人声称)[^。]*', "来源不明"),
                (r'引用自[^，。]*?(?:未知|佚名)', "虚假引用"),
            ]

            for pattern, issue_type in vague_patterns:
                matches = re.findall(pattern, content or "")
                for match in matches:
                    hallucinations.append({
                        "severity": "medium",
                        "page": page,
                        "location": "全文",
                        "content": match[:100],
                        "issue_type": issue_type,
                        "explanation": f"检测到疑似 {issue_type} 的内容",
                        "fix_suggestion": "请确认信息来源并补充引用",
                    })

        return hallucinations

    def _fix_broken_links_with_stubs(self) -> List[Dict]:
        """为被引用但不存在的页面创建 Stub 页面"""
        fixes = []

        # 收集所有被引用但不存在的页面及其引用来源
        all_pages = self._get_all_page_names()
        needed_stubs = {}

        for md_file in self.pages_path.glob("*.md"):
            content = md_file.read_text(encoding="utf-8")
            links = re.findall(r'\[\[(.*?)\]\]', content)
            for link in links:
                target = link.split("|")[0].strip()
                if target and target not in all_pages:
                    if target not in needed_stubs:
                        needed_stubs[target] = []
                    needed_stubs[target].append(md_file.stem)

        # 创建 Stub 页面
        from schema.lint_skill import AUTO_FIX_RULES
        stub_template = AUTO_FIX_RULES["create_stub_page"]["stub_template"]

        for entity_name, referrers in needed_stubs.items():
            stub_file = self.pages_path / f"{entity_name}.md"
            if not stub_file.exists():
                stub_content = stub_template.format(
                    entity_name=entity_name,
                    referenced_by="\n".join(f"* [[{r}]]" for r in referrers),
                    date=datetime.now().strftime("%Y-%m-%d"),
                )
                stub_file.write_text(stub_content, encoding="utf-8")
                fixes.append({
                    "type": "create_stub",
                    "entity": entity_name,
                    "referenced_by": referrers,
                    "description": f"为 '{entity_name}' 创建了 Stub 页面（被 {len(referrers)} 个页面引用）",
                })

        return fixes

    def _calculate_scores(self) -> Dict:
        """计算知识库健康评分"""
        all_pages = self._get_all_page_names()
        total_pages = len(all_pages)

        # 链接健康度: 1 - (死链数 / 总链接数)
        total_links = self._count_total_links()
        broken_count = len(self._broken_links)
        link_health = max(0, 100 - int((broken_count / max(1, total_links)) * 100)) if total_links > 0 else 100

        # 完整性: 1 - (孤立节点数 / 总页面数)
        orphan_count = len(self._orphan_pages)
        completeness = max(0, 100 - int((orphan_count / max(1, total_pages)) * 50)) if total_pages > 0 else 0

        # 一致性: 基于冲突数量扣分
        conflict_count = len(self._conflicts)
        consistency = max(0, 100 - conflict_count * 10)

        return {
            "completeness": completeness,
            "link_health": link_health,
            "consistency": consistency,
        }

    def _generate_summary(self, report: Dict) -> str:
        """生成审计摘要"""
        scores = report["scores"]
        summary_parts = []

        summary_parts.append(f"知识库审计完成: {report['total_pages']} 个页面, {report['total_links']} 条链接")
        summary_parts.append(f"评分 - 完整性: {scores['completeness']}/100, 链接健康度: {scores['link_health']}/100, 一致性: {scores['consistency']}/100")

        if report["broken_links"]:
            summary_parts.append(f"⚠️  发现 {len(report['broken_links'])} 个死链")
        if report["orphan_pages"]:
            summary_parts.append(f"🏝️  发现 {len(report['orphan_pages'])} 个孤立节点")
        if report["conflicts"]:
            summary_parts.append(f"⚡ 发现 {len(report['conflicts'])} 个知识冲突")
        if report["hallucinations"]:
            summary_parts.append(f"👻 发现 {len(report['hallucinations'])} 个潜在幻觉")
        if report["auto_fixes"]:
            summary_parts.append(f"🔧 自动修复了 {len(report['auto_fixes'])} 个问题")

        overall = (scores["completeness"] + scores["link_health"] + scores["consistency"]) / 3
        if overall >= 90:
            summary_parts.append("🌟 知识库整体状态优秀")
        elif overall >= 70:
            summary_parts.append("✅ 知识库状态良好，建议处理发现的问题")
        else:
            summary_parts.append("🔴 知识库需要维护，请关注审计报告中的问题")

        return "\n".join(summary_parts)

    def _save_report(self, report: Dict):
        """保存审计报告到文件"""
        report_file = self.vault_path / "lint_report.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        # 同时生成 Markdown 格式报告
        md_report = self._generate_markdown_report(report)
        md_file = self.vault_path / "lint_report.md"
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(md_report)

    def _generate_markdown_report(self, report: Dict) -> str:
        """生成 Markdown 格式的审计报告"""
        from schema.lint_skill import LINT_REPORT_TEMPLATE

        broken_section = "\n".join(
            f"* ❌ `{b['source_page']}` → `[[{b['broken_target']}]]`"
            for b in report["broken_links"][:20]
        ) or "✅ 无死链"

        orphan_section = "\n".join(
            f"* 🏝️ `{p}`" for p in report["orphan_pages"][:20]
        ) or "✅ 无孤立节点"

        conflict_section = "\n".join(
            f"* ⚡ `{c.get('page_a', '?')}` ↔ `{c.get('page_b', '?')}`: {c.get('description', '')[:100]}"
            for c in report["conflicts"][:10]
        ) or "✅ 无冲突"

        hallu_section = "\n".join(
            f"* 👻 `{h.get('page', '?')}`: {h.get('content', '')[:80]}"
            for h in report["hallucinations"][:10]
        ) or "✅ 无幻觉"

        fix_section = "\n".join(
            f"* ✅ {f.get('description', '')}" for f in report["auto_fixes"][:20]
        ) or "无自动修复操作"

        return LINT_REPORT_TEMPLATE.format(
            timestamp=report["timestamp"],
            total_pages=report["total_pages"],
            total_links=report["total_links"],
            completeness_score=report["scores"]["completeness"],
            link_health_score=report["scores"]["link_health"],
            consistency_score=report["scores"]["consistency"],
            broken_count=len(report["broken_links"]),
            broken_links_section=broken_section,
            orphan_count=len(report["orphan_pages"]),
            orphan_pages_section=orphan_section,
            conflict_count=len(report["conflicts"]),
            conflicts_section=conflict_section,
            hallucination_count=len(report["hallucinations"]),
            hallucinations_section=hallu_section,
            auto_fix_section=fix_section,
        )


# ============================================================
# 便捷函数
# ============================================================

def create_lint_agent(vault_path: str = "./wiki_vault", llm_api_func=None) -> LintAgent:
    """创建并返回一个配置好的 Lint Agent 实例"""
    return LintAgent(vault_path=vault_path, llm_api_func=llm_api_func)
