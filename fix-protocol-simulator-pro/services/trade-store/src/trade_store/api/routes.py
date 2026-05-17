from fastapi import APIRouter, HTTPException
from trade_store.repository import TradeRepository
from trade_store.utils.logger import get_logger

router = APIRouter()

repo = TradeRepository()

logger = get_logger(__name__)


@router.get("/health")
def health():

    return {"status": "ok"}


@router.get("/trades")
def get_trades(symbol: str | None = None):

    trades = repo.get_all(symbol)

    logger.debug(f"fetched {len(trades)} trade(s) symbol={symbol}")

    return trades


@router.get("/trades/{trade_id}")
def get_trade(trade_id: str):

    trade = repo.get_by_id(trade_id)

    if not trade:

        logger.debug(f"trade not found {trade_id}")

        raise HTTPException(status_code=404, detail="trade not found")

    logger.debug(f"fetched trade {trade_id}")

    return trade
