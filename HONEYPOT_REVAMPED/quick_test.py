#!/usr/bin/env python3
"""
Быстрый тест обнаружения атак
"""

import requests
import time
import sys

def test_attack(url, name):
    """Тестирование одной атаки"""
    try:
        print(f"\n🔥 Тестируем: {name}")
        print(f"   🔗 URL: {url[:80]}..." if len(url) > 80 else f"   🔗 URL: {url}")
        
        start = time.time()
        response = requests.get(url, timeout=5)
        elapsed = int((time.time() - start) * 1000)
        
        print(f"   ✅ Статус: {response.status_code}")
        print(f"   ⏱️  Время: {elapsed}мс")
        
        # Простой детектор
        url_lower = url.lower()
        
        if "'" in url_lower or "union" in url_lower or "select" in url_lower:
            print(f"   🚨 ОБНАРУЖЕНО: SQL Injection")
            return "SQL"
        elif "<script>" in url_lower or "javascript:" in url_lower:
            print(f"   🚨 ОБНАРУЖЕНО: XSS")
            return "XSS"
        elif "../" in url_lower or "etc/passwd" in url_lower:
            print(f"   🚨 ОБНАРУЖЕНО: Path Traversal")
            return "Traversal"
        elif ";" in url_lower or "|" in url_lower or "`" in url_lower:
            print(f"   🚨 ОБНАРУЖЕНО: Command Injection")
            return "Command"
        else:
            print(f"   ✅ Нормальный запрос")
            return "Normal"
            
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return "Error"

def main():
    """Основная функция"""
    print("=" * 70)
    print("🧪 БЫСТРЫЙ ТЕСТ ОБНАРУЖЕНИЯ АТАК")
    print("=" * 70)
    
    base_url = "http://localhost:3000"
    
    tests = [
        ("SQL Injection", f"{base_url}/rest/products/search?q=' OR '1'='1"),
        ("SQL Injection 2", f"{base_url}/rest/products/search?q=' UNION SELECT * FROM users--"),
        ("XSS", f"{base_url}/#/search?q=<script>alert('XSS')</script>"),
        ("XSS 2", f"{base_url}/#/search?q=<img src='x' onerror=alert('XSS')>"),
        ("Path Traversal", f"{base_url}/assets/../../../etc/passwd"),
        ("Command Injection", f"{base_url}/rest/products/search?q='; ls -la /"),
        ("Normal", f"{base_url}/"),
        ("Normal 2", f"{base_url}/#/login"),
    ]
    
    results = []
    
    for name, url in tests:
        result = test_attack(url, name)
        results.append((name, result))
        time.sleep(0.5)
    
    # Статистика
    print("\n" + "=" * 70)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
    print("=" * 70)
    
    attacks = [r for r in results if r[1] in ["SQL", "XSS", "Traversal", "Command"]]
    normals = [r for r in results if r[1] == "Normal"]
    
    print(f"🔥 Всего атак отправлено: {len(attacks)}")
    print(f"✅ Нормальных запросов: {len(normals)}")
    
    if attacks:
        print(f"\n🎯 ОБНАРУЖЕННЫЕ АТАКИ:")
        for attack in attacks:
            print(f"   • {attack[0]}: {attack[1]}")
    
    print("\n💡 ЗАПУСТИТЕ МОНИТОР ДЛЯ ОБНАРУЖЕНИЯ В РЕАЛЬНОМ ВРЕМЕНИ:")
    print("   sudo python scripts/core/working_monitor.py")
    print("=" * 70)

if __name__ == "__main__":
    # Проверяем доступность honeypot
    try:
        response = requests.get("http://localhost:3000", timeout=3)
        if response.status_code == 200:
            main()
        else:
            print("❌ Honeypot не отвечает!")
            print("   Запустите: docker run -d -p 3000:3000 bkimminich/juice-shop")
    except:
        print("❌ Honeypot не запущен!")
        print("   Запустите: docker run -d -p 3000:3000 bkimminich/juice-shop")
