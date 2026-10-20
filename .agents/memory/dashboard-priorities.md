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

The user approved the compact refreshed dashboard hierarchy, but rejected
restyling only its upper area while leaving the rest of the application visually
inconsistent. All pages must share Sentinum's orange and dark-gray color world.

**Why:** The user explicitly requested the colors of sentinum.de and consistency
across the whole interface, not isolated dashboard styling.

**How to apply:** Extend future visual changes to related tables, forms,
navigation, dialogs and lower-page content. Preserve the operational hierarchy
and functional behavior rather than introducing unrelated dashboard concepts.

Do not put a Sentinum logo in the upper-right application header. In the
Sentinum Cloud settings, use the light/orange logo on black, not a white tile.

**Why:** The user wants less prominent Sentinum branding and explicitly requested
these two logo treatments.

**How to apply:** Keep global navigation/header unbranded by Sentinum; reserve
its logo for the actual Cloud integration.
