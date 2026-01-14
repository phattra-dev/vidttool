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

-- Activations table
CREATE TABLE IF NOT EXISTS activations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    license_key TEXT REFERENCES licenses(key) ON DELETE CASCADE,
    machine_hash TEXT,
    activated_at TIMESTAMPTZ DEFAULT NOW(),
    ip TEXT,
    app_version TEXT
);

-- Activity logs table
CREATE TABLE IF NOT EXISTS activity_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action TEXT,
    details JSONB,
    ip TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_licenses_active ON licenses(active);
CREATE INDEX IF NOT EXISTS idx_licenses_expires ON licenses(expires_at);
CREATE INDEX IF NOT EXISTS idx_activations_license ON activations(license_key);
CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON activity_logs(timestamp DESC);

-- Enable Row Level Security (optional but recommended)
ALTER TABLE licenses ENABLE ROW LEVEL SECURITY;
ALTER TABLE activations ENABLE ROW LEVEL SECURITY;
ALTER TABLE activity_logs ENABLE ROW LEVEL SECURITY;

-- Create policies for service role access (allows full access with service_role key)
CREATE POLICY "Service role full access" ON licenses FOR ALL USING (true);
CREATE POLICY "Service role full access" ON activations FOR ALL USING (true);
CREATE POLICY "Service role full access" ON activity_logs FOR ALL USING (true);
