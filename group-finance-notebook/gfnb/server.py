from __future__ import annotations

import json
import mimetypes
import shutil
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .service import NotebookService


STATIC_DIR = Path(__file__).with_name("static")


class NotebookRequestHandler(BaseHTTPRequestHandler):
    server_version = "GroupFinanceNotebook/0.1"

    @property
    def notebook(self) -> NotebookService:
        return self.server.notebook_service  # type: ignore[attr-defined]

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/" or path == "/index.html":
            self._serve_file(STATIC_DIR / "index.html")
            return
        if path.startswith("/static/"):
            file_path = STATIC_DIR / path.removeprefix("/static/")
            self._serve_file(file_path)
            return
        if path == "/api/summary":
            as_of = self._query_value(parsed.query, "as_of", default=self._default_as_of())
            self._json(self.notebook.summary(as_of))
            return
        if path == "/api/graph":
            as_of = self._query_value(parsed.query, "as_of", default=self._default_as_of())
            self._json(self.notebook.graph(as_of))
            return
        if path == "/api/search":
            query = self._query_value(parsed.query, "q", default="")
            as_of = self._query_value(parsed.query, "as_of", default=self._default_as_of())
            self._json({"results": self.notebook.search(query, as_of)})
            return
        if path.startswith("/api/company/"):
            company_id = path.rsplit("/", 1)[-1]
            as_of = self._query_value(parsed.query, "as_of", default=self._default_as_of())
            detail = self.notebook.company_detail(company_id, as_of)
            if not detail:
                self._json({"error": "not found"}, status=404)
                return
            self._json(detail)
            return
        if path.startswith("/api/edge/"):
            edge_id = path.rsplit("/", 1)[-1]
            detail = self.notebook.edge_detail(edge_id)
            if not detail:
                self._json({"error": "not found"}, status=404)
                return
            self._json(detail)
            return
        if path == "/api/export/csv":
            self._send_download(*self.notebook.export_bundle("csv"))
            return
        if path == "/api/export/txt":
            self._send_download(*self.notebook.export_bundle("txt"))
            return
        if path == "/api/export/db":
            self._send_download(*self.notebook.export_bundle("db"))
            return
        self._json({"error": "not found"}, status=404)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        body = self._read_json()
        if path == "/api/company":
            try:
                payload = self.notebook.upsert_company(body)
            except ValueError as exc:
                self._json({"error": str(exc)}, status=400)
                return
            self._json(payload, status=201)
            return
        if path == "/api/edge":
            try:
                payload = self.notebook.upsert_edge(body)
            except ValueError as exc:
                self._json({"error": str(exc)}, status=400)
                return
            self._json(payload, status=201)
            return
        if path == "/api/layout":
            self.notebook.save_layout(body.get("positions", []))
            self._json({"status": "ok"})
            return
        if path == "/api/import/preview":
            self._json(self.notebook.preview_import(body.get("text", "")))
            return
        if path == "/api/import/apply":
            result = self.notebook.apply_import(
                body.get("text", ""),
                source_name=body.get("source_name", "excel paste"),
            )
            self._json(result, status=201 if result["status"] == "applied" else 400)
            return
        if path == "/api/reset-demo":
            self.notebook.reset_demo_data()
            self._json({"status": "ok"})
            return
        self._json({"error": "not found"}, status=404)

    def _default_as_of(self) -> str:
        dates = self.notebook.available_dates()
        return dates[-1] if dates else "2026-06-30"

    def _query_value(self, query: str, key: str, default: str) -> str:
        return parse_qs(query).get(key, [default])[0]

    def _json(self, payload: dict, status: int = 200) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _read_json(self) -> dict:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(content_length) if content_length else b"{}"
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8"))

    def _serve_file(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            self._json({"error": "not found"}, status=404)
            return
        mime_type, _ = mimetypes.guess_type(path.name)
        mime_type = mime_type or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", f"{mime_type}; charset=utf-8")
        self.send_header("Content-Length", str(path.stat().st_size))
        self.end_headers()
        with path.open("rb") as handle:
            shutil.copyfileobj(handle, self.wfile)

    def _send_download(self, name: str, content: bytes, mime_type: str) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mime_type)
        self.send_header("Content-Disposition", f'attachment; filename="{name}"')
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


def serve(service: NotebookService, host: str, port: int) -> None:
    httpd = ThreadingHTTPServer((host, port), NotebookRequestHandler)
    httpd.notebook_service = service  # type: ignore[attr-defined]
    print(f"Group Finance Notebook listening on http://{host}:{port}")
    httpd.serve_forever()
