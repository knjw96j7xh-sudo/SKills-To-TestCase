---
description: 基于检查点/评审点资产，按标准五阶段流程生成测试用例，支持评审迭代与多格式导出
---

# 用例生成 Skill — testcase-creator

> **核心原则**：先确认输入，不自动导入，不生成自动化测试代码；检查点和评审点可随项目经验持续沉淀。

---

## 0. 初始化检查（每次触发自动执行）

请执行以下检查：

1. 读取 `.testcase-assets/checkpoints-index.md`，若文件不存在则提示用户创建并**中止流程**。
2. 读取 `.testcase-assets/review-expectations-index.md`，若文件不存在则提示用户创建并**中止流程**。
3. 读取 `.testcase-assets/project.config.md`（若存在），从中载入以下上下文，后续流程无需再次询问：
   - 项目名称、项目英文标识（用于文件命名）
   - 业务域列表（用于检查点分类匹配）
   - 默认优先级规则、评审默认应用维度
4. **配置校验（强制阻断）**：检查 `project.config.md` 是否包含 `[填写` 开头的占位符。若检测到任何占位符，**直接中止流程**，输出：
   ```
   [BLOCK] project.config.md 中存在未填写的占位符，无法继续：
     - [填写项目中文名] → 请替换为实际项目名称
     - [填写英文缩写] → 请替换为实际英文标识
     - [填写姓名] → 请替换为测试负责人姓名
     - [填写团队共享路径] → 请替换为实际共享路径
   请先完善配置，再重新触发 /testcase-creator。
   ```
   **不提供「是否继续」选项，必须填写完整后才能进入阶段 1。**
5. 初始化通过后输出：

```
[OK] 资产加载成功
[DIR] 检查点索引：.testcase-assets/checkpoints-index.md
[DIR] 评审点索引：.testcase-assets/review-expectations-index.md
[DIR] 项目配置：.testcase-assets/project.config.md（已载入上下文）
>> 开始用例生成流程，共 5 个阶段，每步需您确认后继续。
```

> **历史记录管理**：本次运行的所有文件将归入独立子目录 `.testcase-assets/history/<YYYYMMDD>_<HHMMSS>_<模块名>/`，并在 `history-index.md` 中追加索引记录。

---

## 1. 需求输入（阶段 1/5）

提示用户选择需求来源：

```
【阶段 1 — 需求输入】
请提供需求来源（选择一种或多种）：
  A. 直接粘贴文字需求描述
  B. 乐享页面链接
  C. 接口文档链接或本地文件路径
  D. 本地技术方案文件路径（.md / .docx / .pdf）
  E. 图片/截图（.png / .jpg / .jpeg / .gif / .webp）
  F. 飞书文档链接
  G. Excel 需求列表（.xlsx / .xls）
  H. 需求管理工具链接（Jira / Tapd / 禅道）

请输入类型（A-H）并提供对应内容：
```

**文件读取规则**（按文件扩展名执行）：

- `.pdf` 文件：**必须**使用 Bash 命令 `pdftotext '<文件路径>' -` 读取文本内容，**不得**直接用文件读取工具打开 PDF，以避免模型路由错误。
- `.md` 文件：使用 `Read` 工具直接读取。
- `.docx` 文件（按操作系统选择）：
  - **macOS**：使用 Bash 命令 `textutil -convert txt -stdout '<文件路径>'`
  - **Windows**：使用 Bash 命令 `python3 -c "import docx; d=docx.Document('<文件路径>'); print('\n'.join(p.text for p in d.paragraphs if p.text))"`（需先 `pip install python-docx`）
  - 若不确定系统，优先尝试 macOS 方式，失败则切换 Windows 方式
- `.xlsx` / `.xls` 文件：使用 Bash 命令 `python3 -c "import openpyxl; wb=openpyxl.load_workbook('<文件路径>'); [print('\t'.join(str(c.value or '') for c in row)) for ws in wb.worksheets for row in ws.iter_rows()]"`（需先 `pip install openpyxl`）
- `.png` / `.jpg` / `.jpeg` / `.gif` / `.webp` 图片：使用 `Read` 工具直接读取，模型将自动识别图片中的需求内容（UI 设计稿、原型图、流程图等）。
- 飞书文档链接（`feishu.cn` / `larksuite.com`）：使用 `WebFetch` 工具读取页面内容。
- 需求管理工具链接（Jira / Tapd / 禅道）：使用 `WebFetch` 工具读取页面内容；若为 API 链接可使用 `Bash` + `curl` 获取。

收到输入后，读取内容并提取需求要素，输出确认清单：

```markdown
##  需求解析结果（请确认）

- **测试对象**：[功能名称/模块]
- **业务规则**：
  1. [规则1]
  2. [规则2]
- **限制条件**：[如：仅限已登录用户、金额 ≥ 0.01 元]
- **接口/端点**：[如有]
- **涉及角色**：[如：普通用户、管理员]

[OK] 若解析正确，请回复「确认」继续阶段 2。
[FAIL] 若需修正，请指出错误内容。
```

**用户确认后**，执行以下操作：
1. 提取「测试对象」作为模块名（取简短关键词，如"碳盘查清单"、"用户中心"）
2. **模块名清理**：移除文件系统不允许的字符（`/ \ : * ? " < > |`），替换为空格或下划线
3. 创建本次运行的子目录：`.testcase-assets/history/<YYYYMMDD>_<HHMMSS>_<模块名>/`
4. 后续所有文件均写入此子目录

---

## 2. 输入结构化（阶段 2/5）

**触发条件**：用户确认阶段 1 后执行

1. 读取 `.testcase-assets/checkpoints-index.md`，**完整展示所有分类和检查点**，格式如下：

```
【阶段 2 — 检查点选择】
请选择适用于本次需求的检查点编号（多个用逗号分隔）：

>> 业务域：[域名]
  [XX-01] 描述...
  [XX-02] 描述...

>> 通用风险
  [RISK-01] 描述...

[NOTE] 输入编号（如：UC-01,RISK-02），或输入「全选」/「跳过」
```

2. 收到选择后，生成结构化摘要并写入 `.testcase-assets/history/<运行目录>/0-用例准备.md`：

```markdown
##  输入结构化结果（0-用例准备）

### 需求要素
| 项目 | 内容 |
|------|------|
| 测试对象 | ... |
| 业务规则 | ... |
| 限制条件 | ... |

### 已关联检查点
| 编号 | 描述 | 分类 |
|------|------|------|
| ... | ... | ... |

[OK] 结构化完成，请回复「生成用例」进入阶段 3。
```

---

## 3. 用例生成（阶段 3/5）

**触发条件**：用户回复「生成用例」后执行

基于需求要素 + 已选检查点，按正向/异常/边界/并发四类拆分测试点，生成用例表：

> **优先级赋值规则**（与 project.config.md 保持一致）：
> - P0：异常场景（直接影响核心流程的阻断性错误）
> - P1：正向主流程 / 边界场景
> - P2：并发场景 / 低频边界
> - P3：体验类、兼容性等非核心场景

```markdown
##  测试用例表（初稿）

| 用例ID | 测试点 | 前置条件 | 操作步骤 | 预期结果 | 关联检查点 | 场景类型 | 优先级 |
|--------|--------|----------|----------|----------|------------|----------|--------|
| TC-001 | ... | ... | 1. ... 2. ... | ... | XX-01 | 正向 | P1 |
| TC-002 | ... | ... | 1. ... | ... | XX-01 | 异常 | P0 |
| TC-003 | ... | ... | 1. ... | ... | RISK-01 | 边界 | P1 |

> 共生成 X 条用例：正向 X 条 / 异常 X 条 / 边界 X 条 / 并发 X 条

[OK] 请回复「进入评审」进入阶段 4，或告诉我需要修改的用例编号和内容。
```

将用例表写入 `.testcase-assets/history/<运行目录>/1-评审记要.md`。

---

## 4. 评审优化（阶段 4/5）

**触发条件**：用户回复「进入评审」后执行

1. 读取 `.testcase-assets/review-expectations-index.md`，**完整展示所有评审点**：

```
【阶段 4 — 评审点选择】
请选择本次评审要重点关注的维度：

>> [分类]
  [XX-01] 描述...

[NOTE] 输入评审点编号（多个用逗号分隔），或输入「全部」应用所有评审点：
```

2. **双人独立评审（2 个 subagent 并行）**：

   用户选择评审维度后，**同时启动 2 个隔离上下文的 subagent** 执行独立评审，模拟「两个人分别审」的效果：
   - 每个 subagent 独立接收：需求要素摘要 + 用例表 + 已选评审点列表
   - 两个 subagent 互不可见，各自以独立评审人视角逐条判断覆盖情况
   - 主 agent 等待两个 subagent 完成后，合并两份评审报告

   > **为什么要用 2 个 subagent**：同一上下文生成的用例再自己审，容易有确认偏误。2 个隔离 subagent 提供两个独立视角，交叉验证可提高发现问题的可信度。

   **subagent prompt 模板**（两个 subagent 使用相同 prompt）：

   ```
   你是一名独立测试评审专家，未参与用例设计。
   请基于以下需求和评审点，对用例表进行逐条审查。

   ## 需求要素
   [粘贴需求摘要]

   ## 评审维度
   [粘贴已选评审点编号和描述]

   ## 待评审用例表
   [粘贴用例表]

   请输出：
   1. 评审报告表格（评审点 / 是否已覆盖 / 分析说明 / 建议补充用例）
   2. 建议补充用例表（如有）
   3. 整体评审结论
   ```

3. **合并评审结果**：

   主 agent 将两份评审报告按以下规则合并：

   | 两人共识 | 处理方式 |
   |----------|----------|
   | 两人均标记 [FAIL] | 直接采纳，标记为「共识-未覆盖」 |
   | 两人均标记 [OK] | 直接采纳，标记为「共识-已覆盖」 |
   | 一人 [FAIL] 一人 [OK] | 标记为「待确认」，展示双方观点供用户判断 |
   | 一人 [FAIL] 一人 [WARN] | 采纳补充建议，标记为「待确认」 |

   合并后写入 `.testcase-assets/history/<运行目录>/1-评审记要.md`，包含：
   - 评审员 A 报告
   - 评审员 B 报告
   - 合并结论（共识项 + 待确认项）

4. 主 agent 展示合并后的评审报告，询问用户操作选项：
   - **A**：接受所有补充建议 → 合并后重新输出完整用例表，可再次评审（支持多轮）
   - **B**：部分接受（指定编号） → 同上
   - **C**：手动修改 → 同上
   - **D**：忽略，进入阶段 5

4. 评审通过后将最终用例表追加记录到 `<运行目录>/1-评审记要.md`。

---

## 5. 定稿导入（阶段 5/5）

**触发条件**：用户确认评审通过后执行

1. 输出完整最终用例表，写入 `.testcase-assets/history/<运行目录>/2-用例定稿.md`

2. 询问导出平台（可多选，逗号分隔）：

```
【阶段 5 — 定稿导出】
[OK] 用例定稿已保存。

请选择导出平台（可多选，逗号分隔）：
  J. Jira CSV（.csv，可直接导入 Jira）
  E. Excel（.xlsx 表格，带颜色分类、冻结表头）
  X. XMind（思维导图，用于用例展示和评审）
  N. 不需要导出，本次到此结束
```

3. **按所选平台分别执行导出**：

### 3a. Jira CSV 导出（若选 J）

- 按 `.testcase-assets/templates/csv-schema.json` 的字段映射规则生成 CSV
- 输出文件 `<运行目录>/jira_export.csv`
- 编码：UTF-8 with BOM（确保 Jira 导入时中文不乱码）
- 多步骤用例处理规则：首行填写 序号/标题/描述/优先级/需求/测试用例集，后续步骤行仅填写 步骤ID/步骤/测试数据/期望结果
- 优先级映射：P0→High, P1→Medium, P2→Low, P3→Low
- 提示：`[EXPORT] Jira CSV 已生成，请手动导入 Jira 系统。`

### 3b. Excel / XMind 导出（若选 E 或 X）

**步骤 A — 序列化用例数据**：将最终用例以如下 JSON 格式写入中间文件 `.testcase-assets/history/<运行目录>/export_data.json`：

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

> **格式说明**：
> - `steps`：换行分隔的字符串（`"1. 步骤一\n2. 步骤二"`），供 Excel/XMind 脚本按 `\n` 拆分各步骤。
> - `priority`：从用例表「优先级」列直接取值（P0/P1/P2/P3）。
> - `type` 字段值必须为以下之一：`正向` / `异常` / `边界` / `并发`。

**步骤 B — 调用导出脚本**（按所选格式分别执行）：

- 若选 **E**（Excel）：
  ```bash
  python3 .testcase-assets/scripts/export_excel.py \
    .testcase-assets/history/<运行目录>/export_data.json \
    .testcase-assets/history/<运行目录>/testcases.xlsx
  ```

- 若选 **X**（XMind）：
  ```bash
  python3 .testcase-assets/scripts/export_xmind.py \
    .testcase-assets/history/<运行目录>/export_data.json \
    .testcase-assets/history/<运行目录>/testcases.xmind
  ```

**步骤 C — 确认输出**：脚本执行后，输出文件路径并提示用户：
```
[OK] 文件已生成：
  Excel → .testcase-assets/history/<运行目录>/testcases.xlsx
  XMind → .testcase-assets/history/<运行目录>/testcases.xmind
[TIP] XMind 文件需 XMind 8 或更高版本打开。
```

4. **更新历史索引**：将本次运行记录追加到 `.testcase-assets/history/history-index.md`：

```markdown
| <YYYY-MM-DD HH:mm> | <模块名> | <用例数> 条 | <运行目录>/2-用例定稿.md | <已生成的导出文件列表> |
```

5. **流程结束，输出总结**：

```markdown
##  本次用例生成完成

| 项目 | 详情 |
|------|------|
| 测试对象 | ... |
| 用例总数 | X 条（正向X / 异常X / 边界X / 并发X） |
| 关联检查点 | X 个 |
| 评审轮次 | X 轮 |
| 运行目录 | .testcase-assets/history/<运行目录>/ |
| 定稿文件 | 2-用例定稿.md |
| Jira 导出 | jira_export.csv（如已生成） |
| Excel 导出 | testcases.xlsx（如已生成） |
| XMind 导出 | testcases.xmind（如已生成） |

[TIP] 是否有新的检查点或评审点需要沉淀？回复「沉淀」继续。
[TOKEN] 本次会话结束时，请留意终端底部的 token 消耗统计。
```

---

## 6. 资产沉淀（可在任意阶段触发）

**触发方式**：用户输入「沉淀」

1. 询问沉淀类型：新检查点 / 新评审点 / 两者都有
2. 收集信息，格式：`[分类] [描述]`（每行一条）
3. 自动分配编号（读取现有最大编号 + 1），进行去重检查（基于编号前缀和描述关键词）
4. 追加写入对应索引文件（不覆盖原有内容），格式：

```markdown
- [XX-XX] 描述内容  <!-- 新增于 YYYY-MM-DD，来源：[评审问题/用户补充/导入问题/漏测风险] -->
```

5. 输出追加内容预览，确认完成。
