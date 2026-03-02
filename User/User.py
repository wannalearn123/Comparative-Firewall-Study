#!/usr/bin/env python3
import time
import random
import argparse
import csv
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class LegitimateUser:
    def __init__(self, target_ip="172.20.0.10", target_port=80, log_file="/app/user_log.csv"):
        self.target_ip = target_ip
        self.target_port = target_port
        self.target_url = f"http://{target_ip}:{target_port}/"
        self.log_file = log_file
        self.results = []
        self.running = True
        
        self.session = requests.Session()
        retry = Retry(total=0, backoff_factor=0)
        adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
        self.session.mount('http://', adapter)
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        })
        
        self.total_requests = 0
        self.success_requests = 0
        self.failed_requests = 0
        self.blocked_requests = 0
        
        print(f"[USER] Target: {self.target_url}")
    
    def log_request(self, status, response_time, timestamp):
        self.results.append({
            'timestamp': timestamp,
            'request_type': 'legitimate',
            'status': status,
            'response_time': response_time,
            'target': self.target_url
        })
    
    def save_logs(self):
        with open(self.log_file, 'w', newline='') as f:
            if self.results:
                writer = csv.DictWriter(f, fieldnames=self.results[0].keys())
                writer.writeheader()
                writer.writerows(self.results)
        print(f"[USER] Log saved: {len(self.results)} entries")
    
    def send_request(self):
        timestamp = datetime.now().isoformat()
        start_time = time.time()
        
        try:
            response = self.session.get(self.target_url, timeout=5)
            status = response.status_code
            response_time = time.time() - start_time
        except requests.exceptions.Timeout:
            status = 0
            response_time = 5.0
        except requests.exceptions.ConnectionError:
            status = 503
            response_time = time.time() - start_time
        except Exception:
            status = 0
            response_time = time.time() - start_time
        
        self.total_requests += 1
        if status == 200:
            self.success_requests += 1
        elif status in (503, 429):
            self.blocked_requests += 1
        else:
            self.failed_requests += 1
        
        self.log_request(status, response_time, timestamp)
        return status, response_time
    
    def browse_normally(self, duration=600, min_interval=0.3, max_interval=2.0):
        print(f"\n[USER] NORMAL BROWSING | Duration: {duration}s | Interval: {min_interval}-{max_interval}s\n")
        
        start_time = time.time()
        last_print = start_time
        
        while time.time() - start_time < duration and self.running:
            status, response_time = self.send_request()
            
            current_time = time.time()
            if current_time - last_print >= 10:
                elapsed = current_time - start_time
                success_rate = (self.success_requests / self.total_requests * 100) if self.total_requests > 0 else 0
                print(f"[USER] {elapsed:6.1f}s | Req: {self.total_requests:4d} | "
                      f"Success: {success_rate:.1f}% | RT: {response_time:.3f}s")
                last_print = current_time
            
            interval = random.uniform(min_interval, max_interval)
            time.sleep(interval)
        
        self.print_summary()
    
    def concurrent_users(self, duration=600, num_users=3, requests_per_user=200):
        print(f"\n[USER] CONCURRENT USERS | Users: {num_users} | Duration: {duration}s\n")
        
        def user_session(user_id):
            count = 0
            while count < requests_per_user and self.running:
                self.send_request()
                count += 1
                time.sleep(random.uniform(0.5, 2.0))
        
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=num_users) as executor:
            futures = [executor.submit(user_session, i) for i in range(num_users)]
            
            while time.time() - start_time < duration and self.running:
                time.sleep(10)
                success_rate = (self.success_requests / self.total_requests * 100) if self.total_requests > 0 else 0
                print(f"[USER] {time.time()-start_time:.0f}s | Total: {self.total_requests} | Success: {success_rate:.1f}%")
        
        self.print_summary()
    
    def print_summary(self):
        success_rate = (self.success_requests / self.total_requests * 100) if self.total_requests > 0 else 0
        blocked_rate = (self.blocked_requests / self.total_requests * 100) if self.total_requests > 0 else 0
        
        print(f"\n{'='*60}")
        print(f"[USER] SUMMARY")
        print(f"  Total: {self.total_requests} | Success: {self.success_requests} ({success_rate:.1f}%)")
        print(f"  Blocked: {self.blocked_requests} ({blocked_rate:.1f}%) | Failed: {self.failed_requests}")
        print(f"{'='*60}")
    
    def stop(self):
        self.running = False

def main():
    parser = argparse.ArgumentParser(description='Legitimate User Simulator')
    parser.add_argument('--target', type=str, default='172.20.0.10')
    parser.add_argument('--port', type=int, default=80)
    parser.add_argument('--mode', type=str, choices=['normal', 'concurrent'], default='normal')
    parser.add_argument('--duration', type=int, default=600)
    parser.add_argument('--users', type=int, default=3)
    parser.add_argument('--log', type=str, default='/app/user_log.csv')
    
    args = parser.parse_args()
    
    user = LegitimateUser(target_ip=args.target, target_port=args.port, log_file=args.log)
    
    try:
        if args.mode == 'normal':
            user.browse_normally(duration=args.duration)
        elif args.mode == 'concurrent':
            user.concurrent_users(duration=args.duration, num_users=args.users)
    except KeyboardInterrupt:
        print("\n[USER] Interrupted")
        user.stop()
    finally:
        user.save_logs()
        user.print_summary()

if __name__ == "__main__":
    main()
