# 定稿与导出工作流

## 1. 定稿

把最终完整用例表写入 `<运行目录>/2-用例定稿.md`，然后询问：

```text
【阶段 5 — 定稿导出】
J. Jira CSV
E. Excel
X. XMind
N. 不导出
```

## 2. Jira CSV

先对 Markdown 定稿执行质检并生成审计摘要：

```bash
python3 .testcase-assets/scripts/testcase_quality.py \
  <运行目录>/2-用例定稿.md \
  --audit-output <运行目录>/audit-summary.md \
  --strict
```

修复阻断项后执行：

```bash
python3 .testcase-assets/scripts/md_to_csv.py \
  <运行目录>/2-用例定稿.md \
  <运行目录>/jira_export.csv
```

CSV 使用 UTF-8 BOM。优先级映射为 P0→High、P1→Medium、P2/P3→Low；多步骤首行填写基础信息，后续行填写步骤和预期。

## 3. Excel 与 XMind

### 3.1 序列化 JSON

将定稿序列化为 `<运行目录>/export_data.json`：

```json
{
  "meta": {
    "project": "项目名称",
    "module": "测试对象",
    "generated_at": "YYYY-MM-DD"
  },
  "testcases": [
    {
      "id": "TC-001",
      "module": "所属模块",
      "test_point": "测试点",
      "precondition": "前置条件",
      "steps": "1. 步骤一\n2. 步骤二",
      "expected": "1. 结果一\n2. 结果二",
      "checkpoint": "XX-01",
      "type": "正向",
      "priority": "P1",
      "remark": ""
    }
  ]
}
```

`module` 为必填字段。生成流程中的 `remark` 必须固定为空字符串，不得删除字段规避检查。

### 3.2 JSON 与质量检查

先验证严格 JSON：

```bash
python3 -c "import json; json.load(open('<运行目录>/export_data.json'))"
```

失败时修复单引号、尾逗号、未转义引号、Python 字面量、BOM、真实换行、反斜杠或前导零等问题并重试。然后验证备注并执行质检：

```bash
python3 -c "import json; d=json.load(open('<运行目录>/export_data.json')); assert all(tc.get('remark', '') == '' for tc in d['testcases'])"

python3 .testcase-assets/scripts/testcase_quality.py \
  <运行目录>/export_data.json \
  --audit-output <运行目录>/audit-summary.md \
  --strict
```

`--strict` 阻断重复 ID、重复步骤编号、核心必填字段空值和非法枚举；模糊措辞、术语、引号及步骤对应关系作为警告写入摘要。

### 3.3 导出

```bash
python3 .testcase-assets/scripts/export_excel.py \
  <运行目录>/export_data.json <运行目录>/testcases.xlsx

python3 .testcase-assets/scripts/export_xmind.py \
  <运行目录>/export_data.json <运行目录>/testcases.xmind
```

Excel 导出后更新公式审计：

```bash
python3 .testcase-assets/scripts/testcase_quality.py \
  <运行目录>/export_data.json \
  --audit-output <运行目录>/audit-summary.md \
  --xlsx <运行目录>/testcases.xlsx \
  --strict
```

## 4. 完成处理

将本次运行记录追加到 `.testcase-assets/history/history-index.md`。输出至少包含：

- 测试对象和用例总数；
- 正向、异常、边界、并发分布；
- 关联检查点和评审轮次；
- 运行目录、定稿和各导出文件；
- `audit-summary.md` 路径；
- 全阶段 token 消耗与累计值。

审计摘要必须包含模块数量与分布、场景分布、字段空值、重复 ID、异常字段、内容质量警告和 Excel 公式错误。
