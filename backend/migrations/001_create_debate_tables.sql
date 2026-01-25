-- Migration: 001_create_debate_tables
-- Description: Create tables for debate management with RLS policies
-- Run this in Supabase SQL Editor

-- ============================================================================
-- TABLES
-- ============================================================================

-- Debates table
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
    completed_at TIMESTAMPTZ,

    -- Settings stored as JSON for flexibility
    settings JSONB DEFAULT '{}'::jsonb,

    -- Cost tracking
    total_tokens INTEGER DEFAULT 0,
    total_cost DECIMAL(10, 6) DEFAULT 0,

    CONSTRAINT valid_status CHECK (status IN ('pending', 'active', 'completed', 'failed'))
);

-- Debate rounds table
CREATE TABLE debate_rounds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    debate_id UUID NOT NULL REFERENCES debates(id) ON DELETE CASCADE,
    round_number INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(debate_id, round_number)
);

-- Personality responses within a round
CREATE TABLE debate_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    round_id UUID NOT NULL REFERENCES debate_rounds(id) ON DELETE CASCADE,
    personality_name VARCHAR(100) NOT NULL,
    thinking_content TEXT,
    answer_content TEXT,
    tokens_used INTEGER DEFAULT 0,
    cost DECIMAL(10, 6) DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(round_id, personality_name)
);

-- Synthesis (final response)
CREATE TABLE debate_synthesis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    debate_id UUID NOT NULL REFERENCES debates(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    tokens_used INTEGER DEFAULT 0,
    cost DECIMAL(10, 6) DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(debate_id)
);

-- ============================================================================
-- ROW LEVEL SECURITY
-- ============================================================================

-- Enable Row Level Security
ALTER TABLE debates ENABLE ROW LEVEL SECURITY;
ALTER TABLE debate_rounds ENABLE ROW LEVEL SECURITY;
ALTER TABLE debate_responses ENABLE ROW LEVEL SECURITY;
ALTER TABLE debate_synthesis ENABLE ROW LEVEL SECURITY;

-- RLS Policies: Users can only see their own debates
CREATE POLICY "Users can view own debates" ON debates
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own debates" ON debates
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own debates" ON debates
    FOR UPDATE USING (auth.uid() = user_id);

-- Rounds inherit access from parent debate
CREATE POLICY "Users can view own debate rounds" ON debate_rounds
    FOR SELECT USING (
        EXISTS (SELECT 1 FROM debates WHERE debates.id = debate_rounds.debate_id AND debates.user_id = auth.uid())
    );

CREATE POLICY "Service can insert rounds" ON debate_rounds
    FOR INSERT WITH CHECK (true);  -- Backend service inserts via service role

-- Similar policies for responses and synthesis
CREATE POLICY "Users can view own responses" ON debate_responses
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM debate_rounds r
            JOIN debates d ON d.id = r.debate_id
            WHERE r.id = debate_responses.round_id AND d.user_id = auth.uid()
        )
    );

CREATE POLICY "Service can insert responses" ON debate_responses
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Users can view own synthesis" ON debate_synthesis
    FOR SELECT USING (
        EXISTS (SELECT 1 FROM debates WHERE debates.id = debate_synthesis.debate_id AND debates.user_id = auth.uid())
    );

CREATE POLICY "Service can insert synthesis" ON debate_synthesis
    FOR INSERT WITH CHECK (true);

-- ============================================================================
-- INDEXES
-- ============================================================================

-- Indexes for performance
CREATE INDEX idx_debates_user_id ON debates(user_id);
CREATE INDEX idx_debates_status ON debates(status);
CREATE INDEX idx_debates_created_at ON debates(created_at DESC);
CREATE INDEX idx_debate_rounds_debate_id ON debate_rounds(debate_id);
CREATE INDEX idx_debate_responses_round_id ON debate_responses(round_id);
