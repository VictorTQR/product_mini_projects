import uuid
import json
import random
from pathlib import Path


def make_template(content=''):
    messages = [
        {
            "role": "user",
            "content": content
        }
    ]
    return {
        "custom_id": str(uuid.uuid4()),
        "method": "POST",
        "url": "/v1/chat/completions", 
        "body": {
            "model": "qwen-plus",
            "messages": messages,
            "temperature": 0.1
        }
    }


def read_examples(example_dir):
    """从指定目录读取所有jsonl文件作为示例数据"""
    example_path = Path(example_dir)
    # 如果是相对路径，转换为相对于脚本文件的绝对路径
    if not example_path.is_absolute():
        example_path = Path(__file__).parent / example_dir
    
    example_files = list(example_path.glob('*.jsonl'))
    examples = []
    for example_file in example_files:
        with open(example_file, 'r', encoding='utf-8') as f:
            for line in f:
                example = json.loads(line)
                examples.append(example)
    return examples


def select_random_examples(examples, count=2):
    """从示例数据中随机选择指定数量的数据"""
    if len(examples) < count:
        return examples
    return random.sample(examples, count)


def build_prompt(examples):
    """构建生成数据的提示词"""
    examples_text = ""
    for i, example in enumerate(examples, 1):
        examples_text += f"\n示例{i}：\n{json.dumps(example, ensure_ascii=False, indent=2)}\n"
    
    prompt = f"""请参考以下2条社交媒体数据示例，生成5条新的类似数据。

{examples_text}

要求：
1. 生成的数据结构必须与示例一致（post_id、media、content、like_count、collect_count、comment_count、comments、tag、publish_date、platform）
2. id字段改为post_id
3. platform字段为社交媒体平台名称（小红书、抖音、微博等）
4. 内容风格要符合平台真实用户的发布风格
5. 生成的5条数据主题都为打铁花，但是内容及评论不能完全相同，且应主要是正面情感
6. 请以JSON格式返回，格式为：{{"datas": [生成的5条数据]}}
"""
    return prompt


def generate_jsonl(count=1000, example_dir='crawler/data'):
    """生成batch.jsonl文件
    
    Args:
        count: 要生成的请求数量
        example_dir: 示例数据目录路径
    """
    # 读取所有示例数据
    examples = read_examples(example_dir)
    print(f"已读取 {len(examples)} 条示例数据")
    
    if not examples:
        print("警告：未找到示例数据，请检查example_dir路径")
        return
    
    # 生成batch.jsonl文件
    with open('batch.jsonl', 'w', encoding='utf-8') as f:
        for i in range(count):
            # 随机选择2条示例数据
            selected_examples = select_random_examples(examples, 2)
            
            # 构建提示词
            prompt = build_prompt(selected_examples)
            
            # 生成模板
            template = make_template(prompt)
            
            # 写入文件
            f.write(json.dumps(template, ensure_ascii=False) + '\n')
            
            # 进度提示
            if (i + 1) % 10 == 0 or i == 0:
                print(f"已生成 {i + 1}/{count} 个请求")
    
    print(f"完成！已生成 {count} 个请求到 batch.jsonl")


if __name__ == '__main__':
    generate_jsonl(count=300, example_dir='data')
