"""empty message

Revision ID: 25eced811a3
Revises: d66f086b258
Create Date: 2014-11-03 23:03:39.497151

"""

# revision identifiers, used by Alembic.
revision = '25eced811a3'
down_revision = 'd66f086b258'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('avatar_hash', sa.String(length=32), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users', 'avatar_hash')
    ### end Alembic commands ###