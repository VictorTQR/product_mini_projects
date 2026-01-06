from dotenv import load_dotenv
import os
import json
from pathlib import Path
from loguru import logger

load_dotenv()

from langfuse import get_client
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from docxtpl import DocxTemplate

langfuse = get_client()


def extract_all_lesson_info_from_excel(excel_path: str) -> list[dict]:
    """
    从Excel文件中提取所有课次基础信息

    Args:
        excel_path: Excel文件路径

    Returns:
        课次信息列表，每个元素包含课程名称、课次名称、课次描述、上次课次描述
    """
    import pandas as pd
    df = pd.read_excel(excel_path)
    lesson_info_list = []
    for idx, row in df.iterrows():
        lesson_info = {
            "course_name": row["课程名称"],
            "lesson_name": row["课次名称"],
            "lesson_desc": row["课次描述"]
        }
        lesson_info_list.append(lesson_info)
    return lesson_info_list


def generate_lesson_plan_simple(lesson_info: dict, model: str = "glm-4-flash") -> dict:
    """
    生成单次教案

    Args:
        lesson_info: 课次信息字典

    Returns:
        生成的教案结果字典
    """
    course_name = lesson_info["course_name"]
    lesson_name = lesson_info["lesson_name"]
    lesson_desc = lesson_info["lesson_desc"]

    llm = ChatOpenAI(model=model)

    messages_prompt = langfuse.get_prompt("jiaoan/old_lesson_completed_jiaoan")
    messages = messages_prompt.compile(
        course_name=course_name,
        lesson_name=lesson_name,
        lesson_content=lesson_desc,
    )
    logger.debug("已构建课程计划生成消息")

    response = llm.invoke(messages)
    parser = JsonOutputParser()
    result = parser.parse(response.content)

    result["course_name"] = course_name
    result["lesson_name"] = lesson_name

    return result

def save_result_to_json(result: dict, output_path: str):
    """
    将agent运行结果保存为JSON文件

    Args:
        result: agent运行结果字典
        output_path: 输出JSON文件路径
    """
    # 确保输出目录存在
    output_dir = os.path.dirname(output_path)
    if output_dir:
        Path(output_dir).mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    logger.info(f"已将结果保存到 {output_path}")

def save_result_to_word(result: dict, template_word_path: str, output_word_path: str):
    """
    将教案结果保存为Word文档

    Args:
        result: agent运行结果字典
        template_word_path: Word模板文件路径
        output_word_path: 输出Word文件路径
    """
    # 确保输出目录存在
    output_dir = os.path.dirname(output_word_path)
    if output_dir:
        Path(output_dir).mkdir(parents=True, exist_ok=True)

    template_data = result

    # 渲染Word文档
    doc = DocxTemplate(template_word_path)
    doc.render(template_data)
    doc.save(output_word_path)

def generate_and_save_single_lesson(lesson_info: dict, lesson_index: int, output_dir: str, template_word_path: str, model: str = "glm-4-flash"):
    """
    生成单个教案并立即保存为JSON和Word文档

    Args:
        lesson_info: 课次信息字典
        lesson_index: 课次序号
        output_dir: 输出目录路径
        template_word_path: Word模板文件路径
        model: 模型名称

    Returns:
        生成的教案结果字典
    """
    print(f"\n{'='*60}")
    print(f"正在生成第 {lesson_index} 个教案: {lesson_info['course_name']} - {lesson_info['lesson_name']}")
    print(f"{'='*60}")

    # 生成教案
    result = generate_lesson_plan_simple(lesson_info, model)

    # 生成输出文件名
    safe_lesson_name = lesson_info['lesson_name'].replace('/', '_').replace('\\', '_').replace(':', '_')
    base_filename = f"{lesson_index}_{safe_lesson_name}"

    save_dir = os.path.join(output_dir, f"{lesson_info['course_name']}")
    # 保存JSON文件
    json_output_path = os.path.join(save_dir, "json", f"{base_filename}.json")
    save_result_to_json(result, json_output_path)
    print(f"✓ JSON文件已保存: {json_output_path}")

    # 保存Word文档
    word_output_path = os.path.join(save_dir, "word", f"{base_filename}.docx")
    save_result_to_word(result, template_word_path, word_output_path)
    print(f"✓ Word文档已保存: {word_output_path}")

    return result

def main(excel_path: str, output_dir: str, template_word_path: str, model: str = "glm-4-flash"):
    """
    主函数 - 从Excel读取课程信息，生成教案并保存为JSON和Word文档

    Args:
        excel_path: Excel文件路径
        output_dir: 输出目录路径
        template_word_path: Word模板文件路径
        model: 模型名称
    """
    print(f"\n{'='*60}")
    print("教案生成工作流启动")
    print(f"{'='*60}")
    print(f"Excel文件: {excel_path}")
    print(f"输出目录: {output_dir}")
    print(f"Word模板: {template_word_path}")
    print(f"模型: {model}")
    print(f"{'='*60}\n")

    # 1. 从Excel中读取所有lesson_info
    print("正在从Excel读取课程信息...")
    lesson_info_list = extract_all_lesson_info_from_excel(excel_path)
    print(f"✓ 共读取 {len(lesson_info_list)} 个课程信息\n")

    # 2. 遍历lesson_info，生成教案并立即保存
    success_count = 0
    for idx, lesson_info in enumerate(lesson_info_list, start=1):
        try:
            generate_and_save_single_lesson(
                lesson_info=lesson_info,
                lesson_index=idx,
                output_dir=output_dir,
                template_word_path=template_word_path,
                model=model
            )
            success_count += 1
        except Exception as e:
            print(f"✗ 生成第 {idx} 个教案时出错: {e}")
            import traceback
            traceback.print_exc()

    # 3. 输出总结
    print(f"\n{'='*60}")
    print("教案生成工作流完成")
    print(f"{'='*60}")
    print(f"成功生成: {success_count}/{len(lesson_info_list)} 个教案")
    print(f"输出目录: {output_dir}")
    print(f"  - JSON文件: {output_dir}/{lesson_info['course_name']}/")
    print(f"  - Word文档: {output_dir}/{lesson_info['course_name']}/")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    # 配置参数
    excel_path = "./assets/信息生成记录表.xlsx"
    output_dir = "./output_simple"
    template_word_path = "./assets/简案模板.docx"
    model = "glm-4-flash"

    # 执行主函数
    main(
        excel_path=excel_path,
        output_dir=output_dir,
        template_word_path=template_word_path,
        model=model
    )
