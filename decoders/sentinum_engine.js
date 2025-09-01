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

// Export für Node.js
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    parseSensorData,
    executeConverterCode
  };
}