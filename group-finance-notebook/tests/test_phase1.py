from __future__ import annotations

import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from gfnb.service import NotebookService


class Phase1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"
        self.service = NotebookService(self.db_path)
        self.service.ensure_demo_data()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_resolver_matches_code_short_and_full_name(self) -> None:
        code_match = self.service.resolve_company("A001", "2026-06-30")
        short_match = self.service.resolve_company("Alpha Holding", "2026-06-30")
        full_match = self.service.resolve_company("Alpha Holding Ltd.", "2026-06-30")
        self.assertEqual(code_match.status, "resolved")
        self.assertEqual(short_match.company_id, code_match.company_id)
        self.assertEqual(full_match.company_id, code_match.company_id)

    def test_as_of_graph_changes_between_march_and_june(self) -> None:
        march = self.service.graph("2026-03-31")
        june = self.service.graph("2026-06-30")
        march_edges = {(edge["parent_company_id"], edge["child_company_id"], edge["ownership_pct"]) for edge in march["edges"]}
        june_edges = {(edge["parent_company_id"], edge["child_company_id"], edge["ownership_pct"]) for edge in june["edges"]}
        self.assertIn(0.6, {edge[2] for edge in march_edges})
        self.assertIn(0.8, {edge[2] for edge in june_edges})
        self.assertEqual(len(march["edges"]), 1)
        self.assertEqual(len(june["edges"]), 2)

    def test_import_preview_and_apply(self) -> None:
        text = "\n".join(
            [
                "母公司代碼\t母公司簡稱\t子公司代碼\t子公司簡稱\t持股比例\t變更日期",
                "A001\tAlpha Holding\tE001\tEpsilon Ops\t55%\t2026-07-01",
            ]
        )
        preview = self.service.preview_import(text)
        self.assertFalse(preview["errors"])
        self.assertEqual(preview["mode"], "edge")
        self.assertEqual(len(preview["changes"]["new_companies"]), 1)
        result = self.service.apply_import(text)
        self.assertEqual(result["status"], "applied")
        july = self.service.graph("2026-07-01")
        self.assertEqual(len(july["edges"]), 3)

    def test_export_csv_bundle_contains_manifest_and_edges(self) -> None:
        name, content, mime_type = self.service.export_bundle("csv")
        self.assertEqual(name, "group-finance-notebook-csv.zip")
        self.assertEqual(mime_type, "application/zip")
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            self.assertIn("manifest.json", archive.namelist())
            self.assertIn("investment_edges.csv", archive.namelist())

    def test_company_versioning_keeps_history(self) -> None:
        alpha = self.service.search("A001", "2026-06-30")[0]
        company_id = alpha["company_id"]
        self.service.upsert_company(
            {
                "company_id": company_id,
                "valid_from": "2026-08-01",
                "company_code": "A001",
                "short_name": "Alpha Holding",
                "full_name": "Alpha Holding Ltd.",
                "main_business": "控股管理",
                "symbol_code": "ALPHA",
                "region": "台灣",
                "currency": "USD",
                "note": "currency update",
            }
        )
        june = self.service.company_detail(company_id, "2026-06-30")
        august = self.service.company_detail(company_id, "2026-08-01")
        self.assertEqual(june["profile"]["currency"], "TWD")
        self.assertEqual(august["profile"]["currency"], "USD")
        self.assertGreaterEqual(len(august["history"]), 2)


if __name__ == "__main__":
    unittest.main()
