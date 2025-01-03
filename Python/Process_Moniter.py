import time
from datetime import datetime

import GPUtil
import psutil


def monitor_process(process_name):
    try:
        while True:
            # 現在の時刻を取得
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # プロセス情報を取得
            for process in psutil.process_iter(["pid", "name"]):
                if process.info["name"] == process_name:
                    pid = process.info["pid"]
                    process = psutil.Process(pid)

                    # CPU使用率
                    cpu_usage = process.cpu_percent(interval=1)

                    # メモリ使用率
                    memory_info = process.memory_info()
                    memory_usage = memory_info.rss / (1024 * 1024)  # MB単位

                    # GPU使用率
                    gpu_stats = GPUtil.getGPUs()
                    if gpu_stats:
                        gpu_usage = [
                            f"GPU {gpu.id}: {gpu.load * 100:.1f}% 使用中"
                            for gpu in gpu_stats
                        ]
                    else:
                        gpu_usage = ["GPUの情報が取得できません。"]

                    # ログメッセージを作成
                    log_message = (
                        f"{current_time} - プロセス: {process_name} (PID: {pid})\n"
                        f"CPU使用率: {cpu_usage:.1f}%\n"
                        f"メモリ使用量: {memory_usage:.1f} MB\n"
                        f"GPU使用率: {'; '.join(gpu_usage)}\n"
                    )

                    # 上書き表示（コンソールに表示する内容を上書き）
                    print(f"\033[H\033[J{log_message}", end="")

            time.sleep(0.5)  # 更新間隔（秒）
    except KeyboardInterrupt:
        print("\n監視を終了します。")


if __name__ == "__main__":
    # 監視したいプロセス名を指定
    process_name_to_monitor = input("監視したいプロセス名を入力してください: ")
    monitor_process(process_name_to_monitor)
