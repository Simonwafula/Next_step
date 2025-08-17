"""Add user authentication and profile models

Revision ID: 001_add_user_auth
Revises: 
Create Date: 2025-08-17 23:24:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_add_user_auth'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('uuid', sa.String(length=36), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('whatsapp_number', sa.String(length=20), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False, default=False),
        sa.Column('subscription_tier', sa.String(length=50), nullable=False, default='basic'),
        sa.Column('subscription_expires', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_users_uuid', 'users', ['uuid'], unique=True)
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # Create user_profiles table
    op.create_table('user_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('current_role', sa.String(length=255), nullable=True),
        sa.Column('experience_level', sa.String(length=50), nullable=True),
        sa.Column('education', sa.Text(), nullable=True),
        sa.Column('skills', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column('career_goals', sa.Text(), nullable=True),
        sa.Column('preferred_locations', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default=[]),
        sa.Column('salary_expectations', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column('job_alert_preferences', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column('notification_preferences', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column('privacy_settings', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column('profile_completeness', sa.Float(), nullable=False, default=0.0),
        sa.Column('cv_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column('linkedin_url', sa.String(length=500), nullable=True),
        sa.Column('portfolio_url', sa.String(length=500), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_user_profiles_user_id', 'user_profiles', ['user_id'], unique=True)

    # Create saved_jobs table
    op.create_table('saved_jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('job_post_id', sa.Integer(), nullable=False),
        sa.Column('saved_at', sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('folder', sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(['job_post_id'], ['job_post.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_user_job_saved', 'saved_jobs', ['user_id', 'job_post_id'], unique=True)

    # Create job_applications table
    op.create_table('job_applications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('job_post_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, default='applied'),
        sa.Column('applied_at', sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.Column('last_updated', sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.Column('cover_letter', sa.Text(), nullable=True),
        sa.Column('cv_version', sa.String(length=100), nullable=True),
        sa.Column('application_source', sa.String(length=100), nullable=True),
        sa.Column('referrer_info', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column('interview_dates', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default=[]),
        sa.Column('feedback_received', sa.Text(), nullable=True),
        sa.Column('salary_offered', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['job_post_id'], ['job_post.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_user_job_application', 'job_applications', ['user_id', 'job_post_id'], unique=True)

    # Create search_history table
    op.create_table('search_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('query', sa.String(length=500), nullable=False),
        sa.Column('filters', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column('results_count', sa.Integer(), nullable=False, default=0),
        sa.Column('clicked_jobs', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default=[]),
        sa.Column('searched_at', sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_search_history_searched_at', 'search_history', ['searched_at'])

    # Create user_notifications table
    op.create_table('user_notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column('is_read', sa.Boolean(), nullable=False, default=False),
        sa.Column('delivered_via', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default=[]),
        sa.Column('delivery_status', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.Column('read_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_user_notifications_created_at', 'user_notifications', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_user_notifications_created_at', table_name='user_notifications')
    op.drop_table('user_notifications')
    op.drop_index('ix_search_history_searched_at', table_name='search_history')
    op.drop_table('search_history')
    op.drop_index('idx_user_job_application', table_name='job_applications')
    op.drop_table('job_applications')
    op.drop_index('idx_user_job_saved', table_name='saved_jobs')
    op.drop_table('saved_jobs')
    op.drop_index('ix_user_profiles_user_id', table_name='user_profiles')
    op.drop_table('user_profiles')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_index('ix_users_uuid', table_name='users')
    op.drop_table('users')
