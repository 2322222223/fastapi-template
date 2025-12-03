"""Add region, business_district and store tables

Revision ID: f4d8b9e2a1c0
Revises: 1a31ce608336
Create Date: 2025-08-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f4d8b9e2a1c0'
down_revision = '1a31ce608336'
branch_labels = None
depends_on = None


def upgrade():
    # Create region table
    op.create_table('region',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('code', sa.String(length=20), nullable=False),
    sa.Column('country', sa.String(length=50), nullable=False),
    sa.Column('province', sa.String(length=50), nullable=True),
    sa.Column('city', sa.String(length=50), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('code')
    )
    
    # Create businessdistrict table
    op.create_table('businessdistrict',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('image_url', sa.String(length=500), nullable=False),
    sa.Column('rating', sa.Float(), nullable=False),
    sa.Column('free_duration', sa.Integer(), nullable=False),
    sa.Column('ranking', sa.Integer(), nullable=False),
    sa.Column('address', sa.String(length=255), nullable=False),
    sa.Column('distance', sa.String(length=50), nullable=False),
    sa.Column('region_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.ForeignKeyConstraint(['region_id'], ['region.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    
    # Create store table
    op.create_table('store',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('category', sa.String(length=50), nullable=False),
    sa.Column('rating', sa.Float(), nullable=False),
    sa.Column('review_count', sa.Integer(), nullable=False),
    sa.Column('price_range', sa.String(length=20), nullable=False),
    sa.Column('location', sa.String(length=255), nullable=False),
    sa.Column('floor', sa.String(length=10), nullable=False),
    sa.Column('image_url', sa.String(length=500), nullable=False),
    sa.Column('tags', sa.String(length=500), nullable=False),
    sa.Column('is_live', sa.Boolean(), nullable=False),
    sa.Column('has_delivery', sa.Boolean(), nullable=False),
    sa.Column('distance', sa.String(length=50), nullable=False),
    sa.Column('title', sa.String(length=100), nullable=False),
    sa.Column('sub_title', sa.String(length=200), nullable=True),
    sa.Column('sub_icon', sa.String(length=100), nullable=True),
    sa.Column('type', sa.Integer(), nullable=False),
    sa.Column('business_district_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.ForeignKeyConstraint(['business_district_id'], ['businessdistrict.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('store')
    op.drop_table('businessdistrict')
    op.drop_table('region')