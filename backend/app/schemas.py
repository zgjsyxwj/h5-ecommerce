from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, model_validator


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    sku: str
    stock: int
    price: Decimal
    image_url: str


class TrackingStatus(str, Enum):
    order_placed = "order_placed"
    shipped = "shipped"
    in_transit = "in_transit"
    delivered = "delivered"


class TrackingEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timestamp: str
    status: TrackingStatus
    location: str
    description: str


class LogisticsInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recipient: str
    address: str
    phone: str
    tracking_no: str
    courier: str
    current_status: TrackingStatus
    tracking_history: list[TrackingEvent]

    @model_validator(mode="after")
    def _check_history_consistency(self):
        if len(self.tracking_history) < 1:
            raise ValueError("tracking_history must contain at least 1 event")
        last_status = self.tracking_history[-1].status
        if self.current_status != last_status:
            raise ValueError(
                f"current_status ({self.current_status}) must match last tracking_history "
                f"event status ({last_status})"
            )
        return self
