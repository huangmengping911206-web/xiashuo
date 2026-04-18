# app/database/schemas/stock.py
# A股分析模块 - Pydantic 数据模型

from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime, date


# ============ 自选股 ============

class WatchlistAdd(BaseModel):
    """添加自选股"""
    symbol: str
    name: str
    sort_order: int = 0


class WatchlistOut(BaseModel):
    """自选股输出"""
    id: int
    symbol: str
    name: str
    sort_order: int
    added_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============ 预判 ============

class PredictionCreate(BaseModel):
    """创建/更新预判（内部 API 用）"""
    symbol: str
    name: Optional[str] = None
    analysis_date: date
    analysis_type: Optional[str] = None
    prediction: str  # 看涨/看跌/中性
    magnitude_min: Optional[float] = None
    magnitude_max: Optional[float] = None
    magnitude_period: Optional[str] = None  # T+1/T+5/T+20
    score: Optional[float] = None
    entry_price: Optional[float] = None
    support_price: Optional[float] = None
    resistance_price: Optional[float] = None
    scores_detail: Optional[str] = None  # JSON string
    fundamental: Optional[str] = None
    industry: Optional[str] = None
    news: Optional[str] = None
    technical: Optional[str] = None
    capital: Optional[str] = None
    risk: Optional[str] = None
    reasons: Optional[str] = None
    tweet_id: Optional[int] = None


class PredictionOut(BaseModel):
    """预判输出"""
    id: int
    symbol: str
    name: Optional[str] = None
    analysis_date: date
    analysis_type: Optional[str] = None
    prediction: str
    magnitude_min: Optional[float] = None
    magnitude_max: Optional[float] = None
    magnitude_period: Optional[str] = None
    score: Optional[float] = None
    entry_price: Optional[float] = None
    support_price: Optional[float] = None
    resistance_price: Optional[float] = None
    scores_detail: Optional[str] = None
    fundamental: Optional[str] = None
    industry: Optional[str] = None
    news: Optional[str] = None
    technical: Optional[str] = None
    capital: Optional[str] = None
    risk: Optional[str] = None
    reasons: Optional[str] = None
    tweet_id: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============ 看板（自选股 + 最新预判 + 实时行情） ============

class WatchlistItemWithPrediction(BaseModel):
    """看板单条：自选股 + 最新预判"""
    symbol: str
    name: str
    sort_order: int
    # 实时行情（由 API 从 Finance API 获取后填充）
    price: Optional[float] = None
    change_pct: Optional[float] = None
    volume: Optional[int] = None
    day_high: Optional[float] = None
    day_low: Optional[float] = None
    market_cap: Optional[float] = None
    # 最新预判
    prediction: Optional[str] = None
    magnitude_min: Optional[float] = None
    magnitude_max: Optional[float] = None
    magnitude_period: Optional[str] = None
    score: Optional[float] = None
    entry_price: Optional[float] = None
    analysis_date: Optional[date] = None


class BoardResponse(BaseModel):
    """看板响应"""
    indices: Optional[List[dict]] = None  # 大盘指数
    watchlist: List[WatchlistItemWithPrediction] = []


# ============ 回测 ============

class BacktestCreate(BaseModel):
    """创建回测结果（内部 API 用）"""
    prediction_id: Optional[int] = None
    symbol: str
    check_period: str  # T+1/T+5/T+20
    actual_price: Optional[float] = None
    actual_change_pct: Optional[float] = None
    predicted_min: Optional[float] = None
    predicted_max: Optional[float] = None
    predicted_direction: Optional[str] = None
    is_correct: int = 0
    is_direction_correct: int = 0


class BacktestOut(BaseModel):
    """回测输出"""
    id: int
    prediction_id: Optional[int] = None
    symbol: str
    check_period: str
    actual_price: Optional[float] = None
    actual_change_pct: Optional[float] = None
    predicted_min: Optional[float] = None
    predicted_max: Optional[float] = None
    predicted_direction: Optional[str] = None
    is_correct: int
    is_direction_correct: int
    checked_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============ 统计 ============

class AccuracyStats(BaseModel):
    """准确率统计"""
    total_count: int = 0
    correct_count: int = 0
    accuracy_rate: float = 0.0
    direction_correct_count: int = 0
    direction_accuracy_rate: float = 0.0
    avg_actual_change: float = 0.0
    # 按方向拆分
    bullish_count: int = 0
    bullish_correct: int = 0
    bearish_count: int = 0
    bearish_correct: int = 0
    neutral_count: int = 0
    neutral_correct: int = 0
    # 按周期拆分
    by_period: Optional[dict] = None
