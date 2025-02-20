"""add_processing_timestamps

Revision ID: 09_7794b1ea430f
Revises: 08_387b9dc01c4b
Create Date: 2020-11-17 04:39:00.759295

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "09_7794b1ea430f"
down_revision = "08_387b9dc01c4b"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "dataset_processing_status",
        sa.Column(
            "created_at", postgresql.TIMESTAMP, server_default=sa.text("now()"), autoincrement=False, nullable=False
        ),
    )
    op.add_column(
        "dataset_processing_status",
        sa.Column(
            "updated_at", postgresql.TIMESTAMP, server_default=sa.text("now()"), autoincrement=False, nullable=False
        ),
    )


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("dataset_processing_status", "updated_at")
    op.drop_column("dataset_processing_status", "created_at")
