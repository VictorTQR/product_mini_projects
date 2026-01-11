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


def load_result_from_json(json_path: str) -> dict:
    """
    从JSON文件加载教案结果

    Args:
        json_path: JSON文件路径

    Returns:
        教案结果字典
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        result = json.load(f)
    return result

def _sanitize_template_data(data: any) -> any:
    """
    清洗模板数据中的特殊字符，防止Jinja2模板解析错误

    Args:
        data: 原始数据（可以是字符串、字典、列表或其他类型）

    Returns:
        清洗后的数据
    """
    import html
    if isinstance(data, str):
        # 转义Jinja2模板特殊字符（< >）
        return html.escape(data)
    elif isinstance(data, dict):
        # 递归清洗字典的值
        return {key: _sanitize_template_data(value) for key, value in data.items()}
    elif isinstance(data, list):
        # 递归清洗列表的元素
        return [_sanitize_template_data(item) for item in data]
    else:
        # 其他类型保持不变
        return data


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

    # 清洗模板数据中的特殊字符
    template_data = _sanitize_template_data(template_data)

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
        model: 模型名称，默认"glm-4-flash"

    Returns:
        生成的教案结果字典
    """
    print(f"\n{'='*60}")
    print(f"正在处理第 {lesson_index} 个教案: {lesson_info['course_name']} - {lesson_info['lesson_name']}")
    print(f"{'='*60}")

    # 生成输出文件名
    safe_lesson_name = lesson_info['lesson_name'].replace('/', '_').replace('\\', '_').replace(':', '_')
    base_filename = f"{lesson_index}_{safe_lesson_name}"

    course_name = lesson_info["course_name"]
    json_output_path = os.path.join(output_dir, course_name, "json", f"{base_filename}.json")
    word_output_path = os.path.join(output_dir, course_name, "word", f"{base_filename}.docx")

    # 检查文件是否存在
    json_exists = os.path.exists(json_output_path)
    word_exists = os.path.exists(word_output_path)

    if json_exists and word_exists:
        # 两个文件都存在，跳过生成
        print(f"⏭️  教案已存在，跳过生成")
        print(f"   JSON文件: {json_output_path}")
        print(f"   Word文档: {word_output_path}")
        result = load_result_from_json(json_output_path)
    elif json_exists and not word_exists:
        # JSON存在但Word不存在，从JSON读取并生成Word
        print(f"📄 JSON文件已存在，正在读取并生成Word文档")
        result = load_result_from_json(json_output_path)
        save_result_to_word(result, template_word_path, word_output_path)
        print(f"✓ Word文档已保存: {word_output_path}")
    else:
        # 两个文件都不存在，执行正常生成流程
        print(f"🔄 正在生成教案...")
        result = generate_lesson_plan_simple(lesson_info, model=model)
        
        # 保存JSON文件
        save_result_to_json(result, json_output_path)
        print(f"✓ JSON文件已保存: {json_output_path}")

        # 保存Word文档
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
        model: 模型名称，默认"glm-4-flash"
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
                model=model,
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


def test_generate_lesson_plan_simple():
    """
    测试生成教案的简单函数
    """
    # 准备测试数据
    test_lesson_info = {
        "lesson_index": 1,
        "course_name": "前端开发",
        "lesson_name": "HTML基础",
        "lesson_desc": "介绍HTML的基本结构和标签",
    }
    # 调用函数生成教案
    result = generate_lesson_plan_simple(test_lesson_info)
    # 检查结果是否包含预期的键
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    # 配置参数
    course = "网页设计"
    excel_path = f"./output/{course}.xlsx"
    output_dir = "./output/output_workflow"
    template_word_path = f"./output/{course}.docx"

    # 测试生成教案的简单函数
    # test_generate_lesson_plan_simple()
    # exit(0)

    # 执行主函数
    main(
        excel_path=excel_path,
        output_dir=output_dir,
        template_word_path=template_word_path,
        model="glm-4.5-flash"
    )
