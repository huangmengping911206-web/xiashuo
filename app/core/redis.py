from typing import Any, List, Dict, Optional
from collections import defaultdict
import time


class MY_RedisClient:

    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0, password: Optional[str] = None):
        """
        初始化模拟的Redis客户端
        host, port, db, password: 模拟Redis接口，实际不使用网络连接
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        # 数据存储：键值对、过期时间、列表、哈希
        self._store: Dict[str, Any] = {}  # 字符串存储
        self._expirations: Dict[str, float] = {}  # 过期时间戳
        self._lists: Dict[str, List[Any]] = defaultdict(list)  # 列表存储
        self._hashes: Dict[str, Dict[str, Any]] = defaultdict(dict)  # 哈希存储

    def _check_expired(self, key: str) -> None:
        """
        检查并清理过期键
        """
        if key in self._expirations:
            if time.time() > self._expirations[key]:
                self._store.pop(key, None)
                self._lists.pop(key, None)
                self._hashes.pop(key, None)
                self._expirations.pop(key, None)

    def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """
        设置键值对
        ex: 过期时间（秒）
        """
        try:
            self._store[key] = str(value)
            if ex is not None:
                self._expirations[key] = time.time() + ex
            self._lists.pop(key, None)  # 确保键类型唯一
            self._hashes.pop(key, None)
            return True
        except Exception as e:
            print(f"Set operation failed: {str(e)}")
            return False

    def get(self, key: str) -> Optional[str]:
        """
        获取键的值
        """
        try:
            self._check_expired(key)
            return self._store.get(key)
        except Exception as e:
            print(f"Get operation failed: {str(e)}")
            return None

    def delete(self, key: str) -> bool:
        """
        删除键
        """
        try:
            self._check_expired(key)
            removed = False
            if key in self._store:
                self._store.pop(key)
                removed = True
            if key in self._lists:
                self._lists.pop(key)
                removed = True
            if key in self._hashes:
                self._hashes.pop(key)
                removed = True
            self._expirations.pop(key, None)
            return removed
        except Exception as e:
            print(f"Delete operation failed: {str(e)}")
            return False

    def incr(self, key: str) -> int:
        """
        键值自增
        """
        try:
            self._check_expired(key)
            value = self._store.get(key)
            if value is None:
                self._store[key] = "1"
                return 1
            try:
                new_value = int(value) + 1
                self._store[key] = str(new_value)
                return new_value
            except ValueError:
                raise ValueError("Value is not an integer")
        except Exception as e:
            print(f"Increment operation failed: {str(e)}")
            return 0

    def push_list(self, key: str, values: List[Any], left: bool = False) -> int:
        """
        向列表添加元素
        left: True表示从左边插入，False表示从右边插入
        """
        try:
            self._check_expired(key)
            values = [str(v) for v in values]
            self._store.pop(key, None)  # 确保键类型唯一
            self._hashes.pop(key, None)
            if left:
                self._lists[key][0:0] = values
            else:
                self._lists[key].extend(values)
            return len(self._lists[key])
        except Exception as e:
            print(f"List push operation failed: {str(e)}")
            return 0

    def pop_list(self, key: str, left: bool = False) -> Optional[str]:
        """
        从列表弹出元素
        left: True表示从左边弹出，False表示从右边弹出
        """
        try:
            self._check_expired(key)
            if key not in self._lists or not self._lists[key]:
                return None
            if left:
                return self._lists[key].pop(0)
            return self._lists[key].pop()
        except Exception as e:
            print(f"List pop operation failed: {str(e)}")
            return None

    def get_list(self, key: str, start: int = 0, end: int = -1) -> List[str]:
        """
        获取列表范围内的元素
        """
        try:
            self._check_expired(key)
            lst = self._lists.get(key, [])
            if not lst:
                return []
            if end < 0:
                end = len(lst) + end
            return lst[start:end + 1]
        except Exception as e:
            print(f"Get list operation failed: {str(e)}")
            return []

    def hset(self, key: str, field: str, value: Any) -> bool:
        """
        设置哈希字段值
        """
        try:
            self._check_expired(key)
            self._store.pop(key, None)  # 确保键类型唯一
            self._lists.pop(key, None)
            self._hashes[key][field] = str(value)
            return True
        except Exception as e:
            print(f"Hash set operation failed: {str(e)}")
            return False

    def hget(self, key: str, field: str) -> Optional[str]:
        """
        获取哈希字段值
        """
        try:
            self._check_expired(key)
            return self._hashes.get(key, {}).get(field)
        except Exception as e:
            print(f"Hash get operation failed: {str(e)}")
            return None

    def hgetall(self, key: str) -> Dict[str, str]:
        """
        获取哈希所有字段和值
        """
        try:
            self._check_expired(key)
            return dict(self._hashes.get(key, {}))
        except Exception as e:
            print(f"Hash getall operation failed: {str(e)}")
            return {}

    def close(self):
        """
        模拟关闭连接，清空数据
        """
        try:
            self._store.clear()
            self._expirations.clear()
            self._lists.clear()
            self._hashes.clear()
        except Exception as e:
            print(f"Close operation failed: {str(e)}")

# 示例用法
if __name__ == "__main__":
    try:
        redis_client = MY_RedisClient(host='localhost', port=6379, db=0)

        # 字符串操作
        redis_client.set('name', 'Alice', ex=3600)
        print(redis_client.get('name'))  # 输出: Alice
        redis_client.incr('counter')
        print(redis_client.get('counter'))  # 输出: 1
        redis_client.delete('name')
        print(redis_client.get('name'))  # 输出: None

        # 列表操作
        redis_client.push_list('mylist', ['apple', 'banana'], left=True)
        redis_client.push_list('mylist', ['orange'], left=False)
        print(redis_client.get_list('mylist'))  # 输出: ['banana', 'apple', 'orange']
        print(redis_client.pop_list('mylist', left=True))  # 输出: banana
        print(redis_client.get_list('mylist'))  # 输出: ['apple', 'orange']

        # 哈希操作
        redis_client.hset('user:1', 'name', 'Bob')
        redis_client.hset('user:1', 'age', '30')
        print(redis_client.hget('user:1', 'name'))  # 输出: Bob
        print(redis_client.hgetall('user:1'))  # 输出: {'name': 'Bob', 'age': '30'}

        redis_client.close()
    except Exception as e:
        print(f"Error: {str(e)}")