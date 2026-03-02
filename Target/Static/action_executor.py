import subprocess
import re

class ActionExecutor:
    """
    Enhanced action executor with 5 granular actions and connection limiting.
    A0: Allow all (100/s)
    A1: Light limit (50/s)
    A2: Moderate limit (25/s)
    A3: Strict limit (10/s)
    A4: Block top offender + strict limit
    """
    def __init__(self, interface='eth0'):
        self.interface = self._validate_interface(interface)
        self.blocked_ips = set()
        self.last_action = -1

    def _validate_interface(self, interface):
        if not re.match(r'^[a-zA-Z0-9]+$', interface):
            raise ValueError("Invalid interface name")
        return interface

    def _validate_ip(self, ip):
        pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if not re.match(pattern, ip):
            return False
        octets = ip.split('.')
        return all(0 <= int(octet) <= 255 for octet in octets)

    def execute_action(self, action):
        if not isinstance(action, int) or action < 0 or action > 4:
            return
        
        if action == self.last_action:
            return
        
        try:
            subprocess.run(['iptables', '-F', 'INPUT'], check=True, timeout=2)
            
            subprocess.run(['iptables', '-A', 'INPUT', '-m', 'conntrack', 
                          '--ctstate', 'ESTABLISHED,RELATED', '-j', 'ACCEPT'], 
                          check=True, timeout=2)
            
            if action == 0:
                subprocess.run(['iptables', '-A', 'INPUT', '-p', 'tcp', '--dport', '80',
                              '-m', 'limit', '--limit', '100/sec', '--limit-burst', '150',
                              '-j', 'ACCEPT'], check=True, timeout=2)
            elif action == 1:
                subprocess.run(['iptables', '-A', 'INPUT', '-p', 'tcp', '--dport', '80',
                              '-m', 'limit', '--limit', '50/sec', '--limit-burst', '75',
                              '-j', 'ACCEPT'], check=True, timeout=2)
            elif action == 2:
                subprocess.run(['iptables', '-A', 'INPUT', '-p', 'tcp', '--dport', '80',
                              '-m', 'limit', '--limit', '25/sec', '--limit-burst', '40',
                              '-j', 'ACCEPT'], check=True, timeout=2)
            elif action == 3:
                subprocess.run(['iptables', '-A', 'INPUT', '-p', 'tcp', '--dport', '80',
                              '-m', 'limit', '--limit', '10/sec', '--limit-burst', '20',
                              '-j', 'ACCEPT'], check=True, timeout=2)
            elif action == 4:
                top_ip = self._get_top_offender_ip()
                if top_ip and self._validate_ip(top_ip) and top_ip not in self.blocked_ips:
                    subprocess.run(['iptables', '-I', 'INPUT', '-s', top_ip, '-j', 'DROP'],
                                 check=True, timeout=2)
                    self.blocked_ips.add(top_ip)
                
                subprocess.run(['iptables', '-A', 'INPUT', '-p', 'tcp', '--dport', '80',
                              '-m', 'limit', '--limit', '10/sec', '--limit-burst', '15',
                              '-j', 'ACCEPT'], check=True, timeout=2)
            
            subprocess.run(['iptables', '-A', 'INPUT', '-p', 'tcp', '--dport', '80',
                          '-m', 'connlimit', '--connlimit-above', '20', '-j', 'REJECT'],
                          check=True, timeout=2)
            
            subprocess.run(['iptables', '-A', 'INPUT', '-p', 'tcp', '--dport', '80',
                          '-j', 'DROP'], check=True, timeout=2)
            
            self.last_action = action
            
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            print(f"Action {action} failed: {e}")

    def _get_top_offender_ip(self):
        try:
            result = subprocess.run(['netstat', '-ntu'], capture_output=True, 
                                  text=True, timeout=2)
            ip_counts = {}
            
            for line in result.stdout.split('\n'):
                match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):80\s+.*ESTABLISHED', line)
                if match:
                    ip = match.group(1)
                    if self._validate_ip(ip):
                        ip_counts[ip] = ip_counts.get(ip, 0) + 1
            
            if ip_counts:
                return max(ip_counts, key=ip_counts.get)
            return None
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            return None
