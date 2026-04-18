from collections import defaultdict

# 全局字典，记录每个 Topic 待处理的消息数量
# 结构: {'email': 5, 'report': 0}
topic_counters = defaultdict(int)


def incr_topic(topic: str):
    """增加计数"""
    topic_counters[topic] += 1


def decr_topic(topic: str):
    """减少计数，防止减到负数"""
    if topic_counters[topic] > 0:
        topic_counters[topic] -= 1


def get_count(topic: str) -> int:
    """获取当前计数"""
    return topic_counters[topic]
