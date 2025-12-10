#!/bin/bash
# ПРАВИЛЬНЫЙ ЗАПУСК СИСТЕМЫ

echo "🎯 ПРАВИЛЬНЫЙ ЗАПУСК HONEYPOT СИСТЕМЫ"
echo "===================================="

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Очистка
echo -e "${BLUE}[1/5] Очистка старых процессов...${NC}"
docker stop honeypot-juice 2>/dev/null || true
docker rm honeypot-juice 2>/dev/null || true
sudo fuser -k 3000/tcp 2>/dev/null || true
sudo fuser -k 3001/tcp 2>/dev/null || true
pkill -f "python.*proxy" 2>/dev/null || true

# Запуск honeypot
echo -e "${BLUE}[2/5] Запуск OWASP Juice Shop...${NC}"
docker run -d -p 3000:3000 --name honeypot-juice bkimminich/juice-shop
sleep 8

# Проверка honeypot
echo -e "${BLUE}[3/5] Проверка honeypot...${NC}"
if curl -s http://localhost:3000 > /dev/null; then
    echo -e "${GREEN}✅ Honeypot запущен: http://localhost:3000${NC}"
else
    echo -e "${RED}❌ Honeypot не запустился!${NC}"
    docker logs honeypot-juice
    exit 1
fi

# Запуск прокси-монитора
echo -e "${BLUE}[4/5] Запуск прокси-монитора...${NC}"
python3 scripts/core/simple_proxy.py --listen-port 3001 --target-port 3000 &
PROXY_PID=$!
sleep 3

# Проверка прокси
if ps -p $PROXY_PID > /dev/null; then
    echo -e "${GREEN}✅ Прокси-монитор запущен (PID: $PROXY_PID)${NC}"
else
    echo -e "${RED}❌ Прокси-монитор не запустился!${NC}"
    exit 1
fi

# Тестовые запросы
echo -e "${BLUE}[5/5] Отправка тестовых запросов...${NC}"
sleep 2

echo -e "\n${YELLOW}📡 ТЕСТОВЫЕ ЗАПРОСЫ:${NC}"

# 1. Нормальный запрос (должен показать нормальный)
echo -e "\n${BLUE}[1] Нормальный запрос:${NC}"
curl -s "http://localhost:3001/" > /dev/null
echo "   ✅ Отправлен: GET /"

# 2. SQL Injection (должен обнаружить атаку)
echo -e "\n${BLUE}[2] SQL Injection:${NC}"
curl -G -s "http://localhost:3001/rest/products/search" --data-urlencode "q=' OR '1'='1" > /dev/null
echo "   ✅ Отправлен: SQL Injection"

# 3. XSS (должен обнаружить атаку)
echo -e "\n${BLUE}[3] XSS:${NC}"
curl -G -s "http://localhost:3001/rest/products/search" --data-urlencode "q=<script>alert('XSS')</script>" > /dev/null
echo "   ✅ Отправлен: XSS"

# 4. Path Traversal (должен обнаружить атаку)
echo -e "\n${BLUE}[4] Path Traversal:${NC}"
curl -s "http://localhost:3001/assets/../../../etc/passwd" > /dev/null
echo "   ✅ Отправлен: Path Traversal"

# 5. Command Injection (должен обнаружить атаку)
echo -e "\n${BLUE}[5] Command Injection:${NC}"
curl -G -s "http://localhost:3001/rest/products/search" --data-urlencode "q='; ls -la /" > /dev/null
echo "   ✅ Отправлен: Command Injection"

echo -e "\n${GREEN}✅ Все тестовые запросы отправлены!${NC}"
echo -e "\n${YELLOW}=================================================${NC}"
echo -e "${GREEN}🎯 СИСТЕМА РАБОТАЕТ!${NC}"
echo -e "${YELLOW}=================================================${NC}"
echo -e "\n📊 Проверьте вывод прокси-монитора выше."
echo -e "   Вы должны увидеть обнаруженные атаки с пометкой ${RED}🚨${NC}"
echo -e "\n🎯 ДЛЯ ДОПОЛНИТЕЛЬНОГО ТЕСТИРОВАНИЯ:"
echo -e "   Откройте новый терминал и отправьте запросы:"
echo -e "   ${BLUE}curl -G \"http://localhost:3001/rest/products/search\" --data-urlencode \"q=' OR '1'='1\"${NC}"
echo -e "   ${BLUE}curl \"http://localhost:3001/assets/../../../etc/passwd\"${NC}"
echo -e "\n🌐 Или откройте браузер: ${BLUE}http://localhost:3001${NC}"
echo -e "\n${RED}🛑 ДЛЯ ОСТАНОВКИ: нажмите Ctrl+C в этом окне${NC}"
echo -e "${YELLOW}=================================================${NC}"

# Ждем Ctrl+C
wait $PROXY_PID

# Очистка
echo -e "\n${BLUE}🧹 Очистка...${NC}"
docker stop honeypot-juice
docker rm honeypot-juice
pkill -f "python.*proxy" 2>/dev/null || true

echo -e "${GREEN}✅ Система остановлена!${NC}"
