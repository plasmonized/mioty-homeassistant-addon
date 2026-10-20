---
name: Embedded preview verification
description: Direct screenshots do not verify that the Replit editor can embed the app.
---

A successful direct page screenshot or HTTP 200 does not prove that the editor's
embedded preview loads. Check framing policy on the proxied development URL when
the user reports a blank preview despite a healthy server.

**Why:** The user twice reported a blank preview while direct screenshots and
API requests succeeded. A same-origin-only framing header blocked embedding
across the editor and development origins.

**How to apply:** Distinguish direct rendering from iframe compatibility. Allow
only trusted editor parents in development, preserve the normal Home Assistant
framing protection, and verify the actual proxied response headers rather than
repeatedly restarting a healthy service.
