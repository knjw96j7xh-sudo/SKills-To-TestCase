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

导出前建议跑版本体检（落后则提示 `--sync`，勿用旧脚本硬导）：

```bash
python3 .testcase-assets/scripts/check_framework_version.py
```

---

## 2. 选择导出平台

```
【选择导出平台】
请选择导出平台（可多选，逗号分隔）：
  J. CSV（默认 Jira；可选 Tapd / 禅道）
  E. Excel（.xlsx）
  X. XMind（思维导图）
  A. 一键全导出（推荐：质检+JSON+多格式）
  S. 冒烟子集（如 P0+P1）
  N. 取消
```

---

## 3. 执行导出

> 所有导出文件均写入选定的子目录：`.testcase-assets/history/<选定目录>/`  
> **主输入是 Markdown 定稿**。优先使用 `export_all.py`；禁止手写整份 `export_data.json`。

### 3a. 一键导出（选 A 或同时选多种格式时优先）

```bash
python3 .testcase-assets/scripts/export_all.py \
  .testcase-assets/history/<选定目录>/2-用例定稿.md \
  --out-dir .testcase-assets/history/<选定目录> \
  --formats j,e,x \
  --project "<项目名称>" \
  --module "<模块名>"
```

冒烟子集（选 S）：

```bash
python3 .testcase-assets/scripts/export_all.py \
  .testcase-assets/history/<选定目录>/2-用例定稿.md \
  --out-dir .testcase-assets/history/<选定目录> \
  --formats e \
  --priority P0,P1 \
  --project "<项目名称>" --module "<模块名>"
```

CSV 工具：`--csv-tool jira|tapd|zentao`。

### 3b. 分步：内容质量检查

```bash
python3 .testcase-assets/scripts/testcase_quality.py \
  .testcase-assets/history/<选定目录>/2-用例定稿.md \
  --audit-output .testcase-assets/history/<选定目录>/audit-summary.md \
  --strict
```

ERROR 级问题须修复定稿后重试；WARN 写入审计摘要，不阻断导出。

### 3c. 分步：CSV

```bash
python3 .testcase-assets/scripts/md_to_csv.py \
  .testcase-assets/history/<选定目录>/2-用例定稿.md \
  .testcase-assets/history/<选定目录>/jira_export.csv

# 可选
python3 .testcase-assets/scripts/md_to_csv.py ... --tool tapd
python3 .testcase-assets/scripts/md_to_csv.py ... --tool zentao
```

- 编码：UTF-8 with BOM
- Jira 优先级：P0→High, P1→Medium, P2/P3→Low；缺省时并发为 P2/Low

### 3d. 分步：Excel / XMind

```bash
python3 .testcase-assets/scripts/md_to_json.py \
  .testcase-assets/history/<选定目录>/2-用例定稿.md \
  .testcase-assets/history/<选定目录>/export_data.json \
  --project "<项目名称>" \
  --module "<测试对象或模块名>"
```

独立导出**允许保留定稿中已有备注**。脚本失败时修正 **Markdown 定稿表** 后重跑，不要手写 JSON。

```bash
python3 .testcase-assets/scripts/export_excel.py \
  .testcase-assets/history/<选定目录>/export_data.json \
  .testcase-assets/history/<选定目录>/testcases.xlsx

python3 .testcase-assets/scripts/export_xmind.py \
  .testcase-assets/history/<选定目录>/export_data.json \
  .testcase-assets/history/<选定目录>/testcases.xmind
```

Excel 后再跑公式审计（若生成了 xlsx）。

---

## 4. 导出完成

```
【导出完成】
[OK] 文件已生成：

  CSV      → .../jira_export.csv（或 tapd/zentao）
  Excel    → .../testcases.xlsx
  XMind    → .../testcases.xmind（含：测试用例 / 按模块 / 统计总览）
  审计摘要 → .../audit-summary.md

[TIP] 可再次运行 /testcase-export；冒烟包见 *-smoke.* 文件。
```
