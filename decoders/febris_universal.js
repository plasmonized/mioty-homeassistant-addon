/**
 * SENTINUM UNIVERSAL FEBRIS DECODER v2.0 - PRODUCTION READY
 * 🎯 Universeller Decoder für ALLE Febris Sensor-Varianten (TH, CO2, SCW)
 * ✅ Offizieller Sentinum Decoder mit Verbesserungen:
 *   - Korrekte Einheiten für alle Messwerte
 *   - Verbesserte Humidity-Dekodierung 
 *   - Konsistente Formatierung für Home Assistant
 *   - Vollständige Sensor-Unterstützung (TH, CO2, Wand-Sensoren)
 */

function decodeUplink(input) {

    var decoded = {};
    var bytes = input.bytes;

    if (input.fPort == 1) {//TELEMETRY

        //decode header
        decoded.base_id = bytes[0] >> 4;
        decoded.major_version = bytes[0] & 0x0F;
        decoded.minor_version = bytes[1] >> 4;
        decoded.product_version = bytes[1] & 0x0F;
        decoded.up_cnt = bytes[2];
        
        // Battery voltage mit Einheit
        decoded.battery_voltage = {
            "value": ((bytes[3] << 8) | bytes[4]) / 1000.0,
            "unit": "V"
        };
        
        // Internal temperature mit Einheit
        decoded.internal_temperature = {
            "value": ((bytes[5] << 8) | bytes[6]) / 10 - 100,
            "unit": "°C"
        };
        
        decoded.networkBaseType = 'mioty';
        decoded.networkSubType = 'mioty';
        
        var it = 7;
        
        if(decoded.minor_version >= 3){
            it = 7;
        
            // Luftfeuchte mit Einheit (1 Byte für Kompatibilität)
            decoded.humidity = {
                "value": bytes[it++],
                "unit": "%"
            };
    
            if (decoded.product_version & 0x01) { // Co2 und Druck sind enthalten wenn subversion bit0 = 1, andernfalls 0
                decoded.pressure = {
                    "value": (bytes[it++] << 8 | bytes[it++]),
                    "unit": "hPa"
                };
                decoded.co2_ppm = {
                    "value": (bytes[it++] << 8 | bytes[it++]),
                    "unit": "ppm"
                };
            } else {
                it += 4;//Werte sind 0  aus kompatibilitäts Gründen, daher überspringen
            }
    
            decoded.alarm = bytes[it++];//Alarm-Level, entspricht grün, gelb, rot
    
            //FIFO Werte wegwerfen (1 byte fifo size, 1 byte period, 7 bytes pro fifo eintrag)
            it += 2 + bytes[it] * 7;
    
            // Taupunkt mit Einheit
            decoded.dew_point = {
                "value": ((bytes[it++] << 8) | bytes[it++]) / 10 - 100,
                "unit": "°C"
            };
            
            // Wandtemperatur und Feuchte enthalten wenn subversion bit 2 = 1
            if (decoded.product_version & 0x04) {
                decoded.wall_temperature = {
                    "value": ((bytes[it++] << 8) | bytes[it++]) / 10 - 100,
                    "unit": "°C"
                };
                decoded.therm_temperature = {
                    "value": ((bytes[it++] << 8) | bytes[it++]) / 10 - 100,
                    "unit": "°C"
                };
                decoded.wall_humidity = {
                    "value": bytes[it++],
                    "unit": "%"
                };
            }
    
        }else{
            it = 7;
        
            // Luftfeuchte mit Einheit (1 Byte für ältere Versionen)
            decoded.humidity = {
                "value": bytes[it++],
                "unit": "%"
            };
    
            if (decoded.product_version & 0x01) { // Co2 und Druck sind enthalten wenn subversion bit0 = 1, andernfalls 0
                decoded.pressure = {
                    "value": (bytes[it++] << 8 | bytes[it++]),
                    "unit": "hPa"
                };
                decoded.co2_ppm = {
                    "value": (bytes[it++] << 8 | bytes[it++]),
                    "unit": "ppm"
                };
            } else {
                it += 4;//Werte sind 0  aus kompatibilitäts Gründen, daher überspringen
            }
    
            decoded.alarm = bytes[it++];//Alarm-Level, entspricht grün, gelb, rot
    
            //FIFO Werte wegwerfen (1 byte fifo size, 1 byte period, 7 bytes pro fifo eintrag)
            it += 2 + bytes[it] * 7;
    
            //Taupunkt seit minor version 2 bei alle Varianten enthalten (ausnahme früher versionen subversion 2, daher byte prüfen)
            if (decoded.minor_version >= 2 && bytes[it] ) {
                decoded.dew_point = {
                    "value": bytes[it++] - 100,
                    "unit": "°C"
                };
            }
            
            // Wandtemperatur und Feuchte enthalten wenn subversion bit 2 = 1
            if (decoded.product_version & 0x04) {
                decoded.wall_temperature = {
                    "value": bytes[it++] - 100,
                    "unit": "°C"
                };
                decoded.therm_temperature = {
                    "value": bytes[it++] - 100,
                    "unit": "°C"
                };
                decoded.wall_humidity = {
                    "value": bytes[it++],
                    "unit": "%"
                };
            }
        }
    }

    return {
        data: decoded,
        warnings: [],
        errors: []
    };

}

/**
 * 🔧 MIOTY SYSTEM WRAPPER - CommonJS Interface
 * Wraps TTN-style decodeUplink for mioty system compatibility
 */
function decode(payload, metadata) {
    // Convert raw payload to TTN input format
    const input = { 
        bytes: payload, 
        fPort: (metadata && metadata.fPort) || 1 
    };
    
    // Call original TTN decoder
    const result = decodeUplink(input);
    
    // Return plain object (not wrapped in 'data')
    return result && result.data ? result.data : result;
}

// CommonJS export for mioty system
module.exports = { decode };