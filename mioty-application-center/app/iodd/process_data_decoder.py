"""
Process Data Decoder Module
Decodes raw process data bytes according to IODD specification
Uses pure Python implementation without external bitstring dependency
"""

from typing import List, Dict, Any, Union
import struct
from .iodd_parser import ProcessDataVariable


class BitBuffer:
    """Pure Python bit manipulation class for process data decoding."""
    
    def __init__(self, data: bytes):
        self.data = data
        self.length = len(data) * 8
    
    def __len__(self):
        return self.length
    
    def get_bits(self, offset: int, length: int) -> int:
        """Extract bits from the buffer at given offset and length."""
        if offset + length > self.length:
            raise ValueError(f"Not enough bits: need {offset + length}, have {self.length}")
        
        result = 0
        for i in range(length):
            byte_idx = (offset + i) // 8
            bit_idx = 7 - ((offset + i) % 8)
            if byte_idx < len(self.data):
                if self.data[byte_idx] & (1 << bit_idx):
                    result |= (1 << (length - 1 - i))
        return result
    
    def get_uint(self, offset: int, length: int) -> int:
        """Get unsigned integer value."""
        return self.get_bits(offset, length)
    
    def get_int(self, offset: int, length: int) -> int:
        """Get signed integer value (two's complement)."""
        value = self.get_bits(offset, length)
        if value >= (1 << (length - 1)):
            value -= (1 << length)
        return value
    
    def get_float32(self, offset: int) -> float:
        """Get 32-bit float value (big-endian)."""
        uint_val = self.get_bits(offset, 32)
        bytes_val = uint_val.to_bytes(4, 'big')
        return struct.unpack('>f', bytes_val)[0]
    
    def get_float64(self, offset: int) -> float:
        """Get 64-bit float value (big-endian)."""
        uint_val = self.get_bits(offset, 64)
        bytes_val = uint_val.to_bytes(8, 'big')
        return struct.unpack('>d', bytes_val)[0]


class ProcessDataDecoder:
    """Decodes raw IO-Link process data based on IODD structure"""
    
    def __init__(self, variables: List[ProcessDataVariable]):
        """
        Initialize the decoder with IODD variable definitions
        
        Args:
            variables: List of ProcessDataVariable from IODD parser
        """
        self.variables = variables
        
    def decode(self, payload: Union[str, bytes], port: int = 1) -> Dict[str, Any]:
        """
        Decode process data payload
        
        Args:
            payload: Raw payload as hex string (e.g., "A1B2C3") or bytes
            port: Port number for multi-port adapters (1 or 2, default 1)
            
        Returns:
            Dictionary with variable names as keys and decoded values
        """
        if isinstance(payload, str):
            payload = bytes.fromhex(payload.replace(' ', '').replace('0x', ''))
        
        # Calculate expected length from variables
        if self.variables:
            max_bit = max((v.bit_offset + v.bit_length) for v in self.variables)
            expected_bytes = (max_bit + 7) // 8
            
            # Handle multi-port IO-Link adapter payloads
            # 2-Port adapter: 9 bytes per port (8 data + 1 qualifier) = 17-18 bytes total
            # 1-Port adapter: 9 bytes (8 data + 1 qualifier)
            port_size = expected_bytes + 1  # Process data + Port Qualifier
            
            if len(payload) >= 2 * port_size - 1:
                # This is a 2-port adapter payload
                if port == 1:
                    # Extract Port 1: first 'expected_bytes' bytes (before qualifier)
                    payload = payload[:expected_bytes]
                elif port == 2:
                    # Extract Port 2: bytes starting after Port 1 + qualifier
                    port2_start = port_size
                    payload = payload[port2_start:port2_start + expected_bytes]
            elif len(payload) == expected_bytes + 1:
                # Single port adapter: remove Port Qualifier (last byte)
                payload = payload[:-1]
            
        bits = BitBuffer(payload)
        
        result = {}
        
        for var in self.variables:
            try:
                value = self._extract_value(bits, var)
                
                display_name = var.name
                if var.unit:
                    display_name = f"{var.name} ({var.unit})"
                    
                result[display_name] = {
                    'value': value,
                    'raw_name': var.name,
                    'unit': var.unit,
                    'datatype': var.datatype,
                    'bit_offset': var.bit_offset,
                    'bit_length': var.bit_length
                }
                
            except Exception as e:
                result[var.name] = {
                    'value': f'Error: {e}',
                    'error': str(e)
                }
                
        return result
    
    def _extract_value(self, bits: BitBuffer, var: ProcessDataVariable) -> Union[int, float, bool]:
        """Extract and convert a value from the bit buffer"""
        if var.bit_offset + var.bit_length > len(bits):
            raise ValueError(f"Not enough bits: need {var.bit_offset + var.bit_length}, have {len(bits)}")
        
        datatype_lower = var.datatype.lower()
        
        if 'boolean' in datatype_lower or 'bool' in datatype_lower:
            return bits.get_uint(var.bit_offset, var.bit_length) == 1
            
        elif 'float32' in datatype_lower:
            if var.bit_length == 32:
                return bits.get_float32(var.bit_offset)
            else:
                return 0.0
        
        elif 'float64' in datatype_lower:
            if var.bit_length == 64:
                return bits.get_float64(var.bit_offset)
            else:
                return 0.0
        
        is_signed = 'integer' in datatype_lower and 'uint' not in datatype_lower
        
        if is_signed:
            raw_value = bits.get_int(var.bit_offset, var.bit_length)
        else:
            raw_value = bits.get_uint(var.bit_offset, var.bit_length)
        
        if var.scale_gradient is not None or var.scale_offset is not None:
            gradient = var.scale_gradient if var.scale_gradient is not None else 1.0
            offset = var.scale_offset if var.scale_offset is not None else 0.0
            return float(raw_value) * gradient + offset
            
        return raw_value
    
    def decode_with_metadata(self, payload: Union[str, bytes]) -> Dict[str, Any]:
        """
        Decode with additional metadata about the decoding process
        
        Returns:
            Dictionary with decoded data and metadata
        """
        if isinstance(payload, str):
            payload_bytes = bytes.fromhex(payload.replace(' ', '').replace('0x', ''))
        else:
            payload_bytes = payload
            
        decoded = self.decode(payload_bytes)
        
        return {
            'payload_length_bytes': len(payload),
            'payload_length_bits': len(payload) * 8,
            'variables_count': len(self.variables),
            'decoded': decoded
        }
