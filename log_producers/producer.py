import redis
import json
import time
import random
from multiprocessing import Process, Event
from config.settings import Config


def generate_log(device_id, stop_event):
    """日志生成核心函数（改进版）"""
    r = redis.Redis(host=Config.REDIS_HOST, port=Config.REDIS_PORT)
    levels = ['INFO', 'WARN', 'ERROR']

    while not stop_event.is_set():
        start_time = time.time()
        try:
            log = {
                "device_id": device_id,
                "timestamp": time.strftime("%Y-%m-%d%H:%M:%S"),
                "log_level": random.choices(levels, weights=[70, 20, 10])[0],
                "message": "System status" + (" normal" if random.random() > 0.1 else " abnormal")
            }
            r.publish('log_channel1', json.dumps(log))
        except redis.RedisError as e:
            print(f"[{device_id}] Redis error: {e}")
        except Exception as e:
            print(f"[{device_id}] Fatal error: {e}")
            break

        # 确保严格100ms间隔
        elapsed = time.time() - start_time
        if elapsed < 0.1:
            time.sleep(0.1 - elapsed)


if __name__ == '__main__':
    processes = []
    stop_event = Event()
    try:
        for i in range(3):
            p = Process(
                target=generate_log,
                args=(f'device_{i}', stop_event),
                name=f'LogProducer-{i}'
            )
            p.start()
            processes.append(p)
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print("\nStopping processes...")
        stop_event.set()
        for p in processes:
            p.join(timeout=5)
            if p.is_alive():
                p.terminate()