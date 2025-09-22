-- Production database initialization script
-- This script sets up the initial database configuration

-- Create extensions if they don't exist
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Create application user with limited privileges
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'acrylican_app') THEN
        CREATE ROLE acrylican_app WITH LOGIN PASSWORD 'app_password_to_be_changed';
    END IF;
END
$$;

-- Grant necessary permissions
GRANT CONNECT ON DATABASE acrylican_platform TO acrylican_app;
GRANT USAGE ON SCHEMA public TO acrylican_app;
GRANT CREATE ON SCHEMA public TO acrylican_app;

-- Set up logging table for audit purposes
CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    table_name VARCHAR(50) NOT NULL,
    operation VARCHAR(10) NOT NULL,
    old_data JSONB,
    new_data JSONB,
    user_id VARCHAR(255),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_audit_log_table_name ON audit_log(table_name);
CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON audit_log(user_id);

-- Set up connection limits
ALTER ROLE acrylican_app CONNECTION LIMIT 20;