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
Accept customer-scoped topic shortcuts from onboarding instructions, but resolve
them to telemetry-only subscriptions rather than passing broad `#` filters through.

Sources:
- https://docs.sentinum.de/en/new-integration-guide
- https://raw.githack.com/bellaminemo81172/sentinum_documentation/8cf19341ffea6af3d72dbc8f46a07207557abc12/Datahub_User_Guide/Datahub_user_Guide_EN.pdf

## Product scope

The user states: „die sentinumcloud kann alle sensordaten streamen“.
Do not describe the cloud itself as cellular-only in headings or branding.

**Why:** The user explicitly corrected the cellular-only heading and requested
the Sentinum logo instead of a generic “S”.

**How to apply:** Distinguish the cloud's capabilities from any currently
implemented transport filtering; changing branding alone does not expand ingestion.

## Fixed connection address

The user wants the Sentinum broker and TLS port to be fixed, not editable;
only credentials and the customer topic should be entered.

**Why:** The user states that Sentinum has one cloud address and requested
non-editable broker and TLS-port fields.

**How to apply:** Keep the endpoint `broker.sentinum.de:8883` fixed in the
configuration UI and server validation.
