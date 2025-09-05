/**
 * Sentinum Sensor Data Decoder Engine
 * Extrahiert aus dem mioty Service Center
 * Verwendung: const result = parseSensorData(rawData, converterCode);
 */

// Haupt-Parser Funktion
function parseSensorData(rawData, converterCode = null) {
  const result = {
    sensorType: 'Unknown',
    measurements: [],
    metadata: {
      dataLength: rawData.length,
      format: 'raw',
      parseSuccess: false,
      errors: []
    }
  };

  try {
    // Blueprint-basierte Parsing (wenn Converter Code verfügbar)
    if (converterCode) {
      const decoded = executeConverterCode(converterCode, rawData);
      if (decoded) {
        result.measurements = convertDecodedToMeasurements(decoded);
        result.metadata.parseSuccess = true;
        result.metadata.format = 'blueprint';
        return result;
      }
    }

    // Fallback zu Standard-Parsing
    const sensorType = detectSensorType(rawData);
    result.sensorType = sensorType;

    switch (sensorType) {
      case 'FEBR-Environmental':
        result.measurements = parseEnvironmentalSensor(rawData);
        break;
      case 'FEBR-Utility':
        result.measurements = parseUtilitySensor(rawData);
        break;
      default:
        result.measurements = parseUnknownSensor(rawData);
        break;
    }

    result.metadata.parseSuccess = result.measurements.length > 0;
    return result;
    
  } catch (error) {
    result.metadata.errors = [`Parse error: ${error.message}`];
    return result;
  }
}

// Converter Code Executor (unterstützt decodeUplink Funktion)
function executeConverterCode(converterCode, rawData) {
  try {
    const input = {
      bytes: rawData,
      fPort: 1
    };

    // JavaScript Converter Code ausführen
    const converterFunction = new Function('input', `
      const bytes = input.bytes;
      const port = input.fPort;
      const fPort = input.fPort;
      
      ${converterCode}
      
      // decodeUplink aufrufen falls vorhanden
      if (typeof decodeUplink === 'function') {
        const result = decodeUplink(input);
        
        if (result && typeof result === 'object') {
          // Sentinum Format mit 'data' Property
          if (result.data && typeof result.data === 'object') {
            return result.data;
          }
          return result;
        }
        return result;
      }
      
      // decoded Variable falls vorhanden
      if (typeof decoded !== 'undefined') {
        return decoded;
      }
      
      return {};
    `);

    return converterFunction(input);
  } catch (error) {
    console.error('Converter Error:', error);
    return null;
  }
}

// Decoded Object zu Measurements konvertieren
function convertDecodedToMeasurements(decoded) {
  const measurements = [];
  
  for (const [key, value] of Object.entries(decoded)) {
    if (key === 'networkBaseType' || key === 'networkSubType' || typeof value === 'undefined') {
      continue;
    }
    
    let unit = '';
    let description = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    
    // Temperatur Mapping
    if (key.toLowerCase().includes('temperature')) {
      unit = '°C';
    }
    // Luftfeuchtigkeit
    else if (key === 'humidity') {
      unit = '%RH';
      description = 'Relative Humidity';
    }
    // Batterie Spannung
    else if (key.includes('battery') && key.includes('voltage')) {
      unit = 'V';
      description = 'Battery Voltage';
    }
    // Taupunkt
    else if (key.includes('dew_point')) {
      unit = '°C';
      description = 'Dew Point';
    }
    
    measurements.push({
      type: key,
      value: typeof value === 'number' ? value : String(value),
      unit,
      description
    });
  }
  
  return measurements;
}

// Sensor Typ Detection (vereinfacht)
function detectSensorType(rawData) {
  if (rawData.length >= 17 && rawData[0] === 0x11) {
    return 'FEBR-Environmental';
  } else if (rawData.length >= 12) {
    return 'FEBR-Utility';
  }
  return 'Generic-mioty';
}

// Standard Environmental Sensor Parser
function parseEnvironmentalSensor(data) {
  if (data.length < 17) return [];
  
  const measurements = [];
  
  // Batterie Spannung (Bytes 3-4)
  const batteryVoltage = ((data[3] << 8) | data[4]) / 1000.0;
  measurements.push({
    type: 'battery_voltage',
    value: batteryVoltage,
    unit: 'V',
    description: 'Battery Voltage'
  });

  // Interne Temperatur (Bytes 5-6)
  const internalTemp = (((data[5] << 8) | data[6]) / 10.0) - 100;
  measurements.push({
    type: 'internal_temperature',
    value: internalTemp,
    unit: '°C',
    description: 'Internal Temperature'
  });

  // Luftfeuchtigkeit (Bytes 7-8)
  const humidity = ((data[7] << 8) | data[8]) / 100.0;
  measurements.push({
    type: 'humidity',
    value: humidity,
    unit: '%RH',
    description: 'Relative Humidity'
  });

  return measurements;
}

// Utility Sensor Parser
function parseUtilitySensor(data) {
  const measurements = [];
  
  // Einfacher Parser für Utility Sensoren
  if (data.length >= 6) {
    const value = (data[2] << 8) | data[3];
    measurements.push({
      type: 'meter_reading',
      value: value,
      unit: 'units',
      description: 'Meter Reading'
    });
  }
  
  return measurements;
}

// Unbekannte Sensor Parser
function parseUnknownSensor(data) {
  return [{
    type: 'raw_data',
    value: data.map(b => b.toString(16).padStart(2, '0')).join(' '),
    unit: 'hex',
    description: 'Raw Hex Data'
  }];
}

// Export für Node.js
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    parseSensorData,
    executeConverterCode,
    convertDecodedToMeasurements
  };
}