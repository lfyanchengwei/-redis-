# server.py
from eventlet import queue
from flask import Flask, render_template
from flask_socketio import SocketIO
import redis
import json
import time
from datetime import datetime, timedelta
from threading import Thread, Lock
from collections import defaultdict
from config.settings import Config

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Redis连接
r = redis.Redis(
    host=Config.REDIS_HOST,
    port=Config.REDIS_PORT,
    decode_responses=True
)

# 全局消息队列（线程安全）
msg_queue = queue.Queue()


class DeviceState:
    """设备状态存储（线程安全）"""

    def __init__(self):
        self.data = defaultdict(lambda: {
            'history': [],  # 时序数据: {timestamp, errors, warns}
            'alerts': [],  # 告警记录
            'alert_count': 0,  # 总告警次数
            'last_error': None  # 最后ERROR事件
        })
        self.lock = Lock()

    def update_analysis(self, device_id, stats):
        """更新分析数据"""
        with self.lock:
            # 验证必要字段
            if 'timestamp' not in stats or 'error_ratio' not in stats or 'warn_ratio' not in stats:
                app.logger.warning(f"无效分析数据: {stats}")
                return
            entry = self.data[device_id]

            # 添加时序数据点
            entry['history'].append({
                'timestamp': stats['timestamp'],
                'errors': stats['error_ratio'],
                'warns': stats['warn_ratio']
            })

            # 保留时间窗口内的数据
            try:
                cutoff = datetime.now() - timedelta(seconds=Config.VIZ_TIME_WINDOW)
                entry['history'] = [
                    p for p in entry['history']
                    if datetime.fromisoformat(p['timestamp']) > cutoff
                ]
            except ValueError as e:
                app.logger.error(f"时间戳格式错误: {e}")

            # 更新最后ERROR事件
            last_error = stats.get('last_error')
            if last_error and 'timestamp' in last_error and 'message' in last_error:
                entry['last_error'] = last_error

    def update_alert(self, device_id, alert):
        """更新告警数据"""
        with self.lock:
            # 验证告警字段
            if 'timestamp' not in alert or 'message' not in alert:
                app.logger.warning(f"无效告警数据: {alert}")
                return

            entry = self.data[device_id]
            entry['alerts'].append(alert)
            entry['alert_count'] += 1


device_state = DeviceState()


@app.route('/')
def dashboard():
    """仪表盘页面"""
    return render_template('dashboard.html')


def background_listener():
    """Redis消息监听线程"""
    pubsub = r.pubsub()
    pubsub.subscribe(['analysis_channel1', 'alert_channel1'])

    for message in pubsub.listen():
        try:
            if message['type'] != 'message':
                continue
            data = json.loads(message['data'])
            channel = message['channel']

            # 验证设备ID存在性
            if 'device_id' not in data:
                app.logger.error(f"缺失device_id字段: {data}")
                continue

            device_id = data['device_id']

            # 分支处理
            if channel == 'analysis_channel1':
                device_state.update_analysis(device_id, data)
            elif channel == 'alert_channel1':
                device_state.update_alert(device_id, data)
            else:
                app.logger.warning(f"未知频道: {channel}")
                continue

            # 构建安全响应数据
            response = {
                'device': device_id,
                'type': 'analysis' if channel == 'analysis_channel1' else 'alert',
                'data': {
                    'current': {
                        'errors': data.get('error_ratio', 0),
                        'warns': data.get('warn_ratio', 0)
                    },
                    'alert_count': device_state.data[device_id]['alert_count']
                }
            }

            # 添加可选字段
            if 'last_error' in data:
                response['data']['current']['last_error'] = data['last_error']
            print(response)
            # 将消息放入队列而非直接发送
            msg_queue.put(response)

        except json.JSONDecodeError:
            app.logger.error(f"JSON解析失败: {message['data']}")
        except Exception as e:
            app.logger.error(f"处理消息失败: {str(e)}")
            app.logger.error(f"原始消息内容: {message}")


def flush_message_queue():
    """消息队列处理任务（运行在SocketIO上下文中）"""
    while True:
        while not msg_queue.empty():
            try:
                msg = msg_queue.get_nowait()
                # 在正确的上下文中发送消息
                socketio.emit('data_update', msg)
            except queue.Empty:
                break
            except Exception as e:
                app.logger.error(f"发送消息失败: {str(e)}")
        socketio.sleep(0.5)  # 降低CPU占用


@socketio.on('connect')
def handle_connect():
    """WebSocket连接初始化"""
    with device_state.lock:
        devices = list(device_state.data.keys())
        socketio.emit('device_list', {'devices': devices})

        # 启动队列处理任务
        socketio.start_background_task(target=flush_message_queue)

if __name__ == '__main__':
    Thread(target=background_listener, daemon=True).start()
    socketio.run(app, port=Config.WEB_PORT, debug=True)