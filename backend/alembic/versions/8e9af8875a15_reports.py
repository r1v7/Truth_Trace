"""reports

Revision ID: 8e9af8875a15
Revises: 9ec2472b3ae8
Create Date: 2026-09-14 20:16:48.083429
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '8e9af8875a15'
down_revision = '9ec2472b3ae8'
branch_labels = None
depends_on = None


def upgrade() -> None:

    op.create_table('reports',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('case_id', sa.Integer(), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('summary', sa.Text(), nullable=True),
    sa.Column('status', sa.Enum('draft', 'submitted', 'approved', 'returned', name='report_status'), nullable=False),
    sa.Column('snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('content_sha256', sa.String(length=64), nullable=True),
    sa.Column('prepared_by_id', sa.Integer(), nullable=False),
    sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('decided_by_id', sa.Integer(), nullable=True),
    sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('decision_note', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['decided_by_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['prepared_by_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('case_id', 'version', name='uq_report_case_version')
    )
    op.create_index(op.f('ix_reports_case_id'), 'reports', ['case_id'], unique=False)
    op.create_table('report_items',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('report_id', sa.Integer(), nullable=False),
    sa.Column('finding_id', sa.Integer(), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('note', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['finding_id'], ['findings.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['report_id'], ['reports.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('report_id', 'finding_id', name='uq_report_item')
    )
    op.create_index(op.f('ix_report_items_report_id'), 'report_items', ['report_id'], unique=False)



def downgrade() -> None:

    op.drop_index(op.f('ix_report_items_report_id'), table_name='report_items')
    op.drop_table('report_items')
    op.drop_index(op.f('ix_reports_case_id'), table_name='reports')
    op.drop_table('reports')
    sa.Enum(name='report_status').drop(op.get_bind(), checkfirst=True)

