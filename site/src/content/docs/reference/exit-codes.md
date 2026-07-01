---
title: Exit codes
description: The stable exit-code table an agent can branch on — 0 ok, 3 empty, 5 not found, 7 rate-limited, 20 upstream drift, and more.
---

`0` ok · `2` usage · `3` empty · `5` not found · `7` rate limited/blocked · `8` retryable · `10` config · `13` input required · `20` upstream drift · `130` cancelled. Codes `4`/`6`/`12` are N/A for this read-only tool.

<!-- TODO(harvest-docs): the full exit-code table with meanings and agent branching guidance. Source of truth: `nook schema --json`. -->
