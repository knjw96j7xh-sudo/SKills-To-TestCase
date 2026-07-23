# testcase-creator · 项目级测试用例生成方案

> 先确认输入，不自动导入，不生成自动化测试代码。检查点和评审点可随项目经验持续沉淀。

---

## 最快体验

```bash
./init-testcase.sh _template .                # 构建最新 Skill 并初始化到当前目录
```

然后在 Claude Code 或 Cursor 中输入 `/testcase-creator`，按提示走完五阶段流程。

> 初始化脚本每次都会重新构建 `dist/`，确保部署的是最新 Skill。仅需生成各平台产物、不执行初始化时，可单独运行 `./build.sh`。

---

## 环境依赖

| 工具 | 用途 | macOS | Windows |
|------|------|-------|---------|
| Python 3.x | 运行导出脚本 | 系统自带 | [python.org](https://python.org) |
| openpyxl | Excel 导出 | `pip3 install openpyxl` | `pip install openpyxl` |
| pdftotext | 读取 PDF（需求来源 D） | `brew install poppler` | WSL: `apt install poppler-utils` |
| XMind 8+ | 打开 .xmind | [xmind.app](https://xmind.app) | [xmind.app](https://xmind.app) |

> XMind 和 Jira CSV 导出无需额外 Python 包。Windows 用户建议在 WSL 中运行 Claude Code。

---

## 目录结构

```
.
├── skills/                        # 统一源文件，只在这里改 prompt
│   ├── testcase-creator/          #   meta.yaml + prompt.md
│   └── testcase-export/           #   meta.yaml + prompt.md
├── framework/                     # 通用框架（与业务无关）
│   ├── templates/                 #   用例表模板、列配置、CSV Schema
│   └── scripts/                   #   导出脚本（Excel / XMind / CSV）
├── projects/                      # 项目资产（按项目隔离）
│   ├── _template/                 #   新项目模板
│   └── <your-project>/            #   你的项目（project.config + checkpoints + reviews）
├── dist/                          # 构建产物（自动生成，gitignore）
├── build.sh / build.py            # 构建脚本
├── init-testcase.sh / .ps1        # 一键初始化脚本
├── TESTCASE_GUIDE.md              # 纯对话工具（ChatGPT 等）使用指南
└── CHANGELOG.md
```

---

## 可用命令

| 命令 | 平台 | 用途 |
|------|------|------|
| `/testcase-creator` | Claude Code / Cursor | 完整五阶段用例生成 |
| `/testcase-export` | Claude Code / Cursor | 从已有定稿导出，不重走流程 |
| `source-command-testcase-creator` | Codex | 同上（Agent 技能） |
| `source-command-testcase-export` | Codex | 同上（Agent 技能） |

---

## 五阶段流程

![用例生成 Skill 流程图](assets/testcase-skill-flow.png)

### 1. 需求与设计输入

支持八种来源：文字粘贴 / 乐享链接 / 接口文档 / 本地文件（md/docx/pdf）/ 图片或截图 / 飞书文档 / Excel 需求列表 / Jira/Tapd/禅道链接。

设计稿请先导出为 PDF 或图片，可与任一需求来源组合输入。阶段一会分别提取测试对象、业务规则、页面流程、组件字段、交互状态和校验反馈，并标记需求与设计之间的缺失、冲突及补充项。确认后创建运行子目录。

### 2. 输入结构化

读取 `checkpoints-index.md`，展示所有分类和检查点，用户选择关联编号，写入 `0-用例准备.md`。

### 3. 用例生成

基于需求要素 + 设计稿要素（如有）+ 检查点，生成覆盖正向/异常/边界/并发四类的用例表，包含优先级列（P0-P3）。

> P0=异常场景（阻断） / P1=正向主流程/边界 / P2=并发 / P3=体验类

### 4. 评审优化

按 UX/DATA/COMP/EXEC/BUG/SEC/PERF 七个维度并行评审，支持多轮增量迭代，每轮生成独立评审报告。

### 5. 定稿导出

写入 `2-用例定稿.md`，支持三种导出格式：

| 选项 | 格式 | 特点 |
|------|------|------|
| J | Jira CSV | UTF-8 BOM 编码，可直接导入 Jira |
| E | Excel (.xlsx) | 场景颜色、冻结表头、优先级着色、统计 Sheet |
| X | XMind (.xmind) | 四级结构：检查点 → 场景类型 → 用例 → 步骤 |

---

## 详细上手

### 安装到你的项目

```bash
# macOS / Linux
./init-testcase.sh <项目名称或目录> <目标路径>

# 示例：用模板初始化新项目
./init-testcase.sh _template /path/to/your-project

# 也可以直接传入项目资产目录
./init-testcase.sh ./projects/_template /path/to/your-project

# 强制覆盖已有文件
./init-testcase.sh _template /path/to/your-project --force
```

| 参数 | 说明 |
|------|------|
| `<项目名称或目录>` | `projects/` 下的子目录名（如 `_template`），或项目资产目录路径 |
| `<目标路径>` | 你要安装到的实际项目目录（绝对路径） |

脚本会自动完成：复制 skill 文件、框架模板、导出脚本、项目资产，生成 `.claude/settings.local.json`，初始化 history 目录，追加 `.gitignore` 规则。

### 安装到当前目录（在本仓库内使用）

```bash
./init-testcase.sh _template .
```

### 各工具触发方式

| 工具 | 操作 |
|------|------|
| **Cursor** | 输入 `/testcase-creator` |
| **Claude Code** | 输入 `/testcase-creator`（确保 `.claude/settings.local.json` 路径正确） |
| **Codex** | 直接说明「运行 testcase-creator」|
| **ChatGPT 等** | 复制 `TESTCASE_GUIDE.md` + 三个资产文件到对话开头 |

---

## 常见操作

### 添加新项目

```
源仓库 (skills-to-testcase/)          目标项目 (your-project/)
├── projects/                          ├── .testcase-assets/
│   └── my-project/                    │   ├── checkpoints-index.md  ← 从这里复制
│       ├── project.config.md          │   ├── project.config.md
│       ├── checkpoints-index.md       │   ├── history/              ← 运行时生成
│       └── review-expectations-index.md│  └── ...
└── ...                                └── ...
```

```bash
cp -r projects/_template projects/my-project    # 复制模板
vim projects/my-project/project.config.md        # 填写项目信息
vim projects/my-project/checkpoints-index.md     # 补充检查点
./build.sh                                        # 构建
./init-testcase.sh my-project /path/to/target     # 安装
```

### 修改 skill 流程

```bash
vim skills/testcase-creator/prompt.md     # 编辑源文件
./build.sh                                # 重新构建
./init-testcase.sh <项目名> <目标路径> --force  # 覆盖安装
```

### 更新项目资产

```bash
vim projects/<项目名>/checkpoints-index.md      # 添加检查点
./init-testcase.sh <项目名> <目标路径>            # 重新安装（不会覆盖已有文件）
```

---

## 历史记录

每次运行创建独立子目录：

```
.testcase-assets/history/
├── history-index.md                      # 自动追加索引
├── 20260601_174203_碳盘查清单/           # 子目录：日期_时间_模块名
│   ├── 0-用例准备.md
│   ├── 1-评审记要.md
│   ├── 2-用例定稿.md
│   └── jira_export.csv
└── 20260615_090000_用户中心/
    └── ...
```

---

## 资产管理规范

| 操作 | 规范 |
|------|------|
| 新增检查点 | 追加到分类末尾，编号递增，不修改已有编号 |
| 废弃检查点 | 描述后标注 `[已废弃]`，不删除 |
| Git 提交 | `chore: 沉淀检查点 XX-XX` |
| history/ 目录 | 已加入 `.gitignore`，可按需调整 |

---

## 导出格式详情

### Jira CSV

- 编码 UTF-8 with BOM，中文不乱码
- 优先级映射：P0→High, P1→Medium, P2/P3→Low
- 多步骤用例首行填基础信息，后续行填步骤详情

### Excel

- 场景分组首行彩色粗边框（正向/异常/边界/并发各一色）
- 优先级列 P0-P3 自动着色
- 列名行筛选器 + 前两行冻结 + 统计 Sheet（柱状图）

### XMind

- 四级结构：根节点 → 检查点 → 场景类型 → 用例 → 步骤
- 优先级显示为用例节点标签，Sheet 2 为统计总览

---

## Jira CSV 导入

1. 运行流程至阶段 5，选择 J 生成 CSV（或用 `/testcase-export` 独立导出）
2. Jira Cloud：项目设置 → Issue Types → Import Issues from CSV
3. Jira Server：项目 → 导入与导出 → 从 CSV 导入
4. 上传 CSV，按向导完成字段映射

| CSV 列 | Jira 字段 |
|--------|-----------|
| 序号 | Issue Key |
| 标题 | Summary |
| 描述 | Description |
| 优先级 | Priority |
| 步骤ID / 步骤 / 测试数据 / 期望结果 | Test Steps（需 Xray / Zephyr 插件） |
| 需求 | Labels / 自定义字段 |
| 测试用例集 | Component / 自定义字段 |

> 中文乱码：选择 UTF-8 编码导入。多步骤用例需 Xray 或 Zephyr Scale 插件支持。

---

*由 testcase-creator skill 维护 · 最后更新：2026-07-23*
