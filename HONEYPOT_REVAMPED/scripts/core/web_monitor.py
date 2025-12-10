#!/usr/bin/env python3
"""
Веб-монитор для обнаружения атак
Работает через логи веб-сервера
"""

import os
import sys
import time
import json
import subprocess
from datetime import datetime
from threading import Thread

class WebMonitor:
    def __init__(self, port=3000):
        self.port = port
        self.stats = {
            'total': 0,
            'attacks': 0,
            'normal': 0,
            'types': {},
            'start_time': time.time()
        }
        
        # Цвета
        self.RED = '\033[91m'
        self.GREEN = '\033[92m'
        self.YELLOW = '\033[93m'
        self.BLUE = '\033[94m'
        self.MAGENTA = '\033[95m'
        self.CYAN = '\033[96m'
        self.RESET = '\033[0m'
        self.BOLD = '\033[1m'
        
        self.show_banner()
    
    def show_banner(self):
        """Показать баннер"""
        os.system('clear')
        print(f"{self.CYAN}{'='*70}{self.RESET}")
        print(f"{self.BOLD}{self.YELLOW}🌐 WEB ATTACK MONITOR v1.0{self.RESET}")
        print(f"{self.CYAN}{'='*70}{self.RESET}")
        print(f"{self.GREEN}📍 Honeypot: http://localhost:{self.port}{self.RESET}")
        print(f"{self.GREEN}📡 Режим: АНАЛИЗ HTTP ЗАПРОСОВ{self.RESET}")
        print(f"{self.YELLOW}💡 Монитор ожидает HTTP запросы...{self.RESET}")
        print(f"{self.CYAN}{'-'*70}{self.RESET}\n")
    
    def analyze_request(self, method, url, headers):
        """Анализ HTTP запроса на наличие атак"""
        url_lower = url.lower()
        
        # Признаки атак
        sql_keywords = ["'", "or 1=1", "union", "--", "select ", "from ", "sleep(", "benchmark"]
        xss_keywords = ["<script>", "alert(", "onerror=", "onload=", "<img", "javascript:"]
        traversal_keywords = ["../", "..%2f", "etc/passwd", "%252f", "..\\", "../../"]
        cmd_keywords = [";", "|", "`", "$(", "&&", "||", "exec(", "system("]
        
        has_sql = any(kw in url_lower for kw in sql_keywords)
        has_xss = any(kw in url_lower for kw in xss_keywords)
        has_traversal = any(kw in url_lower for kw in traversal_keywords)
        has_cmd = any(kw in url_lower for kw in cmd_keywords)
        
        # Определяем тип атаки
        if has_sql:
            return "SQL Injection", 0.93
        elif has_xss:
            return "XSS", 0.86
        elif has_traversal:
            return "Path Traversal", 0.78
        elif has_cmd:
            return "Command Injection", 0.82
        else:
            return "Normal", 0.0
    
    def log_attack(self, attack_type, confidence, method, url, src_ip="127.0.0.1"):
        """Логирование обнаруженной атаки"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        print(f"\n{self.RED}{'🚨'*20}{self.RESET}")
        print(f"{self.RED}{self.BOLD}🚨 АТАКА ОБНАРУЖЕНА! [{timestamp}]{self.RESET}")
        print(f"{self.RED}{'─'*50}{self.RESET}")
        print(f"{self.YELLOW}🔥 Тип:{self.RESET} {attack_type}")
        print(f"{self.YELLOW}📊 Уверенность:{self.RESET} {confidence:.1%}")
        print(f"{self.YELLOW}📍 Источник:{self.RESET} {src_ip}")
        print(f"{self.YELLOW}📝 Метод:{self.RESET} {method}")
        print(f"{self.YELLOW}🎯 URL:{self.RESET} {url[:80]}..." if len(url) > 80 else f"{self.YELLOW}🎯 URL:{self.RESET} {url}")
        print(f"{self.RED}{'─'*50}{self.RESET}")
        
        # Обновляем статистику
        self.stats['attacks'] += 1
        if attack_type not in self.stats['types']:
            self.stats['types'][attack_type] = 0
        self.stats['types'][attack_type] += 1
        
        # Показываем статистику после каждой атаки
        self.show_stats()
    
    def log_normal(self, method, url):
        """Логирование нормального запроса"""
        self.stats['normal'] += 1
        
        # Показываем каждый 5-й нормальный запрос
        if self.stats['normal'] % 5 == 0:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"{self.GREEN}[{timestamp}] 📡 {method} {url[:50]}...{self.RESET}")
    
    def show_stats(self):
        """Показать статистику"""
        total = self.stats['total']
        attacks = self.stats['attacks']
        normal = self.stats['normal']
        elapsed = time.time() - self.stats['start_time']
        
        print(f"\n{self.CYAN}📊 СТАТИСТИКА ОБНАРУЖЕНИЯ:{self.RESET}")
        print(f"{self.CYAN}{'─'*40}{self.RESET}")
        print(f"{self.BLUE}📦 Всего запросов:{self.RESET} {total}")
        print(f"{self.GREEN}✅ Нормальных:{self.RESET} {normal}")
        print(f"{self.RED}🚨 Атак:{self.RESET} {attacks}")
        
        if attacks > 0:
            print(f"\n{self.YELLOW}🎯 РАСПРЕДЕЛЕНИЕ АТАК:{self.RESET}")
            for atk_type, count in self.stats['types'].items():
                percentage = count / attacks * 100
                print(f"   • {atk_type}: {count} ({percentage:.1f}%)")
        
        if total > 0:
            detection_rate = attacks / total * 100
            print(f"\n{self.MAGENTA}📈 Эффективность:{self.RESET} {detection_rate:.1f}%")
        
        print(f"{self.CYAN}{'─'*40}{self.RESET}\n")
    
    def simulate_traffic(self):
        """Симуляция трафика для тестирования"""
        print(f"{self.YELLOW}🧪 ЗАПУСК ТЕСТОВОЙ СИМУЛЯЦИИ...{self.RESET}")
        
        test_cases = [
            ("GET", "/rest/products/search?q=' OR '1'='1", {}),
            ("GET", "/#/search?q=<script>alert('XSS')</script>", {}),
            ("GET", "/assets/../../../etc/passwd", {}),
            ("GET", "/rest/products/search?q='; ls -la /", {}),
            ("GET", "/", {}),
            ("GET", "/#/login", {}),
            ("GET", "/#/search?q=apple", {}),
        ]
        
        for method, url, headers in test_cases:
            self.stats['total'] += 1
            time.sleep(0.5)
            
            attack_type, confidence = self.analyze_request(method, url, headers)
            
            if attack_type != "Normal":
                self.log_attack(attack_type, confidence, method, url)
            else:
                self.log_normal(method, url)
        
        print(f"{self.GREEN}✅ Тестовая симуляция завершена!{self.RESET}")
    
    def start_http_server(self):
        """Запуск простого HTTP сервера для анализа запросов"""
        print(f"{self.GREEN}🌐 Запуск HTTP сервера на порту 8080...{self.RESET}")
        print(f"{self.YELLOW}📡 Отправляйте запросы на http://localhost:8080{self.RESET}")
        print(f"{self.CYAN}{'-'*70}{self.RESET}\n")
        
        try:
            # Импортируем здесь, чтобы избежать ошибок если нет библиотеки
            from http.server import HTTPServer, BaseHTTPRequestHandler
            import urllib.parse
            
            class AttackHandler(BaseHTTPRequestHandler):
                def do_GET(self):
                    # Анализируем запрос
                    self.server.monitor.stats['total'] += 1
                    
                    parsed_url = urllib.parse.urlparse(self.path)
                    attack_type, confidence = self.server.monitor.analyze_request(
                        "GET", parsed_url.path + "?" + parsed_url.query if parsed_url.query else parsed_url.path, 
                        dict(self.headers)
                    )
                    
                    # Отправляем ответ
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    
                    response = f"<html><body><h1>Honeypot Monitor</h1><p>Request received: {self.path}</p></body></html>"
                    self.wfile.write(response.encode('utf-8'))
                    
                    # Логируем
                    client_ip = self.client_address[0]
                    if attack_type != "Normal":
                        self.server.monitor.log_attack(attack_type, confidence, "GET", self.path, client_ip)
                    else:
                        self.server.monitor.log_normal("GET", self.path)
                
                def log_message(self, format, *args):
                    # Отключаем стандартное логирование
                    pass
            
            # Создаем сервер
            server = HTTPServer(('localhost', 8080), AttackHandler)
            server.monitor = self  # Передаем монитор в сервер
            
            print(f"{self.GREEN}✅ Сервер запущен на http://localhost:8080{self.RESET}")
            print(f"{self.YELLOW}🛑 Нажмите Ctrl+C для остановки{self.RESET}\n")
            
            server.serve_forever()
            
        except ImportError:
            print(f"{self.RED}❌ Не удалось импортировать http.server{self.RESET}")
            print(f"{self.YELLOW}⚠️  Используйте Python 3.x{self.RESET}")
        except Exception as e:
            print(f"{self.RED}❌ Ошибка сервера: {e}{self.RESET}")
    
    def start(self):
        """Запуск монитора"""
        print(f"{self.GREEN}🎯 ВЫБЕРИТЕ РЕЖИМ РАБОТЫ:{self.RESET}")
        print(f"  1. {self.YELLOW}Тестовая симуляция{self.RESET}")
        print(f"  2. {self.YELLOW}HTTP сервер (порт 8080){self.RESET}")
        print(f"  3. {self.YELLOW}Ручной ввод запросов{self.RESET}")
        
        try:
            choice = input(f"\n{self.CYAN}Выберите вариант (1-3): {self.RESET}")
            
            if choice == "1":
                self.simulate_traffic()
                self.show_final_stats()
            elif choice == "2":
                self.start_http_server()
            elif choice == "3":
                self.manual_mode()
            else:
                print(f"{self.RED}❌ Неверный выбор{self.RESET}")
                
        except KeyboardInterrupt:
            print(f"\n{self.YELLOW}🛑 Монитор остановлен{self.RESET}")
            self.show_final_stats()
    
    def manual_mode(self):
        """Режим ручного ввода"""
        print(f"\n{self.CYAN}✍️  РЕЖИМ РУЧНОГО ВВОДА{self.RESET}")
        print(f"{self.YELLOW}Вводите URL для анализа (или 'exit' для выхода):{self.RESET}")
        
        while True:
            try:
                url = input(f"\n{self.BLUE}URL: {self.RESET}")
                
                if url.lower() == 'exit':
                    break
                
                self.stats['total'] += 1
                attack_type, confidence = self.analyze_request("GET", url, {})
                
                if attack_type != "Normal":
                    self.log_attack(attack_type, confidence, "GET", url)
                else:
                    print(f"{self.GREEN}✅ Нормальный запрос{self.RESET}")
                    self.stats['normal'] += 1
                
                self.show_stats()
                
            except KeyboardInterrupt:
                break
        
        self.show_final_stats()
    
    def show_final_stats(self):
        """Показать финальную статистику"""
        print(f"\n{self.CYAN}{'='*60}{self.RESET}")
        print(f"{self.BOLD}📊 ФИНАЛЬНАЯ СТАТИСТИКА{self.RESET}")
        print(f"{self.CYAN}{'='*60}{self.RESET}")
        
        total_time = time.time() - self.stats['start_time']
        
        print(f"{self.BLUE}⏱️  Время работы:{self.RESET} {int(total_time)} сек")
        print(f"{self.BLUE}📦 Всего запросов:{self.RESET} {self.stats['total']}")
        print(f"{self.GREEN}✅ Нормальных:{self.RESET} {self.stats['normal']}")
        print(f"{self.RED}🚨 Атак:{self.RESET} {self.stats['attacks']}")
        
        if self.stats['types']:
            print(f"\n{self.YELLOW}🎯 РАСПРЕДЕЛЕНИЕ АТАК:{self.RESET}")
            for atk_type, count in self.stats['types'].items():
                percentage = count / max(self.stats['attacks'], 1) * 100
                print(f"   • {atk_type}: {count} ({percentage:.1f}%)")
        
        if self.stats['total'] > 0:
            detection_rate = self.stats['attacks'] / self.stats['total'] * 100
            print(f"{self.MAGENTA}📈 Эффективность обнаружения:{self.RESET} {detection_rate:.1f}%")
        
        print(f"{self.CYAN}{'='*60}{self.RESET}")

def main():
    """Точка входа"""
    monitor = WebMonitor(port=3000)
    monitor.start()

if __name__ == "__main__":
    main()
