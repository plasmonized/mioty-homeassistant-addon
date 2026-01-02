"""
IODD Parser Module
Parses IODD XML files and extracts ProcessData structure

Supports all IODD namespaces: 2010/10, 2011/10, 2013/10, 2017/10, 2023/01
Uses namespace-agnostic parsing for maximum compatibility.
Supports both lxml and standard library xml.etree.ElementTree.
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

try:
    from lxml import etree
    LXML_AVAILABLE = True
except ImportError:
    import xml.etree.ElementTree as etree
    LXML_AVAILABLE = False


@dataclass
class ProcessDataVariable:
    """Represents a variable in the process data"""
    name: str
    bit_offset: int
    bit_length: int
    datatype: str
    unit: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    description: Optional[str] = None
    scale_gradient: Optional[float] = None
    scale_offset: Optional[float] = None
    path: Optional[str] = None


def _ln(tag: str) -> str:
    """Extract local name from a qualified tag name (strips namespace)."""
    if '}' in tag:
        return tag.split('}', 1)[1]
    return tag


def _find_one(node, local_name: str):
    """Find first child element by local name, ignoring namespace."""
    if LXML_AVAILABLE:
        result = node.xpath(f"./*[local-name()='{local_name}']")
        return result[0] if result else None
    else:
        for child in node:
            if _ln(child.tag) == local_name:
                return child
        return None


def _find_all(node, local_name: str) -> List:
    """Find all child elements by local name, ignoring namespace."""
    if LXML_AVAILABLE:
        return node.xpath(f"./*[local-name()='{local_name}']")
    else:
        return [child for child in node if _ln(child.tag) == local_name]


def _find_descendants(node, local_name: str) -> List:
    """Find all descendant elements by local name, ignoring namespace."""
    if LXML_AVAILABLE:
        return node.xpath(f".//*[local-name()='{local_name}']")
    else:
        result = []
        for child in node.iter():
            if _ln(child.tag) == local_name:
                result.append(child)
        return result


class IODDParser:
    """Parses IODD XML files and extracts device information"""
    
    UNIT_MAP = {
        '1000': 'mm', '1001': 'cm', '1002': 'm', '1003': 'km',
        '1004': 'inch', '1005': 'ft', '1006': 'yd', '1007': 'mi',
        '1010': '°C', '1011': 'K', '1012': '°F',
        '1020': 'bar', '1021': 'mbar', '1022': 'Pa', '1023': 'kPa',
        '1024': 'MPa', '1025': 'psi',
        '1030': 'l', '1031': 'ml', '1032': 'm³', '1033': 'cm³',
        '1040': 'g', '1041': 'kg', '1042': 'mg', '1043': 't',
        '1044': 'lb', '1045': 'oz',
        '1050': 's', '1051': 'ms', '1052': 'µs', '1053': 'min',
        '1054': 'h', '1055': 'd',
        '1060': 'Hz', '1061': 'kHz', '1062': 'MHz', '1063': 'GHz',
        '1064': 'rpm',
        '1070': 'V', '1071': 'mV', '1072': 'kV', '1073': 'µV',
        '1080': 'A', '1081': 'mA', '1082': 'µA', '1083': 'kA',
        '1090': 'W', '1091': 'kW', '1092': 'mW', '1093': 'MW',
        '1100': '%', '1101': 'ppm', '1102': 'ppb',
        '1110': 'Ω', '1111': 'kΩ', '1112': 'mΩ', '1113': 'MΩ',
        '1120': 'F', '1121': 'µF', '1122': 'nF', '1123': 'pF',
        '1130': 'H', '1131': 'mH', '1132': 'µH',
        '1140': 'N', '1141': 'kN', '1142': 'mN',
        '1150': 'Nm', '1151': 'kNm', '1152': 'mNm',
        '1160': 'm/s', '1161': 'km/h', '1162': 'mm/s', '1163': 'm/min',
        '1170': 'm/s²', '1171': 'mm/s²', '1172': 'g',
        '1180': 'l/min', '1181': 'l/h', '1182': 'm³/h', '1183': 'ml/min',
        '1190': '°', '1191': 'rad', '1192': 'mrad',
        '1200': 'lux', '1201': 'lm', '1202': 'cd',
        '1210': 'dB', '1211': 'dBA',
        '1220': 'J', '1221': 'kJ', '1222': 'Wh', '1223': 'kWh',
        '1230': 'S', '1231': 'mS', '1232': 'µS',
        '1240': 'kg/m³', '1241': 'g/cm³', '1242': 'g/l',
    }
    
    DATATYPE_BIT_LENGTHS = {
        'BooleanT': 1, 'UIntegerT': 32, 'IntegerT': 32,
        'UInteger8T': 8, 'Integer8T': 8,
        'UInteger16T': 16, 'Integer16T': 16,
        'UInteger32T': 32, 'Integer32T': 32,
        'UInteger64T': 64, 'Integer64T': 64,
        'Float32T': 32, 'Float64T': 64,
        'OctetStringT': 8, 'StringT': 8,
    }
    
    def __init__(self, iodd_path: Path):
        """Initialize the IODD parser"""
        self.iodd_path = Path(iodd_path)
        self.tree = None
        self.root = None
        self.text_catalog: Dict[str, str] = {}
        self.datatype_catalog: Dict[str, Any] = {}
        self._parse_xml()
        self._build_text_catalog()
        self._build_datatype_catalog()
        
    def _parse_xml(self):
        """Parse the IODD XML file with security measures against XXE attacks."""
        try:
            if LXML_AVAILABLE:
                parser = etree.XMLParser(
                    resolve_entities=False,
                    no_network=True,
                    dtd_validation=False,
                    load_dtd=False
                )
                self.tree = etree.parse(str(self.iodd_path), parser)
            else:
                self.tree = etree.parse(str(self.iodd_path))
            self.root = self.tree.getroot()
        except Exception as e:
            raise ValueError(f"Failed to parse IODD XML: {e}")
    
    def _build_text_catalog(self):
        """Build a catalog of all text elements for name resolution."""
        text_elems = _find_descendants(self.root, 'Text')
        for elem in text_elems:
            text_id = elem.get('id')
            text_value = elem.get('value')
            if text_id and text_value:
                self.text_catalog[text_id] = text_value
        
        redefine_elems = _find_descendants(self.root, 'TextRedefine')
        for elem in redefine_elems:
            text_id = elem.get('id')
            text_value = elem.get('value')
            if text_id and text_value:
                self.text_catalog[text_id] = text_value
    
    def _build_datatype_catalog(self):
        """Build a catalog of all datatypes with IDs for reference resolution."""
        datatype_collections = _find_descendants(self.root, 'DatatypeCollection')
        for dtc in datatype_collections:
            datatypes = _find_all(dtc, 'Datatype')
            for dt in datatypes:
                dt_id = dt.get('id')
                if dt_id:
                    self.datatype_catalog[dt_id] = dt
    
    def _get_text(self, text_id: str) -> Optional[str]:
        """Get text content by text ID from the catalog."""
        return self.text_catalog.get(text_id)
    
    def _decode_unit_code(self, unit_code: str) -> str:
        """Decode SI unit code to human-readable unit."""
        return self.UNIT_MAP.get(unit_code, f'Unit_{unit_code}')
    
    def _get_xsi_type(self, element) -> Optional[str]:
        """Get the xsi:type attribute value, extracting just the type name."""
        xsi_type = element.get('{http://www.w3.org/2001/XMLSchema-instance}type')
        if xsi_type:
            if ':' in xsi_type:
                return xsi_type.split(':', 1)[1]
            return xsi_type
        return None
    
    def _get_standard_bit_length(self, datatype: str) -> int:
        """Get standard bit length for known datatypes."""
        for key, bits in self.DATATYPE_BIT_LENGTHS.items():
            if key in datatype:
                return bits
        return 8
    
    def _resolve_name(self, node: Any, fallback: Optional[str] = None) -> str:
        """Resolve the name from a Name child element or fallback to id/tag."""
        name_elem = _find_one(node, 'Name')
        if name_elem is not None:
            text_id = name_elem.get('textId')
            if text_id:
                resolved = self._get_text(text_id)
                if resolved:
                    return resolved
        
        id_attr = node.get('id')
        if id_attr:
            return id_attr
        
        if fallback:
            return fallback
        
        return _ln(node.tag)
    
    def _get_scaling_info(self, node: Any) -> tuple:
        """Extract gradient and offset from SimpleDatatype or ValuePresentation."""
        gradient = None
        offset = None
        
        gradient_str = node.get('gradient')
        offset_str = node.get('offset')
        
        if gradient_str:
            try:
                gradient = float(gradient_str)
            except ValueError:
                pass
        
        if offset_str:
            try:
                offset = float(offset_str)
            except ValueError:
                pass
        
        value_pres = _find_one(node, 'ValuePresentation')
        if value_pres is not None:
            if gradient is None:
                grad_str = value_pres.get('gradient')
                if grad_str:
                    try:
                        gradient = float(grad_str)
                    except ValueError:
                        pass
            if offset is None:
                off_str = value_pres.get('offset')
                if off_str:
                    try:
                        offset = float(off_str)
                    except ValueError:
                        pass
        
        linear_scaling = _find_one(node, 'LinearScaling')
        if linear_scaling is not None:
            if gradient is None:
                grad_str = linear_scaling.get('gradient')
                if grad_str:
                    try:
                        gradient = float(grad_str)
                    except ValueError:
                        pass
            if offset is None:
                off_str = linear_scaling.get('offset')
                if off_str:
                    try:
                        offset = float(off_str)
                    except ValueError:
                        pass
        
        return gradient, offset
    
    def _parse_simple_datatype(
        self,
        node: Any,
        bit_offset: int,
        parent_path: str,
        name_override: Optional[str] = None
    ) -> List[ProcessDataVariable]:
        """Parse a SimpleDatatype and create a leaf ProcessDataVariable."""
        xsi_type = self._get_xsi_type(node)
        datatype = xsi_type or 'Unknown'
        
        bit_length_attr = node.get('bitLength') or node.get('fixedLength')
        if bit_length_attr:
            bit_length = int(bit_length_attr)
        else:
            bit_length = self._get_standard_bit_length(datatype)
        
        name = name_override or self._resolve_name(node, datatype)
        path = f"{parent_path}/{name}" if parent_path else name
        
        unit = None
        unit_code = node.get('unitCode')
        if unit_code:
            unit = self._decode_unit_code(unit_code)
        
        gradient, offset = self._get_scaling_info(node)
        
        min_val = None
        max_val = None
        try:
            lower = node.get('lowerValue') or node.get('min')
            upper = node.get('upperValue') or node.get('max')
            if lower:
                min_val = float(lower)
            if upper:
                max_val = float(upper)
        except ValueError:
            pass
        
        return [ProcessDataVariable(
            name=name,
            bit_offset=bit_offset,
            bit_length=bit_length,
            datatype=datatype,
            unit=unit,
            min_value=min_val,
            max_value=max_val,
            scale_gradient=gradient,
            scale_offset=offset,
            path=path
        )]
    
    def _parse_type(
        self,
        node: Any,
        base_offset: int,
        parent_path: str,
        name_override: Optional[str] = None
    ) -> List[ProcessDataVariable]:
        """Recursively parse a datatype node and extract all leaf ProcessDataVariables."""
        tag = _ln(node.tag)
        variables = []
        
        datatype_ref = node.get('datatypeRef') or node.get('datatypeId')
        if datatype_ref:
            referenced = self.datatype_catalog.get(datatype_ref)
            if referenced is not None:
                resolved_name = name_override or self._resolve_name(node)
                return self._parse_type(referenced, base_offset, parent_path, resolved_name)
            else:
                return []
        
        if tag == 'DatatypeRef':
            ref_id = node.get('datatypeId')
            if ref_id:
                referenced = self.datatype_catalog.get(ref_id)
                if referenced is not None:
                    return self._parse_type(referenced, base_offset, parent_path, name_override)
            return []
        
        if tag == 'SimpleDatatype':
            return self._parse_simple_datatype(node, base_offset, parent_path, name_override)
        
        xsi_type = self._get_xsi_type(node)
        
        if xsi_type == 'RecordT' or tag == 'RecordT':
            return self._parse_record(node, base_offset, parent_path, name_override)
        
        if xsi_type and xsi_type != 'RecordT':
            bit_length_attr = node.get('bitLength') or node.get('fixedLength')
            if bit_length_attr:
                bit_length = int(bit_length_attr)
            else:
                bit_length = self._get_standard_bit_length(xsi_type)
            
            name = name_override or self._resolve_name(node, xsi_type)
            path = f"{parent_path}/{name}" if parent_path else name
            
            unit = None
            unit_code = node.get('unitCode')
            if unit_code:
                unit = self._decode_unit_code(unit_code)
            
            gradient, offset = self._get_scaling_info(node)
            
            return [ProcessDataVariable(
                name=name,
                bit_offset=base_offset,
                bit_length=bit_length,
                datatype=xsi_type,
                unit=unit,
                scale_gradient=gradient,
                scale_offset=offset,
                path=path
            )]
        
        for child in node:
            child_tag = _ln(child.tag)
            if child_tag in ('Datatype', 'SimpleDatatype', 'DatatypeRef', 'RecordT'):
                child_vars = self._parse_type(child, base_offset, parent_path, name_override)
                variables.extend(child_vars)
                if child_vars:
                    last_var = child_vars[-1]
                    base_offset = last_var.bit_offset + last_var.bit_length
        
        return variables
    
    def _get_field_bit_length(self, item: Any) -> int:
        """Get the bit length of a RecordItem field."""
        simple_dt = _find_one(item, 'SimpleDatatype')
        if simple_dt is not None:
            bit_length_attr = simple_dt.get('bitLength') or simple_dt.get('fixedLength')
            if bit_length_attr:
                return int(bit_length_attr)
            xsi_type = self._get_xsi_type(simple_dt)
            if xsi_type:
                return self._get_standard_bit_length(xsi_type)
        
        datatype_ref = _find_one(item, 'DatatypeRef')
        if datatype_ref is not None:
            ref_id = datatype_ref.get('datatypeId')
            if ref_id:
                referenced = self.datatype_catalog.get(ref_id)
                if referenced is not None:
                    bit_length_attr = referenced.get('bitLength')
                    if bit_length_attr:
                        return int(bit_length_attr)
        
        datatype_elem = _find_one(item, 'Datatype')
        if datatype_elem is not None:
            bit_length_attr = datatype_elem.get('bitLength')
            if bit_length_attr:
                return int(bit_length_attr)
        
        xsi_type = self._get_xsi_type(item)
        if xsi_type:
            bit_length_attr = item.get('bitLength')
            if bit_length_attr:
                return int(bit_length_attr)
            return self._get_standard_bit_length(xsi_type)
        
        return 8
    
    def _detect_lsb_offset_convention(self, record_items: List[Any]) -> bool:
        """Detect if the IODD uses LSB-based bitOffset (IO-Link convention)."""
        if len(record_items) < 2:
            return False
        
        offsets_with_subindex = []
        for item in record_items:
            subindex = item.get('subindex')
            bit_offset = item.get('bitOffset')
            if subindex is not None and bit_offset is not None:
                offsets_with_subindex.append((int(subindex), int(bit_offset)))
        
        if len(offsets_with_subindex) < 2:
            return False
        
        offsets_with_subindex.sort(key=lambda x: x[0])
        
        descending_count = 0
        for i in range(1, len(offsets_with_subindex)):
            if offsets_with_subindex[i][1] < offsets_with_subindex[i-1][1]:
                descending_count += 1
        
        return descending_count > len(offsets_with_subindex) // 2
    
    def _parse_record(
        self,
        record_node: Any,
        base_offset: int,
        parent_path: str,
        name_override: Optional[str] = None,
        total_record_bits: Optional[int] = None
    ) -> List[ProcessDataVariable]:
        """Parse a RecordT structure and its RecordItem children."""
        variables = []
        current_offset = base_offset
        
        if total_record_bits is None:
            bit_length_attr = record_node.get('bitLength')
            if bit_length_attr:
                total_record_bits = int(bit_length_attr)
            else:
                total_record_bits = 0
        
        record_items = _find_all(record_node, 'RecordItem')
        use_lsb_conversion = self._detect_lsb_offset_convention(record_items) and total_record_bits > 0
        
        for item in record_items:
            bit_offset_attr = item.get('bitOffset')
            field_bit_length = self._get_field_bit_length(item)
            
            if bit_offset_attr is not None:
                iodd_bit_offset = int(bit_offset_attr)
                if use_lsb_conversion:
                    actual_bit_offset = total_record_bits - iodd_bit_offset - field_bit_length
                    item_offset = base_offset + actual_bit_offset
                else:
                    item_offset = base_offset + iodd_bit_offset
            else:
                item_offset = current_offset
            
            item_name = self._resolve_name(item)
            item_path = f"{parent_path}/{item_name}" if parent_path else item_name
            
            simple_dt = _find_one(item, 'SimpleDatatype')
            if simple_dt is not None:
                sub_vars = self._parse_simple_datatype(simple_dt, item_offset, parent_path, item_name)
                variables.extend(sub_vars)
                if sub_vars:
                    current_offset = sub_vars[-1].bit_offset + sub_vars[-1].bit_length
                continue
            
            datatype_ref = _find_one(item, 'DatatypeRef')
            if datatype_ref is not None:
                ref_id = datatype_ref.get('datatypeId')
                if ref_id:
                    referenced = self.datatype_catalog.get(ref_id)
                    if referenced is not None:
                        sub_vars = self._parse_type(referenced, item_offset, parent_path)
                        variables.extend(sub_vars)
                        if sub_vars:
                            current_offset = sub_vars[-1].bit_offset + sub_vars[-1].bit_length
                continue
            
            datatype_elem = _find_one(item, 'Datatype')
            if datatype_elem is not None:
                sub_vars = self._parse_type(datatype_elem, item_offset, item_path)
                variables.extend(sub_vars)
                if sub_vars:
                    current_offset = sub_vars[-1].bit_offset + sub_vars[-1].bit_length
                continue
            
            xsi_type = self._get_xsi_type(item)
            if xsi_type:
                bit_length_attr = item.get('bitLength')
                if bit_length_attr:
                    bit_length = int(bit_length_attr)
                else:
                    bit_length = self._get_standard_bit_length(xsi_type)
                
                path = f"{parent_path}/{item_name}" if parent_path else item_name
                
                variables.append(ProcessDataVariable(
                    name=item_name,
                    bit_offset=item_offset,
                    bit_length=bit_length,
                    datatype=xsi_type,
                    path=path
                ))
                current_offset = item_offset + bit_length
        
        variables.sort(key=lambda v: v.bit_offset)
        return variables
    
    def get_device_info(self) -> Dict[str, Any]:
        """Get basic device information."""
        info = {}
        
        try:
            device_id_elems = self.root.xpath("//*[local-name()='DeviceIdentity']")
            if device_id_elems:
                device_id = device_id_elems[0]
                info['vendor_id'] = device_id.get('vendorId')
                info['device_id'] = device_id.get('deviceId')
                info['vendor_name'] = device_id.get('vendorName', 'Unknown')
                
                device_name = _find_one(device_id, 'DeviceName')
                if device_name is not None:
                    text_id = device_name.get('textId')
                    if text_id:
                        info['device_name'] = self._get_text(text_id)
        except Exception:
            pass
            
        return info
    
    def get_process_data_in(self) -> List[ProcessDataVariable]:
        """Extract ProcessDataIn structure (data from device to master)."""
        variables = []
        
        try:
            pdin_elems = self.root.xpath("//*[local-name()='ProcessDataIn']")
            if not pdin_elems:
                return []
            
            pdin = pdin_elems[0]
            
            datatype = _find_one(pdin, 'Datatype')
            if datatype is not None:
                variables = self._parse_type(datatype, 0, "")
            else:
                for child in pdin:
                    child_tag = _ln(child.tag)
                    if child_tag not in ('Name', 'Description'):
                        sub_vars = self._parse_type(child, 0, "")
                        variables.extend(sub_vars)
                        
        except Exception as e:
            print(f"Warning: Could not parse ProcessDataIn: {e}")
            
        return variables
    
    def get_process_data_out(self) -> List[ProcessDataVariable]:
        """Extract ProcessDataOut structure (data from master to device)."""
        variables = []
        
        try:
            pdout_elems = self.root.xpath("//*[local-name()='ProcessDataOut']")
            if not pdout_elems:
                return []
            
            pdout = pdout_elems[0]
            
            datatype = _find_one(pdout, 'Datatype')
            if datatype is not None:
                variables = self._parse_type(datatype, 0, "")
            else:
                for child in pdout:
                    child_tag = _ln(child.tag)
                    if child_tag not in ('Name', 'Description'):
                        sub_vars = self._parse_type(child, 0, "")
                        variables.extend(sub_vars)
                        
        except Exception as e:
            print(f"Warning: Could not parse ProcessDataOut: {e}")
            
        return variables
