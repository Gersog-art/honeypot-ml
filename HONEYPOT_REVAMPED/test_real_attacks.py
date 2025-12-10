#!/usr/bin/env python3
"""
ТЕСТИРОВАНИЕ РАЗЛИЧНЫХ ТИПОВ ЗАПРОСОВ
"""

import os
import time

def test_requests():
    """Тестируем разные типы запросов"""

    print("🧪 ТЕСТИРОВАНИЕ ДЕТЕКЦИИ")
    print("="*50)

    # Нормальные запросы (не должны детектироваться как атаки)
    normal_requests = [
        "GET / HTTP/1.1",
        "GET /styles.css HTTP/1.1",
        "GET /vendor.js HTTP/1.1",
        "GET /socket.io/?EIO=4&transport=polling HTTP/1.1",
        "GET /api/Challenges?name=Score%20Board HTTP/1.1",
        "GET /assets/image.jpg HTTP/1.1",
        "GET /favicon.ico HTTP/1.1",
    ]

    # Атаки (должны детектироваться)
    attack_requests = [
        ("GET /test' OR '1'='1 HTTP/1.1", "SQL инъекция"),
        ("GET /search?q=<script>alert('xss')</script> HTTP/1.1", "XSS"),
        ("GET /../../../etc/passwd HTTP/1.1", "Path Traversal"),
        ("GET /test;ls HTTP/1.1", "Command Injection"),
        ("GET /test?xml=<!DOCTYPE foo [<!ENTITY xxe SYSTEM \"file:///etc/passwd\">]> HTTP/1.1", "XXE"),
    ]

    print("\n📡 НОРМАЛЬНЫЕ ЗАПРОСЫ (не должны быть атаками):")
    for req in normal_requests:
        print(f"  {req[:60]}...")
        os.system(f"curl -s 'http://localhost:3000{req.split()[1]}' > /dev/null 2>&1")
        time.sleep(0.2)

    print("\n🔥 РЕАЛЬНЫЕ АТАКИ (должны детектироваться):")
    for req, desc in attack_requests:
        print(f"  {desc}: {req[:60]}...")
        # Кодируем URL для curl
        import urllib.parse
        url_part = req.split()[1]
        encoded = urllib.parse.quote(url_part, safe='')
        os.system(f"curl -s 'http://localhost:3000{url_part}' > /dev/null 2>&1")
        time.sleep(0.5)

    print("\n✅ Тестирование завершено!")
    print("📊 Проверьте монитор - должны быть обнаружены только реальные атаки")

if __name__ == "__main__":
    test_requests()
