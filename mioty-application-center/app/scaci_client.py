"""
SCACI Client für BSSCI mioty Add-on
Implementiert das MIOTY Service Center Application Center Interface (SCACI) v1.0.0

Das Application Center (dieses Add-on) baut eine persistente, TLS-gesicherte
TCP-Verbindung zum Service Center auf. Nachrichten werden MessagePack-kodiert
mit einem binären Header übertragen:

    Header: "MIOTYA01" (8 Byte ASCII) + Payload-Größe (4 Byte, little endian)
"""

import os
import ssl
import json
import time
import socket
import struct
import logging
import threading
import secrets
from typing import Dict, Any, Optional, Callable, List

try:
    import msgpack
except ImportError:
    msgpack = None

SCACI_IDENTIFIER = b"MIOTYA01"
SCACI_HEADER_SIZE = 12  # 8 Byte Identifier + 4 Byte Größe
SCACI_VERSION = "1.0.0"
MAX_PAYLOAD_SIZE = 16 * 1024 * 1024  # 16 MB Schutzgrenze


class SCACIError(Exception):
    """SCACI Protokollfehler."""

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"SCACI Error {code}: {message}")


class SCACIClient:
    """Vollständiger SCACI v1.0.0 Client (Application Center Seite)."""

    def __init__(
        self,
        host: str,
        port: int,
        ac_eui: str,
        ca_cert: Optional[str] = None,
        client_cert: Optional[str] = None,
        client_key: Optional[str] = None,
        tls_insecure: bool = False,
        session_file: Optional[str] = None,
        name: str = "mioty Application Center",
        vendor: str = "Sentinum",
        model: str = "BSSCI Add-on",
        sw_version: str = "1.0.6.14",
    ):
        self.host = host
        self.port = int(port)
        self.ac_eui = int(ac_eui, 16) if isinstance(ac_eui, str) else int(ac_eui)
        self.ca_cert = ca_cert
        self.client_cert = client_cert
        self.client_key = client_key
        self.tls_insecure = tls_insecure
        self.name = name
        self.vendor = vendor
        self.model = model
        self.sw_version = sw_version

        # Operation-IDs: AC nutzt positive, streng aufsteigende 64-bit IDs
        self._op_id = 0
        self._op_lock = threading.Lock()

        # Session-Verwaltung (für Session-Resume nach Verbindungsverlust)
        self.session_file = session_file
        self.sn_ac_uuid: List[int] = []
        self.sn_sc_uuid: List[int] = []
        self._load_session()

        # Ausstehende, von uns initiierte Operationen: opId -> Event/Ergebnis
        self._pending: Dict[int, Dict[str, Any]] = {}
        self._pending_lock = threading.Lock()

        # Verbindung
        self._sock: Optional[ssl.SSLSocket] = None
        self._sock_lock = threading.Lock()
        self.connected = False
        self.connect_completed = False
        self._running = False
        self._rx_thread: Optional[threading.Thread] = None
        self._keepalive_thread: Optional[threading.Thread] = None
        self._reconnect_delay = 5
        self._last_activity = 0.0

        # Status-Informationen
        self.sc_info: Dict[str, Any] = {}
        self.last_error: Optional[str] = None
        self.last_connect_time: Optional[float] = None

        # Callbacks
        self.on_ul_data: Optional[Callable[[str, Dict[str, Any]], None]] = None
        self.on_ep_status: Optional[Callable[[str, Dict[str, Any]], None]] = None
        self.on_dl_data_result: Optional[Callable[[str, Dict[str, Any]], None]] = None
        self.on_connection_change: Optional[Callable[[bool], None]] = None

    # ------------------------------------------------------------------
    # Session-Persistenz
    # ------------------------------------------------------------------
    def _load_session(self):
        self.sn_ac_uuid = list(secrets.token_bytes(16))
        if self.session_file and os.path.exists(self.session_file):
            try:
                with open(self.session_file, "r") as f:
                    data = json.load(f)
                if isinstance(data.get("sn_ac_uuid"), list) and len(data["sn_ac_uuid"]) == 16:
                    self.sn_ac_uuid = data["sn_ac_uuid"]
                self._op_id = int(data.get("op_id", 0))
            except Exception as e:
                logging.warning(f"SCACI: Konnte Session nicht laden: {e}")

    def _save_session(self):
        if not self.session_file:
            return
        try:
            os.makedirs(os.path.dirname(self.session_file) or ".", exist_ok=True)
            with open(self.session_file, "w") as f:
                json.dump({"sn_ac_uuid": self.sn_ac_uuid, "op_id": self._op_id}, f)
        except Exception as e:
            logging.warning(f"SCACI: Konnte Session nicht speichern: {e}")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def start(self):
        """Starte Client mit automatischem Reconnect im Hintergrund."""
        if msgpack is None:
            raise RuntimeError("msgpack ist nicht installiert")
        self._running = True
        thread = threading.Thread(target=self._connection_loop, daemon=True, name="scaci-conn")
        thread.start()
        logging.info(f"🔌 SCACI Client gestartet ({self.host}:{self.port}, AC-EUI {self.ac_eui:016X})")

    def stop(self):
        """Stoppe Client und schließe Verbindung."""
        self._running = False
        self._close_socket()
        logging.info("🔌 SCACI Client gestoppt")

    def _connection_loop(self):
        while self._running:
            try:
                self._connect_once()
            except Exception as e:
                self.last_error = str(e)
                logging.error(f"❌ SCACI Verbindungsfehler: {e}")
            self._set_connected(False)
            if not self._running:
                break
            logging.info(f"🔄 SCACI Reconnect in {self._reconnect_delay}s ...")
            time.sleep(self._reconnect_delay)
            self._reconnect_delay = min(self._reconnect_delay * 2, 60)

    def _is_ip_address(self) -> bool:
        """Prüft ob self.host eine IP-Adresse ist (kein Hostname)."""
        import ipaddress
        try:
            ipaddress.ip_address(self.host)
            return True
        except ValueError:
            return False

    def _build_ssl_context(self) -> ssl.SSLContext:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        # TLS 1.2 als Minimum für Kompatibilität mit Embedded-Geräten
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        # Bei IP-Adresse: check_hostname deaktivieren (SNI erfordert FQDN, keine IP)
        if self._is_ip_address():
            ctx.check_hostname = False
        if self.ca_cert and os.path.exists(self.ca_cert):
            ctx.load_verify_locations(cafile=self.ca_cert)
        else:
            ctx.load_default_certs()
        if self.tls_insecure:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            logging.warning("⚠️ SCACI: TLS-Zertifikatsprüfung DEAKTIVIERT (nur für Tests!)")
        if self.client_cert and self.client_key and os.path.exists(self.client_cert) and os.path.exists(self.client_key):
            ctx.load_cert_chain(certfile=self.client_cert, keyfile=self.client_key)
            logging.info("🔐 SCACI: Client-Zertifikat geladen")
        return ctx

    def _connect_once(self):
        ctx = self._build_ssl_context()
        raw = socket.create_connection((self.host, self.port), timeout=15)
        raw.settimeout(30)
        # SNI nur bei echtem Hostnamen senden — IP-Adressen sind kein gültiger SNI-Wert (RFC 6066)
        sni_host = None if self._is_ip_address() else self.host
        sock = ctx.wrap_socket(raw, server_hostname=sni_host)
        logging.info(f"🔐 SCACI TLS-Verbindung aufgebaut zu {self.host}:{self.port} ({sock.version()}, SNI={'nein' if sni_host is None else sni_host})")
        with self._sock_lock:
            self._sock = sock
        self.connected = True
        self.connect_completed = False
        self._last_activity = time.time()

        # RX-Thread starten
        rx = threading.Thread(target=self._rx_loop, daemon=True, name="scaci-rx")
        rx.start()

        try:
            self._do_connect_operation()
            self.connect_completed = True
            self.last_connect_time = time.time()
            self._reconnect_delay = 5
            self.last_error = None
            self._set_connected(True)
            logging.info("✅ SCACI Connect-Operation abgeschlossen — Session aktiv")

            # Keepalive-Loop im aktuellen Thread
            self._keepalive_loop(rx)
        finally:
            self.connect_completed = False
            self._close_socket()
            rx.join(timeout=5)

    def _keepalive_loop(self, rx_thread: threading.Thread):
        """Sendet Ping bei Inaktivität, überwacht RX-Thread."""
        while self._running and self.connected and rx_thread.is_alive():
            time.sleep(1)
            idle = time.time() - self._last_activity
            if idle >= 30:
                try:
                    self.ping(timeout=15)
                except Exception as e:
                    logging.warning(f"⚠️ SCACI Ping fehlgeschlagen: {e}")
                    return

    def _set_connected(self, state: bool):
        prev = self.connect_completed if state else self.connected
        self.connected = state and self.connected
        if not state:
            self.connected = False
            self.connect_completed = False
            # Alle wartenden Operationen freigeben
            with self._pending_lock:
                for op in self._pending.values():
                    op["error"] = SCACIError(103, "Verbindung getrennt")
                    op["event"].set()
                self._pending.clear()
        if self.on_connection_change:
            try:
                self.on_connection_change(state)
            except Exception:
                pass

    def _close_socket(self):
        with self._sock_lock:
            if self._sock:
                try:
                    self._sock.close()
                except Exception:
                    pass
                self._sock = None
        self.connected = False

    # ------------------------------------------------------------------
    # Framing / Senden / Empfangen
    # ------------------------------------------------------------------
    def _send_message(self, message: Dict[str, Any]):
        payload = msgpack.packb(message, use_bin_type=True)
        frame = SCACI_IDENTIFIER + struct.pack("<I", len(payload)) + payload
        with self._sock_lock:
            if not self._sock:
                raise SCACIError(107, "Nicht verbunden")
            self._sock.sendall(frame)
        self._last_activity = time.time()
        logging.debug(f"➡️ SCACI TX: {message.get('command')} (opId {message.get('opId')})")

    def _recv_exact(self, n: int) -> bytes:
        buf = b""
        while len(buf) < n:
            with self._sock_lock:
                sock = self._sock
            if not sock:
                raise ConnectionError("Socket geschlossen")
            try:
                chunk = sock.recv(n - len(buf))
            except socket.timeout:
                continue
            if not chunk:
                raise ConnectionError("Verbindung vom Service Center geschlossen")
            buf += chunk
        return buf

    def _rx_loop(self):
        try:
            while self._running and self.connected:
                header = self._recv_exact(SCACI_HEADER_SIZE)
                if header[:8] != SCACI_IDENTIFIER:
                    raise SCACIError(71, f"Ungültiger SCACI Header: {header[:8]!r}")
                size = struct.unpack("<I", header[8:12])[0]
                if size > MAX_PAYLOAD_SIZE:
                    raise SCACIError(90, f"Payload zu groß: {size} Bytes")
                payload = self._recv_exact(size)
                self._last_activity = time.time()
                try:
                    message = msgpack.unpackb(payload, raw=False, strict_map_key=False)
                except Exception:
                    # Fallback: JSON-kodierte Nachricht
                    message = json.loads(payload.decode("utf-8"))
                if not isinstance(message, dict):
                    raise SCACIError(71, "SCACI Nachricht ist kein Objekt")
                self._handle_message(message)
        except (ConnectionError, OSError) as e:
            if self._running and self.connected:
                logging.warning(f"⚠️ SCACI Verbindung verloren: {e}")
        except Exception as e:
            logging.error(f"❌ SCACI RX-Fehler: {e}")
        finally:
            self._close_socket()
            self._set_connected(False)

    # ------------------------------------------------------------------
    # Nachrichten-Dispatch
    # ------------------------------------------------------------------
    def _handle_message(self, message: Dict[str, Any]):
        command = message.get("command")
        op_id = message.get("opId")
        if command is None or op_id is None:
            logging.warning(f"⚠️ SCACI: Nachricht ohne Kernfelder ignoriert: {message}")
            return
        logging.debug(f"⬅️ SCACI RX: {command} (opId {op_id})")

        # Antworten auf von uns initiierte Operationen (positive opId)
        if op_id >= 0 and (command.endswith("Rsp") or command == "error"):
            self._handle_own_op_reply(command, op_id, message)
            return

        # Vom Service Center initiierte Operationen (negative opId)
        handlers = {
            "ping": self._sc_ping,
            "ulData": self._sc_ul_data,
            "epStat": self._sc_ep_status,
            "dlDataRes": self._sc_dl_data_result,
            "error": self._sc_error,
        }
        # Abschluss-Nachrichten des SC für seine eigenen Operationen — keine Aktion nötig
        if command.endswith("Cmp") or command == "errorAck":
            return
        handler = handlers.get(command)
        if handler:
            try:
                handler(op_id, message)
            except Exception as e:
                logging.error(f"❌ SCACI Handler-Fehler für {command}: {e}")
                self._send_error(op_id, 5, f"Interner Fehler: {e}")
        elif command.startswith("rc."):
            # ReCon Sublayer wird nicht unterstützt -> Fehler laut Spezifikation
            self._send_error(op_id, 38, "ReCon Sublayer nicht unterstützt")
        else:
            self._send_error(op_id, 95, f"Unbekannte Operation: {command}")

    def _handle_own_op_reply(self, command: str, op_id: int, message: Dict[str, Any]):
        with self._pending_lock:
            op = self._pending.get(op_id)
        if not op:
            logging.warning(f"⚠️ SCACI: Antwort für unbekannte Operation {op_id}: {command}")
            return
        if command == "error":
            # Spec: Fehlerfeld heißt "rc", nicht "code"
            op["error"] = SCACIError(message.get("rc", message.get("code", -1)), message.get("message", ""))
            # Fehler mit errorAck bestätigen (schließt die Operation ab)
            try:
                self._send_message({"command": "errorAck", "opId": op_id})
            except Exception:
                pass
        else:
            op["response"] = message
            # Operation mit Complete-Nachricht abschließen
            cmp_command = op["command"] + "Cmp"
            try:
                self._send_message({"command": cmp_command, "opId": op_id})
            except Exception as e:
                op["error"] = SCACIError(107, f"Complete konnte nicht gesendet werden: {e}")
        op["event"].set()

    # --- SC-initiierte Operationen -------------------------------------
    def _sc_ping(self, op_id: int, message: Dict[str, Any]):
        self._send_message({"command": "pingRsp", "opId": op_id})

    def _sc_ul_data(self, op_id: int, message: Dict[str, Any]):
        ep_eui = self._eui_to_hex(message.get("epEui"))
        self._send_message({"command": "ulDataRsp", "opId": op_id})
        if self.on_ul_data:
            self.on_ul_data(ep_eui, message)

    def _sc_ep_status(self, op_id: int, message: Dict[str, Any]):
        ep_eui = self._eui_to_hex(message.get("epEui"))
        self._send_message({"command": "epStatRsp", "opId": op_id})
        # Spec: online (bool) + attached (bool), kein "epStatus"-Feld
        online = message.get("online", False)
        attached = message.get("attached", False)
        logging.info(f"📡 SCACI EP-Status: {ep_eui} -> online={online}, attached={attached}")
        if self.on_ep_status:
            self.on_ep_status(ep_eui, message)

    def _sc_dl_data_result(self, op_id: int, message: Dict[str, Any]):
        ep_eui = self._eui_to_hex(message.get("epEui"))
        # Achtung: Laut Spezifikation heißt die Antwort "txDataResRsp"
        self._send_message({"command": "txDataResRsp", "opId": op_id})
        logging.info(f"📨 SCACI DL-Ergebnis für {ep_eui}: {message.get('result')}")
        if self.on_dl_data_result:
            self.on_dl_data_result(ep_eui, message)

    def _sc_error(self, op_id: int, message: Dict[str, Any]):
        # Spec: Fehlerfeld heißt "rc", nicht "code"
        logging.error(f"❌ SCACI Fehler vom Service Center (opId {op_id}): "
                      f"rc={message.get('rc', message.get('code'))} - {message.get('message')}")
        self._send_message({"command": "errorAck", "opId": op_id})

    def _send_error(self, op_id: int, code: int, text: str):
        try:
            # Spec: Fehlerfeld heißt "rc"
            self._send_message({"command": "error", "opId": op_id, "rc": code, "message": text})
        except Exception:
            pass

    # ------------------------------------------------------------------
    # AC-initiierte Operationen
    # ------------------------------------------------------------------
    def _next_op_id(self) -> int:
        with self._op_lock:
            self._op_id += 1
            self._save_session()
            return self._op_id

    def _run_operation(self, message: Dict[str, Any], timeout: float = 30) -> Dict[str, Any]:
        """Sende Operation, warte auf Rsp und sende Cmp (erledigt der RX-Handler)."""
        op_id = message["opId"]
        op = {"command": message["command"], "event": threading.Event(), "response": None, "error": None}
        with self._pending_lock:
            self._pending[op_id] = op
        try:
            self._send_message(message)
            if not op["event"].wait(timeout):
                raise SCACIError(110, f"Timeout bei Operation {message['command']} (opId {op_id})")
            if op["error"]:
                raise op["error"]
            return op["response"] or {}
        finally:
            with self._pending_lock:
                self._pending.pop(op_id, None)

    def _do_connect_operation(self):
        """Connect-Operation, muss opId 0 verwenden."""
        message = {
            "command": "con",
            "opId": 0,
            "version": SCACI_VERSION,
            "acEui": self.ac_eui,
            "vendor": self.vendor,
            "model": self.model,
            "name": self.name,
            "swVersion": self.sw_version,
            "snAcUuid": self.sn_ac_uuid,
        }
        op = {"command": "con", "event": threading.Event(), "response": None, "error": None}
        with self._pending_lock:
            self._pending[0] = op
        try:
            self._send_message(message)
            if not op["event"].wait(30):
                raise SCACIError(110, "Timeout bei Connect-Operation")
            if op["error"]:
                raise op["error"]
            rsp = op["response"] or {}
            version = rsp.get("version", SCACI_VERSION)
            major_minor = ".".join(version.split(".")[:2])
            if major_minor != ".".join(SCACI_VERSION.split(".")[:2]):
                raise SCACIError(71, f"Inkompatible SCACI Version: {version}")
            self.sc_info = {
                "scEui": self._eui_to_hex(rsp.get("scEui")),
                "vendor": rsp.get("vendor"),
                "model": rsp.get("model"),
                "name": rsp.get("name"),
                "swVersion": rsp.get("swVersion"),
                "version": version,
                "snResume": rsp.get("snResume", False),
            }
            if isinstance(rsp.get("snScUuid"), (list, bytes)):
                self.sn_sc_uuid = list(rsp["snScUuid"])
            if not rsp.get("snResume"):
                logging.info("🆕 SCACI: Neue Session gestartet")
            else:
                logging.info("♻️ SCACI: Vorherige Session fortgesetzt")
        finally:
            with self._pending_lock:
                self._pending.pop(0, None)

    def ping(self, timeout: float = 30) -> bool:
        """Ping-Operation zum Verbindungstest."""
        self._run_operation({"command": "ping", "opId": self._next_op_id()}, timeout)
        return True

    def get_status(self, timeout: float = 30) -> Dict[str, Any]:
        """Status-Operation: Service Center- und Base-Station-Status abrufen."""
        rsp = self._run_operation({"command": "status", "opId": self._next_op_id()}, timeout)
        base_stations = []
        # Spec: Feld heißt "basestations" (komplett lowercase), nicht "baseStations"
        for bs in rsp.get("basestations") or rsp.get("baseStations") or []:
            entry = dict(bs)
            for eui_field in ("eui", "bsEui"):
                if eui_field in entry and entry[eui_field] is not None:
                    entry[eui_field] = self._eui_to_hex(entry[eui_field])
            base_stations.append(entry)
        return {
            # Spec-Felder: rc, message, timeNs, uptimeS
            "rc": rsp.get("rc", rsp.get("code")),
            "message": rsp.get("message"),
            "timeNs": rsp.get("timeNs", rsp.get("time")),
            "uptimeS": rsp.get("uptimeS", rsp.get("uptime")),
            "bsConnected": rsp.get("bsConnected"),
            "epRegistered": rsp.get("epRegistered"),
            "epOnline": rsp.get("epOnline"),
            "baseStations": base_stations,
        }

    def register_endpoint(
        self,
        ep_eui: str,
        nwk_key: str,
        short_addr: int,
        bidi: bool = False,
        pre_attach: bool = True,
        attach_cnt: int = 0,
        packet_cnt: int = 0,
        dual_chan: bool = False,
        repetition: bool = False,
        wide_carr_off: bool = False,
        long_blk_dist: bool = False,
        timeout: float = 30,
    ) -> bool:
        """Register-Operation: End Point am Service Center registrieren."""
        key_bytes = bytes.fromhex(nwk_key)
        if len(key_bytes) != 16:
            raise ValueError("Network Key muss 16 Byte (32 Hex-Zeichen) lang sein")
        self._run_operation({
            "command": "reg",
            "opId": self._next_op_id(),
            "epEui": int(ep_eui, 16),
            "bidi": bidi,
            "preAttach": pre_attach,
            "nwkKey": list(key_bytes),
            "shAddr": int(short_addr),
            "attachCnt": int(attach_cnt),
            "packetCnt": int(packet_cnt),
            "dualChan": dual_chan,
            "repetition": repetition,
            "wideCarrOff": wide_carr_off,
            "longBlkDist": long_blk_dist,
        }, timeout)
        logging.info(f"✅ SCACI: End Point {ep_eui.upper()} registriert")
        return True

    def deregister_endpoint(self, ep_eui: str, timeout: float = 30) -> bool:
        """Deregister-Operation: End Point am Service Center abmelden."""
        self._run_operation({
            "command": "dereg",
            "opId": self._next_op_id(),
            "epEui": int(ep_eui, 16),
        }, timeout)
        logging.info(f"✅ SCACI: End Point {ep_eui.upper()} deregistriert")
        return True

    def queue_downlink(
        self,
        ep_eui: str,
        user_data: bytes,
        queue_id: Optional[int] = None,
        cnt_depend: bool = False,
        packet_cnt: Optional[List[int]] = None,
        prio: float = 0.0,
        response_exp: bool = False,
        timeout: float = 30,
    ) -> int:
        """DL data queue Operation: Downlink-Daten einreihen."""
        que_id = queue_id if queue_id is not None else secrets.randbits(63)
        message: Dict[str, Any] = {
            "command": "dlDataQue",
            "opId": self._next_op_id(),
            "epEui": int(ep_eui, 16),
            "queId": que_id,
            "cntDepend": cnt_depend,
            "userData": [list(user_data)] if cnt_depend else list(user_data),
            "prio": float(prio),
        }
        if cnt_depend and packet_cnt:
            message["packetCnt"] = packet_cnt
        if response_exp:
            message["responseExp"] = True
        self._run_operation(message, timeout)
        logging.info(f"📤 SCACI: Downlink für {ep_eui.upper()} eingereiht (queId {que_id})")
        return que_id

    def revoke_downlink(self, ep_eui: str, packet_cnt: int, timeout: float = 30) -> bool:
        """DL data revoke Operation: Eingereihte Downlink-Daten zurückziehen."""
        self._run_operation({
            "command": "dlDataRev",
            "opId": self._next_op_id(),
            "epEui": int(ep_eui, 16),
            "packetCnt": int(packet_cnt),
        }, timeout)
        return True

    # ------------------------------------------------------------------
    # Hilfsfunktionen
    # ------------------------------------------------------------------
    @staticmethod
    def _eui_to_hex(eui: Any) -> str:
        """EUI zu 16-stelligem Hex-String (Großbuchstaben).
        Unterstützt: Integer (wie Spec vorschreibt), Hex-Strings ('502DF4000056A0BE'),
        Bytes/Bytearray (8 Byte big-endian).
        """
        if eui is None:
            return ""
        if isinstance(eui, (bytes, bytearray)):
            return eui.hex().upper().zfill(16)
        if isinstance(eui, str):
            s = eui.strip()
            try:
                return f"{int(s, 16):016X}"
            except ValueError:
                return s.upper().zfill(16)
        try:
            return f"{int(eui):016X}"
        except (TypeError, ValueError):
            return str(eui).upper()

    def get_connection_info(self) -> Dict[str, Any]:
        """Statusinfo für die Web-GUI."""
        return {
            "connected": self.connected and self.connect_completed,
            "host": self.host,
            "port": self.port,
            "ac_eui": f"{self.ac_eui:016X}",
            "sc_info": self.sc_info,
            "last_error": self.last_error,
            "last_connect_time": self.last_connect_time,
            "tls_insecure": self.tls_insecure,
            "client_cert": bool(self.client_cert and os.path.exists(self.client_cert or "")),
        }


def parse_ul_data_message(message: Dict[str, Any]) -> Dict[str, Any]:
    """Konvertiere eine SCACI ulData Nachricht in das interne Sensor-Datenformat
    (kompatibel zum MQTT-Format des Add-ons).

    Unterstützt beide bekannten Feldvarianten des Service Centers:
    - Empfangsinfos in "rxInfo" oder "baseStations" (Liste) sowie zusätzlich
      snr/rssi/bsEui/rxTime auf der obersten Ebene
    - Paketzähler als "cnt" oder "packetCnt"
    - Nutzdaten als "userData" oder "data"
    """
    rx_list = message.get("rxInfo") or message.get("baseStations") or []
    best: Dict[str, Any] = {}
    if rx_list:
        # Empfangsweg mit bestem SNR wählen
        best = max(rx_list, key=lambda b: b.get("snr", -999))
    
    # Fallback / Vorrang: Werte auf oberster Ebene (so sendet sie das reale SC)
    snr = message.get("snr", best.get("snr", 0))
    rssi = message.get("rssi", best.get("rssi", 0))
    rx_time = message.get("rxTime", best.get("rxTime", 0))
    bs_eui = message.get("bsEui", best.get("bsEui"))
    
    user_data = message.get("userData")
    if user_data is None:
        user_data = message.get("data") or []
    if isinstance(user_data, (bytes, bytearray)):
        user_data = list(user_data)
    
    packet_cnt = message.get("cnt", message.get("packetCnt", 0))
    
    return {
        "data": user_data,
        "snr": snr,
        "rssi": rssi,
        "timestamp_ns": rx_time,
        "rxTime": rx_time,
        "bs_eui": SCACIClient._eui_to_hex(bs_eui) if bs_eui is not None else "Unknown",
        "packet_cnt": packet_cnt,
        "short_addr": message.get("shAddr"),
        "dl_open": message.get("dlOpen", False),
        "response_exp": message.get("responseExp", False),
        "dl_ack": message.get("dlAck", False),
        "format": message.get("format", 0),
        "base_station_count": max(len(rx_list), 1 if bs_eui is not None else 0),
        "type": "mioty",
        "source": "scaci",
    }


def generate_ac_eui(name: str = "") -> str:
    """Erzeuge eine AC-EUI (16 Hex-Zeichen): 'AC' + 6 Hex aus dem Namen + 8 Hex zufällig."""
    import hashlib
    name_part = hashlib.sha256((name or "mioty-ac").encode("utf-8")).hexdigest()[:6]
    random_part = secrets.token_hex(4)
    return ("ac" + name_part + random_part).upper()
