#!/usr/bin/env python3
"""
Python 语法高亮测试文件
演示各种 Python 语法特性
"""

import os
import sys
from typing import List, Dict, Optional
import asyncio
import json

# 类定义
class DataProcessor:
    """数据处理器类"""
    
    def __init__(self, name: str, debug: bool = False):
        self.name = name
        self.debug = debug
        self._data: List[Dict] = []
    
    @property
    def data_count(self) -> int:
        """返回数据数量"""
        return len(self._data)
    
    def add_data(self, data: Dict) -> None:
        """添加数据"""
        if self.debug:
            print(f"Adding data: {data}")
        self._data.append(data)
    
    async def process_async(self) -> List[str]:
        """异步处理数据"""
        results = []
        for item in self._data:
            # 模拟异步处理
            await asyncio.sleep(0.1)
            processed = self._process_item(item)
            results.append(processed)
        return results
    
    def _process_item(self, item: Dict) -> str:
        """处理单个数据项"""
        return f"Processed: {item.get('name', 'Unknown')}"

# 函数定义
def fibonacci(n: int) -> List[int]:
    """生成斐波那契数列"""
    if n <= 0:
        return []
    elif n == 1:
        return [0]
    elif n == 2:
        return [0, 1]
    
    fib = [0, 1]
    for i in range(2, n):
        fib.append(fib[i-1] + fib[i-2])
    return fib

# 装饰器示例
def timing_decorator(func):
    """计时装饰器"""
    import time
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(f"{func.__name__} 执行时间: {end - start:.4f}秒")
        return result
    return wrapper

@timing_decorator
def complex_calculation(data: List[int]) -> float:
    """复杂计算示例"""
    return sum(x ** 2 for x in data if x % 2 == 0) / len(data)

# 主程序
if __name__ == "__main__":
    # 字符串操作
    message = f"""
    这是一个多行字符串
    用于测试 Python 语法高亮
    包含变量插值: {sys.version}
    """
    
    # 列表推导式
    squares = [x**2 for x in range(10) if x % 2 == 0]
    
    # 字典操作
    config = {
        "name": "测试配置",
        "version": 1.0,
        "features": ["syntax", "highlighting", "python"],
        "nested": {
            "debug": True,
            "timeout": 30
        }
    }
    
    # 异常处理
    try:
        processor = DataProcessor("TestProcessor", debug=True)
        processor.add_data({"name": "测试数据", "value": 42})
        
        # 正则表达式
        import re
        pattern = r'\d+\.\d+'
        version_match = re.search(pattern, str(config["version"]))
        
        if version_match:
            print(f"找到版本号: {version_match.group()}")
            
    except Exception as e:
        print(f"发生错误: {e}")
    finally:
        print("程序执行完成")
    
    # F-string 和各种数据类型
    numbers = [1, 2, 3, 4, 5]
    result = complex_calculation(numbers)
    print(f"计算结果: {result:.2f}")
    
    # 生成器表达式
    even_squares = (x**2 for x in range(100) if x % 2 == 0)
    first_five = [next(even_squares) for _ in range(5)]
    print(f"前五个偶数的平方: {first_five}") 