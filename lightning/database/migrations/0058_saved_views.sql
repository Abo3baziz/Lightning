-- Named register filters. Only the filter fields supported by SavedViewService are stored.
CREATE TABLE saved_views (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL CHECK (length(trim(name)) BETWEEN 1 AND 64),
    account_id  INTEGER REFERENCES accounts(id) ON DELETE CASCADE,
    preset      TEXT NOT NULL CHECK (preset IN ('all_time','this_month','last_month','year_to_date','custom')),
    date_from   TEXT,
    date_to     TEXT,
    query_text  TEXT NOT NULL DEFAULT '',
    tag         TEXT NOT NULL DEFAULT '',
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    CHECK ((preset='custom' AND date_from IS NOT NULL AND date_to IS NOT NULL AND date_to >= date_from)
        OR (preset!='custom' AND date_from IS NULL AND date_to IS NULL))
);
CREATE UNIQUE INDEX ux_saved_views_scope_name ON saved_views(COALESCE(account_id, 0), name COLLATE NOCASE);
CREATE INDEX ix_saved_views_scope ON saved_views(account_id, name COLLATE NOCASE, id);
