#!/bin/bash
# Запуск honeypot с автообучением

echo "🚀 ЗАПУСК HONEYPOT-ML С АВТООБУЧЕНИЕМ"
echo "===================================="

# Проверяем зависимости
if ! command -v tcpdump &> /dev/null; then
    echo "❌ tcpdump не найден"
    echo "Установите: sudo apt install tcpdump"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo "❌ python3 не найден"
    exit 1
fi

# Создаем директории
mkdir -p ml_models logs

# Показываем меню
PS3='Выберите действие: '
options=("Запустить монитор с обучением" "Запустить монитор без обучения" "Терминал обучения" "Показать статистику" "Очистить данные" "Выход")
select opt in "${options[@]}"
do
    case $opt in
        "Запустить монитор с обучением")
            echo "🎯 Запуск монитора с автообучением..."
            sudo python3 scripts/core/working_monitor.py --port 3000
            ;;
        "Запустить монитор без обучения")
            echo "🎯 Запуск монитора без автообучения..."
            sudo python3 scripts/core/working_monitor.py --port 3000 --no-learn
            ;;
        "Терминал обучения")
            echo "🧠 Запуск терминала обучения..."
            python3 scripts/utils/learn_terminal.py
            ;;
        "Показать статистику")
            echo "📊 Статистика обучения:"
            if [ -f "ml_models/attack_patterns.json" ]; then
                python3 -c "
import json
with open('ml_models/attack_patterns.json') as f:
    data = json.load(f)
total = sum(len(v) for v in data.values())
print(f'Типов атак: {len(data)}')
print(f'Всего паттернов: {total}')
for k, v in data.items():
    print(f'  {k}: {len(v)}')
"
            else
                echo "❌ Файл паттернов не найден"
            fi
            ;;
        "Очистить данные")
            read -p "Точно очистить все данные обучения? (y/N): " confirm
            if [[ $confirm == [yY] ]]; then
                rm -f ml_models/attack_patterns.json ml_models/learning_history.json
                echo "✅ Данные обучения очищены"
            else
                echo "❌ Отменено"
            fi
            ;;
        "Выход")
            echo "👋 Выход"
            break
            ;;
        *) echo "❌ Неверный выбор $REPLY";;
    esac
done
