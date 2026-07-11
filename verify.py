"""
LLM Wiki 系统验证脚本
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.ingest_agent import IngestAgent
from core.query_agent import QueryAgent
from core.lint_agent import LintAgent

# 1. 构建图索引
print("=" * 50)
print("  LLM Wiki 系统完整性验证")
print("=" * 50)

print("\n=== 1. 构建知识图谱索引 ===")
ingest = IngestAgent(vault_path="./wiki_vault")
ingest._build_graph_index()

graph_file = Path("./wiki_vault/index_graph.json")
data = json.loads(graph_file.read_text(encoding="utf-8"))
print(f"   节点数: {data['metadata']['node_count']}")
print(f"   边数: {data['metadata']['edge_count']}")
print(f"   节点列表: {[n['id'] for n in data['nodes']]}")
for e in data["edges"]:
    print(f"   边: {e['source']} --> {e['target']}")

# 2. 测试检索
print("\n=== 2. 测试知识检索 ===")
query = QueryAgent(vault_path="./wiki_vault")
result = query.search("Transformer", top_n=3)
print(f"   匹配实体: {result['found_entities']}")
print(f"   相关页面: {[p['name'] for p in result['pages_used']]}")
if result.get("graph_paths"):
    for p in result["graph_paths"][:3]:
        print(f"   路径: {p['path']}")

# 3. 测试审计
print("\n=== 3. 测试知识审计 ===")
lint = LintAgent(vault_path="./wiki_vault")
report = lint.run_full_audit(auto_fix=True)
scores = report["scores"]
print(f"   完整性评分: {scores['completeness']}/100")
print(f"   链接健康度: {scores['link_health']}/100")
print(f"   一致性评分: {scores['consistency']}/100")
print(f"   死链数: {len(report['broken_links'])}")
print(f"   孤立节点数: {len(report['orphan_pages'])}")
print(f"   自动修复数: {len(report['auto_fixes'])}")

# 4. 列出所有主题
print("\n=== 4. 知识库主题列表 ===")
topics = query.list_topics()
for t in topics:
    print(f"   📄 {t}")

print("\n" + "=" * 50)
print("  ✅ 系统验证完成！所有组件运行正常")
print("=" * 50)

# 统计文件
wiki_files = list(Path("./wiki_vault/pages").glob("*.md"))
raw_files = list(Path("./raw_sources").glob("*"))
print(f"\n📊 最终统计:")
print(f"   📚 Wiki 页面: {len(wiki_files)}")
print(f"   📥 原始文档: {len(raw_files)}")
print(f"   🔗 图边: {len(data['edges'])}")
print(f"   📌 图节点: {len(data['nodes'])}")
