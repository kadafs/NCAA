-- Add mode column to predictions_history table
-- Default to 'safe' for existing rows to maintain consistency

ALTER TABLE predictions_history 
ADD COLUMN IF NOT EXISTS mode text DEFAULT 'safe';

-- Optional: Create an index if we plan to query by mode often
CREATE INDEX IF NOT EXISTS idx_predictions_history_mode ON predictions_history(mode);
