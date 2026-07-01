---
title: Upstream drift (exit 20)
description: When Airbnb changes its internals, nook returns exit 20 — distinct from a rate limit — and the fix is to update nook.
---

Exit `20` means Airbnb changed its internals and nook can no longer parse a response — distinct from a rate limit. The fix is to update nook: `nook version --check`.

<!-- TODO(harvest-docs): what upstream drift is, how it differs from exit 7, and how to report/resolve it. -->
