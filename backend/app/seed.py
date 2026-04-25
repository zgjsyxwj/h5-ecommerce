from decimal import Decimal

from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.models import Order, Product
from app.schemas import LogisticsInfo

_UNSPLASH = "https://images.unsplash.com/photo-{id}?w=400&h=400&fit=crop&auto=format"

PRODUCT_SEED_DATA = [
    {"name": "蓝牙耳机·Pro",          "sku": "AUDIO-001",   "stock": 50,  "price": Decimal("299.00"), "image_url": _UNSPLASH.format(id="1505740420928-5e560c06d30e")},
    {"name": "智能手表·X7",           "sku": "WATCH-001",   "stock": 25,  "price": Decimal("899.00"), "image_url": _UNSPLASH.format(id="1523275335684-37898b6baf30")},
    {"name": "运动跑鞋·轻盈版",       "sku": "SHOE-001",    "stock": 80,  "price": Decimal("499.00"), "image_url": _UNSPLASH.format(id="1542291026-7eec264c27ff")},
    {"name": "机械键盘·87 键",        "sku": "KB-001",      "stock": 100, "price": Decimal("459.00"), "image_url": _UNSPLASH.format(id="1587829741301-dc798b83add3")},
    {"name": "无线鼠标·静音款",       "sku": "MOUSE-001",   "stock": 200, "price": Decimal("99.00"),  "image_url": _UNSPLASH.format(id="1527864550417-7fd91fc51a46")},
    {"name": "便携充电宝·20000mAh",   "sku": "POWER-001",   "stock": 60,  "price": Decimal("159.00"), "image_url": _UNSPLASH.format(id="1609091839311-d5365f9ff1c5")},
    {"name": "USB-C 数据线·三件装",   "sku": "CABLE-001",   "stock": 500, "price": Decimal("39.90"),  "image_url": _UNSPLASH.format(id="1583394838336-acd977736f90")},
    {"name": "智能音箱·小白",         "sku": "SPEAKER-001", "stock": 15,  "price": Decimal("599.00"), "image_url": _UNSPLASH.format(id="1543512214-318c7553f230")},
]


ORDER_SEED_DATA = [
    {
        "username": "alex",
        "product_sku": "AUDIO-001",
        "quantity": 2,
        "logistics": {
            "recipient": "张三",
            "address": "北京市朝阳区建国路88号",
            "phone": "13800138000",
            "tracking_no": "SF1234567890",
            "courier": "顺丰速运",
            "current_status": "delivered",
            "tracking_history": [
                {"timestamp": "2026-04-15T10:00:00", "status": "order_placed", "location": "北京",         "description": "订单已创建"},
                {"timestamp": "2026-04-16T14:30:00", "status": "shipped",      "location": "北京发货中心", "description": "已从仓库发出"},
                {"timestamp": "2026-04-17T09:15:00", "status": "in_transit",   "location": "上海中转中心", "description": "运输中"},
                {"timestamp": "2026-04-18T16:45:00", "status": "delivered",    "location": "上海市浦东新区", "description": "已签收"},
            ],
        },
    },
    {
        "username": "alex",
        "product_sku": "KB-001",
        "quantity": 1,
        "logistics": {
            "recipient": "张三",
            "address": "北京市朝阳区建国路88号",
            "phone": "13800138000",
            "tracking_no": "ZTO9876543210",
            "courier": "中通快递",
            "current_status": "in_transit",
            "tracking_history": [
                {"timestamp": "2026-04-22T11:00:00", "status": "order_placed", "location": "北京",         "description": "订单已创建"},
                {"timestamp": "2026-04-23T15:00:00", "status": "shipped",      "location": "北京发货中心", "description": "已从仓库发出"},
                {"timestamp": "2026-04-24T09:00:00", "status": "in_transit",   "location": "天津转运中心", "description": "运输中"},
            ],
        },
    },
    {
        "username": "tom",
        "product_sku": "WATCH-001",
        "quantity": 1,
        "logistics": {
            "recipient": "李四",
            "address": "上海市浦东新区世纪大道100号",
            "phone": "13900139000",
            "tracking_no": "YTO5555666677",
            "courier": "圆通速递",
            "current_status": "delivered",
            "tracking_history": [
                {"timestamp": "2026-04-10T08:30:00", "status": "order_placed", "location": "上海",          "description": "订单已创建"},
                {"timestamp": "2026-04-11T10:00:00", "status": "shipped",      "location": "上海发货中心",  "description": "已从仓库发出"},
                {"timestamp": "2026-04-12T18:20:00", "status": "in_transit",   "location": "上海市浦东新区", "description": "派送中"},
                {"timestamp": "2026-04-13T11:00:00", "status": "delivered",    "location": "上海市浦东新区", "description": "已签收"},
            ],
        },
    },
    {
        "username": "jerry",
        "product_sku": "MOUSE-001",
        "quantity": 3,
        "logistics": {
            "recipient": "王五",
            "address": "广州市天河区珠江新城88号",
            "phone": "13700137000",
            "tracking_no": "SF8888999900",
            "courier": "顺丰速运",
            "current_status": "shipped",
            "tracking_history": [
                {"timestamp": "2026-04-23T14:00:00", "status": "order_placed", "location": "广州",         "description": "订单已创建"},
                {"timestamp": "2026-04-24T09:30:00", "status": "shipped",      "location": "广州发货中心", "description": "已从仓库发出"},
            ],
        },
    },
    {
        "username": "jerry",
        "product_sku": "CABLE-001",
        "quantity": 5,
        "logistics": {
            "recipient": "王五",
            "address": "广州市天河区珠江新城88号",
            "phone": "13700137000",
            "tracking_no": "STO1111222233",
            "courier": "申通快递",
            "current_status": "delivered",
            "tracking_history": [
                {"timestamp": "2026-04-12T16:00:00", "status": "order_placed", "location": "广州",         "description": "订单已创建"},
                {"timestamp": "2026-04-13T10:30:00", "status": "shipped",      "location": "广州发货中心", "description": "已从仓库发出"},
                {"timestamp": "2026-04-14T14:00:00", "status": "in_transit",   "location": "深圳转运中心", "description": "运输中"},
                {"timestamp": "2026-04-16T09:45:00", "status": "delivered",    "location": "广州市天河区", "description": "已签收"},
            ],
        },
    },
]


def seed_products(db: Session) -> None:
    if db.query(Product).count() > 0:
        return
    for item in PRODUCT_SEED_DATA:
        db.add(Product(**item))
    db.commit()


def init_database() -> None:
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        seed_products(db)
        seed_orders(db)
    finally:
        db.close()


def seed_orders(db: Session) -> None:
    if db.query(Order).count() > 0:
        return
    for item in ORDER_SEED_DATA:
        product = db.query(Product).filter_by(sku=item["product_sku"]).one()
        quantity = item["quantity"]
        logistics = LogisticsInfo.model_validate(item["logistics"])
        db.add(
            Order(
                username=item["username"],
                product_sku=product.sku,
                product_name=product.name,
                unit_price=product.price,
                quantity=quantity,
                total_amount=product.price * quantity,
                logistics_info=logistics.model_dump_json(),
            )
        )
    db.commit()
