"""
教案生成工作流 - 从Excel读取课程信息，生成教案并立即保存为JSON和Word文档
"""
from loguru import logger
from dotenv import load_dotenv
import os
import json
from pathlib import Path

load_dotenv()


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
            "lesson_index": row["课次序号"],
            "course_name": row["课程名称"],
            "lesson_name": row["课次名称"],
            "lesson_desc": row["课次描述"],
            "previous_lesson_desc": df.loc[idx-1, "课次描述"] if idx > 0 else "",
        }
        lesson_info_list.append(lesson_info)
    return lesson_info_list


def generate_lesson_plan_simple(lesson_info: dict) -> dict:
    """
    生成单次教案

    Args:
        lesson_info: 课次信息字典

    Returns:
        生成的教案结果字典
    """
    from src.graphs.jiaoan_graph.graph import create_jiaoan_graph
    agent = create_jiaoan_graph().compile()
    # result = agent.invoke({"lesson_info": lesson_info}, context={"plan_model": "glm-4.5-air"})
    result = agent.invoke({"lesson_info": lesson_info}, context={"plan_model": "glm-4-flash"})
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


def save_result_to_word(result: dict, lesson_info: dict, template_word_path: str, output_word_path: str):
    """
    将教案结果保存为Word文档

    Args:
        result: agent运行结果字典
        lesson_info: 课次信息字典
        template_word_path: Word模板文件路径
        output_word_path: 输出Word文件路径
    """
    # 确保输出目录存在
    output_dir = os.path.dirname(output_word_path)
    if output_dir:
        Path(output_dir).mkdir(parents=True, exist_ok=True)

    # 构建教案数据结构（与02_write_word_func.py中的格式保持一致）
    jiaoan_data = {
        "课次序号": str(lesson_info.get("lesson_index", "")),
        "课次名称": lesson_info.get("lesson_name", ""),
        "教学目标及重难点": result.get("lesson_goal", {}),
        "教学环节": result.get("lesson_plan", []),
        "教学反思": result.get("lesson_reflection", {})
    }

    from docxtpl import DocxTemplate

    # 转换为模板数据
    template_data = _transform_data(jiaoan_data)
    
    # 清洗模板数据中的特殊字符
    template_data = _sanitize_template_data(template_data)

    # 渲染Word文档
    doc = DocxTemplate(template_word_path)
    doc.render(template_data)
    doc.save(output_word_path)


def _transform_data(data: dict) -> dict:
    """
    将教案数据转换为模板格式

    Args:
        data: 教案数据字典

    Returns:
        转换后的模板数据字典
    """
    template_data = {}
    
    # 课次基本信息
    if "课次序号" in data:
        template_data["lesson_index"] = data["课次序号"]
    if "课次名称" in data:
        template_data["lesson_name"] = data["课次名称"]

    # 教学目标及重难点
    if "教学目标及重难点" in data:
        goals = data["教学目标及重难点"]
        template_data["lesson_goal_zhishi"] = goals.get("知识目标", "")
        template_data["lesson_goal_nengli"] = goals.get("能力目标", "")
        template_data["lesson_goal_suzhi"] = goals.get("素质目标", "")
        template_data["lesson_goal_zhongdian"] = goals.get("教学重点", "")
        template_data["lesson_goal_nandian"] = goals.get("教学难点", "")

    # 教学反思
    if "教学反思" in data:
        reflection = data["教学反思"]
        template_data["lesson_xiaoguo"] = reflection.get("学习效果", "")
        template_data["lesson_chuangxin"] = reflection.get("特色创新", "")
        template_data["lesson_gaijin"] = reflection.get("诊断改进", "")

    # 教学环节
    if "教学环节" in data:
        # 静态环节名称到字段前缀的映射
        static_link_map = {
            "上次课内容复习": "lesson_plan_fuxi",
            "引入": "lesson_plan_yinru",
            "知识内容讲解1": "lesson_plan_jiangjie1",
            "知识内容讲解2": "lesson_plan_jiangjie2",
        }
        
        for item in data["教学环节"]:
            link_name = item.get("环节名称", "")
            if link_name in static_link_map:
                prefix = static_link_map[link_name]
                template_data[f"{prefix}_content"] = item.get("教学内容", "")
                template_data[f"{prefix}_teacher"] = item.get("教师活动", "")
                template_data[f"{prefix}_student"] = item.get("学生活动", "")
                template_data[f"{prefix}_yitu"] = item.get("教学意图", "")
    
    return template_data


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


def generate_and_save_single_lesson(lesson_info: dict, lesson_index: int, output_dir: str, template_word_path: str):
    """
    生成单个教案并立即保存为JSON和Word文档

    Args:
        lesson_info: 课次信息字典
        lesson_index: 课次序号
        output_dir: 输出目录路径
        template_word_path: Word模板文件路径

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
        save_result_to_word(result, lesson_info, template_word_path, word_output_path)
        print(f"✓ Word文档已保存: {word_output_path}")
    else:
        # 两个文件都不存在，执行正常生成流程
        print(f"🔄 正在生成教案...")
        result = generate_lesson_plan_simple(lesson_info)
        
        # 保存JSON文件
        save_result_to_json(result, json_output_path)
        print(f"✓ JSON文件已保存: {json_output_path}")

        # 保存Word文档
        save_result_to_word(result, lesson_info, template_word_path, word_output_path)
        print(f"✓ Word文档已保存: {word_output_path}")

    return result


def main(excel_path: str, output_dir: str, template_word_path: str):
    """
    主函数 - 从Excel读取课程信息，生成教案并保存为JSON和Word文档

    Args:
        excel_path: Excel文件路径
        output_dir: 输出目录路径
        template_word_path: Word模板文件路径
    """
    print(f"\n{'='*60}")
    print("教案生成工作流启动")
    print(f"{'='*60}")
    print(f"Excel文件: {excel_path}")
    print(f"输出目录: {output_dir}")
    print(f"Word模板: {template_word_path}")
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
                template_word_path=template_word_path
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
    print(f"  - JSON文件: {output_dir}/json/")
    print(f"  - Word文档: {output_dir}/word/")
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
        "lesson_gaijin": "学生需要掌握HTML的基本标签和文档结构"
    }
    # 调用函数生成教案
    result = generate_lesson_plan_simple(test_lesson_info)
    # 检查结果是否包含预期的键
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    # 配置参数
    course = "web前端开发"
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
        template_word_path=template_word_path
    )
