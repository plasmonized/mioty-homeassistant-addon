"""
IODD Service Module
Central service for managing IO-Link adapters, IODD files, and process data decoding
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from .iodd_parser import IODDParser, ProcessDataVariable
from .process_data_decoder import ProcessDataDecoder
from .iodd_downloader import IODDDownloader


class IODDService:
    """Central service for IODD management and IO-Link adapter registry"""
    
    def __init__(self, data_dir: Path, iodd_dir: Path):
        """
        Initialize the IODD service
        
        Args:
            data_dir: Directory for storing configuration and registry
            iodd_dir: Directory for storing IODD files
        """
        self.data_dir = Path(data_dir)
        self.iodd_dir = Path(iodd_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.iodd_dir.mkdir(parents=True, exist_ok=True)
        
        self.registry_file = self.data_dir / "iolink_adapter_registry.json"
        self.iodd_cache_dir = self.iodd_dir / "cache"
        self.iodd_cache_dir.mkdir(exist_ok=True)
        
        self.downloader = IODDDownloader(str(self.iodd_cache_dir))
        
        self._adapters: Dict[str, Dict] = {}
        self._iodd_assignments: Dict[str, str] = {}
        self._parser_cache: Dict[str, IODDParser] = {}
        
        self._load_registry()
    
    def _load_registry(self):
        """Load adapter registry from file"""
        if self.registry_file.exists():
            try:
                with open(self.registry_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._adapters = data.get('adapters', {})
                    self._iodd_assignments = data.get('iodd_assignments', {})
                    logging.info(f"📋 Loaded {len(self._adapters)} IO-Link adapters from registry")
            except Exception as e:
                logging.error(f"Failed to load adapter registry: {e}")
                self._adapters = {}
                self._iodd_assignments = {}
    
    def _save_registry(self):
        """Save adapter registry to file"""
        try:
            data = {
                'adapters': self._adapters,
                'iodd_assignments': self._iodd_assignments,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.registry_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logging.info("💾 Adapter registry saved")
        except Exception as e:
            logging.error(f"Failed to save adapter registry: {e}")
    
    def register_adapter(self, sensor_eui: str, name: str = None, 
                        description: str = None) -> Dict[str, Any]:
        """
        Register a mioty-io-link adapter
        
        Args:
            sensor_eui: The EUI of the adapter sensor
            name: Optional friendly name for the adapter
            description: Optional description
            
        Returns:
            The registered adapter info
        """
        adapter = {
            'eui': sensor_eui,
            'name': name or f"IO-Link Adapter {sensor_eui[-4:]}",
            'description': description or "",
            'registered_at': datetime.now().isoformat(),
            'assigned_iodd': self._iodd_assignments.get(sensor_eui),
            'io_link_devices': []
        }
        
        self._adapters[sensor_eui] = adapter
        self._save_registry()
        
        logging.info(f"🔌 Registered IO-Link adapter: {sensor_eui}")
        return adapter
    
    def unregister_adapter(self, sensor_eui: str) -> bool:
        """Unregister an IO-Link adapter"""
        if sensor_eui in self._adapters:
            del self._adapters[sensor_eui]
            if sensor_eui in self._iodd_assignments:
                del self._iodd_assignments[sensor_eui]
            self._save_registry()
            logging.info(f"🗑️ Unregistered IO-Link adapter: {sensor_eui}")
            return True
        return False
    
    def get_adapter(self, sensor_eui: str) -> Optional[Dict[str, Any]]:
        """Get adapter info by EUI"""
        adapter = self._adapters.get(sensor_eui)
        if adapter:
            adapter['assigned_iodd'] = self._iodd_assignments.get(sensor_eui)
        return adapter
    
    def list_adapters(self) -> List[Dict[str, Any]]:
        """List all registered adapters"""
        adapters = []
        for eui, adapter in self._adapters.items():
            adapter_info = adapter.copy()
            adapter_info['assigned_iodd'] = self._iodd_assignments.get(eui)
            adapters.append(adapter_info)
        return adapters
    
    def update_adapter(self, sensor_eui: str, name: str = None, 
                      description: str = None) -> Optional[Dict[str, Any]]:
        """Update adapter information"""
        if sensor_eui not in self._adapters:
            return None
        
        if name:
            self._adapters[sensor_eui]['name'] = name
        if description is not None:
            self._adapters[sensor_eui]['description'] = description
        
        self._adapters[sensor_eui]['updated_at'] = datetime.now().isoformat()
        self._save_registry()
        
        return self.get_adapter(sensor_eui)
    
    def assign_iodd(self, sensor_eui: str, iodd_filename: str) -> bool:
        """
        Assign an IODD file to an adapter
        
        Args:
            sensor_eui: The adapter EUI
            iodd_filename: The IODD filename (in iodd_dir)
            
        Returns:
            True if successful
        """
        iodd_path = self.iodd_dir / iodd_filename
        if not iodd_path.exists():
            iodd_path = self.iodd_cache_dir / iodd_filename
        
        if not iodd_path.exists():
            logging.error(f"IODD file not found: {iodd_filename}")
            return False
        
        try:
            parser = IODDParser(iodd_path)
            self._parser_cache[iodd_filename] = parser
        except Exception as e:
            logging.error(f"Failed to parse IODD {iodd_filename}: {e}")
            return False
        
        self._iodd_assignments[sensor_eui] = iodd_filename
        self._save_registry()
        
        logging.info(f"🔗 Assigned IODD {iodd_filename} to adapter {sensor_eui}")
        return True
    
    def unassign_iodd(self, sensor_eui: str) -> bool:
        """Remove IODD assignment from adapter"""
        if sensor_eui in self._iodd_assignments:
            del self._iodd_assignments[sensor_eui]
            self._save_registry()
            return True
        return False
    
    def get_assigned_iodd(self, sensor_eui: str) -> Optional[str]:
        """Get the assigned IODD filename for an adapter"""
        return self._iodd_assignments.get(sensor_eui)
    
    def list_available_iodds(self) -> List[Dict[str, Any]]:
        """List all available IODD files with their device info"""
        iodds = []
        
        for xml_file in self.iodd_dir.glob("*.xml"):
            try:
                parser = IODDParser(xml_file)
                device_info = parser.get_device_info()
                iodds.append({
                    'filename': xml_file.name,
                    'path': str(xml_file),
                    'vendor_id': device_info.get('vendor_id'),
                    'device_id': device_info.get('device_id'),
                    'vendor_name': device_info.get('vendor_name', 'Unknown'),
                    'device_name': device_info.get('device_name', 'Unknown'),
                    'source': 'uploaded'
                })
            except Exception as e:
                iodds.append({
                    'filename': xml_file.name,
                    'path': str(xml_file),
                    'error': str(e),
                    'source': 'uploaded'
                })
        
        for xml_file in self.iodd_cache_dir.glob("*.xml"):
            try:
                parser = IODDParser(xml_file)
                device_info = parser.get_device_info()
                iodds.append({
                    'filename': xml_file.name,
                    'path': str(xml_file),
                    'vendor_id': device_info.get('vendor_id'),
                    'device_id': device_info.get('device_id'),
                    'vendor_name': device_info.get('vendor_name', 'Unknown'),
                    'device_name': device_info.get('device_name', 'Unknown'),
                    'source': 'cached'
                })
            except Exception as e:
                iodds.append({
                    'filename': xml_file.name,
                    'path': str(xml_file),
                    'error': str(e),
                    'source': 'cached'
                })
        
        return iodds
    
    def upload_iodd(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """
        Upload an IODD file
        
        Args:
            file_content: The file content as bytes
            filename: The filename
            
        Returns:
            Info about the uploaded IODD
        """
        if not filename.lower().endswith('.xml'):
            raise ValueError("Only XML files are supported")
        
        save_path = self.iodd_dir / filename
        save_path.write_bytes(file_content)
        
        try:
            parser = IODDParser(save_path)
            device_info = parser.get_device_info()
            
            return {
                'success': True,
                'filename': filename,
                'vendor_id': device_info.get('vendor_id'),
                'device_id': device_info.get('device_id'),
                'vendor_name': device_info.get('vendor_name'),
                'device_name': device_info.get('device_name')
            }
        except Exception as e:
            return {
                'success': True,
                'filename': filename,
                'warning': f"File saved but parsing failed: {e}"
            }
    
    def delete_iodd(self, filename: str) -> bool:
        """Delete an IODD file"""
        file_path = self.iodd_dir / filename
        if file_path.exists():
            file_path.unlink()
            
            for eui, assigned in list(self._iodd_assignments.items()):
                if assigned == filename:
                    del self._iodd_assignments[eui]
            self._save_registry()
            
            if filename in self._parser_cache:
                del self._parser_cache[filename]
            
            return True
        return False
    
    def get_parser(self, iodd_filename: str) -> Optional[IODDParser]:
        """Get or create an IODD parser for a file"""
        if iodd_filename in self._parser_cache:
            return self._parser_cache[iodd_filename]
        
        iodd_path = self.iodd_dir / iodd_filename
        if not iodd_path.exists():
            iodd_path = self.iodd_cache_dir / iodd_filename
        
        if not iodd_path.exists():
            return None
        
        try:
            parser = IODDParser(iodd_path)
            self._parser_cache[iodd_filename] = parser
            return parser
        except Exception as e:
            logging.error(f"Failed to create parser for {iodd_filename}: {e}")
            return None
    
    def _extract_process_data(self, payload_hex: str) -> Dict[str, Any]:
        """
        Extract process data from mioty-io-link adapter packet.
        
        Packet structure:
        - Control (1 Byte): Bit0=PD-in, Bit1=PD-out, Bit2=Event, Bit3=Adapter Event
        - PD-in length (1 Byte): if Control Bit 0 == 1
        - PD-out length (1 Byte): if Control Bit 1 == 1
        - Vendor ID (2 Bytes): Mandatory
        - Device ID (4 Bytes): Mandatory
        - [PD] (x Bytes): Process Data (PD-in + PD-out)
        - [Event] (3 Bytes): if Control Bit 2 == 1
        - [Adapter Event] (1 Byte): if Control Bit 3 == 1
        
        Args:
            payload_hex: Full adapter payload as hex string
            
        Returns:
            Dict with extracted process_data_hex, header info, or error
        """
        try:
            payload_bytes = bytes.fromhex(payload_hex.replace(' ', '').replace('0x', ''))
            
            if len(payload_bytes) < 8:
                return {'error': 'Payload too short for mioty-io-link header', 'process_data_hex': payload_hex}
            
            offset = 0
            
            # Control byte
            control = payload_bytes[offset]
            offset += 1
            
            has_pd_in = (control & 0x01) != 0
            has_pd_out = (control & 0x02) != 0
            has_event = (control & 0x04) != 0
            has_adapter_event = (control & 0x08) != 0
            
            pd_in_length = 0
            pd_out_length = 0
            
            # PD-in length
            if has_pd_in:
                pd_in_length = payload_bytes[offset]
                offset += 1
            
            # PD-out length
            if has_pd_out:
                pd_out_length = payload_bytes[offset]
                offset += 1
            
            # Vendor ID (2 bytes)
            if offset + 2 > len(payload_bytes):
                return {'error': 'Payload too short for Vendor ID', 'process_data_hex': payload_hex}
            vendor_id = int.from_bytes(payload_bytes[offset:offset+2], 'big')
            offset += 2
            
            # Device ID (4 bytes)
            if offset + 4 > len(payload_bytes):
                return {'error': 'Payload too short for Device ID', 'process_data_hex': payload_hex}
            device_id = int.from_bytes(payload_bytes[offset:offset+4], 'big')
            offset += 4
            
            # Process Data
            pd_total_length = pd_in_length + pd_out_length
            if pd_total_length > 0 and offset + pd_total_length <= len(payload_bytes):
                process_data = payload_bytes[offset:offset + pd_total_length]
                process_data_hex = process_data.hex().upper()
            else:
                process_data_hex = payload_hex
            
            logging.debug(f"mioty-io-link header: control=0x{control:02X}, pd_in={pd_in_length}, "
                         f"pd_out={pd_out_length}, vendor=0x{vendor_id:04X}, device=0x{device_id:08X}")
            logging.debug(f"Extracted process data: {process_data_hex} ({pd_total_length} bytes)")
            
            return {
                'success': True,
                'process_data_hex': process_data_hex,
                'control': control,
                'pd_in_length': pd_in_length,
                'pd_out_length': pd_out_length,
                'vendor_id': vendor_id,
                'device_id': device_id,
                'has_event': has_event,
                'has_adapter_event': has_adapter_event
            }
            
        except Exception as e:
            logging.error(f"Failed to extract process data: {e}")
            return {'error': str(e), 'process_data_hex': payload_hex}
    
    def decode_process_data(self, sensor_eui: str, payload_hex: str) -> Dict[str, Any]:
        """
        Decode IO-Link process data for an adapter
        
        Args:
            sensor_eui: The adapter EUI
            payload_hex: The raw payload as hex string (full mioty-io-link packet)
            
        Returns:
            Decoded data dictionary
        """
        iodd_filename = self._iodd_assignments.get(sensor_eui)
        if not iodd_filename:
            return {
                'success': False,
                'error': 'No IODD assigned to this adapter',
                'raw_payload': payload_hex
            }
        
        parser = self.get_parser(iodd_filename)
        if not parser:
            return {
                'success': False,
                'error': f'Failed to load IODD: {iodd_filename}',
                'raw_payload': payload_hex
            }
        
        try:
            # Extract process data from mioty-io-link packet header
            extraction = self._extract_process_data(payload_hex)
            process_data_hex = extraction.get('process_data_hex', payload_hex)
            
            logging.info(f"🔧 IODD decode: raw={payload_hex} → process_data={process_data_hex}")
            
            process_data_vars = parser.get_process_data_in()
            
            if not process_data_vars:
                return {
                    'success': False,
                    'error': 'No ProcessDataIn structure found in IODD',
                    'raw_payload': payload_hex
                }
            
            decoder = ProcessDataDecoder(process_data_vars)
            decoded = decoder.decode(process_data_hex)
            
            device_info = parser.get_device_info()
            
            return {
                'success': True,
                'decoder_type': 'iodd',
                'iodd_file': iodd_filename,
                'device_info': device_info,
                'data': decoded,
                'raw_payload': payload_hex,
                'process_data': process_data_hex,
                'header_info': {
                    'vendor_id': extraction.get('vendor_id'),
                    'device_id': extraction.get('device_id'),
                    'pd_in_length': extraction.get('pd_in_length'),
                    'pd_out_length': extraction.get('pd_out_length')
                }
            }
            
        except Exception as e:
            logging.error(f"Failed to decode process data: {e}")
            return {
                'success': False,
                'error': str(e),
                'raw_payload': payload_hex
            }
    
    def test_decode(self, iodd_filename: str, payload_hex: str) -> Dict[str, Any]:
        """
        Test decoding with an IODD file (without requiring adapter assignment)
        
        Args:
            iodd_filename: The IODD filename
            payload_hex: Test payload as hex string
            
        Returns:
            Decoded result
        """
        parser = self.get_parser(iodd_filename)
        if not parser:
            return {
                'success': False,
                'error': f'Failed to load IODD: {iodd_filename}'
            }
        
        try:
            process_data_vars = parser.get_process_data_in()
            device_info = parser.get_device_info()
            
            if not process_data_vars:
                return {
                    'success': False,
                    'error': 'No ProcessDataIn structure found in IODD',
                    'device_info': device_info
                }
            
            decoder = ProcessDataDecoder(process_data_vars)
            decoded = decoder.decode(payload_hex)
            
            return {
                'success': True,
                'device_info': device_info,
                'variables_count': len(process_data_vars),
                'data': decoded,
                'raw_payload': payload_hex
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_iodd_info(self, iodd_filename: str) -> Dict[str, Any]:
        """Get detailed information about an IODD file"""
        parser = self.get_parser(iodd_filename)
        if not parser:
            return {'error': f'Failed to load IODD: {iodd_filename}'}
        
        try:
            device_info = parser.get_device_info()
            process_data_in = parser.get_process_data_in()
            process_data_out = parser.get_process_data_out()
            
            return {
                'filename': iodd_filename,
                'device_info': device_info,
                'process_data_in': [
                    {
                        'name': v.name,
                        'datatype': v.datatype,
                        'bit_offset': v.bit_offset,
                        'bit_length': v.bit_length,
                        'unit': v.unit,
                        'scale_gradient': v.scale_gradient,
                        'scale_offset': v.scale_offset
                    }
                    for v in process_data_in
                ],
                'process_data_out': [
                    {
                        'name': v.name,
                        'datatype': v.datatype,
                        'bit_offset': v.bit_offset,
                        'bit_length': v.bit_length,
                        'unit': v.unit
                    }
                    for v in process_data_out
                ],
                'total_pdin_bits': sum(v.bit_length for v in process_data_in) if process_data_in else 0,
                'total_pdout_bits': sum(v.bit_length for v in process_data_out) if process_data_out else 0
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def is_adapter(self, sensor_eui: str) -> bool:
        """Check if a sensor EUI is a registered IO-Link adapter"""
        return sensor_eui in self._adapters
    
    def download_iodd(self, vendor_id: int, device_id: int) -> Dict[str, Any]:
        """
        Try to download an IODD from ioddfinder.com
        
        Args:
            vendor_id: IO-Link Vendor ID
            device_id: IO-Link Device ID
            
        Returns:
            Result dictionary
        """
        try:
            iodd_path = self.downloader.get_iodd_path(vendor_id, device_id)
            
            if iodd_path:
                parser = IODDParser(iodd_path)
                device_info = parser.get_device_info()
                
                return {
                    'success': True,
                    'filename': iodd_path.name,
                    'path': str(iodd_path),
                    'device_info': device_info
                }
            else:
                return {
                    'success': False,
                    'error': 'IODD not found. Please download manually from ioddfinder.io-link.com',
                    'manual_url': self.downloader.get_iodd_finder_url(vendor_id, device_id)
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
