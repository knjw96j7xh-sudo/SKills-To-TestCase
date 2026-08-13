import csv
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "framework/scripts"


def load_module(name: str, path: Path):
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


COMMON = load_module("testcase_common", SCRIPTS / "testcase_common.py")


SAMPLE_MD = """## 用户中心

| 用例ID | 所属模块 | 测试点 | 前置条件 | 操作步骤 | 预期结果 | 关联检查点 | 场景类型 | 优先级 | 备注 |
|--------|----------|--------|----------|----------|----------|------------|----------|--------|------|
| TC-001 | 用户中心 | 保存资料 | 已登录 | 1. 输入姓名 2. 单击保存按钮 | 1. 提示“保存成功” | UC-01 | 正向 | P1 | |
| TC-002 | 用户中心 | 并发提交 | 已登录 | 1. 同时提交两次 | 1. 仅成功一次 | RISK-01 | 并发 |  | |
"""


class ExportPipelineTest(unittest.TestCase):
    def test_priority_rules_align_with_docs(self):
        self.assertEqual("P2", COMMON.default_priority_for_type("并发"))
        self.assertEqual("Low", COMMON.priority_to_jira("", "并发"))
        self.assertEqual("High", COMMON.priority_to_jira("", "异常"))
        self.assertEqual("Medium", COMMON.priority_to_jira("P1", "并发"))

    def test_md_to_json_and_csv_share_parser(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            md_path = temp_path / "2-用例定稿.md"
            json_path = temp_path / "export_data.json"
            csv_path = temp_path / "jira_export.csv"
            md_path.write_text(SAMPLE_MD, encoding="utf-8")

            json_result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "md_to_json.py"),
                    str(md_path),
                    str(json_path),
                    "--project",
                    "演示项目",
                    "--module",
                    "用户中心",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(0, json_result.returncode, json_result.stderr)
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(2, len(payload["testcases"]))
            concurrent = next(tc for tc in payload["testcases"] if tc["id"] == "TC-002")
            self.assertEqual("P2", concurrent["priority"])
            self.assertEqual("演示项目", payload["meta"]["project"])

            csv_result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "md_to_csv.py"),
                    str(md_path),
                    str(csv_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(0, csv_result.returncode, csv_result.stderr)
            with csv_path.open(encoding="utf-8-sig") as handle:
                rows = list(csv.reader(handle))
            # 表头 + 至少两条用例首行
            self.assertGreaterEqual(len(rows), 3)
            concurrent_rows = [row for row in rows if row and row[0] == "TC-002"]
            self.assertEqual(1, len(concurrent_rows))
            self.assertEqual("Low", concurrent_rows[0][3])

    def test_case_sort_key_orders_suffix(self):
        ids = ["TC-002", "TC-001a", "TC-001", "TC-010"]
        ordered = sorted(ids, key=COMMON.case_sort_key)
        self.assertEqual(["TC-001", "TC-001a", "TC-002", "TC-010"], ordered)


class SkillContractTest(unittest.TestCase):
    def test_creator_routes_change_and_export_md_pipeline(self):
        skill_dir = ROOT / "skills/testcase-creator"
        prompt = (skill_dir / "prompt.md").read_text(encoding="utf-8")
        export_ref = (skill_dir / "references/export-workflow.md").read_text(encoding="utf-8")
        change_ref = skill_dir / "references/change-workflow.md"
        input_ref = (skill_dir / "references/input-and-generation.md").read_text(encoding="utf-8")

        self.assertTrue(change_ref.is_file())
        self.assertIn("references/testcase-creator/change-workflow.md", prompt)
        self.assertIn("增量变更", prompt)
        self.assertIn("md_to_json.py", prompt)
        self.assertIn("md_to_json.py", export_ref)
        self.assertIn("采用推荐", input_ref)
        self.assertIn("历史用例复用", input_ref)
        self.assertIn("禁止手写", (ROOT / "skills/testcase-export/prompt.md").read_text(encoding="utf-8"))

    def test_versions(self):
        creator = (ROOT / "skills/testcase-creator/meta.yaml").read_text(encoding="utf-8")
        export = (ROOT / "skills/testcase-export/meta.yaml").read_text(encoding="utf-8")
        self.assertIn('version: "1.9.0"', creator)
        self.assertIn('version: "1.6.0"', export)


if __name__ == "__main__":
    unittest.main()
