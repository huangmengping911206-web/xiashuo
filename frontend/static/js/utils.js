// static/js/utils.js

/**
 * 工具函数模块
 * 包含应用中通用的纯函数工具，不依赖组件状态 (this)
 */
window.AppUtils = {

    /**
     * 获取默认头像
     * @returns {string} 返回一个 SVG 格式的 Base64 编码图片字符串
     */
    getDefaultAvatar() {
        return 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"%3E%3Ccircle cx="24" cy="24" r="24" fill="%2387CEEB"/%3E%3Ctext x="24" y="30" text-anchor="middle" font-size="20" fill="white"%3E👤%3C/text%3E%3C/svg%3E';
    },

    /**
     * 格式化时间显示
     * @param {string} dateStr - 日期字符串
     * @returns {string} 格式化后的相对时间 (如：刚刚、5分钟前、3天前)
     */
    formatTime(dateStr) {
        if (!dateStr) return '';

        try {
            // 直接解析时间字符串
            // 后端返回的是 UTC 时间，JavaScript 会自动转换为本地时间
            const date = new Date(dateStr.replace(' ', 'T') + 'Z');
            const now = new Date();
            // 计算时间差（秒）
            const diff = (now - date) / 1000;

            if (diff < 60) return '刚刚';
            if (diff < 3600) return Math.floor(diff / 60) + '分钟前';
            if (diff < 86400) return Math.floor(diff / 3600) + '小时前';
            if (diff < 604800) return Math.floor(diff / 86400) + '天前';

            // 超过一周显示具体日期
            return date.toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' });
        } catch (e) {
            return dateStr;
        }
    },

    /**
     * 文本截断
     * @param {string} text - 原始文本
     * @param {number} maxLength - 最大长度
     * @returns {string} 截断后的文本，超出部分用省略号替代
     */
    truncateText(text, maxLength) {
        if (!text) return '';
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    },

    /**
     * 解析标签字符串
     * @param {string} tagsStr - 逗号分隔的标签字符串
     * @returns {Array} 标签数组
     */
    parseTags(tagsStr) {
        if (!tagsStr) return [];
        return tagsStr.split(',').filter(t => t.trim());
    },

    /**
     * 根据图片数量获取对应的网格布局类名
     * @param {number} count - 图片数量
     * @returns {string} CSS 类名
     */
    getImageGridClass(count) {
        if (count === 1) return 'single';
        if (count === 2) return 'double';
        if (count === 4) return 'grid-2';
        return 'grid-3';
    },

    /**
     * 根据头像ID获取图片URL
     * @param {number} avatarId - 头像ID
     * @returns {string} 图片URL或默认头像
     */
    getAvatarUrl(avatarId) {
        if (!avatarId) return this.getDefaultAvatar();
        return `/api/v2/image/${avatarId}`;
    },

    /**
     * 判断推文是否为长文
     * @param {string} content - 推文内容
     * @returns {boolean} 是否超过300字
     */
    isTweetLong(content) {
        return content && content.length > 300;
    },

    /**
     * 获取用于展示的图片数组
     * @param {Array} imageIds - 图片ID数组
     * @returns {Array} 最多9张图片的数组
     */
    getDisplayImages(imageIds) {
        if (!imageIds) return [];
        return imageIds.slice(0, 9);
    },

    /**
     * 格式化标签显示
     * @param {string} tagsStr - 逗号分隔的标签字符串
     * @returns {string} 格式化后的显示文本（最多显示2个标签）
     */
    formatTags(tagsStr) {
        if (!tagsStr) return '';

        const tags = tagsStr.split(',').filter(t => t.trim());

        if (tags.length === 0) return '';
        if (tags.length === 1) return tags[0];

        // 显示前两个标签，超过则加省略号
        return tags.slice(0, 2).join(', ') + (tags.length > 2 ? '...' : '');
    }
};
