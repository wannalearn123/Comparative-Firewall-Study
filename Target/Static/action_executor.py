import subprocess

class ActionExecutor:
    """
    Kelas untuk eksekusi aturan firewall statis dengan rate limit tetap.
    Berbeda dengan Dynamic, rate limit TIDAK berubah selama runtime.
    """
    def __init__(self, rate_limit=50):
        self.rate_limit = rate_limit
        self.rules_applied = False

    def apply_static_rules(self):
        """Apply aturan firewall statis dengan rate limit tetap."""
        try:
            # Flush rules
            subprocess.run(['iptables', '-F'], check=True)
            subprocess.run(['iptables', '-X'], check=True)
            
            # Allow loopback
            subprocess.run(['iptables', '-A', 'INPUT', '-i', 'lo', '-j', 'ACCEPT'], check=True)
            
            # Allow established connections
            subprocess.run([
                'iptables', '-A', 'INPUT', '-m', 'state', 
                '--state', 'ESTABLISHED,RELATED', '-j', 'ACCEPT'
            ], check=True)
            
            # Rate limit pada port 80
            subprocess.run([
                'iptables', '-A', 'INPUT', '-p', 'tcp', '--dport', '80',
                '-m', 'limit', '--limit', f'{self.rate_limit}/sec',
                '--limit-burst', str(self.rate_limit * 2),
                '-j', 'ACCEPT'
            ], check=True)
            
            # Drop sisanya
            subprocess.run([
                'iptables', '-A', 'INPUT', '-p', 'tcp', '--dport', '80',
                '-j', 'DROP'
            ], check=True)
            
            self.rules_applied = True
            print(f"[ACTION] Static firewall applied: {self.rate_limit}/sec (FIXED)")
            
        except subprocess.CalledProcessError as e:
            print(f"[ACTION] Error applying rules: {e}")

    def cleanup(self):
        """Reset iptables ke default."""
        try:
            subprocess.run(['iptables', '-F'], check=True)
            subprocess.run(['iptables', '-X'], check=True)
            subprocess.run(['iptables', '-P', 'INPUT', 'ACCEPT'], check=True)
            self.rules_applied = False
            print("[ACTION] Firewall rules cleaned up")
        except subprocess.CalledProcessError as e:
            print(f"[ACTION] Error cleanup: {e}")