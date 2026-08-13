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
> **主输入是 Markdown 定稿**。Excel/XMind 的 JSON 必须由 `md_to_json.py` 生成，禁止手写整份 `export_data.json`。

### 3a. 内容质量检查（所有导出前）

```bash
python3 .testcase-assets/scripts/testcase_quality.py \
  .testcase-assets/history/<选定目录>/2-用例定稿.md \
  --audit-output .testcase-assets/history/<选定目录>/audit-summary.md \
  --strict
```

ERROR 级问题须修复定稿后重试；WARN 写入审计摘要，不阻断导出。

### 3b. Jira CSV 导出（若选 J）

```bash
python3 .testcase-assets/scripts/md_to_csv.py \
  .testcase-assets/history/<选定目录>/2-用例定稿.md \
  .testcase-assets/history/<选定目录>/jira_export.csv
```

- 编码：UTF-8 with BOM
- 优先级：P0→High, P1→Medium, P2/P3→Low；缺省时并发为 P2/Low
- 多步骤：首行填基础信息，后续行填步骤
- 提示：`[EXPORT] Jira CSV 已生成，请手动导入 Jira 系统。`

### 3c. Excel / XMind 导出（若选 E 或 X）

**步骤 A — MD 转 JSON（必须用脚本）**

从 `.testcase-assets/project.config.md` 读取项目名称：

```bash
python3 .testcase-assets/scripts/md_to_json.py \
  .testcase-assets/history/<选定目录>/2-用例定稿.md \
  .testcase-assets/history/<选定目录>/export_data.json \
  --project "<项目名称>" \
  --module "<测试对象或模块名>"
```

独立导出**允许保留定稿中已有备注**；不得用审计信息覆盖备注。  
脚本失败时修正 **Markdown 定稿表** 后重跑，不要手写 JSON。

**步骤 B — 调用导出脚本**

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

**步骤 C — Excel 公式审计（若生成了 xlsx）**

```bash
python3 .testcase-assets/scripts/testcase_quality.py \
  .testcase-assets/history/<选定目录>/export_data.json \
  --audit-output .testcase-assets/history/<选定目录>/audit-summary.md \
  --xlsx .testcase-assets/history/<选定目录>/testcases.xlsx \
  --strict
```

**步骤 D — 确认输出**

```text
[OK] 文件已生成：
  Excel → .testcase-assets/history/<选定目录>/testcases.xlsx
  XMind → .testcase-assets/history/<选定目录>/testcases.xmind
[TIP] XMind 文件需 XMind 8 或更高版本打开。
```

---

## 4. 导出完成

```
【导出完成】
[OK] 文件已生成：

  Jira CSV → .testcase-assets/history/<选定目录>/jira_export.csv
  Excel    → .testcase-assets/history/<选定目录>/testcases.xlsx（如已生成）
  XMind    → .testcase-assets/history/<选定目录>/testcases.xmind（如已生成）
  审计摘要 → .testcase-assets/history/<选定目录>/audit-summary.md

[TIP] 可再次运行 /testcase-export 导出其他格式。
```
