#!/usr/bin/env python3
"""
МИНИМАЛЬНЫЙ ПРОКСИ-МОНИТОР
Самая простая рабочая версия
"""

import socket
import sys
import time
from datetime import datetime

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

def start_proxy(listen_port=3001, target_port=3000):
    """Запуск прокси"""
    print("🎯 МИНИМАЛЬНЫЙ ПРОКСИ-МОНИТОР")
    print("================================")
    print(f"📍 Слушаю порт: {listen_port}")
    print(f"🎯 Перенаправляю на: {target_port}")
    print("📡 Ожидание запросов...")
    print("================================")
    
    stats = {'total': 0, 'attacks': 0, 'normal': 0}
    
    try:
        # Создаем серверный сокет
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', listen_port))
        server.listen(5)
        
        print(f"✅ Прокси запущен на порту {listen_port}")
        
        while True:
            # Принимаем соединение
            client_sock, client_addr = server.accept()
            
            # Получаем данные
            data = client_sock.recv(4096)
            
            if data:
                stats['total'] += 1
                
                # Анализируем запрос
                attack_type, confidence = detect_attack(data.decode('utf-8', errors='ignore'))
                
                if attack_type != "Normal":
                    stats['attacks'] += 1
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    print(f"\n🚨 [{timestamp}] ОБНАРУЖЕНА АТАКА!")
                    print(f"   🔥 Тип: {attack_type}")
                    print(f"   📊 Уверенность: {confidence:.0%}")
                    print(f"   📍 От: {client_addr[0]}")
                    
                    # Показываем первые 100 символов запроса
                    req_line = data.decode('utf-8', errors='ignore').split('\n')[0]
                    print(f"   📝 Запрос: {req_line[:80]}...")
                else:
                    stats['normal'] += 1
                    # Показываем каждые 5 нормальных запросов
                    if stats['normal'] % 5 == 0:
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        print(f"[{timestamp}] 📡 Нормальных запросов: {stats['normal']}")
                
                # Перенаправляем на honeypot
                remote_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                remote_sock.connect(('localhost', target_port))
                remote_sock.send(data)
                
                # Получаем ответ
                response = remote_sock.recv(4096)
                
                # Отправляем ответ клиенту
                client_sock.send(response)
                
                # Закрываем соединения
                remote_sock.close()
                client_sock.close()
                
                # Показываем статистику
                if stats['total'] % 10 == 0:
                    print(f"\n📊 Статистика: Всего={stats['total']}, Атак={stats['attacks']}")
            
    except KeyboardInterrupt:
        print("\n🛑 Прокси остановлен")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
    finally:
        print(f"\n📊 ИТОГОВАЯ СТАТИСТИКА:")
        print(f"   Всего запросов: {stats['total']}")
        print(f"   Атак обнаружено: {stats['attacks']}")
        print(f"   Нормальных: {stats['normal']}")
        
        if stats['total'] > 0:
            print(f"   Эффективность: {stats['attacks']/stats['total']*100:.1f}%")

if __name__ == "__main__":
    # Парсим аргументы
    listen_port = 3001
    target_port = 3000
    
    if len(sys.argv) > 1:
        try:
            listen_port = int(sys.argv[1])
            target_port = int(sys.argv[2]) if len(sys.argv) > 2 else 3000
        except:
            pass
    
    start_proxy(listen_port, target_port)
