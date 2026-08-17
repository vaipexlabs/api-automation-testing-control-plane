"""Deterministic payload factories for valid and invalid API scenarios."""

from dataclasses import dataclass

from vaipex_api_automation.models import OrderStatus, Priority


@dataclass(slots=True)
class OrderPayloadFactory:
    sequence: int = 400

    def valid(
        self,
        *,
        quantity: int = 2,
        priority: Priority = Priority.STANDARD,
    ) -> dict[str, object]:
        self.sequence += 1
        return {
            "product_id": f"product-{self.sequence:03d}",
            "quantity": quantity,
            "priority": priority.value,
        }

    def minimum(self) -> dict[str, object]:
        return self.valid(quantity=1)

    def maximum(self) -> dict[str, object]:
        return self.valid(quantity=100, priority=Priority.EXPEDITED)

    def replacement(
        self, *, status: OrderStatus = OrderStatus.PROCESSING
    ) -> dict[str, object]:
        return {**self.valid(), "status": status.value}

    @staticmethod
    def patch(**changes: object) -> dict[str, object]:
        return changes

    @staticmethod
    def malformed() -> dict[str, object]:
        return {
            "product_id": "not-a-product",
            "quantity": 0,
            "priority": "impossible",
            "unexpected": True,
        }
