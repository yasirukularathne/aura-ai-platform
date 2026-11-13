
CREATE TABLE IF NOT EXISTS workspaces (
    workspace_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_workspaces_tenant_created
    ON workspaces (tenant_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_conversations_tenant_workspace_updated
    ON conversations (tenant_id, workspace_id, updated_at DESC);
