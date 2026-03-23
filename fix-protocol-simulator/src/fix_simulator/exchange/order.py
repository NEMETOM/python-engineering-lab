from dataclasses import dataclass

@dataclass
class Order:
    order_id: str
    side: str
    price: float
    quantity: int