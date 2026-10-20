---
name: Dashboard priorities
description: User priorities for the compact operational start-page overview.
---

The start dashboard should prioritize active sensors across all radio
technologies (including mioty), active base stations within the mioty and LoRaWAN
groups, and connection health for Service Center, Sentinum Cloud and the MQTT
connections, including Home Assistant. Decoder inventory is not a primary metric.
Keep this overview compact, not overloaded.

**Why:** The user described the old dashboard as outdated and explicitly requested
these operational priorities instead of its decoder-focused counters.

**How to apply:** Preserve this hierarchy when extending the dashboard. Overall
activity must include all technologies rather than silently becoming a mioty-only
or list-filtered count.
