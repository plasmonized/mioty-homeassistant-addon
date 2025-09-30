// @name Juno Temperature/Humidity Sensor Decoder
// @version 1.0
// @description Decoder für Juno TH Sensoren

function decodeUplink(input) {
    var bytes = input.bytes;
    var port = input.fPort;
    
    // Conversion of signed integers
    function uncomplement(val, bitwidth) {
        var isnegative = val & (1 << (bitwidth - 1));
        var boundary   = (1 << bitwidth);
        var minval     = -boundary;
        var mask       = boundary - 1;
        return isnegative ? minval + (val & mask) : val;
    }
    
    var decoded = {};
    
    if (port === 1) {
        // Attributes
        decoded.base_id         = bytes[0] >> 4;
        decoded.major_version   = bytes[0] & 0x0F;
        decoded.minor_version   = bytes[1] >> 4;
        decoded.product_version = bytes[1] & 0x0F;
        
        // Telemetry
        decoded.up_cnt               = bytes[2];
        decoded.battery_voltage      = {
            value: ((bytes[3] << 8) | bytes[4]) / 1000.0,
            unit: "V"
        };
        decoded.internal_temperature = {
            value: bytes[5] - 128,
            unit: "°C"
        };
        
        decoded.networkBaseType = 'mioty';
        decoded.networkSubType = 'mioty';
        
        if (decoded.minor_version > 1) {
            var idx = 6; // Start of variable size, version dependent payload section
            
            if (decoded.product_version & 0x01) { // Has Precision TH Sensor
                var user_data = bytes[idx++];
                decoded.alarms = {
                    temperatureMaxAlarm: (user_data & (1 << 0)) !== 0,
                    temperatureMinAlarm: (user_data & (1 << 1)) !== 0,
                    temperatureDeltaAlarm: (user_data & (1 << 2)) !== 0,
                    humidityMaxAlarm: (user_data & (1 << 3)) !== 0,
                    humidityMinAlarm: (user_data & (1 << 4)) !== 0,
                    humidityDeltaAlarm: (user_data & (1 << 5)) !== 0
                };
                
                decoded.temperature = {
                    value: ((bytes[idx++] << 8) | bytes[idx++]) / 10 - 100,
                    unit: "°C"
                };
                decoded.humidity = {
                    value: bytes[idx++],
                    unit: "%"
                };
            }
            
            if (decoded.product_version & 0x02) { // Has Acc Tilt functionality
                decoded.orientation = bytes[idx++];
                decoded.open_alarm = bytes[idx++];
                decoded.opended_since_sent = bytes[idx++];
                decoded.opended_since_boot = (bytes[idx++] << 8) | bytes[idx++];
            }
        }
    }
    
    return { data: decoded };
}

module.exports = { decodeUplink };
