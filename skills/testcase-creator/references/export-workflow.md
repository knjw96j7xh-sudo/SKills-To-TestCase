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

若本次为增量变更模式，定稿文首须包含「本轮变更摘要」（新增/修改/废弃 ID 列表），再接完整有效用例表。废弃用例不得出现在有效表中。

## 2. 统一导出原则

- **主输入是 Markdown 定稿**，不要由 Agent 手写整份 `export_data.json`。
- Excel / XMind 中间 JSON 必须由 `md_to_json.py` 从定稿生成。
- 导出前必须跑内容质量检查；ERROR 阻断，WARN 写入审计摘要但不阻断。
- 生成流程（含全量与增量）中所有用例的 `remark` 必须为空；独立 `/testcase-export` 可保留已有备注。

## 3. Jira CSV

```bash
python3 .testcase-assets/scripts/testcase_quality.py \
  <运行目录>/2-用例定稿.md \
  --audit-output <运行目录>/audit-summary.md \
  --strict
```

修复阻断项后：

```bash
python3 .testcase-assets/scripts/md_to_csv.py \
  <运行目录>/2-用例定稿.md \
  <运行目录>/jira_export.csv
```

CSV 使用 UTF-8 BOM。优先级映射：P0→High、P1→Medium、P2/P3→Low；缺省优先级按场景类型推断（异常=P0/High，正向/边界=P1/Medium，**并发=P2/Low**）。多步骤首行填基础信息，后续行填步骤。

## 4. Excel 与 XMind

### 4.1 质检

```bash
python3 .testcase-assets/scripts/testcase_quality.py \
  <运行目录>/2-用例定稿.md \
  --audit-output <运行目录>/audit-summary.md \
  --strict
```

### 4.2 MD → JSON（必须用脚本）

从 `project.config.md` 读取项目名称，测试对象使用本次模块名：

```bash
python3 .testcase-assets/scripts/md_to_json.py \
  <运行目录>/2-用例定稿.md \
  <运行目录>/export_data.json \
  --project "<项目名称>" \
  --module "<测试对象>"
```

生成后校验备注（生成流程强制为空）：

```bash
python3 -c "import json; d=json.load(open('<运行目录>/export_data.json')); assert all(tc.get('remark', '') == '' for tc in d['testcases'])"
```

禁止跳过 `md_to_json.py` 手写 JSON。仅当脚本失败且无法修复定稿表时，才允许手工修正 **MD 表** 后重跑脚本，不得直接编造 JSON 字段。

### 4.3 导出

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

## 5. 完成处理

将本次运行记录追加到 `.testcase-assets/history/history-index.md`。增量模式须标注 `mode: 增量` 与基线目录名。输出至少包含：

- 测试对象和用例总数；
- 正向、异常、边界、并发分布；
- 关联检查点和评审轮次（增量则含变更摘要）；
- 运行目录、定稿和各导出文件；
- `audit-summary.md` 路径；
- 全阶段 token 消耗与累计值（读不到终端统计时可跳过，不阻断）。

审计摘要必须包含模块数量与分布、场景分布、字段空值、重复 ID、异常字段、内容质量警告和 Excel 公式错误。
