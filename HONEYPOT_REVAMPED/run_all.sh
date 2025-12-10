#!/bin/bash
# =============================================================================
# HONEYPOT REVAMPED - АВТОМАТИЧЕСКИЙ ЗАПУСК ВСЕЙ СИСТЕМЫ
# =============================================================================

set -e  # Выход при ошибке

echo "🚀 ЗАПУСК HONEYPOT-ML СИСТЕМЫ"
echo "============================="

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функции
print_status() {
    echo -e "${BLUE}[*]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[+]${NC} $1"
}

print_error() {
    echo -e "${RED}[!]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Проверка root
if [[ $EUID -ne 0 ]]; then
   print_error "Скрипт требует root-прав для захвата трафика!"
   print_warning "Запустите: sudo $0"
   exit 1
fi

# Остановка предыдущих процессов
print_status "Остановка предыдущих процессов..."
docker stop honeypot-juice 2>/dev/null || true
docker rm honeypot-juice 2>/dev/null || true
pkill -f "python.*monitor" 2>/dev/null || true
pkill -f "python.*train" 2>/dev/null || true

# Установка зависимостей
print_status "Проверка зависимостей..."
if ! command -v docker &> /dev/null; then
    print_error "Docker не установлен! Установите Docker и запустите скрипт снова."
    exit 1
fi

# Проверка Python библиотек
print_status "Проверка Python библиотек..."
pip install -r requirements.txt 2>/dev/null || {
    print_warning "Создаю requirements.txt..."
    cat > requirements.txt << 'REQ_EOF'
scapy==2.5.0
scapy-http==1.8.2
scikit-learn==1.3.0
pandas==2.1.1
numpy==1.24.3
requests==2.31.0
joblib==1.3.2
colorama==0.4.6
tqdm==4.66.1
matplotlib==3.8.0
REQ_EOF
    pip install -r requirements.txt
}

# Проверка модели
print_status "Проверка ML модели..."
if [ ! -f "ml_models/attack_detector_model.pkl" ]; then
    print_warning "Модель не найдена. Создаю новую..."
    python scripts/ml/train_model.py
fi

# Запуск honeypot
print_status "Запуск OWASP Juice Shop..."
docker run -d -p 3000:3000 --name honeypot-juice bkimminich/juice-shop
sleep 5

# Проверка honeypot
if curl -s http://localhost:3000 > /dev/null; then
    print_success "Honeypot запущен: http://localhost:3000"
else
    print_error "Honeypot не запустился!"
    docker logs honeypot-juice
    exit 1
fi

# Запуск монитора
print_status "Запуск системы мониторинга..."
python scripts/core/realtime_monitor.py --interface lo --port 3000 &
MONITOR_PID=$!
sleep 3

# Проверка монитора
if ps -p $MONITOR_PID > /dev/null; then
    print_success "Монитор запущен (PID: $MONITOR_PID)"
else
    print_error "Монитор не запустился!"
    exit 1
fi

# Создание тестового трафика
print_status "Создание тестового трафика..."
python scripts/utils/generate_test_traffic.py --normal 5 --attacks 10 --delay 1

# Запуск автоматических тестов
print_status "Запуск автоматических тестов..."
python scripts/utils/test_attacks.py --all

# Вывод информации
echo ""
echo "================================================================================"
echo "✅ СИСТЕМА УСПЕШНО ЗАПУЩЕНА!"
echo "================================================================================"
echo ""
echo "📊 СТАТУС КОМПОНЕНТОВ:"
echo "   • Honeypot:      ${GREEN}работает${NC} на http://localhost:3000"
echo "   • Монитор:       ${GREEN}работает${NC} (PID: $MONITOR_PID)"
echo "   • ML модель:     ${GREEN}загружена${NC}"
echo ""
echo "🎯 ТЕСТИРОВАНИЕ:"
echo "   1. Откройте браузер: http://localhost:3000"
echo "   2. Или отправьте атаку:"
echo "      curl \"http://localhost:3000/rest/products/search?q=' OR '1'='1\""
echo "   3. Смотрите обнаружения в этом окне"
echo ""
echo "📈 СБОР СТАТИСТИКИ:"
echo "   python scripts/utils/show_stats.py"
echo ""
echo "🛑 ДЛЯ ОСТАНОВКИ:"
echo "   1. Нажмите Ctrl+C в этом окне"
echo "   2. Или запустите: ./stop_all.sh"
echo ""
echo "================================================================================"

# Сохранение логов
mkdir -p logs
echo "$(date): System started" >> logs/session.log

# Ожидание Ctrl+C
wait $MONITOR_PID

# Очистка при завершении
print_status "Остановка системы..."
docker stop honeypot-juice
docker rm honeypot-juice
pkill -f "python.*monitor" 2>/dev/null || true

print_success "Система остановлена!"
