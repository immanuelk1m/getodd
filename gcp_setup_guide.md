
## 1. 🔧 시스템 업데이트 및 기본 패키지 설치

```bash
# 시스템 업데이트
sudo apt update && sudo apt upgrade -y

# 필수 도구 설치
sudo apt install -y \
    git \
    curl \
    wget \
    build-essential \
    software-properties-common \
    ca-certificates \
    gnupg \
    lsb-release
```

## 2. 🐍 Python 3.10+ 확인 및 설정

```bash
# Python 버전 확인 (GCP 인스턴스에는 기본적으로 Python 3.10이 설치되어 있음)
python3 --version

# pip와 venv 모듈 설치 (필요한 경우)
sudo apt install -y python3-pip python3-venv

# pip 업그레이드
python3 -m pip install --upgrade pip
```

## 3. 🌐 Chromium 브라우저 및 ChromeDriver 설치

```bash
# Chromium과 ChromeDriver 설치
sudo apt install -y \
    chromium-browser \
    chromium-chromedriver

# 헤드리스 환경을 위한 추가 패키지
sudo apt install -y \
    xvfb \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils

# 설치 확인
chromium-browser --version
chromedriver --version
```

## 4. 📦 프로젝트 클론 및 설정

```bash
# 홈 디렉토리로 이동
cd ~

# Git 저장소 클론 (저장소 URL을 실제 URL로 변경)
git clone https://github.com/your-username/getodd.git
# 또는 직접 파일 업로드
# scp -r getodd/ username@gcp-instance-ip:~/

# 프로젝트 디렉토리로 이동
cd getodd

# 가상환경 생성
python3 -m venv .venv

# 가상환경 활성화
source .venv/bin/activate

# pip 업그레이드
pip install --upgrade pip
```

## 5. 📚 Python 패키지 설치

```bash
# requirements.txt가 있는 경우
pip install -r requirements.txt


# 테스트 모드로 실행 (1개 워커)
xvfb-run -a python -m getodd_module \
    --test \
    --workers 1 \
    --handicaps "+2.5"

# 성공하면 실제 데이터로 테스트
xvfb-run -a python -m getodd_module \
    --input-dir match_urls_complete/by_league/switzerland \
    --output-dir test_output \
    --workers 1 \
    --handicaps "+2.5" \
    --batch-size 2
```

## 8. 🚀 실제 실행

```bash
# 가상환경 활성화
cd ~/getodd
source .venv/bin/activate

# Switzerland 데이터 수집 실행
xvfb-run -a python -m getodd_module \
    --input-dir match_urls_complete/by_league/switzerland \
    --output-dir switzerland_odds_output \
    --workers 5 \
    --handicaps "+2.5,+3,+3.5"
```


## 12. 📈 성능 최적화

### 시스템 설정
```bash
# 파일 디스크립터 제한 증가
ulimit -n 4096

# Chrome 프로세스 제한 설정
echo "* soft nofile 4096" | sudo tee -a /etc/security/limits.conf
echo "* hard nofile 8192" | sudo tee -a /etc/security/limits.conf
```

### 워커 수 조정 가이드
- 2 vCPU: 2-3 workers
- 4 vCPU: 4-5 workers  
- 8 vCPU: 6-8 workers

## 13. 🔄 재시작 후 실행

```bash
#!/bin/bash
# run_scraper.sh 스크립트 생성

cd ~/getodd
source .venv/bin/activate

xvfb-run -a python -m getodd_module \
    --input-dir match_urls_complete/by_league/switzerland \
    --output-dir switzerland_odds_output \
    --workers 5 \
    --handicaps "+2.5,+3,+3.5" \
    --resume  # 중단된 작업 재개
```

```bash
# 실행 권한 부여
chmod +x run_scraper.sh

# 실행
./run_scraper.sh
```

## 14. ✅ 체크리스트

- [ ] Python 3.10+ 설치 완료
- [ ] Chromium & ChromeDriver 설치 완료
- [ ] xvfb 설치 완료
- [ ] 프로젝트 파일 업로드/클론 완료
- [ ] Python 패키지 설치 완료
- [ ] 테스트 실행 성공
- [ ] 실제 데이터 수집 시작

---

## 📝 예상 실행 시간

Switzerland 데이터 (약 1,500개 URL) 기준:
- 5 workers 사용: 약 1.5-2시간
- 3 workers 사용: 약 2.5-3시간

## 🆘 추가 지원

문제 발생 시 다음 정보와 함께 문의:
- `chromium-browser --version` 출력
- `python --version` 출력  
- `tail -100 switzerland_odds_output/processing_log.txt` 출력
- 에러 메시지 전체