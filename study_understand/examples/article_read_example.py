"""
Article Read Graph 使用示例
"""
from langgraph.checkpoint.memory import MemorySaver
from loguru import logger
from src.graphs.article_read_graph import create_article_read_graph_lf, ArticleReadState


# 配置 loguru
logger.add(
    "logs/article_read_example_{time}.log",
    rotation="10 MB",
    retention="7 days",
    level="INFO"
)


def analyze_article(article: str, model: str = "gpt-4o-mini") -> str:
    """
    分析文章

    Args:
        article: 要分析的文章内容
        model: 使用的模型

    Returns:
        str: 分析结果
    """
    # 创建图
    app = create_article_read_graph_lf()

    # 准备初始状态
    initial_state: ArticleReadState = {
        "article": article
    }

    # 准备配置
    config = {
        "configurable": {
            "analysis_model": model,
            "temperature": 0.7,
            "max_tokens": 4000
        }
    }

    # 执行工作流
    logger.info(f"开始分析文章，使用模型: {model}")
    result = app.invoke(initial_state, config)

    # 返回分析结果
    analysis_result = result.get("analysis_result", "")
    logger.success(f"文章分析完成，结果长度: {len(analysis_result)}")

    return analysis_result


def main():
    """主函数"""
    # 示例文章
    sample_article = """
    《红楼梦》是中国古典四大名著之首，清代作家曹雪芹创作的章回体长篇小说。
    小说以贾、史、王、薛四大家族的兴衰为背景，以富贵公子贾宝玉为视角，
    以贾宝玉与林黛玉、薛宝钗的爱情婚姻悲剧为主线，描绘了一批举止见识出于
    须眉之上的闺阁佳人的人生百态。

    《红楼梦》是一部具有世界影响力的人情小说作品，举世公认的中国古典小说
    巅峰之作，中国封建社会的百科全书，传统文化的集大成者。小说作者以
    "真事隐去，假语村言"的方式，按其事体情理，通过草蛇灰线、伏脉千里的
    手法，将当时社会的政治、经济、文化、风俗等方方面面，巧妙地融合在
    一起，展现出一幅广阔的历史画卷。
    """

    try:
        # 分析文章
        result = analyze_article(sample_article, model="gpt-4o-mini")

        # 输出结果
        print("\n" + "="*60)
        print("文章分析结果:")
        print("="*60)
        print(result)
        print("="*60 + "\n")

    except Exception as e:
        logger.error(f"文章分析失败: {e}")
        raise


if __name__ == "__main__":
    main()
