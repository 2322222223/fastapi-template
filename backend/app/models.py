import uuid
from datetime import datetime
from typing import Optional, Union, Dict, Any, List
from enum import Enum

from pydantic import EmailStr
from sqlmodel import Field, Relationship, SQLModel
from sqlalchemy import Column, Enum as SQLEnum


# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=20, description="手机号")
    is_active: bool = True
    is_superuser: bool = False
    full_name: Optional[str] = Field(default=None, max_length=255)
    avatar_url: Optional[str] = Field(default=None, max_length=500, description="用户头像URL")


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=40)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=40)
    full_name: Optional[str] = Field(default=None, max_length=255)


# Properties to receive via API on update, all are optional
class UserUpdate(UserBase):
    email: Optional[EmailStr] = Field(default=None, max_length=255)  # type: ignore
    phone: Optional[str] = Field(default=None, max_length=20, description="手机号")  # type: ignore
    password: Optional[str] = Field(default=None, min_length=8, max_length=40)
    avatar_url: Optional[str] = Field(default=None, max_length=500, description="用户头像URL")  # type: ignore


class UserUpdateMe(SQLModel):
    full_name: Optional[str] = Field(default=None, max_length=255)
    email: Optional[EmailStr] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=20, description="手机号")
    avatar_url: Optional[str] = Field(default=None, max_length=500, description="用户头像URL")


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=40)
    new_password: str = Field(min_length=8, max_length=40)


# Database model, database table inferred from class name
class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    points_balance: int = Field(default=0, description="用户积分余额")
    points_redeemed: int = Field(default=0, description="累计兑换消耗积分")
    invite_code: str = Field(unique=True, index=True, max_length=16, description="用户邀请码")
    items: list["Item"] = Relationship(back_populates="owner", cascade_delete=True)
    data_packages: list["DataPackage"] = Relationship(back_populates="user", cascade_delete=True)
    membership_benefits: list["MembershipBenefit"] = Relationship(back_populates="user", cascade_delete=True)
    user_coupons: list["UserCoupon"] = Relationship(back_populates="user", cascade_delete=True)
    cart_items: list["CartItem"] = Relationship(back_populates="user", cascade_delete=True)
    orders: list["Order"] = Relationship(back_populates="user", cascade_delete=True)
    points_transactions: list["PointsTransaction"] = Relationship(back_populates="user", cascade_delete=True)
    check_in_histories: list["CheckInHistory"] = Relationship(back_populates="user", cascade_delete=True)
    user_tasks: list["UserTask"] = Relationship(back_populates="user", cascade_delete=True)
    # 邀请关系
    invitations_sent: list["Invitation"] = Relationship(back_populates="inviter", sa_relationship_kwargs={"foreign_keys": "Invitation.inviter_id"}, cascade_delete=True)
    invitations_received: list["Invitation"] = Relationship(back_populates="invitee", sa_relationship_kwargs={"foreign_keys": "Invitation.invitee_id"}, cascade_delete=True)
    # 发现页面关系
    articles: list["Article"] = Relationship(back_populates="author", cascade_delete=True)
    community_tasks: list["CommunityTask"] = Relationship(back_populates="publisher", cascade_delete=True)
    task_applications: list["TaskApplication"] = Relationship(back_populates="applicant", cascade_delete=True)
    comments: list["Comment"] = Relationship(back_populates="author", cascade_delete=True)
    likes: list["Like"] = Relationship(back_populates="user", cascade_delete=True)
    # 服务号关系
    service_accounts: list["ServiceAccount"] = Relationship(back_populates="user", cascade_delete=True)
    # 地址关系
    addresses: list["Address"] = Relationship(back_populates="user", cascade_delete=True)
    # 积分商城关系
    points_product_exchanges: list["PointsProductExchange"] = Relationship(back_populates="user", cascade_delete=True)


# Properties to return via API, id is always required
class UserPublic(UserBase):
    id: uuid.UUID


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


# Shared properties
class ItemBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=255)


# Properties to receive on item creation
class ItemCreate(ItemBase):
    pass


# Properties to receive on item update
class ItemUpdate(ItemBase):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)  # type: ignore


# Database model, database table inferred from class name
class Item(ItemBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    owner: Optional[User] = Relationship(back_populates="items")


# Properties to return via API, id is always required
class ItemPublic(ItemBase):
    id: uuid.UUID
    owner_id: uuid.UUID


class ItemsPublic(SQLModel):
    data: list[ItemPublic]
    count: int


# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: Optional[str] = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=40)


# Region models
class RegionBase(SQLModel):
    name: str = Field(max_length=100)
    code: str = Field(max_length=20, unique=True)
    country: str = Field(max_length=50, default="中国")
    province: Optional[str] = Field(default=None, max_length=50)
    city: Optional[str] = Field(default=None, max_length=50)


class RegionCreate(RegionBase):
    pass


class RegionUpdate(SQLModel):
    name: Optional[str] = Field(default=None, max_length=100)
    province: Optional[str] = Field(default=None, max_length=50)
    city: Optional[str] = Field(default=None, max_length=50)


class Region(RegionBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    business_districts: list["BusinessDistrict"] = Relationship(back_populates="region")


class RegionPublic(RegionBase):
    id: uuid.UUID


# Business District models
class BusinessDistrictBase(SQLModel):
    name: str = Field(max_length=100)
    image_url: str = Field(max_length=500)
    rating: float = Field(ge=0, le=5)
    free_duration: int = Field(ge=0)  # 免费停车时长（分钟）
    ranking: int = Field(ge=1)  # 排名
    address: str = Field(max_length=255)
    distance: str = Field(max_length=50)  # 距离描述，如"1.2km"


class BusinessDistrictCreate(BusinessDistrictBase):
    region_id: uuid.UUID


class BusinessDistrictUpdate(SQLModel):
    name: Optional[str] = Field(default=None, max_length=100)
    image_url: Optional[str] = Field(default=None, max_length=500)
    rating: Optional[float] = Field(default=None, ge=0, le=5)
    free_duration: Optional[int] = Field(default=None, ge=0)
    ranking: Optional[int] = Field(default=None, ge=1)
    address: Optional[str] = Field(default=None, max_length=255)
    distance: Optional[str] = Field(default=None, max_length=50)
    region_id: Optional[uuid.UUID] = None


class BusinessDistrict(BusinessDistrictBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    region_id: uuid.UUID = Field(foreign_key="region.id", nullable=False)
    region: Optional[Region] = Relationship(back_populates="business_districts")
    stores: list["Store"] = Relationship(back_populates="business_district")


class BusinessDistrictPublic(BusinessDistrictBase):
    id: uuid.UUID
    region_id: uuid.UUID


# Store models
class StoreBase(SQLModel):
    name: str = Field(max_length=100)
    category: str = Field(max_length=50)
    rating: float = Field(ge=0, le=5)
    review_count: int = Field(ge=0)
    price_range: str = Field(max_length=20)  # 如 "￥￥￥"
    location: str = Field(max_length=255)
    floor: str = Field(max_length=10)  # 如 "B1", "1F", "2F"
    image_url: str = Field(max_length=500)
    tags: str = Field(max_length=500)  # JSON字符串存储标签数组
    is_live: bool = Field(default=True)  # 营业状态
    has_delivery: bool = Field(default=False)  # 是否有配送
    distance: str = Field(max_length=50)
    title: str = Field(max_length=100)
    sub_title: Optional[str] = Field(default=None, max_length=200)
    sub_icon: Optional[str] = Field(default=None, max_length=100)
    type: int = Field(ge=0)  # 商店类型分类


class StoreCreate(StoreBase):
    business_district_id: uuid.UUID


class StoreUpdate(SQLModel):
    name: Optional[str] = Field(default=None, max_length=100)
    category: Optional[str] = Field(default=None, max_length=50)
    rating: Optional[float] = Field(default=None, ge=0, le=5)
    review_count: Optional[int] = Field(default=None, ge=0)
    price_range: Optional[str] = Field(default=None, max_length=20)
    location: Optional[str] = Field(default=None, max_length=255)
    floor: Optional[str] = Field(default=None, max_length=10)
    image_url: Optional[str] = Field(default=None, max_length=500)
    tags: Optional[str] = Field(default=None, max_length=500)
    is_live: Optional[bool] = None
    has_delivery: Optional[bool] = None
    distance: Optional[str] = Field(default=None, max_length=50)
    title: Optional[str] = Field(default=None, max_length=100)
    sub_title: Optional[str] = Field(default=None, max_length=200)
    sub_icon: Optional[str] = Field(default=None, max_length=100)
    type: Optional[int] = Field(default=None, ge=0)
    business_district_id: Optional[uuid.UUID] = None


class Store(StoreBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    business_district_id: uuid.UUID = Field(foreign_key="businessdistrict.id", nullable=False)
    business_district: Optional[BusinessDistrict] = Relationship(back_populates="stores")
    products: list["Product"] = Relationship(back_populates="store", cascade_delete=True)


class StorePublic(StoreBase):
    id: uuid.UUID
    business_district_id: uuid.UUID


# List response models
class RegionsPublic(SQLModel):
    data: list[RegionPublic]
    count: int


class BusinessDistrictsPublic(SQLModel):
    data: list[BusinessDistrictPublic]
    count: int


class StoresPublic(SQLModel):
    data: list[StorePublic]
    count: int
    is_more: bool


# Phone login models
class PhoneLoginRequest(SQLModel):
    phone: str = Field(max_length=20, description="手机号")
    verification_code: str = Field(max_length=10, description="验证码")


class PhoneRegisterRequest(SQLModel):
    phone: str = Field(max_length=20, description="手机号")
    verification_code: str = Field(max_length=10, description="验证码")
    full_name: Optional[str] = Field(default=None, max_length=255, description="姓名")


class SendVerificationCodeRequest(SQLModel):
    phone: str = Field(max_length=20, description="手机号")
    

# HotSearch models
class HotSearchBase(SQLModel):
    keyword: str = Field(max_length=100,description="热搜关键词")
    icon: str = Field(max_length=100,description="热搜图标")
    
class HotSearchCreate(HotSearchBase):
    pass


class HotSearchUpdate(SQLModel):
    keyword: Optional[str] = Field(default=None, max_length=100)
    icon: Optional[str] = Field(default=None, max_length=100)


class HotSearch(HotSearchBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)


class HotSearchPublic(HotSearchBase):
    id: uuid.UUID
    
    
class HotSearchesPublic(SQLModel):
    data: list[HotSearchPublic]
    count: int
    
    
# Product models
class ProductBase(SQLModel):
    title: str = Field(max_length=255, description="商品主标题")
    subtitle: str = Field(max_length=500, description="商品副标题或简短描述")
    price: float = Field(gt=0, description="商品当前实际售价")
    original_price: float = Field(gt=0, description="商品原价，用于划线价展示")
    discount: str = Field(max_length=100, description="折扣信息，如'8折'或'-¥20'")
    image_url: str = Field(max_length=500, description="商品图片URL地址")
    tag: str = Field(max_length=100, description="商品标签，如'新品'、'热销'")
    sales_count: str = Field(max_length=100, description="销量描述，如'已售1万+'")
    category: str = Field(max_length=100, description="商品所属分类")
    member_price: Optional[float] = Field(default=None, gt=0, description="会员专享价")
    coupon_saved: Optional[float] = Field(default=None, ge=0, description="使用优惠券节省的金额")
    total_saved: Optional[float] = Field(default=None, ge=0, description="总共节省的金额")
    store_id: uuid.UUID = Field(foreign_key="store.id", description="所属店铺ID")


class ProductCreate(ProductBase):
    pass


class ProductUpdate(SQLModel):
    title: Optional[str] = Field(default=None, max_length=255)
    subtitle: Optional[str] = Field(default=None, max_length=500)
    price: Optional[float] = Field(default=None, gt=0)
    original_price: Optional[float] = Field(default=None, gt=0)
    discount: Optional[str] = Field(default=None, max_length=100)
    image_url: Optional[str] = Field(default=None, max_length=500)
    tag: Optional[str] = Field(default=None, max_length=100)
    sales_count: Optional[str] = Field(default=None, max_length=100)
    category: Optional[str] = Field(default=None, max_length=100)
    member_price: Optional[float] = Field(default=None, gt=0)
    coupon_saved: Optional[float] = Field(default=None, ge=0)
    total_saved: Optional[float] = Field(default=None, ge=0)


class Product(ProductBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    store: Store | None = Relationship(back_populates="products")
    detail: Optional["ProductDetail"] = Relationship(back_populates="product")

class ProductPublic(ProductBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class ProductsPublic(SQLModel):
    data: list[ProductPublic]
    count: int
    is_more: bool


class ProductInfo(SQLModel):
    """统一的商品信息模型 - 用于前端复用"""
    id: uuid.UUID
    title: str
    subtitle: str
    price: float
    original_price: float
    discount: str
    image_url: str
    tag: str
    sales_count: str
    category: str
    member_price: Optional[float] = None
    coupon_saved: Optional[float] = None
    total_saved: Optional[float] = None
    store_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# 商品详情模型
class ProductDetailBase(SQLModel):
    name: str = Field(max_length=255, description="商品名称")
    description: str = Field(description="详细描述")
    short_description: str = Field(max_length=255, description="简短描述")
    sku: str = Field(max_length=100, description="库存单位")
    price: float = Field(gt=0, description="标准价格")
    sale_price: Optional[float] = Field(default=None, gt=0, description="促销价格")
    stock_quantity: int = Field(default=0, description="库存数量，-1表示无限库存")
    is_in_stock: bool = Field(default=True, description="库存状态")
    category_id: Optional[int] = Field(default=None, description="分类ID")
    main_image_url: str = Field(max_length=500, description="主图链接")
    gallery_image_urls: str = Field(description="图库链接JSON数组")
    tags: str = Field(description="标签JSON数组")
    status: str = Field(default="published", max_length=20, description="商品状态")
    attributes: str = Field(description="商品属性JSON")
    variants: str = Field(description="商品多规格JSON")
    average_rating: float = Field(default=0.0, ge=0, le=5, description="平均评分")
    review_count: int = Field(default=0, ge=0, description="评价总数")
    # 赠送内容
    gift_data_package: Optional[str] = Field(default=None, max_length=100, description="赠送流量包")
    gift_coupon: Optional[str] = Field(default=None, max_length=100, description="赠送优惠券")
    gift_voice_package: Optional[str] = Field(default=None, max_length=100, description="赠送语音包")
    gift_membership: Optional[str] = Field(default=None, max_length=100, description="赠送会员")
    product_id: uuid.UUID = Field(foreign_key="product.id", description="关联的基础商品ID")
    
    # 商家描述
    product_description: Optional[str] = Field(default=None, max_length=1000, description="产品描述")
    
    # 使用规则/购买须知
    usage_rules: Optional[str] = Field(default=None, max_length=1000, description="使用规则/购买须知")


class ProductDetailCreate(ProductDetailBase):
    pass


class ProductDetailUpdate(SQLModel):
    name: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = Field(default=None)
    short_description: Optional[str] = Field(default=None, max_length=255)
    sku: Optional[str] = Field(default=None, max_length=100)
    price: Optional[float] = Field(default=None, gt=0)
    sale_price: Optional[float] = Field(default=None, gt=0)
    stock_quantity: Optional[int] = Field(default=None)
    is_in_stock: Optional[bool] = Field(default=None)
    category_id: Optional[int] = Field(default=None)
    main_image_url: Optional[str] = Field(default=None, max_length=500)
    gallery_image_urls: Optional[str] = Field(default=None)
    tags: Optional[str] = Field(default=None)
    status: Optional[str] = Field(default=None, max_length=20)
    attributes: Optional[str] = Field(default=None)
    variants: Optional[str] = Field(default=None)
    average_rating: Optional[float] = Field(default=None, ge=0, le=5)
    review_count: Optional[int] = Field(default=None, ge=0)
    gift_data_package: Optional[str] = Field(default=None, max_length=100)
    gift_coupon: Optional[str] = Field(default=None, max_length=100)
    gift_voice_package: Optional[str] = Field(default=None, max_length=100)
    gift_membership: Optional[str] = Field(default=None, max_length=100)
    product_description: Optional[str] = Field(default=None, max_length=1000)
    usage_rules: Optional[str] = Field(default=None, max_length=1000)

class ProductDetail(ProductDetailBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    product: Optional[Product] = Relationship(back_populates="detail")


class ProductDetailPublic(ProductDetailBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    store_id: uuid.UUID


# ==================== 流量包相关模型 ====================

class DataPackageBase(SQLModel):
    package_name: str = Field(max_length=100, description="流量包名称")
    package_type: str = Field(max_length=20, description="包类型：GENERAL(通用), APP_SPECIFIC(定向)")
    total_mb: int = Field(description="总流量（单位：MB）")
    used_mb: int = Field(default=0, description="已用流量（单位：MB）")
    expiration_date: datetime = Field(description="截止日期")
    is_shared: bool = Field(default=False, description="是否为共享流量")
    status: str = Field(default="ACTIVE", max_length=20, description="状态：ACTIVE(有效), EXPIRED(已过期), DEPLETED(已用尽)")


class DataPackageCreate(DataPackageBase):
    user_id: uuid.UUID = Field(description="关联的用户ID")


class DataPackageUpdate(SQLModel):
    package_name: Optional[str] = Field(default=None, max_length=100)
    package_type: Optional[str] = Field(default=None, max_length=20)
    total_mb: Optional[int] = Field(default=None)
    used_mb: Optional[int] = Field(default=None)
    expiration_date: Optional[datetime] = Field(default=None)
    is_shared: Optional[bool] = Field(default=None)
    status: Optional[str] = Field(default=None, max_length=20)


class DataPackage(DataPackageBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", description="关联的用户ID")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    user: Optional["User"] = Relationship(back_populates="data_packages")


class DataPackagePublic(DataPackageBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# ==================== 会员权益相关模型 ====================

class MembershipBenefitBase(SQLModel):
    benefit_name: str = Field(max_length=100, description="权益名称")
    provider_id: str = Field(max_length=50, description="平台唯一标识")
    description: str = Field(max_length=255, description="权益描述")
    total_duration_days: int = Field(description="总权益天数")
    activation_date: datetime = Field(description="权益生效时间")
    expiration_date: datetime = Field(description="权益过期时间")
    status: str = Field(default="ACTIVE", max_length=20, description="状态：ACTIVE(有效), EXPIRED(已过期)")
    ui_config_json: Optional[str] = Field(default=None, description="UI配置JSON")


class MembershipBenefitCreate(MembershipBenefitBase):
    user_id: uuid.UUID = Field(description="关联的用户ID")


class MembershipBenefitUpdate(SQLModel):
    benefit_name: Optional[str] = Field(default=None, max_length=100)
    provider_id: Optional[str] = Field(default=None, max_length=50)
    description: Optional[str] = Field(default=None, max_length=255)
    total_duration_days: Optional[int] = Field(default=None)
    activation_date: Optional[datetime] = Field(default=None)
    expiration_date: Optional[datetime] = Field(default=None)
    status: Optional[str] = Field(default=None, max_length=20)
    ui_config_json: Optional[str] = Field(default=None)


class MembershipBenefit(MembershipBenefitBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", description="关联的用户ID")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    user: Optional["User"] = Relationship(back_populates="membership_benefits")


class MembershipBenefitPublic(MembershipBenefitBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# ==================== 优惠券模板相关模型 ====================

class CouponTemplateBase(SQLModel):
    title: str = Field(max_length=255, description="优惠券标题")
    coupon_type: int = Field(description="优惠券类型 (1-满减券, 2-折扣券, 3-运费抵扣券, 4-兑换券)")
    value: float = Field(ge=0, description="面值/折扣率")
    min_spend: float = Field(default=0.00, ge=0, description="最低消费金额")
    description: Optional[str] = Field(default=None, description="详细使用规则")
    usage_scope_desc: Optional[str] = Field(default=None, max_length=255, description="使用范围简述")
    total_quantity: int = Field(default=-1, description="发行总量 (-1表示无限)")
    issued_quantity: int = Field(default=0, ge=0, description="已领取数量")
    validity_type: int = Field(description="有效期类型 (1-固定日期, 2-领取后X天有效)")
    valid_days: Optional[int] = Field(default=None, description="有效天数（领取后有效模式使用）")
    fixed_start_time: Optional[datetime] = Field(default=None, description="固定开始时间（固定日期模式使用）")
    fixed_end_time: Optional[datetime] = Field(default=None, description="固定结束时间（固定日期模式使用）")
    is_active: bool = Field(default=True, description="是否激活")


class CouponTemplateCreate(CouponTemplateBase):
    pass


class CouponTemplateUpdate(SQLModel):
    title: Optional[str] = Field(default=None, max_length=255)
    coupon_type: Optional[int] = Field(default=None)
    value: Optional[float] = Field(default=None, ge=0)
    min_spend: Optional[float] = Field(default=None, ge=0)
    description: Optional[str] = Field(default=None)
    usage_scope_desc: Optional[str] = Field(default=None, max_length=255)
    total_quantity: Optional[int] = Field(default=None)
    issued_quantity: Optional[int] = Field(default=None, ge=0)
    validity_type: Optional[int] = Field(default=None)
    valid_days: Optional[int] = Field(default=None)
    fixed_start_time: Optional[datetime] = Field(default=None)
    fixed_end_time: Optional[datetime] = Field(default=None)
    is_active: Optional[bool] = Field(default=None)


class CouponTemplate(CouponTemplateBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    user_coupons: list["UserCoupon"] = Relationship(back_populates="coupon_template")


class CouponTemplatePublic(CouponTemplateBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class CouponTemplatesPublic(SQLModel):
    data: list[CouponTemplatePublic]
    count: int


# ==================== 用户优惠券相关模型 ====================

class UserCouponBase(SQLModel):
    title: str = Field(max_length=255, description="优惠券标题")
    status: int = Field(default=0, description="优惠券状态 (0-未使用, 1-已使用, 2-已过期, 3-冻结中)")
    coupon_code: Optional[str] = Field(default=None, max_length=50, description="优惠券编号/用券码")
    coupon_type: int = Field(description="优惠券类型 (1-满减券, 2-折扣券, 3-运费抵扣券, 4-兑换券)")
    value: float = Field(ge=0, description="面值/折扣率")
    min_spend: float = Field(default=0.00, ge=0, description="最低消费金额")
    description: Optional[str] = Field(default=None, description="详细使用规则")
    usage_scope_desc: Optional[str] = Field(default=None, max_length=255, description="使用范围简述")
    detailed_instructions: Optional[str] = Field(default=None, description="详细使用说明和注意事项")
    start_time: datetime = Field(description="有效期开始时间")
    end_time: datetime = Field(description="有效期结束时间")
    used_time: Optional[datetime] = Field(default=None, description="使用时间")


class UserCouponCreate(UserCouponBase):
    user_id: uuid.UUID = Field(description="用户ID")
    coupon_template_id: uuid.UUID = Field(description="优惠券模板ID")
    order_id: Optional[uuid.UUID] = Field(default=None, description="关联的订单ID")


class UserCouponUpdate(SQLModel):
    title: Optional[str] = Field(default=None, max_length=255)
    status: Optional[int] = Field(default=None)
    coupon_code: Optional[str] = Field(default=None, max_length=50)
    coupon_type: Optional[int] = Field(default=None)
    value: Optional[float] = Field(default=None, ge=0)
    min_spend: Optional[float] = Field(default=None, ge=0)
    description: Optional[str] = Field(default=None)
    usage_scope_desc: Optional[str] = Field(default=None, max_length=255)
    detailed_instructions: Optional[str] = Field(default=None, description="详细使用说明和注意事项")
    start_time: Optional[datetime] = Field(default=None)
    end_time: Optional[datetime] = Field(default=None)
    used_time: Optional[datetime] = Field(default=None)
    order_id: Optional[uuid.UUID] = Field(default=None)


class UserCoupon(UserCouponBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", description="用户ID")
    coupon_template_id: uuid.UUID = Field(foreign_key="coupontemplate.id", description="优惠券模板ID")
    order_id: Optional[uuid.UUID] = Field(default=None, description="关联的订单ID")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="领取时间")
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # 关系定义
    user: Optional[User] = Relationship(back_populates="user_coupons")
    coupon_template: Optional[CouponTemplate] = Relationship(back_populates="user_coupons")


class UserCouponPublic(UserCouponBase):
    id: uuid.UUID
    user_id: uuid.UUID
    coupon_template_id: uuid.UUID
    order_id: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime


class UserCouponsPublic(SQLModel):
    data: list[UserCouponPublic]
    count: int


# ==================== 订单系统模型 ====================

# 订单状态枚举
class OrderStatus(str, Enum):
    PENDING_PAYMENT = "pending_payment"  # 待支付
    PROCESSING = "processing"  # 处理中/待发货
    SHIPPED = "shipped"  # 已发货
    DELIVERED = "delivered"  # 已送达
    COMPLETED = "completed"  # 已完成
    CANCELLED = "cancelled"  # 已取消
    REFUNDED = "refunded"  # 已退款/售后
    ON_HOLD = "on_hold"  # 挂起


# 支付方式枚举
class PaymentMethod(str, Enum):
    CREDIT_CARD = "credit_card"
    ALIPAY = "alipay"
    WECHAT_PAY = "wechat_pay"
    PAYPAL = "paypal"
    BANK_TRANSFER = "bank_transfer"


# 订单主表模型
class OrderBase(SQLModel):
    order_number: str = Field(max_length=255, description="订单号，给用户和客服看的业务编号")
    status: OrderStatus = Field(default=OrderStatus.PENDING_PAYMENT, description="订单状态")
    subtotal_amount: float = Field(ge=0, description="商品总金额，不含运费、税费、折扣")
    shipping_fee: float = Field(default=0.0, ge=0, description="运费")
    tax_amount: float = Field(default=0.0, ge=0, description="税费")
    discount_amount: float = Field(default=0.0, ge=0, description="优惠金额")
    total_amount: float = Field(ge=0, description="订单最终总金额")
    shipping_address: str = Field(description="收货地址快照JSON")
    billing_address: Optional[str] = Field(default=None, description="账单地址快照JSON")
    payment_method: Optional[PaymentMethod] = Field(default=None, description="支付方式")
    payment_gateway_txn_id: Optional[str] = Field(default=None, max_length=255, description="支付网关交易号")
    customer_notes: Optional[str] = Field(default=None, description="用户备注")
    internal_notes: Optional[str] = Field(default=None, description="内部备注")
    paid_at: Optional[datetime] = Field(default=None, description="支付时间")
    shipped_at: Optional[datetime] = Field(default=None, description="发货时间")
    completed_at: Optional[datetime] = Field(default=None, description="完成时间")
    pickup_code: Optional[str] = Field(default=None, max_length=9, description="取餐码，9位数字")
    pickup_code_generated_at: Optional[datetime] = Field(default=None, description="取餐码生成时间")
    pickup_code_verified_at: Optional[datetime] = Field(default=None, description="取餐码核销时间")


class OrderCreate(OrderBase):
    user_id: uuid.UUID = Field(description="用户ID")


class OrderUpdate(SQLModel):
    status: Optional[OrderStatus] = Field(default=None)
    shipping_fee: Optional[float] = Field(default=None, ge=0)
    tax_amount: Optional[float] = Field(default=None, ge=0)
    discount_amount: Optional[float] = Field(default=None, ge=0)
    total_amount: Optional[float] = Field(default=None, ge=0)
    shipping_address: Optional[str] = Field(default=None)
    billing_address: Optional[str] = Field(default=None)
    payment_method: Optional[PaymentMethod] = Field(default=None)
    payment_gateway_txn_id: Optional[str] = Field(default=None, max_length=255)
    customer_notes: Optional[str] = Field(default=None)
    internal_notes: Optional[str] = Field(default=None)
    paid_at: Optional[datetime] = Field(default=None)
    shipped_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    pickup_code: Optional[str] = Field(default=None, max_length=9)
    pickup_code_generated_at: Optional[datetime] = Field(default=None)
    pickup_code_verified_at: Optional[datetime] = Field(default=None)


class Order(OrderBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", description="用户ID")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="最后更新时间")
    
    # 软删除字段
    is_deleted: bool = Field(default=False, description="是否已删除")
    deleted_at: Optional[datetime] = Field(default=None, description="删除时间")
    
    # 关系定义
    user: Optional[User] = Relationship(back_populates="orders")
    order_items: list["OrderItem"] = Relationship(back_populates="order", cascade_delete=True)


class OrderPublic(OrderBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class OrdersPublic(SQLModel):
    data: list[OrderPublic]
    count: int
    is_more: bool


# 订单商品表模型
class OrderItemBase(SQLModel):
    product_snapshot: str = Field(description="商品快照JSON")
    quantity: int = Field(ge=1, description="购买数量")
    unit_price: float = Field(gt=0, description="下单时单价")
    total_price: float = Field(gt=0, description="该项商品总价")


class OrderItemCreate(OrderItemBase):
    order_id: uuid.UUID = Field(description="订单ID")
    product_id: uuid.UUID = Field(description="商品ID")


class OrderItemUpdate(SQLModel):
    quantity: Optional[int] = Field(default=None, ge=1)
    unit_price: Optional[float] = Field(default=None, gt=0)
    total_price: Optional[float] = Field(default=None, gt=0)


class OrderItem(OrderItemBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    order_id: uuid.UUID = Field(foreign_key="order.id", description="订单ID")
    product_id: uuid.UUID = Field(foreign_key="product.id", description="商品ID")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新时间")
    
    # 关系定义
    order: Optional[Order] = Relationship(back_populates="order_items")
    product: Optional[Product] = Relationship()


class OrderItemPublic(OrderItemBase):
    id: uuid.UUID
    order_id: uuid.UUID
    product_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# 包含商品信息的订单项
class OrderItemWithProduct(OrderItemPublic):
    product: Optional[dict] = None
    store: Optional[dict] = None


# 包含订单项的完整订单信息
class OrderWithItems(OrderPublic):
    order_items: list[OrderItemWithProduct] = []


class OrdersWithDetailsPublic(SQLModel):
    """包含详情的订单列表响应"""
    data: list[OrderWithItems]
    count: int
    is_more: bool


# 订单创建请求模型
class CreateOrderRequest(SQLModel):
    """创建订单的请求模型"""
    shipping_address: Optional[str] = Field(default="", description="收货地址JSON")
    billing_address: Optional[str] = Field(default=None, description="账单地址JSON")
    customer_notes: Optional[str] = Field(default=None, description="用户备注")
    cart_item_ids: list[uuid.UUID] = Field(description="购物车项ID列表")
    coupon_id: Optional[str] = Field(default=None, description="使用的优惠券ID")


# 支付请求模型
class PaymentRequest(SQLModel):
    """支付请求模型"""
    payment_method: PaymentMethod = Field(description="支付方式")
    payment_gateway_txn_id: Optional[str] = Field(default=None, description="支付网关交易ID")


# 订单状态更新请求模型
class UpdateOrderStatusRequest(SQLModel):
    """更新订单状态的请求模型"""
    status: OrderStatus = Field(description="新状态")
    internal_notes: Optional[str] = Field(default=None, description="内部备注")
    payment_gateway_txn_id: Optional[str] = Field(default=None, description="支付网关交易号")
    tracking_number: Optional[str] = Field(default=None, description="物流单号")


# 取餐码核销请求模型
class VerifyPickupCodeRequest(SQLModel):
    """取餐码核销请求模型"""
    pickup_code: str = Field(min_length=9, max_length=9, description="9位取餐码")


# 订单统计模型
class OrderStats(SQLModel):
    """订单统计信息"""
    total_orders: int = Field(description="总订单数")
    pending_payment: int = Field(description="待支付订单数")
    processing: int = Field(description="处理中订单数")
    shipped: int = Field(description="已发货订单数")
    completed: int = Field(description="已完成订单数")
    cancelled: int = Field(description="已取消订单数")
    total_amount: float = Field(description="总订单金额")


# 三种状态的优惠券列表响应模型
class UserCouponsListPublic(SQLModel):
    data: list[UserCouponPublic]
    count: int
    is_more: bool


# ==================== 购物车相关模型 ====================

class CartItemBase(SQLModel):
    product_id: uuid.UUID = Field(description="商品ID")
    store_id: uuid.UUID = Field(description="店铺ID")
    quantity: int = Field(ge=1, description="商品数量")
    unit_price: float = Field(gt=0, description="添加时的单价")
    total_price: float = Field(gt=0, description="小计金额")
    is_selected: bool = Field(default=True, description="是否选中")
    product_spec: Optional[str] = Field(default=None, max_length=500, description="商品规格信息（JSON格式）")
    notes: Optional[str] = Field(default=None, max_length=255, description="备注信息")


class CartItemCreate(CartItemBase):
    pass


class CartItemSimpleCreate(SQLModel):
    """简化的购物车创建模型 - 只需要商品ID和数量"""
    product_id: uuid.UUID = Field(description="商品ID")
    quantity: int = Field(ge=1, description="商品数量")
    product_spec: Optional[str] = Field(default=None, max_length=500, description="商品规格信息（JSON格式）")
    notes: Optional[str] = Field(default=None, max_length=255, description="备注信息")


class CartItemUpdate(SQLModel):
    quantity: Optional[int] = Field(default=None, ge=1)
    is_selected: Optional[bool] = Field(default=None)
    product_spec: Optional[str] = Field(default=None, max_length=500)
    notes: Optional[str] = Field(default=None, max_length=255)


class CartItem(CartItemBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", description="用户ID")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="添加时间")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新时间")
    
    # 关系定义
    user: Optional[User] = Relationship(back_populates="cart_items")
    product: Optional["Product"] = Relationship(
        sa_relationship_kwargs={
            "primaryjoin": "CartItem.product_id == Product.id",
            "foreign_keys": "[CartItem.product_id]"
        }
    )
    store: Optional["Store"] = Relationship(
        sa_relationship_kwargs={
            "primaryjoin": "CartItem.store_id == Store.id", 
            "foreign_keys": "[CartItem.store_id]"
        }
    )


class CartItemPublic(CartItemBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class CartItemWithDetails(CartItemPublic):
    """包含商品和店铺详情的购物车项"""
    product: Optional["ProductPublic"] = None
    store: Optional["StorePublic"] = None


class CartItemWithProductInfo(CartItemPublic):
    """包含商品信息的购物车项 - 使用统一的ProductInfo模型"""
    product_info: Optional["ProductInfo"] = None


# 批量更新购物车请求模型
class CartItemBatchUpdate(SQLModel):
    """单个购物车项批量更新请求"""
    id: uuid.UUID = Field(description="购物车项ID")
    quantity: Optional[int] = Field(default=None, ge=1, description="商品数量")
    is_selected: Optional[bool] = Field(default=None, description="是否选中")
    product_spec: Optional[str] = Field(default=None, max_length=500, description="商品规格")
    notes: Optional[str] = Field(default=None, max_length=255, description="备注")


class CartBatchUpdateRequest(SQLModel):
    """批量更新购物车请求"""
    updates: list[CartItemBatchUpdate] = Field(description="更新列表")


class CartSummary(SQLModel):
    """购物车汇总信息"""
    total_items: int = Field(description="总商品数量")
    total_quantity: int = Field(description="总商品件数")
    total_amount: float = Field(description="总金额")
    selected_items: int = Field(description="选中商品数量")
    selected_quantity: int = Field(description="选中商品件数")
    selected_amount: float = Field(description="选中商品总金额")
    store_count: int = Field(description="涉及店铺数量")


class CartStoreGroup(SQLModel):
    """按店铺分组的购物车"""
    store_id: uuid.UUID
    store_name: str
    store_image_url: str
    items: list[CartItemWithDetails]
    store_total_amount: float = Field(description="该店铺商品总金额")
    store_selected_amount: float = Field(description="该店铺选中商品总金额")


class CartPublic(SQLModel):
    """购物车完整信息"""
    items: list[CartItemWithDetails]
    store_groups: list[CartStoreGroup]
    summary: CartSummary


class CartItemsPublic(SQLModel):
    """购物车列表响应"""
    data: list[CartItemWithDetails]
    count: int
    is_more: bool
    summary: CartSummary


# ==================== 积分系统相关模型 ====================

# 积分来源类型枚举
class PointsSourceType(str, Enum):
    CHECK_IN = "check_in"  # 签到
    TASK_COMPLETE = "task_complete"  # 任务完成
    ORDER_COMPLETE = "order_complete"  # 订单完成
    REFUND = "refund"  # 退款
    ADMIN_ADJUST = "admin_adjust"  # 管理员调整
    INVITATION = "invitation"  # 邀请奖励
    NEW_USER_BONUS = "new_user_bonus"  # 新用户奖励
    SYSTEM_REWARD = "system_reward"  # 系统奖励
    POINTS_PRODUCT_EXCHANGE = "points_product_exchange"  # 积分商品兑换消耗
    POINTS_PRODUCT_REFUND = "points_product_refund"  # 积分商品退款


# 任务类型枚举
class TaskType(str, Enum):
    ONE_TIME = "one_time"  # 一次性任务
    DAILY = "daily"  # 每日任务
    WEEKLY = "weekly"  # 每周任务
    MONTHLY = "monthly"  # 每月任务
    REPEATABLE = "repeatable"  # 可重复任务


# 用户任务状态枚举
class UserTaskStatus(str, Enum):
    IN_PROGRESS = "in_progress"  # 进行中
    COMPLETED = "completed"  # 已完成
    REWARD_CLAIMED = "reward_claimed"  # 已领取奖励
    EXPIRED = "expired"  # 已过期


class InvitationStatus(str, Enum):
    PENDING = "pending"  # 待处理 - 邀请关系已建立，但奖励条件未达成
    COMPLETED = "completed"  # 已完成 - 被邀请人已满足所有条件，奖励可发放
    EXPIRED = "expired"  # 已过期 - 邀请超过有效期


# 积分流水表 - 核心账本
class PointsTransactionBase(SQLModel):
    user_id: uuid.UUID = Field(foreign_key="user.id", description="用户ID")
    points_change: int = Field(description="本次变动积分，正数代表增加，负数代表减少")
    balance_after: int = Field(description="变动后的总积分")
    source_type: PointsSourceType = Field(description="积分来源类型")
    source_id: Optional[str] = Field(default=None, max_length=255, description="来源关联ID")
    description: str = Field(max_length=255, description="流水描述")


class PointsTransactionCreate(PointsTransactionBase):
    pass


class PointsTransaction(PointsTransactionBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    
    # 关系定义
    user: Optional[User] = Relationship()


class PointsTransactionPublic(PointsTransactionBase):
    id: uuid.UUID
    created_at: datetime


class PointsTransactionsPublic(SQLModel):
    data: list[PointsTransactionPublic]
    count: int
    is_more: bool


# 用户签到历史表
class CheckInHistoryBase(SQLModel):
    user_id: uuid.UUID = Field(foreign_key="user.id", description="用户ID")
    check_in_date: datetime = Field(description="签到日期")
    consecutive_days: int = Field(description="本次签到是连续第几天")
    points_earned: int = Field(description="本次签到获得的积分数")


class CheckInHistoryCreate(CheckInHistoryBase):
    pass


class CheckInHistory(CheckInHistoryBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    
    # 关系定义
    user: Optional[User] = Relationship()
    
    # 唯一约束：每个用户每天只能签到一次
    __table_args__ = (
        {"extend_existing": True},
    )


class CheckInHistoryPublic(CheckInHistoryBase):
    id: uuid.UUID
    created_at: datetime


# 任务定义表
class TaskBase(SQLModel):
    task_code: str = Field(max_length=100, unique=True, description="任务唯一代码")
    title: str = Field(max_length=255, description="任务标题")
    description: str = Field(description="任务详细描述")
    points_reward: int = Field(ge=0, description="完成任务奖励的积分数")
    task_type: TaskType = Field(description="任务类型")
    is_active: bool = Field(default=True, description="任务是否启用")
    max_completions: Optional[int] = Field(default=None, ge=1, description="最大完成次数，None表示无限制")
    cooldown_hours: Optional[int] = Field(default=None, ge=0, description="冷却时间（小时）")
    start_date: Optional[datetime] = Field(default=None, description="任务开始时间")
    end_date: Optional[datetime] = Field(default=None, description="任务结束时间")
    conditions: Optional[str] = Field(default=None, description="完成条件JSON")
    button_text: Optional[str] = Field(default=None, max_length=50, description="按钮显示文本")
    uri: Optional[str] = Field(default=None, max_length=255, description="任务跳转URI")


class TaskCreate(TaskBase):
    pass


class TaskUpdate(SQLModel):
    title: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = Field(default=None)
    points_reward: Optional[int] = Field(default=None, ge=0)
    task_type: Optional[TaskType] = Field(default=None)
    is_active: Optional[bool] = Field(default=None)
    max_completions: Optional[int] = Field(default=None, ge=1)
    cooldown_hours: Optional[int] = Field(default=None, ge=0)
    start_date: Optional[datetime] = Field(default=None)
    end_date: Optional[datetime] = Field(default=None)
    conditions: Optional[str] = Field(default=None)


class Task(TaskBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新时间")
    
    # 关系定义
    user_tasks: list["UserTask"] = Relationship(back_populates="task")


class TaskPublic(TaskBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class TasksPublic(SQLModel):
    data: list[TaskPublic]
    count: int
    is_more: bool


# 用户任务完成情况表
class UserTaskBase(SQLModel):
    user_id: uuid.UUID = Field(foreign_key="user.id", description="用户ID")
    task_id: uuid.UUID = Field(foreign_key="task.id", description="任务ID")
    status: UserTaskStatus = Field(default=UserTaskStatus.IN_PROGRESS, description="任务状态")
    completed_at: Optional[datetime] = Field(default=None, description="完成时间")
    claimed_at: Optional[datetime] = Field(default=None, description="领取奖励时间")
    completion_count: int = Field(default=0, ge=0, description="完成次数")
    last_completed_at: Optional[datetime] = Field(default=None, description="最后完成时间")


class UserTaskCreate(UserTaskBase):
    pass


class UserTaskUpdate(SQLModel):
    status: Optional[UserTaskStatus] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    claimed_at: Optional[datetime] = Field(default=None)
    completion_count: Optional[int] = Field(default=None, ge=0)
    last_completed_at: Optional[datetime] = Field(default=None)


class UserTask(UserTaskBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新时间")
    
    # 关系定义
    user: Optional[User] = Relationship()
    task: Optional[Task] = Relationship(back_populates="user_tasks")


class UserTaskPublic(UserTaskBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class UserTasksPublic(SQLModel):
    data: list[UserTaskPublic]
    count: int
    is_more: bool


# ==================== 邀请系统相关模型 ====================

class InvitationBase(SQLModel):
    inviter_id: uuid.UUID = Field(foreign_key="user.id", description="邀请人ID")
    invitee_id: uuid.UUID = Field(foreign_key="user.id", description="被邀请人ID")
    status: InvitationStatus = Field(default=InvitationStatus.PENDING, description="邀请状态")
    reward_points: int = Field(default=0, ge=0, description="邀请奖励积分")
    reward_claimed_at: Optional[datetime] = Field(default=None, description="奖励领取时间")


class InvitationCreate(SQLModel):
    inviter_id: uuid.UUID = Field(description="邀请人ID")
    invitee_id: uuid.UUID = Field(description="被邀请人ID")
    status: InvitationStatus = Field(default=InvitationStatus.PENDING, description="邀请状态")
    reward_points: int = Field(default=0, ge=0, description="邀请奖励积分")
    reward_claimed_at: Optional[datetime] = Field(default=None, description="奖励领取时间")


class InvitationUpdate(SQLModel):
    status: Optional[InvitationStatus] = Field(default=None)
    reward_claimed_at: Optional[datetime] = Field(default=None)


class Invitation(InvitationBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新时间")
    
    # 关系定义
    inviter: Optional[User] = Relationship(back_populates="invitations_sent", sa_relationship_kwargs={"foreign_keys": "Invitation.inviter_id"})
    invitee: Optional[User] = Relationship(back_populates="invitations_received", sa_relationship_kwargs={"foreign_keys": "Invitation.invitee_id"})


class InvitationPublic(InvitationBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class InvitationsPublic(SQLModel):
    data: list[InvitationPublic]
    count: int
    is_more: bool


# 邀请统计模型
class InvitationStats(SQLModel):
    total_invitations: int = Field(description="总邀请数")
    completed_invitations: int = Field(description="已完成邀请数")
    pending_invitations: int = Field(description="待处理邀请数")
    total_reward_points: int = Field(description="总奖励积分")
    claimed_reward_points: int = Field(description="已领取奖励积分")


# 积分排行榜模型
class PointsLeaderboardEntry(SQLModel):
    user_id: uuid.UUID
    full_name: Optional[str]
    email: str
    points_balance: int


# 积分兑换排行榜模型（用户维度）
class PointsRedemptionLeaderboardEntry(SQLModel):
    user_id: uuid.UUID
    full_name: Optional[str]
    email: str
    points_redeemed: int
    rank: int
    avatar_url: Optional[str] = None


class PointsRedemptionLeaderboardPublic(SQLModel):
    data: list[PointsRedemptionLeaderboardEntry]
    count: int
    user_rank: Optional[int] = None  # 当前用户的排名


# 商品兑换排行榜模型（商品维度）
class ProductExchangeLeaderboardEntry(SQLModel):
    product_id: uuid.UUID
    product_name: str
    product_image_url: str
    exchanged_quantity: int
    points_required: int
    rank: int
    category_name: Optional[str] = None
    tags: list[str] = Field(default_factory=list, description="商品标签")


class ProductExchangeLeaderboardPublic(SQLModel):
    data: list[ProductExchangeLeaderboardEntry]
    count: int


# ==================== 弹窗配置相关模型 ====================

# 弹窗触发事件枚举
class DialogTriggerEvent(str, Enum):
    APP_LAUNCH = "APP_LAUNCH"  # 应用启动
    ENTER_STORE_PAGE = "ENTER_STORE_PAGE"  # 进入商店页面
    ENTER_PRODUCT_PAGE = "ENTER_PRODUCT_PAGE"  # 进入商品页面
    USER_LOGIN = "USER_LOGIN"  # 用户登录
    ORDER_COMPLETE = "ORDER_COMPLETE"  # 订单完成
    CUSTOM = "CUSTOM"  # 自定义事件
    # 注意：新增事件类型时，建议先在数据库中创建配置，然后更新此枚举
    # 这样可以保持向后兼容性


# 弹窗类型枚举
class DialogType(str, Enum):
    PROMOTION_BANNER = "PROMOTION_BANNER"  # 促销横幅
    NOTIFICATION_POPUP = "NOTIFICATION_POPUP"  # 通知弹窗
    CONFIRMATION_DIALOG = "CONFIRMATION_DIALOG"  # 确认对话框
    INFO_MODAL = "INFO_MODAL"  # 信息模态框
    CUSTOM = "CUSTOM"  # 自定义弹窗


# 目标用户群体枚举
class TargetAudience(str, Enum):
    ALL_USERS = "ALL_USERS"  # 所有用户
    NEW_USERS = "NEW_USERS"  # 新用户
    VIP_USERS = "VIP_USERS"  # VIP用户
    SPECIFIC_USERS = "SPECIFIC_USERS"  # 特定用户


# 显示频率枚举
class DisplayFrequency(str, Enum):
    ONCE = "ONCE"  # 只显示一次
    DAILY = "DAILY"  # 每天一次
    WEEKLY = "WEEKLY"  # 每周一次
    ALWAYS = "ALWAYS"  # 每次都显示


# 按钮配置模型
class ButtonConfig(SQLModel):
    text: str = Field(description="按钮文本")
    action_uri: str = Field(description="按钮动作URI")
    action_type: str = Field(default="navigate", description="动作类型：navigate, dismiss, custom")
    style: Optional[str] = Field(default=None, description="按钮样式")


# 弹窗配置基础模型
class DialogConfigBase(SQLModel):
    name: str = Field(max_length=255, description="弹窗名称")
    priority: int = Field(default=0, description="优先级，数字越大优先级越高")
    trigger_event: str = Field(description="触发事件")
    dialog_type: DialogType = Field(description="弹窗类型")
    payload: Optional[str] = Field(default=None, description="动态数据包JSON")
    buttons: Optional[str] = Field(default=None, description="按钮配置JSON")
    start_time: datetime = Field(description="生效开始时间")
    end_time: datetime = Field(description="生效结束时间")
    is_active: bool = Field(default=True, description="是否激活")
    target_audience: TargetAudience = Field(default=TargetAudience.ALL_USERS, description="目标用户群体")
    display_frequency: DisplayFrequency = Field(default=DisplayFrequency.ONCE, description="显示频率")
    max_display_count: Optional[int] = Field(default=None, description="最大显示次数")
    description: Optional[str] = Field(default=None, max_length=500, description="描述")


# 弹窗配置创建模型
class DialogConfigCreate(DialogConfigBase):
    pass


# 弹窗配置更新模型
class DialogConfigUpdate(SQLModel):
    name: Optional[str] = Field(default=None, max_length=255)
    priority: Optional[int] = Field(default=None)
    trigger_event: Optional[DialogTriggerEvent] = Field(default=None)
    dialog_type: Optional[DialogType] = Field(default=None)
    payload: Optional[str] = Field(default=None)
    buttons: Optional[str] = Field(default=None)
    start_time: Optional[datetime] = Field(default=None)
    end_time: Optional[datetime] = Field(default=None)
    is_active: Optional[bool] = Field(default=None)
    target_audience: Optional[TargetAudience] = Field(default=None)
    display_frequency: Optional[DisplayFrequency] = Field(default=None)
    max_display_count: Optional[int] = Field(default=None)
    description: Optional[str] = Field(default=None, max_length=500)


# 弹窗配置数据库模型
class DialogConfig(DialogConfigBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新时间")


# 弹窗配置公开模型
class DialogConfigPublic(DialogConfigBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# 弹窗配置列表模型
class DialogConfigsPublic(SQLModel):
    data: List[DialogConfigPublic]
    count: int
    is_more: bool


# 弹窗显示记录模型
class DialogDisplayRecordBase(SQLModel):
    user_id: uuid.UUID = Field(foreign_key="user.id", description="用户ID")
    dialog_config_id: uuid.UUID = Field(foreign_key="dialogconfig.id", description="弹窗配置ID")
    display_count: int = Field(default=1, description="显示次数")
    last_displayed_at: datetime = Field(default_factory=datetime.utcnow, description="最后显示时间")


# 弹窗显示记录创建模型
class DialogDisplayRecordCreate(DialogDisplayRecordBase):
    pass


# 弹窗显示记录数据库模型
class DialogDisplayRecord(DialogDisplayRecordBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新时间")


# 弹窗显示记录公开模型
class DialogDisplayRecordPublic(DialogDisplayRecordBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class PointsLeaderboardPublic(SQLModel):
    data: list[PointsLeaderboardEntry]
    count: int
    user_rank: Optional[int] = None  # 当前用户的排名


# 签到响应模型
class CheckInResponse(SQLModel):
    success: bool
    message: str
    points_earned: int
    consecutive_days: int
    total_points: int
    current_rank: Optional[int] = None


# 任务完成响应模型
class TaskCompleteResponse(SQLModel):
    success: bool
    message: str
    points_earned: int
    total_points: int
    current_rank: Optional[int] = None
    task_completion_count: int


# 用户积分统计模型
class UserPointsStats(SQLModel):
    total_points: int
    current_rank: Optional[int]
    consecutive_check_in_days: int
    total_check_ins: int
    total_tasks_completed: int
    points_this_month: int
    points_this_week: int
    points_today: int


# 积分历史查询模型
class PointsHistoryQuery(SQLModel):
    start_date: Optional[datetime] = Field(default=None, description="开始日期")
    end_date: Optional[datetime] = Field(default=None, description="结束日期")
    source_type: Optional[PointsSourceType] = Field(default=None, description="来源类型")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")


# 月度签到统计模型
class MonthlyCheckInStats(SQLModel):
    year: int
    month: int
    total_days: int
    check_in_days: int
    consecutive_days: int
    points_earned: int
    check_in_dates: list[datetime]


# ==================== 抽奖系统相关模型 ====================

# 抽奖活动状态枚举
class LotteryActivityStatus(str, Enum):
    DRAFT = "DRAFT"  # 草稿
    ACTIVE = "ACTIVE"  # 进行中
    PAUSED = "PAUSED"  # 暂停
    ENDED = "ENDED"  # 已结束
    CANCELLED = "CANCELLED"  # 已取消


# 奖品类型枚举
class PrizeType(str, Enum):
    POINTS = "POINTS"  # 积分
    VIRTUAL = "VIRTUAL"  # 虚拟奖品（会员、优惠券等）
    PHYSICAL = "PHYSICAL"  # 实物奖品
    THANK_YOU = "THANK_YOU"  # 谢谢参与


# 奖品状态枚举
class PrizeStatus(str, Enum):
    ACTIVE = "ACTIVE"  # 可用
    INACTIVE = "INACTIVE"  # 不可用
    OUT_OF_STOCK = "OUT_OF_STOCK"  # 缺货


# 用户奖品状态枚举
class UserPrizeStatus(str, Enum):
    PENDING = "PENDING"  # 待处理
    CLAIMED = "CLAIMED"  # 已领取
    EXPIRED = "EXPIRED"  # 已过期
    CANCELLED = "CANCELLED"  # 已取消


# 抽奖活动基础模型
class LotteryActivityBase(SQLModel):
    name: str = Field(max_length=100, description="活动名称")
    description: Optional[str] = Field(default=None, max_length=500, description="活动描述")
    start_time: datetime = Field(description="开始时间")
    end_time: datetime = Field(description="结束时间")
    status: LotteryActivityStatus = Field(default=LotteryActivityStatus.DRAFT, description="活动状态")
    max_draws_per_user: Optional[int] = Field(default=None, description="每用户最大抽奖次数")
    points_cost: int = Field(default=0, description="每次抽奖消耗积分")
    is_active: bool = Field(default=True, description="是否启用")


# 抽奖活动创建模型
class LotteryActivityCreate(LotteryActivityBase):
    pass


# 抽奖活动更新模型
class LotteryActivityUpdate(SQLModel):
    name: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: Optional[LotteryActivityStatus] = None
    max_draws_per_user: Optional[int] = None
    points_cost: Optional[int] = None
    is_active: Optional[bool] = None


# 抽奖活动数据库模型
class LotteryActivity(LotteryActivityBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新时间")
    
    # 关联关系
    prizes: list["LotteryPrize"] = Relationship(back_populates="activity", cascade_delete=True)
    records: list["LotteryRecord"] = Relationship(back_populates="activity", cascade_delete=True)


# 抽奖奖品基础模型
class LotteryPrizeBase(SQLModel):
    name: str = Field(max_length=100, description="奖品名称")
    description: Optional[str] = Field(default=None, max_length=500, description="奖品描述")
    prize_type: PrizeType = Field(description="奖品类型")
    image_url: Optional[str] = Field(default=None, max_length=255, description="奖品图片URL")
    quantity: int = Field(ge=0, description="库存数量")
    weight: int = Field(default=1, ge=1, description="权重（用于计算中奖概率）")
    points_value: Optional[int] = Field(default=None, ge=0, description="积分价值")
    is_active: bool = Field(default=True, description="是否启用")
    sort_order: int = Field(default=0, description="排序")


# 抽奖奖品创建模型
class LotteryPrizeCreate(LotteryPrizeBase):
    activity_id: uuid.UUID = Field(description="所属活动ID")


# 抽奖奖品更新模型
class LotteryPrizeUpdate(SQLModel):
    name: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    prize_type: Optional[PrizeType] = None
    image_url: Optional[str] = Field(default=None, max_length=255)
    quantity: Optional[int] = Field(default=None, ge=0)
    weight: Optional[int] = Field(default=None, ge=1)
    points_value: Optional[int] = Field(default=None, ge=0)
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


# 抽奖奖品数据库模型
class LotteryPrize(LotteryPrizeBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    activity_id: uuid.UUID = Field(foreign_key="lotteryactivity.id", description="所属活动ID")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新时间")
    
    # 关联关系
    activity: Optional[LotteryActivity] = Relationship(back_populates="prizes")
    records: list["LotteryRecord"] = Relationship(back_populates="prize", cascade_delete=True)
    user_prizes: list["UserPrize"] = Relationship(back_populates="prize", cascade_delete=True)


# 抽奖记录基础模型
class LotteryRecordBase(SQLModel):
    user_id: uuid.UUID = Field(foreign_key="user.id", description="用户ID")
    activity_id: uuid.UUID = Field(foreign_key="lotteryactivity.id", description="活动ID")
    prize_id: uuid.UUID = Field(foreign_key="lotteryprize.id", description="奖品ID")
    prize_name_snapshot: str = Field(max_length=100, description="奖品名称快照")
    prize_type_snapshot: PrizeType = Field(description="奖品类型快照")
    points_cost: int = Field(description="消耗积分")


# 抽奖记录创建模型
class LotteryRecordCreate(LotteryRecordBase):
    pass


# 抽奖记录数据库模型
class LotteryRecord(LotteryRecordBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, description="抽奖时间")
    
    # 关联关系
    user: Optional[User] = Relationship()
    activity: Optional[LotteryActivity] = Relationship(back_populates="records")
    prize: Optional[LotteryPrize] = Relationship(back_populates="records")


# 用户奖品基础模型
class UserPrizeBase(SQLModel):
    user_id: uuid.UUID = Field(foreign_key="user.id", description="用户ID")
    prize_id: uuid.UUID = Field(foreign_key="lotteryprize.id", description="奖品ID")
    status: UserPrizeStatus = Field(default=UserPrizeStatus.PENDING, description="奖品状态")
    claimed_at: Optional[datetime] = Field(default=None, description="领取时间")
    expired_at: Optional[datetime] = Field(default=None, description="过期时间")
    notes: Optional[str] = Field(default=None, max_length=500, description="备注")


# 用户奖品创建模型
class UserPrizeCreate(UserPrizeBase):
    pass


# 用户奖品更新模型
class UserPrizeUpdate(SQLModel):
    status: Optional[UserPrizeStatus] = None
    claimed_at: Optional[datetime] = None
    expired_at: Optional[datetime] = None
    notes: Optional[str] = Field(default=None, max_length=500)


# 用户奖品数据库模型
class UserPrize(UserPrizeBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, description="获得时间")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新时间")
    
    # 关联关系
    user: Optional[User] = Relationship()
    prize: Optional[LotteryPrize] = Relationship(back_populates="user_prizes")


# ==================== 抽奖系统API响应模型 ====================

# 抽奖活动公开模型
class LotteryActivityPublic(LotteryActivityBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    prize_count: int = Field(default=0, description="奖品数量")
    total_draws: int = Field(default=0, description="总抽奖次数")


# 抽奖奖品公开模型
class LotteryPrizePublic(LotteryPrizeBase):
    id: uuid.UUID
    activity_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# 抽奖记录公开模型
class LotteryRecordPublic(LotteryRecordBase):
    id: uuid.UUID
    created_at: datetime
    prize: Optional[LotteryPrizePublic] = None


# 用户奖品公开模型
class UserPrizePublic(UserPrizeBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    prize: Optional[LotteryPrizePublic] = None


# 抽奖请求模型
class LotteryDrawRequest(SQLModel):
    activity_id: uuid.UUID = Field(description="活动ID")


# 抽奖响应模型
class LotteryDrawResponse(SQLModel):
    success: bool
    message: str
    prize: Optional[LotteryPrizePublic] = None
    points_balance: int = Field(default=0, description="剩余积分")
    remaining_draws: Optional[int] = Field(default=None, description="剩余抽奖次数")


# 抽奖活动列表响应模型
class LotteryActivitiesResponse(SQLModel):
    success: bool
    message: str
    data: list[LotteryActivityPublic]
    total: int
    page: int
    page_size: int


# 抽奖奖品列表响应模型
class LotteryPrizesResponse(SQLModel):
    success: bool
    message: str
    data: list[LotteryPrizePublic]
    total: int
    page: int
    page_size: int


# 用户抽奖记录响应模型
class UserLotteryRecordsResponse(SQLModel):
    success: bool
    message: str
    data: list[LotteryRecordPublic]
    total: int
    page: int
    page_size: int


# 用户奖品列表响应模型
class UserPrizesResponse(SQLModel):
    success: bool
    message: str
    data: list[UserPrizePublic]
    total: int
    page: int
    page_size: int


# ==================== 发现页面相关模型 ====================

# 服务号类型枚举
class ServiceAccountType(str, Enum):
    SERVICE_ACCOUNT = "SERVICE_ACCOUNT"  # 服务号
    MERCHANT_ACCOUNT = "MERCHANT_ACCOUNT"  # 商户号


# 服务号基础模型
class ServiceAccountBase(SQLModel):
    user_id: uuid.UUID = Field(foreign_key="user.id", description="所属用户ID")
    name: str = Field(description="服务号名称")
    avatar_url: str = Field(description="头像URL")
    account_type: ServiceAccountType = Field(description="账号类型")
    description: Optional[str] = Field(default=None, description="描述")
    is_active: bool = Field(default=True, description="是否激活")


# 服务号创建模型
class ServiceAccountCreate(ServiceAccountBase):
    pass


# 服务号更新模型
class ServiceAccountUpdate(SQLModel):
    name: Optional[str] = Field(default=None, description="服务号名称")
    avatar_url: Optional[str] = Field(default=None, description="头像URL")
    account_type: Optional[ServiceAccountType] = Field(default=None, description="账号类型")
    description: Optional[str] = Field(default=None, description="描述")
    is_active: Optional[bool] = Field(default=None, description="是否激活")


# 服务号表模型
class ServiceAccount(ServiceAccountBase, table=True):
    __tablename__ = "service_account"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新时间")
    
    # 关系
    user: Optional["User"] = Relationship(back_populates="service_accounts")


# 服务号公开模型
class ServiceAccountPublic(ServiceAccountBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    user_name: Optional[str] = Field(default=None, description="用户名称")


# 服务号列表响应模型
class ServiceAccountListResponse(SQLModel):
    data: list[ServiceAccountPublic]
    total: int
    page: int
    page_size: int


# 文章类型枚举
class ArticleType(str, Enum):
    SHARE = "SHARE"  # 分享
    TUTORIAL = "TUTORIAL"  # 教程
    ACTIVITY = "ACTIVITY"  # 活动


# 文章状态枚举
class ArticleStatus(str, Enum):
    PUBLISHED = "PUBLISHED"  # 已发布
    DRAFT = "DRAFT"  # 草稿
    DELETED = "DELETED"  # 已删除


# 社区任务类型枚举
class CommunityTaskType(str, Enum):
    TRAFFIC_EXCHANGE = "TRAFFIC_EXCHANGE"  # 流量互换
    TRAFFIC_MEMBERSHIP = "TRAFFIC_MEMBERSHIP"  # 流量换会员
    SECOND_HAND = "SECOND_HAND"  # 换二手
    COUPON_EXCHANGE = "COUPON_EXCHANGE"  # 换优惠券
    TRAFFIC_HELP = "TRAFFIC_HELP"  # 流量互助


# 社区任务状态枚举
class CommunityTaskStatus(str, Enum):
    OPEN = "OPEN"  # 开放中
    IN_PROGRESS = "IN_PROGRESS"  # 进行中
    COMPLETED = "COMPLETED"  # 已完成
    CANCELLED = "CANCELLED"  # 已取消
    EXPIRED = "EXPIRED"  # 已过期


# 申请状态枚举
class ApplicationStatus(str, Enum):
    PENDING = "PENDING"  # 待处理
    ACCEPTED = "ACCEPTED"  # 已接受
    REJECTED = "REJECTED"  # 已拒绝


# 文章基础模型
class ArticleBase(SQLModel):
    title: str = Field(max_length=255, description="文章标题")
    content: str = Field(description="文章正文")
    cover_image_url: Optional[str] = Field(default=None, max_length=255, description="封面图地址")
    type: ArticleType = Field(description="文章类型")
    status: ArticleStatus = Field(default=ArticleStatus.PUBLISHED, description="文章状态")
    view_count: int = Field(default=0, description="浏览数")
    like_count: int = Field(default=0, description="点赞数")
    comment_count: int = Field(default=0, description="评论数")
    share_count: int = Field(default=0, description="分享数")
    hot_score: float = Field(default=0.0, description="热度分")


# 文章创建模型
class ArticleCreate(ArticleBase):
    pass


# 文章更新模型
class ArticleUpdate(SQLModel):
    title: Optional[str] = Field(default=None, max_length=255)
    content: Optional[str] = Field(default=None)
    cover_image_url: Optional[str] = Field(default=None, max_length=255)
    type: Optional[ArticleType] = Field(default=None)
    status: Optional[ArticleStatus] = Field(default=None)


# 文章数据库模型
class Article(ArticleBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", description="作者ID")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # 关系
    author: Optional[User] = Relationship(back_populates="articles")
    comments: list["Comment"] = Relationship(back_populates="article", cascade_delete=True)
    likes: list["Like"] = Relationship(back_populates="article", cascade_delete=True)


# 文章公开模型
class ArticlePublic(ArticleBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    author_name: Optional[str] = Field(default=None, description="作者姓名")
    author_avatar_url: Optional[str] = Field(default=None, description="作者头像URL")


# 文章列表响应模型
class ArticlesPublic(SQLModel):
    data: list[ArticlePublic]
    count: int
    is_more: bool


# 社区任务基础模型
class CommunityTaskBase(SQLModel):
    title: str = Field(max_length=255, description="任务标题")
    description: str = Field(description="任务详细描述")
    task_type: CommunityTaskType = Field(description="任务类型")
    status: CommunityTaskStatus = Field(default=CommunityTaskStatus.OPEN, description="任务状态")
    reward_info: Optional[str] = Field(default=None, max_length=255, description="任务报酬描述")
    contact_info: Optional[str] = Field(default=None, max_length=255, description="联系方式")
    expiry_at: Optional[datetime] = Field(default=None, description="任务过期时间")


# 社区任务创建模型
class CommunityTaskCreate(CommunityTaskBase):
    pass


# 社区任务更新模型
class CommunityTaskUpdate(SQLModel):
    title: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = Field(default=None)
    task_type: Optional[CommunityTaskType] = Field(default=None)
    status: Optional[CommunityTaskStatus] = Field(default=None)
    reward_info: Optional[str] = Field(default=None, max_length=255)
    contact_info: Optional[str] = Field(default=None, max_length=255)
    expiry_at: Optional[datetime] = Field(default=None)


# 社区任务数据库模型
class CommunityTask(CommunityTaskBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", description="任务发布者ID")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # 关系
    publisher: Optional[User] = Relationship(back_populates="community_tasks")
    applications: list["TaskApplication"] = Relationship(back_populates="task", cascade_delete=True)


# 社区任务公开模型
class CommunityTaskPublic(CommunityTaskBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    publisher_name: Optional[str] = Field(default=None, description="发布者姓名")
    publisher_avatar_url: Optional[str] = Field(default=None, description="发布者头像URL")
    application_count: int = Field(default=0, description="申请数量")


# 社区任务列表响应模型
class CommunityTasksPublic(SQLModel):
    data: list[CommunityTaskPublic]
    count: int
    is_more: bool


# 任务申请基础模型
class TaskApplicationBase(SQLModel):
    status: ApplicationStatus = Field(default=ApplicationStatus.PENDING, description="申请状态")
    apply_message: Optional[str] = Field(default=None, max_length=500, description="申请时附带的消息")


# 任务申请创建模型
class TaskApplicationCreate(TaskApplicationBase):
    task_id: uuid.UUID = Field(description="申请的任务ID")


# 任务申请更新模型
class TaskApplicationUpdate(SQLModel):
    status: Optional[ApplicationStatus] = Field(default=None)
    apply_message: Optional[str] = Field(default=None, max_length=500)


# 任务申请数据库模型
class TaskApplication(TaskApplicationBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    task_id: uuid.UUID = Field(foreign_key="communitytask.id", description="申请的任务ID")
    applicant_id: uuid.UUID = Field(foreign_key="user.id", description="申请人ID")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # 关系
    task: Optional[CommunityTask] = Relationship(back_populates="applications")
    applicant: Optional[User] = Relationship(back_populates="task_applications")


# 任务申请公开模型
class TaskApplicationPublic(TaskApplicationBase):
    id: uuid.UUID
    task_id: uuid.UUID
    applicant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    applicant_name: Optional[str] = Field(default=None, description="申请人姓名")
    applicant_avatar_url: Optional[str] = Field(default=None, description="申请人头像URL")


# 任务申请列表响应模型
class TaskApplicationsPublic(SQLModel):
    data: list[TaskApplicationPublic]
    count: int
    is_more: bool


# 评论基础模型
class CommentBase(SQLModel):
    content: str = Field(description="评论内容")
    parent_id: Optional[uuid.UUID] = Field(default=None, description="回复的评论ID")


# 评论创建模型
class CommentCreate(CommentBase):
    article_id: uuid.UUID = Field(description="评论所属的文章ID")


# 评论数据库模型
class Comment(CommentBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    article_id: uuid.UUID = Field(foreign_key="article.id", description="评论所属的文章ID")
    user_id: uuid.UUID = Field(foreign_key="user.id", description="评论者ID")
    parent_id: Optional[uuid.UUID] = Field(default=None, foreign_key="comment.id", description="回复的评论ID")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # 关系
    article: Optional[Article] = Relationship(back_populates="comments")
    author: Optional[User] = Relationship(back_populates="comments")
    parent: Optional["Comment"] = Relationship(
        back_populates="replies", 
        sa_relationship_kwargs={
            "foreign_keys": "[Comment.parent_id]",
            "remote_side": "[Comment.id]"
        }
    )
    replies: list["Comment"] = Relationship(
        back_populates="parent",
        sa_relationship_kwargs={
            "foreign_keys": "[Comment.parent_id]"
        }
    )


# 评论公开模型
class CommentPublic(CommentBase):
    id: uuid.UUID
    article_id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    author_name: Optional[str] = Field(default=None, description="评论者姓名")
    author_avatar_url: Optional[str] = Field(default=None, description="评论者头像URL")
    reply_count: int = Field(default=0, description="回复数量")


# 评论列表响应模型
class CommentsPublic(SQLModel):
    data: list[CommentPublic]
    count: int
    is_more: bool


# 点赞记录数据库模型
class Like(SQLModel, table=True):
    user_id: uuid.UUID = Field(foreign_key="user.id", primary_key=True, description="点赞用户ID")
    article_id: uuid.UUID = Field(foreign_key="article.id", primary_key=True, description="被点赞的文章ID")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="点赞时间")
    
    # 关系
    user: Optional[User] = Relationship(back_populates="likes")
    article: Optional[Article] = Relationship(back_populates="likes")


# 点赞记录公开模型
class LikePublic(SQLModel):
    user_id: uuid.UUID
    article_id: uuid.UUID
    created_at: datetime
    user_name: Optional[str] = Field(default=None, description="点赞用户姓名")
    user_avatar_url: Optional[str] = Field(default=None, description="点赞用户头像URL")


# 点赞记录列表响应模型
class LikesPublic(SQLModel):
    data: list[LikePublic]
    count: int
    is_more: bool


# ============ 地址管理模型 ============

# 地址基础模型
class AddressBase(SQLModel):
    receiver_name: str = Field(max_length=50, description="收货人姓名")
    receiver_phone: str = Field(max_length=20, description="收货人电话")
    province: str = Field(max_length=50, description="省份")
    city: str = Field(max_length=50, description="城市")
    district: str = Field(max_length=50, description="区/县")
    street: str = Field(max_length=255, description="街道地址")
    detail_address: str = Field(max_length=500, description="详细地址")
    postal_code: Optional[str] = Field(default=None, max_length=10, description="邮编")
    is_default: bool = Field(default=False, description="是否默认地址")


# 地址创建模型
class AddressCreate(AddressBase):
    pass


# 地址更新模型
class AddressUpdate(SQLModel):
    receiver_name: Optional[str] = Field(default=None, max_length=50, description="收货人姓名")
    receiver_phone: Optional[str] = Field(default=None, max_length=20, description="收货人电话")
    province: Optional[str] = Field(default=None, max_length=50, description="省份")
    city: Optional[str] = Field(default=None, max_length=50, description="城市")
    district: Optional[str] = Field(default=None, max_length=50, description="区/县")
    street: Optional[str] = Field(default=None, max_length=255, description="街道地址")
    detail_address: Optional[str] = Field(default=None, max_length=500, description="详细地址")
    postal_code: Optional[str] = Field(default=None, max_length=10, description="邮编")
    is_default: Optional[bool] = Field(default=None, description="是否默认地址")


# 地址数据库模型
class Address(AddressBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", nullable=False, ondelete="CASCADE", description="用户ID")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新时间")
    
    # 关系
    user: Optional[User] = Relationship(back_populates="addresses")


# 地址公开模型
class AddressPublic(AddressBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# 地址列表响应模型
class AddressListResponse(SQLModel):
    data: list[AddressPublic]
    total: int
    page: int
    page_size: int


# ============ 积分商城模型 ============

# 积分商品分类枚举
class PointsProductCategoryType(str, Enum):
    DATA_PACKAGE = "data_package"  # 流量包
    MEMBERSHIP_CARD = "membership_card"  # 会员卡
    COUPON = "coupon"  # 优惠券
    MOVIE_TICKET = "movie_ticket"  # 电影票
    PHYSICAL_PRODUCT = "physical_product"  # 实物商品


# 积分商品展示标签枚举
class PointsProductLabel(str, Enum):
    POPULAR_RECOMMEND = "popular_recommend"  # 人气推荐
    GUESS_YOU_LIKE = "guess_you_like"  # 猜你喜欢
    FRESH_GOODS = "fresh_goods"  # 新鲜好物
    HOT_SALE = "hot_sale"  # 热销
    LIMITED_TIME = "limited_time"  # 限时特惠
    NEW_ARRIVAL = "new_arrival"  # 新品
    BEST_VALUE = "best_value"  # 超值
    EXCLUSIVE = "exclusive"  # 专享


# 积分商品分类表
class PointsProductCategoryBase(SQLModel):
    name: str = Field(max_length=50, description="分类名称")
    category_type: PointsProductCategoryType = Field(description="分类类型")
    icon_url: Optional[str] = Field(default=None, max_length=500, description="分类图标URL")
    sort_order: int = Field(default=0, description="排序顺序")
    is_active: bool = Field(default=True, description="是否启用")
    description: Optional[str] = Field(default=None, max_length=255, description="分类描述")


class PointsProductCategoryCreate(PointsProductCategoryBase):
    pass


class PointsProductCategoryUpdate(SQLModel):
    name: Optional[str] = Field(default=None, max_length=50)
    category_type: Optional[PointsProductCategoryType] = Field(default=None)
    icon_url: Optional[str] = Field(default=None, max_length=500)
    sort_order: Optional[int] = Field(default=None)
    is_active: Optional[bool] = Field(default=None)
    description: Optional[str] = Field(default=None, max_length=255)


class PointsProductCategory(PointsProductCategoryBase, table=True):
    __tablename__ = "points_product_category"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新时间")
    
    # 关系
    products: list["PointsProduct"] = Relationship(back_populates="category", cascade_delete=True)


class PointsProductCategoryPublic(PointsProductCategoryBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class PointsProductCategoriesPublic(SQLModel):
    data: list[PointsProductCategoryPublic]


# 积分商品表
class PointsProductBase(SQLModel):
    name: str = Field(max_length=255, description="商品名称")
    description: Optional[str] = Field(default=None, description="商品描述")
    image_url: str = Field(max_length=500, description="商品主图URL")
    images: Optional[str] = Field(default=None, description="商品多图JSON数组")
    category_id: uuid.UUID = Field(foreign_key="points_product_category.id", description="分类ID")
    points_required: int = Field(gt=0, description="所需积分数")
    original_price: Optional[float] = Field(default=None, ge=0, description="原价（用于显示）")
    total_quantity: int = Field(default=-1, ge=-1, description="总库存数量（-1表示无限）")
    exchanged_quantity: int = Field(default=0, ge=0, description="已兑换数量")
    stock_quantity: int = Field(default=0, ge=0, description="当前库存数量")
    is_active: bool = Field(default=True, description="是否上架")
    sort_order: int = Field(default=0, description="排序顺序")
    start_time: Optional[datetime] = Field(default=None, description="上架开始时间")
    end_time: Optional[datetime] = Field(default=None, description="下架结束时间")
    max_exchange_per_user: int = Field(default=-1, ge=-1, description="每用户限兑次数（-1表示无限制）")
    min_points_balance: int = Field(default=0, ge=0, description="兑换所需最低积分余额")
    tags: Optional[str] = Field(default=None, max_length=255, description="标签，逗号分隔")
    label: Optional["PointsProductLabel"] = Field(default=None, description="展示标签（用于app内展示不同样式）")
    detail_info: Optional[str] = Field(default=None, description="详细信息JSON")
    usage_instructions: Optional[str] = Field(default=None, description="使用说明")


class PointsProductCreate(PointsProductBase):
    pass


class PointsProductUpdate(SQLModel):
    name: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = Field(default=None)
    image_url: Optional[str] = Field(default=None, max_length=500)
    images: Optional[str] = Field(default=None)
    category_id: Optional[uuid.UUID] = Field(default=None)
    points_required: Optional[int] = Field(default=None, gt=0)
    original_price: Optional[float] = Field(default=None, ge=0)
    total_quantity: Optional[int] = Field(default=None, ge=-1)
    is_active: Optional[bool] = Field(default=None)
    sort_order: Optional[int] = Field(default=None)
    start_time: Optional[datetime] = Field(default=None)
    end_time: Optional[datetime] = Field(default=None)
    max_exchange_per_user: Optional[int] = Field(default=None, ge=-1)
    min_points_balance: Optional[int] = Field(default=None, ge=0)
    tags: Optional[str] = Field(default=None, max_length=255)
    label: Optional["PointsProductLabel"] = Field(default=None, description="展示标签")
    detail_info: Optional[str] = Field(default=None)
    usage_instructions: Optional[str] = Field(default=None)


class PointsProduct(PointsProductBase, table=True):
    __tablename__ = "points_product"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新时间")
    
    # label 字段需要特殊处理，使用枚举值而不是枚举名称
    # 由于数据库中存储的是枚举值（如 'popular_recommend'），我们需要使用字符串类型
    # 然后在应用层进行转换
    label: Optional["PointsProductLabel"] = Field(
        default=None,
        description="展示标签（用于app内展示不同样式）",
        sa_column=Column(
            SQLEnum(
                PointsProductLabel,
                name="pointsproductlabel",
                native_enum=True,
                values_callable=lambda x: [e.value for e in PointsProductLabel]
            ),
            nullable=True
        )
    )
    
    # 关系
    category: Optional[PointsProductCategory] = Relationship(back_populates="products")
    exchanges: list["PointsProductExchange"] = Relationship(back_populates="product", cascade_delete=True)


class PointsProductPublic(PointsProductBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    category_name: Optional[str] = Field(default=None, description="分类名称")


class PointsProductsPublic(SQLModel):
    data: list[PointsProductPublic]
    total: int
    page: int
    page_size: int


class PointsProductHotProductsPublic(SQLModel):
    data: list[PointsProductPublic]


# 兑换状态枚举
class ExchangeStatus(str, Enum):
    PENDING = "pending"  # 待发放
    ISSUED = "issued"  # 已发放
    USED = "used"  # 已使用
    EXPIRED = "expired"  # 已过期
    REFUNDED = "refunded"  # 已退款
    CANCELLED = "cancelled"  # 已取消


# 积分商品兑换记录表
class PointsProductExchangeBase(SQLModel):
    user_id: uuid.UUID = Field(foreign_key="user.id", description="用户ID")
    product_id: uuid.UUID = Field(foreign_key="points_product.id", description="商品ID")
    quantity: int = Field(gt=0, description="兑换数量")
    points_used: int = Field(gt=0, description="消耗积分")
    status: ExchangeStatus = Field(default=ExchangeStatus.PENDING, description="兑换状态")
    exchange_code: Optional[str] = Field(default=None, max_length=100, unique=True, index=True, description="兑换码/订单号")
    issued_at: Optional[datetime] = Field(default=None, description="发放时间")
    used_at: Optional[datetime] = Field(default=None, description="使用时间")
    expired_at: Optional[datetime] = Field(default=None, description="过期时间")
    refunded_at: Optional[datetime] = Field(default=None, description="退款时间")
    recipient_info: Optional[str] = Field(default=None, description="收货信息JSON（实物商品需要）")
    product_snapshot: Optional[str] = Field(default=None, description="商品快照JSON")
    notes: Optional[str] = Field(default=None, max_length=500, description="备注")


class PointsProductExchangeCreate(PointsProductExchangeBase):
    pass


class PointsProductExchangeUpdate(SQLModel):
    status: Optional[ExchangeStatus] = Field(default=None)
    exchange_code: Optional[str] = Field(default=None, max_length=100)
    issued_at: Optional[datetime] = Field(default=None)
    used_at: Optional[datetime] = Field(default=None)
    expired_at: Optional[datetime] = Field(default=None)
    refunded_at: Optional[datetime] = Field(default=None)
    recipient_info: Optional[str] = Field(default=None)
    notes: Optional[str] = Field(default=None, max_length=500)


class PointsProductExchange(PointsProductExchangeBase, table=True):
    __tablename__ = "points_product_exchange"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, description="兑换时间")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新时间")
    
    # 关系
    user: Optional[User] = Relationship(back_populates="points_product_exchanges")
    product: Optional[PointsProduct] = Relationship(back_populates="exchanges")


class PointsProductExchangePublic(PointsProductExchangeBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    product_name: Optional[str] = Field(default=None, description="商品名称")
    product_image_url: Optional[str] = Field(default=None, description="商品图片")
    tags: list[str] = Field(default_factory=list, description="标签列表")


class PointsProductExchangesPublic(SQLModel):
    data: list[PointsProductExchangePublic]
    total: int
    page: int
    page_size: int