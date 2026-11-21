CREATE TABLE IF NOT EXISTS ingestion_jobs (
    job_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    workspace_id TEXT,
    filename TEXT NOT NULL,
    storage_key TEXT NOT NULL,
    checksum TEXT NOT NULL,
    status TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_scope
    ON ingestion_jobs (tenant_id, workspace_id, checksum);
