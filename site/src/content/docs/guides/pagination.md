---
title: Pagination
description: Page through results with the opaque cursor echoed back as nextCursor.
---

Lists return an opaque `nextCursor`; pass it back with `--cursor` to fetch the next page. When `nextCursor` is absent, you've reached the end of the results.

<!-- TODO(harvest-docs): the cursor model, when nextCursor is null, and stable pagination for agents. -->
