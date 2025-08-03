"""
Add cart_uid to OrderItem

Revision ID: 20250703_add_cart_uid_orderitem
Revises: 4d680eae5a88_initial_migration
Create Date: 2025-07-03 23:21:36
"""

from alembic import op
import sqlalchemy as sa
import uuid

# revision identifiers, used by Alembic.
revision = '20250703_add_cart_uid_orderitem'
down_revision = '4d680eae5a88'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('order_item', sa.Column('cart_uid', sa.String(length=36), nullable=True))
    # Backfill existing rows with unique UUIDs
    conn = op.get_bind()
    order_items = conn.execute(sa.text('SELECT id FROM order_item WHERE cart_uid IS NULL OR cart_uid = ""')).fetchall()
    for row in order_items:
        conn.execute(sa.text('UPDATE order_item SET cart_uid = :uid WHERE id = :id'), {'uid': str(uuid.uuid4()), 'id': row[0]})
    # NOTE: SQLite does not support altering columns to NOT NULL after creation. Enforce NOT NULL at the SQLAlchemy model/application level.

def downgrade():
    op.drop_column('order_item', 'cart_uid')
