

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

class PrebuildReactService:
    def __init__(self):
        llm = ChatOpenAI(model="glm-4-flash")

        self.agent = create_agent(
            llm,
            tools=[get_weather, web_search]
        )