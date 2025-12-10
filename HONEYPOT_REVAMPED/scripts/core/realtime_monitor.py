#!/usr/bin/env python3
"""
УЛУЧШЕННЫЙ МОНИТОР РЕАЛЬНОГО ВРЕМЕНИ
Обнаруживает атаки в сетевом трафике с помощью ML
"""

import numpy as np
import pandas as pd
import joblib
import json
import time
import sys
import os
from datetime import datetime
from collections import deque, defaultdict
import socket
import struct
from threading import Thread, Lock
from scapy.all import *
from scapy.layers.http import HTTPRequest, HTTPResponse
import warnings
warnings.filterwarnings("ignore")

# Добавляем путь для импортов
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class RealTimeAttackMonitor:
    def __init__(self, interface="lo", target_port=3000, model_path="ml_models/attack_detector_model.pkl"):
        """Инициализация монитора"""
        self.interface = interface
        self.target_port = target_port
        self.model_path = model_path
        
        # Статистика
        self.stats = {
            'total_packets': 0,
            'attacks_detected': 0,
            'normal_packets': 0,
            'attack_types': defaultdict(int),
            'start_time': time.time(),
            'last_alert': 0
        }
        
        # Кэши для сопоставления запросов/ответов
        self.request_cache = {}
        self.attack_history = deque(maxlen=100)
        
        # Блокировка для потокобезопасности
        self.lock = Lock()
        
        # ML модель
        self.model = None
        self.metadata = {}
        self.threshold = 0.7
        
        # Цвета для вывода
        self.colors = {
            'RED': '\033[91m',
            'GREEN': '\033[92m',
            'YELLOW': '\033[93m',
            'BLUE': '\033[94m',
            'MAGENTA': '\033[95m',
            'CYAN': '\033[96m',
            'WHITE': '\033[97m',
            'RESET': '\033[0m',
            'BOLD': '\033[1m'
        }
        
        self.init_display()
        self.load_model()
    
    def init_display(self):
        """Инициализация отображения"""
        os.system('clear')
        print(f"{self.colors['CYAN']}{'='*80}{self.colors['RESET']}")
        print(f"{self.colors['BOLD']}{self.colors['YELLOW']}🛡️  REAL-TIME HONEYPOT ATTACK MONITOR v2.0{self.colors['RESET']}")
        print(f"{self.colors['CYAN']}{'='*80}{self.colors['RESET']}")
        print(f"{self.colors['BLUE']}📍 Интерфейс:{self.colors['RESET']} {self.interface}")
        print(f"{self.colors['BLUE']}🎯 Порт honeypot:{self.colors['RESET']} {self.target_port}")
        print(f"{self.colors['BLUE']}📊 ML модель:{self.colors['RESET']} {os.path.basename(self.model_path)}")
        print(f"{self.colors['CYAN']}{'-'*80}{self.colors['RESET']}")
        print(f"{self.colors['GREEN']}✅ Система запущена. Ожидание трафика...{self.colors['RESET']}")
        print(f"{self.colors['YELLOW']}💡 Отправьте атаки на http://localhost:{self.target_port}{self.colors['RESET']}")
        print(f"{self.colors['CYAN']}{'-'*80}{self.colors['RESET']}\n")
    
    def load_model(self):
        """Загрузка ML модели"""
        try:
            if not os.path.exists(self.model_path):
                print(f"{self.colors['RED']}❌ Файл модели не найден: {self.model_path}{self.colors['RESET']}")
                print(f"{self.colors['YELLOW']}⚠️  Запустите обучение модели:{self.colors['RESET']}")
                print(f"{self.colors['WHITE']}   python scripts/ml/train_model.py{self.colors['RESET']}")
                sys.exit(1)
            
            print(f"{self.colors['BLUE']}📊 Загрузка ML модели...{self.colors['RESET']}")
            self.model = joblib.load(self.model_path)
            
            # Загрузка метаданных
            metadata_path = 'ml_models/model_metadata.json'
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    self.metadata = json.load(f)
                    self.threshold = self.metadata.get('detection_threshold', 0.7)
                
                print(f"{self.colors['GREEN']}✅ Модель загружена:{self.colors['RESET']} {self.metadata.get('model_name', 'Unknown')}")
                print(f"{self.colors['GREEN']}📈 Точность:{self.colors['RESET']} {self.metadata.get('accuracy', 0):.1%}")
                print(f"{self.colors['GREEN']}🎯 Порог:{self.colors['RESET']} {self.threshold}")
            else:
                print(f"{self.colors['YELLOW']}⚠️  Модель загружена, но метаданные отсутствуют{self.colors['RESET']}")
                
        except Exception as e:
            print(f"{self.colors['RED']}❌ Ошибка загрузки модели: {e}{self.colors['RESET']}")
            sys.exit(1)
    
    def extract_features_from_packet(self, packet, url, response_time=100, status_code=200):
        """Извлечение признаков из пакета"""
        try:
            url_lower = str(url).lower()
            
            # Признаки атак
            sql_keywords = ["'", "or 1=1", "union", "--", "select ", "from ", "sleep(", "benchmark", "drop ", "insert ", "update "]
            xss_keywords = ["<script>", "alert(", "onerror=", "onload=", "<img", "javascript:", "document.cookie", "eval(", "document.write"]
            traversal_keywords = ["../", "..%2f", "etc/passwd", "%252f", "ftp://", "file://", "../../", "..\\", "win.ini"]
            
            has_sql = 1 if any(kw in url_lower for kw in sql_keywords) else 0
            has_xss = 1 if any(kw in url_lower for kw in xss_keywords) else 0
            has_traversal = 1 if any(kw in url_lower for kw in traversal_keywords) else 0
            
            # Размер пакета
            packet_size = len(packet) if hasattr(packet, '__len__') else len(str(packet))
            
            # Категории размера
            size_cat_small = 1 if packet_size < 500 else 0
            size_cat_medium = 1 if 500 <= packet_size < 1500 else 0
            size_cat_large = 1 if 1500 <= packet_size < 5000 else 0
            size_cat_huge = 1 if packet_size >= 5000 else 0
            
            # Индикатор атаки
            attack_indicator = 1 if (has_sql or has_xss or has_traversal) else 0
            
            # 10 признаков в правильном порядке
            features = np.array([[
                size_cat_small, size_cat_medium, size_cat_large, size_cat_huge,
                response_time, has_sql, has_xss, has_traversal,
                status_code, attack_indicator
            ]])
            
            # Дополнительная информация для отладки
            feature_info = {
                'url': url[:100] + "..." if len(url) > 100 else url,
                'packet_size': packet_size,
                'has_sql': has_sql,
                'has_xss': has_xss,
                'has_traversal': has_traversal,
                'status_code': status_code,
                'response_time': response_time,
                'size_categories': f"S:{size_cat_small} M:{size_cat_medium} L:{size_cat_large} H:{size_cat_huge}"
            }
            
            return features, feature_info
            
        except Exception as e:
            # Возвращаем признаки по умолчанию при ошибке
            default_features = np.array([[0, 1, 0, 0, 100, 0, 0, 0, 200, 0]])
            default_info = {'url': 'ERROR', 'error': str(e)}
            return default_features, default_info
    
    def detect_attack(self, features, feature_info):
        """Обнаружение атаки с помощью ML модели"""
        try:
            if self.model is None:
                return {'is_attack': False, 'attack_type': 'Model not loaded', 'confidence': 0}
            
            # Предсказание
            prediction = self.model.predict(features)[0]
            probabilities = self.model.predict_proba(features)[0]
            
            # Определяем уверенность
            confidence = probabilities[1] if len(probabilities) > 1 else 0
            
            # Определяем тип атаки
            attack_type = "Normal"
            if prediction == 1 and confidence > self.threshold:
                if feature_info.get('has_sql', 0):
                    attack_type = "SQL Injection"
                elif feature_info.get('has_xss', 0):
                    attack_type = "XSS"
                elif feature_info.get('has_traversal', 0):
                    attack_type = "Path Traversal"
                else:
                    attack_type = "Unknown Attack"
            
            return {
                'is_attack': prediction == 1 and confidence > self.threshold,
                'attack_type': attack_type,
                'confidence': confidence,
                'features': feature_info,
                'prediction': prediction
            }
            
        except Exception as e:
            return {'is_attack': False, 'attack_type': f'Error: {str(e)}', 'confidence': 0}
    
    def display_attack_alert(self, detection, src_ip, dst_ip, src_port, dst_port, method="GET"):
        """Отображение оповещения об атаке"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        print(f"\n{self.colors['RED']}{'🚨'*20}{self.colors['RESET']}")
        print(f"{self.colors['RED']}{self.colors['BOLD']}🚨 АТАКА ОБНАРУЖЕНА! [{timestamp}]{self.colors['RESET']}")
        print(f"{self.colors['RED']}{'─'*60}{self.colors['RESET']}")
        print(f"{self.colors['YELLOW']}🔥 Тип:{self.colors['RESET']} {detection['attack_type']}")
        print(f"{self.colors['YELLOW']}📊 Уверенность:{self.colors['RESET']} {detection['confidence']:.1%}")
        print(f"{self.colors['YELLOW']}📍 Источник:{self.colors['RESET']} {src_ip}:{src_port}")
        print(f"{self.colors['YELLOW']}🎯 Цель:{self.colors['RESET']} {dst_ip}:{dst_port}")
        print(f"{self.colors['YELLOW']}📝 Метод:{self.colors['RESET']} {method}")
        
        if 'features' in detection:
            feat = detection['features']
            print(f"{self.colors['YELLOW']}🔗 URL:{self.colors['RESET']} {feat.get('url', 'N/A')}")
            print(f"{self.colors['YELLOW']}📦 Размер:{self.colors['RESET']} {feat.get('packet_size', 0)} байт")
            print(f"{self.colors['YELLOW']}⚡ Ответ:{self.colors['RESET']} {feat.get('response_time', 0)} мс")
            print(f"{self.colors['YELLOW']}🛡️  Признаки:{self.colors['RESET']} SQL={feat.get('has_sql', 0)} XSS={feat.get('has_xss', 0)} Traversal={feat.get('has_traversal', 0)}")
        
        print(f"{self.colors['RED']}{'─'*60}{self.colors['RESET']}")
        
        # Обновляем статистику
        self.stats['attack_types'][detection['attack_type']] += 1
    
    def display_normal_traffic(self, src_ip, dst_ip, src_port, dst_port, url):
        """Отображение нормального трафика (с ограничением частоты)"""
        current_time = time.time()
        if current_time - self.stats['last_alert'] > 10:  # Каждые 10 секунд
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"{self.colors['GREEN']}[{timestamp}] 📡 Нормальный трафик: {src_ip}:{src_port} → {dst_ip}:{dst_port}{self.colors['RESET']}")
            self.stats['last_alert'] = current_time
    
    def update_statistics_display(self):
        """Обновление отображения статистики"""
        current_time = time.time()
        elapsed = current_time - self.stats['start_time']
        
        # Обновляем каждые 30 секунд или после каждой атаки
        if elapsed > 30 or self.stats['attacks_detected'] > 0:
            os.system('clear')
            self.init_display()
            
            print(f"{self.colors['CYAN']}📈 СТАТИСТИКА В РЕАЛЬНОМ ВРЕМЕНИ:{self.colors['RESET']}")
            print(f"{self.colors['CYAN']}{'─'*60}{self.colors['RESET']}")
            print(f"{self.colors['BLUE']}📦 Всего пакетов:{self.colors['RESET']} {self.stats['total_packets']}")
            print(f"{self.colors['GREEN']}✅ Нормальных:{self.colors['RESET']} {self.stats['normal_packets']}")
            print(f"{self.colors['RED']}🚨 Атак обнаружено:{self.colors['RESET']} {self.stats['attacks_detected']}")
            
            if self.stats['attack_types']:
                print(f"\n{self.colors['YELLOW']}🎯 ТИПЫ ОБНАРУЖЕННЫХ АТАК:{self.colors['RESET']}")
                for attack_type, count in self.stats['attack_types'].items():
                    print(f"   • {attack_type}: {count}")
            
            detection_rate = self.stats['attacks_detected'] / max(self.stats['total_packets'], 1)
            print(f"\n{self.colors['MAGENTA']}📊 Скорость обнаружения:{self.colors['RESET']} {detection_rate:.1%}")
            print(f"{self.colors['MAGENTA']}⏱️  Время работы:{self.colors['RESET']} {int(elapsed)} сек")
            print(f"{self.colors['CYAN']}{'─'*60}{self.colors['RESET']}\n")
            
            # Сбрасываем таймер
            self.stats['start_time'] = current_time
    
    def process_packet(self, packet):
        """Обработка захваченного пакета"""
        try:
            with self.lock:
                self.stats['total_packets'] += 1
                
                # Проверяем TCP пакеты
                if TCP in packet:
                    src_port = packet[TCP].sport
                    dst_port = packet[TCP].dport
                    
                    # Проверяем трафик к honeypot
                    if dst_port == self.target_port or src_port == self.target_port:
                        
                        # HTTP запрос
                        if packet.haslayer(HTTPRequest):
                            http = packet[HTTPRequest]
                            
                            # Извлекаем URL
                            path = http.Path.decode('utf-8', errors='ignore') if http.Path else "/"
                            host = http.Host.decode('utf-8', errors='ignore') if http.Host else "localhost"
                            method = http.Method.decode('utf-8', errors='ignore') if http.Method else "GET"
                            
                            full_url = f"http://{host}{path}"
                            
                            # Сохраняем запрос для сопоставления с ответом
                            req_key = f"{packet[IP].src}:{src_port}-{packet[TCP].seq}"
                            self.request_cache[req_key] = {
                                'url': full_url,
                                'timestamp': time.time(),
                                'method': method,
                                'src_ip': packet[IP].src,
                                'dst_ip': packet[IP].dst
                            }
                            
                            # Извлекаем признаки и детектируем
                            features, feature_info = self.extract_features_from_packet(
                                packet, full_url, response_time=100
                            )
                            
                            detection = self.detect_attack(features, feature_info)
                            
                            if detection['is_attack']:
                                self.stats['attacks_detected'] += 1
                                self.display_attack_alert(
                                    detection,
                                    packet[IP].src, packet[IP].dst,
                                    src_port, dst_port,
                                    method
                                )
                                self.update_statistics_display()
                            else:
                                self.stats['normal_packets'] += 1
                                # self.display_normal_traffic(
                                #     packet[IP].src, packet[IP].dst,
                                #     src_port, dst_port, full_url
                                # )
                        
                        # HTTP ответ
                        elif packet.haslayer(HTTPResponse):
                            resp_key = f"{packet[IP].dst}:{dst_port}-{packet[TCP].ack - 1}"
                            
                            if resp_key in self.request_cache:
                                request = self.request_cache[resp_key]
                                
                                # Вычисляем время ответа
                                response_time = int((time.time() - request['timestamp']) * 1000)
                                
                                # Получаем код статуса
                                status_code = 200
                                if hasattr(packet[HTTPResponse], 'Status_Code'):
                                    status_code = int(packet[HTTPResponse].Status_Code)
                                
                                # Повторная проверка с фактическим временем ответа
                                features, feature_info = self.extract_features_from_packet(
                                    packet, request['url'], response_time, status_code
                                )
                                
                                detection = self.detect_attack(features, feature_info)
                                
                                if detection['is_attack']:
                                    print(f"{self.colors['RED']}   ⚡ Подтверждено: статус {status_code}, время {response_time}мс{self.colors['RESET']}")
                                
                                # Удаляем из кэша
                                del self.request_cache[resp_key]
        
        except Exception as e:
            # Игнорируем ошибки обработки пакетов
            pass
    
    def start_capture(self):
        """Запуск захвата трафика"""
        print(f"{self.colors['GREEN']}🎯 Начинаю захват трафика на интерфейсе {self.interface}...{self.colors['RESET']}")
        
        try:
            # Фильтр для honeypot трафика
            bpf_filter = f"tcp port {self.target_port}"
            
            # Запуск захвата
            sniff(
                iface=self.interface,
                prn=self.process_packet,
                store=False,
                filter=bpf_filter,
                timeout=0  # Бесконечный захват
            )
            
        except KeyboardInterrupt:
            print(f"\n{self.colors['YELLOW']}🛑 Захват остановлен пользователем{self.colors['RESET']}")
            self.show_final_stats()
        except Exception as e:
            print(f"{self.colors['RED']}❌ Ошибка захвата: {e}{self.colors['RESET']}")
            self.show_final_stats()
    
    def show_final_stats(self):
        """Показать финальную статистику"""
        print(f"\n{self.colors['CYAN']}{'='*60}{self.colors['RESET']}")
        print(f"{self.colors['BOLD']}📊 ФИНАЛЬНАЯ СТАТИСТИКА{self.colors['RESET']}")
        print(f"{self.colors['CYAN']}{'='*60}{self.colors['RESET']}")
        
        total_time = time.time() - self.stats['start_time']
        
        print(f"{self.colors['BLUE']}⏱️  Общее время работы:{self.colors['RESET']} {int(total_time)} сек")
        print(f"{self.colors['BLUE']}📦 Обработано пакетов:{self.colors['RESET']} {self.stats['total_packets']}")
        print(f"{self.colors['GREEN']}✅ Нормальный трафик:{self.colors['RESET']} {self.stats['normal_packets']}")
        print(f"{self.colors['RED']}🚨 Обнаружено атак:{self.colors['RESET']} {self.stats['attacks_detected']}")
        
        if self.stats['attack_types']:
            print(f"\n{self.colors['YELLOW']}🎯 РАСПРЕДЕЛЕНИЕ АТАК:{self.colors['RESET']}")
            for attack_type, count in self.stats['attack_types'].items():
                percentage = (count / max(self.stats['attacks_detected'], 1)) * 100
                print(f"   • {attack_type}: {count} ({percentage:.1f}%)")
        
        print(f"{self.colors['CYAN']}{'='*60}{self.colors['RESET']}")

def main():
    """Точка входа"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Real-time honeypot attack monitor')
    parser.add_argument('--interface', '-i', default='lo', 
                       help='Network interface (default: lo)')
    parser.add_argument('--port', '-p', type=int, default=3000,
                       help='Honeypot port (default: 3000)')
    parser.add_argument('--model', '-m', default='ml_models/attack_detector_model.pkl',
                       help='Path to ML model (default: ml_models/attack_detector_model.pkl)')
    
    args = parser.parse_args()
    
    # Проверка root прав
    if os.geteuid() != 0:
        print("❌ Этот скрипт требует root-прав для захвата трафика!")
        print("   Запустите: sudo python scripts/core/realtime_monitor.py")
        sys.exit(1)
    
    # Создание и запуск монитора
    monitor = RealTimeAttackMonitor(
        interface=args.interface,
        target_port=args.port,
        model_path=args.model
    )
    
    monitor.start_capture()

if __name__ == "__main__":
    main()
