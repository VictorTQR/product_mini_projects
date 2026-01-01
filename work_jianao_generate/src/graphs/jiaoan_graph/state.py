from typing import TypedDict
from dataclasses import dataclass

class LessonInfo(TypedDict):
    """
    课程信息
    """
    course_name: str # 课程名称
    lesson_name: str # 课次名称
    lesson_desc: str # 课次内容
    previous_lesson_desc: str # 上一次课次内容

class JiaoanState(TypedDict):
    """
    教案状态
    """
    lesson_info: LessonInfo
    generate_policy: str # 教案生成策略

    lesson_content: str # 课次内容

    lesson_goal: dict # 课次目标
    lesson_plan: list # 课次计划
    lesson_reflection: dict # 课次反思

@dataclass
class JiaoanContext:
    """
    教案上下文
    """
    content_model: str = "glm-4-flash" # 内容模型
    goal_model: str = "glm-4-flash" # 目标模型
    plan_model: str = "glm-4-flash" # 计划模型
    reflection_model: str = "glm-4-flash" # 反思模型