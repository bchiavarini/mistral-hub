"""empty message

Revision ID: b940ea1abf8c
Revises: 
Create Date: 2019-10-11 10:22:30.918903

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b940ea1abf8c'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('user', 'abc')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user', sa.Column('abc', sa.VARCHAR(length=80), autoincrement=False, nullable=True))
    # ### end Alembic commands ###
