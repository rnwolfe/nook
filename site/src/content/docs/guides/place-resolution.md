---
title: Place resolution
description: Resolve a fuzzy location string to a precise place ID, coordinates, and bounding box before searching.
---

`nook place search <query>` turns a location string into `{ placeId, coordinates, bbox }` — resolve a place first, then pass its `--place-id` or `--bbox` to `nook search` for precise results.

<!-- TODO(harvest-docs): place resolution flow, the returned shape, and chaining place → search. -->
