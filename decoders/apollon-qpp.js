// Apollon QPP Decoder - Sentinum Format
function decode(payload, metadata) {
    var bytes = payload;
    var port = (metadata && metadata.fPort) || 1;
    
    function val(value, unit) {
        return { value: value, unit: unit };
    }
 
    var decoded = {};
    decoded.deviceType = "apollon";
 
    if (port === 1) {
        decoded.base_id         = bytes[0] >> 4;
        decoded.major_version   = bytes[0] & 0x0F;
        decoded.minor_version   = bytes[1] >> 4;
        decoded.product_version = bytes[1] & 0x0F;

        decoded.up_cnt = bytes[2];
        decoded.battery_voltage = val(((bytes[3] << 8) | bytes[4]) / 1000.0, "V");
        decoded.internal_temperature = val(bytes[5] - 128, "°C");
        
        var status = bytes[6];
        var i = 7;
        decoded.error = 0;

        if (status & 0xF0) {
            decoded.error = status;
        } else if (status === 0) {
            decoded.object_present = false;
        } else {
            decoded.object_present = true;
            decoded.object_status = bytes[i++];
            decoded.object_distance = val((bytes[i++] << 8 | bytes[i++]), "mm");
            decoded.object_sigma = (bytes[i++] << 8 | bytes[i++]);
            decoded.object_signal = (bytes[i++] << 8 | bytes[i++]);
            decoded.object_ambient = (bytes[i++] << 8 | bytes[i++]);
            if (decoded.minor_version >= 2) {
                decoded.object_level = bytes[i++];
            }
        }
    }
    return decoded;
}

module.exports = { decode };
