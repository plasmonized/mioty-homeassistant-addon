function decode(hex) {
    var bytes = [];
    for (var i = 0; i < hex.length; i += 2) {
        bytes.push(parseInt(hex.substr(i, 2), 16));
    }

    function val(value, unit) {
        return { value: value, unit: unit };
    }

    var decoded = {};
    decoded.deviceType = "nyx";

    decoded.base_id = bytes[0] >> 4;
    decoded.major_version = bytes[0] & 0x0F;
    decoded.minor_version = bytes[1] >> 4;
    decoded.product_version = bytes[1] & 0x0F;
    decoded.up_cnt = bytes[2];
    
    decoded.battery_voltage = val(((bytes[3] << 8) | bytes[4]) / 1000.0, "V");
    decoded.internal_temperature = val(((bytes[5] << 8) | bytes[6]) / 10 - 100, "°C");

    var it = 7;
    if (decoded.major_version >= 1 && bytes.length > 10) {
        decoded.humidity = val(bytes[it++], "%");
        decoded.dew_point = val(((bytes[it++] << 8) | bytes[it++]) / 10 - 100, "°C");
        decoded.alarm_level = bytes[it++];

        if (decoded.product_version & 0x01) {
            if (it + 1 < bytes.length) {
                var raw_lux = (bytes[it++] << 8 | bytes[it++]);
                decoded.lux = val((1 << (raw_lux >> 12)) * (raw_lux & 0x0FFF) * 0.01, "lx");
            }
        }

        if (decoded.product_version & 0x04) {
            if (it < bytes.length) {
                decoded.bme_status = bytes[it++];
            }
            if (it + 1 < bytes.length) {
                decoded.pressure = val((bytes[it++] << 8 | bytes[it++]), "hPa");
            }
            if (decoded.product_version & 0x02) {
                if (it < bytes.length) {
                    decoded.iaq_status = bytes[it++];
                }
                if (it + 1 < bytes.length) {
                    decoded.iaq_index = (bytes[it++] << 8 | bytes[it++]);
                }
            }
        }
    }

    return decoded;
}

module.exports = { decode };
