import time
import signal
import sys
from state_observer import StateObserver
from rl_agent import RLAgent
from action_executor import ActionExecutor
from logger import Logger
from visualizer import plot_throughput_vs_time


def signal_handler(sig, frame):
    print("\nShutting down, saving Q-table...")
    agent.save_q_table()
    logger.flush_to_csv()
    plot_throughput_vs_time()
    sys.exit(0)


def main():
    global agent, logger
    
    observer = StateObserver()
    agent = RLAgent()
    executor = ActionExecutor()
    logger = Logger()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    duration = 600
    interval = 3
    start_time = time.time()
    
    print(f"Starting Q-Learning firewall (epsilon={agent.epsilon:.3f})")
    
    while time.time() - start_time < duration:
        state, throughput, cpu_load, packet_drop, prev_throughput = \
            observer.get_state()
        
        action = agent.choose_action(state)
        executor.execute_action(action)
        
        time.sleep(interval)
        
        next_state, next_throughput, next_cpu, next_drop, _ = \
            observer.get_state()
        
        reward = agent.calculate_reward(next_throughput, next_cpu,
                                       next_drop, prev_throughput)
        agent.update_q_table(state, action, reward, next_state)
        
        logger.log_entry(state, action, reward, next_throughput,
                        agent.epsilon)
        
        if int(time.time() - start_time) % 30 == 0:
            logger.flush_to_csv()
            agent.save_q_table()
            elapsed = int(time.time() - start_time)
            print(f"t={elapsed}s | s={state} a={action} "
                  f"r={reward:.2f} ε={agent.epsilon:.3f}")
    
    agent.save_q_table()
    logger.flush_to_csv()
    plot_throughput_vs_time()
    print("Training complete, graph saved")


if __name__ == "__main__":
    main()
