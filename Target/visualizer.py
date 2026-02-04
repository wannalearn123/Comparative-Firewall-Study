import matplotlib.pyplot as plt
import csv

def plot_throughput_vs_time(csv_file='agent_log.csv'):
    """
    Plot line chart throughput vs waktu dari CSV dan simpan sebagai file gambar.
    """
    times = []
    throughputs = []
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            times.append(float(row['time']))
            throughputs.append(float(row['throughput']))
    plt.plot(times, throughputs)
    plt.xlabel('Time (seconds)')
    plt.ylabel('Throughput Legal')
    plt.title('Throughput vs Time')
    plt.savefig('throughput_plot.png')  # Simpan sebagai PNG
    print("Plot saved as throughput_plot.png")  # Konfirmasi
    # plt.show()  # Komentar atau hapus ini untuk container