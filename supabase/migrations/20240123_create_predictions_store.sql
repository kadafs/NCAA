-- Create the predictions_store table for Vercel/Next.js to read from
CREATE TABLE IF NOT EXISTS predictions_store (
    league TEXT PRIMARY KEY,
    data JSONB NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS (Row Level Security)
ALTER TABLE predictions_store ENABLE ROW LEVEL SECURITY;

-- Allow public read access (if you want public or restricted)
CREATE POLICY "Allow public read access" ON predictions_store
    FOR SELECT USING (true);

-- Allow service role to manage data
CREATE POLICY "Allow service role to manage all" ON predictions_store
    FOR ALL USING (auth.role() = 'service_role');
