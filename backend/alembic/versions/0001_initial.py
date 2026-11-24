"""Initial campaign mapping and audit events.

Revision ID: 0001
Revises:
"""
from alembic import op
import sqlalchemy as sa
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('campaign_records',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('keitaro_campaign_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('geo', sa.String(2), nullable=False),
        sa.Column('offer_stream_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_campaign_records_keitaro_campaign_id', 'campaign_records', ['keitaro_campaign_id'], unique=True)
    op.create_table('audit_events',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('campaign_id', sa.Integer(), nullable=False),
        sa.Column('operation', sa.String(40), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_audit_events_campaign_id', 'audit_events', ['campaign_id'])

def downgrade():
    op.drop_index('ix_audit_events_campaign_id', table_name='audit_events')
    op.drop_table('audit_events')
    op.drop_index('ix_campaign_records_keitaro_campaign_id', table_name='campaign_records')
    op.drop_table('campaign_records')
