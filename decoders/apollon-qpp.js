// Up to Date Apollon decoder
function Decoder(bytes, port) {
 
    var decoded = {};
 
    if (port === 1) {
 
        // Attributes
        decoded.base_id         = bytes[0] >> 4;
        decoded.major_version   = bytes[0] & 0x0F;
        decoded.minor_version   = bytes[1] >> 4;
        decoded.product_version = bytes[1] & 0x0F;
 
        // Telemetry
        decoded.up_cnt               = bytes[2];
        decoded.battery_voltage      = ((bytes[3] << 8) | bytes[4]) / 1000.0;
        decoded.internal_temperature = bytes[5] - 128;
        var status = bytes[6];
 
        var i = 7;//Index of first byte containing status specific payload
        decoded.error = 0;
 
        if(status & 0xF0){
          decoded.error = status;
        } else if(status === 0){
          decoded.object_present = false;
        } else {
          decoded.object_present = true;
                decoded["object_status"] = bytes[i++];
                decoded["object_distance"] = bytes[i++] << 8 | bytes[i++];
                decoded["object_sigma"] = bytes[i++] << 8 | bytes[i++];
                decoded["object_signal"] = bytes[i++] << 8 | bytes[i++];
                decoded["object_ambient"] = bytes[i++] << 8 | bytes[i++];
                if(decoded.minor_version >= 2){
                    decoded["object_level"] = bytes[i++];
                }

        }
 
    }
    return decoded;
}