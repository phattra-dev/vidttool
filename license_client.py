"""
License Client Module - Real-Time License Validation
Enterprise-grade licensing with instant revocation detection via Supabase Realtime
"""

import hashlib
import platform
import uuid
import json
import os
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable
import threading
import logging

# Configuration
SUPABASE_URL = "https://gnmhaxqrtmzcitqwabeg.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdubWhheHFydG16Y2l0cXdhYmVnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjgzMjcyNzgsImV4cCI6MjA4MzkwMzI3OH0.chs9SkmwdFBUmboEUAC57gY7gleDw8UURW9IdffzDtI"
APP_VERSION = "1.2.0"
CACHE_DIR = Path.home() / ".tiktools"
CACHE_FILE = CACHE_DIR / "license_cache.enc"

# Real-time check interval (fallback if websocket fails)
REALTIME_FALLBACK_INTERVAL = 10  # 10 seconds fallback polling - fast detection!
MAX_OFFLINE_HOURS = 24

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LicenseClient")

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    import websocket
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    logger.warning("websocket-client not installed. Install with: pip install websocket-client")


class LicenseStatus:
    VALID = "valid"
    INVALID = "invalid"
    EXPIRED = "expired"
    DISABLED = "disabled"
    REVOKED = "revoked"
    MAX_DEVICES = "max_devices"
    OFFLINE = "offline"
    ERROR = "error"


class RealtimeLicenseClient:
    """
    Real-Time License Validation Client
    
    Uses Supabase Realtime for INSTANT license status updates.
    When admin disables a license, the app knows within milliseconds.
    """
    
    def __init__(self, supabase_url: str = None, supabase_key: str = None):
        self.supabase_url = supabase_url or SUPABASE_URL
        self.supabase_key = supabase_key or SUPABASE_ANON_KEY
        self.machine_id = self._generate_machine_id()
        self.machine_hash = self._generate_machine_hash()
        
        # License state
        self.license_key: Optional[str] = None
        self.license_data: Optional[Dict] = None
        self.license_status: str = LicenseStatus.INVALID
        self.last_online_validation: Optional[datetime] = None
        
        # Callbacks
        self._on_status_change: Optional[Callable] = None
        self._on_license_disabled: Optional[Callable] = None
        self._on_realtime_update: Optional[Callable] = None
        
        # Real-time connection
        self._ws: Optional[Any] = None
        self._ws_thread: Optional[threading.Thread] = None
        self._ws_connected = False
        self._stop_realtime = threading.Event()
        self._realtime_ref = 0
        
        # Fallback polling
        self._polling_thread: Optional[threading.Thread] = None
        self._stop_polling = threading.Event()
        
        # Thread safety
        self._lock = threading.Lock()
        
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self._load_cache()
    
    def _generate_machine_id(self) -> str:
        components = [platform.node(), platform.machine(), platform.processor(), platform.system()]
        try:
            mac = ':'.join(['{:02x}'.format((uuid.getnode() >> i) & 0xff) for i in range(0, 48, 8)][::-1])
            components.append(mac)
        except: pass
        
        if platform.system() == "Windows":
            try:
                import subprocess
                result = subprocess.run(['wmic', 'diskdrive', 'get', 'serialnumber'],
                    capture_output=True, text=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
                serial = result.stdout.strip().split('\n')[-1].strip()
                if serial and serial != "SerialNumber": components.append(serial)
            except: pass
        
        return hashlib.sha256("|".join(filter(None, components)).encode()).hexdigest()
    
    def _generate_machine_hash(self) -> str:
        return hashlib.sha256(f"{self.machine_id}:salt:v1".encode()).hexdigest()[:32]
    
    def _encrypt_data(self, data: dict) -> bytes:
        import base64
        json_str = json.dumps(data, default=str)
        key = (self.machine_id * 2)[:64].encode()
        encrypted = bytes([b ^ key[i % len(key)] for i, b in enumerate(json_str.encode())])
        return base64.b64encode(encrypted)
    
    def _decrypt_data(self, data: bytes) -> Optional[dict]:
        import base64
        try:
            encrypted = base64.b64decode(data)
            key = (self.machine_id * 2)[:64].encode()
            decrypted = bytes([b ^ key[i % len(key)] for i, b in enumerate(encrypted)])
            return json.loads(decrypted.decode())
        except: return None
    
    def _save_cache(self):
        if not self.license_data or not self.license_key: return
        cache_data = {
            "license_key": self.license_key,
            "license_data": self.license_data,
            "license_status": self.license_status,
            "cached_at": datetime.utcnow().isoformat(),
            "last_online_validation": self.last_online_validation.isoformat() if self.last_online_validation else None,
            "machine_id": self.machine_id
        }
        try:
            CACHE_FILE.write_bytes(self._encrypt_data(cache_data))
        except Exception as e:
            logger.error(f"Cache save failed: {e}")
    
    def _load_cache(self):
        if not CACHE_FILE.exists(): return
        try:
            cache_data = self._decrypt_data(CACHE_FILE.read_bytes())
            if not cache_data or cache_data.get("machine_id") != self.machine_id:
                self._clear_cache()
                return
            
            cached_at = datetime.fromisoformat(cache_data["cached_at"])
            if (datetime.utcnow() - cached_at).total_seconds() / 3600 > MAX_OFFLINE_HOURS:
                self.license_key = cache_data.get("license_key")
                return
            
            self.license_key = cache_data.get("license_key")
            self.license_data = cache_data.get("license_data")
            self.license_status = cache_data.get("license_status", LicenseStatus.INVALID)
            if cache_data.get("last_online_validation"):
                self.last_online_validation = datetime.fromisoformat(cache_data["last_online_validation"])
        except Exception as e:
            logger.error(f"Cache load failed: {e}")
            self._clear_cache()
    
    def _clear_cache(self):
        try:
            if CACHE_FILE.exists(): CACHE_FILE.unlink()
        except: pass
    
    def _api_request(self, method: str, table: str, data: dict = None, filters: dict = None) -> Dict:
        if not REQUESTS_AVAILABLE:
            return {"error": "requests_unavailable"}
        
        url = f"{self.supabase_url}/rest/v1/{table}"
        headers = {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        params = {}
        if filters:
            for k, v in filters.items(): params[k] = f"eq.{v}"
        
        try:
            if method == "GET":
                resp = requests.get(url, headers=headers, params=params, timeout=10)
            elif method == "POST":
                resp = requests.post(url, headers=headers, json=data, timeout=10)
            elif method == "PATCH":
                resp = requests.patch(url, headers=headers, params=params, json=data, timeout=10)
            else:
                return {"error": "invalid_method"}
            
            if resp.status_code >= 400:
                return {"error": resp.text}
            return {"data": resp.json() if resp.text else []}
        except requests.exceptions.ConnectionError:
            return {"error": "connection_error"}
        except Exception as e:
            return {"error": str(e)}
    
    def _track_user(self, license_key: str = None):
        """Track user in users table for admin dashboard visibility"""
        try:
            now = datetime.utcnow().isoformat()
            app_id = self.machine_id
            
            # Check if user exists
            result = self._api_request("GET", "users", filters={"app_id": app_id})
            
            if result.get("data"):
                # Update existing user
                user = result["data"][0]
                # Don't update if user is banned, suspicious, or hacking
                if user.get("status") in ["banned", "suspicious", "hacking"]:
                    return  # Don't modify banned/flagged users
                
                updates = {
                    "last_seen": now,
                    "total_visits": (user.get("total_visits") or 0) + 1
                }
                if license_key:
                    updates["license_key"] = license_key
                    # Only set to active if not already in a special status
                    if user.get("status") not in ["banned", "suspicious", "hacking"]:
                        updates["status"] = "active"
                
                self._api_request("PATCH", "users", data=updates, filters={"app_id": app_id})
            else:
                # Create new user
                user_data = {
                    "app_id": app_id,
                    "license_key": license_key,
                    "status": "active" if license_key else "visitor",
                    "first_seen": now,
                    "last_seen": now,
                    "total_visits": 1,
                    "failed_attempts": 0
                }
                self._api_request("POST", "users", data=user_data)
        except Exception as e:
            logger.debug(f"User tracking failed: {e}")
            pass  # Don't fail validation on tracking errors

    # ==================== REAL-TIME WEBSOCKET ====================
    
    def _get_realtime_url(self) -> str:
        """Get Supabase Realtime WebSocket URL"""
        ws_url = self.supabase_url.replace("https://", "wss://").replace("http://", "ws://")
        return f"{ws_url}/realtime/v1/websocket?apikey={self.supabase_key}&vsn=1.0.0"
    
    def _start_realtime(self):
        """Start real-time WebSocket connection for instant updates"""
        if not WEBSOCKET_AVAILABLE:
            logger.warning("WebSocket not available, using polling fallback")
            self._start_polling()
            return
        
        if self._ws_thread and self._ws_thread.is_alive():
            return
        
        self._stop_realtime.clear()
        self._ws_thread = threading.Thread(target=self._realtime_loop, daemon=True, name="RealtimeLicense")
        self._ws_thread.start()
        logger.info("Real-time license monitoring started")
    
    def _stop_realtime_connection(self):
        """Stop real-time connection"""
        self._stop_realtime.set()
        if self._ws:
            try: self._ws.close()
            except: pass
        self._ws_connected = False
    
    def _realtime_loop(self):
        """WebSocket connection loop with auto-reconnect"""
        while not self._stop_realtime.is_set():
            try:
                self._connect_websocket()
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
            
            if not self._stop_realtime.is_set():
                logger.info("Reconnecting in 5 seconds...")
                time.sleep(5)
    
    def _connect_websocket(self):
        """Establish WebSocket connection"""
        import websocket
        
        def on_open(ws):
            self._ws_connected = True
            logger.info("Real-time connected")
            
            # Subscribe to license changes
            if self.license_key:
                self._subscribe_to_license(ws)
        
        def on_message(ws, message):
            self._handle_realtime_message(message)
        
        def on_error(ws, error):
            logger.error(f"WebSocket error: {error}")
            self._ws_connected = False
        
        def on_close(ws, close_status_code, close_msg):
            logger.info("WebSocket closed")
            self._ws_connected = False
        
        self._ws = websocket.WebSocketApp(
            self._get_realtime_url(),
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        
        # Send heartbeat every 30 seconds
        def heartbeat():
            while self._ws_connected and not self._stop_realtime.is_set():
                try:
                    self._ws.send(json.dumps({"topic": "phoenix", "event": "heartbeat", "payload": {}, "ref": str(self._realtime_ref)}))
                    self._realtime_ref += 1
                except: break
                time.sleep(30)
        
        heartbeat_thread = threading.Thread(target=heartbeat, daemon=True)
        heartbeat_thread.start()
        
        self._ws.run_forever()
    
    def _subscribe_to_license(self, ws):
        """Subscribe to changes for current license"""
        if not self.license_key: return
        
        # Join the realtime channel for this license
        subscribe_msg = {
            "topic": f"realtime:public:licenses:key=eq.{self.license_key}",
            "event": "phx_join",
            "payload": {"config": {"broadcast": {"self": False}, "presence": {"key": ""}}},
            "ref": str(self._realtime_ref)
        }
        self._realtime_ref += 1
        
        try:
            ws.send(json.dumps(subscribe_msg))
            logger.info(f"Subscribed to license updates: {self.license_key[:8]}...")
        except Exception as e:
            logger.error(f"Subscribe failed: {e}")
    
    def _handle_realtime_message(self, message: str):
        """Handle incoming real-time message"""
        try:
            data = json.loads(message)
            event = data.get("event")
            payload = data.get("payload", {})
            
            # Handle UPDATE events
            if event == "UPDATE":
                record = payload.get("record", {})
                old_record = payload.get("old_record", {})
                
                logger.info(f"Real-time update received for license")
                
                # Check if license was disabled
                if record.get("key") == self.license_key:
                    was_active = old_record.get("active", True)
                    is_active = record.get("active", True)
                    
                    if was_active and not is_active:
                        # LICENSE DISABLED IN REAL-TIME!
                        logger.warning("LICENSE DISABLED BY ADMIN!")
                        self._handle_license_disabled()
                    
                    # Check if machine was removed
                    old_machines = old_record.get("bound_machines") or []
                    new_machines = record.get("bound_machines") or []
                    if self.machine_hash in old_machines and self.machine_hash not in new_machines:
                        logger.warning("MACHINE REMOVED FROM LICENSE!")
                        self._handle_license_disabled()
                    
                    # Update local data
                    if is_active:
                        self.license_data = {
                            "valid": True,
                            "license_type": record.get("license_type", "standard"),
                            "features": record.get("features") or [],
                            "expires_at": record.get("expires_at"),
                            "max_machines": record.get("max_machines", 1)
                        }
                        self._save_cache()
                    
                    if self._on_realtime_update:
                        self._on_realtime_update(record)
            
            # Handle DELETE events
            elif event == "DELETE":
                old_record = payload.get("old_record", {})
                if old_record.get("key") == self.license_key:
                    logger.warning("LICENSE DELETED!")
                    self._handle_license_disabled()
                    
        except Exception as e:
            logger.debug(f"Message parse error: {e}")
    
    def _handle_license_disabled(self, message: str = None):
        """Handle license being disabled/revoked"""
        with self._lock:
            # Prevent multiple triggers
            if self.license_status == LicenseStatus.DISABLED:
                return
            
            old_status = self.license_status
            self.license_status = LicenseStatus.DISABLED
            self.license_data = None
            self._clear_cache()
            
            # Stop all background checks immediately
            self._stop_polling.set()
            self._stop_realtime.set()
            
            # Log the disable reason for debugging
            logger.warning(f"License disabled: {message or 'No reason provided'}")
            
            if self._on_status_change and old_status != LicenseStatus.DISABLED:
                try: self._on_status_change(old_status, LicenseStatus.DISABLED)
                except: pass
            
            if self._on_license_disabled:
                try: self._on_license_disabled(message or "License has been disabled by administrator")
                except: pass

    # ==================== FALLBACK POLLING ====================
    
    def _start_polling(self, interval: int = None):
        """Start fallback polling when WebSocket unavailable"""
        interval = interval or REALTIME_FALLBACK_INTERVAL
        
        if self._polling_thread and self._polling_thread.is_alive():
            return
        
        self._stop_polling.clear()
        self._polling_thread = threading.Thread(
            target=self._polling_loop, args=(interval,), daemon=True, name="LicensePolling"
        )
        self._polling_thread.start()
        logger.info(f"Fallback polling started (every {interval}s)")
    
    def _polling_loop(self, interval: int):
        """Polling loop for license status"""
        while not self._stop_polling.wait(timeout=interval):
            if self.license_key:
                logger.debug(f"Polling check - License: {self.license_key[:8]}... Status: {self.license_status}")
                self._check_license_status()
    
    def _check_license_status(self):
        """Quick check of license status and ban status"""
        if not self.license_key: return
        
        logger.debug(f"Polling license status...")
        
        # Check if user is banned - check both machine_id and machine_hash
        ban_check = self._api_request("GET", "users", filters={"app_id": self.machine_id})
        if not ban_check.get("data"):
            # Also check by machine_hash (for old records)
            ban_check = self._api_request("GET", "users", filters={"app_id": self.machine_hash})
        
        if ban_check.get("data"):
            user_data = ban_check["data"][0]
            if user_data.get("status") == "banned":
                ban_reason = user_data.get("ban_reason", "Your device has been banned by administrator")
                logger.warning(f"USER BANNED: {ban_reason}")
                self._handle_license_disabled(f"Device Banned: {ban_reason}")
                return
        
        # Check license status
        result = self._api_request("GET", "licenses", filters={"key": self.license_key})
        if result.get("error"): 
            logger.debug(f"Poll error: {result.get('error')}")
            return
        
        data = result.get("data", [])
        if not data:
            logger.warning("LICENSE NOT FOUND - DISABLED!")
            self._handle_license_disabled("License has been deleted")
            return
        
        record = data[0]
        is_active = record.get("active", False)
        logger.debug(f"License active status: {is_active}")
        
        if not is_active:
            logger.warning("LICENSE DISABLED BY ADMIN!")
            self._handle_license_disabled("License has been disabled by administrator")
            return
        
        # Check if machine still bound
        bound = record.get("bound_machines") or []
        if self.machine_hash not in bound:
            logger.warning("MACHINE REMOVED FROM LICENSE!")
            self._handle_license_disabled("Device has been removed from license")
    
    # ==================== MAIN VALIDATION ====================
    
    def validate(self, license_key: str = None, start_realtime: bool = True) -> Dict[str, Any]:
        """
        Validate license and start real-time monitoring
        
        Args:
            license_key: License key to validate
            start_realtime: Start real-time monitoring after validation
        """
        with self._lock:
            key = (license_key or self.license_key or "").strip().upper()
            if not key:
                return {"valid": False, "status": LicenseStatus.INVALID, "error": "No license key"}
            
            # Check if this device is banned (check both machine_id and machine_hash)
            ban_check = self._api_request("GET", "users", filters={"app_id": self.machine_id})
            if not ban_check.get("data"):
                # Also check by machine_hash (for old records)
                ban_check = self._api_request("GET", "users", filters={"app_id": self.machine_hash})
            if ban_check.get("data"):
                user_data = ban_check["data"][0]
                if user_data.get("status") == "banned":
                    ban_reason = user_data.get("ban_reason", "Your device has been banned by administrator")
                    self._clear_cache()
                    return {"valid": False, "status": LicenseStatus.DISABLED, "error": f"Device Banned: {ban_reason}"}
            
            # Online validation
            result = self._api_request("GET", "licenses", filters={"key": key})
            
            if result.get("error") == "connection_error":
                return self._handle_offline(key)
            
            if result.get("error"):
                return {"valid": False, "status": LicenseStatus.ERROR, "error": result["error"]}
            
            data = result.get("data", [])
            if not data:
                return {"valid": False, "status": LicenseStatus.INVALID, "error": "Invalid license key"}
            
            record = data[0]
            
            # Check active
            if not record.get("active", False):
                self._clear_cache()
                return {"valid": False, "status": LicenseStatus.DISABLED, "error": "License disabled"}
            
            # Check expiration
            expires_at = record.get("expires_at")
            if expires_at:
                try:
                    expires = datetime.fromisoformat(expires_at.replace("Z", "").split("+")[0])
                    if datetime.utcnow() > expires:
                        return {"valid": False, "status": LicenseStatus.EXPIRED, "error": "License expired"}
                except: pass
            
            # Check machine binding
            bound = record.get("bound_machines") or []
            max_machines = record.get("max_machines", 1)
            
            if self.machine_hash not in bound:
                if len(bound) >= max_machines:
                    return {"valid": False, "status": LicenseStatus.MAX_DEVICES, 
                            "error": f"Max {max_machines} devices allowed"}
                
                # Bind machine
                bound.append(self.machine_hash)
                self._api_request("PATCH", "licenses", data={"bound_machines": bound}, filters={"key": key})
                self._api_request("POST", "activations", data={
                    "license_key": key, "machine_hash": self.machine_hash,
                    "app_id": self.machine_id,
                    "activated_at": datetime.utcnow().isoformat(), "app_version": APP_VERSION
                })
            
            # Track user in users table
            self._track_user(key)
            
            # Update last seen
            self._api_request("PATCH", "licenses", data={
                "last_seen": datetime.utcnow().isoformat(), "last_version": APP_VERSION
            }, filters={"key": key})
            
            # Save state
            self.license_key = key
            self.license_status = LicenseStatus.VALID
            self.license_data = {
                "valid": True,
                "license_type": record.get("license_type", "standard"),
                "features": record.get("features") or [],
                "expires_at": expires_at,
                "max_machines": max_machines,
                "email": record.get("email", ""),
                "name": record.get("name", "")
            }
            self.last_online_validation = datetime.utcnow()
            self._save_cache()
            
            # Start real-time monitoring
            if start_realtime:
                self._start_realtime()
            
            return {"valid": True, "status": LicenseStatus.VALID, **self.license_data}
    
    def _handle_offline(self, key: str) -> Dict:
        """Handle offline validation"""
        if self.license_data and self.license_key == key and self.last_online_validation:
            hours = (datetime.utcnow() - self.last_online_validation).total_seconds() / 3600
            if hours <= MAX_OFFLINE_HOURS:
                return {"valid": True, "status": LicenseStatus.OFFLINE, "offline_hours": round(hours, 1), **self.license_data}
        return {"valid": False, "status": LicenseStatus.ERROR, "error": "Cannot connect - online validation required"}
    
    # ==================== PUBLIC API ====================
    
    def is_valid(self) -> bool:
        return self.license_status == LicenseStatus.VALID
    
    def get_status(self) -> str:
        return self.license_status
    
    def get_license_type(self) -> str:
        return self.license_data.get("license_type", "none") if self.license_data else "none"
    
    def has_feature(self, feature: str) -> bool:
        if not self.license_data: return False
        features = self.license_data.get("features") or []
        return feature.lower() in [f.lower() for f in features]
    
    def get_days_remaining(self) -> Optional[int]:
        if not self.license_data: return None
        expires = self.license_data.get("expires_at")
        if not expires: return None
        try:
            exp_date = datetime.fromisoformat(expires.replace("Z", "").split("+")[0])
            return max(0, (exp_date - datetime.utcnow()).days)
        except: return None
    
    def deactivate(self) -> Dict:
        """Deactivate this machine"""
        if not self.license_key:
            return {"success": False, "error": "No license"}
        
        result = self._api_request("GET", "licenses", filters={"key": self.license_key})
        if result.get("error") or not result.get("data"):
            return {"success": False, "error": "License not found"}
        
        record = result["data"][0]
        bound = record.get("bound_machines") or []
        
        if self.machine_hash in bound:
            bound.remove(self.machine_hash)
            self._api_request("PATCH", "licenses", data={"bound_machines": bound}, filters={"key": self.license_key})
        
        self._stop_realtime_connection()
        self._stop_polling.set()
        self.license_key = None
        self.license_data = None
        self.license_status = LicenseStatus.INVALID
        self._clear_cache()
        
        return {"success": True}
    
    def on_license_disabled(self, callback: Callable[[str], None]):
        """Set callback for when license is disabled - CALLED INSTANTLY"""
        self._on_license_disabled = callback
    
    def on_status_change(self, callback: Callable[[str, str], None]):
        """Set callback for status changes"""
        self._on_status_change = callback
    
    def on_realtime_update(self, callback: Callable[[Dict], None]):
        """Set callback for any real-time updates"""
        self._on_realtime_update = callback
    
    def stop(self):
        """Stop all background processes"""
        self._stop_realtime_connection()
        self._stop_polling.set()
    
    def start_background_validation(self, interval: int = None):
        """Start background validation (backward compatibility)
        
        Note: Real-time monitoring starts automatically with validate().
        This method is kept for backward compatibility.
        """
        # Always start polling as reliable fallback (every 10 seconds)
        self._start_polling(interval or REALTIME_FALLBACK_INTERVAL)
        
        # Also try WebSocket for instant updates
        if WEBSOCKET_AVAILABLE:
            self._start_realtime()
    
    def stop_background_validation(self):
        """Stop background validation (backward compatibility)"""
        self.stop()


# Singleton
_client: Optional[RealtimeLicenseClient] = None
_lock = threading.Lock()

def get_license_client() -> RealtimeLicenseClient:
    global _client
    with _lock:
        if _client is None:
            _client = RealtimeLicenseClient()
        return _client

# Convenience aliases
LicenseClient = RealtimeLicenseClient

def validate_license(key: str = None) -> Dict:
    return get_license_client().validate(key)

def is_license_valid() -> bool:
    return get_license_client().is_valid()


if __name__ == "__main__":
    print("=" * 50)
    print("Real-Time License Client Test")
    print("=" * 50)
    
    client = get_license_client()
    
    def on_disabled(msg):
        print(f"\n🚨 LICENSE DISABLED: {msg}")
        print("Application should exit now!")
    
    client.on_license_disabled(on_disabled)
    
    key = input("\nEnter license key: ").strip()
    if key:
        print("\nValidating...")
        result = client.validate(key)
        print(f"Result: {'✓ Valid' if result['valid'] else '✗ ' + result.get('error', 'Invalid')}")
        
        if result['valid']:
            print(f"Type: {result.get('license_type')}")
            print("\n⚡ Real-time monitoring active!")
            print("Disable this license in admin dashboard to test instant detection...")
            print("Press Ctrl+C to exit\n")
            
            try:
                while client.is_valid():
                    time.sleep(1)
                print("\n❌ License no longer valid!")
            except KeyboardInterrupt:
                print("\nStopped")
            finally:
                client.stop()
