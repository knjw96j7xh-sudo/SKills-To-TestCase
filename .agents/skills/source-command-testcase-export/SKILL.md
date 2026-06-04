---
name: "source-command-testcase-export"
description: "独立导出命令，从已定稿的用例文件导出为 Jira CSV / Excel / XMind 格式"
---

# source-command-testcase-export

Use this skill when the user asks to run the migrated source command `testcase-export`.

## Command Template

# 用例导出 Skill — testcase-export

> 从 `.testcase-assets/history/` 子目录中的定稿文件独立导出，无需重走用例生成流程。

---

## 1. 扫描定稿文件

**优先读取索引**：读取 `.testcase-assets/history/history-index.md`，列出所有已记录的运行。

若索引文件不存在或为空，则扫描 `.testcase-assets/history/` 下所有子目录，查找 `2-用例定稿.md` 文件。

若无定稿文件，提示：
```
[FAIL] 未找到定稿文件。请先运行 /testcase-creator 生成用例。
```

若有文件，列出供选择：
```
【选择定稿文件】
找到以下用例定稿，请选择（输入编号）：

  [1] 20260601_175456_碳盘查清单  （118 条用例，2026-06-01）
  [2] 20260615_090000_用户中心    （45 条用例，2026-06-15）
```

---

## 2. 选择导出平台

```
【选择导出平台】
请选择导出平台（可多选，逗号分隔）：
  J. Jira CSV（.csv，可直接导入 Jira）
  E. Excel（.xlsx 表格，带颜色分类、冻结表头）
  X. XMind（思维导图，用于用例展示和评审）
  N. 取消
```

---

## 3. 执行导出

> 所有导出文件均写入选定的子目录：`.testcase-assets/history/<选定目录>/`

### 3a. Jira CSV 导出（若选 J）

- 按 `.testcase-assets/templates/csv-schema.json` 的字段映射规则生成 CSV
- 运行转换脚本：
  ```bash
  python3 .testcase-assets/scripts/md_to_csv.py \
    .testcase-assets/history/<选定目录>/2-用例定稿.md \
    .testcase-assets/history/<选定目录>/jira_export.csv
  ```
- 编码：UTF-8 with BOM
- 提示：`[EXPORT] Jira CSV 已生成，请手动导入 Jira 系统。`

### 3b. Excel / XMind 导出（若选 E 或 X）

**步骤 A — 序列化用例数据**：将定稿用例以如下 JSON 格式写入中间文件 `.testcase-assets/history/<选定目录>/export_data.json`：

```json
{
  "meta": {
    "project": "<从 .testcase-assets/project.config.md 读取项目名称>",
    "module": "<本次测试模块名>",
    "generated_at": "<YYYY-MM-DD>"
  },
  "testcases": [
    {
      "id": "TC-001",
      "test_point": "测试点描述",
      "precondition": "前置条件",
      "steps": "1. 步骤一\n2. 步骤二",
      "expected": "预期结果",
      "checkpoint": "XX-01",
      "type": "正向",
      "priority": "P1"
    }
  ]
}
```

**步骤 B — 调用导出脚本**：

- 若选 **E**（Excel）：
  ```bash
  python3 .testcase-assets/scripts/export_excel.py \
    .testcase-assets/history/<选定目录>/export_data.json \
    .testcase-assets/history/<选定目录>/testcases.xlsx
  ```

- 若选 **X**（XMind）：
  ```bash
  python3 .testcase-assets/scripts/export_xmind.py \
    .testcase-assets/history/<选定目录>/export_data.json \
    .testcase-assets/history/<选定目录>/testcases.xmind
  ```

---

## 4. 导出完成

```
【导出完成】
[OK] 文件已生成：

  Jira CSV → .testcase-assets/history/<选定目录>/jira_export.csv
  Excel    → .testcase-assets/history/<选定目录>/testcases.xlsx（如已生成）
  XMind    → .testcase-assets/history/<选定目录>/testcases.xmind（如已生成）

[TIP] 可再次运行 /testcase-export 导出其他格式。
[TOKEN] 本次会话结束时，请留意终端底部的 token 消耗统计。
```
