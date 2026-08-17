"""Thread-safe deterministic in-memory order repository."""

from datetime import UTC, datetime, timedelta
from threading import RLock

from vaipex_api_automation.models import (
    Order,
    OrderCreate,
    OrderPatch,
    OrderReplace,
    OrderStatus,
    Principal,
    Priority,
    Role,
)

BASE_TIME = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


class OrderRepository:
    def __init__(self) -> None:
        self._lock = RLock()
        self.reset()

    def reset(self) -> int:
        with self._lock:
            self._sequence = 3
            self._clock_tick = 3
            self._orders = {
                "order-001": self._seed_order(
                    "order-001", "user-001", "product-101", 2, Priority.STANDARD, 0
                ),
                "order-002": self._seed_order(
                    "order-002", "user-002", "product-202", 1, Priority.EXPEDITED, 1
                ),
                "order-003": self._seed_order(
                    "order-003", "user-003", "product-303", 4, Priority.STANDARD, 2
                ),
            }
            return len(self._orders)

    def _seed_order(
        self,
        order_id: str,
        owner_id: str,
        product_id: str,
        quantity: int,
        priority: Priority,
        offset: int,
    ) -> Order:
        timestamp = BASE_TIME + timedelta(seconds=offset)
        return Order(
            order_id=order_id,
            owner_id=owner_id,
            product_id=product_id,
            quantity=quantity,
            priority=priority,
            status=OrderStatus.PENDING,
            version=1,
            created_at=timestamp,
            updated_at=timestamp,
        )

    def _timestamp(self) -> datetime:
        timestamp = BASE_TIME + timedelta(seconds=self._clock_tick)
        self._clock_tick += 1
        return timestamp

    @staticmethod
    def _can_access(principal: Principal, order: Order) -> bool:
        return principal.role is Role.ADMIN or order.owner_id == principal.subject

    def list_for(self, principal: Principal) -> list[Order]:
        with self._lock:
            return [
                order.model_copy(deep=True)
                for order in self._orders.values()
                if self._can_access(principal, order)
            ]

    def get_for(self, order_id: str, principal: Principal) -> Order | None:
        with self._lock:
            order = self._orders.get(order_id)
            if order is None or not self._can_access(principal, order):
                return None
            return order.model_copy(deep=True)

    def create(self, payload: OrderCreate, owner_id: str) -> Order:
        with self._lock:
            self._sequence += 1
            order_id = f"order-{self._sequence:03d}"
            timestamp = self._timestamp()
            order = Order(
                order_id=order_id,
                owner_id=owner_id,
                product_id=payload.product_id,
                quantity=payload.quantity,
                priority=payload.priority,
                status=OrderStatus.PENDING,
                version=1,
                created_at=timestamp,
                updated_at=timestamp,
            )
            self._orders[order_id] = order
            return order.model_copy(deep=True)

    def replace(
        self, order_id: str, payload: OrderReplace, principal: Principal
    ) -> Order | None:
        with self._lock:
            existing = self._orders.get(order_id)
            if existing is None or not self._can_access(principal, existing):
                return None
            requested_state = payload.model_dump()
            current_state = {
                "product_id": existing.product_id,
                "quantity": existing.quantity,
                "priority": existing.priority,
                "status": existing.status,
            }
            if requested_state == current_state:
                return existing.model_copy(deep=True)
            replacement = existing.model_copy(
                update={
                    **requested_state,
                    "version": existing.version + 1,
                    "updated_at": self._timestamp(),
                }
            )
            self._orders[order_id] = replacement
            return replacement.model_copy(deep=True)

    def patch(
        self, order_id: str, payload: OrderPatch, principal: Principal
    ) -> Order | None:
        with self._lock:
            existing = self._orders.get(order_id)
            if existing is None or not self._can_access(principal, existing):
                return None
            changes = payload.model_dump(exclude_none=True)
            changes.update(
                version=existing.version + 1,
                updated_at=self._timestamp(),
            )
            updated = existing.model_copy(update=changes)
            self._orders[order_id] = updated
            return updated.model_copy(deep=True)

    def delete(self, order_id: str, principal: Principal) -> bool:
        with self._lock:
            existing = self._orders.get(order_id)
            if existing is None or not self._can_access(principal, existing):
                return False
            del self._orders[order_id]
            return True
