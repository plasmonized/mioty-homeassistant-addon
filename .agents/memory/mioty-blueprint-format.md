---
name: mioty Blueprint format
description: Quirks of the official mioty Blueprint decoder JSON format and safe evaluation rules
---

# mioty Blueprint format quirks

- `component.size` is in **bits** (4-bit nibbles common in version headers), `littleEndian: false` = MSB-first big-endian.
- `uplink[].payload` entries may carry their own `condition` (e.g. `$radar_peaks >= 1`) and `hidden` — both at field level, not only on the component. Conditional fields must be skipped entirely (no bits consumed) when the condition is false.
- Conditions/funcs use **JavaScript syntax**: `&&`, `||`, `!`. Translate to Python (`and`/`or`/`not`) before evaluating; use regex `!(?!=)` so `!=` survives.
- `$fieldname` references earlier decoded fields by their payload `name` (not component name); replace longest names first.
- Metadata is under `meta.name` / `meta.vendor` / `meta.description`, device type under `typeEui`.

**Why:** Blueprints are user-uploadable — evaluating their expressions with `eval()` is remote code execution.
**How to apply:** always use `safe_eval_expr` (AST whitelist: literals, arithmetic, bitwise, comparisons, boolops) in payload_decoder.py; never reintroduce `eval` there.

Built-in Sentinum blueprints (Eos, Febris, Aion, Apollon, Hyperion, Juno) ship in `app/builtin_decoders/` and are auto-copied into the decoder dir at startup; registry entries refresh when file mtime is newer than `created_at`.
