import time
import csv
from state_observer import StateObserver
from action_executor import ActionExecutor
from visualizer import plot_throughput_vs_time

class StaticFirewall:
    """
    Main class untuk Static Firewall.
    Assembler dari StateObserver, ActionExecutor, dan Visualizer.
    """
    
    def __init__(self, rate_limit=50, duration=300, interval=5):
        self.duration = duration
        self.interval = interval
        self.observer = StateObserver()
        self.executor = ActionExecutor(rate_limit=rate_limit)
        self.log_data = []
    
    def run(self):
        # Jalankan static firewall.
        print(f"\n[STATIC FIREWALL] Starting...")
        print(f"[STATIC FIREWALL] Rate Limit: {self.executor.rate_limit}/sec (FIXED)")
        print(f"[STATIC FIREWALL] Duration: {self.duration}s\n")
        
        # Apply rules sekali di awal
        self.executor.apply_static_rules()
        
        start_time = time.time()
        
        while (time.time() - start_time) < self.duration:
            elapsed = time.time() - start_time
            
            # Observe
            state, throughput, cpu_state = self.observer.get_state()
            
            # Log
            self.log_data.append({
                'time': round(elapsed, 2),
                'state': state,
                'throughput': throughput
            })
            
            print(f"[STATIC FW] Time: {elapsed:6.1f}s | State: {state} | Throughput: {throughput}")
            
            time.sleep(self.interval)
        
        self.shutdown()
    
    def shutdown(self):
        # Cleanup dan generate plot.
        # Save log
        with open('static_log.csv', 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['time', 'state', 'throughput'])
            writer.writeheader()
            writer.writerows(self.log_data)
        print(f"\n[STATIC FIREWALL] Log saved to static_log.csv")
        
        # Generate plot
        plot_throughput_vs_time('static_log.csv')
        
        # Cleanup rules
        self.executor.cleanup()
        print("[STATIC FIREWALL] Stopped\n")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Static Firewall')
    parser.add_argument('--rate', type=int, default=50, help='Rate limit per detik')
    parser.add_argument('--duration', type=int, default=300, help='Durasi dalam detik')
    parser.add_argument('--interval', type=int, default=5, help='Interval polling')
    
    args = parser.parse_args()
    
    firewall = StaticFirewall(
        rate_limit=args.rate,
        duration=args.duration,
        interval=args.interval
    )
    firewall.run()