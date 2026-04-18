# app/services/stock_service.py
# A股分析模块 - 业务逻辑

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from typing import Optional, List
from datetime import datetime, date, timedelta

from app.database.models.stock import StockWatchlist, StockPrediction, StockBacktest
from app.database.schemas.stock import (
    WatchlistAdd, WatchlistOut,
    PredictionCreate, PredictionOut,
    BacktestCreate, BacktestOut,
    AccuracyStats, WatchlistItemWithPrediction, BoardResponse
)
from app.core.logging import logger


class StockService:
    """自选股服务"""

    @staticmethod
    async def get_watchlist(session: AsyncSession) -> List[WatchlistOut]:
        """获取自选股列表"""
        result = await session.execute(
            select(StockWatchlist).order_by(StockWatchlist.sort_order, StockWatchlist.id)
        )
        items = result.scalars().all()
        return [WatchlistOut.model_validate(item) for item in items]

    @staticmethod
    async def add_to_watchlist(session: AsyncSession, data: WatchlistAdd) -> WatchlistOut:
        """添加自选股"""
        # 检查是否已存在
        existing = await session.execute(
            select(StockWatchlist).where(StockWatchlist.symbol == data.symbol)
        )
        if existing.scalar_one_or_none():
            from fastapi import HTTPException
            raise HTTPException(status_code=409, detail="该股票已在自选列表中")

        item = StockWatchlist(
            symbol=data.symbol,
            name=data.name,
            sort_order=data.sort_order,
        )
        session.add(item)
        await session.commit()
        await session.refresh(item)
        return WatchlistOut.model_validate(item)

    @staticmethod
    async def remove_from_watchlist(session: AsyncSession, symbol: str) -> dict:
        """删除自选股"""
        result = await session.execute(
            select(StockWatchlist).where(StockWatchlist.symbol == symbol)
        )
        item = result.scalar_one_or_none()
        if not item:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="自选股不存在")

        await session.delete(item)
        await session.commit()
        return {"message": "删除成功"}

    @staticmethod
    async def get_symbols(session: AsyncSession) -> List[str]:
        """获取所有自选股代码"""
        result = await session.execute(select(StockWatchlist.symbol))
        return [row[0] for row in result.all()]


class PredictionService:
    """预判服务"""

    @staticmethod
    async def create_prediction(session: AsyncSession, data: PredictionCreate) -> PredictionOut:
        """创建预判记录"""
        prediction = StockPrediction(
            symbol=data.symbol,
            name=data.name,
            analysis_date=data.analysis_date,
            analysis_type=data.analysis_type,
            prediction=data.prediction,
            magnitude_min=data.magnitude_min,
            magnitude_max=data.magnitude_max,
            magnitude_period=data.magnitude_period,
            score=data.score,
            entry_price=data.entry_price,
            support_price=data.support_price,
            resistance_price=data.resistance_price,
            scores_detail=data.scores_detail,
            fundamental=data.fundamental,
            industry=data.industry,
            news=data.news,
            technical=data.technical,
            capital=data.capital,
            risk=data.risk,
            reasons=data.reasons,
            tweet_id=data.tweet_id,
        )
        session.add(prediction)
        await session.commit()
        await session.refresh(prediction)
        return PredictionOut.model_validate(prediction)

    @staticmethod
    async def get_latest_predictions(
        session: AsyncSession, symbols: Optional[List[str]] = None
    ) -> dict:
        """获取自选股的最新预判（每只股票取最新一条）"""
        if not symbols:
            return {}

        # 子查询：每只股票最新的预判 ID
        latest_subq = (
            select(
                StockPrediction.symbol,
                func.max(StockPrediction.id).label("latest_id")
            )
            .where(StockPrediction.symbol.in_(symbols))
            .group_by(StockPrediction.symbol)
            .subquery()
        )

        result = await session.execute(
            select(StockPrediction)
            .join(
                latest_subq,
                and_(
                    StockPrediction.symbol == latest_subq.c.symbol,
                    StockPrediction.id == latest_subq.c.latest_id,
                )
            )
        )
        predictions = result.scalars().all()
        return {p.symbol: PredictionOut.model_validate(p) for p in predictions}

    @staticmethod
    async def get_prediction_history(
        session: AsyncSession, symbol: str, limit: int = 20
    ) -> List[PredictionOut]:
        """获取某只股票的预判历史"""
        result = await session.execute(
            select(StockPrediction)
            .where(StockPrediction.symbol == symbol)
            .order_by(desc(StockPrediction.created_at))
            .limit(limit)
        )
        items = result.scalars().all()
        return [PredictionOut.model_validate(item) for item in items]


class BacktestService:
    """回测服务"""

    @staticmethod
    async def create_backtest(session: AsyncSession, data: BacktestCreate) -> BacktestOut:
        """创建回测记录"""
        backtest = StockBacktest(
            prediction_id=data.prediction_id,
            symbol=data.symbol,
            check_period=data.check_period,
            actual_price=data.actual_price,
            actual_change_pct=data.actual_change_pct,
            predicted_min=data.predicted_min,
            predicted_max=data.predicted_max,
            predicted_direction=data.predicted_direction,
            is_correct=data.is_correct,
            is_direction_correct=data.is_direction_correct,
        )
        session.add(backtest)
        await session.commit()
        await session.refresh(backtest)
        return BacktestOut.model_validate(backtest)

    @staticmethod
    async def get_stats(session: AsyncSession, period_days: int = 30) -> AccuracyStats:
        """获取准确率统计"""
        cutoff = datetime.utcnow() - timedelta(days=period_days)

        result = await session.execute(
            select(StockBacktest).where(StockBacktest.checked_at >= cutoff)
        )
        backtests = result.scalars().all()

        if not backtests:
            return AccuracyStats()

        total = len(backtests)
        correct = sum(1 for b in backtests if b.is_correct)
        dir_correct = sum(1 for b in backtests if b.is_direction_correct)
        avg_change = sum(b.actual_change_pct or 0 for b in backtests) / total

        bullish = [b for b in backtests if b.predicted_direction == "看涨"]
        bearish = [b for b in backtests if b.predicted_direction == "看跌"]
        neutral = [b for b in backtests if b.predicted_direction == "中性"]

        # 按周期统计
        by_period = {}
        for period in ["T+1", "T+5", "T+20"]:
            period_items = [b for b in backtests if b.check_period == period]
            if period_items:
                p_total = len(period_items)
                p_correct = sum(1 for b in period_items if b.is_correct)
                by_period[period] = {
                    "total": p_total,
                    "correct": p_correct,
                    "accuracy": round(p_correct / p_total * 100, 1),
                }

        return AccuracyStats(
            total_count=total,
            correct_count=correct,
            accuracy_rate=round(correct / total * 100, 1),
            direction_correct_count=dir_correct,
            direction_accuracy_rate=round(dir_correct / total * 100, 1),
            avg_actual_change=round(avg_change, 2),
            bullish_count=len(bullish),
            bullish_correct=sum(1 for b in bullish if b.is_correct),
            bearish_count=len(bearish),
            bearish_correct=sum(1 for b in bearish if b.is_correct),
            neutral_count=len(neutral),
            neutral_correct=sum(1 for b in neutral if b.is_correct),
            by_period=by_period,
        )

    @staticmethod
    async def get_pending_backtests(session: AsyncSession) -> List[dict]:
        """获取待回测的预判（已到期的 T+1/T+5/T+20）"""
        today = date.today()
        periods = {
            "T+1": today - timedelta(days=1),
            "T+5": today - timedelta(days=5),
            "T+20": today - timedelta(days=20),
        }

        pending = []
        for period_name, target_date in periods.items():
            result = await session.execute(
                select(StockPrediction).where(
                    StockPrediction.analysis_date == target_date
                )
            )
            predictions = result.scalars().all()
            for p in predictions:
                # 检查是否已有回测记录
                existing = await session.execute(
                    select(StockBacktest).where(
                        and_(
                            StockBacktest.prediction_id == p.id,
                            StockBacktest.check_period == period_name,
                        )
                    )
                )
                if not existing.scalar_one_or_none():
                    pending.append({
                        "prediction_id": p.id,
                        "symbol": p.symbol,
                        "prediction": p.prediction,
                        "magnitude_min": p.magnitude_min,
                        "magnitude_max": p.magnitude_max,
                        "entry_price": p.entry_price,
                        "check_period": period_name,
                    })

        return pending
