#!/usr/bin/env python3
"""
РЕАЛЬНЫЙ МОНИТОР с захватом трафика через socat/nc
"""

import os
import sys
import time
import subprocess
import threading
from datetime import datetime

class RealMonitor:
    def __init__(self, port=3000):
        self.port = port
        self.stats = {
            'total': 0,
            'attacks': 0,
            'normal': 0,
            'start_time': time.time(),
            'attack_types': {}
        }
        self.running = True
        
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
        print(f"{self.BOLD}{self.YELLOW}🎯 REAL TRAFFIC MONITOR v2.0{self.RESET}")
        print(f"{self.CYAN}{'='*70}{self.RESET}")
        print(f"{self.GREEN}📍 Honeypot порт: {self.port}{self.RESET}")
        print(f"{self.GREEN}📡 Режим: ЗАХВАТ РЕАЛЬНОГО ТРАФИКА{self.RESET}")
        print(f"{self.YELLOW}💡 Отправляйте запросы на http://localhost:{self.port}{self.RESET}")
        print(f"{self.CYAN}{'-'*70}{self.RESET}\n")
        
        print(f"{self.GREEN}🎯 ДЛЯ ТЕСТИРОВАНИЯ ОТКРОЙТЕ НОВЫЙ ТЕРМИНАЛ И ВЫПОЛНИТЕ:{self.RESET}")
        print(f"{self.YELLOW}   curl \"http://localhost:{self.port}/rest/products/search?q=' OR '1'='1\"{self.RESET}")
        print(f"{self.YELLOW}   curl \"http://localhost:{self.port}/#/search?q=<script>alert('XSS')</script>\"{self.RESET}")
        print(f"{self.CYAN}{'-'*70}{self.RESET}\n")
    
    def detect_attack(self, request):
        """Обнаружение атаки в HTTP запросе"""
        request_lower = request.lower()
        
        # SQL Injection
        if "'" in request_lower or "union" in request_lower or "select" in request_lower:
            return "SQL Injection", 0.93
        
        # XSS
        elif "<script>" in request_lower or "javascript:" in request_lower:
            return "XSS", 0.86
        
        # Path Traversal
        elif "../" in request_lower or "etc/passwd" in request_lower:
            return "Path Traversal", 0.78
        
        # Command Injection
        elif ";" in request_lower or "|" in request_lower or "`" in request_lower:
            return "Command Injection", 0.82
        
        else:
            return "Normal", 0.0
    
    def log_attack(self, attack_type, confidence, request, src_ip="127.0.0.1"):
        """Логирование атаки"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        print(f"\n{self.RED}{'🚨'*20}{self.RESET}")
        print(f"{self.RED}{self.BOLD}🚨 РЕАЛЬНАЯ АТАКА ОБНАРУЖЕНА! [{timestamp}]{self.RESET}")
        print(f"{self.RED}{'─'*50}{self.RESET}")
        print(f"{self.YELLOW}🔥 Тип:{self.RESET} {attack_type}")
        print(f"{self.YELLOW}📊 Уверенность:{self.RESET} {confidence:.1%}")
        print(f"{self.YELLOW}📍 Источник:{self.RESET} {src_ip}")
        print(f"{self.YELLOW}📝 Запрос:{self.RESET} {request[:80]}..." if len(request) > 80 else f"{self.YELLOW}📝 Запрос:{self.RESET} {request}")
        print(f"{self.RED}{'─'*50}{self.RESET}")
        
        # Обновляем статистику
        self.stats['attacks'] += 1
        if attack_type not in self.stats['attack_types']:
            self.stats['attack_types'][attack_type] = 0
        self.stats['attack_types'][attack_type] += 1
        
        self.show_stats()
    
    def log_normal(self, request):
        """Логирование нормального запроса"""
        self.stats['normal'] += 1
        
        # Показываем каждый 3-й нормальный запрос
        if self.stats['normal'] % 3 == 0:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"{self.GREEN}[{timestamp}] 📡 Нормальный запрос: {request[:50]}...{self.RESET}")
    
    def show_stats(self):
        """Показать статистику"""
        total = self.stats['total']
        attacks = self.stats['attacks']
        normal = self.stats['normal']
        elapsed = time.time() - self.stats['start_time']
        
        print(f"\n{self.CYAN}📊 РЕАЛЬНАЯ СТАТИСТИКА:{self.RESET}")
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
    
    def capture_with_socat(self):
        """Захват трафика через socat"""
        try:
            print(f"{self.GREEN}🎯 Запуск захвата трафика через socat...{self.RESET}")
            
            # Проверяем наличие socat
            if subprocess.run(['which', 'socat'], capture_output=True).returncode != 0:
                print(f"{self.RED}❌ socat не установлен!{self.RESET}")
                print(f"{self.YELLOW}Установите: sudo apt install socat{self.RESET}")
                return
            
            # Команда для перенаправления трафика
            cmd = f'socat -v TCP-LISTEN:{self.port},fork,reuseaddr TCP:localhost:3000'
            
            process = subprocess.Popen(
                cmd, 
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            
            print(f"{self.GREEN}✅ Прокси запущен на порту {self.port}{self.RESET}")
            print(f"{self.YELLOW}📡 Анализирую трафик...{self.RESET}")
            
            while self.running:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                
                if line:
                    # Ищем HTTP запросы
                    if 'GET /' in line or 'POST /' in line:
                        self.stats['total'] += 1
                        
                        # Извлекаем URL
                        if 'GET' in line:
                            parts = line.split('GET ')
                            if len(parts) > 1:
                                url = parts[1].split(' HTTP')[0]
                                attack_type, confidence = self.detect_attack(url)
                                
                                if attack_type != "Normal":
                                    self.log_attack(attack_type, confidence, f"GET {url}")
                                else:
                                    self.log_normal(f"GET {url}")
                        
                        elif 'POST' in line:
                            parts = line.split('POST ')
                            if len(parts) > 1:
                                url = parts[1].split(' HTTP')[0]
                                attack_type, confidence = self.detect_attack(url)
                                
                                if attack_type != "Normal":
                                    self.log_attack(attack_type, confidence, f"POST {url}")
                                else:
                                    self.log_normal(f"POST {url}")
                    
                    time.sleep(0.01)
            
            process.terminate()
            
        except KeyboardInterrupt:
            print(f"\n{self.YELLOW}🛑 Захват остановлен{self.RESET}")
        except Exception as e:
            print(f"{self.RED}❌ Ошибка: {e}{self.RESET}")
    
    def start(self):
        """Запуск монитора"""
        try:
            # Проверяем, что honeypot работает
            print(f"{self.GREEN}🔍 Проверяю honeypot...{self.RESET}")
            result = subprocess.run(
                ['curl', '-s', f'http://localhost:{self.port}'],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"{self.RED}❌ Honeypot на порту {self.port} не отвечает!{self.RESET}")
                print(f"{self.YELLOW}Запустите: docker run -d -p {self.port}:3000 bkimminich/juice-shop{self.RESET}")
                return
            
            print(f"{self.GREEN}✅ Honeypot работает{self.RESET}")
            
            # Запускаем захват
            self.capture_with_socat()
            
        except KeyboardInterrupt:
            print(f"\n{self.YELLOW}🛑 Монитор остановлен{self.RESET}")
        finally:
            self.show_final_stats()
    
    def show_final_stats(self):
        """Показать финальную статистику"""
        print(f"\n{self.CYAN}{'='*60}{self.RESET}")
        print(f"{self.BOLD}📊 ФИНАЛЬНАЯ СТАТИСТИКА РЕАЛЬНОГО МОНИТОРА{self.RESET}")
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
    
    parser = argparse.ArgumentParser(description='Реальный монитор трафика honeypot')
    parser.add_argument('--port', '-p', type=int, default=3000,
                       help='Порт honeypot (по умолчанию: 3000)')
    
    args = parser.parse_args()
    
    # Проверка прав
    if os.geteuid() != 0:
        print("❌ Этот скрипт требует root-прав для захвата трафика!")
        print("   Запустите: sudo python scripts/core/real_monitor.py")
        sys.exit(1)
    
    monitor = RealMonitor(port=args.port)
    monitor.start()

if __name__ == "__main__":
    main()
