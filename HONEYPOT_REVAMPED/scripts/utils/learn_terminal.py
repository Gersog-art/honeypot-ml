#!/usr/bin/env python3
"""
ТЕРМИНАЛЬНЫЙ ИНТЕРФЕЙС ДЛЯ РУЧНОГО ОБУЧЕНИЯ
"""

import json
import os
import sys

def main():
    """Интерактивное обучение через терминал"""

    print("🤖 ТЕРМИНАЛ ОБУЧЕНИЯ HONEYPOT-ML")
    print("="*50)

    # Загружаем существующие паттерны
    patterns_file = "ml_models/attack_patterns.json"
    if os.path.exists(patterns_file):
        with open(patterns_file, 'r') as f:
            patterns = json.load(f)
        print(f"✅ Загружено {sum(len(v) for v in patterns.values())} паттернов")
    else:
        patterns = {
            "sql": [], "xss": [], "path": [], "cmd": [], "xxe": []
        }
        print("⚠️  Создана новая база паттернов")

    while True:
        print("\n" + "="*50)
        print("1. Добавить пример атаки")
        print("2. Показать все паттерны")
        print("3. Поиск паттерна")
        print("4. Удалить паттерн")
        print("5. Импорт из файла")
        print("6. Экспорт в файл")
        print("7. Выйти")

        choice = input("\nВыберите действие: ").strip()

        if choice == "1":
            print("\nПримеры:")
            print("  SQL: SELECT * FROM users WHERE '1'='1'")
            print("  XSS: <script>alert('XSS')</script>")
            print("  Path: ../../../etc/passwd")
            print("  CMD: ; ls -la")
            print("  XXE: <!DOCTYPE foo [<!ENTITY xxe SYSTEM \"file:///etc/passwd\">]>")

            attack = input("\nВведите пример атаки: ").strip()
            if not attack:
                print("❌ Пустой ввод")
                continue

            print("\nТипы атак:")
            print("  sql - SQL инъекция")
            print("  xss - Межсайтовый скриптинг")
            print("  path - Обход путей")
            print("  cmd - Инъекция команд")
            print("  xxe - XXE атака")

            atype = input("Тип атаки (sql/xss/path/cmd/xxe): ").strip().lower()

            if atype not in patterns:
                print(f"❌ Неизвестный тип. Создаю новый: {atype}")
                patterns[atype] = []

            # Извлекаем ключевые слова
            words = attack.lower().split()
            keywords = [w for w in words if 2 < len(w) < 50]

            added = 0
            for kw in keywords[:10]:  # Берем первые 10 слов
                if kw not in patterns[atype]:
                    patterns[atype].append(kw)
                    added += 1

            print(f"✅ Добавлено {added} новых паттернов для {atype}")

            # Сохраняем
            os.makedirs("ml_models", exist_ok=True)
            with open(patterns_file, 'w') as f:
                json.dump(patterns, f, indent=2)

        elif choice == "2":
            print("\n📚 ВСЕ ПАТТЕРНЫ:")
            total = 0
            for atype, pats in patterns.items():
                if pats:
                    print(f"\n{atype.upper()} ({len(pats)}):")
                    for i, p in enumerate(pats[:20], 1):  # Показываем первые 20
                        print(f"  {i:3}. {p}")
                    if len(pats) > 20:
                        print(f"  ... и еще {len(pats)-20}")
                    total += len(pats)
            print(f"\n📊 Всего: {total} паттернов")

        elif choice == "3":
            search = input("Поиск паттерна: ").strip().lower()
            found = []
            for atype, pats in patterns.items():
                for p in pats:
                    if search in p.lower():
                        found.append((atype, p))

            if found:
                print(f"\n🔍 Найдено {len(found)} совпадений:")
                for atype, p in found[:20]:  # Показываем первые 20
                    print(f"  [{atype}] {p}")
                if len(found) > 20:
                    print(f"  ... и еще {len(found)-20}")
            else:
                print("❌ Совпадений не найдено")

        elif choice == "4":
            atype = input("Тип паттерна для удаления (sql/xss/path/cmd/xxe): ").strip().lower()
            if atype in patterns and patterns[atype]:
                print(f"\nПаттерны {atype}:")
                for i, p in enumerate(patterns[atype], 1):
                    print(f"  {i}. {p}")

                try:
                    num = int(input("Номер для удаления (0 - отмена): "))
                    if 0 < num <= len(patterns[atype]):
                        removed = patterns[atype].pop(num-1)
                        print(f"✅ Удален: {removed}")

                        # Сохраняем
                        with open(patterns_file, 'w') as f:
                            json.dump(patterns, f, indent=2)
                except:
                    print("❌ Неверный номер")
            else:
                print(f"❌ Нет паттернов для типа {atype}")

        elif choice == "5":
            filename = input("Путь к файлу для импорта (JSON или текстовый): ").strip()
            if os.path.exists(filename):
                try:
                    if filename.endswith('.json'):
                        with open(filename, 'r') as f:
                            imported = json.load(f)
                        # Объединяем
                        for atype, pats in imported.items():
                            if atype not in patterns:
                                patterns[atype] = []
                            for p in pats:
                                if p not in patterns[atype]:
                                    patterns[atype].append(p)
                    else:
                        # Текстовый файл
                        with open(filename, 'r') as f:
                            lines = f.readlines()

                        atype = input("Тип для импортируемых паттернов: ").strip().lower()
                        if atype not in patterns:
                            patterns[atype] = []

                        added = 0
                        for line in lines:
                            line = line.strip()
                            if line and line not in patterns[atype]:
                                patterns[atype].append(line)
                                added += 1

                        print(f"✅ Импортировано {added} паттернов")

                    # Сохраняем
                    with open(patterns_file, 'w') as f:
                        json.dump(patterns, f, indent=2)

                except Exception as e:
                    print(f"❌ Ошибка импорта: {e}")
            else:
                print("❌ Файл не найден")

        elif choice == "6":
            filename = input("Имя файла для экспорта (по умолчанию: patterns_export.json): ").strip()
            if not filename:
                filename = "patterns_export.json"

            with open(filename, 'w') as f:
                json.dump(patterns, f, indent=2)
            print(f"✅ Паттерны экспортированы в {filename}")

        elif choice == "7":
            print("👋 Выход")
            break

        else:
            print("❌ Неверный выбор")

if __name__ == "__main__":
    main()
