"""Add assessment_question, assessment_session, assessment_session_answer (T-DS-941/942/943).

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-03-23
"""

from alembic import op
import sqlalchemy as sa

try:
    from sqlalchemy.dialects.postgresql import JSONB
except ImportError:
    JSONB = sa.JSON  # type: ignore[misc,assignment]

revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- assessment_question (T-DS-941) ---
    op.create_table(
        "assessment_question",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("skill_name", sa.String(120), nullable=False),
        sa.Column("role_family", sa.String(120), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("options", JSONB(), nullable=False, server_default="[]"),
        sa.Column("correct_index", sa.Integer(), nullable=False),
        sa.Column("difficulty", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "question_bank_version",
            sa.String(30),
            nullable=False,
            server_default="v1",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_assessment_question_skill_name", "assessment_question", ["skill_name"]
    )
    op.create_index(
        "ix_assessment_question_role_family", "assessment_question", ["role_family"]
    )
    op.create_index(
        "ix_assessment_question_version",
        "assessment_question",
        ["question_bank_version"],
    )
    op.create_index(
        "idx_aq_role_skill", "assessment_question", ["role_family", "skill_name"]
    )
    op.create_index(
        "idx_aq_role_version",
        "assessment_question",
        ["role_family", "question_bank_version"],
    )

    # --- assessment_session (T-DS-942/943) ---
    op.create_table(
        "assessment_session",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("role_family", sa.String(120), nullable=False),
        sa.Column(
            "status", sa.String(20), nullable=False, server_default="in_progress"
        ),
        sa.Column("question_ids", JSONB(), nullable=False, server_default="[]"),
        sa.Column(
            "question_bank_version",
            sa.String(30),
            nullable=False,
            server_default="v1",
        ),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("questions_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "questions_correct", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("percentile", sa.Float(), nullable=True),
        sa.Column("level", sa.String(30), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_assessment_session_user_id", "assessment_session", ["user_id"])
    op.create_index(
        "ix_assessment_session_role_family", "assessment_session", ["role_family"]
    )
    op.create_index(
        "ix_assessment_session_status", "assessment_session", ["status"]
    )
    op.create_index(
        "idx_as_user_role", "assessment_session", ["user_id", "role_family"]
    )

    # --- assessment_session_answer (T-DS-942) ---
    op.create_table(
        "assessment_session_answer",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "session_id",
            sa.Integer(),
            sa.ForeignKey("assessment_session.id"),
            nullable=False,
        ),
        sa.Column(
            "question_id",
            sa.Integer(),
            sa.ForeignKey("assessment_question.id"),
            nullable=False,
        ),
        sa.Column("selected_index", sa.Integer(), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.Column(
            "answered_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_asa_session_id", "assessment_session_answer", ["session_id"]
    )
    op.create_index(
        "ix_asa_question_id", "assessment_session_answer", ["question_id"]
    )


def downgrade() -> None:
    op.drop_table("assessment_session_answer")
    op.drop_table("assessment_session")
    op.drop_table("assessment_question")
