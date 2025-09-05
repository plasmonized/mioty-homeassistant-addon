/**
 * Sentinum Decoder - Verwendungsbeispiel
 * Zeigt wie die Decoder-Dateien in Ihrem neuen Replit-Projekt verwendet werden
 */

// Import der Decoder-Module (falls Node.js)
// const { parseSensorData } = require('./sentinum-decoder-engine.js');
// const { decodeUplink } = require('./sentinum-febris-th-decoder.js');
// const utils = require('./sentinum-decoder-utils.js');

// === BEISPIEL 1: Febris TH Environmental Sensor ===

// Beispiel Sensor-Daten (17 Bytes)
const febrisTHData = [0x11, 0x32, 0x21, 0x18, 0xe0, 0x04, 0xef, 0x32, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x05, 0x04, 0x7f];

console.log('=== FEBRIS TH SENSOR DECODE ===');
console.log('Raw Bytes:', febrisTHData.map(b => '0x' + b.toString(16).padStart(2, '0')).join(' '));

// Direkte Verwendung des Febris TH Decoders
if (typeof decodeUplink !== 'undefined') {
    const febrisResult = decodeUplink({bytes: febrisTHData});
    console.log('Decoded Febris Data:');
    console.log('- Temperatur:', febrisResult.data.internal_temperature + '°C');
    console.log('- Luftfeuchtigkeit:', febrisResult.data.humidity + '%RH');
    console.log('- Batterie:', febrisResult.data.battery_voltage + 'V');
    console.log('- Taupunkt:', febrisResult.data.dew_point?.toFixed(1) + '°C');
    console.log('- Upload Counter:', febrisResult.data.up_cnt);
}

// === BEISPIEL 2: Mit Converter Code ===

// Febris TH Converter Code als String
const febrisTHConverterCode = `
function decodeUplink(input) {
  const bytes = input.bytes;
  
  if (bytes.length < 17) {
    return { data: {}, warnings: ['Payload zu kurz'], errors: [] };
  }

  const data = {
    base_id: (bytes[0] >> 4) & 0x0F,
    major_version: bytes[0] & 0x0F,
    minor_version: (bytes[1] >> 4) & 0x0F,
    product_version: bytes[1] & 0x0F,
    up_cnt: bytes[2],
    battery_voltage: ((bytes[3] << 8) | bytes[4]) / 1000.0,
    internal_temperature: (((bytes[5] << 8) | bytes[6]) / 10.0) - 100.0,
    humidity: ((bytes[7] << 8) | bytes[8]) / 100.0,
    alarm: bytes[14] || 0,
    networkBaseType: "lorawan",
    networkSubType: "tti"
  };

  // Taupunkt berechnen
  if (data.internal_temperature && data.humidity) {
    const temp = data.internal_temperature;
    const rh = data.humidity;
    const a = 17.27;
    const b = 237.7;
    const alpha = ((a * temp) / (b + temp)) + Math.log(rh / 100.0);
    data.dew_point = (b * alpha) / (a - alpha);
  }

  return { data: data, warnings: [], errors: [] };
}
`;

// Mit Engine parsen
console.log('\\n=== ENGINE-BASIERTES PARSING ===');
if (typeof parseSensorData !== 'undefined') {
    const engineResult = parseSensorData(febrisTHData, febrisTHConverterCode);
    console.log('Parse Success:', engineResult.metadata.parseSuccess);
    console.log('Format:', engineResult.metadata.format);
    console.log('Measurements found:', engineResult.measurements.length);
    
    // Alle Messungen anzeigen
    engineResult.measurements.forEach(measurement => {
        console.log(\`- \${measurement.description}: \${measurement.value}\${measurement.unit}\`);
    });
}

// === BEISPIEL 3: Hex String Input ===

console.log('\\n=== HEX STRING PARSING ===');
const hexPayload = "11322118e004ef32000000000000050547f";

// Hex zu Bytes konvertieren (falls utils verfügbar)
if (typeof hexStringToBytes !== 'undefined') {
    const bytesFromHex = hexStringToBytes(hexPayload);
    console.log('Hex Input:', hexPayload);
    console.log('Converted to Bytes:', bytesFromHex);
    
    // Parsen
    const hexResult = parseSensorData(bytesFromHex, febrisTHConverterCode);
    if (hexResult.metadata.parseSuccess) {
        console.log('Parsing erfolgreich!');
    }
}

// === BEISPIEL 4: Eigener Custom Decoder ===

// Einfacher Custom Decoder für eigene Sensoren
function customSensorDecoder(bytes) {
    if (bytes.length < 6) return null;
    
    return {
        sensor_id: bytes[0],
        value1: (bytes[1] << 8) | bytes[2],
        value2: (bytes[3] << 8) | bytes[4],
        checksum: bytes[5]
    };
}

console.log('\\n=== CUSTOM DECODER BEISPIEL ===');
const customData = [0x01, 0x12, 0x34, 0x56, 0x78, 0x9A];
const customResult = customSensorDecoder(customData);
console.log('Custom Sensor Result:', customResult);

// === VERWENDUNG IN REPLIT ===
console.log('\\n=== REPLIT INTEGRATION ===');
console.log('1. Kopieren Sie alle .js Dateien in Ihr Replit-Projekt');
console.log('2. Importieren Sie die benötigten Module:');
console.log('   const { parseSensorData } = require("./sentinum-decoder-engine.js");');
console.log('3. Verwenden Sie parseSensorData(bytes, converterCode) für Ihre Sensoren');
console.log('4. Oder verwenden Sie spezifische Decoder wie decodeUplink() direkt');