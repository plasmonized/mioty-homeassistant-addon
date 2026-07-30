---
name: Dual sensor metadata stores
description: Two separate persistence files for sensor metadata and the EUI case rule
---

# Dual sensor metadata stores

- Sensors page saves via `PUT /api/sensor-config/<eui>` → `sensor_configs.json` (uppercase EUI keys).
- Dashboard saves via `POST /api/sensors/<eui>/metadata` → `manual_sensor_metadata.json`.
- The list endpoint merges manual metadata into configs with a case-sensitive dict lookup.

**Why:** Mixed-case EUI keys in `manual_sensor_metadata.json` made dashboard-entered metadata "disappear" — the uppercase lookup missed lowercase keys.
**How to apply:** any code path touching these JSON files must uppercase EUI keys on save AND normalize keys to uppercase on load; also dedupe old mixed-case entries when writing.
