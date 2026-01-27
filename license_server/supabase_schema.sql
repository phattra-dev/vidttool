-- Supabase SQL Schema for License Server
-- Run this in Supabase SQL Editor to create the tables

-- Licenses table
CREATE TABLE IF NOT EXISTS licenses (
    key TEXT PRIMARY KEY,
    email TEXT,
    name TEXT,
    license_type TEXT DEFAULT 'standard',
    max_machines INTEGER DEFAULT 1,
    bound_machines TEXT[] DEFAULT '{}',
    features TEXT[] DEFAULT '{}',
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    last_seen TIMESTAMPTZ,
    last_ip TEXT,
    last_version TEXT,
    notes TEXT,
    custom_message TEXT
);

-- Activations table (tracks device activations)
CREATE TABLE IF NOT EXISTS activations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    license_key TEXT REFERENCES licenses(key) ON DELETE CASCADE,
    machine_hash TEXT,
    app_id TEXT,
    activated_at TIMESTAMPTZ DEFAULT NOW(),
    ip TEXT,
    app_version TEXT
);

-- Users table (tracks all users/devices)
CREATE TABLE IF NOT EXISTS users (
    app_id TEXT PRIMARY KEY,
    license_key TEXT,
    status TEXT DEFAULT 'visitor',  -- visitor, active, suspicious, hacking, banned
    first_seen TIMESTAMPTZ DEFAULT NOW(),
    last_seen TIMESTAMPTZ DEFAULT NOW(),
    last_ip TEXT,
    total_visits INTEGER DEFAULT 0,
    failed_attempts INTEGER DEFAULT 0,
    ban_reason TEXT,
    banned_at TIMESTAMPTZ
);

-- Activity logs table
CREATE TABLE IF NOT EXISTS activity_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action TEXT,
    license_key TEXT,
    app_id TEXT,
    ip TEXT,
    details TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_licenses_active ON licenses(active);
CREATE INDEX IF NOT EXISTS idx_licenses_expires ON licenses(expires_at);
CREATE INDEX IF NOT EXISTS idx_activations_license ON activations(license_key);
CREATE INDEX IF NOT EXISTS idx_activations_app_id ON activations(app_id);
CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);
CREATE INDEX IF NOT EXISTS idx_users_license ON users(license_key);
CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON activity_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_logs_action ON activity_logs(action);

-- Enable Row Level Security (optional but recommended)
ALTER TABLE licenses ENABLE ROW LEVEL SECURITY;
ALTER TABLE activations ENABLE ROW LEVEL SECURITY;
ALTER TABLE activity_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Create policies for service role access (allows full access with service_role key)
DROP POLICY IF EXISTS "Service role full access" ON licenses;
DROP POLICY IF EXISTS "Service role full access" ON activations;
DROP POLICY IF EXISTS "Service role full access" ON activity_logs;
DROP POLICY IF EXISTS "Service role full access" ON users;

CREATE POLICY "Service role full access" ON licenses FOR ALL USING (true);
CREATE POLICY "Service role full access" ON activations FOR ALL USING (true);
CREATE POLICY "Service role full access" ON activity_logs FOR ALL USING (true);
CREATE POLICY "Service role full access" ON users FOR ALL USING (true);

-- Migration: Add app_id column to activations if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'activations' AND column_name = 'app_id') THEN
        ALTER TABLE activations ADD COLUMN app_id TEXT;
    END IF;
END $$;
