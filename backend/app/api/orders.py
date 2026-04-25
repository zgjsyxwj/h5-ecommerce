from fastapi import APIRouter, HTTPException, Query

from app.agent.tools import get_order_detail, lookup_orders

router = APIRouter()


@router.get("/api/orders")
def get_orders(username: str = Query(..., min_length=1)) -> list[dict]:
    return lookup_orders(username)


@router.get("/api/orders/{order_id}")
def get_order(order_id: int) -> dict:
    result = get_order_detail(order_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=f"order {order_id} not found")
    return result
