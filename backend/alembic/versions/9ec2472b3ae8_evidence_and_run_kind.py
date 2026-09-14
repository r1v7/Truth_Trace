"""evidence and run kind

Revision ID: 9ec2472b3ae8
Revises: 724cd03f1867
Create Date: 2026-09-14 20:07:45.613238
"""
from alembic import op
import sqlalchemy as sa


revision = '9ec2472b3ae8'
down_revision = '724cd03f1867'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('evidence',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('case_id', sa.Integer(), nullable=False),
    sa.Column('kind', sa.Enum('call_log', 'message_log', 'transcript', 'document', 'other', name='evidence_kind'), nullable=False),
    sa.Column('original_filename', sa.String(length=255), nullable=False),
    sa.Column('content_type', sa.String(length=128), nullable=False),
    sa.Column('size_bytes', sa.BigInteger(), nullable=False),
    sa.Column('sha256', sa.String(length=64), nullable=False),
    sa.Column('storage_path', sa.String(length=512), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('uploaded_by_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['uploaded_by_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_evidence_case_id'), 'evidence', ['case_id'], unique=False)
    op.create_index(op.f('ix_evidence_sha256'), 'evidence', ['sha256'], unique=False)
    # add_column does not create the enum type the way create_table does, so it is
    # created explicitly first.
    run_kind = sa.Enum('interview_pair', 'evidence', name='run_kind')
    run_kind.create(op.get_bind(), checkfirst=True)
    # Existing rows are all interview-pair runs, so they need a default to become
    # NOT NULL; the default is then dropped so new rows must state their kind.
    op.add_column(
        'analysis_runs',
        sa.Column('kind', run_kind, nullable=False, server_default='interview_pair'),
    )
    op.alter_column('analysis_runs', 'kind', server_default=None)
    op.add_column('analysis_runs', sa.Column('evidence_id', sa.Integer(), nullable=True))
    op.alter_column('analysis_runs', 'interview_b_id',
               existing_type=sa.INTEGER(),
               nullable=True)
    # Named so that downgrade can actually drop it.
    op.create_foreign_key(
        'fk_analysis_runs_evidence_id', 'analysis_runs', 'evidence',
        ['evidence_id'], ['id'], ondelete='CASCADE',
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    op.drop_constraint('fk_analysis_runs_evidence_id', 'analysis_runs', type_='foreignkey')
    op.alter_column('analysis_runs', 'interview_b_id',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.drop_column('analysis_runs', 'evidence_id')
    op.drop_column('analysis_runs', 'kind')
    op.drop_index(op.f('ix_evidence_sha256'), table_name='evidence')
    op.drop_index(op.f('ix_evidence_case_id'), table_name='evidence')
    op.drop_table('evidence')
    sa.Enum(name='run_kind').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='evidence_kind').drop(op.get_bind(), checkfirst=True)
