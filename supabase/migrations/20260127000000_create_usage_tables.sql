-- Migration: Create usage tracking tables
-- Story 15: Usage Module Implementation
--
-- This migration creates the tables for usage tracking:
-- - user_usage: Aggregated usage per billing period (monthly)
-- - usage_log: Individual request records for detailed tracking
-- Plus the upsert_user_usage function for atomic updates

-- ============================================================================
-- USER USAGE TABLE (Aggregated by period)
-- ============================================================================

CREATE TABLE user_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    total_tokens INTEGER DEFAULT 0,
    total_cost DECIMAL(10, 6) DEFAULT 0,
    debates_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(user_id, period_start)
);

-- ============================================================================
-- USAGE LOG TABLE (Individual requests)
-- ============================================================================

CREATE TABLE usage_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    debate_id UUID REFERENCES debates(id) ON DELETE SET NULL,
    provider VARCHAR(50) NOT NULL,
    model VARCHAR(100) NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    cached_tokens INTEGER DEFAULT 0,
    cost DECIMAL(10, 6) NOT NULL,
    operation VARCHAR(50),
    personality VARCHAR(100),
    round_number INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- ROW LEVEL SECURITY
-- ============================================================================

-- Enable RLS
ALTER TABLE user_usage ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_log ENABLE ROW LEVEL SECURITY;

-- Policies: Users can view own usage
CREATE POLICY "Users can view own usage" ON user_usage
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can view own usage log" ON usage_log
    FOR SELECT USING (auth.uid() = user_id);

-- Service role policies for insert/update (backend uses service role)
CREATE POLICY "Service can manage usage" ON user_usage
    FOR ALL USING (true);

CREATE POLICY "Service can insert usage log" ON usage_log
    FOR INSERT WITH CHECK (true);

-- ============================================================================
-- INDEXES
-- ============================================================================

-- Query performance indexes
CREATE INDEX idx_user_usage_user_period ON user_usage(user_id, period_start);
CREATE INDEX idx_usage_log_user ON usage_log(user_id);
CREATE INDEX idx_usage_log_created ON usage_log(created_at);
CREATE INDEX idx_usage_log_debate ON usage_log(debate_id);

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Upsert user usage for a period
-- This function atomically updates or creates a usage record for a billing period
CREATE OR REPLACE FUNCTION upsert_user_usage(
    p_user_id UUID,
    p_period_start TIMESTAMPTZ,
    p_period_end TIMESTAMPTZ,
    p_tokens INTEGER,
    p_cost DECIMAL,
    p_increment_debates BOOLEAN DEFAULT FALSE
)
RETURNS VOID AS $$
BEGIN
    INSERT INTO user_usage (user_id, period_start, period_end, total_tokens, total_cost, debates_count)
    VALUES (p_user_id, p_period_start, p_period_end, p_tokens, p_cost, CASE WHEN p_increment_debates THEN 1 ELSE 0 END)
    ON CONFLICT (user_id, period_start)
    DO UPDATE SET
        total_tokens = user_usage.total_tokens + p_tokens,
        total_cost = user_usage.total_cost + p_cost,
        debates_count = user_usage.debates_count + CASE WHEN p_increment_debates THEN 1 ELSE 0 END,
        updated_at = NOW();
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Auto-update updated_at on user_usage
CREATE TRIGGER update_user_usage_updated_at
    BEFORE UPDATE ON user_usage
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
