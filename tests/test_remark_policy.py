import json
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RemarkPolicyTest(unittest.TestCase):
    def test_creator_requires_empty_remarks(self):
        prompt = (ROOT / "skills/testcase-creator/prompt.md").read_text(encoding="utf-8")
        export_reference = (
            ROOT / "skills/testcase-creator/references/export-workflow.md"
        ).read_text(encoding="utf-8")
        config = json.loads(
            (ROOT / "framework/templates/testcase-table-config.json").read_text(encoding="utf-8")
        )
        remark_column = next(
            column for column in config["optional_columns"] if column["field"] == "remark"
        )

        self.assertIn("**备注列强制规则**", prompt)
        self.assertIn("md_to_json.py", export_reference)
        self.assertIn("assert all(tc.get('remark', '') == ''", export_reference)
        self.assertIn("生成用例时固定留空", remark_column["description"])

    def test_shared_excel_export_preserves_existing_remark(self):
        payload = {
            "meta": {
                "project": "回归测试",
                "module": "导出",
                "generated_at": "2026-07-23",
            },
            "testcases": [
                {
                    "id": "TC-001",
                    "module": "模块一",
                    "test_point": "已有备注导出",
                    "precondition": "无",
                    "steps": "1. 导出用例",
                    "expected": "保留已有备注",
                    "checkpoint": "",
                    "type": "正向",
                    "priority": "P1",
                    "remark": "需要保留",
                }
            ],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_path = temp_path / "input.json"
            output_path = temp_path / "output.xlsx"
            input_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "framework/scripts/export_excel.py"),
                    str(input_path),
                    str(output_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            with zipfile.ZipFile(output_path) as archive:
                sheet = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
            namespace = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
            cell = sheet.find(".//x:c[@r='M3']", namespace)
            self.assertIsNotNone(cell)
            self.assertEqual("需要保留", cell.findtext(".//x:t", namespaces=namespace))


if __name__ == "__main__":
    unittest.main()
