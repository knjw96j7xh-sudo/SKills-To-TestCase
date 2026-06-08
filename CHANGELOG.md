# Changelog

All notable changes to this project will be documented in this file.

---

## [1.2.0] - 2026-06-03

### Added

- **阶段 1 需求来源扩展**
  - 新增 E：图片/截图（.png/.jpg/.jpeg/.gif/.webp），支持 UI 设计稿、原型图、流程图识别
  - 新增 F：飞书文档链接（feishu.cn / larksuite.com）
  - 新增 G：Excel 需求列表（.xlsx/.xls），通过 openpyxl 解析
  - 新增 H：需求管理工具链接（Jira / Tapd / 禅道）
  - 所有 3 个 skill 文件（agents / claude / cursor）同步更新

- **Cursor 版 testcase-export skill**
  - 新增 `.cursor/skills/testcase-export/skill.md`，Cursor 用户可使用 `/testcase-export` 独立导出
  - init 脚本（sh / ps1）同步更新，自动复制到目标项目

- **TESTCASE_GUIDE.md 快速触发话术扩展**
  - 新增 6 种触发场景：完整流程、仅评审、仅导出、追问补充、资产沉淀、快速生成
  - 纯对话工具用户可直接复制对应话术启动不同场景

- **阶段 4 评审升级为 subagent 隔离上下文模式**
  - 启动独立 subagent 执行评审，模拟「换一个人审」的多人评审效果
  - subagent 以全新视角审查用例，不受生成时的确认偏误影响
  - 评审报告由 subagent 独立写入，主 agent 展示结果供用户决策

- **Token 消耗提示**
  - 全部 5 个 skill 文件（testcase-creator / testcase-export / cursor / agents）流程结束时增加 `[TOKEN]` 提示，提醒用户查看终端底部 token 统计

### Fixed

- **Cursor 版 testcase-creator 一致性修复**
  - 移除不存在的 `/checkpoint-init` 命令引用
  - 补充 Jira CSV 多步骤用例处理规则和优先级映射说明
  - 占位符校验补充 `[填写姓名]` 和 `[填写团队共享路径]` 检查

- **P3 优先级映射补充**
  - `csv-schema.json` 新增 P3→Low 映射，避免导出时优先级丢失
  - 所有 skill 文件的优先级映射说明同步更新

### Changed

- **.gitignore 更新**
  - 新增 `*.pptx` 过滤规则，培训资料不纳入版本管理

- **本地知识保留机制**
  - `checkpoints-index.md` 和 `review-expectations-index.md` 标记为 `--skip-worktree`
  - Git 远端保持初始模板版本，本地保留实际沉淀的检查点/评审点
  - 避免后续推送时覆盖个人积累的知识资产

---

## [1.1.0] - 2026-06-01

### Added

- **Jira CSV 导出支持**
  - 新增 `.testcase-assets/templates/jira-csv-template.csv` 示例文件
  - 新增 `.testcase-assets/templates/csv-schema.json` 字段映射规则
  - 新增 `.testcase-assets/scripts/md_to_csv.py` MD 转 CSV 转换脚本
  - CSV 格式：UTF-8 with BOM 编码，支持 Jira 直接导入
  - 多步骤用例自动展开为多行，首行填写用例基础信息，后续行仅填写步骤详情
  - 优先级映射：P0→High, P1→Medium, P2→Low

- **独立导出命令 `/testcase-export`**
  - 新增 `.claude/commands/testcase-export.md`
  - 支持从已有定稿文件独立导出，无需重走 5 阶段用例生成流程
  - 自动扫描历史子目录或读取 `history-index.md` 列出可选文件
  - 支持多平台导出：Jira CSV / Excel / XMind

- **历史记录管理**
  - 每次运行归入独立子目录：`.testcase-assets/history/<YYYYMMDD>_<HHMMSS>_<模块名>/`
  - 新增 `history-index.md` 索引文件，自动追加每次运行记录
  - 子目录内文件统一命名（无时间戳后缀），便于管理

### Changed

- **阶段 5 导出流程重构**（`testcase-creator.md`）
  - 原流程：Excel/XMind 单独询问，导出入口分散
  - 新流程：统一展示所有导出平台（J/E/X/N），一次选择，可多选
  - 新增 Jira CSV 作为首选导出选项

- **文件目录结构重构**
  - 原结构：`history/0-用例准备_<timestamp>.md`、`1-评审记要_<timestamp>.md` 平铺
  - 新结构：`history/<运行目录>/0-用例准备.md`、`1-评审记要.md` 归入子目录
  - 已有文件迁移至 `20260601_174203_碳盘查清单/` 子目录

---

## [1.1.1] - 2026-06-02

### Fixed

- **Critical 修复**
  - `init-testcase.sh` 补充 v1.1.0 缺失文件：`testcase-export.md`、`md_to_csv.py`、`csv-schema.json`、`jira-csv-template.csv`、`history-index.md`
  - `init-testcase.ps1` 同步补充 v1.1.0 缺失文件（与 sh 版本保持一致）
  - `.gitkeep.md` 重命名为 `.gitkeep`，修复与 `.gitignore` 规则不匹配问题
  - `.cursor/skills/testcase-creator/skill.md` 同步新目录结构（子目录命名 + Jira CSV 导出）
  - `.claude/settings.local.json` 权限 glob 模式更新为 `history/*/` 匹配新目录结构
  - `init-testcase.ps1` settings.local.json 模板更新为新目录 glob 模式

- **High 修复**
  - `md_to_csv.py` 优先级读取改为显式读取 MD 表格中的优先级列，不再依赖启发式推断
  - 三个 Python 脚本（`export_excel.py`、`export_xmind.py`、`md_to_csv.py`）增加文件 I/O 错误处理（try/except）
  - 脚本增加输入文件存在性校验、JSON 格式校验、编码校验
  - 脚本增加 `testcases` 字段类型校验（必须为数组）

- **Medium 修复**
  - 初始化检查增加 `project.config.md` 占位符检测，未填写时警告用户
  - 模块名清理：移除文件系统不允许的字符（`/ \ : * ? " < > |`）
  - `md_to_csv.py` 步骤解析正则优化，减少误拆风险
  - `md_to_csv.py` 解析失败时输出格式提示，不再静默生成空 CSV
  - `TESTCASE_GUIDE.md` 文件命名更新为子目录结构
  - `TESTCASE_GUIDE.md` 阶段 5 导出流程更新为统一 J/O/E/X/N 选择
  - `README.md` 完善目录结构、可用命令、导出格式、历史记录管理等章节

---

## [1.0.0] - 2026-05-01

### Added

- **用例生成 Skill `/testcase-creator`**
  - 5 阶段流程：需求输入 → 输入结构化 → 用例生成 → 评审优化 → 定稿导入
  - 支持多种需求来源：文字描述、乐享链接、接口文档、本地文件（.md/.docx/.pdf）
  - 检查点索引（checkpoints-index.md）：按业务域分类管理检查点
  - 评审点索引（review-expectations-index.md）：多维度评审覆盖检查
  - 资产沉淀：支持新增检查点和评审点，自动编号去重

- **Excel / XMind 导出**
  - 支持导出 Excel（.xlsx）带颜色分类、冻结表头
  - 支持导出 XMind（.xmind）思维导图
  - 脚本：`.testcase-assets/scripts/export_excel.py`、`export_xmind.py`

- **初始化脚本**
  - `init-testcase.sh`（macOS/Linux）
  - `init-testcase.ps1`（Windows）
