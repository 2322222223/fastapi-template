"""add_points_source_type_enum_values

Revision ID: fd159a5e02ad
Revises: 7b62b73f82c6
Create Date: 2025-11-05 08:52:29.747806

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'fd159a5e02ad'
down_revision = '7b62b73f82c6'
branch_labels = None
depends_on = None


def upgrade():
    # 添加缺失的枚举值到 pointssourcetype
    # 注意：PostgreSQL 枚举存储的是枚举名称（大写），而不是枚举值
    op.execute("ALTER TYPE pointssourcetype ADD VALUE IF NOT EXISTS 'INVITATION'")
    op.execute("ALTER TYPE pointssourcetype ADD VALUE IF NOT EXISTS 'NEW_USER_BONUS'")
    op.execute("ALTER TYPE pointssourcetype ADD VALUE IF NOT EXISTS 'POINTS_PRODUCT_EXCHANGE'")
    op.execute("ALTER TYPE pointssourcetype ADD VALUE IF NOT EXISTS 'POINTS_PRODUCT_REFUND'")


def downgrade():
    # PostgreSQL 不支持删除枚举值，只能删除整个类型
    # 这里不做降级处理，因为删除枚举值可能导致数据不一致
    pass
