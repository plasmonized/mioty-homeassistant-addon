/**
 * Sentinum Febris TH Environmental Sensor Decoder
 * Temperatur & Luftfeuchtigkeit Sensor
 * 
 * Verwendung:
 * const result = decodeUplink({bytes: [0x11, 0x32, 0x21, ...]});
 */

function decodeUplink(input) {
  const bytes = input.bytes;
  
  if (bytes.length < 17) {
    return {
      data: {},
      warnings: ['Payload zu kurz'],
      errors: ['Mindestens 17 Bytes erforderlich']
    };
  }

  try {
    const data = {};

    // Byte 0: Base ID (obere 4 Bits) und Major Version (untere 4 Bits)
    data.base_id = (bytes[0] >> 4) & 0x0F;
    data.major_version = bytes[0] & 0x0F;

    // Byte 1: Minor Version (obere 4 Bits) und Product Version (untere 4 Bits)
    data.minor_version = (bytes[1] >> 4) & 0x0F;
    data.product_version = bytes[1] & 0x0F;

    // Byte 2: Upload Counter
    data.up_cnt = bytes[2];

    // Bytes 3-4: Battery Voltage (mV)
    data.battery_voltage = ((bytes[3] << 8) | bytes[4]) / 1000.0;

    // Bytes 5-6: Internal Temperature (0.1°C - 100°C offset)
    const temp_raw = (bytes[5] << 8) | bytes[6];
    data.internal_temperature = (temp_raw / 10.0) - 100.0;

    // Bytes 7-8: Relative Humidity (0.01% RH)
    data.humidity = ((bytes[7] << 8) | bytes[8]) / 100.0;

    // Bytes 9-10: External Temperature (falls verfügbar)
    if (bytes.length > 10) {
      const ext_temp_raw = (bytes[9] << 8) | bytes[10];
      data.external_temperature = (ext_temp_raw / 10.0) - 100.0;
    }

    // Alarm Status (falls verfügbar)
    if (bytes.length > 14) {
      data.alarm = bytes[14];
    }

    // Taupunkt berechnen (Approximation)
    if (data.internal_temperature && data.humidity) {
      const temp = data.internal_temperature;
      const rh = data.humidity;
      
      // Magnus-Formel für Taupunkt
      const a = 17.27;
      const b = 237.7;
      const alpha = ((a * temp) / (b + temp)) + Math.log(rh / 100.0);
      data.dew_point = (b * alpha) / (a - alpha);
    }

    // Netzwerk Metadaten
    data.networkBaseType = "lorawan";
    data.networkSubType = "tti";

    return {
      data: data,
      warnings: [],
      errors: []
    };

  } catch (error) {
    return {
      data: {},
      warnings: [],
      errors: [`Decode Error: ${error.message}`]
    };
  }
}

// Beispiel Verwendung:
/*
const testData = [0x11, 0x32, 0x21, 0x18, 0xe0, 0x04, 0xef, 0x32, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x05, 0x04, 0x7f];
const result = decodeUplink({bytes: testData});
console.log('Decoded:', result.data);
*/

// Export für Node.js
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { decodeUplink };
}