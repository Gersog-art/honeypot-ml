#!/bin/bash
# ПРОСТОЙ ТЕСТ СИСТЕМЫ

echo "🧪 ТЕСТИРОВАНИЕ HONEYPOT СИСТЕМЫ"
echo "================================"

# Проверка Docker
if ! docker ps | grep -q "juice"; then
    echo "❌ Honeypot не запущен"
    echo "   Запускаю honeypot..."
    docker run -d -p 3000:3000 bkimminich/juice-shop
    sleep 5
fi

# Проверка доступности
echo "🔍 Проверка honeypot..."
if curl -s http://localhost:3000 > /dev/null; then
    echo "✅ Honeypot доступен: http://localhost:3000"
else
    echo "❌ Honeypot недоступен"
    exit 1
fi

echo ""
echo "🎯 ОТПРАВКА ТЕСТОВЫХ АТАК:"
echo ""

# 1. SQL Injection
echo "1. SQL Injection..."
curl -s "http://localhost:3000/rest/products/search?q=' OR '1'='1"
echo "   ✅ Отправлено: SQL Injection"

# 2. XSS
echo ""
echo "2. XSS..."
curl -s "http://localhost:3000/#/search?q=<script>alert('XSS')</script>"
echo "   ✅ Отправлено: XSS"

# 3. Path Traversal
echo ""
echo "3. Path Traversal..."
curl -s "http://localhost:3000/assets/../../../etc/passwd"
echo "   ✅ Отправлено: Path Traversal"

# 4. Command Injection
echo ""
echo "4. Command Injection..."
curl -s "http://localhost:3000/rest/products/search?q='; ls -la /"
echo "   ✅ Отправлено: Command Injection"

# 5. Нормальные запросы
echo ""
echo "5. Нормальные запросы..."
curl -s "http://localhost:3000/"
curl -s "http://localhost:3000/#/login"
echo "   ✅ Отправлено: 2 нормальных запроса"

echo ""
echo "=========================================="
echo "✅ ТЕСТОВЫЕ АТАКИ ОТПРАВЛЕНЫ!"
echo ""
echo "🎯 ЗАПУСТИТЕ МОНИТОР ДЛЯ ПРОВЕРКИ:"
echo "   python3 scripts/core/web_monitor.py"
echo "   (выберите режим 1 - тестовая симуляция)"
echo "=========================================="
