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


def call_asr_with_format(media_file_path: str, provider: str = "siliconflow") -> str:
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


def main(source_file: str):
    """
    主函数：处理媒体文件并输出识别结果
    :param source_file: 源文件路径
    """
    logger.info(f"开始处理文件: {source_file}")

    try:
        result = call_asr_with_format(source_file, provider="siliconflow")
        print(result)
        logger.info("文件处理完成")
    except Exception as e:
        logger.error(f"处理失败: {e}")
        raise


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        source_file = sys.argv[1]
    else:
        source_file = r"G:\Storage\LocalStorage\03音视频\播客\张小珺Jùn｜商业访谈录\【张小珺Jùn｜商业访谈录】92. 和张亚勤院士聊，意识、寿命、机器人、生物智能和物种的延伸.m4a"
        logger.warning(f"未指定文件，使用默认文件: {source_file}")

    main(source_file)
