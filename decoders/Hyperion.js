
// Hyperion
if (eui.substring(0, 8) == "FCA84A06" && uplink.cmd === "rx") { 

 var dataBlob = new ArrayBuffer(dataBytes.length);
 var dataView = new DataView(dataBlob);

 for(var i = 0; i <dataBytes.length; i++) {
  dataView.setUint8(i,dataBytes[i]);
 }

 var index = 0;
  
 function fetchUint32(littleEndian){
  var offset = index;
  index +=4;
  return dataView.getUint32(offset,littleEndian);
 }

 function fetchUint64(littleEndian){
  var offset = index;
  index +=8;
  var left = dataView.getUint32(offset,littleEndian);
  var right = dataView.getUint32(offset+4,littleEndian);
  var val =  littleEndian ? left + right*Math.pow(32,2) : left*Math.pow(32,2) + right;
  return val;
 }

 function fetchSint8(littleEndian){
  var offset = index;
  index +=1;
  return dataView.getInt8(offset,littleEndian);
 }

 function fetchSint16(littleEndian){
  var offset = index;
  index +=2;
  return dataView.getInt16(offset,littleEndian);
 }

 function fetchSint32(littleEndian){
  var offset = index;
  index +=4;
  return dataView.getInt32(offset,littleEndian);
 }

    var deviceName = 'hyperion_mioty_' + eui;
    var deviceType = 'hyperion';

    result = {
        deviceName: deviceName,
        deviceType: deviceType,
        attributes: {
            devEui: uplink.id,
            versionMajor: ver_maj,
            versionMinor: ver_min,
            deviceSubType: ver_sub,
            networkBaseType: 'mioty',
            networkSubType: 'loriot',
            integrationName: metadata[
                'integrationName'],
            serialNumber: parseInt(dataBytes[4]).toString(16) + parseInt(dataBytes[5]).toString(16) + parseInt(dataBytes[6]).toString(16) + parseInt(dataBytes[7]).toString(16),
            appVer : "v" + parseInt(dataBytes[8]-48) + "." + parseInt(dataBytes[9]-48) + "." + parseInt(dataBytes[10]-48),
            midVer : "v" + parseInt(dataBytes[12]-48) + "." + parseInt(dataBytes[13]-48) + "." + parseInt(dataBytes[14]-48),
        },
        telemetry: {
            uplink_counter: dataBytes[2],
            status : dataBytes[3]
        }
    };
    
    if(ver_min < 3){

        index = 16;//For min 1-2, meter data stats at index 16

        if(ver_min == 1){
  
            if(result.telemetry.status === 1){//Full history entry every 15 mins. Values are sent little endian
            
                result.telemetry["index"] = fetchUint32(true);
                result.telemetry["epoch"] = fetchUint64(true);
                result.telemetry["epoch_old"] = fetchUint64(true);
                result.telemetry["e_t1_a_i"] = fetchUint64(true);
                result.telemetry["e_t2_a_i"] = fetchUint64(true);
                result.telemetry["e_t1_a_e"] = fetchUint64(true);
                result.telemetry["e_t2_a_e"] = fetchUint64(true);
                result.telemetry["e_t1_r_i"] = fetchUint64(true);
                result.telemetry["e_t2_r_i"] = fetchUint64(true);
                result.telemetry["e_t1_r_e"] = fetchUint64(true);
                result.telemetry["e_t2_r_e"] = fetchUint64(true);
                result.telemetry["i_l1"] = fetchSint32(true);//mA
                result.telemetry["i_l2"] = fetchSint32(true);//mA
                result.telemetry["i_l3"] = fetchSint32(true);//mA
                result.telemetry["i_l4"] = fetchSint32(true);//mA
                result.telemetry["i_l123"] = fetchSint32(true);//mA
                result.telemetry["p_l1_a"] = fetchSint32(true);//W
                result.telemetry["p_l2_a"] = fetchSint32(true);//W
                result.telemetry["p_l3_a"] = fetchSint32(true);//W
                result.telemetry["p_l123_a"] = fetchSint32(true);//W
                result.telemetry["p_l123_a_avg"] = fetchSint32(true);//W
                result.telemetry["u_l1"] = fetchSint32(true) / 10;//V
                result.telemetry["u_l2"] = fetchSint32(true) / 10;//V
                result.telemetry["u_l3"] = fetchSint32(true) / 10;//V
                result.telemetry["f"] = fetchSint16(true) / 10;//Hz
                index += 16; // We Skip CT/VT Ratios for now
                result.telemetry["pf_l1"] = fetchSint8(true) / 10;//Hz
                result.telemetry["pf_l2"] = fetchSint8(true) / 10;//Hz
                result.telemetry["pf_l3"] = fetchSint8(true) / 10;//Hz
    
            }else if(result.telemetry.status === 2){//energy import export only. We use big endian here
    
               result.telemetry["e_ta_a_i"] = fetchUint64(false);
               result.telemetry["e_ta_a_e"] = fetchUint64(false);
    
            }  
            
        }else if(ver_min == 2){//Revised parameter set for gerardo
            
            if(result.telemetry.status === 1){//Long payload. All data in big endian
                result.telemetry["p_l1_a"] = fetchSint32(false);//W
                result.telemetry["p_l2_a"] = fetchSint32(false);//W
                result.telemetry["p_l3_a"] = fetchSint32(false);//W
                result.telemetry["p_l123_a"] = fetchSint32(false);//W
                result.telemetry["i_l1"] = fetchSint32(false);//mA
                result.telemetry["i_l2"] = fetchSint32(false);//mA
                result.telemetry["i_l3"] = fetchSint32(false);//mA
                result.telemetry["i_l123"] = fetchSint32(false);//mA
                result.telemetry["u_l1"] = fetchSint32(false) / 10;//V
                result.telemetry["u_l2"] = fetchSint32(false) / 10;//V
                result.telemetry["u_l3"] = fetchSint32(false) / 10;//V
                result.telemetry["e_ta_a_i"] = fetchUint64(false);
                result.telemetry["e_ta_a_e"] = fetchUint64(false);
                result.telemetry["e_ta_r_i"] = fetchUint64(false);
                result.telemetry["e_ta_r_e"] = fetchUint64(false);
                result.telemetry["pf_l1"] = fetchSint8(false) / 100;//Hz
                result.telemetry["pf_l2"] = fetchSint8(false) / 100;//Hz
                result.telemetry["pf_l3"] = fetchSint8(false) / 100;//Hz
                result.telemetry["f"] = fetchSint16(false) / 10;//Hz
                result.telemetry["pwr_fail"] = fetchSint32(false) / 10;//Hz
    
            }else if(result.telemetry.status === 2){//short payload. Current and power only
     
                result.telemetry["p_l1_a"] = fetchSint32(false);//W
                result.telemetry["p_l2_a"] = fetchSint32(false);//W
                result.telemetry["p_l3_a"] = fetchSint32(false);//W
                result.telemetry["p_l123_a"] = fetchSint32(false);//W
                result.telemetry["i_l1"] = fetchSint32(false);//mA
                result.telemetry["i_l2"] = fetchSint32(false);//mA
                result.telemetry["i_l3"] = fetchSint32(false);//mA
                result.telemetry["i_l123"] = fetchSint32(false);//mA
                
            }  

        }


        //This converter does not support versions below 3
        return result;

    }else if(result.telemetry.status != 0){//For ver min 3 and up, status 0 is good, everything else bad
        return result;
    }


    index = 17;
    
    result.telemetry.payload_profile = dataBytes[16];

    /**
     * Due to duty cycle restrictions, we group the payload into different payloads
     * that can be configured via the Meter's UI.
     */

    if(result.telemetry.payload_profile === 0){//Long generic payload. Period 5 minutes. All data in big endian
        result.telemetry["p_l1_a"] = fetchSint32(false);//W
        result.telemetry["p_l2_a"] = fetchSint32(false);//W
        result.telemetry["p_l3_a"] = fetchSint32(false);//W
        result.telemetry["p_l123_a"] = fetchSint32(false);//W
        result.telemetry["i_l1"] = fetchSint32(false);//mA
        result.telemetry["i_l2"] = fetchSint32(false);//mA
        result.telemetry["i_l3"] = fetchSint32(false);//mA
        result.telemetry["i_l123"] = fetchSint32(false);//mA
        result.telemetry["u_l1"] = fetchSint32(false) / 10;//V
        result.telemetry["u_l2"] = fetchSint32(false) / 10;//V
        result.telemetry["u_l3"] = fetchSint32(false) / 10;//V
        result.telemetry["u_l12"] = fetchSint32(false) / 10;//V
        result.telemetry["u_l23"] = fetchSint32(false) / 10;//V
        result.telemetry["u_l31"] = fetchSint32(false) / 10;//V
        result.telemetry["e_ta_a_i"] = fetchUint64(false);
        result.telemetry["e_ta_a_e"] = fetchUint64(false);
        result.telemetry["e_ta_r_i"] = fetchUint64(false);
        result.telemetry["e_ta_r_e"] = fetchUint64(false);
        result.telemetry["pf_l1"] = fetchSint8(false) / 100;//Hz
        result.telemetry["pf_l2"] = fetchSint8(false) / 100;//Hz
        result.telemetry["pf_l3"] = fetchSint8(false) / 100;//Hz
        result.telemetry["f"] = fetchSint16(false) / 10;//Hz
        result.telemetry["pwr_fail"] = fetchUint32(false) ;

    }else if(result.telemetry.payload_profile === 1){//short payload. Current and power only
        result.telemetry["rawlen"] = dataBytes.length;
        result.telemetry["u_l1"] = fetchSint32(false) / 10;//V
        result.telemetry["u_l2"] = fetchSint32(false) / 10;//V
        result.telemetry["u_l3"] = fetchSint32(false) / 10;//V
        result.telemetry["u_l12"] = fetchSint32(false) / 10;//V
        result.telemetry["u_l23"] = fetchSint32(false) / 10;//V
        result.telemetry["u_l31"] = fetchSint32(false) / 10;//V
        result.telemetry["i_l1"] = fetchSint32(false);//mA
        result.telemetry["i_l2"] = fetchSint32(false);//mA
        result.telemetry["i_l3"] = fetchSint32(false);//mA
        result.telemetry["i_l123"] = fetchSint32(false);//mA
        result.telemetry["pf_l1"] = fetchSint8(false) / 100;//Hz
        result.telemetry["pf_l2"] = fetchSint8(false) / 100;//Hz
        result.telemetry["pf_l3"] = fetchSint8(false) / 100;//Hz
        result.telemetry["f"] = fetchSint16(false) / 10;//Hz

    }else if(result.telemetry.payload_profile === 2){//short payload. Current and power only

        result.telemetry["p_l1_a"] = fetchSint32(false);//W
        result.telemetry["p_l2_a"] = fetchSint32(false);//W
        result.telemetry["p_l3_a"] = fetchSint32(false);//W
        result.telemetry["p_l123_a"] = fetchSint32(false);//W
        result.telemetry["i_l1"] = fetchSint32(false);//mA
        result.telemetry["i_l2"] = fetchSint32(false);//mA
        result.telemetry["i_l3"] = fetchSint32(false);//mA
        result.telemetry["i_l123"] = fetchSint32(false);//mA
        result.telemetry["pf_l1"] = fetchSint8(false) / 100;//Hz
        result.telemetry["pf_l2"] = fetchSint8(false) / 100;//Hz
        result.telemetry["pf_l3"] = fetchSint8(false) / 100;//Hz
        result.telemetry["f"] = fetchSint16(false) / 10;//Hz

    }else if(result.telemetry.payload_profile === 3){//fast energy metering every 2 minutes

        result.telemetry["e_ta_a_i"] = fetchUint64(false);
        result.telemetry["e_ta_a_e"] = fetchUint64(false);
        result.telemetry["e_ta_r_i"] = fetchUint64(false);
        result.telemetry["e_ta_r_e"] = fetchUint64(false);

    }  else if(result.telemetry.payload_profile === 4){

        /*
            This is the emu legacy telegram profile. It contains an historic record
            as defined by emu and will be send according to emus historic recods
            update interval which can be configured via the user interface. Minimum however
            is 5 minutes due to duty-cycle restrictions.
        */

        result.telemetry["index"] = fetchUint32(true);
        result.telemetry["epoch"] = fetchUint64(true);
        result.telemetry["epoch_old"] = fetchUint64(true);
        result.telemetry["e_t1_a_i"] = fetchUint64(true);
        result.telemetry["e_t2_a_i"] = fetchUint64(true);
        result.telemetry["e_t1_a_e"] = fetchUint64(true);
        result.telemetry["e_t2_a_e"] = fetchUint64(true);
        result.telemetry["e_t1_r_i"] = fetchUint64(true);
        result.telemetry["e_t2_r_i"] = fetchUint64(true);
        result.telemetry["e_t1_r_e"] = fetchUint64(true);
        result.telemetry["e_t2_r_e"] = fetchUint64(true);
        result.telemetry["i_l1"] = fetchSint32(true);//mA
        result.telemetry["i_l2"] = fetchSint32(true);//mA
        result.telemetry["i_l3"] = fetchSint32(true);//mA
        result.telemetry["i_l4"] = fetchSint32(true);//mA
        result.telemetry["i_l123"] = fetchSint32(true);//mA
        result.telemetry["p_l1_a"] = fetchSint32(true);//W
        result.telemetry["p_l2_a"] = fetchSint32(true);//W
        result.telemetry["p_l3_a"] = fetchSint32(true);//W
        result.telemetry["p_l123_a"] = fetchSint32(true);//W
        result.telemetry["p_l123_a_avg"] = fetchSint32(true);//W
        result.telemetry["u_l1"] = fetchSint32(true) / 10;//V
        result.telemetry["u_l2"] = fetchSint32(true) / 10;//V
        result.telemetry["u_l3"] = fetchSint32(true) / 10;//V
        result.telemetry["f"] = fetchSint16(true) / 10;//Hz
        index += 16; // We Skip CT/VT Ratios for now
        result.telemetry["pf_l1"] = fetchSint8(true) / 10;//Hz
        result.telemetry["pf_l2"] = fetchSint8(true) / 10;//Hz
        result.telemetry["pf_l3"] = fetchSint8(true) / 10;//Hz

    }  
        
}