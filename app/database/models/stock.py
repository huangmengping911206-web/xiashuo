# app/database/models/stock.py
# A股分析模块 - 数据库模型

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, Date, ForeignKey
from datetime import datetime, date

from app.database.models import Base


class StockWatchlist(Base):
    """自选股列表"""
    __tablename__ = "stock_watchlist"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, unique=True, comment="股票代码，如 600519.SS")
    name = Column(String(50), nullable=False, comment="股票名称，如 贵州茅台")
    sort_order = Column(Integer, default=0, comment="排序权重，越小越靠前")
    added_at = Column(DateTime, default=datetime.utcnow)


class StockPrediction(Base):
    """自选股预判记录（每次分析生成一条，保留历史）"""
    __tablename__ = "stock_prediction"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True, comment="股票代码")
    name = Column(String(50), nullable=True, comment="股票名称")
    analysis_date = Column(Date, nullable=False, index=True, comment="分析日期")
    analysis_type = Column(String(20), nullable=True, comment="分析类型：盘中异动/上午盘后/全天盘后")

    # 预判核心字段
    prediction = Column(String(10), nullable=False, comment="预判方向：看涨/看跌/中性")
    magnitude_min = Column(Float, nullable=True, comment="预测幅度下限，如 -5.0")
    magnitude_max = Column(Float, nullable=True, comment="预测幅度上限，如 -2.0")
    magnitude_period = Column(String(10), nullable=True, comment="预测周期：T+1/T+5/T+20")
    score = Column(Float, nullable=True, comment="综合评分 1-10")
    entry_price = Column(Float, nullable=True, comment="分析时价格")
    support_price = Column(Float, nullable=True, comment="支撑位")
    resistance_price = Column(Float, nullable=True, comment="压力位")

    # 六维评分详情（JSON）
    scores_detail = Column(Text, nullable=True, comment='六维评分JSON，如 {"fundamental":7,"industry":5,...}')

    # 六维详细依据
    fundamental = Column(Text, nullable=True, comment="基本面依据")
    industry = Column(Text, nullable=True, comment="行业面依据")
    news = Column(Text, nullable=True, comment="消息面依据")
    technical = Column(Text, nullable=True, comment="技术面依据")
    capital = Column(Text, nullable=True, comment="资金面依据")
    risk = Column(Text, nullable=True, comment="风险面依据")

    # 综合判断
    reasons = Column(Text, nullable=True, comment="综合判断理由摘要")

    # 关联推文
    tweet_id = Column(Integer, nullable=True, comment="关联的推文 ID")

    created_at = Column(DateTime, default=datetime.utcnow)


class StockBacktest(Base):
    """回测结果：对比预判与实际走势"""
    __tablename__ = "stock_backtest"

    id = Column(Integer, primary_key=True, autoincrement=True)
    prediction_id = Column(Integer, ForeignKey("stock_prediction.id"), nullable=True, comment="关联预判 ID")
    symbol = Column(String(20), nullable=False, index=True, comment="股票代码")
    check_period = Column(String(10), nullable=False, comment="回测周期：T+1/T+5/T+20")
    actual_price = Column(Float, nullable=True, comment="实际价格")
    actual_change_pct = Column(Float, nullable=True, comment="实际涨跌幅 %")
    predicted_min = Column(Float, nullable=True, comment="预测幅度下限")
    predicted_max = Column(Float, nullable=True, comment="预测幅度上限")
    predicted_direction = Column(String(10), nullable=True, comment="预测方向：看涨/看跌/中性")
    is_correct = Column(Integer, default=0, comment="实际走势是否在预测区间内：1=是 0=否")
    is_direction_correct = Column(Integer, default=0, comment="方向是否正确：1=是 0=否")

    checked_at = Column(DateTime, default=datetime.utcnow)
