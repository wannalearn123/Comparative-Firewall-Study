import time
from state_observer import StateObserver
from rl_agent import RLAgent
from action_executor import ActionExecutor
from logger import Logger
from visualizer import plot_throughput_vs_time

def main():
    """
    Script utama: Loop polling selama 300 detik, update agen, log, dan plot di akhir.
    Jalankan sebagai root di container target.
    """
    observer = StateObserver()
    agent = RLAgent()
    executor = ActionExecutor()
    logger = Logger()
    
    duration = 300  # 5 menit
    interval = 5  # Polling setiap 5 detik
    start_time = time.time()
    
    while time.time() - start_time < duration:
        # Ambil state
        state, throughput, cpu_load = observer.get_state()
        packet_drop_fp = 0  # Simplifikasi: asumsikan 0, bisa dihitung dari log
        
        # Pilih dan eksekusi action
        action = agent.choose_action(state)
        executor.execute_action(action)
        
        # Hitung reward dan update Q
        reward = agent.calculate_reward(throughput, cpu_load, packet_drop_fp)
        next_state, _, _ = observer.get_state()  # Next state untuk update
        agent.update_q_table(state, action, reward, next_state)
        
        # Log
        logger.log_entry(state, action, reward, throughput)
        
        # Flush ke CSV setiap 30 detik
        if int(time.time() - start_time) % 30 == 0:
            logger.flush_to_csv()
        
        time.sleep(interval)
    
    # Akhir tes: Flush final dan plot
    logger.flush_to_csv()
    plot_throughput_vs_time()

if __name__ == "__main__":
    main()
