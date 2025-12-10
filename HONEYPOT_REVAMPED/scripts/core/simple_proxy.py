#!/usr/bin/env python3
"""
ПРОСТОЙ ПРОКСИ-МОНИТОР для honeypot
Работает без внешних зависимостей
"""

import socket
import threading
import time
import sys
import os
from datetime import datetime

class SimpleProxyMonitor:
    def __init__(self, listen_port=3001, target_port=3000):
        self.listen_port = listen_port
        self.target_port = target_port
        self.stats = {
            'total': 0,
            'attacks': 0,
            'normal': 0,
            'start_time': time.time(),
            'attack_types': {}
        }
        
        # Цвета
        self.RED = '\033[91m'
        self.GREEN = '\033[92m'
        self.YELLOW = '\033[93m'
        self.BLUE = '\033[94m'
        self.CYAN = '\033[96m'
        self.RESET = '\033[0m'
        self.BOLD = '\033[1m'
        
        self.show_banner()
    
    def show_banner(self):
        """Показать баннер"""
        os.system('clear')
        print(f"{self.CYAN}{'='*70}{self.RESET}")
        print(f"{self.BOLD}{self.YELLOW}🔄 ПРОКСИ-МОНИТОР ДЛЯ HONEYPOT{self.RESET}")
        print(f"{self.CYAN}{'='*70}{self.RESET}")
        print(f"{self.GREEN}📍 Прослушиваю порт: {self.listen_port}{self.RESET}")
        print(f"{self.GREEN}🎯 Перенаправляю на порт: {self.target_port}{self.RESET}")
        print(f"{self.YELLOW}💡 Отправляйте запросы на http://localhost:{self.listen_port}{self.RESET}")
        print(f"{self.CYAN}{'-'*70}{self.RESET}\n")
        
        print(f"{self.GREEN}🎯 ДЛЯ ТЕСТИРОВАНИЯ ОТКРОЙТЕ НОВЫЙ ТЕРМИНАЛ И ВЫПОЛНИТЕ:{self.RESET}")
        print(f"{self.YELLOW}   curl \"http://localhost:{self.listen_port}/rest/products/search?q=' OR '1'='1\"{self.RESET}")
        print(f"{self.YELLOW}   curl \"http://localhost:{self.listen_port}/#/search?q=<script>alert('XSS')</script>\"{self.RESET}")
        print(f"{self.CYAN}{'-'*70}{self.RESET}\n")
    
    def detect_attack(self, data):
        """Обнаружение атаки в данных"""
        try:
            data_str = data.decode('utf-8', errors='ignore').lower()
        except:
            return "Normal", 0.0
        
        # SQL Injection
        if "'" in data_str or "union" in data_str or "select" in data_str:
            return "SQL Injection", 0.93
        
        # XSS
        elif "<script>" in data_str or "javascript:" in data_str:
            return "XSS", 0.86
        
        # Path Traversal
        elif "../" in data_str or "etc/passwd" in data_str:
            return "Path Traversal", 0.78
        
        # Command Injection
        elif ";" in data_str or "|" in data_str or "`" in data_str:
            return "Command Injection", 0.82
        
        else:
            return "Normal", 0.0
    
    def log_attack(self, attack_type, confidence, data, client_ip):
        """Логирование атаки"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        # Извлекаем первую строку запроса
        try:
            request_line = data.decode('utf-8', errors='ignore').split('\n')[0]
        except:
            request_line = "Unknown request"
        
        print(f"\n{self.RED}{'🚨'*20}{self.RESET}")
        print(f"{self.RED}{self.BOLD}🚨 АТАКА ОБНАРУЖЕНА! [{timestamp}]{self.RESET}")
        print(f"{self.RED}{'─'*50}{self.RESET}")
        print(f"{self.YELLOW}🔥 Тип:{self.RESET} {attack_type}")
        print(f"{self.YELLOW}📊 Уверенность:{self.RESET} {confidence:.1%}")
        print(f"{self.YELLOW}📍 Источник:{self.RESET} {client_ip}")
        print(f"{self.YELLOW}📝 Запрос:{self.RESET} {request_line[:80]}..." if len(request_line) > 80 else f"{self.YELLOW}📝 Запрос:{self.RESET} {request_line}")
        print(f"{self.RED}{'─'*50}{self.RESET}")
        
        # Обновляем статистику
        self.stats['attacks'] += 1
        if attack_type not in self.stats['attack_types']:
            self.stats['attack_types'][attack_type] = 0
        self.stats['attack_types'][attack_type] += 1
        
        self.show_stats()
    
    def log_normal(self, data, client_ip):
        """Логирование нормального запроса"""
        self.stats['normal'] += 1
        
        # Показываем каждый 3-й нормальный запрос
        if self.stats['normal'] % 3 == 0:
            timestamp = datetime.now().strftime("%H:%M:%S")
            try:
                request_line = data.decode('utf-8', errors='ignore').split('\n')[0]
            except:
                request_line = "Unknown"
            
            print(f"{self.GREEN}[{timestamp}] 📡 Нормальный запрос от {client_ip}: {request_line[:50]}...{self.RESET}")
    
    def show_stats(self):
        """Показать статистику"""
        total = self.stats['total']
        attacks = self.stats['attacks']
        normal = self.stats['normal']
        elapsed = time.time() - self.stats['start_time']
        
        print(f"\n{self.CYAN}📊 СТАТИСТИКА ПРОКСИ:{self.RESET}")
        print(f"{self.CYAN}{'─'*40}{self.RESET}")
        print(f"{self.BLUE}📦 Всего запросов:{self.RESET} {total}")
        print(f"{self.GREEN}✅ Нормальных:{self.RESET} {normal}")
        print(f"{self.RED}🚨 Атак:{self.RESET} {attacks}")
        
        if self.stats['attack_types']:
            print(f"\n{self.YELLOW}🎯 ТИПЫ АТАК:{self.RESET}")
            for atk_type, count in self.stats['attack_types'].items():
                percentage = count / attacks * 100
                print(f"   • {atk_type}: {count} ({percentage:.1f}%)")
        
        if total > 0:
            detection_rate = attacks / total * 100
            print(f"{self.CYAN}📈 Эффективность:{self.RESET} {detection_rate:.1f}%")
        
        print(f"{self.CYAN}⏱️  Время работы:{self.RESET} {int(elapsed)} сек")
        print(f"{self.CYAN}{'─'*40}{self.RESET}\n")
    
    def handle_client(self, client_socket, client_address):
        """Обработка клиентского соединения"""
        try:
            # Подключаемся к реальному honeypot
            remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            remote_socket.connect(('localhost', self.target_port))
            
            # Получаем данные от клиента
            data = client_socket.recv(4096)
            
            if data:
                self.stats['total'] += 1
                client_ip = client_address[0]
                
                # Анализируем запрос
                attack_type, confidence = self.detect_attack(data)
                
                if attack_type != "Normal":
                    self.log_attack(attack_type, confidence, data, client_ip)
                else:
                    self.log_normal(data, client_ip)
                
                # Пересылаем запрос на honeypot
                remote_socket.send(data)
                
                # Получаем ответ от honeypot
                response = remote_socket.recv(4096)
                
                # Отправляем ответ клиенту
                client_socket.send(response)
            
            # Закрываем соединения
            remote_socket.close()
            client_socket.close()
            
        except Exception as e:
            # print(f"Ошибка обработки: {e}")  # Не показываем ошибки пользователю
            pass
    
    def start_proxy(self):
        """Запуск прокси-сервера"""
        try:
            # Создаем серверный сокет
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(('0.0.0.0', self.listen_port))
            server.listen(5)
            
            print(f"{self.GREEN}✅ Прокси запущен на порту {self.listen_port}{self.RESET}")
            print(f"{self.YELLOW}📡 Ожидание подключений... (Ctrl+C для остановки){self.RESET}\n")
            
            while True:
                # Принимаем соединения
                client_socket, client_address = server.accept()
                
                # Обрабатываем клиента в отдельном потоке
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, client_address)
                )
                client_thread.daemon = True
                client_thread.start()
                
        except KeyboardInterrupt:
            print(f"\n{self.YELLOW}🛑 Прокси остановлен{self.RESET}")
        except Exception as e:
            print(f"{self.RED}❌ Ошибка прокси: {e}{self.RESET}")
        finally:
            try:
                server.close()
            except:
                pass
    
    def start(self):
        """Запуск монитора"""
        try:
            # Проверяем, что honeypot доступен
            print(f"{self.GREEN}🔍 Проверяю honeypot на порту {self.target_port}...{self.RESET}")
            
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.settimeout(2)
            result = test_socket.connect_ex(('localhost', self.target_port))
            test_socket.close()
            
            if result == 0:
                print(f"{self.GREEN}✅ Honeypot доступен{self.RESET}")
            else:
                print(f"{self.RED}❌ Honeypot недоступен на порту {self.target_port}{self.RESET}")
                print(f"{self.YELLOW}Запустите: docker run -d -p {self.target_port}:3000 bkimminich/juice-shop{self.RESET}")
                return
            
            # Запускаем прокси
            self.start_proxy()
            
        except KeyboardInterrupt:
            print(f"\n{self.YELLOW}🛑 Монитор остановлен{self.RESET}")
        finally:
            self.show_final_stats()
    
    def show_final_stats(self):
        """Показать финальную статистику"""
        print(f"\n{self.CYAN}{'='*60}{self.RESET}")
        print(f"{self.BOLD}📊 ФИНАЛЬНАЯ СТАТИСТИКА ПРОКСИ-МОНИТОРА{self.RESET}")
        print(f"{self.CYAN}{'='*60}{self.RESET}")
        
        total_time = time.time() - self.stats['start_time']
        
        print(f"{self.BLUE}⏱️  Время работы:{self.RESET} {int(total_time)} сек")
        print(f"{self.BLUE}📦 Всего запросов:{self.RESET} {self.stats['total']}")
        print(f"{self.GREEN}✅ Нормальных:{self.RESET} {self.stats['normal']}")
        print(f"{self.RED}🚨 Атак:{self.RESET} {self.stats['attacks']}")
        
        if self.stats['attack_types']:
            print(f"\n{self.YELLOW}🎯 ТИПЫ ОБНАРУЖЕННЫХ АТАК:{self.RESET}")
            for atk_type, count in self.stats['attack_types'].items():
                percentage = count / max(self.stats['attacks'], 1) * 100
                print(f"   • {atk_type}: {count} ({percentage:.1f}%)")
        
        if self.stats['total'] > 0:
            detection_rate = self.stats['attacks'] / self.stats['total'] * 100
            print(f"{self.CYAN}📈 Эффективность обнаружения:{self.RESET} {detection_rate:.1f}%")
        
        print(f"{self.CYAN}{'='*60}{self.RESET}")

def main():
    """Точка входа"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Простой прокси-монитор для honeypot')
    parser.add_argument('--listen-port', '-l', type=int, default=3001,
                       help='Порт для прослушивания (по умолчанию: 3001)')
    parser.add_argument('--target-port', '-t', type=int, default=3000,
                       help='Порт honeypot (по умолчанию: 3000)')
    
    args = parser.parse_args()
    
    # Проверка прав (не требуется для портов > 1024)
    if args.listen_port < 1024 and os.geteuid() != 0:
        print("❌ Для портов ниже 1024 нужны root права!")
        print(f"   Запустите: sudo python3 {sys.argv[0]}")
        sys.exit(1)
    
    monitor = SimpleProxyMonitor(
        listen_port=args.listen_port,
        target_port=args.target_port
    )
    monitor.start()

if __name__ == "__main__":
    main()
