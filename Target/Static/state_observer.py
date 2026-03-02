import psutil
import subprocess
import time
import re

class StateObserver:
    """
    Enhanced state observer with 15-state space and packet drop tracking.
    States: 3 traffic levels × 5 CPU levels = 15 states
    """
    def __init__(self, log_file_path='/var/log/nginx/access.log', interface='eth0'):
        self.log_file_path = self._validate_path(log_file_path)
        self.interface = self._validate_interface(interface)
        self.last_packet_count = 0
        self.last_drop_count = 0
        self.last_time = time.time()
        self.prev_throughput = 0

    def _validate_interface(self, interface):
        if not re.match(r'^[a-zA-Z0-9]+$', interface):
            raise ValueError("Invalid interface name")
        return interface

    def _validate_path(self, path):
        if not re.match(r'^[a-zA-Z0-9/_.-]+$', path):
            raise ValueError("Invalid file path")
        return path

    def get_cpu_state(self):
        cpu_percent = psutil.cpu_percent(interval=0.5)
        if cpu_percent < 30:
            return 0
        elif cpu_percent < 50:
            return 1
        elif cpu_percent < 70:
            return 2
        elif cpu_percent < 85:
            return 3
        else:
            return 4

    def get_packet_rate_and_drops(self):
        try:
            result = subprocess.run(['iptables', '-L', 'INPUT', '-v', '-n', '-x'], 
                                  capture_output=True, text=True, timeout=2)
            lines = result.stdout.split('\n')
            
            total_packets = 0
            dropped_packets = 0
            
            for line in lines:
                if 'DROP' in line or 'REJECT' in line:
                    parts = line.split()
                    if len(parts) > 0 and parts[0].isdigit():
                        dropped_packets += int(parts[0])
                elif 'ACCEPT' in line or 'tcp dpt:80' in line:
                    parts = line.split()
                    if len(parts) > 0 and parts[0].isdigit():
                        total_packets += int(parts[0])
            
            current_time = time.time()
            time_delta = current_time - self.last_time
            
            packet_rate = (total_packets - self.last_packet_count) / time_delta if time_delta > 0 else 0
            drop_rate = (dropped_packets - self.last_drop_count) / time_delta if time_delta > 0 else 0
            
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
            result = subprocess.run(['tail', '-n', '200', self.log_file_path], 
                                  capture_output=True, text=True, timeout=2)
            lines = result.stdout.split('\n')
            
            recent_success = 0
            
            for line in lines:
                if ' 200 ' in line:
                    recent_success += 1
            
            return recent_success
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
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
