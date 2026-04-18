// module.stock.js - A股分析模块
// 依赖: Alpine.js, app.main.js (this.api)

window.StockModule = {
    // ==================== 数据状态 ====================
    boardLoading: false,
    marketIndices: [],      // 大盘指数
    watchlist: [],          // 自选股列表（含行情+预判）
    stats: null,            // 准确率统计

    // 预判详情页
    predictionDetail: null,
    predictionHistory: [],
    predictionStats: null,

    // 添加自选股弹窗
    showAddStockModal: false,
    addStockSymbol: '',
    addStockName: '',
    addStockLoading: false,

    // 预判依据展开状态
    expandedDimensions: {},

    // ==================== 页面导航 ====================

    navigateToStock() {
        this.page = 'stock';
        this.loadStockBoard();
    },

    goBackFromStock() {
        if (this.page === 'stock-detail') {
            this.page = 'stock';
        } else {
            this.page = 'home';
        }
    },

    // ==================== 看板数据 ====================

    async loadStockBoard() {
        this.boardLoading = true;
        try {
            const data = await this.api('/v2/stock/board');
            this.marketIndices = data.indices || [];
            this.watchlist = data.watchlist || [];
            this.stats = data.stats || null;
        } catch (e) {
            console.error('加载看板失败:', e);
            this.showToast('加载看板失败', 'error');
        } finally {
            this.boardLoading = false;
        }
    },

    async refreshBoard() {
        await this.loadStockBoard();
    },

    // ==================== 自选股管理 ====================

    async manualAddToWatchlist() {
        if (!this.addStockSymbol.trim() || !this.addStockName.trim()) return;
        this.addStockLoading = true;
        try {
            await this.api('/v2/stock/watchlist', 'POST', {
                symbol: this.addStockSymbol.trim(),
                name: this.addStockName.trim()
            });
            this.showToast('已添加 ' + this.addStockName.trim(), 'success');
            this.addStockSymbol = '';
            this.addStockName = '';
            this.showAddStockModal = false;
            await this.loadStockBoard();
        } catch (e) {
            const msg = e.detail || e.message || '添加失败';
            this.showToast(msg, 'error');
        } finally {
            this.addStockLoading = false;
        }
    },

    async removeFromWatchlist(symbol) {
        try {
            await this.api('/v2/stock/watchlist/' + symbol, 'DELETE');
            this.showToast('已删除', 'success');
            await this.loadStockBoard();
        } catch (e) {
            this.showToast('删除失败', 'error');
        }
    },

    // ==================== 预判详情 ====================

    async loadPredictionDetail(symbol) {
        this.page = 'stock-detail';
        this.predictionDetail = null;
        this.predictionHistory = [];
        this.predictionStats = null;
        this.expandedDimensions = {};
        try {
            const data = await this.api('/v2/stock/prediction/' + symbol);
            this.predictionDetail = data.latest;
            this.predictionHistory = data.history || [];
            this.predictionStats = data.stats || null;
        } catch (e) {
            console.error('加载预判详情失败:', e);
            this.showToast('加载失败', 'error');
        }
    },

    toggleDimension(dim) {
        this.expandedDimensions[dim] = !this.expandedDimensions[dim];
    },

    // ==================== 工具方法 ====================

    formatChange(pct) {
        if (pct == null || pct === undefined) return '--';
        const sign = pct > 0 ? '+' : '';
        return sign + pct.toFixed(2) + '%';
    },

    getChangeClass(pct) {
        if (pct == null) return 'stock-flat';
        if (pct > 0) return 'stock-up';
        if (pct < 0) return 'stock-down';
        return 'stock-flat';
    },

    getPredictionEmoji(prediction) {
        if (prediction === '看涨') return '📈';
        if (prediction === '看跌') return '📉';
        return '➡️';
    },

    getPredictionClass(prediction) {
        if (prediction === '看涨') return 'bullish';
        if (prediction === '看跌') return 'bearish';
        return 'neutral';
    },

    formatMagnitude(min, max) {
        if (min == null || max == null) return '--';
        const signMin = min >= 0 ? '+' : '';
        const signMax = max >= 0 ? '+' : '';
        return signMin + min + '% ~ ' + signMax + max + '%';
    },

    formatScore(score) {
        if (score == null) return '--';
        return score + '/10';
    },

    formatDate(dateStr) {
        if (!dateStr) return '';
        const d = new Date(dateStr);
        return (d.getMonth() + 1) + '/' + d.getDate();
    },
};
