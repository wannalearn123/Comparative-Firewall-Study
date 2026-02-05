import csv
import time

class Logger:
    """
    Kelas untuk logging buffer in-memory dan output periodik ke CSV.
    """
    def __init__(self, csv_file='agent_log.csv'):
        self.csv_file = csv_file
        self.buffer = []  # List of dicts: {'time': ..., 'state': ..., 'action': ..., 'reward': ..., 'throughput': ...}

    def log_entry(self, state, action, reward, throughput):
        """Tambah entry ke buffer."""
        self.buffer.append({
            'time': time.time(),
            'state': state,
            'action': action,
            'reward': reward,
            'throughput': throughput
        })

    def flush_to_csv(self):
        """Flush buffer ke CSV secara periodik."""
        if self.buffer:
            with open(self.csv_file, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['time', 'state', 'action', 'reward', 'throughput'])
                if f.tell() == 0:  # Jika file kosong, tulis header
                    writer.writeheader()
                writer.writerows(self.buffer)
            self.buffer.clear()  # Clear buffer setelah flush