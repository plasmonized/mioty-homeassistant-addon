---
name: paho wait_for_publish deadlock
description: Never call wait_for_publish from inside paho-mqtt callbacks (on_message etc.)
---
Rule: QoS-1 publishes with `wait_for_publish()` must not run on the paho network thread (inside on_message/on_connect callbacks) — it blocks the loop, so the PUBACK can never arrive and the wait always times out.

**Why:** Observed live: adding PUBACK confirmation to a shared publish helper made callback-context response publishes falsely report "message lost".

**How to apply:** Shared publish helpers need a `confirm` flag; pass `confirm=False` (fire-and-forget) at every call site reached from an MQTT callback, keep confirmation only for API/user-facing paths (e.g. sensor registration).
