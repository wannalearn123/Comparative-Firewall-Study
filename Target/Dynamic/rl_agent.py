import numpy as np
import random

class RLAgent:
    """
    Kelas untuk logika Q-Learning: Q-Table, epsilon-greedy, dan update Q.
    Parameter: alpha=0.1, gamma=0.9, epsilon=0.1, W1=1.0, W2=0.5, W3=0.2.
    """
    def __init__(self, num_states=9, num_actions=4, alpha=0.1, gamma=0.9, epsilon=0.1):
        self.num_states = num_states
        self.num_actions = num_actions
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        self.q_table = np.random.uniform(0, 1, (num_states, num_actions))  # Inisialisasi random

    def choose_action(self, state):
        # Epsilon-greedy: Pilih action random dengan prob epsilon, else max Q.
        if random.random() < self.epsilon:
            return random.randint(0, self.num_actions - 1)
        else:
            return np.argmax(self.q_table[state])

    def calculate_reward(self, throughput_legal, cpu_load, packet_drop_fp, w1=1.0, w2=0.5, w3=0.2):
        # Hitung reward: R = (W1 * throughput) - (W2 * cpu_load) - (W3 * packet_drop_fp).
        return (w1 * throughput_legal) - (w2 * cpu_load) - (w3 * packet_drop_fp)

    def update_q_table(self, state, action, reward, next_state):
        # Update Q-Table menggunakan Bellman equation.
        best_next_action = np.argmax(self.q_table[next_state])
        td_target = reward + self.gamma * self.q_table[next_state][best_next_action]
        td_error = td_target - self.q_table[state][action]
        self.q_table[state][action] += self.alpha * td_error
