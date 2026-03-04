import psutil
import subprocess
import time
import os

class StateObserver:
    """
    Enhanced state observer with 15-state space and packet drop tracking.
    States: 3 traffic levels × 5 CPU levels = 15 states
    """
    def __init__(self, log_file_path='/var/log/nginx/access.log',
                 interface='eth0'):
        self.log_file_path = log_file_path
        self.interface = interface
        self.last_packet_count = 0
        self.last_drop_count = 0
        self.last_time = time.time()
        self.prev_throughput = 0
        self.process = psutil.Process(os.getpid())
        self.last_cpu_time = self.process.cpu_times()


    def get_cpu_state(self):
        try:
            current_cpu_time = self.process.cpu_times()
            cpu_delta = (current_cpu_time.user - self.last_cpu_time.user) + \
                       (current_cpu_time.system - self.last_cpu_time.system)
            
            time_delta = time.time() - self.last_time
            cpu_percent = (cpu_delta / time_delta) * 100 if time_delta > 0 else 0
            
            cpu_percent = min(cpu_percent, 100)
            
            if cpu_percent < 30:
                return 0
            elif cpu_percent < 50:
                return 1
            elif cpu_percent < 70:
                return 2
            elif cpu_percent < 85:
                return 3
            return 4
        except:
            return 0

    def get_packet_rate_and_drops(self):
        try:
            result = subprocess.run(
                ['iptables', '-L', 'INPUT', '-v', '-n', '-x'],
                capture_output=True, text=True, timeout=2)
            lines = result.stdout.split('\n')
            
            total_packets = 0
            dropped_packets = 0
            
            for line in lines:
                parts = line.split()
                if len(parts) > 0 and parts[0].isdigit():
                    if 'DROP' in line or 'REJECT' in line:
                        dropped_packets += int(parts[0])
                    elif 'ACCEPT' in line or 'tcp dpt:80' in line:
                        total_packets += int(parts[0])
            
            current_time = time.time()
            time_delta = current_time - self.last_time
            
            if time_delta > 0:
                packet_rate = (total_packets - self.last_packet_count) / \
                             time_delta
                drop_rate = (dropped_packets - self.last_drop_count) / \
                           time_delta
            else:
                packet_rate = 0
                drop_rate = 0
            
            self.last_packet_count = total_packets
            self.last_drop_count = dropped_packets
            self.last_time = current_time
            
            if packet_rate < 50:
                traffic_load = 0
            elif packet_rate < 200:
                traffic_load = 1
            else:
                traffic_load = 2
            
            drop_percent = (drop_rate / (packet_rate + 1)) * 100
            
            return traffic_load, drop_percent
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            return 0, 0

    def get_throughput_legal(self):
        try:
            result = subprocess.run(
                ['tail', '-n', '200', self.log_file_path],
                capture_output=True, text=True, timeout=2)
            lines = result.stdout.split('\n')
            
            recent_success = sum(1 for line in lines if ' 200 ' in line)
            return recent_success
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError,
                FileNotFoundError):
            return 0

    def get_state(self):
        traffic_load, drop_percent = self.get_packet_rate_and_drops()
        cpu_state = self.get_cpu_state()
        throughput = self.get_throughput_legal()
        
        state = traffic_load * 5 + cpu_state
        
        result = (state, throughput, psutil.cpu_percent(interval=0),
                 drop_percent, self.prev_throughput)
        self.prev_throughput = throughput
        
        return result
