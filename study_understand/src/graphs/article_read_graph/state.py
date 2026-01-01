"""
Article Read Graph - State 和 Context 定义
"""
from typing import TypedDict, Optional
from dataclasses import dataclass


class ArticleReadState(TypedDict):
    """文章阅读分析的状态"""
    article: str  # 传入的文章内容
    analysis_result: str  # 深度分析节点的结果


@dataclass
class ArticleReadContext:
    """文章阅读分析的上下文配置"""
    analysis_model: str = "glm-4.5-flash"  # 深度分析使用的模型
