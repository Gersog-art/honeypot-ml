#!/bin/bash
# АВТОМАТИЧЕСКИЙ ЗАПУСК РАБОЧЕЙ СИСТЕМЫ

echo "🚀 ЗАПУСК РАБОЧЕЙ HONEYPOT СИСТЕМЫ"
echo "=================================="

# Проверка прав
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Требуются root права!"
    echo "   Запустите: sudo ./auto_start.sh"
    exit 1
fi

# Очистка
echo "🧹 Очистка старых процессов..."
docker stop honeypot-juice 2>/dev/null
docker rm honeypot-juice 2>/dev/null
pkill -f "python.*monitor" 2>/dev/null

# Проверка tcpdump
if ! command -v tcpdump &> /dev/null; then
    echo "📦 Установка tcpdump..."
    apt update && apt install -y tcpdump
fi

# Запуск honeypot
echo "🎯 Запуск OWASP Juice Shop..."
docker run -d -p 3000:3000 --name honeypot-juice bkimminich/juice-shop
sleep 5

# Проверка honeypot
echo "🔍 Проверка honeypot..."
if curl -s http://localhost:3000 > /dev/null; then
    echo "✅ Honeypot запущен: http://localhost:3000"
else
    echo "❌ Honeypot не запустился!"
    docker logs honeypot-juice
    exit 1
fi

# Создание простой модели
echo "🤖 Создание простой ML модели..."
python3 scripts/ml/simple_train.py

# Запуск тестовых атак в фоне
echo "🔥 Запуск тестовых атак в фоне..."
cat > test_attacks.sh << 'TEST_EOF'
#!/bin/bash
echo "🧪 ЗАПУСК ТЕСТОВЫХ АТАК..."
sleep 3

# SQL Injection
echo "1. SQL Injection..."
curl -s "http://localhost:3000/rest/products/search?q=' OR '1'='1" > /dev/null
sleep 1

# XSS
echo "2. XSS..."
curl -s "http://localhost:3000/#/search?q=<script>alert('XSS')</script>" > /dev/null
sleep 1

# Path Traversal
echo "3. Path Traversal..."
curl -s "http://localhost:3000/assets/../../../etc/passwd" > /dev/null
sleep 1

# Command Injection
echo "4. Command Injection..."
curl -s "http://localhost:3000/rest/products/search?q='; ls -la /" > /dev/null
sleep 1

# Нормальные запросы
echo "5. Нормальные запросы..."
curl -s "http://localhost:3000/" > /dev/null
curl -s "http://localhost:3000/#/login" > /dev/null
curl -s "http://localhost:3000/#/search?q=apple" > /dev/null

echo "✅ Тестовые атаки отправлены!"
TEST_EOF

chmod +x test_attacks.sh
./test_attacks.sh &
ATTACK_PID=$!

# Запуск монитора
echo "📡 Запуск рабочего монитора..."
echo ""
echo "=========================================="
echo "🛡️  СИСТЕМА ЗАПУЩЕНА!"
echo "=========================================="
echo "✅ Honeypot: http://localhost:3000"
echo "✅ Монитор: захват трафика на порту 3000"
echo ""
echo "🎯 ОТПРАВЬТЕ АТАКИ ДЛЯ ТЕСТИРОВАНИЯ:"
echo "   curl \"http://localhost:3000/rest/products/search?q=' OR '1'='1\""
echo "   curl \"http://localhost:3000/#/search?q=<script>alert('XSS')</script>\""
echo ""
echo "📊 ИЛИ ОТКРОЙТЕ БРАУЗЕР: http://localhost:3000"
echo ""
echo "🛑 ДЛЯ ОСТАНОВКИ: Ctrl+C"
echo "=========================================="
echo ""

# Запуск монитора
python3 scripts/core/working_monitor.py

# Очистка
echo "🧹 Очистка..."
kill $ATTACK_PID 2>/dev/null
docker stop honeypot-juice
docker rm honeypot-juice
rm -f test_attacks.sh

echo "✅ Система остановлена!"
