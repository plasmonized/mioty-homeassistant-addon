// Hyperion Decoder für mioty Application Center
// Konvertiert von Original-Format zu Sentinum-kompatiblem Format

function decode(dataBytes, metadata) {
    var result = {};
    
    if (!dataBytes || dataBytes.length < 16) {
        return { error: "Payload zu kurz (min. 16 Bytes)", raw_length: dataBytes ? dataBytes.length : 0 };
    }
    
    var dataBlob = new ArrayBuffer(dataBytes.length);
    var dataView = new DataView(dataBlob);
    
    for (var i = 0; i < dataBytes.length; i++) {
        dataView.setUint8(i, dataBytes[i]);
    }
    
    var index = 0;
    
    function fetchUint32(littleEndian) {
        var offset = index;
        index += 4;
        if (offset + 4 > dataBytes.length) return 0;
        return dataView.getUint32(offset, littleEndian);
    }
    
    function fetchUint64(littleEndian) {
        var offset = index;
        index += 8;
        if (offset + 8 > dataBytes.length) return 0;
        var left = dataView.getUint32(offset, littleEndian);
        var right = dataView.getUint32(offset + 4, littleEndian);
        var val = littleEndian ? left + right * Math.pow(2, 32) : left * Math.pow(2, 32) + right;
        return val;
    }
    
    function fetchSint8(littleEndian) {
        var offset = index;
        index += 1;
        if (offset + 1 > dataBytes.length) return 0;
        return dataView.getInt8(offset, littleEndian);
    }
    
    function fetchSint16(littleEndian) {
        var offset = index;
        index += 2;
        if (offset + 2 > dataBytes.length) return 0;
        return dataView.getInt16(offset, littleEndian);
    }
    
    function fetchSint32(littleEndian) {
        var offset = index;
        index += 4;
        if (offset + 4 > dataBytes.length) return 0;
        return dataView.getInt32(offset, littleEndian);
    }
    
    // Header parsing
    var ver_maj = dataBytes[0];
    var ver_min = dataBytes[1];
    var ver_sub = dataBytes[11] || 0;
    
    result.deviceType = 'hyperion';
    result.uplink_counter = dataBytes[2];
    result.status = dataBytes[3];
    
    // Serial number aus Bytes 4-7
    result.serialNumber = 
        dataBytes[4].toString(16).padStart(2, '0') + 
        dataBytes[5].toString(16).padStart(2, '0') + 
        dataBytes[6].toString(16).padStart(2, '0') + 
        dataBytes[7].toString(16).padStart(2, '0');
    
    // App/Mid Version
    if (dataBytes.length > 14) {
        result.appVer = "v" + (dataBytes[8] - 48) + "." + (dataBytes[9] - 48) + "." + (dataBytes[10] - 48);
        result.midVer = "v" + (dataBytes[12] - 48) + "." + (dataBytes[13] - 48) + "." + (dataBytes[14] - 48);
    }
    
    result.version_major = ver_maj;
    result.version_minor = ver_min;
    
    if (ver_min < 3) {
        index = 16;
        
        if (ver_min == 1) {
            if (result.status === 1 && dataBytes.length >= 140) {
                result.index_val = fetchUint32(true);
                result.epoch = fetchUint64(true);
                result.epoch_old = fetchUint64(true);
                result.e_t1_a_i = fetchUint64(true); result.e_t1_a_i_unit = "Wh";
                result.e_t2_a_i = fetchUint64(true); result.e_t2_a_i_unit = "Wh";
                result.e_t1_a_e = fetchUint64(true); result.e_t1_a_e_unit = "Wh";
                result.e_t2_a_e = fetchUint64(true); result.e_t2_a_e_unit = "Wh";
                result.e_t1_r_i = fetchUint64(true); result.e_t1_r_i_unit = "Wh";
                result.e_t2_r_i = fetchUint64(true); result.e_t2_r_i_unit = "Wh";
                result.e_t1_r_e = fetchUint64(true); result.e_t1_r_e_unit = "Wh";
                result.e_t2_r_e = fetchUint64(true); result.e_t2_r_e_unit = "Wh";
                result.i_l1 = fetchSint32(true); result.i_l1_unit = "mA";
                result.i_l2 = fetchSint32(true); result.i_l2_unit = "mA";
                result.i_l3 = fetchSint32(true); result.i_l3_unit = "mA";
                result.i_l4 = fetchSint32(true); result.i_l4_unit = "mA";
                result.i_l123 = fetchSint32(true); result.i_l123_unit = "mA";
                result.p_l1_a = fetchSint32(true); result.p_l1_a_unit = "W";
                result.p_l2_a = fetchSint32(true); result.p_l2_a_unit = "W";
                result.p_l3_a = fetchSint32(true); result.p_l3_a_unit = "W";
                result.p_l123_a = fetchSint32(true); result.p_l123_a_unit = "W";
                result.p_l123_a_avg = fetchSint32(true); result.p_l123_a_avg_unit = "W";
                result.u_l1 = fetchSint32(true) / 10; result.u_l1_unit = "V";
                result.u_l2 = fetchSint32(true) / 10; result.u_l2_unit = "V";
                result.u_l3 = fetchSint32(true) / 10; result.u_l3_unit = "V";
                result.f = fetchSint16(true) / 10; result.f_unit = "Hz";
                index += 16;
                result.pf_l1 = fetchSint8(true) / 10;
                result.pf_l2 = fetchSint8(true) / 10;
                result.pf_l3 = fetchSint8(true) / 10;
            } else if (result.status === 2) {
                result.e_ta_a_i = fetchUint64(false); result.e_ta_a_i_unit = "Wh";
                result.e_ta_a_e = fetchUint64(false); result.e_ta_a_e_unit = "Wh";
            }
        } else if (ver_min == 2) {
            if (result.status === 1) {
                result.p_l1_a = fetchSint32(false); result.p_l1_a_unit = "W";
                result.p_l2_a = fetchSint32(false); result.p_l2_a_unit = "W";
                result.p_l3_a = fetchSint32(false); result.p_l3_a_unit = "W";
                result.p_l123_a = fetchSint32(false); result.p_l123_a_unit = "W";
                result.i_l1 = fetchSint32(false); result.i_l1_unit = "mA";
                result.i_l2 = fetchSint32(false); result.i_l2_unit = "mA";
                result.i_l3 = fetchSint32(false); result.i_l3_unit = "mA";
                result.i_l123 = fetchSint32(false); result.i_l123_unit = "mA";
                result.u_l1 = fetchSint32(false) / 10; result.u_l1_unit = "V";
                result.u_l2 = fetchSint32(false) / 10; result.u_l2_unit = "V";
                result.u_l3 = fetchSint32(false) / 10; result.u_l3_unit = "V";
                result.e_ta_a_i = fetchUint64(false); result.e_ta_a_i_unit = "Wh";
                result.e_ta_a_e = fetchUint64(false); result.e_ta_a_e_unit = "Wh";
                result.e_ta_r_i = fetchUint64(false); result.e_ta_r_i_unit = "Wh";
                result.e_ta_r_e = fetchUint64(false); result.e_ta_r_e_unit = "Wh";
                result.pf_l1 = fetchSint8(false) / 100;
                result.pf_l2 = fetchSint8(false) / 100;
                result.pf_l3 = fetchSint8(false) / 100;
                result.f = fetchSint16(false) / 10; result.f_unit = "Hz";
                result.pwr_fail = fetchSint32(false) / 10;
            } else if (result.status === 2) {
                result.p_l1_a = fetchSint32(false); result.p_l1_a_unit = "W";
                result.p_l2_a = fetchSint32(false); result.p_l2_a_unit = "W";
                result.p_l3_a = fetchSint32(false); result.p_l3_a_unit = "W";
                result.p_l123_a = fetchSint32(false); result.p_l123_a_unit = "W";
                result.i_l1 = fetchSint32(false); result.i_l1_unit = "mA";
                result.i_l2 = fetchSint32(false); result.i_l2_unit = "mA";
                result.i_l3 = fetchSint32(false); result.i_l3_unit = "mA";
                result.i_l123 = fetchSint32(false); result.i_l123_unit = "mA";
            }
        }
        return result;
    }
    
    if (result.status === 2) {
        index = 16;
        result.e_ta_a_i = fetchUint64(false); result.e_ta_a_i_unit = "Wh";
        result.e_ta_a_e = fetchUint64(false); result.e_ta_a_e_unit = "Wh";
        return result;
    }
    
    if (result.status === 1) {
        index = 16;
        result.p_l123_a = fetchSint32(true); result.p_l123_a_unit = "W";
        result.epoch = fetchUint64(true);
        result.epoch_old = fetchUint64(true);
        result.e_t1_a_i = fetchUint64(true); result.e_t1_a_i_unit = "Wh";
        result.e_t2_a_i = fetchUint64(true); result.e_t2_a_i_unit = "Wh";
        result.e_t1_a_e = fetchUint64(true); result.e_t1_a_e_unit = "Wh";
        result.e_t2_a_e = fetchUint64(true); result.e_t2_a_e_unit = "Wh";
        result.i_l123 = fetchSint32(true); result.i_l123_unit = "mA";
        index = 84;
        result.e_ta_a_i = fetchUint64(true); result.e_ta_a_i_unit = "Wh";
        return result;
    }
    
    if (result.status != 0) {
        return result;
    }
    
    index = 17;
    result.payload_profile = dataBytes[16];
    
    if (result.payload_profile === 0) {
        result.p_l1_a = fetchSint32(false); result.p_l1_a_unit = "W";
        result.p_l2_a = fetchSint32(false); result.p_l2_a_unit = "W";
        result.p_l3_a = fetchSint32(false); result.p_l3_a_unit = "W";
        result.p_l123_a = fetchSint32(false); result.p_l123_a_unit = "W";
        result.i_l1 = fetchSint32(false); result.i_l1_unit = "mA";
        result.i_l2 = fetchSint32(false); result.i_l2_unit = "mA";
        result.i_l3 = fetchSint32(false); result.i_l3_unit = "mA";
        result.i_l123 = fetchSint32(false); result.i_l123_unit = "mA";
        result.u_l1 = fetchSint32(false) / 10; result.u_l1_unit = "V";
        result.u_l2 = fetchSint32(false) / 10; result.u_l2_unit = "V";
        result.u_l3 = fetchSint32(false) / 10; result.u_l3_unit = "V";
        result.u_l12 = fetchSint32(false) / 10; result.u_l12_unit = "V";
        result.u_l23 = fetchSint32(false) / 10; result.u_l23_unit = "V";
        result.u_l31 = fetchSint32(false) / 10; result.u_l31_unit = "V";
        result.e_ta_a_i = fetchUint64(false); result.e_ta_a_i_unit = "Wh";
        result.e_ta_a_e = fetchUint64(false); result.e_ta_a_e_unit = "Wh";
        result.e_ta_r_i = fetchUint64(false); result.e_ta_r_i_unit = "Wh";
        result.e_ta_r_e = fetchUint64(false); result.e_ta_r_e_unit = "Wh";
        result.pf_l1 = fetchSint8(false) / 100;
        result.pf_l2 = fetchSint8(false) / 100;
        result.pf_l3 = fetchSint8(false) / 100;
        result.f = fetchSint16(false) / 10; result.f_unit = "Hz";
        result.pwr_fail = fetchUint32(false);
    } else if (result.payload_profile === 1) {
        result.u_l1 = fetchSint32(false) / 10; result.u_l1_unit = "V";
        result.u_l2 = fetchSint32(false) / 10; result.u_l2_unit = "V";
        result.u_l3 = fetchSint32(false) / 10; result.u_l3_unit = "V";
        result.u_l12 = fetchSint32(false) / 10; result.u_l12_unit = "V";
        result.u_l23 = fetchSint32(false) / 10; result.u_l23_unit = "V";
        result.u_l31 = fetchSint32(false) / 10; result.u_l31_unit = "V";
        result.i_l1 = fetchSint32(false); result.i_l1_unit = "mA";
        result.i_l2 = fetchSint32(false); result.i_l2_unit = "mA";
        result.i_l3 = fetchSint32(false); result.i_l3_unit = "mA";
        result.i_l123 = fetchSint32(false); result.i_l123_unit = "mA";
        result.pf_l1 = fetchSint8(false) / 100;
        result.pf_l2 = fetchSint8(false) / 100;
        result.pf_l3 = fetchSint8(false) / 100;
        result.f = fetchSint16(false) / 10; result.f_unit = "Hz";
    } else if (result.payload_profile === 2) {
        result.p_l1_a = fetchSint32(false); result.p_l1_a_unit = "W";
        result.p_l2_a = fetchSint32(false); result.p_l2_a_unit = "W";
        result.p_l3_a = fetchSint32(false); result.p_l3_a_unit = "W";
        result.p_l123_a = fetchSint32(false); result.p_l123_a_unit = "W";
        result.i_l1 = fetchSint32(false); result.i_l1_unit = "mA";
        result.i_l2 = fetchSint32(false); result.i_l2_unit = "mA";
        result.i_l3 = fetchSint32(false); result.i_l3_unit = "mA";
        result.i_l123 = fetchSint32(false); result.i_l123_unit = "mA";
        result.pf_l1 = fetchSint8(false) / 100;
        result.pf_l2 = fetchSint8(false) / 100;
        result.pf_l3 = fetchSint8(false) / 100;
        result.f = fetchSint16(false) / 10; result.f_unit = "Hz";
    } else if (result.payload_profile === 3) {
        result.e_ta_a_i = fetchUint64(false); result.e_ta_a_i_unit = "Wh";
        result.e_ta_a_e = fetchUint64(false); result.e_ta_a_e_unit = "Wh";
        result.e_ta_r_i = fetchUint64(false); result.e_ta_r_i_unit = "Wh";
        result.e_ta_r_e = fetchUint64(false); result.e_ta_r_e_unit = "Wh";
    } else if (result.payload_profile === 4) {
        result.index_val = fetchUint32(true);
        result.epoch = fetchUint64(true);
        result.epoch_old = fetchUint64(true);
        result.e_t1_a_i = fetchUint64(true); result.e_t1_a_i_unit = "Wh";
        result.e_t2_a_i = fetchUint64(true); result.e_t2_a_i_unit = "Wh";
        result.e_t1_a_e = fetchUint64(true); result.e_t1_a_e_unit = "Wh";
        result.e_t2_a_e = fetchUint64(true); result.e_t2_a_e_unit = "Wh";
        result.e_t1_r_i = fetchUint64(true); result.e_t1_r_i_unit = "Wh";
        result.e_t2_r_i = fetchUint64(true); result.e_t2_r_i_unit = "Wh";
        result.e_t1_r_e = fetchUint64(true); result.e_t1_r_e_unit = "Wh";
        result.e_t2_r_e = fetchUint64(true); result.e_t2_r_e_unit = "Wh";
        result.i_l1 = fetchSint32(true); result.i_l1_unit = "mA";
        result.i_l2 = fetchSint32(true); result.i_l2_unit = "mA";
        result.i_l3 = fetchSint32(true); result.i_l3_unit = "mA";
        result.i_l4 = fetchSint32(true); result.i_l4_unit = "mA";
        result.i_l123 = fetchSint32(true); result.i_l123_unit = "mA";
        result.p_l1_a = fetchSint32(true); result.p_l1_a_unit = "W";
        result.p_l2_a = fetchSint32(true); result.p_l2_a_unit = "W";
        result.p_l3_a = fetchSint32(true); result.p_l3_a_unit = "W";
        result.p_l123_a = fetchSint32(true); result.p_l123_a_unit = "W";
        result.p_l123_a_avg = fetchSint32(true); result.p_l123_a_avg_unit = "W";
        result.u_l1 = fetchSint32(true) / 10; result.u_l1_unit = "V";
        result.u_l2 = fetchSint32(true) / 10; result.u_l2_unit = "V";
        result.u_l3 = fetchSint32(true) / 10; result.u_l3_unit = "V";
        result.f = fetchSint16(true) / 10; result.f_unit = "Hz";
        index += 16;
        result.pf_l1 = fetchSint8(true) / 10;
        result.pf_l2 = fetchSint8(true) / 10;
        result.pf_l3 = fetchSint8(true) / 10;
    }
    
    return result;
}

module.exports = { decode };
