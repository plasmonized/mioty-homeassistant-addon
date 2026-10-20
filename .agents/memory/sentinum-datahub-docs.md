---
name: Sentinum Datahub documentation differences
description: Conflicting legacy and Datahub 2.0 MQTT instructions; prefer the newer guide for transport security and topics.
---

Use the Datahub 2.0 guide (23 June 2026) for connection security and topic
permissions, not only the older integration page.

**Why:** Sentinum's older web examples still mention plaintext port 1883,
`data.sentinum.de`, and broad subscriptions. The newer guide requires TLS on
8883, uses `broker.sentinum.de`, and warns that subscribing to prohibited
control topics can disconnect a client. The legacy `devices` telemetry mirror
is available alongside the newer `datahub` topic tree.

**How to apply:** Keep subscriptions limited to customer telemetry `/up`.
Do not weaken TLS or broaden subscriptions to fix a login/topic error without
checking the current account permissions and newer documentation.

Sources:
- https://docs.sentinum.de/en/new-integration-guide
- https://raw.githack.com/bellaminemo81172/sentinum_documentation/8cf19341ffea6af3d72dbc8f46a07207557abc12/Datahub_User_Guide/Datahub_user_Guide_EN.pdf
