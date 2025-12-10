#!/bin/bash
# ФИНАЛЬНЫЙ ТЕСТ - ВСЁ В ОДНОМ ОКНЕ

echo "🎯 ФИНАЛЬНЫЙ ТЕСТ СИСТЕМЫ ОБНАРУЖЕНИЯ АТАК"
echo "========================================="

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# 1. Очистка
echo -e "${CYAN}[1] Очистка...${NC}"
docker stop honeypot-juice 2>/dev/null || true
docker rm honeypot-juice 2>/dev/null || true
pkill -f "python.*proxy" 2>/dev/null || true

# 2. Запуск honeypot
echo -e "${CYAN}[2] Запуск honeypot...${NC}"
docker run -d -p 3000:3000 --name honeypot-juice bkimminich/juice-shop
sleep 5

# Проверка
if ! curl -s http://localhost:3000 > /dev/null; then
    echo -e "${RED}❌ Honeypot не запустился${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Honeypot запущен${NC}"

# 3. Запуск простого монитора
echo -e "${CYAN}[3] Запуск монитора...${NC}"
echo ""
echo -e "${YELLOW}=================================================${NC}"
echo -e "${GREEN}        СИСТЕМА МОНИТОРИНГА ЗАПУЩЕНА        ${NC}"
echo -e "${YELLOW}=================================================${NC}"
echo ""
echo -e "${BLUE}Отправляю тестовые запросы через 3 секунды...${NC}"
echo ""

# Даем время увидеть сообщение
sleep 3

# 4. Отправка тестовых запросов
echo -e "${CYAN}[4] Отправка тестовых запросов...${NC}"
echo ""

# Запускаем прокси в фоне
python3 scripts/core/minimal_proxy.py &
PROXY_PID=$!
sleep 2

# Тестовые запросы
echo -e "${YELLOW}--- ТЕСТ 1: Нормальный запрос ---${NC}"
curl -s "http://localhost:3001/" > /dev/null
sleep 1

echo -e "${YELLOW}--- ТЕСТ 2: SQL Injection ---${NC}"
curl -G -s "http://localhost:3001/rest/products/search" --data-urlencode "q=' OR '1'='1" > /dev/null
sleep 1

echo -e "${YELLOW}--- ТЕСТ 3: XSS ---${NC}"
curl -G -s "http://localhost:3001/rest/products/search" --data-urlencode "q=<script>alert('XSS')</script>" > /dev/null
sleep 1

echo -e "${YELLOW}--- ТЕСТ 4: Path Traversal ---${NC}"
curl -s "http://localhost:3001/assets/../../../etc/passwd" > /dev/null
sleep 1

echo -e "${YELLOW}--- ТЕСТ 5: Command Injection ---${NC}"
curl -G -s "http://localhost:3001/rest/products/search" --data-urlencode "q='; ls -la /" > /dev/null
sleep 1

echo -e "${YELLOW}--- ТЕСТ 6: Еще SQL Injection ---${NC}"
curl -G -s "http://localhost:3001/rest/products/search" --data-urlencode "q=' UNION SELECT * FROM users--" > /dev/null
sleep 1

echo -e "\n${GREEN}✅ Все тестовые запросы отправлены!${NC}"
echo ""
echo -e "${CYAN}=================================================${NC}"
echo -e "${GREEN}  ПРОВЕРЬТЕ ВЫШЕ ОБНАРУЖЕНИЯ АТАК!  ${NC}"
echo -e "${CYAN}=================================================${NC}"
echo ""
echo -e "${BLUE}Если вы видите сообщения '🚨 ОБНАРУЖЕНА АТАКА!' - система работает!${NC}"
echo ""
echo -e "${YELLOW}Для дополнительного тестирования откройте новый терминал:${NC}"
echo -e "${BLUE}  curl -G \"http://localhost:3001/rest/products/search\" --data-urlencode \"q=' OR '1'='1\"${NC}"
echo ""
echo -e "${RED}Нажмите Ctrl+C для остановки...${NC}"

# Ждем
wait $PROXY_PID

# Очистка
echo -e "\n${CYAN}[5] Очистка...${NC}"
docker stop honeypot-juice
docker rm honeypot-juice
pkill -f "python.*proxy" 2>/dev/null || true

echo -e "${GREEN}✅ Тест завершен!${NC}"
