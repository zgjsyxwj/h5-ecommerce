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


def get_order_detail(order_id: int) -> dict:
    """按订单 ID 查询订单详情，含完整物流时间线。

    若订单不存在，返回 {"error": "order_not_found", "order_id": <id>}。
    """
    with SessionLocal() as db:
        o = db.get(Order, order_id)
        if o is None:
            return {"error": "order_not_found", "order_id": order_id}
        logistics = json.loads(o.logistics_info)
        return {
            "order_id": o.id,
            "username": o.username,
            "product_name": o.product_name,
            "product_sku": o.product_sku,
            "quantity": o.quantity,
            "unit_price": str(o.unit_price),
            "total_amount": str(o.total_amount),
            "recipient": logistics.get("recipient"),
            "address": logistics.get("address"),
            "phone": logistics.get("phone"),
            "tracking_no": logistics.get("tracking_no"),
            "courier": logistics.get("courier"),
            "current_status": logistics.get("current_status"),
            "tracking_history": logistics.get("tracking_history", []),
        }
