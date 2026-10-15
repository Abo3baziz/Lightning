ALTER TABLE planned_items ADD COLUMN match_window_days INTEGER NOT NULL DEFAULT 7
    CHECK (match_window_days BETWEEN 0 AND 31);
ALTER TABLE planned_items ADD COLUMN match_tolerance_pct INTEGER NOT NULL DEFAULT 10
    CHECK (match_tolerance_pct BETWEEN 0 AND 25);
UPDATE planned_items SET match_tolerance_pct=1 WHERE kind='LOAN';
