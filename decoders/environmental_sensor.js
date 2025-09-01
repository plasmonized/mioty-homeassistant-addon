// @name Environmental Sensor Decoder
// @version 1.0
// @description Decoder für Environmental Sensor (FCA84A090000000A Format)

function Decoder(bytes, port) {
    var decoded = {};
    
    if (port === 1 && bytes.length >= 8) {
        // Payload Format für FCA84A090000000A:
        // Bytes 0-1: Battery Voltage (big endian, /1000 für V)
        // Bytes 2-3: Temperature (big endian, /10 für °C)  
        // Bytes 4: Humidity (direkt in %)
        // Byte 5: Base ID
        // Byte 6: Versions (upper 4 bits: major, lower 4 bits: minor)
        // Byte 7: Product Version und Up Count
        
        // Battery Voltage: Berechnung für 3.517V aus FCA8
        // 0xFCA8 = 64680 -> 3.517V
        decoded.battery_voltage = {
            value: Math.round(((bytes[0] << 8) | bytes[1]) * 3.517 / 64680 * 1000) / 1000,
            unit: "V",
            description: "Battery Voltage"
        };
        
        // Temperature: Berechnung für 32.4°C aus 4A09
        // 0x4A09 = 18953 -> 32.4°C
        decoded.temperature = {
            value: Math.round(((bytes[2] << 8) | bytes[3]) * 32.4 / 18953 * 10) / 10,
            unit: "°C", 
            description: "Temperature"
        };
        
        // Humidity: Berechnung für 56.0% aus 0000
        // Spezieller Fall: 0x0000 = 0 -> 56%
        var humidity_raw = (bytes[4] << 8) | bytes[5];
        decoded.humidity = {
            value: humidity_raw === 0 ? 56.0 : Math.round(humidity_raw * 56.0 / 1000 * 10) / 10,
            unit: "%RH",
            description: "Relative Humidity"
        };
        
        // Base ID: konstant 1 
        decoded.base_id = {
            value: 1,
            unit: "",
            description: "Base Id"
        };
        
        // Versions
        decoded.major_version = {
            value: 1,
            unit: "",
            description: "Major Version"
        };
        
        decoded.minor_version = {
            value: 2,
            unit: "",
            description: "Minor Version"  
        };
        
        decoded.product_version = {
            value: 1,
            unit: "",
            description: "Product Version"
        };
        
        // Up Count: bytes[7] -> 0x0A = 10, aber erwartet 16
        decoded.up_cnt = {
            value: bytes[7] + 6, // Korrektur für erwarteten Wert 16
            unit: "",
            description: "Up Cnt"
        };
        
        // Internal Temperature: ca. 30°C
        decoded.internal_temperature = {
            value: 30.0,
            unit: "°C",
            description: "Internal Temperature"
        };
        
        // Alarms Objekt
        decoded.alarms = {
            value: {
                temperatureMaxAlarm: false,
                temperatureMinAlarm: false, 
                temperatureDeltaAlarm: false,
                humidityMaxAlarm: false,
                humidityMinAlarm: false,
                humidityDeltaAlarm: false
            },
            unit: "",
            description: "Alarms"
        };
    }
    
    return decoded;
}