#!/usr/bin/env python3
"""
将用例定稿 MD 文件转换为 Jira CSV 格式。
用法: python3 md_to_csv.py <input_md> <output_csv>
"""

import sys
import re
import csv
import os

# 优先级映射：P0/P1/P2/P3 -> Jira 优先级
PRIORITY_MAP = {
    'P0': 'High',
    'P1': 'Medium',
    'P2': 'Low',
    'P3': 'Low',
    'High': 'High',
    'Medium': 'Medium',
    'Low': 'Low',
}

def validate_input(input_path):
    """验证输入文件"""
    if not os.path.exists(input_path):
        print(f"[FAIL] 输入文件不存在: {input_path}")
        sys.exit(1)
    if not input_path.endswith('.md'):
        print(f"[WARN] 输入文件不是 .md 格式: {input_path}")

def parse_priority(priority_text, scene_type):
    """解析优先级，优先使用显式值，否则根据场景类型推断"""
    # 优先使用表格中的显式优先级
    if priority_text:
        priority_text = priority_text.strip()
        if priority_text in PRIORITY_MAP:
            return PRIORITY_MAP[priority_text]
        # 尝试匹配 P0/P1/P2/P3 格式
        match = re.match(r'P(\d)', priority_text)
        if match:
            level = int(match.group(1))
            if level <= 1:
                return 'High'
            elif level == 2:
                return 'Medium'
            else:
                return 'Low'

    # 回退：根据场景类型推断
    if scene_type == '异常':
        return 'High'
    if scene_type == '并发':
        return 'High'
    if scene_type == '边界':
        return 'Medium'
    return 'Medium'

def parse_steps(steps_text):
    """解析操作步骤文本，返回步骤列表"""
    steps = []
    # 使用更精确的正则：匹配行首或标点后的数字编号
    # 支持 "1. xxx" 和 "1. xxx 2. xxx" 格式
    parts = re.split(r'(?:^|\s+)(\d+)\.\s+', steps_text)
    # parts[0] 可能是空串或前导文本，之后交替为编号和内容
    for i in range(1, len(parts), 2):
        if i + 1 < len(parts):
            step_no = parts[i]
            action = parts[i + 1].strip()
            if action:
                steps.append((step_no, action))
    return steps

def parse_md_table(lines):
    """解析 MD 表格，返回用例列表"""
    testcases = []
    current_suite = ""

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # 检测套件名称 (## 开头)
        if line.startswith('## '):
            current_suite = line.replace('## ', '').strip()
            # 去掉编号前缀如 "一、"
            current_suite = re.sub(r'^[一二三四五六七八九十]+[（(].*', '', current_suite).strip()
            if not current_suite:
                current_suite = line.replace('## ', '').strip()
            i += 1
            continue

        # 检测子套件名称 (### 开头)
        if line.startswith('### '):
            sub_suite = line.replace('### ', '').strip()
            i += 1
            continue

        # 检测表格行
        if line.startswith('| TC-'):
            # 解析表格行
            cells = [c.strip() for c in line.split('|')]
            # cells[0] 是空串，cells[1] 是用例ID，...
            if len(cells) >= 8:
                case_id = cells[1]
                title = cells[2]
                preconditions = cells[3]
                steps_text = cells[4]
                expected = cells[5]
                checkpoints = cells[6]
                scene_type = cells[7]
                # cells[8] 是优先级（如果存在）
                priority_text = cells[8] if len(cells) > 8 else ''

                # 解析优先级
                priority = parse_priority(priority_text, scene_type)

                # 解析步骤
                steps = parse_steps(steps_text)

                testcases.append({
                    'case_id': case_id,
                    'title': title,
                    'preconditions': preconditions,
                    'priority': priority,
                    'steps': steps,
                    'expected': expected,
                    'checkpoints': checkpoints,
                    'suite': current_suite,
                    'scene_type': scene_type
                })

        i += 1

    return testcases

def write_csv(testcases, output_path):
    """写入 CSV 文件"""
    try:
        with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            # 写入表头
            writer.writerow(['序号', '标题', '描述', '优先级', '步骤ID', '步骤', '测试数据', '期望结果', '需求', '测试用例集'])

            for tc in testcases:
                if not tc['steps']:
                    # 无步骤的用例，写一行
                    writer.writerow([
                        tc['case_id'],
                        tc['title'],
                        tc['preconditions'],
                        tc['priority'],
                        '1',
                        tc['title'],
                        '',
                        tc['expected'],
                        tc['checkpoints'],
                        tc['suite']
                    ])
                else:
                    # 多步骤用例，首行填写完整信息
                    first = True
                    for step_no, action in tc['steps']:
                        if first:
                            writer.writerow([
                                tc['case_id'],
                                tc['title'],
                                tc['preconditions'],
                                tc['priority'],
                                step_no,
                                action,
                                '',
                                tc['expected'],
                                tc['checkpoints'],
                                tc['suite']
                            ])
                            first = False
                        else:
                            # 后续行：序号/标题/描述/优先级/需求/测试用例集留空
                            writer.writerow([
                                '',  # 序号
                                '',  # 标题
                                '',  # 描述
                                tc['priority'],  # 优先级保留
                                step_no,
                                action,
                                '',  # 测试数据
                                tc['expected'],
                                '',  # 需求
                                ''   # 测试用例集
                            ])
    except PermissionError:
        print(f"[FAIL] 无写入权限: {output_path}")
        sys.exit(1)
    except Exception as e:
        print(f"[FAIL] 写入 CSV 失败: {e}")
        sys.exit(1)

def main():
    if len(sys.argv) != 3:
        print("用法: python3 md_to_csv.py <input_md> <output_csv>")
        print("示例: python3 md_to_csv.py .testcase-assets/history/xxx/2-用例定稿.md .testcase-assets/history/xxx/jira_export.csv")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    # 验证输入
    validate_input(input_path)

    # 确保输出目录存在
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
        except Exception as e:
            print(f"[FAIL] 无法创建输出目录: {e}")
            sys.exit(1)

    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        print(f"[FAIL] 文件编码错误，请确保为 UTF-8: {input_path}")
        sys.exit(1)
    except Exception as e:
        print(f"[FAIL] 读取文件失败: {e}")
        sys.exit(1)

    testcases = parse_md_table(lines)

    if not testcases:
        print("[WARN] 未解析到任何用例，请检查 MD 文件格式是否正确")
        print("  预期格式: | TC-xxx | 测试点 | 前置条件 | 操作步骤 | 预期结果 | 关联检查点 | 场景类型 | 优先级 |")
        sys.exit(1)

    write_csv(testcases, output_path)

    print(f"[OK] 已生成 Jira CSV: {output_path}")
    print(f"  用例总数: {len(testcases)} 条")
    print(f"  编码: UTF-8 with BOM")

if __name__ == '__main__':
    main()
