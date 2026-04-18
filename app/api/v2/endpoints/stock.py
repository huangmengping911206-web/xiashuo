# app/api/v2/endpoints/stock.py
# A股分析模块 - 用户端 API（需要登录）

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from app.database.session import get_session
from app.database.schemas.stock import (
    WatchlistAdd, WatchlistOut,
    PredictionOut, BoardResponse, AccuracyStats
)
from app.services.stock_service import StockService, PredictionService, BacktestService
from app.core.logging import logger

import httpx

router = APIRouter()

# Finance API 配置
FINANCE_API_BASE = "https://internal-api.z.ai/external/finance/v1"
FINANCE_HEADERS = {"X-Z-AI-From": "Z"}


async def _fetch_stock_quotes(symbols: List[str]) -> dict:
    """从 Finance API 批量获取实时行情"""
    if not symbols:
        return {}
    try:
        ticker_str = ",".join(symbols)
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{FINANCE_API_BASE}/markets/stock/quotes",
                params={"ticker": ticker_str},
                headers=FINANCE_HEADERS,
            )
            data = resp.json()
            body = data.get("body", [])
            return {item["symbol"]: item for item in body}
    except Exception as e:
        logger.error(f"[Stock API] 获取行情失败: {e}")
        return {}


async def _search_stocks(keyword: str) -> list:
    """从 Finance API 搜索股票"""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{FINANCE_API_BASE}/markets/search",
                params={"search": keyword},
                headers=FINANCE_HEADERS,
            )
            data = resp.json()
            body = data.get("body", [])
            # 过滤出 A 股（.SS 上交所 / .SZ 深交所）
            results = []
            for item in body:
                sym = item.get("symbol", "")
                if ".SS" in sym or ".SZ" in sym:
                    results.append({
                        "symbol": sym,
                        "name": item.get("shortname", item.get("longname", "")),
                        "exchange": item.get("exchDisp", ""),
                        "industry": item.get("industryDisp", ""),
                    })
            return results[:10]  # 最多返回10条
    except Exception as e:
        logger.error(f"[Stock API] 搜索股票失败: {e}")
        return []


@router.get("/search", summary="搜索股票")
async def search_stocks(keyword: str = Query(..., min_length=1, description="股票代码或名称")):
    """搜索 A 股股票，返回匹配结果"""
    results = await _search_stocks(keyword)
    return {"results": results}


@router.get("/board", response_model=BoardResponse, summary="股票看板")
async def get_stock_board(session: AsyncSession = Depends(get_session)):
    """
    获取股票看板数据：大盘指数 + 自选股行情 + 最新预判
    """
    # 1. 获取自选股列表
    watchlist = await StockService.get_watchlist(session)
    if not watchlist:
        return BoardResponse(indices=[], watchlist=[])

    symbols = [item.symbol for item in watchlist]

    # 2. 获取大盘指数
    index_symbols = ["000001.SS", "399001.SZ", "399006.SZ"]
    index_quotes = await _fetch_stock_quotes(index_symbols)
    indices = []
    index_names = {
        "000001.SS": "上证指数",
        "399001.SZ": "深证成指",
        "399006.SZ": "创业板指",
    }
    for sym in index_symbols:
        if sym in index_quotes:
            q = index_quotes[sym]
            indices.append({
                "symbol": sym,
                "name": index_names.get(sym, sym),
                "price": q.get("regularMarketPrice"),
                "change_pct": q.get("regularMarketChangePercent"),
                "volume": q.get("regularMarketVolume"),
            })

    # 3. 获取自选股实时行情
    all_symbols = symbols + [s for s in index_symbols if s not in symbols]
    quotes = await _fetch_stock_quotes(all_symbols)

    # 4. 获取最新预判
    predictions = await PredictionService.get_latest_predictions(session, symbols)

    # 5. 组装看板数据
    watchlist_items = []
    for wl in watchlist:
        q = quotes.get(wl.symbol, {})
        pred = predictions.get(wl.symbol)

        change_pct = q.get("regularMarketChangePercent")
        if isinstance(change_pct, dict):
            change_pct = change_pct.get("raw")

        price = q.get("regularMarketPrice")
        if isinstance(price, dict):
            price = price.get("raw")

        watchlist_items.append({
            "symbol": wl.symbol,
            "name": wl.name,
            "sort_order": wl.sort_order,
            "price": round(price, 2) if price else None,
            "change_pct": round(change_pct, 2) if change_pct else None,
            "volume": q.get("regularMarketVolume"),
            "day_high": q.get("regularMarketDayHigh"),
            "day_low": q.get("regularMarketDayLow"),
            "market_cap": q.get("marketCap"),
            "prediction": pred.prediction if pred else None,
            "magnitude_min": pred.magnitude_min if pred else None,
            "magnitude_max": pred.magnitude_max if pred else None,
            "magnitude_period": pred.magnitude_period if pred else None,
            "score": pred.score if pred else None,
            "entry_price": pred.entry_price if pred else None,
            "analysis_date": pred.analysis_date if pred else None,
        })

    return BoardResponse(indices=indices, watchlist=watchlist_items)


@router.get("/watchlist", response_model=List[WatchlistOut], summary="获取自选股列表")
async def get_watchlist(session: AsyncSession = Depends(get_session)):
    """获取自选股列表"""
    return await StockService.get_watchlist(session)


@router.post("/watchlist", response_model=WatchlistOut, summary="添加自选股")
async def add_to_watchlist(
    data: WatchlistAdd,
    session: AsyncSession = Depends(get_session),
):
    """添加股票到自选列表"""
    return await StockService.add_to_watchlist(session, data)


@router.delete("/watchlist/{symbol}", summary="删除自选股")
async def remove_from_watchlist(
    symbol: str,
    session: AsyncSession = Depends(get_session),
):
    """从自选列表删除股票"""
    return await StockService.remove_from_watchlist(session, symbol)


@router.get("/prediction/{symbol}", summary="获取股票预判详情")
async def get_prediction_detail(
    symbol: str,
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """
    获取某只股票的预判历史 + 最新预判详情 + 准确率统计
    """
    history = await PredictionService.get_prediction_history(session, symbol, limit)
    stats = await BacktestService.get_stats(session, period_days=30)

    return {
        "symbol": symbol,
        "latest": history[0].model_dump() if history else None,
        "history": [h.model_dump() for h in history],
        "stats": stats.model_dump(),
    }


@router.get("/stats", response_model=AccuracyStats, summary="获取准确率统计")
async def get_accuracy_stats(
    period: int = Query(30, ge=1, le=365, description="统计天数"),
    session: AsyncSession = Depends(get_session),
):
    """获取预判准确率统计"""
    return await BacktestService.get_stats(session, period_days=period)
