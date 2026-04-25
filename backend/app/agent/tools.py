from sqlalchemy import or_, select

from app.database import SessionLocal
from app.models import Product


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
