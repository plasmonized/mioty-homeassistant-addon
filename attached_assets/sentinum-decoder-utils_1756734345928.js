/**
 * Sentinum Decoder Utilities
 * Hilfs-Funktionen für Sensor Data Parsing
 */

// Hex String zu Byte Array konvertieren
function hexStringToBytes(hex) {
  const cleanHex = hex.replace(/[^0-9A-Fa-f]/g, '');
  const result = [];
  
  for (let i = 0; i < cleanHex.length; i += 2) {
    result.push(parseInt(cleanHex.substr(i, 2), 16));
  }
  
  return result;
}

// Byte Array zu Hex String
function bytesToHexString(bytes) {
  return bytes.map(b => b.toString(16).padStart(2, '0').toUpperCase()).join(' ');
}

// Signed 16-bit Integer aus 2 Bytes (Little Endian)
function bytesToInt16LE(byte1, byte2) {
  const value = (byte2 << 8) | byte1;
  return value > 32767 ? value - 65536 : value;
}

// Signed 16-bit Integer aus 2 Bytes (Big Endian)
function bytesToInt16BE(byte1, byte2) {
  const value = (byte1 << 8) | byte2;
  return value > 32767 ? value - 65536 : value;
}

// Unsigned 16-bit Integer aus 2 Bytes (Little Endian)
function bytesToUint16LE(byte1, byte2) {
  return (byte2 << 8) | byte1;
}

// Unsigned 16-bit Integer aus 2 Bytes (Big Endian)
function bytesToUint16BE(byte1, byte2) {
  return (byte1 << 8) | byte2;
}

// Temperatur von Raw-Wert konvertieren (typisch für mioty Sensoren)
function rawToTemperature(raw, offset = 100, divisor = 10) {
  return (raw / divisor) - offset;
}

// Luftfeuchtigkeit von Raw-Wert
function rawToHumidity(raw, divisor = 100) {
  return raw / divisor;
}

// Batterie Spannung von Raw-Wert
function rawToBatteryVoltage(raw, divisor = 1000) {
  return raw / divisor;
}

// Taupunkt aus Temperatur und Luftfeuchtigkeit berechnen
function calculateDewPoint(temperature, humidity) {
  const a = 17.27;
  const b = 237.7;
  
  const alpha = ((a * temperature) / (b + temperature)) + Math.log(humidity / 100.0);
  return (b * alpha) / (a - alpha);
}

// Sensor-Typ basierend auf Payload erkennen
function detectSensorTypeFromPayload(bytes) {
  if (bytes.length < 2) return 'Unknown';
  
  // Febris Environmental (17 bytes, startet mit 0x11)
  if (bytes.length === 17 && bytes[0] === 0x11) {
    return 'Febris-TH';
  }
  
  // Febris Utility (12+ bytes)
  if (bytes.length >= 12 && bytes[0] >= 0x10 && bytes[0] <= 0x1F) {
    return 'Febris-Utility';
  }
  
  // IO-Link Format erkennen
  if (bytes.length >= 8 && (bytes[0] & 0x01) !== 0) {
    return 'IO-Link';
  }
  
  return 'Generic-mioty';
}

// Payload Validierung
function validatePayload(bytes, expectedLength = null, expectedStartByte = null) {
  const errors = [];
  
  if (!Array.isArray(bytes)) {
    errors.push('Payload ist kein Array');
    return { valid: false, errors };
  }
  
  if (bytes.length === 0) {
    errors.push('Payload ist leer');
    return { valid: false, errors };
  }
  
  if (expectedLength && bytes.length !== expectedLength) {
    errors.push(`Erwartete Länge: ${expectedLength}, erhalten: ${bytes.length}`);
  }
  
  if (expectedStartByte !== null && bytes[0] !== expectedStartByte) {
    errors.push(`Erwartetes Start-Byte: 0x${expectedStartByte.toString(16)}, erhalten: 0x${bytes[0].toString(16)}`);
  }
  
  // Prüfe auf gültige Byte-Werte (0-255)
  for (let i = 0; i < bytes.length; i++) {
    if (bytes[i] < 0 || bytes[i] > 255 || !Number.isInteger(bytes[i])) {
      errors.push(`Ungültiger Byte-Wert an Position ${i}: ${bytes[i]}`);
      break;
    }
  }
  
  return { valid: errors.length === 0, errors };
}

// CRC8 Checksum berechnen (für Datenvalidierung)
function calculateCRC8(bytes) {
  let crc = 0x00;
  const polynomial = 0x07;
  
  for (let byte of bytes) {
    crc ^= byte;
    for (let i = 0; i < 8; i++) {
      if (crc & 0x80) {
        crc = (crc << 1) ^ polynomial;
      } else {
        crc = crc << 1;
      }
      crc &= 0xFF;
    }
  }
  
  return crc;
}

// Debug Ausgabe formatieren
function formatDebugOutput(bytes, decoded = null) {
  const hexString = bytesToHexString(bytes);
  
  console.log('=== Sentinum Decoder Debug ===');
  console.log(`Raw Bytes (${bytes.length}):`, hexString);
  console.log('Byte Array:', bytes);
  
  if (decoded) {
    console.log('Decoded Data:');
    for (const [key, value] of Object.entries(decoded)) {
      console.log(`  ${key}: ${value}`);
    }
  }
  console.log('===============================');
}

// Export für Node.js
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    hexStringToBytes,
    bytesToHexString,
    bytesToInt16LE,
    bytesToInt16BE,
    bytesToUint16LE,
    bytesToUint16BE,
    rawToTemperature,
    rawToHumidity,
    rawToBatteryVoltage,
    calculateDewPoint,
    detectSensorTypeFromPayload,
    validatePayload,
    calculateCRC8,
    formatDebugOutput
  };
}