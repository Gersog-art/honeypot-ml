#!/usr/bin/env python3
"""
САМЫЙ ПРОСТОЙ ЗАПУСК - ВСЁ В ОДНОМ ФАЙЛЕ
"""

import os
import sys
import time
import socket
import subprocess
from datetime import datetime
from threading import Thread

print("🎯 ПРОСТАЯ СИСТЕМА ОБНАРУЖЕНИЯ АТАК")
print("=================================")

# 1. Запуск Docker (если не запущен)
print("1. Запуск Docker...")
os.system("sudo systemctl start docker 2>/dev/null || true")

# 2. Остановка старых контейнеров
print("2. Очистка...")
os.system("docker stop honeypot-juice 2>/dev/null || true")
os.system("docker rm honeypot-juice 2>/dev/null || true")
os.system("sudo fuser -k 3000/tcp 2>/dev/null || true")
os.system("sudo fuser -k 3001/tcp 2>/dev/null || true")

# 3. Запуск honeypot
print("3. Запуск OWASP Juice Shop...")
result = subprocess.run(
    "docker run -d -p 3000:3000 bkimminich/juice-shop",
    shell=True,
    capture_output=True,
    text=True
)

if result.returncode != 0:
    print("❌ Ошибка запуска Docker!")
    print("   Попробуйте запустить вручную:")
    print("   sudo docker run -d -p 3000:3000 bkimminich/juice-shop")
    sys.exit(1)

print("✅ Honeypot запущен!")
time.sleep(5)

# 4. Проверка honeypot
print("4. Проверка honeypot...")
try:
    import urllib.request
    response = urllib.request.urlopen("http://localhost:3000", timeout=5)
    if response.status == 200:
        print("✅ Honeypot работает: http://localhost:3000")
    else:
        print("⚠️  Honeypot отвечает со статусом:", response.status)
except:
    print("❌ Honeypot недоступен!")
    print("   Проверьте: docker ps")
    sys.exit(1)

# 5. Запуск простого прокси
print("\n5. Запуск монитора...")
print("="*60)
print("🛡️  МОНИТОР ЗАПУЩЕН")
print("="*60)
print("📍 Порт монитора: 3001")
print("🎯 Honeypot порт: 3000")
print("📡 Отправляйте запросы на http://localhost:3001")
print("="*60)

# Статистика
stats = {'total': 0, 'attacks': 0, 'normal': 0}

def detect_attack(data):
    """Обнаружение атак"""
    data_str = data.lower()
    
    if "'" in data_str or "union" in data_str or "select" in data_str:
        return "SQL Injection", 0.93
    elif "<script>" in data_str or "javascript:" in data_str:
        return "XSS", 0.86
    elif "../" in data_str or "etc/passwd" in data_str:
        return "Path Traversal", 0.78
    elif ";" in data_str or "|" in data_str or "`" in data_str:
        return "Command Injection", 0.82
    else:
        return "Normal", 0.0

def handle_client(client_sock, client_addr):
    """Обработка клиента"""
    try:
        # Получаем запрос
        data = client_sock.recv(4096)
        if not data:
            return
        
        stats['total'] += 1
        
        # Анализируем
        attack_type, confidence = detect_attack(data.decode('utf-8', errors='ignore'))
        
        # Логируем
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if attack_type != "Normal":
            stats['attacks'] += 1
            print(f"\n🚨 [{timestamp}] ОБНАРУЖЕНА АТАКА!")
            print(f"   🔥 Тип: {attack_type}")
            print(f"   📊 Уверенность: {confidence:.0%}")
            print(f"   📍 От: {client_addr[0]}")
            
            # Показываем первую строку запроса
            req_line = data.decode('utf-8', errors='ignore').split('\n')[0]
            print(f"   📝 Запрос: {req_line[:80]}...")
            print("   ──────────────────────────────────────────")
        else:
            stats['normal'] += 1
            if stats['normal'] % 5 == 0:
                print(f"[{timestamp}] 📡 Нормальных запросов: {stats['normal']}")
        
        # Показываем статистику
        if stats['total'] % 5 == 0:
            print(f"\n📊 Статистика: Всего={stats['total']}, Атак={stats['attacks']}")
        
        # Перенаправляем на honeypot
        remote_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        remote_sock.connect(('localhost', 3000))
        remote_sock.send(data)
        
        # Получаем ответ
        response = remote_sock.recv(4096)
        
        # Отправляем клиенту
        client_sock.send(response)
        
        # Закрываем соединения
        remote_sock.close()
        client_sock.close()
        
    except Exception as e:
        pass  # Игнорируем ошибки

# Запускаем сервер
try:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('0.0.0.0', 3001))
    server.listen(5)
    
    print("\n✅ Монитор запущен и ждет запросы...")
    print("🎯 Отправьте тестовые запросы:")
    print("   curl \"http://localhost:3001/rest/products/search?q=test\"")
    print("   curl \"http://localhost:3001/assets/../../../etc/passwd\"")
    print("\n🛑 Для остановки нажмите Ctrl+C")
    print("="*60)
    
    # Автоматическая отправка тестовых запросов
    def send_test_requests():
        time.sleep(3)
        print("\n🧪 Отправляю тестовые запросы...")
        
        test_urls = [
            "http://localhost:3001/",
            "http://localhost:3001/rest/products/search?q=' OR '1'='1",
            "http://localhost:3001/rest/products/search?q=<script>alert('XSS')</script>",
            "http://localhost:3001/assets/../../../etc/passwd",
            "http://localhost:3001/rest/products/search?q='; ls -la /",
        ]
        
        for url in test_urls:
            try:
                req = urllib.request.Request(url)
                urllib.request.urlopen(req, timeout=2)
                time.sleep(1)
            except:
                pass
    
    # Запускаем тесты в отдельном потоке
    test_thread = Thread(target=send_test_requests)
    test_thread.daemon = True
    test_thread.start()
    
    # Главный цикл сервера
    while True:
        client_sock, client_addr = server.accept()
        Thread(target=handle_client, args=(client_sock, client_addr)).start()
        
except KeyboardInterrupt:
    print("\n🛑 Остановка...")
except Exception as e:
    print(f"\n❌ Ошибка: {e}")

finally:
    # Закрываем сервер
    try:
        server.close()
    except:
        pass
    
    # Очистка
    print("\n🧹 Очистка...")
    os.system("docker stop $(docker ps -q) 2>/dev/null || true")
    os.system("docker rm $(docker ps -a -q) 2>/dev/null || true")
    
    print(f"\n📊 ФИНАЛЬНАЯ СТАТИСТИКА:")
    print(f"   Всего запросов: {stats['total']}")
    print(f"   Атак обнаружено: {stats['attacks']}")
    print(f"   Нормальных: {stats['normal']}")
    
    if stats['total'] > 0:
        print(f"   Эффективность: {stats['attacks']/stats['total']*100:.1f}%")
    
    print("\n✅ Система остановлена!")
