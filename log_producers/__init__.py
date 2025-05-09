"""
日志生产者包初始化文件
"""

from .producer import generate_log  # 显式暴露接口

__all__ = ['generate_log']  # 定义公开接口