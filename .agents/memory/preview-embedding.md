---
name: Embedded preview verification
description: Direct screenshots do not verify that the Replit editor can embed the app.
---

A successful direct page screenshot or HTTP 200 does not prove that the editor's
embedded preview loads. Check framing policy on the proxied development URL when
the user reports a blank preview despite a healthy server.

**Why:** The user reported a blank preview while direct screenshots and API
requests succeeded. A framing header was initially suspected, but the user's
screenshot later showed the external development URL incorrectly using :5000.
That URL returned 502 while the same host without an explicit port returned 200.
Do not treat a plausible framing issue as the established cause without evidence.

**How to apply:** Distinguish direct rendering from iframe compatibility. Allow
only trusted editor parents in development, preserve the normal Home Assistant
framing protection, and verify the actual proxied response headers rather than
repeatedly restarting a healthy service.
Also compare the preview address with the external port mapping: a service
listening internally on 5000 and forwarded externally on 80 is reached through
the normal HTTPS development URL, not by appending :5000.
