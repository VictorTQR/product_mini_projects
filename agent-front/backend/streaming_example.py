from dotenv import load_dotenv

load_dotenv()

from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI


@tool
def get_weather(location: str) -> str:
    """Get the current weather in a given location"""
    return f"The weather in {location} is 25°C"

@tool
def web_search(query: str) -> str:
    """Search the web for a given query"""
    return f"The search result for {query} is ..."

llm = ChatOpenAI(model="glm-4-flash")

agent = create_agent(
    llm,
    tools=[get_weather, web_search]
)

messages = [
    {"role": "user", "content": "北京天气如何"}
]

def updates_mode(messages: list):
    for chunk in agent.stream({"messages": messages}):
        for step, data in chunk.items():
            print(step, data)

def messages_mode(messages: list):
    for token, metadata in agent.stream({"messages": messages}, stream_mode="messages"):
        print(f"node: {metadata['langgraph_node']}")
        print(f"content: {token.content_blocks}")
        print("\n")

def updates_and_messages_mode(messages: list):
    full_message = ""
    for stream_mode, data in agent.stream({"messages": messages}, stream_mode=["messages", "updates"]):
        if stream_mode == "messages":
            token, metadata = data
            if token.content:  # LLM token
                full_message += token.content
                print(token.content, end="", flush=True)  # 实时显示
        elif stream_mode == "updates":
            for node, update in data.items():
                print(f"\n步骤 {node} 完成: {update['messages'][-1].content}")

updates_and_messages_mode(messages)