"""Prompt-injection hardening (contract §8).

Free text returned by Airbnb — listing titles, descriptions, host bios, house rules, review
text — is authored by third parties and must be treated as DATA, never as instructions to a
downstream agent. In agent mode (the default), we fence such fields with explicit begin/end
markers so an agent doesn't execute instructions embedded in fetched content. `--no-wrap` (human
path) disables it.
"""

from __future__ import annotations

from typing import Any

_BEGIN = "‹untrusted-airbnb-content›"  # ‹untrusted-airbnb-content›
_END = "‹/untrusted-airbnb-content›"


def wrap(text: str | None) -> str | None:
    """Fence a single free-text value. None/empty passes through unchanged."""
    if not text:
        return text
    return f"{_BEGIN} {text} {_END}"


def fence_fields(obj: Any, paths: list[str], enabled: bool) -> Any:
    """Return a copy of `obj` with each dot-path free-text field wrapped, when `enabled`.

    Paths may traverse dicts and lists (a list segment wraps the field on every element), e.g.
    "description", "host.name", "reviews.text". Missing paths are skipped silently.
    """
    if not enabled:
        return obj
    for path in paths:
        _wrap_path(obj, path.split("."))
    return obj


def _wrap_path(node: Any, parts: list[str]) -> None:
    if node is None or not parts:
        return
    head, rest = parts[0], parts[1:]
    if isinstance(node, list):
        for el in node:
            _wrap_path(el, parts)
        return
    if not isinstance(node, dict) or head not in node:
        return
    if not rest:
        if isinstance(node[head], str):
            node[head] = wrap(node[head])
        return
    _wrap_path(node[head], rest)
