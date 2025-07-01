-- PostgreSQL initialization script for Bot Provisional
-- This script runs when the PostgreSQL container starts for the first time

-- Create database if not exists (redundant but safe)
SELECT 'CREATE DATABASE bot_provisional'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'bot_provisional')\gexec

-- Connect to the bot_provisional database
\c bot_provisional;

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS fine_tuning;
CREATE SCHEMA IF NOT EXISTS analytics;

-- Create tables for fine-tuning data
CREATE TABLE IF NOT EXISTS fine_tuning.conversations (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    session_id UUID NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    user_message TEXT NOT NULL,
    bot_response TEXT NOT NULL,
    was_corrected BOOLEAN DEFAULT FALSE,
    corrected_response TEXT,
    correction_timestamp TIMESTAMP WITH TIME ZONE,
    correction_reason TEXT,
    quality_score INTEGER CHECK (quality_score >= 1 AND quality_score <= 5),
    tags TEXT[],
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON fine_tuning.conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_session_id ON fine_tuning.conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_conversations_timestamp ON fine_tuning.conversations(timestamp);
CREATE INDEX IF NOT EXISTS idx_conversations_quality_score ON fine_tuning.conversations(quality_score);
CREATE INDEX IF NOT EXISTS idx_conversations_tags ON fine_tuning.conversations USING gin(tags);
CREATE INDEX IF NOT EXISTS idx_conversations_metadata ON fine_tuning.conversations USING gin(metadata);

-- Create table for conversation analytics
CREATE TABLE IF NOT EXISTS analytics.daily_stats (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    total_conversations INTEGER DEFAULT 0,
    total_corrections INTEGER DEFAULT 0,
    average_quality_score NUMERIC(3,2),
    unique_users INTEGER DEFAULT 0,
    total_tokens_used INTEGER DEFAULT 0,
    total_cost NUMERIC(10,4) DEFAULT 0.00,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for analytics
CREATE INDEX IF NOT EXISTS idx_daily_stats_date ON analytics.daily_stats(date);

-- Create table for system metrics
CREATE TABLE IF NOT EXISTS analytics.system_metrics (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metric_name VARCHAR(100) NOT NULL,
    metric_value NUMERIC,
    metric_unit VARCHAR(50),
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for system metrics
CREATE INDEX IF NOT EXISTS idx_system_metrics_timestamp ON analytics.system_metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_system_metrics_name ON analytics.system_metrics(metric_name);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_conversations_updated_at 
    BEFORE UPDATE ON fine_tuning.conversations 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_daily_stats_updated_at 
    BEFORE UPDATE ON analytics.daily_stats 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert initial data
INSERT INTO analytics.daily_stats (date, total_conversations, total_corrections, average_quality_score, unique_users)
VALUES (CURRENT_DATE, 0, 0, 0.00, 0)
ON CONFLICT (date) DO NOTHING;

-- Grant permissions (if needed for specific users)
-- GRANT ALL PRIVILEGES ON SCHEMA fine_tuning TO bot_user;
-- GRANT ALL PRIVILEGES ON SCHEMA analytics TO bot_user;
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA fine_tuning TO bot_user;
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA analytics TO bot_user;

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'Bot Provisional database initialized successfully at %', NOW();
END $$;