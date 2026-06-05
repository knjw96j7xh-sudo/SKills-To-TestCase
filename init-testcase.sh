#!/bin/bash

# ============================================================
# testcase-creator 一键初始化脚本
# 用法：bash init-testcase.sh [目标项目路径]
# 示例：bash init-testcase.sh /path/to/your-project
#       bash init-testcase.sh .   （在目标项目根目录下直接运行）
# ============================================================

set -e

# ---------- 颜色定义 ----------
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ---------- 脚本自身目录（模板源）----------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ---------- 目标项目路径 ----------
if [ -n "$1" ]; then
  TARGET_DIR="$(cd "$1" && pwd)"
else
  echo -e "${YELLOW}请输入目标项目的绝对路径（直接回车则使用当前目录）：${NC}"
  read -r INPUT_PATH
  if [ -z "$INPUT_PATH" ]; then
    TARGET_DIR="$(pwd)"
  else
    TARGET_DIR="$(cd "$INPUT_PATH" && pwd)"
  fi
fi

# ---------- 确认目标路径 ----------
echo ""
echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}   testcase-creator 初始化脚本${NC}"
echo -e "${BLUE}==========================================${NC}"
echo ""
echo -e "[DIR] 模板来源：${SCRIPT_DIR}"
echo -e "[TARGET] 目标项目：${TARGET_DIR}"
echo ""

if [ ! -d "$TARGET_DIR" ]; then
  echo -e "${RED}[FAIL] 目标路径不存在：$TARGET_DIR${NC}"
  exit 1
fi

echo -e "${YELLOW}确认将模板文件复制到上述目标路径？(y/N)${NC}"
read -r CONFIRM
if [[ "$CONFIRM" != "y" && "$CONFIRM" != "Y" ]]; then
  echo -e "${RED}已取消。${NC}"
  exit 0
fi

echo ""

# ---------- 复制函数（带冲突检测）----------
copy_with_check() {
  local SRC="$1"
  local DEST="$2"
  local LABEL="$3"

  if [ -e "$DEST" ]; then
    if [ "$SRC" -ef "$DEST" ]; then
      echo -e "  ${GREEN}[OK] 目标与源相同，无需复制：${LABEL}${NC}"
    else
      echo -e "  ${YELLOW}[WARN]  已存在，跳过（如需覆盖请加 --force 参数）：${LABEL}${NC}"
    fi
  else
    mkdir -p "$(dirname "$DEST")"
    cp -r "$SRC" "$DEST"
    echo -e "  ${GREEN}[OK] 已复制：${LABEL}${NC}"
  fi
}

# 如果传入 --force 参数，则强制覆盖
FORCE=false
for arg in "$@"; do
  if [ "$arg" == "--force" ]; then
    FORCE=true
  fi
done

copy_with_force() {
  local SRC="$1"
  local DEST="$2"
  local LABEL="$3"

  if [ -e "$DEST" ] && [ "$SRC" -ef "$DEST" ]; then
    echo -e "  ${GREEN}[OK] 目标与源相同，无需复制：${LABEL}${NC}"
    return 0
  fi

  if [ "$FORCE" == "true" ]; then
    mkdir -p "$(dirname "$DEST")"
    cp -r "$SRC" "$DEST"
    echo -e "  ${GREEN}[OK] 强制覆盖：${LABEL}${NC}"
  else
    copy_with_check "$SRC" "$DEST" "$LABEL"
  fi
}

# ---------- 开始复制 ----------
echo -e "${BLUE}-> 正在复制 Agent/Codex Skills...${NC}"
copy_with_force \
  "${SCRIPT_DIR}/.agents/skills/source-command-testcase-creator/SKILL.md" \
  "${TARGET_DIR}/.agents/skills/source-command-testcase-creator/SKILL.md" \
  ".agents/skills/source-command-testcase-creator/SKILL.md"

copy_with_force \
  "${SCRIPT_DIR}/.agents/skills/source-command-testcase-export/SKILL.md" \
  "${TARGET_DIR}/.agents/skills/source-command-testcase-export/SKILL.md" \
  ".agents/skills/source-command-testcase-export/SKILL.md"

echo ""
echo -e "${BLUE}-> 正在复制 Cursor Skill...${NC}"
copy_with_force \
  "${SCRIPT_DIR}/.cursor/skills/testcase-creator/skill.md" \
  "${TARGET_DIR}/.cursor/skills/testcase-creator/skill.md" \
  ".cursor/skills/testcase-creator/skill.md"

copy_with_force \
  "${SCRIPT_DIR}/.cursor/skills/testcase-export/skill.md" \
  "${TARGET_DIR}/.cursor/skills/testcase-export/skill.md" \
  ".cursor/skills/testcase-export/skill.md"

echo ""
echo -e "${BLUE}-> 正在复制 Claude Code 命令...${NC}"
copy_with_force \
  "${SCRIPT_DIR}/.claude/commands/testcase-creator.md" \
  "${TARGET_DIR}/.claude/commands/testcase-creator.md" \
  ".claude/commands/testcase-creator.md"

copy_with_force \
  "${SCRIPT_DIR}/.claude/commands/testcase-export.md" \
  "${TARGET_DIR}/.claude/commands/testcase-export.md" \
  ".claude/commands/testcase-export.md"

echo ""
echo -e "${BLUE}-> 正在复制测试资产目录...${NC}"

# 检查点索引
copy_with_force \
  "${SCRIPT_DIR}/.testcase-assets/checkpoints-index.md" \
  "${TARGET_DIR}/.testcase-assets/checkpoints-index.md" \
  ".testcase-assets/checkpoints-index.md"

# 评审点索引
copy_with_force \
  "${SCRIPT_DIR}/.testcase-assets/review-expectations-index.md" \
  "${TARGET_DIR}/.testcase-assets/review-expectations-index.md" \
  ".testcase-assets/review-expectations-index.md"

# 模板文件
copy_with_force \
  "${SCRIPT_DIR}/.testcase-assets/templates/testcase-table.md" \
  "${TARGET_DIR}/.testcase-assets/templates/testcase-table.md" \
  ".testcase-assets/templates/testcase-table.md"

copy_with_force \
  "${SCRIPT_DIR}/.testcase-assets/templates/csv-schema.json" \
  "${TARGET_DIR}/.testcase-assets/templates/csv-schema.json" \
  ".testcase-assets/templates/csv-schema.json"

copy_with_force \
  "${SCRIPT_DIR}/.testcase-assets/templates/jira-csv-template.csv" \
  "${TARGET_DIR}/.testcase-assets/templates/jira-csv-template.csv" \
  ".testcase-assets/templates/jira-csv-template.csv"

# history 目录占位
mkdir -p "${TARGET_DIR}/.testcase-assets/history"
echo -e "  ${GREEN}[OK] 已创建：.testcase-assets/history/ 目录${NC}"

# history-index.md 初始化
if [ ! -f "${TARGET_DIR}/.testcase-assets/history/history-index.md" ]; then
  cat > "${TARGET_DIR}/.testcase-assets/history/history-index.md" << 'INDEX_EOF'
# 用例生成历史索引

> 每次运行 `/testcase-creator` 自动追加记录。文件按时间倒序排列（最新在前）。

---

| 时间 | 模块 | 用例数 | 运行目录 | 导出文件 |
|------|------|--------|----------|----------|
INDEX_EOF
  echo -e "  ${GREEN}[OK] 已初始化：.testcase-assets/history/history-index.md${NC}"
fi

# .gitkeep 占位
touch "${TARGET_DIR}/.testcase-assets/history/.gitkeep"

# 项目配置文件
copy_with_force \
  "${SCRIPT_DIR}/.testcase-assets/project.config.md" \
  "${TARGET_DIR}/.testcase-assets/project.config.md" \
  ".testcase-assets/project.config.md"

echo ""
echo -e "${BLUE}-> 正在复制导出脚本...${NC}"
copy_with_force \
  "${SCRIPT_DIR}/.testcase-assets/scripts/export_excel.py" \
  "${TARGET_DIR}/.testcase-assets/scripts/export_excel.py" \
  ".testcase-assets/scripts/export_excel.py"

copy_with_force \
  "${SCRIPT_DIR}/.testcase-assets/scripts/export_xmind.py" \
  "${TARGET_DIR}/.testcase-assets/scripts/export_xmind.py" \
  ".testcase-assets/scripts/export_xmind.py"

copy_with_force \
  "${SCRIPT_DIR}/.testcase-assets/scripts/md_to_csv.py" \
  "${TARGET_DIR}/.testcase-assets/scripts/md_to_csv.py" \
  ".testcase-assets/scripts/md_to_csv.py"

echo ""
echo -e "${BLUE}-> 正在复制 Codex/纯对话工具指南...${NC}"
copy_with_force \
  "${SCRIPT_DIR}/TESTCASE_GUIDE.md" \
  "${TARGET_DIR}/TESTCASE_GUIDE.md" \
  "TESTCASE_GUIDE.md"

# ---------- .gitignore 追加 ----------
echo ""
echo -e "${BLUE}-> 检查 .gitignore...${NC}"
GITIGNORE="${TARGET_DIR}/.gitignore"
HISTORY_PATTERN=".testcase-assets/history/"

if [ -f "$GITIGNORE" ]; then
  if grep -qF "$HISTORY_PATTERN" "$GITIGNORE"; then
    echo -e "  ${YELLOW}[WARN]  .gitignore 已包含 history 目录规则，跳过${NC}"
  else
    echo "" >> "$GITIGNORE"
    echo "# testcase-creator 生成的历史记录（可按需改为 Git 追踪）" >> "$GITIGNORE"
    echo "$HISTORY_PATTERN" >> "$GITIGNORE"
    echo -e "  ${GREEN}[OK] 已追加 .testcase-assets/history/ 到 .gitignore${NC}"
  fi
else
  echo -e "  ${YELLOW}[WARN]  未找到 .gitignore，已跳过（可手动添加 .testcase-assets/history/）${NC}"
fi

# ---------- 自动生成 .claude/settings.local.json ----------
echo ""
echo -e "${BLUE}-> 正在生成 .claude/settings.local.json（根据当前用户动态写入路径）...${NC}"

SETTINGS_FILE="${TARGET_DIR}/.claude/settings.local.json"
mkdir -p "${TARGET_DIR}/.claude"

cat > "$SETTINGS_FILE" << SETTINGS_EOF
{
  "permissions": {
    "allow": [
      "Bash(pdftotext ${HOME}/Downloads/*.pdf -)",
      "Bash(pdftotext ${HOME}/Desktop/*.pdf -)",
      "Bash(textutil -convert txt -stdout ${HOME}/Downloads/*.docx)",
      "Bash(textutil -convert txt -stdout ${HOME}/Desktop/*.docx)",
      "Bash(python3 .testcase-assets/scripts/export_excel.py .testcase-assets/history/*/export_data.json .testcase-assets/history/*/testcases.xlsx)",
      "Bash(python3 .testcase-assets/scripts/export_xmind.py .testcase-assets/history/*/export_data.json .testcase-assets/history/*/testcases.xmind)",
      "Bash(python3 .testcase-assets/scripts/md_to_csv.py .testcase-assets/history/*/2-用例定稿.md .testcase-assets/history/*/jira_export.csv)"
    ]
  }
}
SETTINGS_EOF

echo -e "  ${GREEN}[OK] 已生成 .claude/settings.local.json（路径已适配当前用户: ${HOME}）${NC}"

# ---------- 完成摘要 ----------
echo ""
echo -e "${BLUE}==========================================${NC}"
echo -e "${GREEN} 初始化完成！${NC}"
echo -e "${BLUE}==========================================${NC}"
echo ""
echo -e "[DIR] 目标项目结构："
echo -e "   ${TARGET_DIR}/"
echo -e "   ├── .agents/skills/"
echo -e "   │   ├── source-command-testcase-creator/SKILL.md"
echo -e "   │   └── source-command-testcase-export/SKILL.md"
echo -e "   ├── .cursor/skills/testcase-creator/skill.md"
echo -e "   ├── .claude/commands/"
echo -e "   │   ├── testcase-creator.md"
echo -e "   │   └── testcase-export.md"
echo -e "   ├── TESTCASE_GUIDE.md                 （Codex/纯对话工具使用）"
echo -e "   └── .testcase-assets/"
echo -e "       ├── project.config.md               （项目配置，首次使用前请填写）"
echo -e "       ├── checkpoints-index.md"
echo -e "       ├── review-expectations-index.md"
echo -e "       ├── templates/"
echo -e "       │   ├── testcase-table.md"
echo -e "       │   ├── csv-schema.json"
echo -e "       │   └── jira-csv-template.csv"
echo -e "       ├── scripts/"
echo -e "       │   ├── export_excel.py         （Excel 导出）"
echo -e "       │   ├── export_xmind.py         （XMind 导出）"
echo -e "       │   └── md_to_csv.py            （Jira CSV 导出）"
echo -e "       └── history/"
echo -e "           ├── history-index.md"
echo -e "           └── .gitkeep"
echo ""
echo -e ">> 下一步："
echo -e "   1. 【必填】编辑 ${GREEN}.testcase-assets/project.config.md${NC}，填写项目名称、业务域、默认导出路径"
echo -e "   2. 【必填】根据实际业务补充 ${GREEN}.testcase-assets/checkpoints-index.md${NC}"
echo -e "   3. 【环境】安装 Excel 导出依赖：${YELLOW}pip3 install openpyxl${NC}"
echo -e "   4. 【环境】如需读取 PDF 文件：${YELLOW}brew install poppler${NC}  (可选)"
echo -e "   5. Cursor 用户：在项目中输入 ${GREEN}/testcase-creator${NC} 触发"
echo -e "   6. Claude Code 用户：输入 ${GREEN}/testcase-creator${NC} 触发"
echo -e "   7. Codex 用户：确认 ${GREEN}.agents/skills/${NC} 已复制，可直接说明运行 testcase-creator"
echo -e "   8. ChatGPT/纯对话工具用户：复制 ${GREEN}TESTCASE_GUIDE.md${NC} 内容到对话开头"
echo ""
echo -e "[TIP] 提示：如需强制覆盖已有文件，请加 ${YELLOW}--force${NC} 参数重新运行"
echo ""
