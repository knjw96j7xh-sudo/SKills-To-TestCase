# testcase-creator · 项目级测试用例生成方案

> **先确认输入，不自动导入，不生成自动化测试代码；检查点和评审点可随项目经验持续沉淀。**

---

## 目录结构

```
.
├── .cursor/
│   └── skills/
│       └── testcase-creator/
│           └── skill.md              # Cursor 触发词：/testcase-creator
│
├── .claude/
│   ├── commands/
│   │   └── testcase-creator.md       # Claude Code 触发词：/testcase-creator
│   └── settings.local.json           # Bash 权限白名单（pdftotext / 导出脚本）
│
├── .testcase-assets/                  # 项目级可复用资产（建议 Git 管理）
│   ├── project.config.md             # 项目配置（首次使用前必填）
│   ├── checkpoints-index.md          # 检查点索引（UC / PAY / LIST / FILE / RISK / API / CARB / APPR）
│   ├── review-expectations-index.md  # 评审点索引（UX / DATA / COMP / EXEC / BUG / SEC / PERF）
│   ├── templates/
│   │   ├── testcase-table.md         # 用例表输出模板
│   │   └── otp-schema.json           # OTP 树形 JSON 结构示例
│   ├── scripts/
│   │   ├── export_excel.py           # 用例导出为 Excel（需 Python + openpyxl）
│   │   └── export_xmind.py           # 用例导出为 XMind（需 Python，无额外依赖）
│   └── history/                      # 每次生成的历史记录（自动写入）
│       ├── 0-用例准备_xxx.md
│       ├── 1-评审记要_xxx.md
│       ├── 2-用例定稿_xxx.md
│       ├── export_data_xxx.json      # Excel/XMind 中间数据
│       ├── testcases_xxx.xlsx
│       ├── testcases_xxx.xmind
│       └── otp_export_xxx.json
│
├── TESTCASE_GUIDE.md                 # 纯对话工具（ChatGPT 等）使用指南
├── init-testcase.sh                  # 一键初始化脚本，将资产复制到目标项目
└── README.md                         # 本文件
```

---

## 环境依赖

| 工具 | 用途 | macOS | Windows |
|------|------|-------|---------|
| Python 3.x | 运行导出脚本 | 系统自带 | [python.org](https://python.org) 或 `winget install Python.Python.3` |
| openpyxl | Excel 导出 | `pip3 install openpyxl` | `pip install openpyxl` |
| pdftotext | 读取 PDF | `brew install poppler` | `winget install poppler`（或 WSL: `apt install poppler-utils` |
| python-docx | 读取 .docx | 不需要（系统自带 textutil） | `pip install python-docx` |
| XMind 8+ | 打开 .xmind | [xmind.app](https://xmind.app) | [xmind.app](https://xmind.app) |

> **Windows 用户注意**：建议在 WSL（Windows Subsystem for Linux）中运行 Claude Code，这样 bash 命令和 Linux 路径均可直接使用，体验与 macOS 一致。Cursor 原生支持 Windows，无需额外配置。

> XMind 导出无需安装任何额外 Python 包，直接运行即可。

---

## 五阶段流程概览

```
1. 需求输入  →  2. 输入结构化  →  3. 用例生成  →  4. 评审优化  →  5. 定稿导入
   用户确认        选择检查点       生成用例表      多轮迭代       OTP / Excel / XMind
   支持 PDF/MD     写入0-用例准备   含优先级列      关联评审点     写入history目录
```

### 1. 需求输入
支持四种来源：
- **A** 直接粘贴文字描述
- **B** 乐享页面链接
- **C** 接口文档链接或本地路径
- **D** 本地文件（`.md` / `.docx` / `.pdf`）

提取测试对象、业务规则、限制条件，输出确认清单。

### 2. 输入结构化
读取 `checkpoints-index.md`，展示所有分类和检查点，用户选择关联编号，生成结构化摘要写入 `0-用例准备` 文件。

### 3. 用例生成
基于需求要素 + 检查点，生成覆盖正向/异常/边界/并发四类的用例表，包含「优先级」列（P0–P3），写入 `1-评审记要` 文件。

> 优先级规则：P0=异常场景（阻断性错误）/ P1=正向主流程/边界 / P2=并发 / P3=体验类

### 4. 评审优化
读取 `review-expectations-index.md`，用户选择评审维度，AI 独立视角逐条判断覆盖情况，输出评审报告和补充建议，支持多轮迭代。

### 5. 定稿导入
写入 `2-用例定稿` 文件，然后依次询问：

1. **OTP 导出**（可选）：生成 `otp_export_xxx.json`，手动导入 OTP 系统
2. **格式导出**（可选，可多选）：
   - `E` → Excel (`.xlsx`)：带场景颜色、冻结表头、优先级、执行状态、统计 Sheet
   - `X` → XMind (`.xmind`)：四级结构（检查点 → 场景类型 → 用例 → 步骤），含统计总览 Sheet

---

## 快速上手

### 方式一：clone 本仓库后初始化到你的项目

```bash
# macOS / Linux
bash init-testcase.sh /path/to/your-project
```

```powershell
# Windows PowerShell
.\init-testcase.ps1 -TargetDir C:\path\to\your-project

# 若遇到执行策略限制，先运行：
# Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

> 脚本会自动完成：
> - 复制所有资产文件（skill.md / commands / checkpoints / scripts 等）
> - 根据当前用户名动态生成 .claude/settings.local.json（Windows 会自动检测 WSL）
> - 在目标项目的 .gitignore 追加 history/ 规则

# 5. 必填：编辑项目配置
vim /path/to/your-project/.testcase-assets/project.config.md

> **注意**：`.claude/settings.local.json` 包含本机路径，不会进入 git。
> 每个开发者在自己机器上运行 `init-testcase.sh` 时会自动生成对应版本。

---

### 方式二：在本仓库直接使用（不复制到其他项目）

```bash
# 第一次使用前，手动生成本机的 settings.local.json
bash init-testcase.sh .   # 用 . 表示当前目录（本仓库本身）

# 或直接手动创建（把 YOUR_USERNAME 替换成你的 macOS 用户名）
# .claude/settings.local.json 已在 .gitignore 中，放心写
```

### Cursor 用户
1. 完成上述初始化
2. 在 Cursor 中输入 `/testcase-creator` 触发流程
3. 按提示逐步确认

### Claude Code 用户
1. 完成上述初始化，确认 `.claude/settings.local.json` 中的权限白名单路径与本机一致
2. 在 Claude Code 中输入 `/testcase-creator` 触发流程
3. 选择需求来源 D（PDF）时，工具会自动使用 `pdftotext` 读取内容

### 纯对话工具（ChatGPT / Copilot 等）
1. 打开 `TESTCASE_GUIDE.md`，将全文复制
2. 同时复制以下文件内容，一并粘贴到对话开头：
   - `project.config.md`
   - `checkpoints-index.md`
   - `review-expectations-index.md`
3. 按流程交互，手动保存输出内容
4. 若需 Excel/XMind 导出，将 AI 输出的 `export_data.json` 保存到本地，手动运行导出脚本

---

## 导出格式说明

### Excel（export_excel.py）

| 特性 | 说明 |
|------|------|
| 列 | 用例ID / 测试点 / 前置条件 / 操作步骤 / 预期结果 / 关联检查点 / 场景类型 / 优先级 / 执行状态 / 编写人 / 执行人 / 备注 |
| 场景分组 | 每组首行加彩色粗边框分隔（正向/异常/边界/并发各自一色） |
| 场景类型列 | 深色徽章样式（绿/红/橙/蓝）|
| 优先级列 | P0–P3 自动着色 |
| 筛选/冻结 | 列名行筛选器 + 前两行冻结 |
| 统计 Sheet | 各场景类型用例数 + 柱状图 |
| 打印 | A4 横向，自动缩放，每页重复表头 |

### XMind（export_xmind.py）

| 特性 | 说明 |
|------|------|
| 结构 | 四级：根节点 → 检查点 → 场景类型 → 用例 → 步骤细节 |
| 步骤 | 每步独立子节点，操作步骤作为父节点折叠 |
| 优先级 | 显示为用例节点的标签（P0/P1/P2） |
| Sheet 2 | 统计总览：场景类型 → 各检查点覆盖条数 |
| 兼容性 | XMind 8 或更高版本 |

```bash
# 手动运行导出（Claude Code 会自动调用）
python3 .testcase-assets/scripts/export_excel.py <input.json> <output.xlsx>
python3 .testcase-assets/scripts/export_xmind.py <input.json> <output.xmind>
```

---

## 资产管理规范

| 操作 | 规范 |
|------|------|
| 新增检查点 | 追加到对应分类末尾，编号递增，不修改已有编号 |
| 废弃检查点 | 描述后追加 `[已废弃]`，不删除行 |
| 新增评审点 | 同上 |
| 历史文件 | `.testcase-assets/history/` 下只新增，不删除，时间戳区分 |
| Git 提交 | 更新索引文件后单独提交，格式：`chore: 沉淀检查点 XX-XX` |
| history/ 目录 | 已加入 `.gitignore`，不纳入版本控制（可按需调整） |

---

## 文件命名规范

| 文件类型 | 格式 | 示例 |
|----------|------|------|
| 用例准备 | `0-用例准备_YYYYMMDD_HHMMSS.md` | `0-用例准备_20260601_143000.md` |
| 评审记要 | `1-评审记要_YYYYMMDD_HHMMSS.md` | `1-评审记要_20260601_150000.md` |
| 用例定稿 | `2-用例定稿_YYYYMMDD_HHMMSS.md` | `2-用例定稿_20260601_160000.md` |
| 导出中间数据 | `export_data_YYYYMMDD_HHMMSS.json` | `export_data_20260601_160000.json` |
| Excel 导出 | `testcases_YYYYMMDD_HHMMSS.xlsx` | `testcases_20260601_160000.xlsx` |
| XMind 导出 | `testcases_YYYYMMDD_HHMMSS.xmind` | `testcases_20260601_160000.xmind` |
| OTP 导出 | `otp_export_YYYYMMDD_HHMMSS.json` | `otp_export_20260601_160000.json` |

---

## OTP 导入说明

> **注意**：导入前请确认 `project.config.md` 中「OTP 字段映射配置」全部勾选，字段名称与目标 OTP 系统完全一致。

1. 运行流程至阶段 5，选择「Y」生成 JSON 文件
2. 建议先用 **1~2 条用例**测试导入，确认字段映射正确后再批量导入
3. 登录 OTP 系统，选择「导入测试用例」，上传 `otp_export_xxx.json`
4. 导入后如有字段不符，在对话中告知 AI 调整映射关系后重新生成

---

*由 testcase-creator skill 维护 · 最后更新：2026-06-02*
