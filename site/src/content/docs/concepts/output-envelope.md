---
title: The output envelope
description: Every read returns a stable envelope — schemaVersion, scope, data, nextCursor, and meta.
---

Reads return a stable shape: `{ schemaVersion, scope, data, nextCursor, meta }`. stdout is data, stderr is notes and errors; `--json` (or `--format json`) selects machine output. The `scope` object records `auth` and `corpus` on every response.

<!-- TODO(harvest-docs): field-by-field envelope reference, the scope object, stdout/stderr split, and why the shape is stable. Written from src/nook/SKILL.md. -->
