#!/bin/bash
# Простой запуск системы для Kali Linux

echo "🚀 ЗАПУСК HONEYPOT СИСТЕМЫ (Kali Linux)"
echo "======================================"

# Проверка Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен"
    sudo apt install docker.io -y
    sudo systemctl start docker
    sudo systemctl enable docker
fi

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не установлен"
    sudo apt install python3 python3-pip -y
fi

# Остановка старого
echo "🛑 Остановка предыдущих процессов..."
docker stop honeypot-juice 2>/dev/null
docker rm honeypot-juice 2>/dev/null

# Запуск honeypot
echo "🎯 Запуск OWASP Juice Shop..."
docker run -d -p 3000:3000 --name honeypot-juice bkimminich/juice-shop
sleep 5

# Проверка honeypot
echo "🔍 Проверка honeypot..."
if curl -s http://localhost:3000 > /dev/null; then
    echo "✅ Honeypot запущен: http://localhost:3000"
else
    echo "❌ Honeypot не запустился"
    docker logs honeypot-juice
    exit 1
fi

# Создание простой модели
echo "🤖 Создание простой ML модели..."
python3 scripts/ml/simple_train.py

# Запуск монитора
echo "📡 Запуск монитора..."
echo ""
echo "=========================================="
echo "🛡️  СИСТЕМА ГОТОВА К РАБОТЕ!"
echo "=========================================="
echo ""
echo "1. Запустите монитор:"
echo "   python3 scripts/core/simple_monitor.py"
echo ""
echo "2. Выберите режим 1 (симуляция) для теста"
echo ""
echo "3. Или отправьте атаки вручную:"
echo "   curl \"http://localhost:3000/rest/products/search?q=' OR '1'='1\""
echo "   curl \"http://localhost:3000/#/search?q=<script>alert('XSS')</script>\""
echo ""
echo "4. Откройте браузер: http://localhost:3000"
echo ""
echo "=========================================="

# Запуск монитора
python3 scripts/core/simple_monitor.py

# Очистка
echo "🧹 Очистка..."
docker stop honeypot-juice
docker rm honeypot-juice
