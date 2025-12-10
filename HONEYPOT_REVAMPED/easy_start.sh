#!/bin/bash
# ПРОСТОЙ ЗАПУСК ВСЕЙ СИСТЕМЫ

echo "🚀 ЗАПУСК ПРОСТОЙ СИСТЕМЫ ОБНАРУЖЕНИЯ АТАК"
echo "========================================="

# Очистка
echo "🧹 Очистка старых процессов..."
docker stop honeypot-juice 2>/dev/null || true
docker rm honeypot-juice 2>/dev/null || true
sudo fuser -k 3000/tcp 2>/dev/null || true
sudo fuser -k 3001/tcp 2>/dev/null || true

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

echo ""
echo "=========================================="
echo "🛡️  СИСТЕМА ГОТОВА К РАБОТЕ!"
echo "=========================================="
echo ""
echo "🎯 ШАГ 1: ЗАПУСТИТЕ ПРОКСИ-МОНИТОР (в этом окне):"
echo "   python3 scripts/core/simple_proxy.py"
echo ""
echo "🎯 ШАГ 2: ОТКРОЙТЕ НОВЫЙ ТЕРМИНАЛ И ОТПРАВЬТЕ АТАКИ:"
echo "   curl \"http://localhost:3001/rest/products/search?q=' OR '1'='1\""
echo "   curl \"http://localhost:3001/#/search?q=<script>alert('XSS')</script>\""
echo ""
echo "🎯 ШАГ 3: СМОТРИТЕ ОБНАРУЖЕНИЯ В ПЕРВОМ ОКНЕ!"
echo ""
echo "💡 ИЛИ ИСПОЛЬЗУЙТЕ ВЕБ-МОНИТОР ДЛЯ ДЕМО:"
echo "   python3 scripts/core/web_monitor.py"
echo "   (выберите режим 1 - тестовая симуляция)"
echo "=========================================="
