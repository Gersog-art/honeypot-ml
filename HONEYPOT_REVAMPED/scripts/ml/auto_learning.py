#!/usr/bin/env python3
"""
АВТООБУЧЕНИЕ ДЛЯ HONEYPOT-ML
Интеграция с существующей структурой
"""

import json
import os
import pickle
import numpy as np
from datetime import datetime
from pathlib import Path
import joblib

class AutoLearner:
    def __init__(self, model_path="ml_models/attack_detector_model.pkl"):
        self.model_path = model_path
        self.learned_file = "ml_models/learned_attacks.json"
        self.stats_file = "ml_models/learning_stats.json"

        # Загружаем или создаем базу знаний
        self.learned_attacks = self.load_learned_data()
        self.model = self.load_model()

        # Счетчики
        self.new_learned = 0
        self.total_detections = 0

    def load_model(self):
        """Загружаем модель или создаем заглушку"""
        try:
            return joblib.load(self.model_path)
        except:
            print("⚠️  Модель не найдена, создаю заглушку")
            return self.create_stub_model()

    def create_stub_model(self):
        """Создаем простую модель для начала"""
        class StubModel:
            def predict(self, X):
                return [0] * len(X) if hasattr(X, '__len__') else [0]
            def predict_proba(self, X):
                return [[0.9, 0.1]] * len(X) if hasattr(X, '__len__') else [[0.9, 0.1]]

        return StubModel()

    def load_learned_data(self):
        """Загружаем выученные атаки"""
        try:
            with open(self.learned_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            # Стартовый набор паттернов
            return {
                "sql_injection": {
                    "patterns": ["'", "union", "select", "1=1", "--", "/*", "*/", "or ", "and "],
                    "examples": [],
                    "count": 0
                },
                "xss": {
                    "patterns": ["<script>", "</script>", "javascript:", "alert(", "onload="],
                    "examples": [],
                    "count": 0
                },
                "path_traversal": {
                    "patterns": ["../", "..\\", "etc/passwd", "win.ini", "/etc/"],
                    "examples": [],
                    "count": 0
                },
                "command_injection": {
                    "patterns": [";", "|", "&", "$(", "`", "system(", "exec("],
                    "examples": [],
                    "count": 0
                }
            }

    def save_learned_data(self):
        """Сохраняем выученные атаки"""
        with open(self.learned_file, 'w') as f:
            json.dump(self.learned_attacks, f, indent=2)

    def extract_patterns(self, attack_text, attack_type):
        """Извлекаем паттерны из атаки"""
        text = attack_text.lower()
        patterns = []

        # Разные методы извлечения
        words = [w for w in text.split() if 3 < len(w) < 50]
        patterns.extend(words[:5])

        # Спецсимволы
        special = set()
        for char in ["'", '"', "<", ">", ";", "|", "&", "`", "$", "{", "}", "[", "]", "(", ")"]:
            if char in text:
                special.add(char)
        patterns.extend(list(special))

        # Строковые константы
        if "'" in text:
            parts = text.split("'")
            for part in parts[1:-1]:  # Между кавычками
                if len(part) > 5:
                    patterns.append(part[:30])

        # Уникальные и ограничение длины
        unique_patterns = []
        for p in patterns:
            if len(p) < 50 and p not in unique_patterns:
                unique_patterns.append(p)

        return unique_patterns[:10]  # Не больше 10 паттернов

    def detect_attack_type(self, text):
        """Определяем тип атаки (можно улучшить)"""
        text_lower = text.lower()

        # Проверяем по существующим паттернам
        for atype, data in self.learned_attacks.items():
            for pattern in data["patterns"]:
                if pattern in text_lower:
                    return atype

        # Эвристики для новых атак
        if any(x in text_lower for x in ["'", "union", "select", "--"]):
            return "sql_injection"
        elif any(x in text_lower for x in ["<script>", "javascript:", "alert("]):
            return "xss"
        elif any(x in text_lower for x in ["../", "..\\", "etc/passwd"]):
            return "path_traversal"
        elif any(x in text_lower for x in [";", "|", "&", "$(", "`"]):
            return "command_injection"

        return "unknown"

    def learn_from_attack(self, attack_text, attack_type=None):
        """Учимся на новой атаке"""
        if attack_type is None:
            attack_type = self.detect_attack_type(attack_text)

        # Создаем новую категорию если нужно
        if attack_type not in self.learned_attacks:
            self.learned_attacks[attack_type] = {
                "patterns": [],
                "examples": [],
                "count": 0
            }

        # Извлекаем паттерны
        new_patterns = self.extract_patterns(attack_text, attack_type)

        # Добавляем новые паттерны
        added = 0
        for pattern in new_patterns:
            if pattern not in self.learned_attacks[attack_type]["patterns"]:
                self.learned_attacks[attack_type]["patterns"].append(pattern)
                added += 1

        # Сохраняем пример (первые 500 символов)
        example = attack_text[:500]
        if example not in self.learned_attacks[attack_type]["examples"]:
            self.learned_attacks[attack_type]["examples"].append(example)

        # Обновляем счетчик
        self.learned_attacks[attack_type]["count"] += 1
        self.new_learned += 1
        self.total_detections += 1

        # Сохраняем
        self.save_learned_data()
        self.save_stats()

        if added > 0:
            print(f"🧠 Выучено {added} новых паттернов для {attack_type}")

        return attack_type, added

    def save_stats(self):
        """Сохраняем статистику обучения"""
        stats = {
            "total_attacks_learned": self.total_detections,
            "new_patterns_learned": self.new_learned,
            "attack_types": len(self.learned_attacks),
            "last_updated": datetime.now().isoformat(),
            "breakdown": {atype: data["count"] for atype, data in self.learned_attacks.items()}
        }

        with open(self.stats_file, 'w') as f:
            json.dump(stats, f, indent=2)

    def get_stats(self):
        """Получаем статистику"""
        total_patterns = sum(len(data["patterns"]) for data in self.learned_attacks.values())
        total_examples = sum(len(data["examples"]) for data in self.learned_attacks.values())

        return {
            "attack_types": len(self.learned_attacks),
            "total_patterns": total_patterns,
            "total_examples": total_examples,
            "new_learned": self.new_learned,
            "total_detections": self.total_detections
        }

    def print_stats(self):
        """Печатаем статистику"""
        stats = self.get_stats()

        print("\n" + "="*50)
        print("📊 СТАТИСТИКА АВТООБУЧЕНИЯ")
        print("="*50)

        for atype, data in self.learned_attacks.items():
            print(f"\n{atype.upper():20}")
            print(f"  Паттернов: {len(data['patterns']):4}")
            print(f"  Примеров:  {len(data['examples']):4}")
            print(f"  Всего:     {data['count']:4}")

        print(f"\n📈 ИТОГО:")
        print(f"  Типов атак:     {stats['attack_types']}")
        print(f"  Всего паттернов: {stats['total_patterns']}")
        print(f"  Новых выучено:   {stats['new_learned']}")
        print("="*50)

def quick_learn():
    """Быстрое обучение через терминал"""
    import sys

    if len(sys.argv) < 2:
        print("""
        Использование:
          python3 auto_learning.py "пример атаки" [тип]

        Примеры:
          python3 auto_learning.py "SELECT * FROM users WHERE 1=1"
          python3 auto_learning.py "<script>alert(1)</script>" xss
          python3 auto_learning.py --stats
          python3 auto_learning.py --list
        """)
        return

    learner = AutoLearner()

    if sys.argv[1] == "--stats":
        learner.print_stats()
    elif sys.argv[1] == "--list":
        for atype, data in learner.learned_attacks.items():
            print(f"\n{atype}:")
            for pattern in data["patterns"][:5]:
                print(f"  - {pattern}")
    else:
        attack_text = sys.argv[1]
        attack_type = sys.argv[2] if len(sys.argv) > 2 else None

        atype, added = learner.learn_from_attack(attack_text, attack_type)
        print(f"✅ Атака типа '{atype}' выучена!")
        print(f"📊 Добавлено {added} новых паттернов")

if __name__ == "__main__":
    quick_learn()
