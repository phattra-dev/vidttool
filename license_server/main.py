"""
License Server API - Supabase Version
Secure license key management with real-time control
Deploy on: Vercel, Railway, Render, or any Python host
"""

from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime, timedelta
import hashlib
import secrets
import uuid
import json
import os

# Supabase client
from supabase import create_client, Client

app = FastAPI(title="License Server API", version="2.0.0")

# CORS for admin dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Supabase configuration - set these environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")  # Use service_role key for admin operations
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "change-this-secret-key")

# Initialize Supabase client
supabase: Client = None

def get_supabase() -> Client:
    global supabase
    if supabase is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise HTTPException(status_code=500, detail="Supabase not configured")
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    return supabase

def get_machine_hash(machine_id: str) -> str:
    """Generate secure hash of machine ID"""
    return hashlib.sha256(f"{machine_id}:salt:v1".encode()).hexdigest()[:32]

def generate_license_key() -> str:
    """Generate a secure license key"""
    parts = [secrets.token_hex(4).upper() for _ in range(4)]
    return "-".join(parts)

def log_activity(action: str, details: dict, ip: str = None):
    """Log activity for audit trail"""
    try:
        db = get_supabase()
        log_entry = {
            "id": str(uuid.uuid4()),
            "action": action,
            "license_key": details.get("license"),
            "app_id": details.get("app_id"),
            "ip": ip,
            "details": json.dumps(details) if details else None,
            "timestamp": datetime.utcnow().isoformat()
        }
        db.table("activity_logs").insert(log_entry).execute()
    except:
        pass  # Don't fail on logging errors

def verify_admin(api_key: str = Header(None, alias="X-Admin-Key")):
    """Verify admin API key"""
    if api_key != ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid admin key")
    return True

# ============ PUBLIC API (Client) ============

@app.post("/api/validate")
async def validate_license(request: Request):
    """Validate a license key"""
    try:
        data = await request.json()
        license_key = data.get("license_key", "").strip().upper()
        machine_id = data.get("machine_id", "")
        app_version = data.get("app_version", "")
        app_id = data.get("app_id", machine_id)  # Use app_id if provided, fallback to machine_id
        
        if not license_key or not machine_id:
            return JSONResponse({"valid": False, "error": "Missing required fields"})
        
        db = get_supabase()
        client_ip = request.client.host
        
        # Check if user is banned
        user_result = db.table("users").select("*").eq("app_id", app_id).execute()
        if user_result.data and user_result.data[0].get("status") == "banned":
            return JSONResponse({"valid": False, "error": "This device has been banned"})
        
        # Find license
        result = db.table("licenses").select("*").eq("key", license_key).execute()
        
        if not result.data:
            # Track failed attempt
            track_user(db, app_id, None, client_ip, app_version, failed=True)
            log_activity("validate_failed", {"license": license_key, "reason": "not_found", "app_id": app_id}, client_ip)
            return JSONResponse({"valid": False, "error": "Invalid license key"})
        
        license_data = result.data[0]
        
        # Check if license is active
        if not license_data.get("active", False):
            track_user(db, app_id, license_key, client_ip, app_version, failed=True)
            log_activity("validate_failed", {"license": license_key, "reason": "disabled", "app_id": app_id}, client_ip)
            return JSONResponse({"valid": False, "error": "License has been disabled"})
        
        # Check expiration
        if license_data.get("expires_at"):
            expires = datetime.fromisoformat(license_data["expires_at"].replace("Z", ""))
            if datetime.utcnow() > expires:
                track_user(db, app_id, license_key, client_ip, app_version, failed=True)
                log_activity("validate_failed", {"license": license_key, "reason": "expired", "app_id": app_id}, client_ip)
                return JSONResponse({"valid": False, "error": "License has expired"})
        
        # Check machine binding
        machine_hash = get_machine_hash(machine_id)
        bound_machines = license_data.get("bound_machines", []) or []
        max_machines = license_data.get("max_machines", 1)
        
        is_new_activation = machine_hash not in bound_machines
        
        if is_new_activation:
            if len(bound_machines) >= max_machines:
                track_user(db, app_id, license_key, client_ip, app_version, failed=True)
                log_activity("validate_failed", {"license": license_key, "reason": "max_machines", "app_id": app_id}, client_ip)
                return JSONResponse({"valid": False, "error": f"Maximum {max_machines} device(s) allowed"})
            
            # Bind new machine
            bound_machines.append(machine_hash)
            db.table("licenses").update({"bound_machines": bound_machines}).eq("key", license_key).execute()
            
            # Log activation with app_id
            db.table("activations").insert({
                "id": str(uuid.uuid4()),
                "license_key": license_key,
                "machine_hash": machine_hash,
                "app_id": app_id,
                "activated_at": datetime.utcnow().isoformat(),
                "ip": client_ip,
                "app_version": app_version
            }).execute()
            
            log_activity("activate", {"license": license_key, "app_id": app_id}, client_ip)
        
        # Track user (successful validation)
        track_user(db, app_id, license_key, client_ip, app_version, failed=False)
        
        # Update last seen on license
        db.table("licenses").update({
            "last_seen": datetime.utcnow().isoformat(),
            "last_ip": client_ip,
            "last_version": app_version
        }).eq("key", license_key).execute()
        
        log_activity("validate", {"license": license_key, "app_id": app_id}, client_ip)
        
        return JSONResponse({
            "valid": True,
            "license_type": license_data.get("license_type", "standard"),
            "features": license_data.get("features", []),
            "expires_at": license_data.get("expires_at"),
            "message": license_data.get("custom_message", "")
        })
        
    except Exception as e:
        return JSONResponse({"valid": False, "error": str(e)})


def track_user(db, app_id: str, license_key: str, ip: str, app_version: str, failed: bool = False):
    """Track user in users table"""
    try:
        now = datetime.utcnow().isoformat()
        
        # Check if user exists
        result = db.table("users").select("*").eq("app_id", app_id).execute()
        
        if result.data:
            # Update existing user
            user = result.data[0]
            updates = {
                "last_seen": now,
                "last_ip": ip,
                "total_visits": (user.get("total_visits") or 0) + 1
            }
            
            if license_key:
                updates["license_key"] = license_key
                if not failed:
                    updates["status"] = "active"
            
            if failed:
                failed_attempts = (user.get("failed_attempts") or 0) + 1
                updates["failed_attempts"] = failed_attempts
                
                # Auto-flag suspicious activity
                if failed_attempts >= 3 and user.get("status") not in ["banned", "hacking"]:
                    updates["status"] = "suspicious"
                if failed_attempts >= 10 and user.get("status") != "banned":
                    updates["status"] = "hacking"
            
            db.table("users").update(updates).eq("app_id", app_id).execute()
        else:
            # Create new user
            user_data = {
                "app_id": app_id,
                "license_key": license_key,
                "status": "active" if (license_key and not failed) else "visitor",
                "first_seen": now,
                "last_seen": now,
                "last_ip": ip,
                "total_visits": 1,
                "failed_attempts": 1 if failed else 0
            }
            db.table("users").insert(user_data).execute()
    except Exception as e:
        print(f"Error tracking user: {e}")
        pass  # Don't fail validation on tracking errors

@app.post("/api/deactivate")
async def deactivate_machine(request: Request):
    """Deactivate a machine from license"""
    try:
        data = await request.json()
        license_key = data.get("license_key", "").strip().upper()
        machine_id = data.get("machine_id", "")
        
        db = get_supabase()
        result = db.table("licenses").select("*").eq("key", license_key).execute()
        
        if not result.data:
            return JSONResponse({"success": False, "error": "Invalid license"})
        
        license_data = result.data[0]
        machine_hash = get_machine_hash(machine_id)
        bound_machines = license_data.get("bound_machines", []) or []
        
        if machine_hash in bound_machines:
            bound_machines.remove(machine_hash)
            db.table("licenses").update({"bound_machines": bound_machines}).eq("key", license_key).execute()
            log_activity("deactivate", {"license": license_key, "machine": machine_hash[:8]}, request.client.host)
            return JSONResponse({"success": True})
        
        return JSONResponse({"success": False, "error": "Machine not found"})
        
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})

# ============ ADMIN API ============

@app.get("/admin/licenses")
async def list_licenses(admin: bool = Depends(verify_admin)):
    """List all licenses"""
    db = get_supabase()
    result = db.table("licenses").select("*").order("created_at", desc=True).execute()
    return {"licenses": result.data, "total": len(result.data)}

@app.post("/admin/licenses")
async def create_license(request: Request, admin: bool = Depends(verify_admin)):
    """Create a new license"""
    data = await request.json()
    db = get_supabase()
    
    license_key = generate_license_key()
    
    # Calculate expiration
    expires_at = None
    if data.get("duration_days"):
        expires_at = (datetime.utcnow() + timedelta(days=data["duration_days"])).isoformat()
    
    license_data = {
        "key": license_key,
        "email": data.get("email", ""),
        "name": data.get("name", ""),
        "license_type": data.get("license_type", "standard"),
        "max_machines": data.get("max_machines", 1),
        "bound_machines": [],
        "features": data.get("features", []),
        "active": True,
        "created_at": datetime.utcnow().isoformat(),
        "expires_at": expires_at,
        "notes": data.get("notes", ""),
        "custom_message": data.get("custom_message", "")
    }
    
    db.table("licenses").insert(license_data).execute()
    log_activity("license_created", {"license": license_key, "email": data.get("email")})
    
    return {"success": True, "license_key": license_key, "data": license_data}

@app.put("/admin/licenses/{license_key}")
async def update_license(license_key: str, request: Request, admin: bool = Depends(verify_admin)):
    """Update a license"""
    data = await request.json()
    db = get_supabase()
    
    # Update allowed fields
    updates = {}
    allowed_fields = ["email", "name", "license_type", "max_machines", "features", 
                      "active", "notes", "custom_message", "expires_at"]
    
    for field in allowed_fields:
        if field in data:
            updates[field] = data[field]
    
    if updates:
        db.table("licenses").update(updates).eq("key", license_key).execute()
        log_activity("license_updated", {"license": license_key, "updates": list(updates.keys())})
    
    return {"success": True}

@app.delete("/admin/licenses/{license_key}")
async def delete_license(license_key: str, admin: bool = Depends(verify_admin)):
    """Delete a license"""
    db = get_supabase()
    db.table("licenses").delete().eq("key", license_key).execute()
    log_activity("license_deleted", {"license": license_key})
    return {"success": True}

@app.post("/admin/licenses/{license_key}/reset")
async def reset_license_machines(license_key: str, admin: bool = Depends(verify_admin)):
    """Reset all machine bindings for a license"""
    db = get_supabase()
    db.table("licenses").update({"bound_machines": []}).eq("key", license_key).execute()
    log_activity("license_reset", {"license": license_key})
    return {"success": True}

@app.post("/admin/licenses/{license_key}/toggle")
async def toggle_license(license_key: str, admin: bool = Depends(verify_admin)):
    """Toggle license active status"""
    db = get_supabase()
    result = db.table("licenses").select("active").eq("key", license_key).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="License not found")
    
    current_status = result.data[0].get("active", True)
    db.table("licenses").update({"active": not current_status}).eq("key", license_key).execute()
    log_activity("license_toggled", {"license": license_key, "new_status": not current_status})
    return {"success": True, "active": not current_status}

@app.get("/admin/activations")
async def list_activations(admin: bool = Depends(verify_admin)):
    """List all activations"""
    db = get_supabase()
    result = db.table("activations").select("*").order("activated_at", desc=True).execute()
    return {"activations": result.data}

@app.get("/admin/logs")
async def get_logs(limit: int = 100, admin: bool = Depends(verify_admin)):
    """Get activity logs"""
    db = get_supabase()
    result = db.table("activity_logs").select("*").order("timestamp", desc=True).limit(limit).execute()
    return {"logs": result.data}

@app.get("/admin/stats")
async def get_stats(admin: bool = Depends(verify_admin)):
    """Get dashboard statistics"""
    db = get_supabase()
    
    licenses = db.table("licenses").select("*").execute()
    activations = db.table("activations").select("*").execute()
    
    total_licenses = len(licenses.data)
    active_licenses = sum(1 for l in licenses.data if l.get("active", False))
    expired_licenses = sum(1 for l in licenses.data 
                          if l.get("expires_at") and datetime.fromisoformat(l["expires_at"].replace("Z", "")) < datetime.utcnow())
    total_activations = len(activations.data)
    
    # Recent activity (last 24h)
    yesterday = (datetime.utcnow() - timedelta(days=1)).isoformat()
    logs = db.table("activity_logs").select("*").gte("timestamp", yesterday).execute()
    recent_activity = len(logs.data)
    
    # License types breakdown
    license_types = {}
    for l in licenses.data:
        lt = l.get("license_type", "standard")
        license_types[lt] = license_types.get(lt, 0) + 1
    
    return {
        "total_licenses": total_licenses,
        "active_licenses": active_licenses,
        "expired_licenses": expired_licenses,
        "total_activations": total_activations,
        "recent_activity_24h": recent_activity,
        "license_types": license_types
    }

@app.post("/admin/bulk/generate")
async def bulk_generate_licenses(request: Request, admin: bool = Depends(verify_admin)):
    """Generate multiple licenses at once"""
    data = await request.json()
    db = get_supabase()
    count = min(data.get("count", 1), 100)  # Max 100 at once
    
    licenses = []
    for _ in range(count):
        license_key = generate_license_key()
        
        expires_at = None
        if data.get("duration_days"):
            expires_at = (datetime.utcnow() + timedelta(days=data["duration_days"])).isoformat()
        
        license_data = {
            "key": license_key,
            "email": "",
            "name": data.get("batch_name", f"Batch {datetime.utcnow().strftime('%Y%m%d')}"),
            "license_type": data.get("license_type", "standard"),
            "max_machines": data.get("max_machines", 1),
            "bound_machines": [],
            "features": data.get("features", []),
            "active": True,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": expires_at,
            "notes": "Bulk generated",
        }
        
        db.table("licenses").insert(license_data).execute()
        licenses.append(license_key)
    
    log_activity("bulk_generate", {"count": count})
    return {"success": True, "licenses": licenses}

# Health check
@app.get("/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

# Serve admin dashboard
@app.get("/")
async def root():
    return {"message": "License Server API v2.0", "docs": "/docs"}
