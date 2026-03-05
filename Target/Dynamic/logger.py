import csv
import time

class Logger:
    def __init__(self, csv_file='agent_log.csv'):
        self.csv_file = csv_file
        self.buffer = []
        
        with open(self.csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['time', 'state', 
                                                   'action', 'reward', 
                                                   'throughput', 'epsilon'])
            writer.writeheader()

    def log_entry(self, state, action, reward, throughput, epsilon):
        self.buffer.append({
            'time': time.time(),
            'state': state,
            'action': action,
            'reward': reward,
            'throughput': throughput,
            'epsilon': epsilon
        })

    def flush_to_csv(self):
        if self.buffer:
            with open(self.csv_file, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['time', 'state', 
                                                       'action', 'reward', 
                                                       'throughput', 'epsilon'])
                writer.writerows(self.buffer)
            self.buffer.clear()
