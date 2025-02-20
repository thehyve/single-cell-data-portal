"""collection_publisher_metadata

Revision ID: 43e20ba9f9f0
Revises: 24_32f819760df4
Create Date: 2022-01-12 12:16:52.410975

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "25_43e20ba9f9f0"
down_revision = "24_32f819760df4"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("project", sa.Column("publisher_metadata", postgresql.JSON(astext_type=sa.Text()), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("project", "publisher_metadata")
    # ### end Alembic commands ###
