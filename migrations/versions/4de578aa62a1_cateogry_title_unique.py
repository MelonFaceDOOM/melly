"""cateogry title unique

Revision ID: 4de578aa62a1
Revises: 5f3d7e732a25
Create Date: 2018-12-04 16:05:57.648613

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4de578aa62a1'
down_revision = '5f3d7e732a25'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_index(op.f('ix_category_title'), 'category', ['title'], unique=True)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_category_title'), table_name='category')
    # ### end Alembic commands ###
