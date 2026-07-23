# 用例生成 Skill — testcase-creator

> 先确认输入，不自动导入，不生成自动化测试代码；检查点和评审点可随项目经验持续沉淀。

## Reference 路由

按阶段读取以下文件，不要一次性加载全部 reference：

- 进入阶段 1 前，完整读取 `references/testcase-creator/input-and-generation.md`。
- 进入阶段 4 前，完整读取 `references/testcase-creator/review-workflow.md`。
- 进入阶段 5 前，完整读取 `references/testcase-creator/export-workflow.md`。

reference 中的要求是本流程的一部分，读取后必须执行，不得只作为建议。

## 0. 初始化检查（每次触发自动执行）

1. 检查 `.testcase-assets/checkpoints-index.md` 是否存在；不存在则提示用户创建并中止流程。
2. 检查 `.testcase-assets/review-expectations-index.md` 是否存在；不存在则提示用户创建并中止流程。
3. 读取 `.testcase-assets/project.config.md`（若存在），载入项目名称、英文标识、业务域、导出路径、默认优先级规则和评审默认维度。
4. 检查 `project.config.md` 是否包含 `[填写` 开头的占位符。发现任何占位符时直接中止，不提供继续选项：

```text
[BLOCK] project.config.md 中存在未填写的占位符，无法继续：
  - [填写项目中文名] → 请替换为实际项目名称
  - [填写英文缩写] → 请替换为实际英文标识
  - [填写姓名] → 请替换为测试负责人姓名
  - [填写团队共享路径] → 请替换为实际共享路径
请先完善配置，再重新触发 /testcase-creator。
```

5. 初始化通过后输出：

```text
[OK] 资产加载成功
[DIR] 检查点索引：.testcase-assets/checkpoints-index.md
[DIR] 评审点索引：.testcase-assets/review-expectations-index.md
[DIR] 项目配置：.testcase-assets/project.config.md（已载入上下文）
>> 开始用例生成流程，共 5 个阶段，每步需您确认后继续。
```

每个阶段结束时记录终端累计 token，阶段 5 汇总各阶段差值。

## 1. 需求与设计输入（阶段 1/5）

进入本阶段前完整读取 `references/testcase-creator/input-and-generation.md` 的“阶段 1”。

1. 提示用户选择 A-H 的需求来源，可组合提供文字需求和设计稿导出文件。
2. 读取文件或链接，保留多来源归属。设计稿 PDF 必须同时检查文本和渲染页面。
3. 输出需求要素、设计要素及两者差异，等待用户明确回复“确认”。
4. 确认后清理模块名中的文件系统非法字符，创建：
   `.testcase-assets/history/<YYYYMMDD>_<HHMMSS>_<模块名>/`。
5. 后续文件全部写入该运行目录，记录阶段 1 token 基线。

不得用设计稿覆盖文字需求；发现冲突时必须列为待确认项。

## 2. 输入结构化（阶段 2/5）

触发条件：用户确认阶段 1 解析结果。

1. 按分类完整展示 `.testcase-assets/checkpoints-index.md` 中的检查点。
2. 接受编号列表、“全选”或“跳过”。
3. 生成需求要素、设计要素、差异项和已关联检查点摘要。
4. 写入 `<运行目录>/0-用例准备.md`。
5. 等待用户回复“生成用例”，记录阶段 2 token 基线。

具体提示和输出模板见 `references/testcase-creator/input-and-generation.md` 的“阶段 2”。

## 3. 用例生成（阶段 3/5）

触发条件：用户回复“生成用例”。进入本阶段时读取 `references/testcase-creator/input-and-generation.md` 的“阶段 3”。

1. 读取 `.testcase-assets/templates/testcase-table-config.json`；缺失时使用默认 9 列。
2. 仅在用户主动要求时加入可选列。
3. 基于需求、设计、差异结论和检查点生成正向、异常、边界、并发用例。
4. 单模块需求的“所属模块”统一填写测试对象，多模块需求填写对应子模块。
5. 写入 `<运行目录>/1-评审记要.md`，等待用户进入评审或提出修改。

**备注列强制规则**：生成用例的“备注”必须为空。不得写入来源 ID、历史备注、评审结论、检查点说明或追踪信息；过程信息写入评审报告或审计摘要。

## 4. 评审优化（阶段 4/5）

触发条件：用户回复“进入评审”。进入本阶段前完整读取 `references/testcase-creator/review-workflow.md`。

1. 展示评审点并按 UX、DATA、COMP、EXEC、BUG、SEC、PERF 等分类分组。
2. 第 1 轮全量评审；第 2 轮起仅展开新增或修改用例，已有用例只提供摘要。
3. 每个选中维度使用一个独立 subagent 并行评审，每个 subagent 只接收该维度评审点。
4. 合并覆盖结论、去重补充建议，分别写入：
   - `<运行目录>/1-评审报告-第N轮.md`
   - `<运行目录>/1-评审记要.md`（只保留最终用例表）
5. 用户选择 A/B/C/D 时合并修改并进入下一轮增量评审；选择 E 时进入阶段 5。

不得跳过用户决策或把历轮评审内容混入最终用例表。

## 5. 定稿导出（阶段 5/5）

触发条件：用户确认评审通过。进入本阶段前完整读取 `references/testcase-creator/export-workflow.md`。

1. 写入 `<运行目录>/2-用例定稿.md`。
2. 询问导出平台：Jira CSV、Excel、XMind 或不导出。
3. 导出前必须运行内容质量检查，并生成 `<运行目录>/audit-summary.md`：

```bash
python3 .testcase-assets/scripts/testcase_quality.py \
  <输入文件> --audit-output <运行目录>/audit-summary.md --strict
```

4. 质检失败时修复用例数据并重新运行，直到通过；警告项必须写入审计摘要，但不阻断导出。
5. Excel 生成后再次传入 `--xlsx <运行目录>/testcases.xlsx` 更新公式检查结果。
6. 所有新生成用例的 `remark` 必须是空字符串。替换或合并已有 Excel 时，仅保留非目标模块原有备注。
7. 更新 `history-index.md`，输出文件路径、用例统计、审计摘要和 token 汇总。

具体 JSON 结构、校验顺序、导出命令和完成模板见 `references/testcase-creator/export-workflow.md`。

## 6. 资产沉淀（可选）

用户输入“沉淀”或“追加检查点/评审点”时可随时触发：

1. 询问沉淀检查点、评审点或两者。
2. 收集分类和描述，读取现有最大编号后递增分配。
3. 按编号前缀和描述关键词去重。
4. 追加到对应分类末尾，不覆盖、不重排既有编号，并记录日期和来源。
5. 输出追加内容预览。

## 文件约定

运行目录为 `.testcase-assets/history/<YYYYMMDD>_<HHMMSS>_<模块名>/`，其中：

| 文件 | 说明 |
|------|------|
| `0-用例准备.md` | 需求、设计和检查点结构化结果 |
| `1-评审记要.md` | 最终用例表，不含历轮评审记录 |
| `1-评审报告-第N轮.md` | 每轮独立评审报告 |
| `2-用例定稿.md` | 最终定稿用例表 |
| `export_data.json` | Excel/XMind 中间数据 |
| `audit-summary.md` | 内容质量与交付审计摘要 |
| `jira_export.csv` / `testcases.xlsx` / `testcases.xmind` | 对应导出文件 |
