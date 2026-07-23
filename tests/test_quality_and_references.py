import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUALITY_PATH = ROOT / "framework/scripts/testcase_quality.py"
SPEC = importlib.util.spec_from_file_location("testcase_quality", QUALITY_PATH)
QUALITY = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = QUALITY
SPEC.loader.exec_module(QUALITY)


def testcase(**overrides):
    case = {
        "id": "TC-001",
        "module": "用户中心",
        "test_point": "保存用户信息",
        "precondition": "用户已登录",
        "steps": "1. 输入姓名\n2. 单击保存按钮",
        "expected": "1. 姓名显示为张三\n2. 提示“保存成功”",
        "checkpoint": "UC-01",
        "type": "正向",
        "priority": "P1",
        "remark": "",
    }
    case.update(overrides)
    return case


class QualityCheckTest(unittest.TestCase):
    def test_detects_blocking_and_warning_rules(self):
        cases = [
            testcase(expected='1. 正常显示“姓名”\n2. 点击button后提示"成功"'),
            testcase(type="未知", steps="1. 输入\n1. 保存"),
        ]

        issues = QUALITY.inspect_cases(cases)
        codes = {issue.code for issue in issues}

        self.assertIn("DUPLICATE_ID", codes)
        self.assertIn("INVALID_TYPE", codes)
        self.assertIn("STEP_DUPLICATE", codes)
        self.assertIn("FUZZY_WORDING", codes)
        self.assertIn("TERM_BUTTON", codes)
        self.assertIn("QUOTE_MIXED", codes)

    def test_strict_cli_writes_audit_and_fails_only_on_errors(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_path = temp_path / "cases.json"
            audit_path = temp_path / "audit-summary.md"
            input_path.write_text(
                json.dumps({"testcases": [testcase(expected="结果正确")]}, ensure_ascii=False),
                encoding="utf-8",
            )

            warning_result = subprocess.run(
                [
                    sys.executable,
                    str(QUALITY_PATH),
                    str(input_path),
                    "--audit-output",
                    str(audit_path),
                    "--strict",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(0, warning_result.returncode)
            audit = audit_path.read_text(encoding="utf-8")
            self.assertIn("## 模块分布", audit)
            self.assertIn("## 场景分布", audit)
            self.assertIn("FUZZY_WORDING", audit)

            input_path.write_text(
                json.dumps({"testcases": [testcase(priority="紧急")]}, ensure_ascii=False),
                encoding="utf-8",
            )
            error_result = subprocess.run(
                [
                    sys.executable,
                    str(QUALITY_PATH),
                    str(input_path),
                    "--audit-output",
                    str(audit_path),
                    "--strict",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(1, error_result.returncode)
            self.assertIn("INVALID_PRIORITY", audit_path.read_text(encoding="utf-8"))

    def test_markdown_input_and_formula_errors_are_audited(self):
        from openpyxl import Workbook

        markdown = """## 重要性议题

| 用例ID | 所属模块 | 测试点 | 前置条件 | 操作步骤 | 预期结果 | 关联检查点 | 场景类型 | 优先级 | 备注 |
|---|---|---|---|---|---|---|---|---|---|
| TC-001 | 重要性议题 | 保存权重 | 已登录 | 1. 输入权重 | 1. 保存成功 | DATA-01 | 正向 | P1 | |
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            md_path = temp_path / "cases.md"
            xlsx_path = temp_path / "cases.xlsx"
            md_path.write_text(markdown, encoding="utf-8")
            _, cases = QUALITY.load_cases(md_path)
            self.assertEqual("重要性议题", cases[0]["module"])

            workbook = Workbook()
            workbook.active["A1"] = "=#REF!"
            workbook.save(xlsx_path)
            formula_count, errors = QUALITY.inspect_workbook(xlsx_path)
            self.assertEqual(1, formula_count)
            self.assertTrue(any("#REF!" in error for error in errors))


class PromptReferencesTest(unittest.TestCase):
    def test_main_prompt_is_short_and_routes_all_references(self):
        skill_dir = ROOT / "skills/testcase-creator"
        prompt = (skill_dir / "prompt.md").read_text(encoding="utf-8")
        self.assertLess(len(prompt.splitlines()), 200)
        for name in ("input-and-generation.md", "review-workflow.md", "export-workflow.md"):
            self.assertIn(f"references/testcase-creator/{name}", prompt)
            self.assertTrue((skill_dir / "references" / name).is_file())

    def test_locked_dependencies_match_runtime_installers(self):
        lock = (ROOT / "requirements.lock").read_text(encoding="utf-8")
        excel = (ROOT / "framework/scripts/export_excel.py").read_text(encoding="utf-8")
        xmind = (ROOT / "framework/scripts/export_xmind.py").read_text(encoding="utf-8")
        for requirement in ("PyYAML==6.0.3", "json-repair==0.61.2", "openpyxl==3.1.5"):
            self.assertIn(requirement, lock)
        self.assertIn('"json-repair": "0.61.2"', excel)
        self.assertIn('"openpyxl": "3.1.5"', excel)
        self.assertIn('"json-repair": "0.61.2"', xmind)


if __name__ == "__main__":
    unittest.main()
