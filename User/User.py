#!/usr/bin/env python3
"""
Legitimate User Simulator: Mensimulasikan traffic user normal.
Dijalankan di container User (172.20.0.12)
"""

import subprocess
import time
import random
import argparse
import csv
import os
from datetime import datetime

class LegitimateUser:
    """
    Simulator user legitimate untuk testing firewall.
    Mengirim traffic dengan pola normal (tidak agresif).
    """
    
    def __init__(self, target_ip="172.20.0.10", target_port=80, log_file="/app/user_log.csv"):
        self.target_ip = target_ip
        self.target_port = target_port
        self.target_url = f"http://{target_ip}:{target_port}/"
        self.log_file = log_file
        self.results = []
        self.running = True
        
        # Statistik
        self.total_requests = 0
        self.success_requests = 0
        self.failed_requests = 0
        self.blocked_requests = 0
        
        print(f"[USER] Target: {self.target_url}")
        print(f"[USER] Log file: {self.log_file}")
    
    def log_request(self, status, response_time, timestamp):
        """Log hasil request."""
        self.results.append({
            'timestamp': timestamp,
            'request_type': 'legitimate',
            'status': status,
            'response_time': response_time,
            'target': self.target_url
        })
    
    def save_logs(self):
        """Simpan log ke CSV."""
        os.makedirs(os.path.dirname(self.log_file) if os.path.dirname(self.log_file) else '.', exist_ok=True)
        with open(self.log_file, 'w', newline='') as f:
            if self.results:
                writer = csv.DictWriter(f, fieldnames=self.results[0].keys())
                writer.writeheader()
                writer.writerows(self.results)
        print(f"[USER] Log saved: {self.log_file} ({len(self.results)} entries)")
    
    def send_request(self):
        """Kirim single HTTP request seperti user normal."""
        timestamp = datetime.now().isoformat()
        start_time = time.time()
        
        try:
            result = subprocess.run(
                ['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}',
                 '--connect-timeout', '5', '--max-time', '10',
                 '-H', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                 '-H', 'Accept: text/html,application/xhtml+xml',
                 self.target_url],
                capture_output=True,
                text=True,
                timeout=15
            )
            status = int(result.stdout.strip()) if result.stdout.strip().isdigit() else 0
            response_time = time.time() - start_time
        except Exception as e:
            status = 0
            response_time = time.time() - start_time
        
        # Update statistik
        self.total_requests += 1
        if status == 200:
            self.success_requests += 1
        elif status == 503 or status == 429:
            self.blocked_requests += 1
        else:
            self.failed_requests += 1
        
        self.log_request(status, response_time, timestamp)
        return status, response_time
    
    def browse_normally(self, duration=300, min_interval=0.5, max_interval=3.0):
        """
        Simulasi browsing normal dengan interval acak.
        Seperti user manusia yang membaca halaman sebelum klik lagi.
        
        Args:
            duration: Durasi browsing (detik)
            min_interval: Minimum interval antar request (detik)
            max_interval: Maximum interval antar request (detik)
        """
        print(f"\n{'='*60}")
        print(f"[USER] NORMAL BROWSING MODE")
        print(f"[USER] Duration: {duration}s | Interval: {min_interval}-{max_interval}s")
        print(f"{'='*60}\n")
        
        start_time = time.time()
        
        while time.time() - start_time < duration and self.running:
            status, response_time = self.send_request()
            
            # Status indicator
            if status == 200:
                indicator = "✓"
            elif status == 503 or status == 429:
                indicator = "⊘ (rate limited)"
            else:
                indicator = "✗"
            
            elapsed = time.time() - start_time
            success_rate = (self.success_requests / self.total_requests * 100) if self.total_requests > 0 else 0
            
            print(f"[USER] {elapsed:6.1f}s | Request #{self.total_requests:4d} | "
                  f"Status: {status} {indicator} | RT: {response_time:.3f}s | "
                  f"Success Rate: {success_rate:.1f}%")
            
            # Random interval seperti user manusia
            interval = random.uniform(min_interval, max_interval)
            time.sleep(interval)
        
        self.print_summary()
    
    def burst_activity(self, duration=60, requests_per_burst=5, burst_interval=10):
        """
        Simulasi aktivitas burst (misalnya, user membuka beberapa tab sekaligus).
        
        Args:
            duration: Total durasi (detik)
            requests_per_burst: Jumlah request per burst
            burst_interval: Interval antar burst (detik)
        """
        print(f"\n{'='*60}")
        print(f"[USER] BURST ACTIVITY MODE")
        print(f"[USER] Duration: {duration}s | {requests_per_burst} req/burst every {burst_interval}s")
        print(f"{'='*60}\n")
        
        start_time = time.time()
        burst_count = 0
        
        while time.time() - start_time < duration and self.running:
            burst_count += 1
            print(f"\n[USER] --- Burst #{burst_count} ---")
            
            # Kirim beberapa request cepat
            for i in range(requests_per_burst):
                status, response_time = self.send_request()
                indicator = "✓" if status == 200 else "✗"
                print(f"[USER]   Request {i+1}/{requests_per_burst}: {status} {indicator}")
                time.sleep(0.1)  # Sedikit delay antar request dalam burst
            
            # Tunggu sebelum burst berikutnya
            print(f"[USER] Waiting {burst_interval}s before next burst...")
            time.sleep(burst_interval)
        
        self.print_summary()
    
    def mixed_behavior(self, total_duration=300):
        """
        Simulasi perilaku mixed: browsing normal + occasional burst.
        Lebih realistis untuk mensimulasikan user sebenarnya.
        
        Timeline:
        - 0-120s: Normal browsing
        - 120-180s: Burst activity (user aktif)
        - 180-300s: Normal browsing lagi
        """
        print(f"\n{'#'*60}")
        print(f"[USER] MIXED BEHAVIOR SCENARIO")
        print(f"[USER] Total Duration: {total_duration}s")
        print(f"{'#'*60}\n")
        
        # Phase 1: Normal
        print("\n--- PHASE 1: NORMAL BROWSING (0-120s) ---")
        self.browse_normally(duration=120, min_interval=1.0, max_interval=3.0)
        
        if not self.running:
            return
        
        # Phase 2: Burst
        print("\n--- PHASE 2: BURST ACTIVITY (120-180s) ---")
        self.burst_activity(duration=60, requests_per_burst=5, burst_interval=10)
        
        if not self.running:
            return
        
        # Phase 3: Normal lagi
        print("\n--- PHASE 3: NORMAL BROWSING (180-300s) ---")
        self.browse_normally(duration=120, min_interval=1.0, max_interval=3.0)
        
        self.save_logs()
        
        print(f"\n{'#'*60}")
        print(f"[USER] MIXED BEHAVIOR COMPLETED")
        print(f"{'#'*60}")
    
    def print_summary(self):
        """Print ringkasan statistik."""
        success_rate = (self.success_requests / self.total_requests * 100) if self.total_requests > 0 else 0
        blocked_rate = (self.blocked_requests / self.total_requests * 100) if self.total_requests > 0 else 0
        
        print(f"\n{'='*60}")
        print(f"[USER] SESSION SUMMARY")
        print(f"{'='*60}")
        print(f"  Total Requests:   {self.total_requests}")
        print(f"  Successful (200): {self.success_requests} ({success_rate:.1f}%)")
        print(f"  Blocked (503):    {self.blocked_requests} ({blocked_rate:.1f}%)")
        print(f"  Failed (other):   {self.failed_requests}")
        print(f"{'='*60}")
    
    def stop(self):
        """Stop browsing."""
        self.running = False
        print("[USER] Stopping...")


def main():
    parser = argparse.ArgumentParser(description='Legitimate User Simulator')
    parser.add_argument('--target', type=str, default='172.20.0.10', help='Target IP address')
    parser.add_argument('--port', type=int, default=80, help='Target port')
    parser.add_argument('--mode', type=str,
                        choices=['normal', 'burst', 'mixed', 'continuous'],
                        default='normal', help='Browsing mode')
    parser.add_argument('--duration', type=int, default=300, help='Duration (seconds)')
    parser.add_argument('--min-interval', type=float, default=0.5, help='Min interval between requests')
    parser.add_argument('--max-interval', type=float, default=3.0, help='Max interval between requests')
    parser.add_argument('--log', type=str, default='/app/user_log.csv', help='Log file path')
    
    args = parser.parse_args()
    
    user = LegitimateUser(
        target_ip=args.target,
        target_port=args.port,
        log_file=args.log
    )
    
    try:
        if args.mode == 'normal':
            user.browse_normally(
                duration=args.duration,
                min_interval=args.min_interval,
                max_interval=args.max_interval
            )
        elif args.mode == 'burst':
            user.burst_activity(duration=args.duration)
        elif args.mode == 'mixed':
            user.mixed_behavior(total_duration=args.duration)
        elif args.mode == 'continuous':
            print("[USER] Continuous mode - Press Ctrl+C to stop")
            while user.running:
                user.browse_normally(duration=60, min_interval=args.min_interval, max_interval=args.max_interval)
    except KeyboardInterrupt:
        print("\n[USER] Interrupted by user")
        user.stop()
    finally:
        user.save_logs()
        user.print_summary()


if __name__ == "__main__":
    main()