import os


class Config:
    # Redis配置
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))

    # 分析服务参数
    WINDOW_SIZE = 100  # 维护的日志条数N
    ANALYSIS_INTERVAL = 5  # 分析间隔T（秒）
    ALERT_THRESHOLD = 10  # 告警检测窗口S（秒）
    ALERT_WINDOW = 10  # 告警检测窗口S（秒）
    VIZ_TIME_WINDOW = 60 # 可视化时间窗口（秒）

    # Web配置
    WEB_HOST = '0.0.0.0'
    WEB_PORT = 5000