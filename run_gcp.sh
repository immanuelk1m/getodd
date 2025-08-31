#!/bin/bash

# GCP 헤드리스 환경용 실행 스크립트

echo "Starting GetOdd scraper in GCP headless environment..."

# 색상 코드 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Chrome/Chromium 확인
if command -v chromium-browser &> /dev/null; then
    echo -e "${GREEN}✓${NC} Chromium browser found"
elif command -v google-chrome &> /dev/null; then
    echo -e "${GREEN}✓${NC} Google Chrome found"
else
    echo -e "${RED}✗${NC} No Chrome/Chromium browser found!"
    echo "Please install: sudo apt-get install chromium-browser chromium-chromedriver"
    exit 1
fi

# Xvfb 확인
if ! command -v xvfb-run &> /dev/null; then
    echo -e "${YELLOW}!${NC} xvfb-run not found. Installing..."
    sudo apt-get update && sudo apt-get install -y xvfb
fi

# 파라미터 설정
COUNTRY=${1:-sweden}
WORKERS=${2:-5}
HANDICAPS=${3:-"+2.5,+3,+3.5"}

echo -e "\n${GREEN}Configuration:${NC}"
echo "  Country: $COUNTRY"
echo "  Workers: $WORKERS"
echo "  Handicaps: $HANDICAPS"
echo ""

# 가상환경 활성화 (있는 경우)
if [ -f ".venv/bin/activate" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# xvfb-run으로 실행
echo -e "\n${YELLOW}Starting scraper with xvfb-run...${NC}\n"

xvfb-run -a \
    --server-args="-screen 0 1920x1080x24 -ac +extension GLX" \
    python -m getodd_module \
    --input-dir "match_urls_complete/by_league/${COUNTRY}" \
    --output-dir "${COUNTRY}_odds_output" \
    --workers "${WORKERS}" \
    --handicaps "${HANDICAPS}"

# 종료 코드 확인
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✓ Scraping completed successfully!${NC}"
else
    echo -e "\n${RED}✗ Scraping failed with error code $?${NC}"
    exit 1
fi