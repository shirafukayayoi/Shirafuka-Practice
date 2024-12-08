import psutil
import GPUtil
import time
from datetime import datetime


def monitor_process(process_name, log_file):
    try:
        with open(log_file, "a") as log:
            while True:
                # 現在の時刻を取得
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # 指定したプロセスを探す
                process = None
                for proc in psutil.process_iter(attrs=["pid", "name"]):
                    if proc.info["name"] == process_name:
                        process = proc
                        break

                if process is None:
                    log_message = f"{current_time} - プロセス '{process_name}' が見つかりません。\n"
                    print(log_message.strip())
                    log.write(log_message)
                else:
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
                        "--------------------------------------------------\n"
                    )

                    # 結果を表示とログ書き込み
                    print(log_message.strip())
                    log.write(log_message)

                time.sleep(1)  # 更新間隔（秒）
    except KeyboardInterrupt:
        print("監視を終了します。")


if __name__ == "__main__":
    # 監視したいプロセス名を指定
    process_name_to_monitor = input("監視したいプロセス名を入力してください: ")

    # ログファイル名を指定
    log_file_name = f"{process_name_to_monitor}_monitor.log"
    print(f"ログは {log_file_name} に書き込まれます。")

    monitor_process(process_name_to_monitor, log_file_name)
