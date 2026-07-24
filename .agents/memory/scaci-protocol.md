---
name: SCACI protocol quirks
description: Non-obvious details of the mioty SC-AC-Interface (SCACI) v1.0.0 implementation
---

- Spec source: attached_assets/MIOTY_SC-AC-Interface_v1.0.0_*.pdf. Framing: "MIOTYA01" (8 B ASCII) + 4-byte little-endian payload size, payload msgpack-encoded.
- The AC (this add-on) is the TLS **client**; the Service Center listens (default port 16017). Connect operation must use opId 0; AC-initiated ops use positive strictly increasing opIds, SC-initiated ops use negative opIds.
- Spec quirk: the response to an SC-initiated `dlDataRes` is named `txDataResRsp` (not `dlDataResRsp`).
- Every operation is a 3-way handshake: request → Rsp → Cmp (or error → errorAck). The receiver of a Rsp sends the Cmp.
- ReCon (`rc.*`) sublayer is not implemented — must be rejected with error code 38.
- Real-world SC `ulData` payloads: snr/rssi/bsEui/rxTime at TOP level AND in `rxInfo` list (never `baseStations`); packet counter `cnt` (not `packetCnt`); user data `userData` or `data` (identical). Parse both, prefer top-level.
- `statusRsp` field names (spec-exact): `basestations` (all-lowercase list), `rc` (not `code`), `uptimeS` (not `uptime`), `timeNs` (not `time`). Getting these wrong means base stations never appear.
- `epStat` message: uses `online` (bool) and `attached` (bool) fields, NOT `epStatus`. Also has `attachedBsEui`, `packetCnt`, `lastSeen`.
- Error messages use field `rc` (not `code`) — both SC→AC errors and AC→SC error replies.
- **Why:** these details are easy to get wrong when revisiting the client and are not derivable without re-reading the PDF.
- **How to apply:** when touching mioty-application-center/app/scaci_client.py or the mock test server, keep framing/opId/handshake rules consistent with the above.
