"""Enable stateless PDF/XLSX report exports without retaining derivative files."""

from alembic import op

revision = "023_report_formats"
down_revision = "022_account_erasure"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("exports_format_check", "exports", type_="check")
    op.create_check_constraint(
        "exports_format_check", "exports", "format IN ('json','csv','pdf','xlsx')"
    )


def downgrade():
    # Fails safely if newer format rows still exist; never silently deletes reports.
    op.drop_constraint("exports_format_check", "exports", type_="check")
    op.create_check_constraint("exports_format_check", "exports", "format IN ('json','csv')")
