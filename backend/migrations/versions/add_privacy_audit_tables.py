"""Add privacy and audit tables

Revision ID: privacy_audit_001
Revises: d4f9fc78b126
Create Date: 2024-12-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'privacy_audit_001'
down_revision = 'd4f9fc78b126'
branch_labels = None
depends_on = None


def upgrade():
    # Create audit_logs table
    op.create_table('audit_logs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('resource_type', sa.String(), nullable=False),
        sa.Column('resource_id', sa.String(), nullable=True),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('request_method', sa.String(), nullable=True),
        sa.Column('request_path', sa.String(), nullable=True),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('action_metadata', sa.JSON(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False, default=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('sensitivity_level', sa.String(), nullable=False, default='normal'),
        sa.Column('timestamp', sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for audit_logs
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_timestamp', 'audit_logs', ['timestamp'])
    op.create_index('ix_audit_logs_sensitivity', 'audit_logs', ['sensitivity_level'])
    op.create_index('ix_audit_logs_success', 'audit_logs', ['success'])
    
    # Create data_deletion_requests table
    op.create_table('data_deletion_requests',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('deletion_type', sa.String(), nullable=False),
        sa.Column('reason', sa.String(), nullable=False),
        sa.Column('requested_by', sa.String(), nullable=False),
        sa.Column('requested_at', sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.Column('scheduled_for', sa.DateTime(), nullable=False),
        sa.Column('retention_period_days', sa.Integer(), nullable=False, default=30),
        sa.Column('status', sa.String(), nullable=False, default='scheduled'),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('export_requested', sa.Boolean(), default=False),
        sa.Column('export_completed', sa.Boolean(), default=False),
        sa.Column('export_download_url', sa.String(), nullable=True),
        sa.Column('export_expires_at', sa.DateTime(), nullable=True),
        sa.Column('verification_token', sa.String(), nullable=True),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
        sa.Column('request_metadata', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for data_deletion_requests
    op.create_index('ix_deletion_requests_user_id', 'data_deletion_requests', ['user_id'])
    op.create_index('ix_deletion_requests_status', 'data_deletion_requests', ['status'])
    op.create_index('ix_deletion_requests_scheduled_for', 'data_deletion_requests', ['scheduled_for'])
    op.create_index('ix_deletion_requests_deletion_type', 'data_deletion_requests', ['deletion_type'])


def downgrade():
    # Drop indexes first
    op.drop_index('ix_deletion_requests_deletion_type', table_name='data_deletion_requests')
    op.drop_index('ix_deletion_requests_scheduled_for', table_name='data_deletion_requests')
    op.drop_index('ix_deletion_requests_status', table_name='data_deletion_requests')
    op.drop_index('ix_deletion_requests_user_id', table_name='data_deletion_requests')
    
    op.drop_index('ix_audit_logs_success', table_name='audit_logs')
    op.drop_index('ix_audit_logs_sensitivity', table_name='audit_logs')
    op.drop_index('ix_audit_logs_timestamp', table_name='audit_logs')
    op.drop_index('ix_audit_logs_action', table_name='audit_logs')
    op.drop_index('ix_audit_logs_user_id', table_name='audit_logs')
    
    # Drop tables
    op.drop_table('data_deletion_requests')
    op.drop_table('audit_logs')