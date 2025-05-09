# analyzer.py
import redis
from collections import deque, defaultdict
import time
import json
from datetime import datetime, timedelta
from threading import Thread, Lock
import logging
from config.settings import Config

logging.basicConfig(level=logging.INFO)


class DeviceAnalyzer:
    def __init__(self, device_id):
        self.device_id = device_id
        self.log_window = deque(maxlen=Config.WINDOW_SIZE)  # 固定数量窗口
        self.last_error = None  # 仅保留最近一次ERROR
        self.redis = redis.Redis(
            host=Config.REDIS_HOST,
            port=Config.REDIS_PORT,
            decode_responses=True
        )
        self.alert_triggered = False

    def process_log(self, log):
        """更新日志窗口和错误记录"""
        try:
            log_time = datetime.strptime(log['timestamp'], "%Y-%m-%d%H:%M:%S")
        except ValueError as e:
            logging.error(f"解析时间戳失败: {log['timestamp']}, 错误: {e}")
            return

        log_entry = {
            'timestamp': log_time,
            'level': log['log_level'],
            'message': log['message']
        }
        self.log_window.append(log_entry)

        # 记录最近一次ERROR
        if log['log_level'] == 'ERROR':
            self.last_error = {
                'time': log['timestamp'],
                'message': log['message']
            }

    def calculate_stats(self):
        """基于最近N条日志计算统计指标"""
        total = len(self.log_window)
        error_count = sum(1 for log in self.log_window if log['level'] == 'ERROR')
        warn_count = sum(1 for log in self.log_window if log['level'] == 'WARN')
        print({
            'device_id': self.device_id,
            'timestamp': datetime.now().isoformat(),
            'error_ratio': error_count / total if total else 0,
            'warn_ratio': warn_count / total if total else 0,
            'last_error': self.last_error
        })
        return {
            'device_id': self.device_id,
            'timestamp': datetime.now().isoformat(),
            'error_ratio': error_count / total if total else 0,
            'warn_ratio': warn_count / total if total else 0,
            'last_error': self.last_error
        }

    def check_alert(self):
        """检查S秒时间窗口内的错误率"""
        now = datetime.now()
        # 筛选ALERT_WINDOW时间窗口内的日志
        alert_window = [
            log for log in self.log_window
            if (now - log['timestamp']).total_seconds() <= Config.ALERT_WINDOW
        ]
        total = len(alert_window)
        if total == 0:
            return False

        error_count = sum(1 for log in alert_window if log['level'] == 'ERROR')
        error_rate = error_count / total

        if error_rate > 0.5:
            if not self.alert_triggered:
                alert = {
                    'device_id': self.device_id,
                    'type': 'alert',
                    'timestamp': now.isoformat(),
                    'message': f"CRITICAL: Error rate {error_rate * 100:.1f}%",
                    'window_duration': Config.ALERT_WINDOW
                }
                self.redis.publish('alert_channel1', json.dumps(alert))
                self.alert_triggered = True
            return True
        else:
            self.alert_triggered = False
            return False


class AnalysisService:
    def __init__(self):
        self.devices = {}
        self.locks = defaultdict(Lock)
        self.redis = redis.Redis(
            host=Config.REDIS_HOST,
            port=Config.REDIS_PORT,
            decode_responses=True
        )
        self.pubsub = self.redis.pubsub()
        self.pubsub.subscribe('log_channel1')

    def run(self):
        """启动分析服务"""
        Thread(target=self._process_messages, daemon=True).start()
        Thread(target=self._periodic_analysis, daemon=True).start()
        logging.info("Analysis service started")

    def _process_messages(self):
        """直接处理每条完整消息（无换行符分割）"""
        for message in self.pubsub.listen():
            if message['type'] == 'message':
                try:
                    log = json.loads(message['data'])
                    device_id = log['device_id']

                    with self.locks[device_id]:
                        if device_id not in self.devices:
                            self.devices[device_id] = DeviceAnalyzer(device_id)

                        self.devices[device_id].process_log(log)
                except json.JSONDecodeError:
                    logging.error(f"无效JSON数据: {message['data']}")
                except KeyError as e:
                    logging.error(f"日志字段缺失: {e}")

    def _periodic_analysis(self):
        """定时发布统计信息并检查告警"""
        while True:
            time.sleep(Config.ANALYSIS_INTERVAL)
            for device_id in list(self.devices.keys()):  # 避免字典大小变化
                with self.locks[device_id]:
                    analyzer = self.devices[device_id]
                    stats = analyzer.calculate_stats()

                    # 发布统计信息
                    json_stats = json.dumps(stats)
                    print(json_stats)
                    self.redis.publish('analysis_channel1', json_stats)
                    logging.debug(f"已发布统计: {device_id}")

                    # 检查告警
                    if analyzer.check_alert():
                        logging.warning(f"设备 {device_id} 触发告警")


if __name__ == '__main__':
    service = AnalysisService()
    service.run()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("程序已终止")
