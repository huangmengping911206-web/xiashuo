import time


def current_time():
    start_time = time.time()
    # 转换为其他日期格式,如:"%Y-%m-%d %H:%M:%S"
    timeArray = time.localtime(start_time)
    otherStyleTime = time.strftime("%Y-%m-%d %H:%M:%S", timeArray)
    return otherStyleTime


import jieba


def get_tokens(text: str) -> str:
    """
    将文本分词并用空格连接，返回处理后的字符串。
    例如: "数据库是好的" -> "数据库 是 好 的"
    """
    if not text:
        return ""
    # jieba.lcut 返回列表，用空格连接
    # 这样 "数据库" 就是一个整体 token，不会被拆散
    return " ".join(jieba.lcut(text))


def get_query_tokens(keyword: str) -> str:
    """
    处理搜索关键词，支持模糊匹配。
    例如: 搜 "数据" -> 转为 "数据*" (匹配数据库、数据结构等)
    """
    if not keyword:
        return ""

    # 1. 对用户输入进行分词
    tokens = jieba.lcut(keyword)

    # 2. 构造 FTS5 查询语法
    # 给每个词加上 * 号，表示前缀匹配。
    # 例如用户搜 "数据"，分词后是 "数据"，加上 * 变成 "数据*"
    # 这样就能匹配到 "数据库" (因为 "数据库" 以 "数据" 开头)
    processed_tokens = [f"{token}*" for token in tokens]

    # 3. 用空格连接 (FTS5 默认空格代表 AND)
    return " ".join(processed_tokens)



