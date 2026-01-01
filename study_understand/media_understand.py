from multiprocessing import context
import subprocess
import os
from pathlib import Path
from loguru import logger
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置 loguru
logger.add(
    "logs/media_understand_{time}.log",
    rotation="10 MB",
    retention="7 days",
    level="INFO"
)


def call_asr_with_format(media_file_path: str, provider: str = "siliconflow", model: str = "FunAudioLLM/SenseVoiceSmall") -> str:
    """
    调用 ASR 服务对媒体文件进行语音识别
    :param media_file_path: 媒体文件路径
    :param provider: ASR 服务提供商
    :return: 识别结果文本
    """
    logger.info(f"调用 ASR 服务, 提供商: {provider}, 文件: {media_file_path}")

    if provider == "siliconflow":
        from src.tools.siliconflow_asr import SiliconFlowASR
        asr = SiliconFlowASR()
        result = asr.transcribe_with_format(media_file_path)
        logger.success(f"ASR 识别完成, 文本长度: {len(result)}")
        return result
    else:
        logger.error(f"不支持的 ASR 服务提供商: {provider}")
        raise ValueError(f"不支持的 ASR 服务提供商: {provider}")

def call_graph(article: str) -> dict:
    """
    调用文章阅读分析工作流
    :param article: 文章文本
    :return: 分析结果
    """
    from src.graphs.article_read_graph import create_article_read_graph
    graph = create_article_read_graph().compile()
    result = graph.invoke({"article": article}, context={})
    return result


def main(source_file: str):
    """
    主函数：处理媒体文件并输出识别结果
    :param source_file: 源文件路径
    """
    logger.info(f"开始处理文件: {source_file}")

    try:
        result = call_asr_with_format(source_file, provider="siliconflow", model="TeleAI/TeleSpeechASR")
        print(result)
        logger.info("文件处理完成")
    except Exception as e:
        logger.error(f"处理失败: {e}")
        raise

    # 调用文章阅读分析工作流
    analysis_result = call_graph(result)
    print(analysis_result)
    logger.info("文章阅读分析完成")



if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        source_file = sys.argv[1]
    else:
        source_file = r"G:\Storage\LocalStorage\03音视频\播客\张小珺Jùn｜商业访谈录\【张小珺Jùn｜商业访谈录】92. 和张亚勤院士聊，意识、寿命、机器人、生物智能和物种的延伸.m4a"
        logger.warning(f"未指定文件，使用默认文件: {source_file}")

    main(source_file)
