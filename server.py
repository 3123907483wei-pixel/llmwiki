"""
FastAPI 后端服务 — LLM Wiki 知识管理系统 API

提供 RESTful API 供前端或其他客户端调用，封装三个核心 Agent 的功能。
"""

import os
import json
import sys
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# 确保可以导入 core 包
sys.path.insert(0, str(Path(__file__).parent))

from core.ingest_agent import IngestAgent
from core.query_agent import QueryAgent
from core.lint_agent import LintAgent

# ============================================================
# FastAPI 应用初始化
# ============================================================

app = FastAPI(
    title="LLM Wiki — 自演进知识管理系统 API",
    description="基于 Karpathy Knowledge Compilation 范式的知识编译与图检索系统",
    version="1.0.0",
)

# CORS 配置（允许 Streamlit 前端访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# 全局 Agent 实例
# ============================================================

VAULT_PATH = Path(__file__).parent / "wiki_vault"
RAW_PATH = Path(__file__).parent / "raw_sources"

ingest_agent = IngestAgent(vault_path=str(VAULT_PATH))
query_agent = QueryAgent(vault_path=str(VAULT_PATH))
lint_agent = LintAgent(vault_path=str(VAULT_PATH))


# ============================================================
# Pydantic 模型
# ============================================================

class QueryRequest(BaseModel):
    query: str
    top_n: int = 5
    damping_factor: float = 0.85

class QueryResponse(BaseModel):
    status: str
    data: dict

class AuditRequest(BaseModel):
    auto_fix: bool = True

class StatusResponse(BaseModel):
    status: str
    data: dict


# ============================================================
# API 路由: 知识库状态
# ============================================================

@app.get("/api/status", response_model=StatusResponse)
async def get_status():
    """获取系统整体状态"""
    ingest_status = ingest_agent.get_status()
    query_stats = query_agent.get_stats()
    topics = query_agent.list_topics()

    return StatusResponse(
        status="ok",
        data={
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat(),
            "ingest": ingest_status,
            "query": query_stats,
            "topics": topics,
            "topic_count": len(topics),
        }
    )


# ============================================================
# API 路由: 文档摄入
# ============================================================

@app.post("/api/ingest/file")
async def ingest_file(file: UploadFile = File(...)):
    """上传并摄入单个文档文件"""
    try:
        # 保存上传的文件到临时位置
        raw_path = RAW_PATH / file.filename
        content = await file.read()
        raw_path.write_bytes(content)

        # 执行摄入
        result = ingest_agent.ingest(str(raw_path))

        return JSONResponse(content={
            "status": "success" if result["status"] == "success" else "failed",
            "data": result,
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"摄入失败: {str(e)}")


@app.post("/api/ingest/text")
async def ingest_text(
    title: str = Form(...),
    content: str = Form(...),
):
    """摄入纯文本内容"""
    try:
        # 保存为临时文件
        safe_title = "".join(c if c.isalnum() or c in " _-" else "_" for c in title)
        temp_file = RAW_PATH / f"{safe_title}_{datetime.now().strftime('%Y%m%d%H%M%S')}.md"
        temp_file.write_text(content, encoding="utf-8")

        # 执行摄入
        result = ingest_agent.ingest(str(temp_file))

        return JSONResponse(content={
            "status": "success" if result["status"] == "success" else "failed",
            "data": result,
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"摄入失败: {str(e)}")


@app.post("/api/ingest/directory")
async def ingest_directory(dir_path: str = Form(...)):
    """批量摄入目录中的所有文档"""
    try:
        results = ingest_agent.ingest_directory(dir_path)
        return JSONResponse(content={
            "status": "success",
            "data": {"results": results, "total": len(results)},
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量摄入失败: {str(e)}")


# ============================================================
# API 路由: 知识检索
# ============================================================

@app.post("/api/query/search", response_model=QueryResponse)
async def search(request: QueryRequest):
    """执行知识检索"""
    try:
        result = query_agent.search(
            request.query,
            top_n=request.top_n,
            damping_factor=request.damping_factor,
        )
        return QueryResponse(
            status="success" if not result.get("error") else "no_results",
            data=result,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检索失败: {str(e)}")


@app.post("/api/query/answer", response_model=QueryResponse)
async def search_with_answer(request: QueryRequest):
    """检索并生成自然语言回答"""
    try:
        result = query_agent.search_with_answer(request.query, top_n=request.top_n)
        return QueryResponse(
            status="success" if not result.get("error") else "no_results",
            data=result,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"问答失败: {str(e)}")


@app.get("/api/query/topics")
async def list_topics():
    """列出知识库所有主题"""
    topics = query_agent.list_topics()
    return JSONResponse(content={
        "status": "success",
        "data": {"topics": topics, "count": len(topics)},
    })


# ============================================================
# API 路由: 知识审计
# ============================================================

@app.post("/api/lint/run")
async def run_audit(auto_fix: bool = Query(True)):
    """执行完整的知识库审计"""
    try:
        result = lint_agent.run_full_audit(auto_fix=auto_fix)
        return JSONResponse(content={
            "status": "success",
            "data": result,
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"审计失败: {str(e)}")


@app.get("/api/lint/report")
async def get_lint_report():
    """获取最近的审计报告"""
    report = lint_agent.get_report()
    return JSONResponse(content={
        "status": "success",
        "data": report,
    })


# ============================================================
# API 路由: Wiki 页面管理
# ============================================================

@app.get("/api/wiki/pages")
async def list_pages():
    """列出所有 Wiki 页面"""
    pages = []
    for md_file in sorted((VAULT_PATH / "pages").glob("*.md")):
        pages.append({
            "name": md_file.stem,
            "path": str(md_file.relative_to(VAULT_PATH)),
            "size": md_file.stat().st_size,
            "modified": datetime.fromtimestamp(md_file.stat().st_mtime).isoformat(),
        })
    return JSONResponse(content={"status": "success", "data": {"pages": pages, "count": len(pages)}})


@app.get("/api/wiki/page/{page_name}")
async def get_page(page_name: str):
    """获取指定 Wiki 页面的内容"""
    page_file = VAULT_PATH / "pages" / f"{page_name}.md"
    if not page_file.exists():
        raise HTTPException(status_code=404, detail=f"页面 '{page_name}' 不存在")
    content = page_file.read_text(encoding="utf-8")
    return JSONResponse(content={
        "status": "success",
        "data": {"name": page_name, "content": content},
    })


@app.get("/api/wiki/graph")
async def get_graph():
    """获取知识图谱数据（用于前端可视化）"""
    graph_file = VAULT_PATH / "index_graph.json"
    if graph_file.exists():
        data = json.loads(graph_file.read_text(encoding="utf-8"))
        return JSONResponse(content={"status": "success", "data": data})
    return JSONResponse(content={"status": "empty", "data": {"nodes": [], "edges": []}})


# ============================================================
# 启动入口
# ============================================================

if __name__ == "__main__":
    import uvicorn
    print("🚀 LLM Wiki API 服务启动中...")
    print(f"📂 知识库路径: {VAULT_PATH}")
    print(f"📥 原始文档路径: {RAW_PATH}")
    uvicorn.run(app, host="0.0.0.0", port=8000)
