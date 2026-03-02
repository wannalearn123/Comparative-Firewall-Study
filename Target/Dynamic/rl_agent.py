import numpy as np
import random
import pickle
import os
from collections import deque

class RLAgent:
    """
    Q-Learning agent optimized for DDoS mitigation.
    - 15 states (3 traffic × 5 CPU levels)
    - 5 actions (granular rate limiting)
    - Epsilon decay for convergence
    - Experience replay for stability
    """
    def __init__(self, num_states=15, num_actions=5, alpha=0.2, gamma=0.85, 
                 epsilon=1.0, epsilon_min=0.05, epsilon_decay=0.995, 
                 q_table_path='q_table.pkl'):
        self.num_states = num_states
        self.num_actions = num_actions
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay
        self.q_table_path = q_table_path
        self.replay_buffer = deque(maxlen=1000)
        
        if os.path.exists(q_table_path):
            self.q_table = self.load_q_table()
            self.epsilon = epsilon_min
        else:
            self.q_table = np.zeros((num_states, num_actions))
        
        self.steps = 0

    def choose_action(self, state):
        if random.random() < self.epsilon:
            return random.randint(0, self.num_actions - 1)
        return np.argmax(self.q_table[state])

    def calculate_reward(self, throughput_legal, cpu_load, packet_drop, 
                        prev_throughput=0):
        throughput_norm = min(throughput_legal / 100.0, 1.0)
        cpu_penalty = (cpu_load / 100.0) ** 2
        drop_penalty = (packet_drop / 100.0) ** 2
        throughput_delta = (throughput_legal - prev_throughput) / 100.0
        
        reward = (2.0 * throughput_norm) - (1.5 * cpu_penalty) - \
                 (1.0 * drop_penalty) + (0.5 * throughput_delta)
        return reward

    def update_q_table(self, state, action, reward, next_state):
        self.replay_buffer.append((state, action, reward, next_state))
        
        best_next_action = np.argmax(self.q_table[next_state])
        td_target = reward + self.gamma * self.q_table[next_state][best_next_action]
        td_error = td_target - self.q_table[state][action]
        self.q_table[state][action] += self.alpha * td_error
        
        if len(self.replay_buffer) >= 50 and self.steps % 10 == 0:
            batch = random.sample(self.replay_buffer, min(20, len(self.replay_buffer)))
            for s, a, r, ns in batch:
                best_na = np.argmax(self.q_table[ns])
                td_t = r + self.gamma * self.q_table[ns][best_na]
                self.q_table[s][a] += self.alpha * (td_t - self.q_table[s][a])
        
        self.steps += 1
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

    def save_q_table(self):
        with open(self.q_table_path, 'wb') as f:
            pickle.dump({'q_table': self.q_table, 'epsilon': self.epsilon}, f)

    def load_q_table(self):
        with open(self.q_table_path, 'rb') as f:
            data = pickle.load(f)
            self.epsilon = data.get('epsilon', self.epsilon_min)
            return data['q_table']
