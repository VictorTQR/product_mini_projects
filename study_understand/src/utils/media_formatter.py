"""
媒体格式转换模块
"""
import subprocess
import os
from pathlib import Path
from loguru import logger

# 配置 loguru
logger.add(
    "logs/media_formatter_{time}.log",
    rotation="10 MB",
    retention="7 days",
    level="INFO"
)


def format_media_file(source_file_path: str, output_file_path: str = None) -> str:
    """
    使用 ffmpeg 将音视频文件转换为 16KHz 的 MP3 文件

    Args:
        source_file_path: 输入的音视频文件路径
        output_file_path: 输出的 MP3 文件路径。如果不指定，则自动生成

    Returns:
        str: 转换后的 MP3 文件路径

    Raises:
        FileNotFoundError: 输入文件不存在或 ffmpeg 未安装
        subprocess.CalledProcessError: ffmpeg 转换失败
    """
    logger.info(f"开始格式转换: {source_file_path}")

    # 检查输入文件是否存在
    if not os.path.exists(source_file_path):
        logger.error(f"输入文件不存在: {source_file_path}")
        raise FileNotFoundError(f"输入文件不存在: {source_file_path}")

    # 如果未指定输出路径，则自动生成
    if output_file_path is None:
        input_path = Path(source_file_path)
        output_file_path = str(input_path.with_suffix('.mp3'))
        # 如果原文件就是 mp3，添加 _formatted 后缀
        if input_path.suffix.lower() == '.mp3':
            output_file_path = str(input_path.parent / f"{input_path.stem}_formatted.mp3")

    logger.debug(f"输出文件路径: {output_file_path}")

    # 构建 ffmpeg 命令
    # -y: 覆盖输出文件而不询问
    # -i: 输入文件
    # -ar 16000: 设置采样率为 16KHz
    # -ac 1: 设置单声道（可选，如果需要的话）
    # -b:a 64k: 设置音频比特率为 64k（可选）
    # 最后是输出文件路径
    command = [
        'ffmpeg',
        '-y',  # 覆盖输出文件
        '-i', source_file_path,  # 输入文件
        '-ar', '16000',  # 采样率 16KHz
        '-ac', '1',  # 单声道
        '-b:a', '64k',  # 比特率 64k
        output_file_path
    ]

    try:
        # 执行 ffmpeg 命令
        logger.debug(f"执行 ffmpeg 命令: {' '.join(command)}")
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8',  # 指定编码
            errors='ignore'    # 忽略编码错误
        )

        logger.success(f"转换成功: {source_file_path} -> {output_file_path}")
        return output_file_path

    except subprocess.CalledProcessError as e:
        logger.error(f"ffmpeg 转换失败: {e.stderr}")
        raise
    except FileNotFoundError:
        error_msg = (
            "ffmpeg 未安装或不在系统 PATH 中。请先安装 ffmpeg:\n"
            "  - Windows: 使用 choco install ffmpeg 或从 https://ffmpeg.org/download.html 下载\n"
            "  - macOS: 使用 brew install ffmpeg\n"
            "  - Linux: 使用 sudo apt install ffmpeg 或 sudo yum install ffmpeg"
        )
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)


if __name__ == "__main__":
    # 示例用法
    import sys

    if len(sys.argv) < 2:
        print("用法: python media_formatter.py <input_file> [output_file]")
        print("示例: python media_formatter.py video.mp4")
        print("示例: python media_formatter.py video.mp4 output.mp3")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        result = format_media_file(input_file, output_file)
        print(f"转换完成，输出文件: {result}")
    except Exception as e:
        print(f"转换失败: {e}")
        sys.exit(1)
