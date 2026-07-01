---
title: Read-only & booking-excluded
description: nook never mutates and never books — mutation flags are inert no-ops, and transactions are out of scope by design.
---

No command changes Airbnb state. `--allow-mutations`, `--dry-run`, `--yes`, and `--force` exist only for contract uniformity and are inert no-ops. Booking, paying, and messaging are excluded by design — nook surfaces availability; you book like a human.

<!-- TODO(harvest-docs): the read-only guarantee, why the mutation flags are inert, and the booking-excluded scope decision. -->
