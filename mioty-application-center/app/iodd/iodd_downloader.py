"""
IODD Downloader Module
Downloads IODD files from iodd-finder.com based on Vendor ID and Device ID
"""

import os
import requests
from pathlib import Path
from typing import Optional
import zipfile
import io
import logging


class IODDDownloader:
    """Downloads and caches IODD files from iodd-finder.com"""
    
    def __init__(self, cache_dir: str = "iodd_cache"):
        """
        Initialize the IODD downloader
        
        Args:
            cache_dir: Directory to cache downloaded IODD files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.base_url = "https://ioddfinder.io-link.com"
        
    def get_iodd_path(self, vendor_id: int, device_id: int) -> Optional[Path]:
        """
        Get the path to an IODD file, downloading if necessary
        
        Args:
            vendor_id: IO-Link Vendor ID
            device_id: IO-Link Device ID
            
        Returns:
            Path to the IODD XML file, or None if not found
        """
        iodd_filename = f"iodd_{vendor_id}_{device_id}.xml"
        iodd_path = self.cache_dir / iodd_filename
        
        if iodd_path.exists():
            logging.info(f"✓ IODD file found in cache: {iodd_path}")
            return iodd_path
            
        logging.info(f"Downloading IODD for Vendor ID: {vendor_id}, Device ID: {device_id}...")
        
        downloaded_path = self._download_iodd(vendor_id, device_id, iodd_path)
        
        if downloaded_path:
            logging.info(f"✓ IODD file downloaded: {downloaded_path}")
            return downloaded_path
        else:
            logging.warning(f"✗ IODD file not found for Vendor ID: {vendor_id}, Device ID: {device_id}")
            return None
    
    def _download_iodd(self, vendor_id: int, device_id: int, save_path: Path) -> Optional[Path]:
        """
        Download IODD file from iodd-finder.com
        
        Note: IODDfinder.io-link.com does not currently provide a public API for
        automated downloads. This method attempts common URL patterns but will
        likely fail. For production use, manually download IODD files.
        """
        logging.info("Note: Automatic download is not fully supported. Trying common URLs...")
        
        possible_urls = [
            f"{self.base_url}/api/vendors/{vendor_id}/devices/{device_id}/iodd",
            f"{self.base_url}/download/{vendor_id}/{device_id}",
            f"{self.base_url}/api/download?vendorId={vendor_id}&deviceId={device_id}",
        ]
        
        for url in possible_urls:
            try:
                response = requests.get(url, timeout=30, allow_redirects=True)
                
                if response.status_code == 200:
                    if 'application/zip' in response.headers.get('Content-Type', ''):
                        return self._extract_iodd_from_zip(response.content, save_path)
                    elif 'xml' in response.headers.get('Content-Type', ''):
                        save_path.write_bytes(response.content)
                        return save_path
                    
            except requests.exceptions.RequestException:
                continue
                
        return None
    
    def _extract_iodd_from_zip(self, zip_content: bytes, save_path: Path) -> Optional[Path]:
        """Extract IODD XML file from a ZIP archive"""
        try:
            with zipfile.ZipFile(io.BytesIO(zip_content)) as zf:
                for filename in zf.namelist():
                    if filename.endswith('.xml') and not filename.startswith('__'):
                        xml_content = zf.read(filename)
                        save_path.write_bytes(xml_content)
                        return save_path
        except zipfile.BadZipFile:
            pass
            
        return None
    
    def load_iodd_from_file(self, filepath: str) -> Path:
        """
        Load an IODD file that was manually downloaded
        
        Args:
            filepath: Path to the IODD XML or ZIP file
            
        Returns:
            Path to the cached IODD XML file
        """
        source_path = Path(filepath)
        
        if not source_path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
            
        if source_path.suffix.lower() == '.zip':
            with zipfile.ZipFile(source_path) as zf:
                for filename in zf.namelist():
                    if filename.endswith('.xml'):
                        xml_content = zf.read(filename)
                        cached_path = self.cache_dir / Path(filename).name
                        cached_path.write_bytes(xml_content)
                        return cached_path
        elif source_path.suffix.lower() == '.xml':
            cached_path = self.cache_dir / source_path.name
            cached_path.write_bytes(source_path.read_bytes())
            return cached_path
            
        raise ValueError(f"Unsupported file type: {source_path.suffix}")
    
    def list_cached_iodds(self) -> list:
        """List all cached IODD files"""
        return list(self.cache_dir.glob("*.xml"))
    
    def get_iodd_finder_url(self, vendor_id: int, device_id: int) -> str:
        """Get the URL to search for an IODD on ioddfinder.com"""
        return f"https://ioddfinder.io-link.com/productvariants/search?VendorId={vendor_id}&DeviceId={device_id}"
