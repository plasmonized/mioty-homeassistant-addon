"""
Service Center API Client für BSSCI Service Center Integration
Ermöglicht die Anmeldung und Verwaltung von Sensoren am Service Center
"""
import requests
import json
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class ServiceCenterClient:
    """Client für die Kommunikation mit dem BSSCI Service Center"""
    
    def __init__(self, base_url: str, timeout: int = 10):
        """
        Initialisiert den Service Center Client
        
        Args:
            base_url: Basis-URL des Service Centers (z.B. http://service-center:5000)
            timeout: Request-Timeout in Sekunden
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'mioty-application-center/1.0'
        })
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Testet die Verbindung zum Service Center
        
        Returns:
            Dict mit Connection-Status und Informationen
        """
        try:
            response = self.session.get(
                f"{self.base_url}/api/bssci/status",
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Service Center verbunden: {self.base_url}")
            return {
                'connected': True,
                'status': data,
                'message': 'Verbindung erfolgreich'
            }
        except requests.exceptions.ConnectionError:
            error_msg = f"Service Center nicht erreichbar: {self.base_url}"
            logger.warning(error_msg)
            return {
                'connected': False,
                'error': 'Connection Error',
                'message': error_msg
            }
        except requests.exceptions.Timeout:
            error_msg = f"Service Center Timeout: {self.base_url}"
            logger.warning(error_msg)
            return {
                'connected': False,
                'error': 'Timeout',
                'message': error_msg
            }
        except Exception as e:
            error_msg = f"Service Center Fehler: {str(e)}"
            logger.error(error_msg)
            return {
                'connected': False,
                'error': str(e),
                'message': error_msg
            }
    
    def get_sensors(self) -> List[Dict[str, Any]]:
        """
        Holt alle Sensoren vom Service Center
        
        Returns:
            Liste aller Sensoren mit Status-Informationen
        """
        try:
            response = self.session.get(
                f"{self.base_url}/api/sensors",
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            # Konvertiere das Dictionary zu einer Liste
            sensors = []
            for eui, sensor_data in data.items():
                sensor_info = {
                    'eui': eui,
                    'registered': sensor_data.get('registered', False),
                    'base_stations': sensor_data.get('base_stations', []),
                    'total_registrations': sensor_data.get('total_registrations', 0),
                    **sensor_data
                }
                sensors.append(sensor_info)
            
            logger.info(f"Service Center: {len(sensors)} Sensoren geladen")
            return sensors
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Service Center Sensoren: {e}")
            return []
    
    def add_sensor(self, eui: str, nw_key: str, short_addr: str = "0000", bidi: bool = False) -> Dict[str, Any]:
        """
        Fügt einen neuen Sensor am Service Center hinzu
        
        Args:
            eui: Sensor EUI (16 Hex-Zeichen)
            nw_key: Network Key (32 Hex-Zeichen)
            short_addr: Short Address (4 Hex-Zeichen)
            bidi: Bidirektionale Kommunikation
            
        Returns:
            Dict mit Ergebnis der Operation
        """
        try:
            # Validiere Input
            if len(eui) != 16:
                return {'success': False, 'message': 'EUI muss 16 Hex-Zeichen haben'}
            if len(nw_key) != 32:
                return {'success': False, 'message': 'Network Key muss 32 Hex-Zeichen haben'}
            if len(short_addr) != 4:
                return {'success': False, 'message': 'Short Address muss 4 Hex-Zeichen haben'}
            
            sensor_data = {
                'eui': eui.upper(),
                'nwKey': nw_key.upper(),
                'shortAddr': short_addr.upper(),
                'bidi': bidi
            }
            
            response = self.session.post(
                f"{self.base_url}/api/sensors",
                json=sensor_data,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get('success'):
                logger.info(f"Sensor {eui} erfolgreich am Service Center angemeldet")
                return {
                    'success': True,
                    'message': f'Sensor {eui} erfolgreich am Service Center angemeldet',
                    'sensor': sensor_data
                }
            else:
                error_msg = result.get('message', 'Unbekannter Fehler')
                logger.error(f"Service Center Anmeldung fehlgeschlagen für {eui}: {error_msg}")
                return {
                    'success': False,
                    'message': f'Service Center Anmeldung fehlgeschlagen: {error_msg}'
                }
                
        except Exception as e:
            error_msg = f"Fehler bei Service Center Anmeldung für {eui}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'message': error_msg
            }
    
    def delete_sensor(self, eui: str) -> Dict[str, Any]:
        """
        Löscht einen Sensor vom Service Center
        
        Args:
            eui: Sensor EUI
            
        Returns:
            Dict mit Ergebnis der Operation
        """
        try:
            response = self.session.delete(
                f"{self.base_url}/api/sensors/{eui}",
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get('success'):
                logger.info(f"Sensor {eui} vom Service Center gelöscht")
                return {
                    'success': True,
                    'message': f'Sensor {eui} erfolgreich vom Service Center gelöscht'
                }
            else:
                error_msg = result.get('message', 'Unbekannter Fehler')
                logger.error(f"Service Center Löschung fehlgeschlagen für {eui}: {error_msg}")
                return {
                    'success': False,
                    'message': f'Service Center Löschung fehlgeschlagen: {error_msg}'
                }
                
        except Exception as e:
            error_msg = f"Fehler bei Service Center Löschung für {eui}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'message': error_msg
            }
    
    def detach_sensor(self, eui: str) -> Dict[str, Any]:
        """
        Trennt einen Sensor von allen Base Stations
        
        Args:
            eui: Sensor EUI
            
        Returns:
            Dict mit Ergebnis der Operation
        """
        try:
            response = self.session.post(
                f"{self.base_url}/api/sensors/{eui}/detach",
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get('success'):
                logger.info(f"Sensor {eui} vom Service Center getrennt")
                return {
                    'success': True,
                    'message': f'Sensor {eui} erfolgreich getrennt'
                }
            else:
                error_msg = result.get('message', 'Unbekannter Fehler')
                logger.error(f"Service Center Trennung fehlgeschlagen für {eui}: {error_msg}")
                return {
                    'success': False,
                    'message': f'Service Center Trennung fehlgeschlagen: {error_msg}'
                }
                
        except Exception as e:
            error_msg = f"Fehler bei Service Center Trennung für {eui}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'message': error_msg
            }
    
    def attach_all_sensors(self) -> Dict[str, Any]:
        """
        Verbindet alle konfigurierten Sensoren
        
        Returns:
            Dict mit Ergebnis der Operation
        """
        try:
            response = self.session.post(
                f"{self.base_url}/api/sensors/attach-all",
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get('success'):
                message = result.get('message', 'Alle Sensoren verbunden')
                logger.info(f"Service Center: {message}")
                return {
                    'success': True,
                    'message': message
                }
            else:
                error_msg = result.get('message', 'Unbekannter Fehler')
                logger.error(f"Service Center Attach-All fehlgeschlagen: {error_msg}")
                return {
                    'success': False,
                    'message': f'Attach-All fehlgeschlagen: {error_msg}'
                }
                
        except Exception as e:
            error_msg = f"Fehler bei Service Center Attach-All: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'message': error_msg
            }
    
    def detach_all_sensors(self) -> Dict[str, Any]:
        """
        Trennt alle Sensoren von Base Stations
        
        Returns:
            Dict mit Ergebnis der Operation
        """
        try:
            response = self.session.post(
                f"{self.base_url}/api/sensors/detach-all",
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get('success'):
                message = result.get('message', 'Alle Sensoren getrennt')
                logger.info(f"Service Center: {message}")
                return {
                    'success': True,
                    'message': message
                }
            else:
                error_msg = result.get('message', 'Unbekannter Fehler')
                logger.error(f"Service Center Detach-All fehlgeschlagen: {error_msg}")
                return {
                    'success': False,
                    'message': f'Detach-All fehlgeschlagen: {error_msg}'
                }
                
        except Exception as e:
            error_msg = f"Fehler bei Service Center Detach-All: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'message': error_msg
            }
    
    def clear_all_sensors(self) -> Dict[str, Any]:
        """
        Löscht alle Sensoren vom Service Center
        
        Returns:
            Dict mit Ergebnis der Operation
        """
        try:
            response = self.session.post(
                f"{self.base_url}/api/sensors/clear",
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get('success'):
                message = result.get('message', 'Alle Sensoren gelöscht')
                logger.info(f"Service Center: {message}")
                return {
                    'success': True,
                    'message': message
                }
            else:
                error_msg = result.get('message', 'Unbekannter Fehler')
                logger.error(f"Service Center Clear-All fehlgeschlagen: {error_msg}")
                return {
                    'success': False,
                    'message': f'Clear-All fehlgeschlagen: {error_msg}'
                }
                
        except Exception as e:
            error_msg = f"Fehler bei Service Center Clear-All: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'message': error_msg
            }

def create_service_center_client(base_url: str) -> Optional[ServiceCenterClient]:
    """
    Factory-Funktion zur Erstellung eines Service Center Clients
    
    Args:
        base_url: Service Center URL
        
    Returns:
        ServiceCenterClient Instance oder None bei fehlerhafte URL
    """
    if not base_url or not base_url.strip():
        return None
    
    try:
        client = ServiceCenterClient(base_url.strip())
        return client
    except Exception as e:
        logger.error(f"Fehler beim Erstellen des Service Center Clients: {e}")
        return None