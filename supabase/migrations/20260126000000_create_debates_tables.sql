-- Migration: Create debates tables
-- Story 13: Debates Module - CRUD & Models
-- 
-- This migration creates the core tables for the Prizms debate system:
-- - debates: Main debate records
-- - debate_rounds: Individual rounds within a debate
-- - debate_responses: Personality responses within a round
-- - debate_synthesis: Final synthesis for a debate

-- ============================================================================
-- DEBATES TABLE
-- ============================================================================

CREATE TABLE debates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    provider VARCHAR(50) NOT NULL,
    model VARCHAR(100) NOT NULL,
    max_rounds INTEGER NOT NULL DEFAULT 3,
    current_round INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    -- Settings stored as JSON for flexibility
    settings JSONB DEFAULT '{}'::jsonb,

    -- Cost tracking (separate input/output to match Pydantic models)
    total_input_tokens INTEGER DEFAULT 0,
    total_output_tokens INTEGER DEFAULT 0,
    total_cost DECIMAL(10, 6) DEFAULT 0,

    -- Error info
    error_message TEXT,

    CONSTRAINT valid_status CHECK (status IN ('pending', 'active', 'completed', 'failed', 'cancelled'))
);

-- ============================================================================
-- DEBATE ROUNDS TABLE
-- ============================================================================

CREATE TABLE debate_rounds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    debate_id UUID NOT NULL REFERENCES debates(id) ON DELETE CASCADE,
    round_number INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(debate_id, round_number)
);

-- ============================================================================
-- DEBATE RESPONSES TABLE
-- ============================================================================

CREATE TABLE debate_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    round_id UUID NOT NULL REFERENCES debate_rounds(id) ON DELETE CASCADE,
    personality_name VARCHAR(100) NOT NULL,
    thinking_content TEXT,
    answer_content TEXT,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cost DECIMAL(10, 6) DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(round_id, personality_name)
);

-- ============================================================================
-- DEBATE SYNTHESIS TABLE
-- ============================================================================

CREATE TABLE debate_synthesis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    debate_id UUID NOT NULL REFERENCES debates(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cost DECIMAL(10, 6) DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(debate_id)
);

-- ============================================================================
-- ROW LEVEL SECURITY
-- ============================================================================

-- Enable RLS on all tables
ALTER TABLE debates ENABLE ROW LEVEL SECURITY;
ALTER TABLE debate_rounds ENABLE ROW LEVEL SECURITY;
ALTER TABLE debate_responses ENABLE ROW LEVEL SECURITY;
ALTER TABLE debate_synthesis ENABLE ROW LEVEL SECURITY;

-- DEBATES: Users can only access their own debates
CREATE POLICY "Users can view own debates" ON debates
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own debates" ON debates
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own debates" ON debates
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own debates" ON debates
    FOR DELETE USING (auth.uid() = user_id);

-- DEBATE ROUNDS: Access through parent debate ownership
CREATE POLICY "Users can view own debate rounds" ON debate_rounds
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM debates 
            WHERE debates.id = debate_rounds.debate_id 
            AND debates.user_id = auth.uid()
        )
    );

-- Backend service uses service role for inserts (bypasses RLS)
CREATE POLICY "Service can insert rounds" ON debate_rounds
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Service can update rounds" ON debate_rounds
    FOR UPDATE USING (true);

CREATE POLICY "Service can delete rounds" ON debate_rounds
    FOR DELETE USING (true);

-- DEBATE RESPONSES: Access through parent round -> debate ownership
CREATE POLICY "Users can view own responses" ON debate_responses
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM debate_rounds r
            JOIN debates d ON d.id = r.debate_id
            WHERE r.id = debate_responses.round_id 
            AND d.user_id = auth.uid()
        )
    );

CREATE POLICY "Service can insert responses" ON debate_responses
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Service can update responses" ON debate_responses
    FOR UPDATE USING (true);

CREATE POLICY "Service can delete responses" ON debate_responses
    FOR DELETE USING (true);

-- DEBATE SYNTHESIS: Access through parent debate ownership
CREATE POLICY "Users can view own synthesis" ON debate_synthesis
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM debates 
            WHERE debates.id = debate_synthesis.debate_id 
            AND debates.user_id = auth.uid()
        )
    );

CREATE POLICY "Service can insert synthesis" ON debate_synthesis
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Service can update synthesis" ON debate_synthesis
    FOR UPDATE USING (true);

CREATE POLICY "Service can delete synthesis" ON debate_synthesis
    FOR DELETE USING (true);

-- ============================================================================
-- INDEXES
-- ============================================================================

-- Debates: Common query patterns
CREATE INDEX idx_debates_user_id ON debates(user_id);
CREATE INDEX idx_debates_status ON debates(status);
CREATE INDEX idx_debates_created_at ON debates(created_at DESC);
CREATE INDEX idx_debates_user_status ON debates(user_id, status);

-- Rounds: Lookup by debate
CREATE INDEX idx_debate_rounds_debate_id ON debate_rounds(debate_id);

-- Responses: Lookup by round
CREATE INDEX idx_debate_responses_round_id ON debate_responses(round_id);

-- Synthesis: Lookup by debate
CREATE INDEX idx_debate_synthesis_debate_id ON debate_synthesis(debate_id);

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Auto-update updated_at on debates
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_debates_updated_at
    BEFORE UPDATE ON debates
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
