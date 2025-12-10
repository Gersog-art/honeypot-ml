#!/usr/bin/env python3
"""
Упрощенный монитор для обнаружения атак
Работает без сложных зависимостей
"""

import sys
import os
import time
from datetime import datetime

# Добавляем путь для импортов
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class SimpleMonitor:
    def __init__(self):
        self.stats = {
            'total_requests': 0,
            'attacks_detected': 0,
            'normal_requests': 0,
            'start_time': time.time()
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
        print(f"{self.BOLD}{self.YELLOW}🛡️  SIMPLE HONEYPOT ATTACK MONITOR{self.RESET}")
        print(f"{self.CYAN}{'='*70}{self.RESET}")
        print(f"{self.GREEN}✅ Монитор запущен. Ожидание атак...{self.RESET}")
        print(f"{self.YELLOW}💡 Отправьте запросы на http://localhost:3000{self.RESET}")
        print(f"{self.CYAN}{'-'*70}{self.RESET}\n")
    
    def detect_attack(self, url, method="GET", src_ip="127.0.0.1", src_port=0):
        """Обнаружение атаки по простым правилам"""
        url_lower = url.lower()
        
        # Проверяем SQL инъекции
        sql_keywords = ["'", "or 1=1", "union", "--", "select ", "from ", "drop ", "insert "]
        has_sql = any(kw in url_lower for kw in sql_keywords)
        
        # Проверяем XSS
        xss_keywords = ["<script>", "alert(", "onerror=", "javascript:", "document.cookie"]
        has_xss = any(kw in url_lower for kw in xss_keywords)
        
        # Проверяем Path Traversal
        traversal_keywords = ["../", "..%2f", "etc/passwd", "%252f", "..\\"]
        has_traversal = any(kw in url_lower for kw in traversal_keywords)
        
        # Проверяем Command Injection
        cmd_keywords = [";", "|", "`", "$(", "&&", "||"]
        has_cmd = any(kw in url_lower for kw in cmd_keywords)
        
        # Определяем тип атаки
        attack_type = "Normal"
        confidence = 0.0
        
        if has_sql:
            attack_type = "SQL Injection"
            confidence = 0.93
        elif has_xss:
            attack_type = "XSS"
            confidence = 0.86
        elif has_traversal:
            attack_type = "Path Traversal"
            confidence = 0.78
        elif has_cmd:
            attack_type = "Command Injection"
            confidence = 0.82
        
        is_attack = has_sql or has_xss or has_traversal or has_cmd
        
        return {
            'is_attack': is_attack,
            'attack_type': attack_type,
            'confidence': confidence,
            'has_sql': has_sql,
            'has_xss': has_xss,
            'has_traversal': has_traversal,
            'has_cmd': has_cmd
        }
    
    def log_attack(self, detection, url, src_ip, src_port):
        """Логирование обнаруженной атаки"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        print(f"\n{self.RED}{'🚨'*20}{self.RESET}")
        print(f"{self.RED}{self.BOLD}🚨 АТАКА ОБНАРУЖЕНА! [{timestamp}]{self.RESET}")
        print(f"{self.RED}{'─'*50}{self.RESET}")
        print(f"{self.YELLOW}🔥 Тип:{self.RESET} {detection['attack_type']}")
        print(f"{self.YELLOW}📊 Уверенность:{self.RESET} {detection['confidence']:.1%}")
        print(f"{self.YELLOW}📍 Источник:{self.RESET} {src_ip}:{src_port}")
        print(f"{self.YELLOW}🎯 URL:{self.RESET} {url[:100]}..." if len(url) > 100 else f"{self.YELLOW}🎯 URL:{self.RESET} {url}")
        
        # Показываем признаки
        signs = []
        if detection['has_sql']: signs.append("SQL")
        if detection['has_xss']: signs.append("XSS")
        if detection['has_traversal']: signs.append("Traversal")
        if detection['has_cmd']: signs.append("Command")
        
        if signs:
            print(f"{self.YELLOW}🛡️  Признаки:{self.RESET} {', '.join(signs)}")
        
        print(f"{self.RED}{'─'*50}{self.RESET}")
        
        # Обновляем статистику
        self.stats['attacks_detected'] += 1
        self.show_stats()
    
    def log_normal(self, url, src_ip, src_port):
        """Логирование нормального запроса"""
        self.stats['normal_requests'] += 1
        
        # Показываем каждые 10 нормальных запросов
        if self.stats['normal_requests'] % 10 == 0:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"{self.GREEN}[{timestamp}] 📡 Нормальный запрос: {src_ip}:{src_port} → {url[:50]}...{self.RESET}")
            self.show_stats()
    
    def show_stats(self):
        """Показать статистику"""
        total = self.stats['total_requests']
        attacks = self.stats['attacks_detected']
        normal = self.stats['normal_requests']
        elapsed = time.time() - self.stats['start_time']
        
        if total > 0:
            print(f"\n{self.CYAN}📊 СТАТИСТИКА:{self.RESET}")
            print(f"{self.CYAN}{'─'*40}{self.RESET}")
            print(f"{self.BLUE}📦 Всего запросов:{self.RESET} {total}")
            print(f"{self.GREEN}✅ Нормальных:{self.RESET} {normal}")
            print(f"{self.RED}🚨 Атак:{self.RESET} {attacks}")
            print(f"{self.YELLOW}🎯 Скорость обнаружения:{self.RESET} {attacks/max(total,1):.1%}")
            print(f"{self.YELLOW}⏱️  Время работы:{self.RESET} {int(elapsed)} сек")
            print(f"{self.CYAN}{'─'*40}{self.RESET}\n")
    
    def simulate_attacks(self):
        """Симуляция атак для тестирования"""
        print(f"{self.YELLOW}🧪 ЗАПУСК ТЕСТОВЫХ АТАК...{self.RESET}")
        
        test_attacks = [
            ("SQL Injection", "http://localhost:3000/rest/products/search?q=' OR '1'='1", "127.0.0.1", 54321),
            ("XSS", "http://localhost:3000/#/search?q=<script>alert('XSS')</script>", "127.0.0.1", 54322),
            ("Path Traversal", "http://localhost:3000/assets/../../../etc/passwd", "127.0.0.1", 54323),
            ("Command Injection", "http://localhost:3000/rest/products/search?q='; ls -la /", "127.0.0.1", 54324),
        ]
        
        test_normal = [
            ("Normal", "http://localhost:3000/", "127.0.0.1", 54325),
            ("Normal", "http://localhost:3000/#/login", "127.0.0.1", 54326),
        ]
        
        # Тестируем атаки
        for name, url, ip, port in test_attacks:
            self.stats['total_requests'] += 1
            detection = self.detect_attack(url, "GET", ip, port)
            
            if detection['is_attack']:
                self.log_attack(detection, url, ip, port)
            else:
                self.log_normal(url, ip, port)
            
            time.sleep(1)
        
        # Тестируем нормальные запросы
        for name, url, ip, port in test_normal:
            self.stats['total_requests'] += 1
            detection = self.detect_attack(url, "GET", ip, port)
            
            if not detection['is_attack']:
                self.log_normal(url, ip, port)
            
            time.sleep(0.5)
    
    def run(self):
        """Запуск монитора"""
        print(f"{self.GREEN}🎯 Монитор запущен. Выберите режим:{self.RESET}")
        print(f"  1. {self.YELLOW}Режим симуляции (тестовые атаки){self.RESET}")
        print(f"  2. {self.YELLOW}Ручной ввод запросов{self.RESET}")
        print(f"  3. {self.YELLOW}Пассивный мониторинг (только статистика){self.RESET}")
        
        try:
            choice = input(f"\n{self.CYAN}Выберите вариант (1-3): {self.RESET}")
            
            if choice == "1":
                self.simulate_attacks()
            elif choice == "2":
                self.manual_mode()
            elif choice == "3":
                self.passive_mode()
            else:
                print(f"{self.RED}❌ Неверный выбор. Завершение.{self.RESET}")
        
        except KeyboardInterrupt:
            print(f"\n{self.YELLOW}🛑 Монитор остановлен{self.RESET}")
            self.show_stats()
    
    def manual_mode(self):
        """Режим ручного ввода"""
        print(f"\n{self.CYAN}✍️  РУЧНОЙ РЕЖИМ{self.RESET}")
        print(f"{self.YELLOW}Вводите URL для проверки (или 'exit' для выхода):{self.RESET}")
        
        while True:
            try:
                url = input(f"\n{self.BLUE}URL: {self.RESET}")
                
                if url.lower() == 'exit':
                    break
                
                self.stats['total_requests'] += 1
                detection = self.detect_attack(url, "GET", "127.0.0.1", 0)
                
                if detection['is_attack']:
                    self.log_attack(detection, url, "127.0.0.1", 0)
                else:
                    print(f"{self.GREEN}✅ Нормальный запрос{self.RESET}")
                    self.stats['normal_requests'] += 1
                
                self.show_stats()
                
            except KeyboardInterrupt:
                break
        
        self.show_stats()
    
    def passive_mode(self):
        """Пассивный режим мониторинга"""
        print(f"\n{self.CYAN}👁️  ПАССИВНЫЙ МОНИТОРИНГ{self.RESET}")
        print(f"{self.YELLOW}Мониторинг запущен. Нажмите Ctrl+C для остановки.{self.RESET}")
        print(f"{self.YELLOW}Отправляйте запросы на http://localhost:3000{self.RESET}")
        
        # Здесь можно добавить захват реального трафика
        # но для простоты делаем просто ожидание
        try:
            while True:
                time.sleep(1)
                # Показываем статистику каждые 10 секунд
                if time.time() - self.stats['start_time'] > 10:
                    self.show_stats()
                    self.stats['start_time'] = time.time()
        except KeyboardInterrupt:
            print(f"\n{self.YELLOW}🛑 Мониторинг остановлен{self.RESET}")
            self.show_stats()

def main():
    """Точка входа"""
    monitor = SimpleMonitor()
    monitor.run()

if __name__ == "__main__":
    main()
