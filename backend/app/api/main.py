from fastapi import APIRouter

from app.api.routes import items, login, private, users, utils, regions, phone_auth, hot_search, products, data_packages, membership_benefits, user_wallet, coupons, cart, orders, points, invitations, dialogs, lottery, discovery, service_account, address, points_mall, blindbox
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(phone_auth.router, prefix="/phone", tags=["phone-auth"])
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(items.router)
api_router.include_router(regions.router, tags=["regions"])
api_router.include_router(hot_search.router, prefix="/hot-search", tags=["hot-search"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(data_packages.router, prefix="/data-packages", tags=["data-packages"])
api_router.include_router(membership_benefits.router, prefix="/membership-benefits", tags=["membership-benefits"])
api_router.include_router(user_wallet.router, prefix="/wallet", tags=["user-wallet"])
api_router.include_router(coupons.router, prefix="/coupons", tags=["coupons"])
api_router.include_router(cart.router, prefix="/cart", tags=["cart"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
api_router.include_router(points.router, prefix="/points", tags=["points"])
api_router.include_router(invitations.router, prefix="/invitations", tags=["invitations"])
api_router.include_router(dialogs.router, prefix="/dialogs", tags=["dialogs"])
api_router.include_router(lottery.router, prefix="/lottery", tags=["lottery"])
api_router.include_router(discovery.router, prefix="/discovery", tags=["discovery"])
api_router.include_router(service_account.router, prefix="/service-accounts", tags=["service-accounts"])
api_router.include_router(address.router, prefix="/addresses", tags=["addresses"])
api_router.include_router(points_mall.router, prefix="/points-mall", tags=["points-mall"])
api_router.include_router(blindbox.router, prefix="/blindbox", tags=["blindbox"])


if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
