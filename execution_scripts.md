# GetOdd 국가별 실행 스크립트

각 국가별로 약 1,600개의 URL을 처리합니다. `--workers` 옵션으로 병렬 처리 속도를 조절할 수 있습니다.

## 사전 준비
```bash
# Chrome 브라우저가 설치되어 있어야 합니다
google-chrome --version

# 가상환경 활성화
source .venv/bin/activate

# 또는 uv 사용 시
uv sync
```

## 1. 🇧🇪 Belgium (벨기에)
```bash
xvfb-run -a python -m getodd_module \
    --input-dir match_urls_complete/by_league/belgium \
    --output-dir ./data/belgium_odds_output \
    --workers 5 \
    --handicaps "+2.5,+3,+3.5"
```

## 2. 🇩🇰 Denmark (덴마크)
```bash
xvfb-run -a python -m getodd_module \
    --input-dir match_urls_complete/by_league/denmark \
    --output-dir ./data/denmark_odds_output \
    --workers 5 \
    --handicaps "+2.5,+3,+3.5"
```

## 3. 🏴󠁧󠁢󠁥󠁮󠁧󠁿 England (잉글랜드)
```bash
xvfb-run -a python -m getodd_module \
    --input-dir match_urls_complete/by_league/england \
    --output-dir ./data/england_odds_output \
    --workers 5 \
    --handicaps "+2.5,+3,+3.5"
```

## 4. 🇫🇷 France (프랑스)
```bash
xvfb-run -a python -m getodd_module \
    --input-dir match_urls_complete/by_league/france \
    --output-dir ./data/france_odds_output \
    --workers 5 \
    --handicaps "+2.5,+3,+3.5"
```

## 5. 🇩🇪 Germany (독일)
```bash
xvfb-run -a python -m getodd_module \
    --input-dir match_urls_complete/by_league/germany \
    --output-dir ./data/germany_odds_output \
    --workers 5 \
    --handicaps "+2.5,+3,+3.5"
```

## 6. 🇮🇹 Italy (이탈리아)
```bash
xvfb-run -a python -m getodd_module \
    --input-dir match_urls_complete/by_league/italy \
    --output-dir ./data/italy_odds_output \
    --workers 5 \
    --handicaps "+2.5,+3,+3.5"
```

## 7. 🇳🇱 Netherlands (네덜란드)
```bash
xvfb-run -a python -m getodd_module \
    --input-dir match_urls_complete/by_league/netherlands \
    --output-dir ./data/netherlands_odds_output \
    --workers 4 \
    --handicaps "+2.5,+3,+3.5"
```

## 8. 🇳🇴 Norway (노르웨이)
```bash
xvfb-run -a python -m getodd_module \
    --input-dir match_urls_complete/by_league/norway \
    --output-dir ./data/norway_odds_output \
    --workers 4 \
    --handicaps "+2.5,+3,+3.5"
```

## 9. 🇵🇹 Portugal (포르투갈)
```bash
xvfb-run -a python -m getodd_module \
    --input-dir match_urls_complete/by_league/portugal \
    --output-dir ./data/portugal_odds_output \
    --workers 5 \
    --handicaps "+2.5,+3,+3.5"
```

## 10. 🏴󠁧󠁢󠁳󠁣󠁴󠁿 Scotland (스코틀랜드)
```bash
xvfb-run -a python -m getodd_module \
    --input-dir match_urls_complete/by_league/scotland \
    --output-dir ./data/scotland_odds_output \
    --workers 5 \
    --handicaps "+2.5,+3,+3.5"
```

## 11. 🇪🇸 Spain (스페인)
```bash
xvfb-run -a python -m getodd_module \
    --input-dir match_urls_complete/by_league/spain \
    --output-dir ./data/spain_odds_output \
    --workers 5 \
    --handicaps "+2.5,+3,+3.5"
```


--- 12 / 13 진행중

## 12. 🇸🇪 Sweden (스웨덴)
```bash
xvfb-run -a python -m getodd_module \
    --input-dir match_urls_complete/by_league/sweden \
    --output-dir ./data/sweden_odds_output \
    --workers 5 \
    --handicaps "+2.5,+3,+3.5"
```

## 13. 🇨🇭 Switzerland (스위스)
```bash
xvfb-run -a python -m getodd_module \
    --input-dir match_urls_complete/by_league/switzerland \
    --output-dir ./data/switzerland_odds_output \
    --workers 3 \
    --handicaps "+2.5,+3,+3.5"
```

---

## 모든 국가 순차 실행 스크립트

### 방법 1: Shell 스크립트 (run_all.sh)
```bash
#!/bin/bash

countries=("belgium" "denmark" "england" "france" "germany" "italy" 
           "netherlands" "norway" "portugal" "scotland" "spain" 
           "sweden" "switzerland")

for country in "${countries[@]}"; do
    echo "Processing $country..."
    xvfb-run -a python -m getodd_module \
        --input-dir match_urls_complete/by_league/$country \
        --output-dir ./data/${country}_odds_output \
        --workers 5 \
        --handicaps "+2.5,+3,+3.5"
    echo "$country completed!"
    echo "----------------------------"
done
```

### 방법 2: Python 스크립트 (run_all.py)
```python
import subprocess
import time

countries = [
    "belgium", "denmark", "england", "france", "germany", 
    "italy", "netherlands", "norway", "portugal", "scotland", 
    "spain", "sweden", "switzerland"
]

for country in countries:
    print(f"\n{'='*50}")
    print(f"Processing {country.upper()}...")
    print(f"{'='*50}")
    
    cmd = [
        "xvfb-run", "-a", "python", "-m", "getodd_module",
        "--input-dir", f"match_urls_complete/by_league/{country}",
        "--output-dir", f"./data/{country}_odds_output",
        "--workers", "5",
        "--handicaps", "+2.5,+3,+3.5"
    ]
    
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print(f"✅ {country} completed successfully!")
    else:
        print(f"❌ {country} failed with error code {result.returncode}")
    
    # 국가 간 대기 시간 (선택사항)
    time.sleep(10)

print("\n🎉 All countries processed!")
```

---

## 옵션 설명

### 기본 옵션
- `--input-dir`: 입력 CSV 파일 디렉토리
- `--output-dir`: 결과 저장 디렉토리
- `--workers`: 병렬 브라우저 수 (기본: 1, 권장: 5-10)
- `--handicaps`: 수집할 핸디캡 값 (쉼표로 구분)

### 추가 옵션
- `--resume`: 중단된 작업 재개
- `--no-headless`: 브라우저 창 표시 (디버깅용)
- `--batch-size`: 배치 저장 크기 (기본: 10)
- `--test`: test.csv만 처리 (테스트용)

---

## 예상 처리 시간

각 국가별 약 1,600개 URL 기준:
- 1 worker: ~6-7시간
- 5 workers: ~1.5-2시간  
- 10 workers: ~45분-1시간

**전체 13개국 처리 시간:**
- 5 workers 사용 시: 약 20-26시간
- 10 workers 사용 시: 약 10-13시간

---

## 출력 구조

각 국가별로 다음과 같은 구조로 저장됩니다:

```
data/
└── {country}_odds_output/
    ├── 2020-2021_odds.csv
    ├── 2021-2022_odds.csv
    ├── 2022-2023_odds.csv
    ├── 2023-2024_odds.csv
    ├── 2024-2025_odds.csv
    ├── checkpoint.json
    ├── processing_log.txt
    └── failed_urls.json (실패한 URL이 있을 경우)
```

---

## 트러블슈팅

### Chrome 브라우저 오류
```bash
# Chrome 설치 확인
google-chrome --version

# Chrome 재설치
sudo apt update
sudo apt install -y google-chrome-stable
```

### 메모리 부족
```bash
# workers 수 줄이기
--workers 3
```

### 재개하기
```bash
# 중단된 작업 재개
xvfb-run -a python -m getodd_module \
    --input-dir match_urls_complete/by_league/{country} \
    --output-dir ./data/{country}_odds_output \
    --workers 5 \
    --handicaps "+2.5,+3,+3.5" \
    --resume
```