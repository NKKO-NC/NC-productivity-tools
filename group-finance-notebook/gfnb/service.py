from __future__ import annotations

import csv
import io
import json
import math
import sqlite3
import uuid
import zipfile
from collections import Counter, defaultdict, deque
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .database import connect, init_db, now_iso


RESOLVER_ORDER = ["company_code", "full_name", "short_name", "former_name", "custom"]
CORE_ALIAS_TYPES = ["company_code", "short_name", "full_name"]
GRAPH_VIEW_KEY = "default"

COMPANY_FIELD_ALIASES = {
    "company_code": ["公司代碼", "公司代码", "company_code", "代碼", "代码"],
    "short_name": ["公司簡稱", "公司简称", "short_name", "簡稱", "简称"],
    "full_name": ["公司全稱", "公司全称", "full_name", "公司名稱", "公司名称"],
    "main_business": ["公司主營項目", "公司主营项目", "main_business", "主營項目", "主营项目"],
    "symbol_code": ["代號", "代号", "symbol_code", "股票代號", "股票代号"],
    "region": ["所在地區", "所在地区", "地區", "地区", "region"],
    "currency": ["使用幣別", "使用币别", "幣別", "币别", "currency"],
    "note": ["備註", "备注", "note"],
    "valid_from": ["有效起日", "生效日", "valid_from", "change_date", "日期", "date", "as_of_date"],
}

EDGE_FIELD_ALIASES = {
    "parent_company_code_raw": ["母公司代碼", "母公司代码", "parent_company_code", "母公司代码raw", "上層公司代碼", "上层公司代码"],
    "parent_short_name_raw": ["母公司簡稱", "母公司简称", "parent_short_name", "上層公司簡稱", "上层公司简称"],
    "parent_full_name_raw": ["母公司全稱", "母公司全称", "parent_full_name", "上層公司全稱", "上层公司全称"],
    "child_company_code_raw": ["子公司代碼", "子公司代码", "child_company_code", "下層公司代碼", "下层公司代码"],
    "child_short_name_raw": ["子公司簡稱", "子公司简称", "child_short_name", "下層公司簡稱", "下层公司简称"],
    "child_full_name_raw": ["子公司全稱", "子公司全称", "child_full_name", "下層公司全稱", "下层公司全称"],
    "investment_shares": ["投資股數", "投资股数", "investment_shares", "股數", "股数"],
    "child_total_shares": ["子公司總股數", "子公司总股数", "child_total_shares", "總股數", "总股数"],
    "ownership_pct": ["占股比", "持股比例", "持股比", "ownership_pct", "%"],
    "change_date": ["變更日期", "变更日期", "change_date", "日期", "date", "交易日期"],
    "note": ["備註", "备注", "note"],
}

REGION_COLORS = {
    "台灣": "#f4b942",
    "臺灣": "#f4b942",
    "中國": "#ff7a59",
    "香港": "#f26b8a",
    "新加坡": "#4db6ac",
    "美國": "#6b8cff",
    "日本": "#7aa95c",
}


@dataclass
class ResolutionResult:
    status: str
    company_id: str | None = None
    reason: str | None = None
    candidates: list[dict[str, Any]] | None = None


class NotebookService:
    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        init_db(self.db_path)

    def connection(self) -> sqlite3.Connection:
        return closing(connect(self.db_path))

    def ensure_demo_data(self) -> None:
        with self.connection() as connection:
            count = connection.execute(
                "SELECT COUNT(*) AS count FROM company_identity"
            ).fetchone()["count"]
            if count:
                return
            self._seed_demo_data(connection)
            connection.commit()

    def reset_demo_data(self) -> None:
        if self.db_path.exists():
            self.db_path.unlink()
        init_db(self.db_path)
        self.ensure_demo_data()

    def summary(self, as_of_date: str) -> dict[str, Any]:
        graph = self.graph(as_of_date)
        unresolved = 0
        missing_region = sum(1 for node in graph["nodes"] if "region" in node["missing_fields"])
        return {
            "as_of_date": as_of_date,
            "company_count": len(graph["nodes"]),
            "edge_count": len(graph["edges"]),
            "unresolved_count": unresolved,
            "missing_region_count": missing_region,
            "available_dates": self.available_dates(),
        }

    def available_dates(self) -> list[str]:
        with self.connection() as connection:
            rows = connection.execute(
                """
                SELECT DISTINCT valid_from AS value FROM company_profile_scd
                UNION
                SELECT DISTINCT valid_from AS value FROM investment_edge_scd
                ORDER BY value
                """
            ).fetchall()
        return [row["value"] for row in rows]

    def graph(self, as_of_date: str) -> dict[str, Any]:
        parsed = parse_date(as_of_date)
        with self.connection() as connection:
            profile_rows = connection.execute(
                """
                SELECT * FROM company_profile_scd
                WHERE valid_from <= ?
                  AND (valid_to IS NULL OR valid_to > ?)
                ORDER BY COALESCE(short_name, full_name, company_code)
                """,
                (parsed, parsed),
            ).fetchall()
            edge_rows = connection.execute(
                """
                SELECT * FROM investment_edge_scd
                WHERE valid_from <= ?
                  AND (valid_to IS NULL OR valid_to > ?)
                ORDER BY parent_company_id, child_company_id
                """,
                (parsed, parsed),
            ).fetchall()
            layout_rows = connection.execute(
                """
                SELECT company_id, x, y, pinned
                FROM graph_layout
                WHERE view_key = ?
                """,
                (GRAPH_VIEW_KEY,),
            ).fetchall()
        layouts = {row["company_id"]: dict(row) for row in layout_rows}
        positions = self._compute_positions(profile_rows, edge_rows, layouts)
        nodes = []
        for row in profile_rows:
            position = positions[row["company_id"]]
            node = {
                "company_id": row["company_id"],
                "label": row["short_name"] or row["full_name"] or row["company_code"] or row["company_id"],
                "company_code": row["company_code"],
                "short_name": row["short_name"],
                "full_name": row["full_name"],
                "main_business": row["main_business"],
                "symbol_code": row["symbol_code"],
                "region": row["region"],
                "currency": row["currency"],
                "note": row["note"],
                "valid_from": row["valid_from"],
                "valid_to": row["valid_to"],
                "x": position["x"],
                "y": position["y"],
                "pinned": bool(position["pinned"]),
                "missing_fields": missing_profile_fields(row),
                "color": REGION_COLORS.get(row["region"] or "", "#6d8eb3"),
            }
            nodes.append(node)
        edges = []
        duplicate_counter = Counter(
            (row["parent_company_id"], row["child_company_id"]) for row in edge_rows
        )
        for row in edge_rows:
            edges.append(
                {
                    "edge_id": row["edge_id"],
                    "parent_company_id": row["parent_company_id"],
                    "child_company_id": row["child_company_id"],
                    "change_date": row["change_date"],
                    "valid_from": row["valid_from"],
                    "valid_to": row["valid_to"],
                    "investment_shares": row["investment_shares"],
                    "child_total_shares": row["child_total_shares"],
                    "ownership_pct": row["ownership_pct"],
                    "ownership_pct_label": format_percent(row["ownership_pct"]),
                    "note": row["note"],
                    "warning_duplicate": duplicate_counter[
                        (row["parent_company_id"], row["child_company_id"])
                    ]
                    > 1,
                }
            )
        return {"as_of_date": parsed, "nodes": nodes, "edges": edges}

    def search(self, query: str, as_of_date: str) -> list[dict[str, Any]]:
        normalized = normalize_text(query)
        if not normalized:
            return []
        with self.connection() as connection:
            rows = connection.execute(
                """
                SELECT DISTINCT a.company_id,
                       p.short_name,
                       p.full_name,
                       p.company_code,
                       p.region
                FROM company_alias a
                JOIN company_profile_scd p ON p.company_id = a.company_id
                WHERE a.normalized_value LIKE ?
                  AND a.valid_from <= ?
                  AND (a.valid_to IS NULL OR a.valid_to > ?)
                  AND p.valid_from <= ?
                  AND (p.valid_to IS NULL OR p.valid_to > ?)
                ORDER BY COALESCE(p.short_name, p.full_name, p.company_code)
                """,
                (f"%{normalized}%", as_of_date, as_of_date, as_of_date, as_of_date),
            ).fetchall()
        return [dict(row) for row in rows]

    def company_detail(self, company_id: str, as_of_date: str) -> dict[str, Any] | None:
        with self.connection() as connection:
            profile = connection.execute(
                """
                SELECT * FROM company_profile_scd
                WHERE company_id = ?
                  AND valid_from <= ?
                  AND (valid_to IS NULL OR valid_to > ?)
                ORDER BY valid_from DESC
                LIMIT 1
                """,
                (company_id, as_of_date, as_of_date),
            ).fetchone()
            if not profile:
                return None
            aliases = connection.execute(
                """
                SELECT alias_type, alias_value, valid_from, valid_to
                FROM company_alias
                WHERE company_id = ?
                ORDER BY valid_from DESC, alias_type
                """,
                (company_id,),
            ).fetchall()
            history = connection.execute(
                """
                SELECT valid_from, valid_to, short_name, full_name, company_code, region, currency
                FROM company_profile_scd
                WHERE company_id = ?
                ORDER BY valid_from DESC
                """,
                (company_id,),
            ).fetchall()
        return {
            "profile": dict(profile),
            "aliases": [dict(row) for row in aliases],
            "history": [dict(row) for row in history],
        }

    def edge_detail(self, edge_id: str) -> dict[str, Any] | None:
        with self.connection() as connection:
            edge = connection.execute(
                "SELECT * FROM investment_edge_scd WHERE edge_id = ?",
                (edge_id,),
            ).fetchone()
        return dict(edge) if edge else None

    def save_layout(self, positions: list[dict[str, Any]]) -> None:
        timestamp = now_iso()
        with self.connection() as connection:
            for position in positions:
                existing = connection.execute(
                    """
                    SELECT layout_id FROM graph_layout
                    WHERE company_id = ? AND view_key = ?
                    """,
                    (position["company_id"], GRAPH_VIEW_KEY),
                ).fetchone()
                if existing:
                    connection.execute(
                        """
                        UPDATE graph_layout
                        SET x = ?, y = ?, pinned = ?, updated_at = ?
                        WHERE layout_id = ?
                        """,
                        (
                            position["x"],
                            position["y"],
                            int(bool(position.get("pinned"))),
                            timestamp,
                            existing["layout_id"],
                        ),
                    )
                else:
                    connection.execute(
                        """
                        INSERT INTO graph_layout (
                          layout_id, company_id, view_key, x, y, pinned, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            new_id("layout"),
                            position["company_id"],
                            GRAPH_VIEW_KEY,
                            position["x"],
                            position["y"],
                            int(bool(position.get("pinned"))),
                            timestamp,
                        ),
                    )
            connection.commit()

    def upsert_company(self, payload: dict[str, Any]) -> dict[str, Any]:
        valid_from = parse_date(payload["valid_from"])
        with self.connection() as connection:
            company_id = payload.get("company_id")
            if company_id:
                existing = connection.execute(
                    "SELECT company_id FROM company_identity WHERE company_id = ?",
                    (company_id,),
                ).fetchone()
                if not existing:
                    raise ValueError("company_id not found")
            else:
                company_id = new_id("cmp")
                connection.execute(
                    "INSERT INTO company_identity (company_id, created_at, archived_at) VALUES (?, ?, NULL)",
                    (company_id, now_iso()),
                )
            source_batch_id = self._create_source_batch(
                connection,
                source_type="ui_edit",
                source_name="company_edit",
                row_count=1,
                status="applied",
                note=f"company:{company_id}",
            )
            self._insert_company_profile(
                connection,
                company_id=company_id,
                valid_from=valid_from,
                company_code=payload.get("company_code"),
                short_name=payload.get("short_name"),
                full_name=payload.get("full_name"),
                main_business=payload.get("main_business"),
                symbol_code=payload.get("symbol_code"),
                region=payload.get("region"),
                currency=payload.get("currency"),
                note=payload.get("note"),
                source_batch_id=source_batch_id,
            )
            connection.commit()
        return {"company_id": company_id}

    def upsert_edge(self, payload: dict[str, Any]) -> dict[str, Any]:
        change_date = parse_date(payload["change_date"])
        ownership_pct = parse_percentage(payload.get("ownership_pct"))
        investment_shares = parse_optional_number(payload.get("investment_shares"))
        child_total_shares = parse_optional_number(payload.get("child_total_shares"))
        parent_company_id = payload["parent_company_id"]
        child_company_id = payload["child_company_id"]
        if parent_company_id == child_company_id:
            raise ValueError("parent and child company must be different")
        with self.connection() as connection:
            source_batch_id = self._create_source_batch(
                connection,
                source_type="ui_edit",
                source_name="edge_edit",
                row_count=1,
                status="applied",
                note=f"{parent_company_id}->{child_company_id}",
            )
            self._insert_edge(
                connection,
                parent_company_id=parent_company_id,
                child_company_id=child_company_id,
                change_date=change_date,
                parent_company_code_raw=payload.get("parent_company_code_raw"),
                parent_short_name_raw=payload.get("parent_short_name_raw"),
                parent_full_name_raw=payload.get("parent_full_name_raw"),
                child_company_code_raw=payload.get("child_company_code_raw"),
                child_short_name_raw=payload.get("child_short_name_raw"),
                child_full_name_raw=payload.get("child_full_name_raw"),
                investment_shares=investment_shares,
                child_total_shares=child_total_shares,
                ownership_pct=ownership_pct,
                note=payload.get("note"),
                source_batch_id=source_batch_id,
            )
            connection.commit()
        return {"status": "ok"}

    def preview_import(self, text: str) -> dict[str, Any]:
        rows = parse_tsv(text)
        if not rows:
            return {
                "mode": "unknown",
                "row_count": 0,
                "mapping": {},
                "errors": ["沒有可解析的資料列。"],
                "warnings": [],
                "infos": [],
                "changes": {},
            }
        mode, mapping = detect_import_mode(rows[0].keys())
        if mode == "company":
            return self._preview_company_import(rows, mapping)
        return self._preview_edge_import(rows, mapping)

    def apply_import(self, text: str, source_name: str = "excel paste") -> dict[str, Any]:
        preview = self.preview_import(text)
        if preview["errors"]:
            return {"status": "blocked", "preview": preview}
        rows = parse_tsv(text)
        with self.connection() as connection:
            source_batch_id = self._create_source_batch(
                connection,
                source_type="excel_paste",
                source_name=source_name,
                row_count=len(rows),
                status="applied",
                note=preview["mode"],
            )
            if preview["mode"] == "company":
                for item in preview["changes"]["company_records"]:
                    company_id = item.get("resolved_company_id")
                    if not company_id:
                        company_id = new_id("cmp")
                        connection.execute(
                            "INSERT INTO company_identity (company_id, created_at, archived_at) VALUES (?, ?, NULL)",
                            (company_id, now_iso()),
                        )
                    self._insert_company_profile(
                        connection,
                        company_id=company_id,
                        valid_from=item["valid_from"],
                        company_code=item.get("company_code"),
                        short_name=item.get("short_name"),
                        full_name=item.get("full_name"),
                        main_business=item.get("main_business"),
                        symbol_code=item.get("symbol_code"),
                        region=item.get("region"),
                        currency=item.get("currency"),
                        note=item.get("note"),
                        source_batch_id=source_batch_id,
                    )
            else:
                company_cache: dict[str, str] = {}
                for company in preview["changes"]["new_companies"]:
                    key = company["cache_key"]
                    company_id = new_id("cmp")
                    company_cache[key] = company_id
                    connection.execute(
                        "INSERT INTO company_identity (company_id, created_at, archived_at) VALUES (?, ?, NULL)",
                        (company_id, now_iso()),
                    )
                    self._insert_company_profile(
                        connection,
                        company_id=company_id,
                        valid_from=company["valid_from"],
                        company_code=company.get("company_code"),
                        short_name=company.get("short_name"),
                        full_name=company.get("full_name"),
                        main_business=None,
                        symbol_code=None,
                        region=None,
                        currency=None,
                        note="Created from import preview",
                        source_batch_id=source_batch_id,
                    )
                for edge in preview["changes"]["edge_records"]:
                    parent_company_id = edge.get("parent_company_id") or company_cache[edge["parent_cache_key"]]
                    child_company_id = edge.get("child_company_id") or company_cache[edge["child_cache_key"]]
                    self._insert_edge(
                        connection,
                        parent_company_id=parent_company_id,
                        child_company_id=child_company_id,
                        change_date=edge["change_date"],
                        parent_company_code_raw=edge.get("parent_company_code_raw"),
                        parent_short_name_raw=edge.get("parent_short_name_raw"),
                        parent_full_name_raw=edge.get("parent_full_name_raw"),
                        child_company_code_raw=edge.get("child_company_code_raw"),
                        child_short_name_raw=edge.get("child_short_name_raw"),
                        child_full_name_raw=edge.get("child_full_name_raw"),
                        investment_shares=edge.get("investment_shares"),
                        child_total_shares=edge.get("child_total_shares"),
                        ownership_pct=edge.get("ownership_pct"),
                        note=edge.get("note"),
                        source_batch_id=source_batch_id,
                    )
            connection.commit()
        return {"status": "applied", "preview": preview}

    def export_bundle(self, format_name: str) -> tuple[str, bytes, str]:
        if format_name == "db":
            target = io.BytesIO()
            with self.db_path.open("rb") as handle:
                target.write(handle.read())
            return "group-finance-notebook.db", target.getvalue(), "application/octet-stream"
        bundle = io.BytesIO()
        with self.connection() as connection, zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as archive:
            if format_name == "csv":
                manifest = {
                    "schema_version": "0.1",
                    "exported_at": now_iso(),
                    "app": "group-finance-notebook",
                    "files": [
                        "companies.csv",
                        "company_aliases.csv",
                        "company_profiles.csv",
                        "investment_edges.csv",
                        "rules.json",
                        "graph_layout.csv",
                    ],
                }
                archive.writestr(
                    "manifest.json",
                    json.dumps(manifest, ensure_ascii=False, indent=2),
                )
                self._write_csv(archive, connection, "companies.csv", "SELECT * FROM company_identity")
                self._write_csv(archive, connection, "company_aliases.csv", "SELECT * FROM company_alias")
                self._write_csv(archive, connection, "company_profiles.csv", "SELECT * FROM company_profile_scd")
                self._write_csv(archive, connection, "investment_edges.csv", "SELECT * FROM investment_edge_scd")
                self._write_csv(archive, connection, "graph_layout.csv", "SELECT * FROM graph_layout")
                rules = [dict(row) for row in connection.execute("SELECT * FROM rule_definition").fetchall()]
                archive.writestr("rules.json", json.dumps(rules, ensure_ascii=False, indent=2))
            else:
                manifest = {
                    "schema_version": "0.1",
                    "exported_at": now_iso(),
                    "app": "group-finance-notebook",
                    "files": [
                        "companies.jsonl",
                        "company_aliases.jsonl",
                        "company_profiles.jsonl",
                        "investment_edges.jsonl",
                        "rules.jsonl",
                        "graph_layout.jsonl",
                    ],
                }
                archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
                self._write_jsonl(archive, connection, "companies.jsonl", "SELECT * FROM company_identity")
                self._write_jsonl(archive, connection, "company_aliases.jsonl", "SELECT * FROM company_alias")
                self._write_jsonl(archive, connection, "company_profiles.jsonl", "SELECT * FROM company_profile_scd")
                self._write_jsonl(archive, connection, "investment_edges.jsonl", "SELECT * FROM investment_edge_scd")
                self._write_jsonl(archive, connection, "rules.jsonl", "SELECT * FROM rule_definition")
                self._write_jsonl(archive, connection, "graph_layout.jsonl", "SELECT * FROM graph_layout")
        if format_name == "csv":
            return "group-finance-notebook-csv.zip", bundle.getvalue(), "application/zip"
        return "group-finance-notebook-jsonl.zip", bundle.getvalue(), "application/zip"

    def _write_csv(
        self,
        archive: zipfile.ZipFile,
        connection: sqlite3.Connection,
        name: str,
        query: str,
    ) -> None:
        rows = connection.execute(query).fetchall()
        output = io.StringIO()
        writer = csv.writer(output)
        if rows:
            writer.writerow(rows[0].keys())
            for row in rows:
                writer.writerow([row[key] for key in row.keys()])
        archive.writestr(name, output.getvalue())

    def _write_jsonl(
        self,
        archive: zipfile.ZipFile,
        connection: sqlite3.Connection,
        name: str,
        query: str,
    ) -> None:
        lines = []
        for row in connection.execute(query).fetchall():
            lines.append(json.dumps(dict(row), ensure_ascii=False))
        archive.writestr(name, "\n".join(lines))

    def _preview_company_import(self, rows: list[dict[str, str]], mapping: dict[str, str]) -> dict[str, Any]:
        errors: list[str] = []
        warnings: list[str] = []
        infos: list[str] = []
        company_records: list[dict[str, Any]] = []
        for index, row in enumerate(rows, start=1):
            item = remap_row(row, mapping)
            valid_from_value = item.get("valid_from")
            try:
                valid_from = parse_date(valid_from_value)
            except ValueError as exc:
                errors.append(f"第 {index} 列日期錯誤：{exc}")
                continue
            if not any(item.get(field) for field in ("company_code", "short_name", "full_name")):
                errors.append(f"第 {index} 列缺少公司代碼、簡稱或全稱。")
                continue
            resolution = self.resolve_company(
                item.get("company_code") or item.get("full_name") or item.get("short_name"),
                as_of_date=valid_from,
            )
            if resolution.status == "ambiguous":
                errors.append(f"第 {index} 列公司識別衝突，需要人工確認。")
                continue
            if not item.get("full_name"):
                warnings.append(f"第 {index} 列缺少公司全稱。")
            if not item.get("region"):
                warnings.append(f"第 {index} 列缺少所在地區。")
            company_records.append(
                {
                    **item,
                    "valid_from": valid_from,
                    "resolved_company_id": resolution.company_id,
                }
            )
            infos.append(
                f"第 {index} 列將{'更新' if resolution.company_id else '新增'}公司 {item.get('short_name') or item.get('full_name') or item.get('company_code')}。"
            )
        return {
            "mode": "company",
            "row_count": len(rows),
            "mapping": mapping,
            "errors": errors,
            "warnings": warnings,
            "infos": infos,
            "changes": {"company_records": company_records},
        }

    def _preview_edge_import(self, rows: list[dict[str, str]], mapping: dict[str, str]) -> dict[str, Any]:
        errors: list[str] = []
        warnings: list[str] = []
        infos: list[str] = []
        edge_records: list[dict[str, Any]] = []
        new_companies: dict[str, dict[str, Any]] = {}
        for index, row in enumerate(rows, start=1):
            item = remap_row(row, mapping)
            try:
                change_date = parse_date(item.get("change_date"))
            except ValueError as exc:
                errors.append(f"第 {index} 列日期錯誤：{exc}")
                continue
            try:
                ownership_pct = parse_percentage(item.get("ownership_pct"))
            except ValueError as exc:
                errors.append(f"第 {index} 列持股比錯誤：{exc}")
                continue
            try:
                investment_shares = parse_optional_number(item.get("investment_shares"))
                child_total_shares = parse_optional_number(item.get("child_total_shares"))
            except ValueError as exc:
                errors.append(f"第 {index} 列股數錯誤：{exc}")
                continue
            parent = self._resolve_or_prepare_company(
                change_date=change_date,
                code=item.get("parent_company_code_raw"),
                short_name=item.get("parent_short_name_raw"),
                full_name=item.get("parent_full_name_raw"),
                role_label=f"第 {index} 列母公司",
            )
            child = self._resolve_or_prepare_company(
                change_date=change_date,
                code=item.get("child_company_code_raw"),
                short_name=item.get("child_short_name_raw"),
                full_name=item.get("child_full_name_raw"),
                role_label=f"第 {index} 列子公司",
            )
            errors.extend(parent["errors"])
            errors.extend(child["errors"])
            warnings.extend(parent["warnings"])
            warnings.extend(child["warnings"])
            if parent["cache_key"] and parent["new_company"]:
                new_companies[parent["cache_key"]] = parent["new_company"]
            if child["cache_key"] and child["new_company"]:
                new_companies[child["cache_key"]] = child["new_company"]
            if parent["company_id"] and child["company_id"] and parent["company_id"] == child["company_id"]:
                errors.append(f"第 {index} 列上層與下層公司不可相同。")
                continue
            if parent["cache_key"] and child["cache_key"] and parent["cache_key"] == child["cache_key"]:
                errors.append(f"第 {index} 列上層與下層公司不可相同。")
                continue
            if child_total_shares is not None and child_total_shares < 0:
                errors.append(f"第 {index} 列子公司總股數不可小於 0。")
            if investment_shares is not None and investment_shares < 0:
                errors.append(f"第 {index} 列投資股數不可小於 0。")
            if (
                child_total_shares
                and investment_shares is not None
                and ownership_pct is not None
                and child_total_shares > 0
            ):
                estimated = investment_shares / child_total_shares
                if not math.isclose(estimated, ownership_pct, abs_tol=0.02):
                    warnings.append(
                        f"第 {index} 列股數推算 {format_percent(estimated)} 與持股比 {format_percent(ownership_pct)} 不一致。"
                    )
            edge_records.append(
                {
                    **item,
                    "change_date": change_date,
                    "ownership_pct": ownership_pct,
                    "investment_shares": investment_shares,
                    "child_total_shares": child_total_shares,
                    "parent_company_id": parent["company_id"],
                    "child_company_id": child["company_id"],
                    "parent_cache_key": parent["cache_key"],
                    "child_cache_key": child["cache_key"],
                }
            )
            infos.append(
                f"第 {index} 列將建立 {parent['label']} -> {child['label']} {format_percent(ownership_pct)}。"
            )
        return {
            "mode": "edge",
            "row_count": len(rows),
            "mapping": mapping,
            "errors": dedupe(errors),
            "warnings": dedupe(warnings),
            "infos": infos,
            "changes": {
                "new_companies": list(new_companies.values()),
                "edge_records": edge_records,
            },
        }

    def resolve_company(self, identifier: str | None, as_of_date: str) -> ResolutionResult:
        normalized = normalize_text(identifier)
        if not normalized:
            return ResolutionResult(status="missing", reason="empty identifier")
        with self.connection() as connection:
            matches = connection.execute(
                """
                SELECT a.company_id,
                       a.alias_type,
                       a.alias_value,
                       p.short_name,
                       p.full_name,
                       p.company_code
                FROM company_alias a
                JOIN company_profile_scd p ON p.company_id = a.company_id
                WHERE a.normalized_value = ?
                  AND a.valid_from <= ?
                  AND (a.valid_to IS NULL OR a.valid_to > ?)
                  AND p.valid_from <= ?
                  AND (p.valid_to IS NULL OR p.valid_to > ?)
                """,
                (normalized, as_of_date, as_of_date, as_of_date, as_of_date),
            ).fetchall()
        if not matches:
            return ResolutionResult(status="not_found")
        grouped: dict[str, list[sqlite3.Row]] = defaultdict(list)
        for row in matches:
            grouped[row["alias_type"]].append(row)
        for alias_type in RESOLVER_ORDER:
            rows = grouped.get(alias_type)
            if not rows:
                continue
            company_ids = {row["company_id"] for row in rows}
            if len(company_ids) == 1:
                return ResolutionResult(status="resolved", company_id=rows[0]["company_id"])
            return ResolutionResult(
                status="ambiguous",
                reason=f"multiple matches by {alias_type}",
                candidates=[dict(row) for row in rows],
            )
        unique = {row["company_id"] for row in matches}
        if len(unique) == 1:
            return ResolutionResult(status="resolved", company_id=matches[0]["company_id"])
        return ResolutionResult(
            status="ambiguous",
            reason="multiple matches",
            candidates=[dict(row) for row in matches],
        )

    def _resolve_or_prepare_company(
        self,
        *,
        change_date: str,
        code: str | None,
        short_name: str | None,
        full_name: str | None,
        role_label: str,
    ) -> dict[str, Any]:
        errors: list[str] = []
        warnings: list[str] = []
        label = short_name or full_name or code or "未命名公司"
        for candidate in [code, full_name, short_name]:
            result = self.resolve_company(candidate, as_of_date=change_date)
            if result.status == "resolved":
                return {
                    "company_id": result.company_id,
                    "cache_key": None,
                    "label": label,
                    "errors": errors,
                    "warnings": warnings,
                    "new_company": None,
                }
            if result.status == "ambiguous":
                errors.append(f"{role_label} 識別衝突：{candidate}")
                return {
                    "company_id": None,
                    "cache_key": None,
                    "label": label,
                    "errors": errors,
                    "warnings": warnings,
                    "new_company": None,
                }
        if not any([code, short_name, full_name]):
            errors.append(f"{role_label} 缺少可識別欄位。")
            return {
                "company_id": None,
                "cache_key": None,
                "label": label,
                "errors": errors,
                "warnings": warnings,
                "new_company": None,
            }
        if not full_name:
            warnings.append(f"{role_label} 缺少全稱，將以現有欄位建立公司。")
        cache_key = new_company_cache_key(code, short_name, full_name)
        return {
            "company_id": None,
            "cache_key": cache_key,
            "label": label,
            "errors": errors,
            "warnings": warnings,
            "new_company": {
                "cache_key": cache_key,
                "company_code": code,
                "short_name": short_name,
                "full_name": full_name,
                "valid_from": change_date,
            },
        }

    def _insert_company_profile(
        self,
        connection: sqlite3.Connection,
        *,
        company_id: str,
        valid_from: str,
        company_code: str | None,
        short_name: str | None,
        full_name: str | None,
        main_business: str | None,
        symbol_code: str | None,
        region: str | None,
        currency: str | None,
        note: str | None,
        source_batch_id: str | None,
    ) -> None:
        timestamp = now_iso()
        connection.execute(
            """
            UPDATE company_profile_scd
            SET valid_to = ?, updated_at = ?
            WHERE company_id = ?
              AND valid_from <= ?
              AND (valid_to IS NULL OR valid_to > ?)
            """,
            (valid_from, timestamp, company_id, valid_from, valid_from),
        )
        connection.execute(
            """
            INSERT INTO company_profile_scd (
              profile_id, company_id, valid_from, valid_to, company_code, short_name, full_name,
              main_business, symbol_code, region, currency, note, created_at, updated_at, source_batch_id
            ) VALUES (?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_id("profile"),
                company_id,
                valid_from,
                company_code,
                short_name,
                full_name,
                main_business,
                symbol_code,
                region,
                currency,
                note,
                timestamp,
                timestamp,
                source_batch_id,
            ),
        )
        self._sync_core_aliases(
            connection,
            company_id=company_id,
            valid_from=valid_from,
            source_batch_id=source_batch_id,
            aliases={
                "company_code": company_code,
                "short_name": short_name,
                "full_name": full_name,
            },
        )

    def _sync_core_aliases(
        self,
        connection: sqlite3.Connection,
        *,
        company_id: str,
        valid_from: str,
        source_batch_id: str | None,
        aliases: dict[str, str | None],
    ) -> None:
        timestamp = now_iso()
        for alias_type, value in aliases.items():
            if value is None or not str(value).strip():
                continue
            normalized = normalize_text(value)
            connection.execute(
                """
                UPDATE company_alias
                SET valid_to = ?
                WHERE company_id = ?
                  AND alias_type = ?
                  AND valid_from <= ?
                  AND (valid_to IS NULL OR valid_to > ?)
                """,
                (valid_from, company_id, alias_type, valid_from, valid_from),
            )
            connection.execute(
                """
                INSERT INTO company_alias (
                  alias_id, company_id, alias_type, alias_value, normalized_value,
                  valid_from, valid_to, priority, created_at, source_batch_id
                ) VALUES (?, ?, ?, ?, ?, ?, NULL, ?, ?, ?)
                """,
                (
                    new_id("alias"),
                    company_id,
                    alias_type,
                    value.strip(),
                    normalized,
                    valid_from,
                    alias_priority(alias_type),
                    timestamp,
                    source_batch_id,
                ),
            )

    def _insert_edge(
        self,
        connection: sqlite3.Connection,
        *,
        parent_company_id: str,
        child_company_id: str,
        change_date: str,
        parent_company_code_raw: str | None,
        parent_short_name_raw: str | None,
        parent_full_name_raw: str | None,
        child_company_code_raw: str | None,
        child_short_name_raw: str | None,
        child_full_name_raw: str | None,
        investment_shares: float | None,
        child_total_shares: float | None,
        ownership_pct: float | None,
        note: str | None,
        source_batch_id: str | None,
    ) -> None:
        timestamp = now_iso()
        connection.execute(
            """
            UPDATE investment_edge_scd
            SET valid_to = ?, updated_at = ?
            WHERE parent_company_id = ?
              AND child_company_id = ?
              AND valid_from <= ?
              AND (valid_to IS NULL OR valid_to > ?)
            """,
            (
                change_date,
                timestamp,
                parent_company_id,
                child_company_id,
                change_date,
                change_date,
            ),
        )
        connection.execute(
            """
            INSERT INTO investment_edge_scd (
              edge_id, parent_company_id, child_company_id, change_date, valid_from, valid_to,
              parent_company_code_raw, parent_short_name_raw, parent_full_name_raw,
              child_company_code_raw, child_short_name_raw, child_full_name_raw,
              investment_shares, child_total_shares, ownership_pct, note, created_at, updated_at, source_batch_id
            ) VALUES (?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_id("edge"),
                parent_company_id,
                child_company_id,
                change_date,
                change_date,
                parent_company_code_raw,
                parent_short_name_raw,
                parent_full_name_raw,
                child_company_code_raw,
                child_short_name_raw,
                child_full_name_raw,
                investment_shares,
                child_total_shares,
                ownership_pct,
                note,
                timestamp,
                timestamp,
                source_batch_id,
            ),
        )

    def _create_source_batch(
        self,
        connection: sqlite3.Connection,
        *,
        source_type: str,
        source_name: str,
        row_count: int,
        status: str,
        note: str | None,
    ) -> str:
        source_batch_id = new_id("batch")
        connection.execute(
            """
            INSERT INTO source_batch (
              source_batch_id, source_type, source_name, imported_at, row_count, status, note
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (source_batch_id, source_type, source_name, now_iso(), row_count, status, note),
        )
        return source_batch_id

    def _seed_demo_data(self, connection: sqlite3.Connection) -> None:
        demo_companies = [
            {
                "company_code": "A001",
                "short_name": "Alpha Holding",
                "full_name": "Alpha Holding Ltd.",
                "main_business": "控股管理",
                "symbol_code": "ALPHA",
                "region": "台灣",
                "currency": "TWD",
                "note": "Demo root company",
                "valid_from": "2026-01-01",
            },
            {
                "company_code": "B001",
                "short_name": "Beta Tech",
                "full_name": "Beta Technology Co., Ltd.",
                "main_business": "製造",
                "symbol_code": "BETA",
                "region": "中國",
                "currency": "CNY",
                "note": "Demo subsidiary",
                "valid_from": "2026-01-01",
            },
            {
                "company_code": "C001",
                "short_name": "Gamma Ventures",
                "full_name": "Gamma Ventures Pte. Ltd.",
                "main_business": "投資",
                "symbol_code": "GAMMA",
                "region": "新加坡",
                "currency": "SGD",
                "note": "Demo investor",
                "valid_from": "2026-01-01",
            },
            {
                "company_code": "D001",
                "short_name": "Delta Services",
                "full_name": "Delta Services Ltd.",
                "main_business": "服務",
                "symbol_code": "DELTA",
                "region": "香港",
                "currency": "HKD",
                "note": "Appears in 2026-06-30 structure",
                "valid_from": "2026-06-30",
            },
        ]
        company_ids = {}
        batch_id = self._create_source_batch(
            connection,
            source_type="ui_edit",
            source_name="demo_seed",
            row_count=len(demo_companies),
            status="applied",
            note="seed companies",
        )
        for company in demo_companies:
            company_id = new_id("cmp")
            company_ids[company["company_code"]] = company_id
            connection.execute(
                "INSERT INTO company_identity (company_id, created_at, archived_at) VALUES (?, ?, NULL)",
                (company_id, now_iso()),
            )
            self._insert_company_profile(
                connection,
                company_id=company_id,
                valid_from=company["valid_from"],
                company_code=company["company_code"],
                short_name=company["short_name"],
                full_name=company["full_name"],
                main_business=company["main_business"],
                symbol_code=company["symbol_code"],
                region=company["region"],
                currency=company["currency"],
                note=company["note"],
                source_batch_id=batch_id,
            )
        layout_batch = [
            {"company_id": company_ids["A001"], "x": 120, "y": 160, "pinned": 1},
            {"company_id": company_ids["B001"], "x": 420, "y": 160, "pinned": 1},
            {"company_id": company_ids["C001"], "x": 120, "y": 340, "pinned": 1},
            {"company_id": company_ids["D001"], "x": 420, "y": 340, "pinned": 1},
        ]
        for item in layout_batch:
            connection.execute(
                """
                INSERT INTO graph_layout (layout_id, company_id, view_key, x, y, pinned, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_id("layout"),
                    item["company_id"],
                    GRAPH_VIEW_KEY,
                    item["x"],
                    item["y"],
                    item["pinned"],
                    now_iso(),
                ),
            )
        edge_batch_id = self._create_source_batch(
            connection,
            source_type="ui_edit",
            source_name="demo_seed_edges",
            row_count=3,
            status="applied",
            note="seed edges",
        )
        self._insert_edge(
            connection,
            parent_company_id=company_ids["A001"],
            child_company_id=company_ids["B001"],
            change_date="2026-03-31",
            parent_company_code_raw="A001",
            parent_short_name_raw="Alpha Holding",
            parent_full_name_raw="Alpha Holding Ltd.",
            child_company_code_raw="B001",
            child_short_name_raw="Beta Tech",
            child_full_name_raw="Beta Technology Co., Ltd.",
            investment_shares=600,
            child_total_shares=1000,
            ownership_pct=0.6,
            note="Phase 1 acceptance sample",
            source_batch_id=edge_batch_id,
        )
        self._insert_edge(
            connection,
            parent_company_id=company_ids["A001"],
            child_company_id=company_ids["B001"],
            change_date="2026-06-30",
            parent_company_code_raw="A001",
            parent_short_name_raw="Alpha Holding",
            parent_full_name_raw="Alpha Holding Ltd.",
            child_company_code_raw="B001",
            child_short_name_raw="Beta Tech",
            child_full_name_raw="Beta Technology Co., Ltd.",
            investment_shares=800,
            child_total_shares=1000,
            ownership_pct=0.8,
            note="Updated holding ratio",
            source_batch_id=edge_batch_id,
        )
        self._insert_edge(
            connection,
            parent_company_id=company_ids["C001"],
            child_company_id=company_ids["D001"],
            change_date="2026-06-30",
            parent_company_code_raw="C001",
            parent_short_name_raw="Gamma Ventures",
            parent_full_name_raw="Gamma Ventures Pte. Ltd.",
            child_company_code_raw="D001",
            child_short_name_raw="Delta Services",
            child_full_name_raw="Delta Services Ltd.",
            investment_shares=1000,
            child_total_shares=1000,
            ownership_pct=1.0,
            note="New 100% owned subsidiary",
            source_batch_id=edge_batch_id,
        )

    def _compute_positions(
        self,
        profile_rows: list[sqlite3.Row],
        edge_rows: list[sqlite3.Row],
        layouts: dict[str, dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        company_ids = [row["company_id"] for row in profile_rows]
        known = {
            company_id: {
                "x": float(layouts[company_id]["x"]),
                "y": float(layouts[company_id]["y"]),
                "pinned": int(layouts[company_id]["pinned"]),
            }
            for company_id in company_ids
            if company_id in layouts
        }
        adjacency: dict[str, list[str]] = defaultdict(list)
        indegree = {company_id: 0 for company_id in company_ids}
        for row in edge_rows:
            parent = row["parent_company_id"]
            child = row["child_company_id"]
            if parent in indegree and child in indegree:
                adjacency[parent].append(child)
                indegree[child] += 1
        roots = [company_id for company_id, degree in indegree.items() if degree == 0]
        if not roots:
            roots = company_ids[:]
        level_map: dict[str, int] = {}
        queue = deque((root, 0) for root in roots)
        while queue:
            company_id, level = queue.popleft()
            if company_id in level_map and level_map[company_id] <= level:
                continue
            level_map[company_id] = level
            for child in adjacency.get(company_id, []):
                queue.append((child, level + 1))
        for company_id in company_ids:
            level_map.setdefault(company_id, 0)
        grouped: dict[int, list[str]] = defaultdict(list)
        for company_id, level in level_map.items():
            grouped[level].append(company_id)
        positions = {}
        for level in sorted(grouped):
            group = grouped[level]
            group.sort()
            for index, company_id in enumerate(group):
                if company_id in known:
                    positions[company_id] = known[company_id]
                    continue
                positions[company_id] = {
                    "x": 120 + level * 300,
                    "y": 140 + index * 170,
                    "pinned": 0,
                }
        return positions


def parse_tsv(text: str) -> list[dict[str, str]]:
    cleaned = text.strip()
    if not cleaned:
        return []
    reader = csv.DictReader(io.StringIO(cleaned), delimiter="\t")
    return [{key.strip(): (value or "").strip() for key, value in row.items()} for row in reader]


def detect_import_mode(headers: Any) -> tuple[str, dict[str, str]]:
    header_list = list(headers)
    normalized_headers = {normalize_text(header): header for header in header_list}
    edge_mapping = find_mapping(normalized_headers, EDGE_FIELD_ALIASES)
    if any(field.startswith("parent_") or field.startswith("child_") for field in edge_mapping):
        return "edge", edge_mapping
    company_mapping = find_mapping(normalized_headers, COMPANY_FIELD_ALIASES)
    return "company", company_mapping


def find_mapping(
    normalized_headers: dict[str, str],
    aliases: dict[str, list[str]],
) -> dict[str, str]:
    mapping = {}
    for field, candidates in aliases.items():
        for alias in candidates:
            normalized = normalize_text(alias)
            if normalized in normalized_headers:
                mapping[field] = normalized_headers[normalized]
                break
    return mapping


def remap_row(row: dict[str, str], mapping: dict[str, str]) -> dict[str, str]:
    result = {}
    for target_field, source_field in mapping.items():
        result[target_field] = row.get(source_field, "").strip()
    return result


def parse_date(value: str | None) -> str:
    if value is None:
        raise ValueError("缺少日期")
    cleaned = str(value).strip()
    if not cleaned:
        raise ValueError("缺少日期")
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y/%-m/%-d"):
        try:
            return datetime.strptime(cleaned, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    parts = cleaned.replace("/", "-").split("-")
    if len(parts) == 3 and all(part.isdigit() for part in parts):
        year, month, day = (int(part) for part in parts)
        return datetime(year, month, day).strftime("%Y-%m-%d")
    raise ValueError(f"無法解析日期：{value}")


def parse_percentage(value: Any) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    cleaned = str(value).strip().replace(",", "")
    if cleaned.endswith("%"):
        number = float(cleaned[:-1]) / 100
    else:
        number = float(cleaned)
        if number > 1:
            number = number / 100
    if number < 0 or number > 1:
        raise ValueError("持股比需介於 0 到 1 之間")
    return round(number, 6)


def parse_optional_number(value: Any) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    cleaned = str(value).strip().replace(",", "")
    return float(cleaned)


def normalize_text(value: str | None) -> str:
    if value is None:
        return ""
    text = str(value).strip().lower()
    return "".join(text.split())


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def alias_priority(alias_type: str) -> int:
    priorities = {
        "company_code": 10,
        "full_name": 20,
        "short_name": 30,
        "former_name": 40,
        "custom": 50,
    }
    return priorities.get(alias_type, 100)


def format_percent(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value * 100:.1f}%"


def missing_profile_fields(row: sqlite3.Row | dict[str, Any]) -> list[str]:
    missing = []
    for field in ("full_name", "region", "currency"):
        if not row[field]:
            missing.append(field)
    return missing


def new_company_cache_key(code: str | None, short_name: str | None, full_name: str | None) -> str:
    return "|".join(
        [normalize_text(code), normalize_text(short_name), normalize_text(full_name)]
    )


def dedupe(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result
