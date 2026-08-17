"""Versioned resource and identity models for the reference API."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Role(StrEnum):
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


class OrderStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"


class Priority(StrEnum):
    STANDARD = "standard"
    EXPEDITED = "expedited"


class Principal(BaseModel):
    subject: str
    role: Role


class OrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: str = Field(pattern=r"^product-[0-9]{3}$")
    quantity: int = Field(ge=1, le=100)
    priority: Priority = Priority.STANDARD


class OrderReplace(OrderCreate):
    status: OrderStatus


class OrderPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quantity: int | None = Field(default=None, ge=1, le=100)
    priority: Priority | None = None
    status: OrderStatus | None = None


class Order(BaseModel):
    order_id: str
    owner_id: str
    product_id: str
    quantity: int
    priority: Priority
    status: OrderStatus
    version: int
    created_at: datetime
    updated_at: datetime


class OrderCollection(BaseModel):
    items: list[Order]
    count: int


class Health(BaseModel):
    status: str
    service: str
    version: str


class ResetResult(BaseModel):
    restored_orders: int
    status: str
