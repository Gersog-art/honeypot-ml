#!/usr/bin/env python3
"""
Улучшенная ML модель для обнаружения атак
Создает модель с 10 признаками и сохраняет в pickle
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import joblib
import json
import os
from datetime import datetime

class AttackModelTrainer:
    def __init__(self):
        self.model = None
        self.feature_names = [
            'packet_size_category_small',
            'packet_size_category_medium',
            'packet_size_category_large',
            'packet_size_category_huge',
            'response_time_ms',
            'has_sql',
            'has_xss',
            'has_traversal',
            'status_code',
            'attack_indicator'
        ]
        
    def generate_training_data(self, n_samples=2000):
        """Генерация реалистичных тренировочных данных"""
        print("🔧 Генерация тренировочных данных...")
        
        data = []
        labels = []
        
        # Нормальный трафик (50%)
        for i in range(n_samples // 2):
            features = self.generate_normal_features()
            data.append(features)
            labels.append(0)  # 0 = нормальный
            
        # Атакующий трафик (50%)
        attack_types = ['sql', 'xss', 'traversal', 'mixed']
        for i in range(n_samples // 2):
            attack_type = np.random.choice(attack_types)
            features = self.generate_attack_features(attack_type)
            data.append(features)
            labels.append(1)  # 1 = атака
            
        return np.array(data), np.array(labels)
    
    def generate_normal_features(self):
        """Генерация признаков для нормального трафика"""
        # Размер пакета (нормальный: 200-2000 байт)
        packet_size = np.random.randint(200, 2000)
        
        # Категории размера
        size_cat_small = 1 if packet_size < 500 else 0
        size_cat_medium = 1 if 500 <= packet_size < 1500 else 0
        size_cat_large = 1 if 1500 <= packet_size < 5000 else 0
        size_cat_huge = 1 if packet_size >= 5000 else 0
        
        # Время ответа (быстрое: 10-500 мс)
        response_time = np.random.randint(10, 500)
        
        # Признаки атак (все 0 для нормального)
        has_sql = 0
        has_xss = 0
        has_traversal = 0
        
        # Код ответа (в основном 200, иногда 404)
        status_code = 200 if np.random.random() > 0.1 else 404
        
        # Индикатор атаки
        attack_indicator = 0
        
        return [
            size_cat_small, size_cat_medium, size_cat_large, size_cat_huge,
            response_time, has_sql, has_xss, has_traversal,
            status_code, attack_indicator
        ]
    
    def generate_attack_features(self, attack_type):
        """Генерация признаков для атакующего трафика"""
        # Размер пакета (атаки часто больше: 500-5000 байт)
        packet_size = np.random.randint(500, 5000)
        
        # Категории размера
        size_cat_small = 1 if packet_size < 500 else 0
        size_cat_medium = 1 if 500 <= packet_size < 1500 else 0
        size_cat_large = 1 if 1500 <= packet_size < 5000 else 0
        size_cat_huge = 1 if packet_size >= 5000 else 0
        
        # Время ответа (атаки могут быть медленнее: 100-3000 мс)
        response_time = np.random.randint(100, 3000)
        
        # Признаки атак в зависимости от типа
        if attack_type == 'sql':
            has_sql = 1
            has_xss = 0
            has_traversal = 0
        elif attack_type == 'xss':
            has_sql = 0
            has_xss = 1
            has_traversal = 0
        elif attack_type == 'traversal':
            has_sql = 0
            has_xss = 0
            has_traversal = 1
        else:  # mixed
            has_sql = np.random.randint(0, 2)
            has_xss = np.random.randint(0, 2)
            has_traversal = np.random.randint(0, 2)
            
            # Гарантируем хотя бы один признак атаки
            if not (has_sql or has_xss or has_traversal):
                has_sql = 1
        
        # Код ответа (атаки могут вызывать ошибки)
        codes = [200, 400, 403, 404, 500]
        weights = [0.6, 0.1, 0.1, 0.1, 0.1]
        status_code = np.random.choice(codes, p=weights)
        
        # Индикатор атаки
        attack_indicator = 1
        
        return [
            size_cat_small, size_cat_medium, size_cat_large, size_cat_huge,
            response_time, has_sql, has_xss, has_traversal,
            status_code, attack_indicator
        ]
    
    def train(self, X, y):
        """Обучение модели"""
        print("🤖 Обучение модели Random Forest...")
        
        # Разделение данных
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Создание и обучение модели
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            class_weight='balanced',
            n_jobs=-1
        )
        
        self.model.fit(X_train, y_train)
        
        # Оценка модели
        y_pred = self.model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        print("\n📊 РЕЗУЛЬТАТЫ ОБУЧЕНИЯ:")
        print(f"   Точность: {accuracy:.2%}")
        print(f"   Всего примеров: {len(X)}")
        print(f"   Нормальных: {sum(y == 0)}")
        print(f"   Атак: {sum(y == 1)}")
        
        # Кросс-валидация
        cv_scores = cross_val_score(self.model, X, y, cv=5)
        print(f"   Кросс-валидация (5-fold): {cv_scores.mean():.2%} (±{cv_scores.std():.2%})")
        
        return accuracy
    
    def save_model(self, filename='ml_models/attack_detector_model.pkl'):
        """Сохранение модели и метаданных"""
        print("💾 Сохранение модели...")
        
        # Создаем папку если нет
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        # Сохраняем модель
        joblib.dump(self.model, filename)
        
        # Сохраняем метаданные
        metadata = {
            'model_name': 'Honeypot Attack Detector v2.0',
            'created_at': datetime.now().isoformat(),
            'accuracy': float(self.accuracy) if hasattr(self, 'accuracy') else 0.95,
            'feature_names': self.feature_names,
            'feature_importances': self.model.feature_importances_.tolist() if self.model else [],
            'n_estimators': 100,
            'detection_threshold': 0.7,
            'classes': ['normal', 'attack'],
            'version': '2.0'
        }
        
        with open('ml_models/model_metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"✅ Модель сохранена: {filename}")
        print(f"📋 Метаданные: ml_models/model_metadata.json")
        
        return metadata
    
    def run(self):
        """Запуск всего процесса обучения"""
        print("=" * 60)
        print("🤖 ОБУЧЕНИЕ ML МОДЕЛИ ДЛЯ ОБНАРУЖЕНИЯ АТАК")
        print("=" * 60)
        
        # Генерация данных
        X, y = self.generate_training_data(n_samples=2000)
        
        # Обучение модели
        self.accuracy = self.train(X, y)
        
        # Сохранение
        metadata = self.save_model()
        
        print("\n🎯 МОДЕЛЬ ГОТОВА К ИСПОЛЬЗОВАНИЮ!")
        print(f"   • Точность: {metadata['accuracy']:.1%}")
        print(f"   • Признаков: {len(metadata['feature_names'])}")
        print(f"   • Порог обнаружения: {metadata['detection_threshold']}")
        print(f"   • Метка: {metadata['created_at']}")
        
        return metadata

def main():
    """Точка входа"""
    trainer = AttackModelTrainer()
    trainer.run()

if __name__ == "__main__":
    main()
