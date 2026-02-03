#!/usr/bin/env python3
"""
Verify ban detection logic without requiring user input
"""

from license_client import RealtimeLicenseClient
import json

def test_ban_detection_logic():
    """Test the ban detection logic"""
    print("🔍 Testing Ban Detection Logic")
    print("-" * 40)
    
    client = RealtimeLicenseClient()
    
    # Test machine ID generation
    print(f"Machine ID: {client.machine_id[:16]}...")
    print(f"Machine Hash: {client.machine_hash[:16]}...")
    
    # Test API request structure for ban checking
    print(f"\n📡 Testing API request structure...")
    
    # Simulate ban check request
    filters = {"app_id": client.machine_id}
    print(f"Ban check filter (machine_id): {filters}")
    
    filters2 = {"app_id": client.machine_hash}
    print(f"Ban check filter (machine_hash): {filters2}")
    
    # Test message handling
    print(f"\n💬 Testing message handling...")
    
    test_messages = [
        "Device Banned: Suspicious activity detected",
        "Your device has been banned by administrator", 
        "License has been disabled by administrator",
        "Device has been removed from license"
    ]
    
    for msg in test_messages:
        is_ban = ("device banned" in msg.lower() or 
                 "banned:" in msg.lower() or 
                 "has been banned" in msg.lower())
        print(f"   '{msg[:40]}...' -> Ban message: {is_ban}")
    
    print(f"\n✅ Logic verification complete")
    
    # Test callback setup
    callback_called = False
    callback_message = ""
    
    def test_callback(msg):
        nonlocal callback_called, callback_message
        callback_called = True
        callback_message = msg
        print(f"🔔 Callback triggered: {msg}")
    
    client.on_license_disabled(test_callback)
    
    # Simulate a ban
    print(f"\n🧪 Simulating ban detection...")
    client._handle_license_disabled("Device Banned: Test ban message")
    
    if callback_called:
        print(f"✅ Callback system working: {callback_message}")
    else:
        print(f"❌ Callback system failed")
    
    print(f"\n🏁 Test complete")

if __name__ == "__main__":
    test_ban_detection_logic()