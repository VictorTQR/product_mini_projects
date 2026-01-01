"""
Article Read Graph - 使用 Langfuse 管理提示词
"""
from langgraph.graph import StateGraph, START, END
from langgraph.runtime import Runtime
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from langfuse import Langfuse

from .state import ArticleReadState, ArticleReadContext
from loguru import logger


# 初始化 Langfuse
langfuse = Langfuse()


def node_article_deep_analysis(state: ArticleReadState, runtime: Runtime[ArticleReadContext]) -> ArticleReadState:
    """
    文章深度分析节点
    使用 Langfuse 获取提示词模板
    """
    article = state.get("article")
    analysis_model = runtime.context.analysis_model

    logger.info(f"开始文章深度分析，模型: {analysis_model}")

    try:
        # 从 Langfuse 获取提示词
        article_prompt = langfuse.get_prompt("article/baoyu_article_analysis_whole")
        prompt_text = article_prompt.compile()

        # 编译提示词（TextPrompt 转 Chat Template）
        # 由于 Langfuse 的 TextPrompt 需要手动转换为 Chat 模式
        from langchain_core.messages import HumanMessage, SystemMessage

        # 构建 Chat 消息
        messages = [
            SystemMessage(content=prompt_text),
            HumanMessage(content=article)
        ]

        # 创建 LLM 实例
        llm = ChatOpenAI(
            model=analysis_model
        )

        # 调用 LLM
        logger.debug(f"发送文章分析请求，文章长度: {len(article)}")
        response = llm.invoke(messages)

        # 提取分析结果
        analysis_result = response.content
        logger.success(f"文章分析完成，结果长度: {len(analysis_result)}")

        return {"analysis_result": analysis_result}

    except Exception as e:
        logger.error(f"文章深度分析失败: {e}")
        raise


def create_article_read_graph() -> StateGraph:
    """
    创建文章阅读分析的工作流图

    Returns:
        StateGraph: 配置好的工作流图
    """
    logger.info("创建 Article Read Graph (Langfuse版本)")

    # 创建状态图
    graph = StateGraph(ArticleReadState, ArticleReadContext)

    # 添加节点
    graph.add_node("article_deep_analysis", node_article_deep_analysis)

    # 设置边关系
    graph.add_edge(START, "article_deep_analysis")
    graph.add_edge("article_deep_analysis", END)

    logger.info("Article Read Graph 创建成功")
    return graph


# 使用示例
if __name__ == "__main__":
    # 示例文章
    sample_article = """
    《红楼梦》是中国古典四大名著之首，清代作家曹雪芹创作的章回体长篇小说。
    小说以贾、史、王、薛四大家族的兴衰为背景，以富贵公子贾宝玉为视角，
    以贾宝玉与林黛玉、薛宝钗的爱情婚姻悲剧为主线，描绘了一批举止见识出于
    须眉之上的闺阁佳人的人生百态。
    """

    # 创建图
    app = create_article_read_graph()

    # 准备初始状态
    initial_state = {
        "article": sample_article
    }

    # 准备配置
    config = {
        "configurable": {
            "analysis_model": "gpt-4o-mini",
            "temperature": 0.7,
            "max_tokens": 4000
        }
    }

    # 执行工作流
    logger.info("开始执行文章阅读分析工作流")
    result = app.invoke(initial_state, config)

    # 输出结果
    print("\n" + "="*50)
    print("文章分析结果:")
    print("="*50)
    print(result.get("analysis_result"))
    print("="*50 + "\n")
