#!/usr/bin/env python3
"""
Static Firewall: Firewall dengan aturan tetap untuk perbandingan dengan Dynamic Firewall.
Dijalankan di container Target (172.20.0.10)
"""

import subprocess
import time
import psutil
import argparse
import csv
import os
from datetime import datetime

class StaticFirewall:
    """
    Firewall statis dengan rate limit tetap.
    Tidak adaptif - menggunakan rate limit yang sama sepanjang waktu.
    """
    
    def __init__(self, rate_limit=50, log_file='/app/static_firewall_log.csv', mock_mode=False):
        """
        Args:
            rate_limit: Jumlah request per detik yang diizinkan
            log_file: Path file log CSV
            mock_mode: Jika True, simulasi tanpa iptables nyata
        """
        self.rate_limit = rate_limit
        self.log_file = log_file
        self.mock_mode = mock_mode
        self.running = True
        self.start_time = None
        
        # Data untuk logging
        self.log_data = []
        
        # Statistik
        self.total_accepted = 0
        self.total_dropped = 0
        self.last_log_position = 0
        
        print(f"[STATIC FIREWALL] Rate Limit: {rate_limit} req/sec (FIXED)")
        print(f"[STATIC FIREWALL] Log file: {log_file}")
        print(f"[STATIC FIREWALL] Mock mode: {mock_mode}")
    
    def setup_rules(self):
        """Setup iptables rules dengan rate limit statis."""
        if self.mock_mode:
            print(f"[STATIC FIREWALL] MOCK: Rate limit {self.rate_limit}/sec applied")
            return True
        
        try:
            # Flush existing rules
            subprocess.run(['iptables', '-F'], check=True, capture_output=True)
            subprocess.run(['iptables', '-X'], check=True, capture_output=True)
            subprocess.run(['iptables', '-Z'], check=True, capture_output=True)
            
            # Set default policies
            subprocess.run(['iptables', '-P', 'INPUT', 'ACCEPT'], check=True, capture_output=True)
            subprocess.run(['iptables', '-P', 'OUTPUT', 'ACCEPT'], check=True, capture_output=True)
            subprocess.run(['iptables', '-P', 'FORWARD', 'ACCEPT'], check=True, capture_output=True)
            
            # Allow loopback
            subprocess.run(['iptables', '-A', 'INPUT', '-i', 'lo', '-j', 'ACCEPT'], 
                         check=True, capture_output=True)
            
            # Allow established connections
            subprocess.run([
                'iptables', '-A', 'INPUT',
                '-m', 'state', '--state', 'ESTABLISHED,RELATED',
                '-j', 'ACCEPT'
            ], check=True, capture_output=True)
            
            # Rate limit untuk port 80 (HTTP)
            subprocess.run([
                'iptables', '-A', 'INPUT',
                '-p', 'tcp', '--dport', '80',
                '-m', 'limit', '--limit', f'{self.rate_limit}/sec', 
                '--limit-burst', str(self.rate_limit * 2),
                '-j', 'ACCEPT'
            ], check=True, capture_output=True)
            
            # Drop excess traffic ke port 80
            subprocess.run([
                'iptables', '-A', 'INPUT',
                '-p', 'tcp', '--dport', '80',
                '-j', 'DROP'
            ], check=True, capture_output=True)
            
            print(f"[STATIC FIREWALL] iptables rules applied successfully")
            print(f"[STATIC FIREWALL] Rate limit: {self.rate_limit} req/sec on port 80")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"[STATIC FIREWALL] ERROR: iptables setup failed: {e}")
            print("[STATIC FIREWALL] Switching to mock mode")
            self.mock_mode = True
            return False
    
    def get_system_metrics(self):
        """Ambil metrik sistem (CPU, RAM)."""
        cpu_percent = psutil.cpu_percent(interval=0.5)
        ram_percent = psutil.virtual_memory().percent
        return cpu_percent, ram_percent
    
    def get_packet_stats(self):
        """Ambil statistik packet dari iptables."""
        if self.mock_mode:
            return self.total_accepted, self.total_dropped
        
        try:
            result = subprocess.run(
                ['iptables', '-L', 'INPUT', '-v', '-n', '-x'],
                capture_output=True, text=True, check=True
            )
            
            accepted = 0
            dropped = 0
            
            for line in result.stdout.split('\n'):
                if 'dpt:80' in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        try:
                            pkts = int(parts[0])
                            if 'ACCEPT' in line:
                                accepted = pkts
                            elif 'DROP' in line:
                                dropped = pkts
                        except (ValueError, IndexError):
                            pass
            
            self.total_accepted = accepted
            self.total_dropped = dropped
            return accepted, dropped
            
        except Exception as e:
            return self.total_accepted, self.total_dropped
    
    def get_throughput_from_nginx(self):
        """Ambil throughput dari log Nginx (request dengan status 200)."""
        try:
            log_paths = [
                '/var/log/nginx/access.log',
                '/var/log/httpd/access_log',
                '/var/log/access.log'
            ]
            
            log_path = None
            for path in log_paths:
                if os.path.exists(path):
                    log_path = path
                    break
            
            if not log_path:
                return 0
            
            with open(log_path, 'r') as f:
                f.seek(self.last_log_position)
                lines = f.readlines()
                self.last_log_position = f.tell()
            
            # Hitung request dengan status 200
            success_count = 0
            for line in lines:
                if '" 200 ' in line or ' 200 ' in line:
                    success_count += 1
            
            return success_count
            
        except Exception as e:
            return 0
    
    def log_entry(self, elapsed_time, cpu, ram, throughput, accepted, dropped):
        """Log entry ke buffer."""
        self.log_data.append({
            'time': round(elapsed_time, 2),
            'cpu_percent': round(cpu, 2),
            'ram_percent': round(ram, 2),
            'throughput': throughput,
            'packets_accepted': accepted,
            'packets_dropped': dropped,
            'rate_limit': self.rate_limit,
            'firewall_type': 'static'
        })
    
    def save_logs(self):
        """Simpan log ke CSV."""
        try:
            os.makedirs(os.path.dirname(self.log_file) if os.path.dirname(self.log_file) else '.', exist_ok=True)
            with open(self.log_file, 'w', newline='') as f:
                if self.log_data:
                    writer = csv.DictWriter(f, fieldnames=self.log_data[0].keys())
                    writer.writeheader()
                    writer.writerows(self.log_data)
            print(f"[STATIC FIREWALL] Log saved: {self.log_file} ({len(self.log_data)} entries)")
        except Exception as e:
            print(f"[STATIC FIREWALL] Error saving log: {e}")
    
    def run(self, duration=300, interval=5):
        """
        Jalankan static firewall monitoring.
        
        Args:
            duration: Durasi monitoring dalam detik
            interval: Interval polling dalam detik
        """
        print(f"\n{'='*60}")
        print(f"[STATIC FIREWALL] STARTING MONITORING")
        print(f"[STATIC FIREWALL] Rate Limit: {self.rate_limit} req/sec (FIXED)")
        print(f"[STATIC FIREWALL] Duration: {duration} seconds")
        print(f"[STATIC FIREWALL] Interval: {interval} seconds")
        print(f"{'='*60}\n")
        
        # Setup rules sekali di awal
        self.setup_rules()
        
        self.start_time = time.time()
        iteration = 0
        
        try:
            while self.running and (time.time() - self.start_time) < duration:
                iteration += 1
                elapsed = time.time() - self.start_time
                
                # Ambil metrik
                cpu, ram = self.get_system_metrics()
                accepted, dropped = self.get_packet_stats()
                throughput = self.get_throughput_from_nginx()
                
                # Log
                self.log_entry(elapsed, cpu, ram, throughput, accepted, dropped)
                
                # Print status
                drop_rate = (dropped / (accepted + dropped) * 100) if (accepted + dropped) > 0 else 0
                print(f"[STATIC FW] {elapsed:6.1f}s | Iter: {iteration:3d} | "
                      f"CPU: {cpu:5.1f}% | RAM: {ram:5.1f}% | "
                      f"Throughput: {throughput:4d} | "
                      f"Accept: {accepted:6d} | Drop: {dropped:6d} ({drop_rate:.1f}%) | "
                      f"Rate: {self.rate_limit}/sec")
                
                # Save log setiap 60 detik
                if iteration % (60 // interval) == 0:
                    self.save_logs()
                
                time.sleep(interval)
        
        except KeyboardInterrupt:
            print("\n[STATIC FIREWALL] Interrupted by user")
        
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Graceful shutdown."""
        self.running = False
        self.save_logs()
        self.print_summary()
        self.cleanup()
    
    def print_summary(self):
        """Print ringkasan."""
        total_time = time.time() - self.start_time if self.start_time else 0
        total_throughput = sum(entry['throughput'] for entry in self.log_data)
        avg_throughput = total_throughput / len(self.log_data) if self.log_data else 0
        drop_rate = (self.total_dropped / (self.total_accepted + self.total_dropped) * 100) if (self.total_accepted + self.total_dropped) > 0 else 0
        
        print(f"\n{'='*60}")
        print(f"[STATIC FIREWALL] SUMMARY")
        print(f"{'='*60}")
        print(f"  Duration:         {total_time:.1f} seconds")
        print(f"  Rate Limit:       {self.rate_limit} req/sec (FIXED)")
        print(f"  Total Throughput: {total_throughput}")
        print(f"  Avg Throughput:   {avg_throughput:.2f} per interval")
        print(f"  Packets Accepted: {self.total_accepted}")
        print(f"  Packets Dropped:  {self.total_dropped}")
        print(f"  Drop Rate:        {drop_rate:.1f}%")
        print(f"  Log File:         {self.log_file}")
        print(f"{'='*60}")
    
    def cleanup(self):
        """Reset iptables ke default."""
        if self.mock_mode:
            print("[STATIC FIREWALL] MOCK: Rules cleaned up")
            return
        
        try:
            subprocess.run(['iptables', '-F'], check=True, capture_output=True)
            subprocess.run(['iptables', '-X'], check=True, capture_output=True)
            subprocess.run(['iptables', '-P', 'INPUT', 'ACCEPT'], check=True, capture_output=True)
            print("[STATIC FIREWALL] iptables rules cleaned up")
        except subprocess.CalledProcessError as e:
            print(f"[STATIC FIREWALL] WARNING: Cleanup failed: {e}")
    
    def stop(self):
        """Stop monitoring."""
        self.running = False


def main():
    parser = argparse.ArgumentParser(description='Static Firewall dengan Rate Limit Tetap')
    parser.add_argument('--rate', type=int, default=50, 
                        help='Rate limit per detik (default: 50)')
    parser.add_argument('--duration', type=int, default=300, 
                        help='Durasi monitoring dalam detik (default: 300)')
    parser.add_argument('--interval', type=int, default=5, 
                        help='Interval polling dalam detik (default: 5)')
    parser.add_argument('--log', type=str, default='/app/static_firewall_log.csv', 
                        help='Log file path')
    parser.add_argument('--mock', action='store_true', 
                        help='Gunakan mock mode (tanpa iptables)')
    
    args = parser.parse_args()
    
    firewall = StaticFirewall(
        rate_limit=args.rate,
        log_file=args.log,
        mock_mode=args.mock
    )
    
    firewall.run(duration=args.duration, interval=args.interval)


if __name__ == "__main__":
    main()