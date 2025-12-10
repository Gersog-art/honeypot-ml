#!/bin/bash
# ИСПРАВЛЕННЫЙ ЗАПУСК HONEYPOT СИСТЕМЫ

echo "🚀 ЗАПУСК HONEYPOT СИСТЕМЫ (ИСПРАВЛЕННЫЙ)"
echo "========================================"

# Проверка прав
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Требуются root права!"
    echo "   Запустите: sudo ./run_honeypot.sh"
    exit 1
fi

# Очистка старых процессов
echo "🧹 Очистка старых процессов..."
docker stop honeypot-juice 2>/dev/null || true
docker rm honeypot-juice 2>/dev/null || true
sudo fuser -k 3000/tcp 2>/dev/null || true
pkill -f "python.*monitor" 2>/dev/null || true

# Проверка Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен"
    exit 1
fi

# Проверка tcpdump
if ! command -v tcpdump &> /dev/null; then
    echo "❌ tcpdump не установлен"
    exit 1
fi

# Запуск honeypot с другим именем
echo "🎯 Запуск OWASP Juice Shop..."
docker run -d -p 3000:3000 --name juice-shop-container bkimminich/juice-shop
sleep 8  # Даем больше времени на запуск

# Проверка honeypot
echo "🔍 Проверка honeypot..."
if curl -s http://localhost:3000 > /dev/null; then
    echo "✅ Honeypot запущен: http://localhost:3000"
else
    echo "❌ Honeypot не запустился! Проверяем логи..."
    docker logs juice-shop-container | tail -20
    echo "🔄 Пробуем другой подход..."
    docker stop juice-shop-container 2>/dev/null
    docker rm juice-shop-container 2>/dev/null
    docker run -d -p 3000:3000 bkimminich/juice-shop
    sleep 5
    if curl -s http://localhost:3000 > /dev/null; then
        echo "✅ Honeypot запущен (без имени контейнера)"
    else
        echo "❌ Не удалось запустить honeypot"
        exit 1
    fi
fi

# Создание простой модели (если нет)
echo "🤖 Проверка ML модели..."
if [ ! -f "ml_models/attack_detector_model.pkl" ]; then
    echo "📦 Создание простой ML модели..."
    python3 scripts/ml/simple_train.py
else
    echo "✅ ML модель уже существует"
fi

# Запуск монитора
echo ""
echo "=========================================="
echo "🛡️  СИСТЕМА ГОТОВА К РАБОТЕ!"
echo "=========================================="
echo "✅ Honeypot: http://localhost:3000"
echo "✅ ML модель: загружена"
echo ""
echo "🎯 ДЛЯ ОБНАРУЖЕНИЯ АТАК ЗАПУСТИТЕ:"
echo "   sudo python3 scripts/core/working_monitor.py"
echo ""
echo "🔥 ТЕСТОВЫЕ АТАКИ (в другом терминале):"
echo "   curl \"http://localhost:3000/rest/products/search?q=' OR '1'='1\""
echo "   curl \"http://localhost:3000/#/search?q=<script>alert('XSS')</script>\""
echo "   curl \"http://localhost:3000/assets/../../../etc/passwd\""
echo ""
echo "🌐 ИЛИ ОТКРОЙТЕ БРАУЗЕР: http://localhost:3000"
echo "=========================================="

# Запуск тестовых атак в фоне
echo ""
echo "🧪 Запуск автоматических тестовых атак..."
cat > /tmp/test_attacks.sh << 'TEST_EOF'
#!/bin/bash
echo "=== ТЕСТОВЫЕ АТАКИ ==="
sleep 2
echo "1. SQL Injection..."
curl -s "http://localhost:3000/rest/products/search?q=' OR '1'='1"
echo ""
sleep 1
echo "2. XSS..."
curl -s "http://localhost:3000/#/search?q=<script>alert('XSS')</script>"
echo ""
sleep 1
echo "3. Path Traversal..."
curl -s "http://localhost:3000/assets/../../../etc/passwd"
echo ""
sleep 1
echo "4. Command Injection..."
curl -s "http://localhost:3000/rest/products/search?q='; ls -la /"
echo ""
sleep 1
echo "5. Нормальные запросы..."
curl -s "http://localhost:3000/"
curl -s "http://localhost:3000/#/login"
echo ""
echo "✅ Тестовые атаки отправлены!"
TEST_EOF

chmod +x /tmp/test_attacks.sh
/tmp/test_attacks.sh &

# Ждем немного
sleep 2

# Запуск монитора
echo ""
echo "📡 ЗАПУСК МОНИТОРА..."
echo "Нажмите Ctrl+C для остановки"
echo ""

python3 scripts/core/working_monitor.py

# Очистка
echo "🧹 Очистка..."
pkill -f "test_attacks.sh" 2>/dev/null || true
docker stop juice-shop-container 2>/dev/null || true
docker rm juice-shop-container 2>/dev/null || true
rm -f /tmp/test_attacks.sh 2>/dev/null || true

echo "✅ Система остановлена!"
