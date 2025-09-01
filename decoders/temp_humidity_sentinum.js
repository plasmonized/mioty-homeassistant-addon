
// @name Sentinum Temperature Humidity Decoder
// @version 1.0
// @description Decodes temperature and humidity sensor data

function decode(payload, metadata) {
    if (payload.length < 4) {
        return { error: "Payload too short" };
    }
    
    // Temperature (bytes 0-1)
    const tempRaw = (payload[0] << 8) | payload[1];
    const temperature = (tempRaw - 400) / 10.0;
    
    // Humidity (bytes 2-3) 
    const humRaw = (payload[2] << 8) | payload[3];
    const humidity = humRaw / 100.0;
    
    // Battery (byte 4, optional)
    let battery = null;
    if (payload.length >= 5) {
        battery = payload[4] * 0.1;
    }
    
    const result = {
        temperature: {
            value: Math.round(temperature * 10) / 10,
            unit: "°C"
        },
        humidity: {
            value: Math.round(humidity * 10) / 10, 
            unit: "%"
        }
    };
    
    if (battery !== null) {
        result.battery = {
            value: Math.round(battery * 10) / 10,
            unit: "V"
        };
    }
    
    return result;
}

module.exports = { decode };
