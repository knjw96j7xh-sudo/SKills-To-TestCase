---
name: testcase-creator
description: 基于检查点/评审点资产，按标准五阶段流程生成测试用例，支持评审迭代与 OTP 导出
triggers:
  - /testcase-creator
---

# 用例生成 Skill — testcase-creator

> 先确认输入，不自动导入，不生成自动化测试代码；检查点和评审点可随项目经验持续沉淀。

---

## 0. 初始化检查（每次触发自动执行）

1. 检查 `.testcase-assets/checkpoints-index.md` 是否存在：
   - 存在 → 继续
   - 不存在 → 提示用户："检查点索引文件缺失，请先执行 `/checkpoint-init` 创建默认资产，或手动放入 `.testcase-assets/` 目录。"，**中止流程**。
2. 检查 `.testcase-assets/review-expectations-index.md` 是否存在，同上。
3. 读取 `.testcase-assets/project.config.md`（若存在），从中载入以下上下文，后续流程无需再次询问用户：
   - 项目名称、项目英文标识（用于文件命名）
   - 业务域列表（用于检查点分类匹配）
   - 常用导出路径（用于 OTP 导出提示）
   - OTP 字段映射配置（用于生成 JSON 时替换字段名）
   - 默认优先级规则、评审默认应用维度
4. 初始化通过后，输出：

```
[OK] 资产加载成功
[DIR] 检查点索引：.testcase-assets/checkpoints-index.md
[DIR] 评审点索引：.testcase-assets/review-expectations-index.md
[DIR] 项目配置：.testcase-assets/project.config.md（已载入上下文）
>> 开始用例生成流程，共 5 个阶段，每步需您确认后继续。
```

---

## 1. 需求输入（阶段 1/5）

**提示用户：**

```
【阶段 1 — 需求输入】
请提供需求来源（选择一种或多种）：
  A. 直接粘贴文字需求描述
  B. 乐享页面链接（我将读取内容）
  C. 接口文档链接或本地接口文档文件路径
  D. 本地技术方案文件路径（.md / .docx / .pdf）

请输入需求来源类型（A/B/C/D）并提供对应内容：
```

**收到输入后执行：**
- 若为 B/C/D 类型，读取对应链接或文件内容：
  - `.pdf`：`pdftotext '<路径>' -`（macOS/Linux/WSL）或 Windows 原生：`python3 -m pdfplumber --text '<路径>'`
  - `.docx`：`textutil -convert txt -stdout '<路径>'`（macOS）或 `python3 -c "import docx; d=docx.Document('<路径>'); print('\n'.join(p.text for p in d.paragraphs if p.text))"`（Windows，需 `pip install python-docx`）
  - `.md`：直接使用 Read 工具
- 提取并输出以下结构：

```markdown
##  需求解析结果（请确认）

- **测试对象**：[功能名称/模块]
- **业务规则**：
  1. [规则1]
  2. [规则2]
- **限制条件**：[如：仅限已登录用户、金额 ≥ 0.01 元]
- **接口/端点**：[如有]
- **涉及角色**：[如：普通用户、管理员]

[OK] 若以上解析正确，请回复「确认」继续阶段 2。
[FAIL] 若需修正，请指出错误内容后重新确认。
```

---

## 2. 输入结构化（阶段 2/5）

**触发条件**：用户确认阶段 1 结果后执行

**执行步骤：**

1. 读取 `.testcase-assets/checkpoints-index.md`，按分类展示所有检查点：

```
【阶段 2 — 检查点选择】
读取检查点索引，请选择适用于本次需求的检查点编号：

>> 业务域：用户中心
  [UC-01] 手机号格式校验（11位，1开头）
  [UC-02] 验证码发送间隔限制（60秒）

>> 业务域：支付
  [PAY-01] 金额精度校验（最多2位小数）
  [PAY-02] 重复提交拦截

>> 通用风险
  [RISK-01] 并发场景数据一致性
  [RISK-02] 网络中断后重试机制
  [RISK-03] 权限越界访问

[NOTE] 请输入检查点编号（多个用逗号分隔，如：UC-01,UC-02,RISK-01）
   也可输入「全选」应用当前需求域所有检查点，或「跳过」不关联检查点。
```

2. 收到选择后，生成结构化摘要并输出：

```markdown
##  输入结构化结果（0-用例准备）

### 需求要素
| 项目 | 内容 |
|------|------|
| 测试对象 | [xxx] |
| 业务规则 | [xxx] |
| 限制条件 | [xxx] |

### 已关联检查点
| 编号 | 描述 | 分类 |
|------|------|------|
| UC-01 | 手机号格式校验 | 用户中心 |
| RISK-01 | 并发场景数据一致性 | 通用风险 |

[OK] 结构化完成，请回复「生成用例」进入阶段 3。
```

3. 将上述内容写入 `.testcase-assets/history/0-用例准备_<timestamp>.md`

---

## 3. 用例生成（阶段 3/5）

**触发条件**：用户回复「生成用例」后执行

**执行步骤：**

1. 基于需求要素 + 已选检查点，拆分测试点（内部推理，无需展示）
2. 生成测试用例表：

```markdown
##  测试用例表（初稿）

| 用例ID | 测试点 | 前置条件 | 操作步骤 | 预期结果 | 关联检查点 | 场景类型 | 优先级 |
|--------|--------|----------|----------|----------|------------|----------|--------|
| TC-001 | 正常找回密码 | 用户已注册 | 1.输入手机号 2.获取验证码 3.输入新密码 | 密码修改成功，跳转登录页 | UC-01 | 正向 | P1 |
| TC-002 | 手机号格式错误 | 无 | 输入10位手机号点击发送 | 提示"请输入正确手机号" | UC-01 | 异常 | P0 |
| TC-003 | 验证码60秒内重发 | 已发送一次验证码 | 60秒内再次点击发送 | 按鈕置灰，倒计时展示 | UC-02 | 边界 | P1 |
| TC-004 | 并发提交密码重置 | 两个会话同时操作 | 同时提交两个重置请求 | 只有一个成功，另一个提示失效 | RISK-01 | 并发 | P2 |

> 共生成 X 条用例，覆盖正向 X / 异常 X / 边界 X / 并发 X 条

[OK] 请回复「进入评审」进入阶段 4，或直接告诉我需要修改的用例编号和修改内容。
```

3. 将用例表写入 `.testcase-assets/history/1-评审记要_<timestamp>.md`

---

## 4. 评审优化（阶段 4/5）

**触发条件**：用户回复「进入评审」后执行

**执行步骤：**

1. 读取 `.testcase-assets/review-expectations-index.md`，展示评审点列表：

```
【阶段 4 — 评审点选择】
读取评审点索引，请选择本次评审要重点关注的维度：

>> 用户体验
  [UX-01] 操作失败有明确错误提示
  [UX-02] 关键操作有二次确认弹窗

 数据一致性
  [DATA-01] 写操作后读取结果与预期一致
  [DATA-02] 跨模块数据联动正确性

[BUG] 历史易错点
  [BUG-01] 切换账号后缓存未清除
  [BUG-02] 弱网下接口超时无兜底提示

 完整性
  [COMP-01] 所有业务规则均有对应用例
  [COMP-02] 接口入参边界值已覆盖

[NOTE] 请输入评审点编号（多个用逗号分隔），或输入「全部」应用所有评审点：
```

2. 针对每个选中评审点，**逐条判断当前用例表的覆盖情况**，输出：

```markdown
##  独立视角评审报告

| 评审点 | 是否已覆盖 | 分析 | 建议补充用例 |
|--------|------------|------|--------------|
| UX-01 | [OK] 已覆盖 | TC-002 已验证错误提示 | — |
| BUG-01 | [FAIL] 未覆盖 | 无切换账号场景 | 补充TC-005：切换账号后验证缓存清除 |
| COMP-02 | [WARN] 部分覆盖 | 缺少空字符串、特殊字符边界 | 补充TC-006/007 |

###  建议补充用例

| 用例ID | 测试点 | 前置条件 | 操作步骤 | 预期结果 | 关联评审点 |
|--------|--------|----------|----------|----------|------------|
| TC-005 | 切换账号后缓存清除 | 账号A已登录并操作 | 切换到账号B | 账号A数据不显示 | BUG-01 |
```

3. 询问用户：

```
评审完成，发现 X 个未覆盖点，建议补充 X 条用例。

请选择操作：
  A. 接受所有补充建议（自动合并到用例表）
  B. 部分接受（请指定接受的用例编号）
  C. 手动修改（请直接告诉我修改内容）
  D. 忽略，当前版本已足够

[WARN] 评审是否通过？
  → 若选择 A/B/C 将生成优化稿，回到评审循环
  → 若选择 D 将进入阶段 5（定稿导入）
```

4. 若选 A/B/C：合并补充用例，重新输出完整用例表，并询问「是否再次评审？」（支持多轮迭代）
5. 评审通过后将最终用例表写入 `.testcase-assets/history/1-评审记要_<timestamp>.md`（追加评审记录）

---

## 5. 定稿导入（阶段 5/5）

**触发条件**：用户确认评审通过后执行

**执行步骤：**

1. 输出最终定稿用例表（完整版），写入 `.testcase-assets/history/2-用例定稿_<timestamp>.md`

2. 询问是否导入 OTP：

```
【阶段 5 — 定稿导入】
[OK] 用例定稿已保存至 2-用例定稿_<timestamp>.md

是否需要生成 OTP 导入文件？
  Y. 是，生成 OTP 树形 JSON（结构参考 .testcase-assets/templates/otp-schema.json）
  N. 否，本次到此结束
```

3. **若选 Y**：
   - 从 `project.config.md` 中读取项目名称、模块名称（无需再次询问用户）
   - 检查 `project.config.md` 中『OTP 字段映射配置』是否全部勾选 [x]：
     - 未全部勾选 → 提示："[WARN] OTP 字段映射尚未完成对齐，导入可能失败。建议先在 project.config.md 中确认所有字段，再生成 JSON。是否付继续？(Y/N)"
     - 已全部勾选 → 直接生成
   - 按 `project.config.md` 中的字段映射表替换 JSON 中的字段名
   - 生成 OTP JSON 文件，命名为 `otp_export_<英文标识>_<timestamp>.json`
   - 输出文件路径并展示 JSON 内容预览（前20行）
   - 提示：`[EXPORT] 建议先用 1~2 条用例测试导入是否成功，确认无误后再批量导入。`

4. 询问额外格式导出：

```
[格式导出]
是否需要导出 Excel 或 XMind 格式？（可多选，逗号分隔）
  E. 导出 Excel (.xlsx)   — 带颜色分类、冻结表头、场景统计
  X. 导出 XMind (.xmind) — 按检查点分组的思维导图
  N. 不需要，结束
```

**若选 E 或 X**，执行以下步骤：

**步骤 A — 序列化用例数据**：将最终用例写入 `.testcase-assets/history/export_data_<timestamp>.json`，格式：

```json
{
  "meta": {
    "project": "<从 project.config.md 读取项目名称>",
    "module": "<本次测试模块名>",
    "generated_at": "<YYYY-MM-DD>"
  },
  "testcases": [
    {
      "id": "TC-001",
      "test_point": "测试点",
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
    .testcase-assets/history/export_data_<timestamp>.json \
    .testcase-assets/history/testcases_<timestamp>.xlsx
  ```
- 若选 **X**（XMind）：
  ```bash
  python3 .testcase-assets/scripts/export_xmind.py \
    .testcase-assets/history/export_data_<timestamp>.json \
    .testcase-assets/history/testcases_<timestamp>.xmind
  ```

**步骤 C — 确认输出**：
```
[OK] 文件已生成：
  Excel → .testcase-assets/history/testcases_<timestamp>.xlsx
  XMind → .testcase-assets/history/testcases_<timestamp>.xmind
[TIP] XMind 文件需 XMind 8 或更高版本打开。
```

4. **若选 N**：
   - 输出总结摘要后结束

**流程结束输出：**

```markdown
##  本次用例生成完成

| 项目 | 详情 |
|------|------|
| 测试对象 | [xxx] |
| 用例总数 | X 条（正向X / 异常X / 边界X / 并发X） |
| 关联检查点 | X 个 |
| 评审轮次 | X 轮 |
| 定稿文件（MD） | .testcase-assets/history/2-用例定稿_xxx.md |
| 定稿文件（Excel） | .testcase-assets/history/testcases_xxx.xlsx（如已生成） |
| 定稿文件（XMind） | .testcase-assets/history/testcases_xxx.xmind（如已生成） |
| OTP 导出 | otp_export_xxx.json（如已生成） |

---
[TIP] 是否有新的检查点或评审点需要沉淀？请参见下方《资产沉淀》说明。
```

---

## 6. 资产沉淀（可选，贯穿全程）

> 本阶段可在任意时刻触发，不必等到流程结束。

**触发方式**：用户输入「沉淀」或「追加检查点/评审点」

**执行步骤：**

1. 询问沉淀类型：

```
请选择沉淀类型：
  A. 新检查点（来源：评审问题 / 用户补充 / 导入问题 / 漏测风险）
  B. 新评审点
  C. 两者都有
```

2. 收集信息：

```
请提供新检查点信息（可多条，每行一条）：
格式：[分类] [描述]
例：通用风险 登录态过期后操作无提示
```

3. 自动分配编号（读取现有最大编号 + 1），去重检查（基于编号前缀和描述关键词）

4. **追加写入**对应索引文件（追加到对应分类末尾，不覆盖）：

```markdown
- [RISK-04] 登录态过期后操作无提示  <!-- 新增于 2026-06-01，来源：漏测风险 -->
```

5. 确认追加成功，输出追加内容预览。

---

## [REF] 附：文件命名规范

| 文件 | 命名格式 | 示例 |
|------|----------|------|
| 用例准备 | `0-用例准备_YYYYMMDD_HHMMSS.md` | `0-用例准备_20260601_143000.md` |
| 评审记要 | `1-评审记要_YYYYMMDD_HHMMSS.md` | `1-评审记要_20260601_150000.md` |
| 用例定稿 | `2-用例定稿_YYYYMMDD_HHMMSS.md` | `2-用例定稿_20260601_160000.md` |
| OTP导出 | `otp_export_YYYYMMDD_HHMMSS.json` | `otp_export_20260601_160000.json` |
