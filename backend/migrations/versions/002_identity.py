"""Identity, workspace membership and redacted audit. Frozen migration DDL."""

from alembic import op

revision = "002_identity"
down_revision = "001_foundation"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "CREATE TABLE users (\n\tid UUID NOT NULL, \n\temail VARCHAR(254) NOT NULL, \n\tpassword_hash VARCHAR(512) NOT NULL, \n\tdisplay_name VARCHAR(100) NOT NULL, \n\tstatus VARCHAR(16) NOT NULL, \n\tverified_at TIMESTAMP WITH TIME ZONE, \n\tauth_version INTEGER NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT ck_user_status CHECK (status IN ('active','disabled')), \n\tUNIQUE (email)\n)"
    )
    op.execute(
        "CREATE TABLE workspaces (\n\tid UUID NOT NULL, \n\tname VARCHAR(100) NOT NULL, \n\tstatus VARCHAR(16) NOT NULL, \n\tprivacy_epoch BIGINT NOT NULL, \n\tcountry VARCHAR(2) NOT NULL, \n\ttimezone VARCHAR(64) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT ck_workspace_status CHECK (status IN ('active','suspended'))\n)"
    )
    op.execute(
        "CREATE TABLE audit_events (\n\tid UUID NOT NULL, \n\tworkspace_id UUID, \n\tactor_id UUID, \n\taction VARCHAR(64) NOT NULL, \n\tobject_id UUID, \n\tdetails JSONB NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(workspace_id) REFERENCES workspaces (id), \n\tFOREIGN KEY(actor_id) REFERENCES users (id)\n)"
    )
    op.execute("CREATE INDEX ix_audit_events_workspace_id ON audit_events (workspace_id)")
    op.execute(
        "CREATE TABLE memberships (\n\tid UUID NOT NULL, \n\tworkspace_id UUID NOT NULL, \n\tuser_id UUID NOT NULL, \n\trole VARCHAR(16) NOT NULL, \n\tstatus VARCHAR(16) NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_membership_user UNIQUE (workspace_id, user_id), \n\tCONSTRAINT uq_membership_scope UNIQUE (workspace_id, id), \n\tCONSTRAINT ck_member_role CHECK (role IN ('owner','admin','researcher','reviewer','viewer')), \n\tCONSTRAINT ck_member_status CHECK (status IN ('active','revoked')), \n\tFOREIGN KEY(workspace_id) REFERENCES workspaces (id), \n\tFOREIGN KEY(user_id) REFERENCES users (id)\n)"
    )
    op.execute("CREATE INDEX ix_memberships_user_id ON memberships (user_id)")
    op.execute("CREATE INDEX ix_memberships_workspace_id ON memberships (workspace_id)")
    op.execute(
        "CREATE TABLE one_time_tokens (\n\tid UUID NOT NULL, \n\tuser_id UUID NOT NULL, \n\ttoken_hash VARCHAR(64) NOT NULL, \n\tpurpose VARCHAR(16) NOT NULL, \n\texpires_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tused_at TIMESTAMP WITH TIME ZONE, \n\tPRIMARY KEY (id), \n\tCONSTRAINT ck_token_purpose CHECK (purpose IN ('verify','reset')), \n\tFOREIGN KEY(user_id) REFERENCES users (id), \n\tUNIQUE (token_hash)\n)"
    )
    op.execute("CREATE INDEX ix_one_time_tokens_user_id ON one_time_tokens (user_id)")
    op.execute(
        "CREATE TABLE refresh_tokens (\n\tid UUID NOT NULL, \n\tuser_id UUID NOT NULL, \n\tfamily_id UUID NOT NULL, \n\ttoken_hash VARCHAR(64) NOT NULL, \n\tcsrf_hash VARCHAR(64) NOT NULL, \n\texpires_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tused_at TIMESTAMP WITH TIME ZONE, \n\trevoked_at TIMESTAMP WITH TIME ZONE, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(user_id) REFERENCES users (id), \n\tUNIQUE (token_hash)\n)"
    )
    op.execute("CREATE INDEX ix_refresh_tokens_user_id ON refresh_tokens (user_id)")
    op.execute("CREATE INDEX ix_refresh_tokens_family_id ON refresh_tokens (family_id)")
    op.execute(
        "CREATE TABLE workspace_invites (\n\tid UUID NOT NULL, \n\tworkspace_id UUID NOT NULL, \n\tinvited_by UUID NOT NULL, \n\temail VARCHAR(254) NOT NULL, \n\trole VARCHAR(16) NOT NULL, \n\ttoken_hash VARCHAR(64) NOT NULL, \n\texpires_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\taccepted_at TIMESTAMP WITH TIME ZONE, \n\trevoked_at TIMESTAMP WITH TIME ZONE, \n\tPRIMARY KEY (id), \n\tCONSTRAINT ck_invite_role CHECK (role IN ('admin','researcher','reviewer','viewer')), \n\tFOREIGN KEY(workspace_id) REFERENCES workspaces (id), \n\tFOREIGN KEY(invited_by) REFERENCES users (id), \n\tUNIQUE (token_hash)\n)"
    )
    op.execute("CREATE INDEX ix_workspace_invites_workspace_id ON workspace_invites (workspace_id)")


def downgrade():
    op.drop_table("audit_events")
    op.drop_table("workspace_invites")
    op.drop_table("memberships")
    op.drop_table("refresh_tokens")
    op.drop_table("one_time_tokens")
    op.drop_table("workspaces")
    op.drop_table("users")
