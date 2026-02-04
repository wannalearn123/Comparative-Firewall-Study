# Comparative Firewall Simulation

Proyek simulasi perbandingan firewall statis dan dinamis untuk melindungi server web dari serangan DDoS. Menggunakan Docker containers untuk mensimulasikan target (server), attacker (penyerang), dan user (pengguna legitimate).

## Arsitektur

Proyek ini terdiri dari tiga komponen utama:

- **Target** (172.20.0.10): Server Nginx dengan dua jenis firewall
  - Static Firewall: Rate limit tetap (50 req/sec)
  - Dynamic Firewall: Agen Reinforcement Learning (Q-Learning) yang adaptif
- **Attacker** (172.20.0.11): Simulator serangan DDoS (HTTP Flood, Slowloris, SYN Flood)
- **User** (172.20.0.12): Simulator traffic legitimate (normal browsing, burst activity)

## Fitur

### Firewall Statis
- Rate limit tetap pada port 80
- Logging throughput, CPU, RAM, dan statistik paket
- Menggunakan iptables untuk kontrol traffic

### Firewall Dinamis (RL Agent)
- Agen Q-Learning dengan 9 state dan 4 action:
  - A0: Allow all
  - A1: Rate limit moderate (50/sec)
  - A2: Rate limit strict (10/sec)  
  - A3: Block high offender IP
- Reward function: `(throughput) - 0.5*(cpu_load) - 0.2*(packet_drop)`
- State observation: traffic_load + cpu_state

### Simulator Serangan
- HTTP Flood: High-rate HTTP requests
- Slowloris: Partial HTTP headers untuk exhausting connections
- SYN Flood: SYN packets menggunakan hping3
- Mixed Attack: Kombinasi multi-phase attacks

### Simulator User
- Normal browsing: Random intervals (0.5-3s)
- Burst activity: Multiple requests dalam burst
- Mixed behavior: Kombinasi normal + burst

## Instalasi

1. Pastikan Docker dan Docker Compose terinstall
2. Clone repository ini
3. Build dan start containers:
   ```bash
   docker-compose up --build