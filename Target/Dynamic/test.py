import unittest
from unittest.mock import patch, mock_open, MagicMock
import numpy as np
import csv
import os
import tempfile

# Import modul yang akan ditest (asumsi file ada di direktori yang sama)
from state_observer import StateObserver
from rl_agent import RLAgent
from action_executor import ActionExecutor
from logger import Logger

class TestStateObserver(unittest.TestCase):
    def setUp(self):
        self.observer = StateObserver(log_file_path='/fake/log', interface='eth0')

    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    def test_get_cpu_ram_state_safe(self, mock_ram, mock_cpu):
        mock_cpu.return_value = 30.0
        mock_ram.return_value.percent = 40.0
        state = self.observer.get_cpu_ram_state()
        self.assertEqual(state, 0)  # Safe

    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    def test_get_cpu_ram_state_warning(self, mock_ram, mock_cpu):
        mock_cpu.return_value = 60.0
        mock_ram.return_value.percent = 60.0
        state = self.observer.get_cpu_ram_state()
        self.assertEqual(state, 1)  # Warning

    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    def test_get_cpu_ram_state_critical(self, mock_ram, mock_cpu):
        mock_cpu.return_value = 90.0
        mock_ram.return_value.percent = 90.0
        state = self.observer.get_cpu_ram_state()
        self.assertEqual(state, 2)  # Critical

    @patch('subprocess.run')
    @patch('time.time')
    def test_get_packet_rate_low(self, mock_time, mock_subprocess):
        # Mock waktu: init_time = 100, current_time = 101 (delta=1)
        mock_time.side_effect = [100.0, 101.0]
        mock_subprocess.return_value.stdout = "Chain INPUT (policy ACCEPT)\n    50 pkts eth0\n"
        rate = self.observer.get_packet_rate()
        self.assertEqual(rate, 0)  # 50 / 1 = 50, Low

    @patch('subprocess.run')
    @patch('time.time')
    def test_get_packet_rate_medium(self, mock_time, mock_subprocess):
        mock_time.side_effect = [100.0, 101.0]
        mock_subprocess.return_value.stdout = "Chain INPUT (policy ACCEPT)\n   200 pkts eth0\n"
        rate = self.observer.get_packet_rate()
        self.assertEqual(rate, 1)  # 200 / 1 = 200, Medium

    @patch('subprocess.run')
    @patch('time.time')
    def test_get_packet_rate_high(self, mock_time, mock_subprocess):
        mock_time.side_effect = [100.0, 101.0]
        mock_subprocess.return_value.stdout = "Chain INPUT (policy ACCEPT)\n   600 pkts eth0\n"
        rate = self.observer.get_packet_rate()
        self.assertEqual(rate, 2)  # 600 / 1 = 600, High

    @patch('builtins.open', new_callable=mock_open, read_data="127.0.0.1 - - [01/Jan/2023:00:00:00 +0000] \"GET / HTTP/1.1\" 200 123\n" * 10)
    def test_get_throughput_legal(self, mock_file):
        throughput = self.observer.get_throughput_legal()
        self.assertEqual(throughput, 10)  # 10 status 200

    @patch('state_observer.StateObserver.get_packet_rate')
    @patch('state_observer.StateObserver.get_cpu_ram_state')
    @patch('state_observer.StateObserver.get_throughput_legal')
    def test_get_state(self, mock_throughput, mock_cpu, mock_rate):
        mock_rate.return_value = 1  # Medium
        mock_cpu.return_value = 2  # Critical
        mock_throughput.return_value = 5
        state, throughput, cpu = self.observer.get_state()
        self.assertEqual(state, 5)  # 1*3 + 2
        self.assertEqual(throughput, 5)
        self.assertEqual(cpu, 2)

class TestRLAgent(unittest.TestCase):
    def setUp(self):
        self.agent = RLAgent()

    def test_choose_action_greedy(self):
        self.agent.q_table[0] = [0, 1, 0, 0]  # Max di index 1
        action = self.agent.choose_action(0)
        self.assertEqual(action, 1)

    @patch('random.random')
    @patch('random.randint')
    def test_choose_action_random(self, mock_randint, mock_random):
        mock_random.return_value = 0.05  # < epsilon (0.1), random
        mock_randint.return_value = 2
        action = self.agent.choose_action(0)
        self.assertEqual(action, 2)

    def test_calculate_reward(self):
        reward = self.agent.calculate_reward(10, 0.5, 1)
        expected = (1.0 * 10) - (0.5 * 0.5) - (0.2 * 1)  # 10 - 0.25 - 0.2 = 9.55
        self.assertAlmostEqual(reward, 9.55)

    def test_update_q_table(self):
        initial_q = self.agent.q_table[0][0]
        self.agent.update_q_table(0, 0, 1.0, 1)
        self.assertNotEqual(self.agent.q_table[0][0], initial_q)  # Harus berubah

class TestActionExecutor(unittest.TestCase):
    def setUp(self):
        self.executor = ActionExecutor()

    @patch('subprocess.run')
    def test_execute_action_a0(self, mock_subprocess):
        self.executor.execute_action(0)
        self.assertEqual(mock_subprocess.call_count, 2)  # iptables -F dan -P

    @patch('subprocess.run')
    def test_execute_action_a1(self, mock_subprocess):
        self.executor.execute_action(1)
        self.assertEqual(mock_subprocess.call_count, 3)  # Flush, limit, drop

    @patch('subprocess.run')
    def test_execute_action_a2(self, mock_subprocess):
        self.executor.execute_action(2)
        self.assertEqual(mock_subprocess.call_count, 3)

    @patch('subprocess.run')
    def test_execute_action_a3(self, mock_subprocess):
        # Mock dua call: pertama untuk -L -v (return stdout), kedua untuk -A (sukses)
        mock_result1 = MagicMock()
        mock_result1.stdout = "Chain INPUT\n SRC=192.168.1.1 100 pkts\n"
        mock_result2 = MagicMock()  # Sukses tanpa error
        mock_subprocess.side_effect = [mock_result1, mock_result2]
        self.executor.execute_action(3)
        mock_subprocess.assert_any_call(['iptables', '-A', 'INPUT', '-s', '192.168.1.1', '-j', 'DROP'], check=True)

class TestLogger(unittest.TestCase):
    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.csv')
        self.temp_file.close()
        self.logger = Logger(csv_file=self.temp_file.name)

    def tearDown(self):
        os.unlink(self.temp_file.name)

    def test_log_entry(self):
        self.logger.log_entry(0, 1, 2.0, 10)
        self.assertEqual(len(self.logger.buffer), 1)
        self.assertEqual(self.logger.buffer[0]['state'], 0)

    def test_flush_to_csv(self):
        self.logger.log_entry(0, 1, 2.0, 10)
        self.logger.flush_to_csv()
        self.assertEqual(len(self.logger.buffer), 0)  # Buffer cleared
        with open(self.temp_file.name, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            self.assertEqual(len(rows), 1)
            self.assertEqual(int(rows[0]['state']), 0)

if __name__ == '__main__':
    unittest.main()

# Contoh Penggunaan:
# Jalankan di terminal: python3 -m unittest test.py
# Atau dengan pytest: pytest test.py
# Test ini menggunakan mocking untuk menghindari dependensi eksternal seperti iptables atau file sistem.
# Jika ada error, pastikan modul import benar dan dependensi terinstall.