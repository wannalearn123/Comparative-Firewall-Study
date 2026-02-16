import psutil
import subprocess
import time
import re

class StateObserver:
    """
    Kelas untuk mengumpulkan data state real-time: CPU/RAM, packet rate, dan throughput legal dari log HTTP.
    Mengkategorikan ke state diskrit (0-8) berdasarkan kombinasi traffic load dan CPU.
    """
    def __init__(self, log_file_path='/var/log/nginx/access.log', interface='eth0'):
        self.log_file_path = log_file_path
        self.interface = interface
        self.last_packet_count = 0  # Untuk menghitung rate paket
        self.last_time = time.time()

    def get_cpu_ram_state(self):
        # Mengukur CPU dan RAM, kategorikan ke [Safe, Warning, Critical].
        cpu_percent = psutil.cpu_percent(interval=1)  # Interval 1 detik untuk akurasi
        ram_percent = psutil.virtual_memory().percent
        # Threshold: CPU/RAM <50% Safe, 50-80% Warning, >80% Critical
        cpu_state = 0 if cpu_percent < 50 else (1 if cpu_percent < 80 else 2)
        ram_state = 0 if ram_percent < 50 else (1 if ram_percent < 80 else 2)
        # Gunakan CPU sebagai proxy utama untuk state (ram_state bisa ditambahkan jika perlu)
        return cpu_state  # 0: Safe, 1: Warning, 2: Critical

    def get_packet_rate(self):
        # Mengukur laju paket masuk per detik via iptables -L -v.
        try:
            result = subprocess.run(['iptables', '-L', '-v'], capture_output=True, text=True, timeout=5)
            # Parse output untuk packets pada interface (asumsi chain INPUT)
            lines = result.stdout.split('\n')
            packet_count = 0
            for line in lines:
                if self.interface in line and 'pkts' in line:
                    match = re.search(r'(\d+) pkts', line)
                    if match:
                        packet_count += int(match.group(1))
            current_time = time.time()
            rate = (packet_count - self.last_packet_count) / (current_time - self.last_time) if self.last_time else 0
            self.last_packet_count = packet_count
            self.last_time = current_time
            # Kategorikan: <100 Low, 100-500 Medium, >500 High
            traffic_load = 0 if rate < 100 else (1 if rate < 500 else 2)
            return traffic_load  # 0: Low, 1: Medium, 2: High
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            return 0  # Fallback ke Low jika gagal

    def get_throughput_legal(self):
        # Parse log HTTP untuk hitung throughput legal (status 200).
        try:
            with open(self.log_file_path, 'r') as f:
                lines = f.readlines()[-100:]  # Ambil 100 baris terakhir untuk efisiensi
            success_count = sum(1 for line in lines if ' 200 ' in line)
            return success_count  # Throughput sebagai count sederhana
        except FileNotFoundError:
            return 0  # Fallback jika log tidak ada

    def get_state(self):
        # Gabungkan ke state diskrit: traffic_load * 3 + cpu_state (0-8).
        traffic_load = self.get_packet_rate()
        cpu_state = self.get_cpu_ram_state()
        state = traffic_load * 3 + cpu_state
        return state, self.get_throughput_legal(), cpu_state  # Return tambahan untuk reward