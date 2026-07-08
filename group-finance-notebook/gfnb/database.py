from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path


SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS company_identity (
      company_id TEXT PRIMARY KEY,
      created_at TEXT NOT NULL,
      archived_at TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS company_alias (
      alias_id TEXT PRIMARY KEY,
      company_id TEXT NOT NULL,
      alias_type TEXT NOT NULL,
      alias_value TEXT NOT NULL,
      normalized_value TEXT NOT NULL,
      valid_from TEXT NOT NULL,
      valid_to TEXT,
      priority INTEGER NOT NULL DEFAULT 100,
      created_at TEXT NOT NULL,
      source_batch_id TEXT,
      FOREIGN KEY (company_id) REFERENCES company_identity(company_id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS company_profile_scd (
      profile_id TEXT PRIMARY KEY,
      company_id TEXT NOT NULL,
      valid_from TEXT NOT NULL,
      valid_to TEXT,
      company_code TEXT,
      short_name TEXT,
      full_name TEXT,
      main_business TEXT,
      symbol_code TEXT,
      region TEXT,
      currency TEXT,
      note TEXT,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      source_batch_id TEXT,
      FOREIGN KEY (company_id) REFERENCES company_identity(company_id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS investment_edge_scd (
      edge_id TEXT PRIMARY KEY,
      parent_company_id TEXT NOT NULL,
      child_company_id TEXT NOT NULL,
      change_date TEXT NOT NULL,
      valid_from TEXT NOT NULL,
      valid_to TEXT,
      parent_company_code_raw TEXT,
      parent_short_name_raw TEXT,
      parent_full_name_raw TEXT,
      child_company_code_raw TEXT,
      child_short_name_raw TEXT,
      child_full_name_raw TEXT,
      investment_shares NUMERIC,
      child_total_shares NUMERIC,
      ownership_pct NUMERIC,
      note TEXT,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      source_batch_id TEXT,
      FOREIGN KEY (parent_company_id) REFERENCES company_identity(company_id),
      FOREIGN KEY (child_company_id) REFERENCES company_identity(company_id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS source_batch (
      source_batch_id TEXT PRIMARY KEY,
      source_type TEXT NOT NULL,
      source_name TEXT,
      imported_at TEXT NOT NULL,
      row_count INTEGER,
      status TEXT NOT NULL,
      note TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS graph_layout (
      layout_id TEXT PRIMARY KEY,
      company_id TEXT NOT NULL,
      view_key TEXT NOT NULL,
      x NUMERIC NOT NULL,
      y NUMERIC NOT NULL,
      pinned INTEGER NOT NULL DEFAULT 0,
      updated_at TEXT NOT NULL,
      FOREIGN KEY (company_id) REFERENCES company_identity(company_id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS rule_definition (
      rule_id TEXT PRIMARY KEY,
      rule_type TEXT NOT NULL,
      name TEXT NOT NULL,
      config_json TEXT NOT NULL,
      enabled INTEGER NOT NULL DEFAULT 1,
      priority INTEGER NOT NULL DEFAULT 100,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS financial_metric_scd (
      metric_record_id TEXT PRIMARY KEY,
      company_id TEXT NOT NULL,
      period_end TEXT NOT NULL,
      metric_code TEXT NOT NULL,
      metric_name TEXT NOT NULL,
      amount NUMERIC,
      currency TEXT,
      valid_from TEXT NOT NULL,
      valid_to TEXT,
      created_at TEXT NOT NULL,
      source_batch_id TEXT,
      FOREIGN KEY (company_id) REFERENCES company_identity(company_id)
    );
    """,
]


DEFAULT_RULES = [
    {
        "rule_id": "rule_parser_ownership_pct",
        "rule_type": "parser",
        "name": "ownership_pct aliases",
        "config_json": json.dumps(
            {
                "field": "ownership_pct",
                "aliases": ["占股比", "持股比例", "持股比", "%"],
                "parser": "percentage",
            },
            ensure_ascii=False,
        ),
        "priority": 10,
    },
    {
        "rule_id": "rule_resolver_order",
        "rule_type": "resolver",
        "name": "default resolver order",
        "config_json": json.dumps(
            {
                "priority": [
                    "company_code",
                    "full_name",
                    "short_name",
                    "former_name",
                    "custom",
                ]
            },
            ensure_ascii=False,
        ),
        "priority": 10,
    },
    {
        "rule_id": "rule_edge_default",
        "rule_type": "edge",
        "name": "investment edge",
        "config_json": json.dumps(
            {
                "edge_type": "investment",
                "direction": "parent_to_child",
                "label": "ownership_pct",
                "source_table": "investment_edge_scd",
            },
            ensure_ascii=False,
        ),
        "priority": 10,
    },
    {
        "rule_id": "rule_style_region_fill",
        "rule_type": "style",
        "name": "fill by region",
        "config_json": json.dumps(
            {
                "rule_type": "style",
                "target": "company_node",
                "field": "region",
                "style": "fill_color_by_category",
            },
            ensure_ascii=False,
        ),
        "priority": 10,
    },
    {
        "rule_id": "rule_validation_ownership_range",
        "rule_type": "validation",
        "name": "ownership range",
        "config_json": json.dumps(
            {
                "field": "ownership_pct",
                "rule": "between",
                "min": 0,
                "max": 1,
            },
            ensure_ascii=False,
        ),
        "priority": 10,
    },
]


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def connect(db_path: Path | str) -> sqlite3.Connection:
    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db(db_path: Path | str) -> None:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = connect(path)
    try:
        for statement in SCHEMA_STATEMENTS:
            connection.execute(statement)
        ensure_default_rules(connection)
        connection.commit()
    finally:
        connection.close()


def ensure_default_rules(connection: sqlite3.Connection) -> None:
    existing = {
        row["rule_id"]
        for row in connection.execute("SELECT rule_id FROM rule_definition").fetchall()
    }
    timestamp = now_iso()
    for rule in DEFAULT_RULES:
        if rule["rule_id"] in existing:
            continue
        connection.execute(
            """
            INSERT INTO rule_definition (
              rule_id, rule_type, name, config_json, enabled, priority, created_at, updated_at
            ) VALUES (?, ?, ?, ?, 1, ?, ?, ?)
            """,
            (
                rule["rule_id"],
                rule["rule_type"],
                rule["name"],
                rule["config_json"],
                rule["priority"],
                timestamp,
                timestamp,
            ),
        )
