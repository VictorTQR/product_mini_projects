from loguru import logger

from langgraph.graph import StateGraph, START, END
from langgraph.runtime import Runtime
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser

from .state import (
    JiaoanState,
    JiaoanContext,
)
from .prompt import (
    lesson_content_message_prompt,
    lesson_goal_message_prompt,
    lesson_plan_message_prompt,
    lesson_plan_message_prompt_static,
    lesson_reflection_message_prompt,
)

def node_generate_lesson_content(state: JiaoanState, runtime: Runtime[JiaoanContext]) -> JiaoanState:
    """
    生成课程内容节点
    """
    logger.info("正在执行生成课程内容节点...")

    lesson_info = state.get("lesson_info")
    model = runtime.context.content_model

    logger.debug(f"课程信息: 课程名称={lesson_info['course_name']}, 课次名称={lesson_info['lesson_name']}")
    logger.debug(f"使用模型: {model}")

    messages = lesson_content_message_prompt.invoke(
        input={
            "course_name": lesson_info["course_name"],
            "lesson_name": lesson_info["lesson_name"],
            "lesson_desc": lesson_info["lesson_desc"],
        }
    )
    logger.debug("已构建课程内容生成消息")

    llm = ChatOpenAI(model=model)
    response = llm.invoke(messages)
    
    logger.info(f"课程内容生成完成，内容长度: {len(response.content)} 字符")
    logger.debug(f"课程内容预览: {response.content[:200]}...")

    return {
        "lesson_content": response.content,
    }


# 课程目标节点
def node_generate_lesson_goal(state: JiaoanState, runtime: Runtime[JiaoanContext]) -> JiaoanState:
    """
    生成课程目标节点
    """
    logger.info("正在执行生成课次目标节点...")

    lesson_content = state.get("lesson_content")
    model = runtime.context.goal_model

    logger.debug(f"课程内容长度: {len(lesson_content)} 字符")
    logger.debug(f"使用模型: {model}")

    messages = lesson_goal_message_prompt.invoke(
        input={
            "lesson_content": lesson_content,
        }
    )
    logger.debug("已构建课程目标生成消息")

    llm = ChatOpenAI(model=model)
    response = llm.invoke(messages)
    parser = JsonOutputParser()
    lesson_goal = parser.parse(response.content)
    
    logger.info(f"课程目标生成完成: {lesson_goal}")

    return {
        "lesson_goal": lesson_goal,
    }

# 课程计划节点
def node_generate_lesson_plan(state: JiaoanState, runtime: Runtime[JiaoanContext]) -> JiaoanState:
    """
    生成课次计划节点
    """
    logger.info("正在执行生成课次计划节点...")

    lesson_content = state.get("lesson_content")
    previous_lesson_desc = state["lesson_info"].get("previous_lesson_desc", "")
    generate_policy = state.get("generate_policy", "static")
    model = runtime.context.plan_model

    logger.debug(f"课程内容长度: {len(lesson_content)} 字符")
    logger.debug(f"使用模型: {model}")
    logger.debug(f"生成策略: {generate_policy}")

    if generate_policy == "static":
        message_prompt = lesson_plan_message_prompt_static
    else:
        message_prompt = lesson_plan_message_prompt

    messages = message_prompt.invoke(
        input={
            "lesson_content": lesson_content,
            "previous_lesson_desc": previous_lesson_desc,
        }
    )
    logger.debug("已构建课程计划生成消息")

    llm = ChatOpenAI(model=model)
    response = llm.invoke(messages)
    parser = JsonOutputParser()
    lesson_plan = parser.parse(response.content)
    
    logger.info(f"课程计划生成完成，计划项数量: {len(lesson_plan.get('plan', []))}")

    return {
        "lesson_plan": lesson_plan['plan'],
    }

# 课程反思节点
def node_generate_lesson_reflection(state: JiaoanState, runtime: Runtime[JiaoanContext]) -> JiaoanState:
    """
    生成课次反思节点
    """
    logger.info("正在执行生成课次反思节点...")

    lesson_content = state.get("lesson_content")
    model = runtime.context.reflection_model

    logger.debug(f"课程内容长度: {len(lesson_content)} 字符")
    logger.debug(f"使用模型: {model}")

    messages = lesson_reflection_message_prompt.invoke(
        input={
            "lesson_content": lesson_content,
        }
    )
    logger.debug("已构建课程反思生成消息")

    llm = ChatOpenAI(model=model)
    response = llm.invoke(messages)
    parser = JsonOutputParser()
    lesson_reflection = parser.parse(response.content)
    
    logger.info(f"课程反思生成完成: {lesson_reflection}")

    return {
        "lesson_reflection": lesson_reflection,
    }

def create_jiaoan_graph() -> StateGraph:
    """
    创建教案图
    """
    graph = StateGraph(JiaoanState, JiaoanContext)
    graph.add_node("generate_lesson_content", node_generate_lesson_content)
    graph.add_node("generate_lesson_goal", node_generate_lesson_goal)
    graph.add_node("generate_lesson_plan", node_generate_lesson_plan)
    graph.add_node("generate_lesson_reflection", node_generate_lesson_reflection)

    graph.add_edge(START, "generate_lesson_content")
    graph.add_edge("generate_lesson_content", "generate_lesson_goal")
    graph.add_edge("generate_lesson_content", "generate_lesson_plan")
    graph.add_edge("generate_lesson_content", "generate_lesson_reflection")

    graph.add_edge("generate_lesson_goal", END)
    graph.add_edge("generate_lesson_plan", END)
    graph.add_edge("generate_lesson_reflection", END)
    
    return graph
