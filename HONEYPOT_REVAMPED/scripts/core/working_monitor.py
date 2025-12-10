#!/usr/bin/env python3
"""
РАБОЧИЙ МОНИТОР ДЛЯ HONEYPOT - УЛУЧШЕННАЯ ВЕРСИЯ
Меньше ложных срабатываний, лучше детекция
"""

import os
import sys
import time
import json
import socket
import shutil
import re
from datetime import datetime
import subprocess

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class SimpleAttackLearner:
    def __init__(self, data_file="ml_models/attack_patterns.json"):
        self.data_file = data_file
        self.patterns = self.load_patterns()
        self.learning_log = "ml_models/learning_log.json"
        self.new_patterns_count = 0
        self.false_positives = set()  # Для отслеживания ложных срабатываний

    def load_patterns(self):
        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
                return data.get("patterns", {})
        except FileNotFoundError:
            # Более специфичные стартовые паттерны
            return {
                "sql": ["' or '1'='1", "union select", "1=1", "--", "/*", "*/", "drop table"],
                "xss": ["<script>alert", "</script>", "javascript:alert", "onload=", "onerror="],
                "path": ["../etc/passwd", "..\\windows\\", "../../../", "%2e%2e%2f"],
                "cmd": [";ls", "|cat", "`id`", "$(whoami)", "&& ls"],
                "xxe": ["<!DOCTYPE", "<!ENTITY %", "SYSTEM \"file:///", "&xxe;"]
            }

    def save_patterns(self):
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        data = {
            "patterns": self.patterns,
            "false_positives": list(self.false_positives),
            "updated": datetime.now().isoformat()
        }
        with open(self.data_file, 'w') as f:
            json.dump(data, f, indent=2)

        # Логируем
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "new_patterns": self.new_patterns_count,
            "total_patterns": sum(len(v) for v in self.patterns.values())
        }
        with open(self.learning_log, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')

    def learn_attack(self, attack_text, attack_type):
        """Учимся только на реальных атаках"""
        # Мапинг типов
        type_map = {
            "SQL Injection": "sql",
            "XSS": "xss",
            "Path Traversal": "path",
            "Command Injection": "cmd",
            "XXE": "xxe"
        }

        learn_type = type_map.get(attack_type, "unknown")
        if learn_type not in self.patterns:
            self.patterns[learn_type] = []

        # Извлекаем ТОЛЬКО подозрительные паттерны
        suspicious = self.extract_suspicious_patterns(attack_text)

        added = 0
        for pattern in suspicious:
            if pattern not in self.patterns[learn_type]:
                self.patterns[learn_type].append(pattern)
                added += 1

        self.new_patterns_count += added

        if self.new_patterns_count >= 2:  # Сохраняем каждые 2 новых паттерна
            self.save_patterns()
            self.new_patterns_count = 0

        return added

    def extract_suspicious_patterns(self, text):
        """Извлекаем только подозрительные паттерны, игнорируя нормальные"""
        text_lower = text.lower()
        patterns = []

        # Игнорируем нормальные запросы
        normal_patterns = [
            'socket.io', 'eio=', 'transport=', 'sid=', 't=',
            'vendor.js', 'styles.css', '.jpg', '.jpeg', '.png', '.gif',
            'assets/', 'api/challenges', 'rest/admin', 'favicon.ico'
        ]

        for np in normal_patterns:
            if np in text_lower:
                return []  # Это нормальный запрос, не учимся

        # Ищем реальные атаки
        # SQL: ищем конструкции с кавычками и SQL ключевыми словами
        sql_matches = re.findall(r"(['\"]\s*(?:or|and|union|select|from|where)\s+[^'\"]*)", text_lower)
        patterns.extend(sql_matches[:3])

        # XSS: ищем теги скриптов
        xss_matches = re.findall(r"(<[^>]*(?:script|iframe|img|onload|onerror)[^>]*>)", text_lower)
        patterns.extend(xss_matches[:3])

        # Path traversal: множественные точки
        path_matches = re.findall(r"(\.\./|\.\.\\|\.\.%2f|etc/passwd|win\.ini)", text_lower)
        patterns.extend(path_matches[:3])

        # Command: команды с разделителями
        cmd_matches = re.findall(r"([;&|`]\s*[a-z]+)", text_lower)
        patterns.extend(cmd_matches[:3])

        # XXE: только явные признаки
        xxe_matches = re.findall(r"(<!DOCTYPE|<!ENTITY|SYSTEM\s+['\"]|file:///)", text_lower)
        patterns.extend(xxe_matches[:3])

        return list(set(patterns))[:5]  # Уникальные, не более 5

class WorkingMonitor:
    def __init__(self, port=3000, enable_learning=True, strict_mode=True):
        self.port = port
        self.enable_learning = enable_learning
        self.strict_mode = strict_mode  # Режим строгой проверки

        self.stats = {
            'total': 0, 'attacks': 0, 'normal': 0, 'false_positives': 0,
            'start_time': time.time()
        }
        self.running = True

        if self.enable_learning:
            self.learner = SimpleAttackLearner()
            print("🧠 Автообучение активировано")
        else:
            self.learner = None

        # Списки для фильтрации
        self.whitelist_urls = [
            'socket.io', 'vendor.js', 'styles.css', 'main.js', 'runtime.js',
            'polyfills.js', 'favicon.ico', 'robots.txt', 'sitemap.xml'
        ]

        self.whitelist_extensions = [
            '.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg',
            '.woff', '.woff2', '.ttf', '.eot', '.map', '.json', '.txt'
        ]

        # Цвета
        self.RED = '\033[91m'; self.GREEN = '\033[92m'; self.YELLOW = '\033[93m'
        self.BLUE = '\033[94m'; self.CYAN = '\033[96m'; self.RESET = '\033[0m'
        self.BOLD = '\033[1m'; self.MAGENTA = '\033[95m'

        self.show_banner()

    def show_banner(self):
        os.system('clear')
        print(f"{self.CYAN}{'='*70}{self.RESET}")
        print(f"{self.BOLD}{self.YELLOW}🎯 HONEYPOT MONITOR v3.0 (УМНАЯ ДЕТЕКЦИЯ){self.RESET}")
        print(f"{self.CYAN}{'='*70}{self.RESET}")
        print(f"{self.GREEN}📍 Порт honeypot: {self.port}{self.RESET}")
        print(f"{self.GREEN}🧠 Автообучение: {'ВКЛЮЧЕНО' if self.enable_learning else 'ВЫКЛЮЧЕНО'}{self.RESET}")
        print(f"{self.GREEN}🔒 Режим: {'СТРОГИЙ' if self.strict_mode else 'СТАНДАРТНЫЙ'}{self.RESET}")
        print(f"{self.YELLOW}💡 Отправляйте запросы на http://localhost:{self.port}{self.RESET}")
        print(f"{self.CYAN}{'-'*70}{self.RESET}\n")

    def is_normal_request(self, url):
        """Проверяем, является ли запрос нормальным (не атакой)"""
        url_lower = url.lower()

        # 1. Проверяем по белому списку URL
        for whitelist in self.whitelist_urls:
            if whitelist in url_lower:
                return True

        # 2. Проверяем расширения файлов
        for ext in self.whitelist_extensions:
            if url_lower.endswith(ext):
                return True

        # 3. Проверяем статические файлы
        static_patterns = ['/assets/', '/static/', '/public/', '/images/', '/img/', '/css/', '/js/']
        for pattern in static_patterns:
            if pattern in url_lower:
                return True

        # 4. Проверяем API эндпоинты (нормальные)
        api_patterns = ['/api/challenges', '/rest/admin/application-version']
        for pattern in api_patterns:
            if pattern in url_lower:
                return True

        # 5. Простые параметры запроса - это нормально
        if re.match(r'^[a-zA-Z0-9_\-\.=&%\/\?]+$', url_lower):
            # Это нормальный URL с параметрами
            return True

        return False

    def detect_attack(self, request_data):
        """Улучшенная детекция с фильтрацией ложных срабатываний"""
        try:
            # Извлекаем метод и URL
            lines = request_data.split('\n')
            if not lines:
                return {'is_attack': False, 'type': 'Normal', 'confidence': 0}

            first_line = lines[0]
            parts = first_line.split()
            if len(parts) < 2:
                return {'is_attack': False, 'type': 'Normal', 'confidence': 0}

            method = parts[0]
            url = parts[1]
            url_lower = url.lower()

            # ПЕРВОЕ: Проверяем, не нормальный ли это запрос
            if self.is_normal_request(url):
                return {'is_attack': False, 'type': 'Normal', 'confidence': 0}

            # ВТОРОЕ: Детекция атак с более строгими правилами

            # 1. SQL Injection (более строгие правила)
            sql_patterns = [
                r"['\"].*\s+(or|and)\s+.*['\"]",  # ' or '1'='1
                r"union\s+select\s+",            # union select
                r"select\s+\*\s+from",           # select * from
                r"insert\s+into",                # insert into
                r"drop\s+table",                 # drop table
                r"1=['\"]1",                     # 1='1 (но не просто 1=1)
                r"--\s*$",                       # -- в конце
                r"\/\*.*\*\/"                    # /* комментарий */
            ]

            has_sql = False
            for pattern in sql_patterns:
                if re.search(pattern, url_lower, re.IGNORECASE):
                    has_sql = True
                    break

            # 2. XSS (только реальные теги)
            xss_patterns = [
                r"<script[^>]*>.*</script>",     # полный тег script
                r"javascript:\s*alert\s*\(",     # javascript:alert(
                r"onload\s*=\s*[\"'][^\"']*alert", # onload="alert(...)"
                r"onerror\s*=\s*[\"'][^\"']*alert", # onerror="alert(...)"
                r"<img[^>]*onerror\s*=",         # <img onerror=
                r"<iframe[^>]*src\s*="           # <iframe src=
            ]

            has_xss = False
            for pattern in xss_patterns:
                if re.search(pattern, url_lower, re.IGNORECASE):
                    has_xss = True
                    break

            # 3. Path Traversal (множественные ../)
            traversal_patterns = [
                r"\.\.\/\.\.\/\.\.\/",           # три или более ../
                r"\.\.\\\.\.\\\.\.\\",           # три или более ..\
                r"etc/passwd",                   # /etc/passwd
                r"win\.ini",                     # win.ini
                r"\.\.%2f\.\.%2f\.\.%2f"         # закодированные ../
            ]

            has_traversal = False
            for pattern in traversal_patterns:
                if re.search(pattern, url_lower, re.IGNORECASE):
                    has_traversal = True
                    break

            # 4. Command Injection (команды с разделителями)
            cmd_patterns = [
                r";\s*(ls|cat|id|whoami|pwd)\b", # ; ls, ; cat
                r"\|\s*(ls|cat|id|whoami|pwd)\b", # | ls, | cat
                r"`\s*(ls|cat|id|whoami|pwd)\s*`", # `ls`, `id`
                r"\$\s*\(\s*(ls|cat|id|whoami|pwd)\s*\)", # $(ls), $(id)
                r"&&\s*(ls|cat|id|whoami|pwd)\b"  # && ls, && cat
            ]

            has_cmd = False
            for pattern in cmd_patterns:
                if re.search(pattern, url_lower, re.IGNORECASE):
                    has_cmd = True
                    break

            # 5. XXE (ТОЛЬКО ЯВНЫЕ ПРИЗНАКИ - не просто & и =)
            # В строгом режиме игнорируем & и = в параметрах
            xxe_patterns = [
                r"<!DOCTYPE\s+[^>]*>",           # <!DOCTYPE foo>
                r"<!ENTITY\s+[^>]*>",            # <!ENTITY xxe>
                r"SYSTEM\s+['\"]file:///",       # SYSTEM "file:///
                r"&[a-zA-Z]+;\s*%",              # &entity; %
                r"%[a-zA-Z]+;\s*&"               # %entity; &
            ]

            has_xxe = False
            for pattern in xxe_patterns:
                if re.search(pattern, url_lower, re.IGNORECASE):
                    has_xxe = True
                    break

            # Определяем тип атаки
            attack_type = "Normal"
            confidence = 0.0

            if has_sql:
                attack_type = "SQL Injection"
                confidence = 0.96
            elif has_xss:
                attack_type = "XSS"
                confidence = 0.92
            elif has_traversal:
                attack_type = "Path Traversal"
                confidence = 0.88
            elif has_cmd:
                attack_type = "Command Injection"
                confidence = 0.90
            elif has_xxe and self.strict_mode:  # В строгом режиме только явные XXE
                attack_type = "XXE"
                confidence = 0.85

            is_attack = has_sql or has_xss or has_traversal or has_cmd or (has_xxe and self.strict_mode)

            # Обучение только на реальных атаках с высокой уверенностью
            if is_attack and confidence > 0.85 and self.enable_learning and self.learner:
                added = self.learner.learn_attack(url, attack_type)
                if added > 0:
                    print(f"{self.YELLOW}  🧠 Выучено {added} паттернов для {attack_type}{self.RESET}")

            return {
                'is_attack': is_attack,
                'type': attack_type,
                'confidence': confidence,
                'method': method,
                'url': url,
                'details': {
                    'sql': has_sql,
                    'xss': has_xss,
                    'traversal': has_traversal,
                    'cmd': has_cmd,
                    'xxe': has_xxe
                }
            }

        except Exception as e:
            print(f"{self.RED}Ошибка детекции: {e}{self.RESET}")
            return {'is_attack': False, 'type': 'Normal', 'confidence': 0}

    def process_tcpdump_line(self, line):
        """Обработка строки из tcpdump"""
        line = line.strip()

        # Ищем HTTP запросы
        if ('GET ' in line or 'POST ' in line or 'PUT ' in line or
            'DELETE ' in line or 'HEAD ' in line):

            # Очищаем строку
            line = re.sub(r'[^\x20-\x7E]+', ' ', line)

            # Извлекаем IP и порт
            src_ip = "127.0.0.1"
            src_port = "unknown"

            ip_match = re.search(r'(\d+\.\d+\.\d+\.\d+)\.(\d+)', line)
            if ip_match:
                src_ip = ip_match.group(1)
                src_port = ip_match.group(2)

            # Увеличиваем счетчик запросов
            self.stats['total'] += 1

            # Детектируем атаку
            detection = self.detect_attack(line)

            if detection['is_attack']:
                self.log_attack(detection, src_ip, src_port)
            else:
                self.stats['normal'] += 1
                # Показываем только каждый 20-й нормальный запрос
                if self.stats['normal'] % 20 == 0:
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    url_short = detection['url'][:40] + "..." if len(detection['url']) > 40 else detection['url']
                    print(f"{self.GREEN}[{timestamp}] 📡 {detection['method']} {src_ip}:{src_port} → {url_short}{self.RESET}")

    def log_attack(self, detection, src_ip, src_port):
        """Логирование атаки"""
        timestamp = datetime.now().strftime("%H:%M:%S")

        print(f"\n{self.RED}{'🚨'*10}{self.RESET}")
        print(f"{self.RED}{self.BOLD}🚨 ОБНАРУЖЕНА АТАКА! [{timestamp}]{self.RESET}")
        print(f"{self.RED}{'─'*50}{self.RESET}")
        print(f"{self.YELLOW}🔥 Тип:{self.RESET} {detection['type']}")
        print(f"{self.YELLOW}📊 Уверенность:{self.RESET} {detection['confidence']:.0%}")
        print(f"{self.YELLOW}📍 Источник:{self.RESET} {src_ip}:{src_port}")
        print(f"{self.YELLOW}📝 Метод:{self.RESET} {detection['method']}")

        # Показываем URL (обрезанный)
        url = detection['url']
        if len(url) > 80:
            print(f"{self.YELLOW}🎯 URL:{self.RESET} {url[:80]}...")
        else:
            print(f"{self.YELLOW}🎯 URL:{self.RESET} {url}")

        # Показываем детали
        details = []
        if detection['details']['sql']: details.append("SQL")
        if detection['details']['xss']: details.append("XSS")
        if detection['details']['traversal']: details.append("Traversal")
        if detection['details']['cmd']: details.append("Command")
        if detection['details']['xxe']: details.append("XXE")

        if details:
            print(f"{self.YELLOW}🛡️  Признаки:{self.RESET} {', '.join(details)}")

        print(f"{self.RED}{'─'*50}{self.RESET}")

        # Обновляем статистику
        self.stats['attacks'] += 1
        self.show_stats()

    def show_stats(self):
        """Показать статистику"""
        total = self.stats['total']
        attacks = self.stats['attacks']
        normal = self.stats['normal']
        elapsed = time.time() - self.stats['start_time']

        if total > 0:
            print(f"\n{self.CYAN}📊 СТАТИСТИКА:{self.RESET}")
            print(f"{self.CYAN}{'─'*40}{self.RESET}")
            print(f"{self.BLUE}📦 Всего запросов:{self.RESET} {total}")
            print(f"{self.GREEN}✅ Нормальных:{self.RESET} {normal}")
            print(f"{self.RED}🚨 Атак:{self.RESET} {attacks}")

            if attacks > 0:
                detection_rate = attacks / total * 100
                print(f"{self.YELLOW}🎯 Эффективность:{self.RESET} {detection_rate:.1f}%")

            print(f"{self.YELLOW}⏱️  Время:{self.RESET} {int(elapsed)} сек")
            print(f"{self.CYAN}{'─'*40}{self.RESET}\n")

    def capture_traffic(self):
        """Захват трафика"""
        try:
            print(f"{self.GREEN}🎯 Захват трафика на порту {self.port}...{self.RESET}")

            # Команда tcpdump
            cmd = ['sudo', 'tcpdump', '-i', 'lo', '-A', f'port {self.port}', '-s', '0', '-l', '-q']
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            print(f"{self.YELLOW}📡 Мониторинг запущен. Обновляйте страницу браузера или отправляйте запросы...{self.RESET}")

            for line in iter(process.stdout.readline, ''):
                if not self.running:
                    break
                self.process_tcpdump_line(line)

        except KeyboardInterrupt:
            print(f"\n{self.YELLOW}🛑 Захват остановлен{self.RESET}")
        except Exception as e:
            print(f"{self.RED}❌ Ошибка: {e}{self.RESET}")

    def start(self):
        """Запуск монитора"""
        try:
            print(f"{self.GREEN}✅ Монитор запущен!{self.RESET}")
            self.capture_traffic()
        except KeyboardInterrupt:
            print(f"\n{self.YELLOW}🛑 Монитор остановлен{self.RESET}")
        finally:
            # Финальная статистика
            total_time = time.time() - self.stats['start_time']

            print(f"\n{self.CYAN}{'='*60}{self.RESET}")
            print(f"{self.BOLD}📊 ФИНАЛЬНАЯ СТАТИСТИКА{self.RESET}")
            print(f"{self.CYAN}{'='*60}{self.RESET}")
            print(f"{self.BLUE}⏱️  Общее время:{self.RESET} {int(total_time)} сек")
            print(f"{self.BLUE}📦 Всего запросов:{self.RESET} {self.stats['total']}")
            print(f"{self.GREEN}✅ Нормальных:{self.RESET} {self.stats['normal']}")
            print(f"{self.RED}🚨 Атак:{self.RESET} {self.stats['attacks']}")

            if self.stats['total'] > 0:
                detection_rate = self.stats['attacks'] / self.stats['total'] * 100
                print(f"{self.YELLOW}🎯 Эффективность:{self.RESET} {detection_rate:.1f}%")

            # Сохраняем обучение
            if self.enable_learning and self.learner and self.learner.new_patterns_count > 0:
                self.learner.save_patterns()
                print(f"{self.GREEN}💾 Паттерны сохранены в ml_models/attack_patterns.json{self.RESET}")

            print(f"{self.CYAN}{'='*60}{self.RESET}")

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Умный монитор для honeypot')
    parser.add_argument('--port', '-p', type=int, default=3000, help='Порт honeypot')
    parser.add_argument('--no-learn', action='store_true', help='Отключить автообучение')
    parser.add_argument('--show-patterns', action='store_true', help='Показать паттерны')
    parser.add_argument('--strict', action='store_true', help='Строгий режим (меньше ложных срабатываний)')
    parser.add_argument('--test', action='store_true', help='Тестовый режим')

    args = parser.parse_args()

    if args.show_patterns:
        try:
            with open("ml_models/attack_patterns.json", 'r') as f:
                data = json.load(f)

            print("\n📚 ВЫУЧЕННЫЕ ПАТТЕРНЫ:")
            print("="*50)

            if "patterns" in data:
                patterns = data["patterns"]
                for atype, pats in patterns.items():
                    if pats:
                        print(f"\n{atype.upper()} ({len(pats)}):")
                        for p in pats[:15]:
                            print(f"  - {p}")
                        if len(pats) > 15:
                            print(f"  ... и еще {len(pats)-15}")

            if "false_positives" in data and data["false_positives"]:
                print(f"\n🚫 Игнорируемые паттерны ({len(data['false_positives'])}):")
                for fp in data["false_positives"][:10]:
                    print(f"  - {fp}")

            return
        except FileNotFoundError:
            print("Файл паттернов не найден")
            return

    if args.test:
        print("🧪 ТЕСТОВЫЙ РЕЖИМ")
        print("="*50)

        monitor = WorkingMonitor(port=args.port, enable_learning=not args.no_learn, strict_mode=args.strict)

        # Тестовые запросы
        test_requests = [
            ("GET /socket.io/?EIO=4&transport=polling&t=abc123 HTTP/1.1", "Нормальный (Socket.io)"),
            ("GET /styles.css HTTP/1.1", "Нормальный (CSS)"),
            ("GET /api/Challenges?name=Score%20Board HTTP/1.1", "Нормальный (API)"),
            ("GET /test' OR '1'='1 HTTP/1.1", "SQL инъекция"),
            ("GET /test?q=<script>alert(1)</script> HTTP/1.1", "XSS"),
            ("GET /../../../etc/passwd HTTP/1.1", "Path Traversal"),
            ("GET /test;ls HTTP/1.1", "Command Injection"),
        ]

        for request, description in test_requests:
            print(f"\n🔍 Тест: {description}")
            print(f"Запрос: {request}")
            detection = monitor.detect_attack(request)
            print(f"Результат: {'АТАКА' if detection['is_attack'] else 'Нормальный'} - {detection['type']}")
            print("-"*40)

        return

    if os.geteuid() != 0:
        print("❌ Требуются root-права для tcpdump!")
        print("   Запустите: sudo python scripts/core/working_monitor.py")
        sys.exit(1)

    if shutil.which('tcpdump') is None:
        print("❌ tcpdump не найден!")
        print("   Установите: sudo apt install tcpdump")
        sys.exit(1)

    os.makedirs("ml_models", exist_ok=True)
    monitor = WorkingMonitor(port=args.port, enable_learning=not args.no_learn, strict_mode=args.strict)
    monitor.start()

if __name__ == "__main__":
    main()
