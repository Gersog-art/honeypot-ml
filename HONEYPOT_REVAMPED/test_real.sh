#!/bin/bash
# ТЕСТ РЕАЛЬНОЙ СИСТЕМЫ ОБНАРУЖЕНИЯ АТАК

echo "🧪 ТЕСТ РЕАЛЬНОГО ОБНАРУЖЕНИЯ АТАК"
echo "================================="

# Проверка Docker
echo "🔍 Проверка honeypot..."
if ! docker ps | grep -q "juice"; then
    echo "❌ Honeypot не запущен. Запускаю..."
    docker run -d -p 3000:3000 bkimminich/juice-shop
    sleep 5
fi

# Проверка доступности
if curl -s http://localhost:3000 > /dev/null; then
    echo "✅ Honeypot работает: http://localhost:3000"
else
    echo "❌ Honeypot не доступен"
    exit 1
fi

# Установка socat если нужно
if ! command -v socat &> /dev/null; then
    echo "📦 Установка socat..."
    sudo apt install socat -y
fi

echo ""
echo "🎯 ЗАПУСТИТЕ МОНИТОР В ОДНОМ ТЕРМИНАЛЕ:"
echo "   sudo python3 scripts/core/real_monitor.py"
echo ""
echo "🔥 А В ДРУГОМ ТЕРМИНАЛЕ ОТПРАВЬТЕ АТАКИ:"
echo ""
echo "   # SQL Injection"
echo "   curl \"http://localhost:3000/rest/products/search?q=' OR '1'='1\""
echo ""
echo "   # XSS"
echo "   curl \"http://localhost:3000/#/search?q=<script>alert('XSS')</script>\""
echo ""
echo "   # Path Traversal"
echo "   curl \"http://localhost:3000/assets/../../../etc/passwd\""
echo ""
echo "   # Command Injection"
echo "   curl \"http://localhost:3000/rest/products/search?q='; ls -la /\""
echo ""
echo "   # Нормальные запросы"
echo "   curl \"http://localhost:3000/\""
echo "   curl \"http://localhost:3000/#/login\""
echo ""
echo "🎯 МОНИТОР БУДЕТ ПОКАЗЫВАТЬ ОБНАРУЖЕНИЯ В РЕАЛЬНОМ ВРЕМЕНИ!"
