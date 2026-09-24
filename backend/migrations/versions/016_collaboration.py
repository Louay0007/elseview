"""P16 collaboration; self-contained immutable DDL."""

from alembic import op

revision = "016_collaboration"
down_revision = "015_billing"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "\nCREATE TABLE api_keys (\n\tuser_id UUID NOT NULL, \n\ttoken_hash VARCHAR(64) NOT NULL, \n\tscopes JSONB NOT NULL, \n\texpires_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\trevoked_at TIMESTAMP WITH TIME ZONE, \n\tid UUID NOT NULL, \n\tworkspace_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(user_id) REFERENCES users (id), \n\tUNIQUE (token_hash), \n\tFOREIGN KEY(workspace_id) REFERENCES workspaces (id)\n)\n\n"
    )
    op.execute("CREATE INDEX ix_api_keys_workspace_id ON api_keys (workspace_id)")
    op.execute(
        "\nCREATE TABLE report_comments (\n\treport_id UUID NOT NULL, \n\tauthor_id UUID NOT NULL, \n\ttext TEXT NOT NULL, \n\trestricted BOOLEAN NOT NULL, \n\tid UUID NOT NULL, \n\tworkspace_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(workspace_id, report_id) REFERENCES reports (workspace_id, id) ON DELETE CASCADE, \n\tFOREIGN KEY(author_id) REFERENCES users (id), \n\tFOREIGN KEY(workspace_id) REFERENCES workspaces (id)\n)\n\n"
    )
    op.execute("CREATE INDEX ix_report_comments_workspace_id ON report_comments (workspace_id)")
    op.execute(
        "\nCREATE TABLE report_grants (\n\treport_id UUID NOT NULL, \n\tissuer_id UUID NOT NULL, \n\trecipient_id UUID NOT NULL, \n\trevision INTEGER NOT NULL, \n\trevoked BOOLEAN NOT NULL, \n\tid UUID NOT NULL, \n\tworkspace_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(workspace_id, report_id) REFERENCES reports (workspace_id, id) ON DELETE CASCADE, \n\tUNIQUE (report_id, recipient_id), \n\tFOREIGN KEY(issuer_id) REFERENCES users (id), \n\tFOREIGN KEY(recipient_id) REFERENCES users (id), \n\tFOREIGN KEY(workspace_id) REFERENCES workspaces (id)\n)\n\n"
    )
    op.execute("CREATE INDEX ix_report_grants_workspace_id ON report_grants (workspace_id)")
    op.execute(
        "\nCREATE TABLE template_grants (\n\tinstance_id UUID NOT NULL, \n\tissuer_id UUID NOT NULL, \n\trecipient_id UUID NOT NULL, \n\trevoked BOOLEAN NOT NULL, \n\tid UUID NOT NULL, \n\tworkspace_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(workspace_id, instance_id) REFERENCES template_instances (workspace_id, id) ON DELETE CASCADE, \n\tUNIQUE (instance_id, recipient_id), \n\tFOREIGN KEY(issuer_id) REFERENCES users (id), \n\tFOREIGN KEY(recipient_id) REFERENCES users (id), \n\tFOREIGN KEY(workspace_id) REFERENCES workspaces (id)\n)\n\n"
    )
    op.execute("CREATE INDEX ix_template_grants_workspace_id ON template_grants (workspace_id)")
    op.execute(
        "\nCREATE TABLE notification_preferences (\n\tuser_id UUID NOT NULL, \n\treminders BOOLEAN NOT NULL, \n\tid UUID NOT NULL, \n\tworkspace_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (workspace_id, user_id), \n\tFOREIGN KEY(user_id) REFERENCES users (id), \n\tFOREIGN KEY(workspace_id) REFERENCES workspaces (id)\n)\n\n"
    )
    op.execute(
        "CREATE INDEX ix_notification_preferences_workspace_id ON notification_preferences (workspace_id)"
    )
    op.execute(
        "\nCREATE TABLE integrations (\n\tcreator_id UUID NOT NULL, \n\tdestination TEXT NOT NULL, \n\tenabled BOOLEAN NOT NULL, \n\trevision INTEGER NOT NULL, \n\tid UUID NOT NULL, \n\tworkspace_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (workspace_id, id), \n\tFOREIGN KEY(creator_id) REFERENCES users (id), \n\tFOREIGN KEY(workspace_id) REFERENCES workspaces (id)\n)\n\n"
    )
    op.execute("CREATE INDEX ix_integrations_workspace_id ON integrations (workspace_id)")
    op.execute(
        "\nCREATE TABLE webhook_deliveries (\n\tintegration_id UUID NOT NULL, \n\tintegration_revision INTEGER NOT NULL, \n\trequester_id UUID NOT NULL, \n\tcommand_key UUID NOT NULL, \n\tstate VARCHAR(16) NOT NULL, \n\tid UUID NOT NULL, \n\tworkspace_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(workspace_id, integration_id) REFERENCES integrations (workspace_id, id), \n\tUNIQUE (integration_id, command_key), \n\tCHECK (state IN ('pending','succeeded','failed','cancelled')), \n\tFOREIGN KEY(requester_id) REFERENCES users (id), \n\tFOREIGN KEY(workspace_id) REFERENCES workspaces (id)\n)\n\n"
    )
    op.execute(
        "CREATE INDEX ix_webhook_deliveries_workspace_id ON webhook_deliveries (workspace_id)"
    )


def downgrade():
    op.execute("DROP TABLE webhook_deliveries")
    op.execute("DROP TABLE integrations")
    op.execute("DROP TABLE notification_preferences")
    op.execute("DROP TABLE template_grants")
    op.execute("DROP TABLE report_grants")
    op.execute("DROP TABLE report_comments")
    op.execute("DROP TABLE api_keys")
