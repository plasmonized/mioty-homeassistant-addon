function decodeUplink(input) { 

 

    var decoded = {}; 

    var bytes = input.bytes; 

 

    if (input.fPort == 1) { //TELEMETRY 

 

        //decode header 

        decoded.base_id = bytes[0] >> 4; 

        decoded.major_version = bytes[0] & 0x0F; 

        decoded.minor_version = bytes[1] >> 4; 

        decoded.product_version = bytes[1] & 0x0F; 

        decoded.up_cnt = bytes[2]; 

        decoded.battery_voltage = ((bytes[3] << 8) | bytes[4]) / 1000.0; 

        decoded.internal_temperature = ((bytes[5] << 8) | bytes[6]) / 10 - 100; 

        decoded.networkBaseType = 'lorawan'; 

        decoded.networkSubType = 'tti'; 

        var it = 7; 

        if (decoded.major_version >= 1) { 

            it = 7; 

            //Luftfeuchte ist bei allen Varianten enthalten 

            decoded.humidity = bytes[it++]; 

            decoded.dew_point = ((bytes[it++] << 8) | bytes[it++]) / 10 - 100; 

            decoded.alarm_level = bytes[it++]; //Alarm-Level, entspricht grün, gelb, rot 

 

            if (decoded.product_version & 0x01) { //  Lux Sensor 

                var raw_lux = (bytes[it++] << 8 | bytes[it++]); 

                // decoded.lux_status = raw_lux != 0xffff ? 0 : 1; //raw value is 0xFFFF in case of error 

                decoded.lux = (1 << (raw_lux >> 12)) * (raw_lux & 0x0FFF) * 0.01; 

            } 

 

            if (decoded.product_version & 0x04) { //  Has Bme688 Sensor 

                decoded.bme_status = bytes[it++]; 

                decoded.pressure = (bytes[it++] << 8 | bytes[it++]); 

                if (decoded.product_version & 0x02) { // Has IAQ Feature 

                    decoded.iaq_status = bytes[it++]; 

                    decoded.iaq_index = (bytes[it++] << 8 | bytes[it++]); 

                } 

            } 

        } 

    } 

 

    return { 

        data: decoded, 

        warnings: [], 

        errors: [] 

    }; 

 

}