import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import csv

def plot_throughput_vs_time(csv_file='agent_log.csv'):
    times = []
    throughputs = []
    start_time = None
    
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            timestamp = float(row['time'])
            if start_time is None:
                start_time = timestamp
            times.append(timestamp - start_time)
            throughputs.append(float(row['throughput']))
    
    plt.figure(figsize=(12, 6))
    plt.plot(times, throughputs, linewidth=2, color='#2E86AB')
    plt.xlabel('Time (seconds)', fontsize=12)
    plt.ylabel('Legal Packet Throughput', fontsize=12)
    plt.title('Dynamic Firewall - Legal Packet Throughput Over Time', fontsize=14, fontweight='bold')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig('throughput_plot.png', dpi=150)
    plt.close()
    print("Graph saved: throughput_plot.png")
