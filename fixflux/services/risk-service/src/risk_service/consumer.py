import json
from datetime import datetime, timezone

from kafka import KafkaConsumer

from risk_service import config
from risk_service.checker import RiskChecker
from risk_service.models import RejectedOrderEvent, TradeEvent, ValidatedOrder
from risk_service.position_store import PositionStore
from risk_service.producer import RiskProducer
from risk_service.utils.logger import configure_logging, get_logger
from shared.observability.tracing import extract_ctx, init_tracer

configure_logging()
logger = get_logger(__name__)

_tracer = init_tracer("risk-service")


def _build_checker() -> RiskChecker:
    return RiskChecker(
        notional_limit=config.NOTIONAL_LIMIT,
        fat_finger_pct=config.FAT_FINGER_PCT,
        gross_position_limit=config.GROSS_POSITION_LIMIT,
        net_position_limit=config.NET_POSITION_LIMIT,
        max_open_orders=config.MAX_OPEN_ORDERS,
    )


def handle_trade(value: dict, store: PositionStore, last_prices: dict) -> None:
    try:
        trade = TradeEvent(**value)
        last_prices[trade.symbol] = trade.price
        store.fill_order(trade.buy_order_id)
        store.fill_order(trade.sell_order_id)
        logger.debug(
            f"trade {trade.trade_id} filled orders "
            f"{trade.buy_order_id}/{trade.sell_order_id}"
        )
    except Exception as e:
        logger.warning(f"could not process trade: {e}")


def handle_order(
    value: dict,
    checker: RiskChecker,
    store: PositionStore,
    last_prices: dict,
    producer: RiskProducer,
) -> None:
    try:
        order = ValidatedOrder(**value)
        decision = checker.check_all(order, store, last_prices)
        notional = float(order.price) * int(order.quantity)
        last_price = last_prices.get(order.symbol, 0.0)
        if decision.approved:
            store.record_open_order(
                order.order_id,
                order.client_id,
                order.symbol,
                order.side,
                order.quantity,
            )
            producer.approve(value)
            logger.info(
                f"pre_trade_decision | order={order.order_id} client={order.client_id}"
                f" symbol={order.symbol} side={order.side} qty={order.quantity}"
                f" price={order.price} notional={notional:.2f} last_price={last_price}"
                f" decision=APPROVED"
            )
        else:
            rejection = RejectedOrderEvent(
                order_id=order.order_id,
                client_id=order.client_id,
                symbol=order.symbol,
                side=order.side,
                price=order.price,
                quantity=order.quantity,
                reason=decision.reason or "",
                timestamp=datetime.now(timezone.utc),
            )
            producer.reject(rejection.model_dump(mode="json"))
            logger.warning(
                f"pre_trade_decision | order={order.order_id} client={order.client_id}"
                f" symbol={order.symbol} side={order.side} qty={order.quantity}"
                f" price={order.price} notional={notional:.2f} last_price={last_price}"
                f" decision=REJECTED reason={decision.reason!r}"
            )
    except Exception as e:
        logger.error(f"error processing order: {e}")


def run() -> None:
    consumer = KafkaConsumer(
        config.INPUT_TOPIC,
        config.TRADES_TOPIC,
        bootstrap_servers=config.KAFKA_BROKER,
        group_id=config.GROUP_ID,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    )
    checker = _build_checker()
    store = PositionStore()
    last_prices: dict = {}
    producer = RiskProducer()

    logger.info("risk-service started")

    for msg in consumer:
        ctx = extract_ctx(msg.value)
        span_name = f"risk-service.{msg.topic}"
        with _tracer.start_as_current_span(span_name, context=ctx) as span:
            span.set_attribute("kafka.topic", msg.topic)
            if msg.topic == config.TRADES_TOPIC:
                handle_trade(msg.value, store, last_prices)
            else:
                span.set_attribute("order.id", str(msg.value.get("order_id", "")))
                span.set_attribute("order.symbol", str(msg.value.get("symbol", "")))
                handle_order(msg.value, checker, store, last_prices, producer)


if __name__ == "__main__":
    run()
