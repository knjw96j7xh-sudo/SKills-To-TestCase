# 用例生成 Skill — testcase-creator

> 先确认输入，不自动导入，不生成自动化测试代码；检查点和评审点可随项目经验持续沉淀。

## Reference 路由

按阶段读取以下文件，不要一次性加载全部 reference：

- 选择「全量新建」并进入阶段 1 前，完整读取 `references/testcase-creator/input-and-generation.md`。
- 选择「增量变更」后，完整读取 `references/testcase-creator/change-workflow.md`。
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

5. **框架版本体检**（不阻断占位符检查之后的流程选择，但版本落后须先提示）：

```bash
python3 .testcase-assets/scripts/check_framework_version.py --strict
```

- 退出码 0：版本一致，继续。
- 退出码非 0：向用户展示脚本输出，并提示在 Skills 仓库执行  
  `./init-testcase.sh <项目名> <本项目路径> --sync`  
  （本仓库 `projects/*` 可用 `python3 check_project_copies.py --fix` 或 `./sync-projects.sh`）。  
  **版本落后时不得继续生成/导出**（避免旧脚本缺 `md_to_json` / `export_all` 等能力）。用户完成 sync 后重新触发本 Skill。

6. 初始化通过后输出资产加载成功信息，并询问运行模式：
```text
【运行模式】
A. 全量新建（完整五阶段）
B. 增量变更（基于历史定稿做补/改/废）
```

用户也可自然语言直达，例如「增量改…」→ 模式 B。  
模式 B：完整读取并执行 `references/testcase-creator/change-workflow.md`，完成后进入阶段 4 或 5。  
模式 A：继续下方阶段 1–5。

Token 统计：能读到终端累计值时各阶段可记录；读不到则跳过，不阻断流程。

## 1. 需求与设计输入（阶段 1/5）— 全量模式

进入本阶段前完整读取 `references/testcase-creator/input-and-generation.md` 的“阶段 1”。

1. 提示用户选择 A-H 的需求来源，可组合提供文字需求和设计稿导出文件。
2. 读取文件或链接，保留多来源归属。设计稿 PDF 必须同时检查文本和渲染页面。
3. 输出需求要素、设计要素及两者差异，等待用户明确回复“确认”。
4. 确认后清理模块名中的文件系统非法字符，创建：
   `.testcase-assets/history/<YYYYMMDD>_<HHMMSS>_<模块名>/`。
5. 后续文件全部写入该运行目录。

不得用设计稿覆盖文字需求；发现冲突时必须列为待确认项。

## 2. 输入结构化（阶段 2/5）— 全量模式

触发条件：用户确认阶段 1 解析结果。细则见 `input-and-generation.md` 阶段 2（含 2a 检查点推荐、2b 历史复用）。

1. **2a 检查点**：展示索引全部分类，并给出推荐预勾；接受编号列表、「采用推荐」、「全选」或「跳过」。不得静默替用户选定。
2. **2b 历史复用（可选）**：扫描近期 history 定稿，列出候选供勾选，或「跳过」。不得未经勾选整表复制历史。增量模式不做 2b。
3. 生成需求要素、设计要素、差异项、已关联检查点、复用映射摘要。
4. 写入 `<运行目录>/0-用例准备.md`。
5. 等待用户回复“生成用例”。

## 3. 用例生成（阶段 3/5）— 全量模式

触发条件：用户回复“生成用例”。进入本阶段时读取 `references/testcase-creator/input-and-generation.md` 的“阶段 3”。

1. 读取 `.testcase-assets/templates/testcase-table-config.json`；缺失时使用默认 9 列。
2. 仅在用户主动要求时加入可选列。
3. 若阶段 2 勾选了历史复用：本轮统一重新编号，映射写入准备文档；只为未覆盖规则/检查点/场景补新用例。
4. 基于需求、设计、差异结论和检查点生成正向、异常、边界、并发用例。
5. 单模块需求的“所属模块”统一填写测试对象，多模块需求填写对应子模块。
6. 写入 `<运行目录>/1-评审记要.md`，等待用户进入评审或提出修改。

**备注列强制规则**：生成用例的“备注”必须为空。不得写入来源 ID、历史备注、评审结论、检查点说明、复用映射或追踪信息；过程信息写入准备文档、评审报告或审计摘要。

## 4. 评审优化（阶段 4/5）

触发条件：用户回复“进入评审”（全量或增量均可）。进入本阶段前完整读取 `references/testcase-creator/review-workflow.md`。

1. 展示评审点并按 UX、DATA、COMP、EXEC、BUG、SEC、PERF 等分类分组。
2. 第 1 轮全量评审；第 2 轮起仅展开新增或修改用例，已有用例只提供摘要。
3. 每个选中维度优先使用独立 subagent 并行评审；环境不支持并行时，在同一会话内按维度**串行**评审，输出格式不变。
4. 每个维度只接收该维度评审点，不混入其他维度。
5. 合并覆盖结论、去重补充建议，分别写入：
   - `<运行目录>/1-评审报告-第N轮.md`
   - `<运行目录>/1-评审记要.md`（只保留最终用例表）
6. 用户选择 A/B/C/D 时合并修改并进入下一轮增量评审；选择 E 时进入阶段 5。

不得跳过用户决策或把历轮评审内容混入最终用例表。

## 5. 定稿导出（阶段 5/5）

触发条件：用户确认评审通过，或增量模式选择跳过评审。进入本阶段前完整读取 `references/testcase-creator/export-workflow.md`。

1. 写入 `<运行目录>/2-用例定稿.md`（增量须含变更摘要）。
2. 询问导出平台：Jira CSV、Excel、XMind 或不导出。
3. 导出前必须运行内容质量检查，并生成 `<运行目录>/audit-summary.md`。
4. Excel/XMind 必须先用 `md_to_json.py` 从定稿生成 `export_data.json`，禁止 Agent 手写整份 JSON。
5. 质检失败时修复用例数据并重新运行，直到通过；警告项必须写入审计摘要，但不阻断导出。
6. Excel 生成后再次传入 `--xlsx` 更新公式检查结果。
7. 所有新生成用例的 `remark` 必须是空字符串。替换或合并已有 Excel 时，仅保留非目标模块原有备注。
8. 更新 `history-index.md`，输出文件路径、用例统计、审计摘要；token 能汇总则汇总。

## 6. 资产沉淀（可选）

用户输入“沉淀”或“追加检查点/评审点”时可随时触发：

1. 询问沉淀检查点、评审点或两者。
2. 收集分类和描述，读取现有最大编号后递增分配。
3. 按编号前缀和描述关键词去重。
4. 追加到对应分类末尾，不覆盖、不重排既有编号，并记录日期和来源。
5. 输出追加内容预览；**须用户确认后才写入 index**。

### 从缺陷列表结构化沉淀

用户提供缺陷列表（粘贴或文件）时：

```bash
python3 .testcase-assets/scripts/suggest_assets_from_bugs.py <缺陷文件> \
  --kind review|checkpoint|both \
  --checkpoints-index .testcase-assets/checkpoints-index.md \
  --review-index .testcase-assets/review-expectations-index.md \
  --output <运行目录或临时>/缺陷沉淀候选.md
```

1. 向用户展示候选表（编号 / 描述 / 来源）。
2. 用户确认或改编号/分类后，再追加到对应 index。
3. **禁止**脚本或 Agent 在未确认时自动改写 index。

## 文件约定

运行目录为 `.testcase-assets/history/<YYYYMMDD>_<HHMMSS>_<模块名>/`，其中：

| 文件 | 说明 |
|------|------|
| `0-用例准备.md` | 全量：需求、设计、检查点、复用映射 |
| `0-变更分析.md` | 增量：变更影响分析 |
| `1-变更集.md` | 增量：新增/修改/废弃表 |
| `1-评审记要.md` | 最终用例表，不含历轮评审记录 |
| `1-评审报告-第N轮.md` | 每轮独立评审报告 |
| `2-用例定稿.md` | 最终定稿用例表 |
| `export_data.json` | 由 `md_to_json.py` 从定稿生成 |
| `audit-summary.md` | 内容质量与交付审计摘要 |
| `jira_export.csv` / `testcases.xlsx` / `testcases.xmind` | 对应导出文件 |
