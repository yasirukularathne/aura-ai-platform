CREATE TABLE IF NOT EXISTS api_keys (
    key_id TEXT PRIMARY KEY,
    key_hash TEXT UNIQUE NOT NULL,
    tenant_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('viewer', 'editor', 'admin')),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_api_keys_tenant
    ON api_keys (tenant_id, active);

CREATE TABLE IF NOT EXISTS rate_limit_windows (
    key_id TEXT NOT NULL REFERENCES api_keys(key_id) ON DELETE CASCADE,
    bucket TEXT NOT NULL,
    window_start BIGINT NOT NULL,
    request_count INTEGER NOT NULL,
    PRIMARY KEY (key_id, bucket)
);

CREATE TABLE IF NOT EXISTS audit_events (
    event_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    actor_key_id TEXT NOT NULL,
    action TEXT NOT NULL,
    resource TEXT NOT NULL,
    details TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE ingestion_jobs ADD COLUMN IF NOT EXISTS file_path TEXT;
ALTER TABLE ingestion_jobs ADD COLUMN IF NOT EXISTS content_type TEXT;

CREATE INDEX IF NOT EXISTS idx_conversations_tenant_updated
    ON conversations (tenant_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_messages_tenant_conversation
    ON conversation_messages (tenant_id, conversation_id, created_at);
