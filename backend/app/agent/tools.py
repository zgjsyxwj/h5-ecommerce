import json

from sqlalchemy import or_, select

from app.database import SessionLocal
from app.models import Order, Product


def list_products() -> list[dict]:
    """列出商城全部在售商品。"""
    with SessionLocal() as db:
        rows = db.scalars(select(Product)).all()
        return [
            {
                "id": p.id,
                "name": p.name,
                "sku": p.sku,
                "stock": p.stock,
                "price": str(p.price),
                "image_url": p.image_url,
            }
            for p in rows
        ]


def get_product_info(query: str) -> list[dict]:
    """按商品名称或 SKU 模糊查询商品。"""
    pattern = f"%{query}%"
    with SessionLocal() as db:
        rows = db.scalars(
            select(Product).where(or_(Product.name.like(pattern), Product.sku.like(pattern)))
        ).all()
        return [
            {
                "id": p.id,
                "name": p.name,
                "sku": p.sku,
                "stock": p.stock,
                "price": str(p.price),
                "image_url": p.image_url,
            }
            for p in rows
        ]


def lookup_orders(username: str) -> list[dict]:
    """按用户名列出该用户的所有订单概要（不含完整物流时间线）。"""
    with SessionLocal() as db:
        rows = db.scalars(select(Order).where(Order.username == username)).all()
        result = []
        for o in rows:
            logistics = json.loads(o.logistics_info)
            result.append({
                "order_id": o.id,
                "product_name": o.product_name,
                "product_sku": o.product_sku,
                "quantity": o.quantity,
                "unit_price": str(o.unit_price),
                "total_amount": str(o.total_amount),
                "current_status": logistics.get("current_status"),
                "tracking_no": logistics.get("tracking_no"),
                "courier": logistics.get("courier"),
            })
        return result
