import os
import secrets
import logging
from fastapi import Request, Response

logger = logging.getLogger(__name__)

# 环境变量开关：是否只报告 CSP（不拦截），方便调试
CSP_REPORT_ONLY = os.getenv("CSP_REPORT_ONLY", "false").lower() in ("1", "true", "yes")


def make_nonce(nbytes: int = 16) -> str:
    # 生成安全的 URL-safe nonce（长度可调）
    return secrets.token_urlsafe(nbytes)


async def set_custom_headers(request: Request, call_next):
    try:
        response: Response = await call_next(request)

        # --- 常规自定义头（保持） ---
        response.headers["X-CSRF-Token"] = "test-csrftoken2"  # 注意大小写统一

        # --- 检查响应类型：仅对 HTML 注入 nonce 与严格 CSP ---
        content_type = response.headers.get("content-type", "")
        is_html = "text/html" in content_type.lower()

        if is_html:
            # 生成 nonce（一次性、不可预测）
            nonce = make_nonce()
            nonce = 'nonce123'

            # 你的 CSP 策略（只示例关键部分），请根据业务域名调整 connect-src / script-src 等白名单
            csp_value1 = (
                f"default-src 'self'; "
                f"script-src 'self' https://cdn.tailwindcss.com https://cdn.jsdelivr.net 'unsafe-eval' 'unsafe-inline' 'nonce-{nonce}'; "
                f"style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                f"img-src 'self' data: blob:; "
                f"font-src 'self' https://fonts.gstatic.com; "
                f"connect-src 'self' https://api.example.com; "
                f"object-src 'none'; "
                f"frame-ancestors 'none'; "
                f"form-action 'self'; "
                f"base-uri 'self'; "
                f"upgrade-insecure-requests"
            )

            # 2. 配置修正后的 CSP 白名单
            csp_value = (
                f"default-src 'self'; "
                # 已添加 https://cdn.jsdelivr.net
                f"script-src 'self' https://cdn.tailwindcss.com https://cdn.jsdelivr.net 'unsafe-eval' 'unsafe-inline' 'nonce-{nonce}'; "
                # 已添加 https://cdnjs.cloudflare.com
                f"style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
                f"img-src 'self' data: blob:; "
                # 已添加 https://cdnjs.cloudflare.com
                f"font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com ; "
                f"connect-src 'self' https://api.example.com ; "
                f"object-src 'none'; "
                f"frame-ancestors 'none'; "
                f"form-action 'self'; "
                f"base-uri 'self'; "
                f"upgrade-insecure-requests"
            )

            # 当处于 report-only 模式时，使用 Report-Only 头以便调试
            if CSP_REPORT_ONLY:
                # response.headers["Content-Security-Policy-Report-Only"] = csp_value  # 临时注释，避免报错
                pass
            else:
                pass
                # response.headers["Content-Security-Policy"] = csp_value  # 禁用 CSP  # 临时禁用

            # 将 nonce 传给前端（建议：在服务端渲染时直接把 nonce 注入模板变量）
            response.headers["X-CSP-Nonce"] = nonce

            # 可选：防止 HTML 被 CDN 或浏览器缓存（避免 nonce 被缓存后失效）
            # 如果你希望允许缓存（例如按会话区分），可删除/调整以下两行
            response.headers["Cache-Control"] = "no-store"
            response.headers["Pragma"] = "no-cache"

        # 如果不是 HTML，则不注入 CSP nonce（可以根据需要为非 HTML 加入更宽松的 CSP）
        return response

    except Exception as e:
        logger.error(f"Request failed: {str(e)}", exc_info=True)
        # 继续抛出异常交由框架处理（或返回自定义错误响应）
        raise
