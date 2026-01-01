"""
SiliconFlow ASR (自动语音识别) 服务调用模块
"""
import os
import requests
from typing import Optional
from loguru import logger

# 配置 loguru
logger.add(
    "logs/siliconflow_asr_{time}.log",
    rotation="10 MB",
    retention="7 days",
    level="INFO"
)


class SiliconFlowASR:
    """SiliconFlow ASR 服务客户端"""
    supported_models = [
        "FunAudioLLM/SenseVoiceSmall",
        "TeleAI/TeleSpeechASR"
    ]

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化 SiliconFlow ASR 客户端

        Args:
            api_key: SiliconFlow API 密钥。如果不提供，将从环境变量 SILICONFLOW_API_KEY 中读取
        """
        self.api_key = api_key or os.getenv('SILICONFLOW_API_KEY')
        if not self.api_key:
            logger.error("API Key 未提供")
            raise ValueError(
                "API Key 未提供。请通过以下方式之一提供：\n"
                "1. 构造函数参数: SiliconFlowASR(api_key='your-key')\n"
                "2. 环境变量: export SILICONFLOW_API_KEY='your-key'"
            )

        logger.info("SiliconFlow ASR 客户端初始化成功")
        self.base_url = "https://api.siliconflow.cn/v1/audio/transcriptions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}"
        }

    def _check_model(self, model: str):
        """检查模型是否支持"""
        if model not in self.supported_models:
            logger.error(f"模型 {model} 不支持")
            raise ValueError(
                f"模型 {model} 不支持。请选择以下模型之一：{self.supported_models}"
            )

    def transcribe(
        self,
        audio_file_path: str,
        model: str = "FunAudioLLM/SenseVoiceSmall"
    ) -> str:
        """
        对音频文件进行语音识别

        Args:
            audio_file_path: 音频文件路径（支持 mp3, wav, m4a 等格式）
            model: 使用的 ASR 模型
                - FunAudioLLM/SenseVoiceSmall (默认)
                - TeleAI/TeleSpeechASR

        Returns:
            str: 识别出的文本内容

        Raises:
            FileNotFoundError: 音频文件不存在
            requests.RequestException: API 请求失败
            ValueError: API 返回错误
        """
        logger.info(f"开始语音识别: {audio_file_path}, 模型: {model}")
        
        # 检查模型是否支持
        self._check_model(model)
        
        # 检查文件是否存在
        if not os.path.exists(audio_file_path):
            logger.error(f"音频文件不存在: {audio_file_path}")
            raise FileNotFoundError(f"音频文件不存在: {audio_file_path}")

        # 准备请求数据
        payload = {
            "model": model
        }

        try:
            # 打开音频文件并发送请求
            logger.debug(f"发送 API 请求到: {self.base_url}")
            with open(audio_file_path, 'rb') as audio_file:
                files = {
                    "file": (
                        os.path.basename(audio_file_path),
                        audio_file,
                        'audio/mpeg'  # 对于 mp3 文件
                    )
                }

                response = requests.post(
                    self.base_url,
                    data=payload,
                    files=files,
                    headers=self.headers
                )

            # 检查响应状态
            response.raise_for_status()

            # 解析响应
            result = response.json()

            # 返回识别的文本
            if 'text' in result:
                logger.success(f"语音识别成功，文本长度: {len(result['text'])}")
                logger.debug(f"识别文本: {result['text'][:100]}...")
                return result['text']
            else:
                logger.error(f"API 响应格式异常: {result}")
                raise ValueError(f"API 响应格式异常: {result}")

        except requests.exceptions.HTTPError as e:
            error_msg = f"API 请求失败 (状态码: {response.status_code})"
            try:
                error_detail = response.json()
                error_msg += f"\n错误详情: {error_detail}"
            except:
                error_msg += f"\n响应内容: {response.text}"
            logger.error(error_msg)
            raise requests.RequestException(error_msg) from e

        except requests.exceptions.RequestException as e:
            logger.error(f"网络请求失败: {str(e)}")
            raise requests.RequestException(f"网络请求失败: {str(e)}") from e

    def transcribe_with_format(
        self,
        media_file_path: str,
        model: str = "FunAudioLLM/SenseVoiceSmall",
        keep_temp_file: bool = False
    ) -> str:
        """
        对音视频文件进行格式转换后进行语音识别

        Args:
            media_file_path: 音视频文件路径
            model: 使用的 ASR 模型
            keep_temp_file: 是否保留转换后的临时 mp3 文件，默认删除

        Returns:
            str: 识别出的文本内容
        """
        from ..utils.media_formatter import format_media_file

        logger.info(f"开始格式转换并识别: {media_file_path}")

        # 先转换为 16KHz 的 mp3 文件
        formatted_audio = format_media_file(media_file_path)

        try:
            # 进行语音识别
            result = self.transcribe(formatted_audio, model=model)
            return result
        finally:
            # 除非明确要求保留，否则删除临时文件
            if not keep_temp_file and os.path.exists(formatted_audio):
                try:
                    os.remove(formatted_audio)
                    logger.info(f"已删除临时文件: {formatted_audio}")
                except Exception as e:
                    logger.warning(f"删除临时文件失败 {formatted_audio}: {e}")



if __name__ == "__main__":
    # 示例用法
    import sys

    if len(sys.argv) < 2:
        print("用法: python siliconflow_asr.py <audio_file_path>")
        print("示例: python siliconflow_asr.py test_audio.mp3")
        sys.exit(1)

    audio_file = sys.argv[1]

    try:
        client = SiliconFlowASR()
        text = client.transcribe(audio_file)
        print(f"\n识别结果:")
        print(text)

    except Exception as e:
        print(f"识别失败: {e}")
        sys.exit(1)
