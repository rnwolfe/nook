"""The output contract: data to stdout, chatter to stderr, stable JSON, --format,
--select projection, --limit bounding. See contract.md §1, §6.

Reads emit a stable ENVELOPE (schemaVersion / scope / data / nextCursor / meta) via emit_read;
--select + --limit apply to the `data` payload. Human formats (plain/tsv) render just the data
payload for readability and send envelope metadata to stderr. See spec.md §Output schema."""

from __future__ import annotations

import json
import sys
from typing import Any

SCHEMA_VERSION = 1


class Writer:
    def __init__(self, fmt: str = "plain", color: bool = False, limit: int = 50,
                 select: list[str] | None = None, stdout=None, stderr=None):
        self.fmt = fmt
        self.color = color
        self.limit = limit
        self.select = select or []
        self.stdout = stdout or sys.stdout
        self.stderr = stderr or sys.stderr

    def info(self, msg: str) -> None:
        print(msg, file=self.stderr)

    def emit(self, value: Any) -> None:
        """Emit a raw value (non-enveloped) — used by schema/version/agent/doctor."""
        g = json.loads(json.dumps(value, default=str))
        if self.select:
            g = _apply_select(g, self.select)
        g = self._apply_limit(g)
        if self.fmt == "json":
            self.emit_json(g)
        elif self.fmt == "tsv":
            self._render(g, "\t", aligned=False)
        else:
            self._render(g, "\t", aligned=True)

    def emit_read(self, data: Any, scope: dict, next_cursor: str | None = None,
                  meta_extra: dict | None = None) -> None:
        """Emit a read result wrapped in the stable envelope. --select projects fields on each
        item; --limit bounds a list payload with a loud truncation note (contract §6)."""
        g = json.loads(json.dumps(data, default=str))
        if self.select:
            g = _apply_select(g, self.select)
        truncated = False
        total = len(g) if isinstance(g, list) else None
        if isinstance(g, list) and self.limit > 0 and len(g) > self.limit:
            truncated = True
            self.info(f"note: output truncated to {self.limit} of {len(g)} items "
                      f"(use --limit to change, or page with --cursor)")
            g = g[: self.limit]
        meta = {"count": len(g) if isinstance(g, list) else 1, "truncated": truncated}
        if total is not None:
            meta["total"] = total
        if meta_extra:
            meta.update(meta_extra)
        envelope = {
            "schemaVersion": SCHEMA_VERSION,
            "scope": scope,
            "data": g,
            "nextCursor": next_cursor,
            "meta": meta,
        }
        if self.fmt == "json":
            self.emit_json(envelope)
        else:
            # Human path: render only the data payload; envelope metadata to stderr.
            self._render(g, "\t", aligned=(self.fmt != "tsv"))
            if next_cursor:
                self.info(f"note: more results available (--cursor {next_cursor})")

    def emit_json(self, value: Any) -> None:
        print(json.dumps(value, indent=2, ensure_ascii=False), file=self.stdout)

    def _apply_limit(self, g: Any) -> Any:
        if self.limit > 0 and isinstance(g, list) and len(g) > self.limit:
            self.info(f"note: output truncated to {self.limit} of {len(g)} items "
                      f"(use --limit to change)")
            return g[: self.limit]
        return g

    def _render(self, g: Any, sep: str, aligned: bool) -> None:
        if isinstance(g, list):
            if not g:
                return
            if isinstance(g[0], dict):
                headers = _union_keys(g)
                rows = [[_scalar(row.get(h)) for h in headers] for row in g]
                self._write_table([headers] + rows, sep, aligned)
            else:
                for e in g:
                    print(_scalar(e), file=self.stdout)
        elif isinstance(g, dict):
            rows = [[k, _scalar(g[k])] for k in sorted(g)]
            self._write_table(rows, sep, aligned)
        else:
            print(_scalar(g), file=self.stdout)

    def _write_table(self, rows: list[list[str]], sep: str, aligned: bool) -> None:
        if aligned and rows:
            widths = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]
            for r in rows:
                print("  ".join(c.ljust(widths[i]) for i, c in enumerate(r)).rstrip(),
                      file=self.stdout)
        else:
            for r in rows:
                print(sep.join(r), file=self.stdout)


def _apply_select(g: Any, sel: list[str]) -> Any:
    if isinstance(g, list):
        return [_select_obj(e, sel) for e in g]
    return _select_obj(g, sel)


def _select_obj(e: Any, sel: list[str]) -> Any:
    if not isinstance(e, dict):
        return e
    out: dict[str, Any] = {}
    for p in sel:
        p = p.strip()
        if not p:
            continue
        ok, v = _get_path(e, p)
        if ok:
            out[p] = v
    return out


def _get_path(m: dict, path: str):
    cur: Any = m
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return False, None
        cur = cur[part]
    return True, cur


def _union_keys(arr: list[dict]) -> list[str]:
    keys: set[str] = set()
    for e in arr:
        if isinstance(e, dict):
            keys.update(e.keys())
    return sorted(keys)


def _scalar(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (str, int, float)):
        return str(v)
    return json.dumps(v, ensure_ascii=False)
