"""轻量版靶点分析平台基线表结构

Revision ID: 0001_baseline
Revises:
Create Date: 2026-09-16

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '0001_baseline'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.Text(), nullable=False),
        sa.Column('role', sa.Enum('user', 'admin', name='userrole', native_enum=False, create_constraint=True, length=32), nullable=False),
        sa.Column('status', sa.Enum('active', 'disabled', name='userstatus', native_enum=False, create_constraint=True, length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    op.create_table(
        'projects',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('primary_disease', sa.String(length=255), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_projects_user_id'), 'projects', ['user_id'], unique=False)

    op.create_table(
        'user_llm_credentials',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('provider', sa.Enum('deepseek', name='llmprovider', native_enum=False, create_constraint=True, length=32), nullable=False),
        sa.Column('api_key_ciphertext', sa.LargeBinary(), nullable=False),
        sa.Column('nonce', sa.LargeBinary(), nullable=False),
        sa.Column('key_version', sa.Integer(), nullable=False),
        sa.Column('key_last4', sa.String(length=8), nullable=False),
        sa.Column('is_validated', sa.Boolean(), nullable=False),
        sa.Column('validated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'provider'),
    )

    op.create_table(
        'analysis_runs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('project_id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('status', sa.Enum('queued', 'running', 'completed', 'failed', name='runstatus', native_enum=False, create_constraint=True, length=32), nullable=False),
        sa.Column('current_step', sa.String(length=64), nullable=True),
        sa.Column('model_name', sa.String(length=64), nullable=True),
        sa.Column('prompt_version', sa.String(length=64), nullable=True),
        sa.Column('workflow_version', sa.String(length=64), nullable=True),
        sa.Column('credential_id', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_code', sa.String(length=64), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('results_json', sa.JSON(), nullable=True),
        sa.Column('intermediate_json', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['credential_id'], ['user_llm_credentials.id']),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_analysis_runs_project_id'), 'analysis_runs', ['project_id'], unique=False)
    op.create_index(op.f('ix_analysis_runs_user_id'), 'analysis_runs', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_analysis_runs_user_id'), table_name='analysis_runs')
    op.drop_index(op.f('ix_analysis_runs_project_id'), table_name='analysis_runs')
    op.drop_table('analysis_runs')
    op.drop_table('user_llm_credentials')
    op.drop_index(op.f('ix_projects_user_id'), table_name='projects')
    op.drop_table('projects')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
