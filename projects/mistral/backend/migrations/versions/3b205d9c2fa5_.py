"""empty message

Revision ID: 3b205d9c2fa5
Revises: 
Create Date: 2019-10-11 10:26:49.249225

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3b205d9c2fa5'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user', sa.Column('disk_quota', sa.BigInteger(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('user', 'disk_quota')
    # ### end Alembic commands ###
