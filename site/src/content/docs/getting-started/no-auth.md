---
title: No auth
description: nook never logs in — it reads public, logged-out Airbnb pages, and every read says so in its scope.
---

There are no credentials to configure. nook reads only public, logged-out pages, and every read carries `scope: { auth: "none", corpus: "public-logged-out" }` as a standing reminder that this is the public view, not a complete corpus.

<!-- TODO(harvest-docs): explain the no-auth stance, the scope object, and what "public-logged-out corpus" means for completeness/expectations. -->
