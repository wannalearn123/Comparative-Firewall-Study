import subprocess
import re

class ActionExecutor:
    """
    Kelas untuk eksekusi aksi ke iptables: A0 (allow all), A1 (rate limit moderate), A2 (strict), A3 (block high offender).
    """
    def __init__(self, interface='eth0'):
        self.interface = interface

    def execute_action(self, action):
        """Eksekusi action berdasarkan ID."""
        try:
            if action == 0:  # A0: Allow all
                subprocess.run(['iptables', '-F'], check=True)  # Flush rules
                subprocess.run(['iptables', '-P', 'INPUT', 'ACCEPT'], check=True)
            elif action == 1:  # A1: Rate limit moderate (50/sec)
                subprocess.run(['iptables', '-F'], check=True)
                subprocess.run(['iptables', '-A', 'INPUT', '-p', 'tcp', '--dport', '80', '-m', 'limit', '--limit', '50/sec', '-j', 'ACCEPT'], check=True)
                subprocess.run(['iptables', '-A', 'INPUT', '-p', 'tcp', '--dport', '80', '-j', 'DROP'], check=True)
            elif action == 2:  # A2: Rate limit strict (10/sec)
                subprocess.run(['iptables', '-F'], check=True)
                subprocess.run(['iptables', '-A', 'INPUT', '-p', 'tcp', '--dport', '80', '-m', 'limit', '--limit', '10/sec', '-j', 'ACCEPT'], check=True)
                subprocess.run(['iptables', '-A', 'INPUT', '-p', 'tcp', '--dport', '80', '-j', 'DROP'], check=True)
            elif action == 3:  # A3: Block high offender (top IP dari iptables -L -v)
                result = subprocess.run(['iptables', '-L', '-v'], capture_output=True, text=True)
                # Parse top IP (simplifikasi: asumsikan format standar, block IP pertama dengan trafik tinggi)
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'SRC=' in line:
                        ip_match = re.search(r'SRC=(\d+\.\d+\.\d+\.\d+)', line)
                        if ip_match:
                            ip = ip_match.group(1)
                            subprocess.run(['iptables', '-A', 'INPUT', '-s', ip, '-j', 'DROP'], check=True)
                            break
        except subprocess.CalledProcessError as e:
            print(f"Error executing action {action}: {e}")  # Log error, lanjutkan