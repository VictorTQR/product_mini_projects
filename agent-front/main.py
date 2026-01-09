"""
FastAPI 后端服务
提供 SSE 流式聊天端点和社交媒体帖子/评论管理API
"""
import os
import json
import uuid
from typing import AsyncGenerator, List, Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import pyseekdb

from langchain_ollama import ChatOllama
from langchain.agents import create_agent
from langchain_core.tools import tool

from services import PostService, CommentService
from models import (
    PostCreate, PostUpdate, PostResponse,
    CommentCreate, CommentUpdate, CommentResponse,
    SearchPostsRequest, SearchCommentsRequest
)

# 加载环境变量
load_dotenv()

# ==================== 配置 ====================
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://soct.top:11436")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:0.6b")

# SeekDB 配置
SEEKDB_HOST = os.getenv("SEEKDB_HOST", "soct.top")
SEEKDB_PORT = int(os.getenv("SEEKDB_PORT", "2881"))
SEEKDB_DATABASE = os.getenv("SEEKDB_DATABASE", "test")
SEEKDB_USER = os.getenv("SEEKDB_USER", "root")
SEEKDB_PASSWORD = os.getenv("SEEKDB_PASSWORD", "")

# ==================== SeekDB 客户端初始化 ====================
# 初始化 SeekDB 客户端
seekdb_client = pyseekdb.Client(
    host=SEEKDB_HOST,
    port=SEEKDB_PORT,
    database=SEEKDB_DATABASE,
    user=SEEKDB_USER,
    password=SEEKDB_PASSWORD
)

# 初始化服务
post_service = PostService(seekdb_client, dimension=384)
comment_service = CommentService(seekdb_client, dimension=384)

# ==================== 工具定义 ====================
@tool
def get_weather(city: str) -> str:
    """获取城市的天气信息"""
    return f"{city}的天气是晴朗的，温度22°C，湿度45%"

@tool
def calculator(expression: str) -> str:
    """执行数学计算"""
    try:
        result = eval(expression)
        return str(result)
    except Exception as e:
        return f"计算错误: {str(e)}"

# ==================== LLM 和 Agent 初始化 ====================
model = ChatOllama(
    model=OLLAMA_MODEL,
    base_url=OLLAMA_BASE_URL,
    reasoning=True
)

agent = create_agent(
    model,
    tools=[get_weather, calculator]
)

# ==================== 数据模型 ====================
class ChatMessage(BaseModel):
    role: str  # "user" 或 "assistant"
    content: str

class ChatRequest(BaseModel):
    messages: list[ChatMessage]

# ==================== FastAPI 应用 ====================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    print("🚀 FastAPI 应用启动")
    yield
    print("🛑 FastAPI 应用关闭")

app = FastAPI(
    title="AI Agent Chat API",
    description="基于 LangChain 的智能体聊天服务，支持 SSE 流式输出",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== 辅助函数 ====================
async def format_sse(data: dict) -> str:
    """格式化 SSE 事件"""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

async def generate_event_stream(messages: list[dict]) -> AsyncGenerator[str, None]:
    """生成 SSE 事件流"""
    
    # 1. 开始思考
    thinking_id = f"think_{uuid.uuid4().hex[:8]}"
    yield await format_sse({
        "type": "thinking_start",
        "id": thinking_id
    })
    
    # 2. 流式输出推理过程
    reasoning_content = ""
    tool_calls_made = []
    
    try:
        # 使用 agent.stream 进行流式处理
        for token, metadata in agent.stream(
            {"messages": messages},
            stream_mode="messages"
        ):
            if token.type == "AIMessageChunk":
                if token.content_blocks:
                    for content in token.content_blocks:
                        # 处理推理过程
                        if content["type"] == "reasoning":
                            reasoning_text = content["reasoning"]
                            reasoning_content += reasoning_text
                            yield await format_sse({
                                "type": "thinking_delta",
                                "id": thinking_id,
                                "content": reasoning_text
                            })
                        
                        # 处理工具调用
                        elif content["type"] == "tool_call_chunk":
                            tool_name = content["name"]
                            tool_args = content["args"]
                            
                            # 创建工具调用块
                            tool_id = f"tool_{uuid.uuid4().hex[:8]}"
                            tool_calls_made.append(tool_id)
                            
                            yield await format_sse({
                                "type": "tool_call",
                                "id": tool_id,
                                "name": tool_name,
                                "params": json.loads(tool_args) if isinstance(tool_args, str) else tool_args
                            })
                        
                        # 处理文本内容（正常回复）
                        elif content["type"] == "text":
                            text_content = content["text"]
                            yield await format_sse({
                                "type": "text_delta",
                                "content": text_content
                            })
            # 处理工具执行结果
            elif token.type == "tool":
                # 找到对应的工具调用ID并更新结果
                if tool_calls_made:
                    tool_id = tool_calls_made[-1]
                    yield await format_sse({
                        "type": "tool_result",
                        "id": tool_id,
                        "status": "success",
                        "output": token.content
                    })
    
    except Exception as e:
        yield await format_sse({
            "type": "error",
            "message": f"处理错误: {str(e)}"
        })
    
    # 3. 结束思考
    yield await format_sse({
        "type": "thinking_end",
        "id": thinking_id
    })
    
    # 4. 流结束
    yield await format_sse({
        "type": "done"
    })

# ==================== 路由 ====================
@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "AI Agent Chat API",
        "version": "1.0.0",
        "endpoints": {
            "chat_stream": "/api/chat/stream?message=your_message"
        }
    }

@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """SSE 流式聊天端点 - 支持多轮对话"""
    # 将消息数组转换为字典格式
    messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
    
    return StreamingResponse(
        generate_event_stream(messages),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}

# ============================================================================
# 帖子管理 API
# ============================================================================

@app.post("/api/posts", response_model=dict)
async def create_post(post: PostCreate):
    """创建新帖子"""
    try:
        post_dict = post.model_dump()
        post_service.create_post(post_dict)
        return {"message": "帖子创建成功", "post_id": post_dict.get("post_id")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建失败: {str(e)}")

@app.post("/api/posts/batch", response_model=dict)
async def batch_create_posts(posts: List[PostCreate]):
    """批量创建帖子"""
    try:
        posts_list = [post.model_dump() for post in posts]
        post_service.batch_create_posts(posts_list)
        return {"message": f"成功创建 {len(posts_list)} 个帖子"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量创建失败: {str(e)}")

@app.get("/api/posts/{post_id}", response_model=dict)
async def get_post(post_id: str):
    """获取指定ID的帖子"""
    try:
        result = post_service.get_post_by_id(post_id)
        if not result['ids']:
            raise HTTPException(status_code=404, detail="帖子未找到")
        return {
            "post_id": result['ids'][0],
            "content": result['documents'][0],
            "metadata": result['metadatas'][0]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")

@app.put("/api/posts/{post_id}", response_model=dict)
async def update_post(post_id: str, post: PostUpdate):
    """更新帖子"""
    try:
        update_data = post.model_dump(exclude_unset=True)
        if update_data:
            post_service.update_post(post_id, update_data)
        return {"message": "帖子更新成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")

@app.delete("/api/posts/{post_id}", response_model=dict)
async def delete_post(post_id: str):
    """删除帖子"""
    try:
        post_service.delete_post(post_id)
        return {"message": "帖子删除成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")

@app.post("/api/posts/search", response_model=dict)
async def search_posts(request: SearchPostsRequest):
    """搜索帖子（支持向量搜索、元数据过滤、混合搜索）"""
    try:
        # 根据请求参数选择搜索方法
        if request.query_text and request.keyword:
            # 混合搜索：向量 + 关键词
            results = post_service.search_full_text_hybrid(
                query_text=request.query_text,
                keyword=request.keyword,
                n_results=request.n_results
            )
        elif request.query_text and (request.platform or request.min_likes is not None):
            # 混合搜索：向量 + 元数据
            results = post_service.search_hybrid(
                query_text=request.query_text,
                platform=request.platform or "",
                min_likes=request.min_likes or 0,
                n_results=request.n_results
            )
        elif request.query_text:
            # 纯向量搜索
            results = post_service.search_similar_content(
                query_text=request.query_text,
                n_results=request.n_results
            )
        elif request.tags:
            # 按标签搜索
            results = post_service.search_by_tags(
                tags=request.tags,
                n_results=request.n_results
            )
        elif request.start_date and request.end_date:
            # 按日期范围搜索
            results = post_service.search_by_date_range(
                start_date=request.start_date,
                end_date=request.end_date,
                n_results=request.n_results
            )
        elif request.platform:
            # 按平台搜索
            results = post_service.search_by_platform(
                platform=request.platform,
                n_results=request.n_results
            )
        elif request.min_likes is not None:
            # 热门帖子
            results = post_service.search_popular_posts(
                min_likes=request.min_likes,
                n_results=request.n_results
            )
        else:
            raise HTTPException(status_code=400, detail="请提供搜索条件")
        
        # 格式化结果
        posts = []
        if results['ids']:
            for i in range(len(results['ids'][0])):
                posts.append({
                    "post_id": results['ids'][0][i],
                    "content": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i],
                    "distance": results['distances'][0][i] if 'distances' in results else None
                })
        
        return {
            "count": len(posts),
            "results": posts
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")

@app.get("/api/posts", response_model=dict)
async def list_posts(limit: int = 10, offset: int = 0):
    """获取所有帖子（分页）"""
    try:
        results = post_service.get_all_posts(limit=limit + offset)
        total = len(results['ids']) if results['ids'] else 0
        
        posts = []
        if results['ids']:
            for i in range(offset, min(offset + limit, total)):
                posts.append({
                    "post_id": results['ids'][i],
                    "content": results['documents'][i],
                    "metadata": results['metadatas'][i]
                })
        
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "results": posts
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")

@app.get("/api/posts/stats", response_model=dict)
async def get_posts_stats():
    """获取帖子统计信息"""
    try:
        count = post_service.get_stats()
        return {"total_posts": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")

# ============================================================================
# 评论管理 API
# ============================================================================

@app.post("/api/comments", response_model=dict)
async def create_comment(comment: CommentCreate):
    """创建新评论"""
    try:
        comment_dict = comment.model_dump()
        comment_service.create_comment(comment_dict)
        return {"message": "评论创建成功", "comment_id": comment_dict.get("comment_id")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建失败: {str(e)}")

@app.post("/api/comments/batch", response_model=dict)
async def batch_create_comments(comments: List[CommentCreate]):
    """批量创建评论"""
    try:
        comments_list = [comment.model_dump() for comment in comments]
        comment_service.batch_create_comments(comments_list)
        return {"message": f"成功创建 {len(comments_list)} 条评论"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量创建失败: {str(e)}")

@app.get("/api/comments/{comment_id}", response_model=dict)
async def get_comment(comment_id: str):
    """获取指定ID的评论"""
    try:
        result = comment_service.get_comment_by_id(comment_id)
        if not result['ids']:
            raise HTTPException(status_code=404, detail="评论未找到")
        return {
            "comment_id": result['ids'][0],
            "content": result['documents'][0],
            "metadata": result['metadatas'][0]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")

@app.get("/api/posts/{post_id}/comments", response_model=dict)
async def get_post_comments(post_id: str, limit: int = 10):
    """获取指定帖子的所有评论"""
    try:
        results = comment_service.get_comments_by_post_id(post_id, limit=limit)
        
        comments = []
        if results['ids']:
            for i in range(len(results['ids'])):
                comments.append({
                    "comment_id": results['ids'][i],
                    "content": results['documents'][i],
                    "metadata": results['metadatas'][i]
                })
        
        return {
            "post_id": post_id,
            "count": len(comments),
            "results": comments
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")

@app.put("/api/comments/{comment_id}", response_model=dict)
async def update_comment(comment_id: str, comment: CommentUpdate):
    """更新评论"""
    try:
        update_data = comment.model_dump(exclude_unset=True)
        if update_data:
            comment_service.update_comment(comment_id, update_data)
        return {"message": "评论更新成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")

@app.delete("/api/comments/{comment_id}", response_model=dict)
async def delete_comment(comment_id: str):
    """删除评论"""
    try:
        comment_service.delete_comment(comment_id)
        return {"message": "评论删除成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")

@app.delete("/api/posts/{post_id}/comments", response_model=dict)
async def delete_post_comments(post_id: str):
    """删除指定帖子的所有评论"""
    try:
        comment_service.delete_comments_by_post_id(post_id)
        return {"message": f"帖子 {post_id} 的所有评论已删除"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")

@app.post("/api/comments/search", response_model=dict)
async def search_comments(request: SearchCommentsRequest):
    """搜索评论（支持向量搜索、元数据过滤、混合搜索）"""
    try:
        # 根据请求参数选择搜索方法
        if request.query_text and request.keyword:
            # 混合搜索：向量 + 关键词
            results = comment_service.search_full_text_hybrid(
                query_text=request.query_text,
                keyword=request.keyword,
                n_results=request.n_results
            )
        elif request.query_text and request.post_id:
            # 混合搜索：向量 + 帖子ID
            results = comment_service.search_hybrid(
                query_text=request.query_text,
                post_id=request.post_id,
                min_likes=request.min_likes or 0,
                n_results=request.n_results
            )
        elif request.query_text:
            # 纯向量搜索
            results = comment_service.search_similar_content(
                query_text=request.query_text,
                n_results=request.n_results
            )
        elif request.post_id and request.start_date and request.end_date:
            # 按帖子和日期范围搜索
            results = comment_service.search_by_post_and_date(
                post_id=request.post_id,
                start_date=request.start_date,
                end_date=request.end_date,
                n_results=request.n_results
            )
        elif request.start_date and request.end_date:
            # 按日期范围搜索
            results = comment_service.search_by_date_range(
                start_date=request.start_date,
                end_date=request.end_date,
                n_results=request.n_results
            )
        elif request.platform:
            # 按平台搜索
            results = comment_service.search_by_platform(
                platform=request.platform,
                n_results=request.n_results
            )
        elif request.min_likes is not None:
            # 热门评论
            results = comment_service.search_popular_comments(
                min_likes=request.min_likes,
                post_id=request.post_id,
                n_results=request.n_results
            )
        else:
            raise HTTPException(status_code=400, detail="请提供搜索条件")
        
        # 格式化结果
        comments = []
        if results['ids']:
            for i in range(len(results['ids'][0])):
                comments.append({
                    "comment_id": results['ids'][0][i],
                    "content": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i],
                    "distance": results['distances'][0][i] if 'distances' in results else None
                })
        
        return {
            "count": len(comments),
            "results": comments
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")

@app.get("/api/comments", response_model=dict)
async def list_comments(limit: int = 10, offset: int = 0):
    """获取所有评论（分页）"""
    try:
        results = comment_service.get_all_comments(limit=limit + offset)
        total = len(results['ids']) if results['ids'] else 0
        
        comments = []
        if results['ids']:
            for i in range(offset, min(offset + limit, total)):
                comments.append({
                    "comment_id": results['ids'][i],
                    "content": results['documents'][i],
                    "metadata": results['metadatas'][i]
                })
        
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "results": comments
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")

@app.get("/api/comments/stats", response_model=dict)
async def get_comments_stats():
    """获取评论统计信息"""
    try:
        count = comment_service.get_stats()
        return {"total_comments": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")

@app.get("/api/posts/{post_id}/comments/stats", response_model=dict)
async def get_post_comments_stats(post_id: str):
    """获取指定帖子的评论统计"""
    try:
        count = comment_service.get_comment_count_by_post(post_id)
        return {"post_id": post_id, "comment_count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")

# ==================== 启动命令 ====================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
