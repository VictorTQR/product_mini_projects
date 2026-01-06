from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.tools import tool
from pydantic import BaseModel
import json
import asyncio
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

app = FastAPI()

# 示例工具
@tool
def get_weather(city: str) -> str:
    """获取城市天气"""
    return f"{city} 的天气晴朗，温度 25°C！"

# 创建 agent
llm = init_chat_model("openai:glm-4-flash", temperature=0)
agent = create_agent(
    model=llm,
    tools=[get_weather],
    system_prompt="你是一个有帮助的助手，用中文回复。"
)

class ChatRequest(BaseModel):
    message: str

async def agent_stream_generator(request: ChatRequest):
    """生成 SSE 格式的 agent stream"""
    async for stream_mode, chunk in agent.astream(
        {"messages": [{"role": "user", "content": request.message}]},
        stream_mode=["messages", "updates"]  # 多模式：tokens + 步骤
    ):
        if stream_mode == "messages":
            token, metadata = chunk
            if token.content:
                # 发送 token（实时打字效果）
                yield f"data: {json.dumps({'type': 'token', 'content': token.content})}\n\n"
        elif stream_mode == "updates":
            # 发送步骤更新（工具调用、完成）
            for node, update in chunk.items():
                msg = update.get("messages")[-1]
                if msg:
                    yield f"data: {json.dumps({'type': 'step', 'node': node, 'message': msg.content})}\n\n"
    yield "data: {json.dumps({'type': 'end'})}\n\n"

@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    return StreamingResponse(
        agent_stream_generator(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)