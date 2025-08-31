import time
import pandas as pd
from datetime import datetime
import pytz
import re  # 정규표현식 모듈 import
import argparse
import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# [전면 수정] 더 강력한 URL 파싱 함수
def parse_url_for_info(url):
    """
    URL에서 리그 이름과 시즌 정보를 정규표현식을 사용하여 더 안정적으로 추출하는 함수.
    'league-name-YYYY-YYYY' 와 'league-name-YYYY' 형식을 모두 지원.
    """
    try:
        clean_url = url.split('/#')[0].strip('/')
        parts = clean_url.split('/')
        
        # URL 구조: .../football/country/league-season/match-teams/
        # football 다음의 league-season 부분 찾기
        league_season_slug = None
        
        if 'football' in parts:
            football_idx = parts.index('football')
            # football 다음 다음이 league-season (country 건너뛰기)
            if len(parts) > football_idx + 2:
                league_season_slug = parts[football_idx + 2]
        
        if not league_season_slug:
            # fallback: 끝에서 두 번째 (기존 로직)
            if len(parts) >= 2:
                # URL이 /로 끝나면 -2, 아니면 -1이 match 부분
                if parts[-1]:  # URL이 /로 끝나지 않음
                    league_season_slug = parts[-2]
                else:  # URL이 /로 끝남
                    league_season_slug = parts[-3] if len(parts) >= 3 else parts[-2]
            else:
                return 'N/A', 'N/A'
        
        # 정규표현식 패턴: (리그이름)-(YYYY-YYYY 또는 YYYY)
        pattern = re.compile(r'^(.+?)-(\d{4}(?:-\d{4})?)$')
        match = pattern.match(league_season_slug)
        
        if match:
            # 그룹 1: 리그 이름 슬러그, 그룹 2: 시즌 정보
            league_name_slug = match.group(1)
            season_info = match.group(2)
            league_name = league_name_slug.replace('-', ' ').title()
            
            # 시즌 정보 정규화: YYYY -> YYYY-YYYY+1
            if '-' not in season_info and len(season_info) == 4:
                year = int(season_info)
                season_info = f'{year}-{year + 1}'
            # 이미 YYYY-YYYY 형식이면 그대로 유지
            
        else:
            # 패턴에 맞지 않으면 시즌 정보 없이 전체를 리그 이름으로 처리
            season_info = 'N/A'
            league_name = league_season_slug.replace('-', ' ').title()
            
        return league_name, season_info
    except Exception:
        # URL 구조가 예상과 완전히 다른 경우에 대한 예외 처리
        return 'N/A', 'N/A'

def scrape_match_and_odds(base_url, handicaps_to_scrape):
    """
    주어진 URL에서 경기 정보와 여러 핸디캡 배당률을 수집하여 CSV로 저장하는 함수
    """
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--start-maximized")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    all_odds_data = []
    
    league_name, season_info = parse_url_for_info(base_url)
    target_url = base_url.rstrip('/') + "/#over-under;2"

    try:
        driver.get(target_url)
        print(f"'{target_url}'에 접속 중...")
        wait = WebDriverWait(driver, 20)
        
        try:
            wait.until(EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))).click()
            print("쿠키 동의 버튼을 클릭했습니다.")
        except TimeoutException:
            print("쿠키 동의 버튼이 나타나지 않았습니다.")

        print("\n경기 기본 정보를 수집합니다...")
        
        try:
            home_team = wait.until(EC.visibility_of_element_located((By.XPATH, "//div[@data-testid='game-host']/p"))).text
            away_team = wait.until(EC.visibility_of_element_located((By.XPATH, "//div[@data-testid='game-guest']/p"))).text
        except TimeoutException:
            home_team, away_team = 'N/A', 'N/A'

        try:
            time_container = wait.until(EC.visibility_of_element_located((By.XPATH, "//div[@data-testid='game-time-item']")))
            date_parts_text = time_container.text.split('\n')
            date_str = f"{date_parts_text[1].strip(',')} {date_parts_text[2]}"
            
            local_dt = datetime.strptime(date_str, "%d %b %Y %H:%M")
            korea_tz = pytz.timezone('Asia/Seoul')
            korea_dt = korea_tz.localize(local_dt)
            utc_dt = korea_dt.astimezone(pytz.utc)
            match_date_utc = utc_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        except (NoSuchElementException, IndexError, ValueError):
            match_date_utc = 'N/A'
            
        print(f"리그: {league_name} (시즌: {season_info})")
        print(f"경기: {home_team} vs {away_team}")
        print(f"날짜(UTC): {match_date_utc}")

        # --- 핸디캡별 배당률 수집 ---
        for handicap in handicaps_to_scrape:
            print(f"\n{'='*30}\n▶ Over/Under {handicap} 배당률 수집 시작\n{'='*30}")
            target_row = None
            try:
                target_row_xpath = f"//div[contains(@class, 'h-9') and .//p[normalize-space(.)='Over/Under {handicap}']]"
                target_row = wait.until(EC.presence_of_element_located((By.XPATH, target_row_xpath)))
                
                driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", target_row)
                time.sleep(1)
                
                wait.until(EC.element_to_be_clickable(target_row)).click()
                print(f"Over/Under {handicap} 항목을 펼쳤습니다.")

                expanded_container_xpath = f"{target_row_xpath}/following-sibling::div[1]"
                wait.until(EC.visibility_of_element_located((By.XPATH, expanded_container_xpath)))
                time.sleep(2)

                bookmaker_rows = driver.find_elements(By.XPATH, f"{expanded_container_xpath}//div[contains(@data-testid, 'expanded-row')]")
                
                for row in bookmaker_rows:
                    try:
                        bookmaker = row.find_element(By.XPATH, ".//p[contains(@data-testid, 'bookmaker-name')]").text
                        odds_elements = row.find_elements(By.XPATH, ".//p[@class='odds-text']")
                        
                        over_odds = odds_elements[0].text if len(odds_elements) > 0 else 'N/A'
                        under_odds = odds_elements[1].text if len(odds_elements) > 1 else 'N/A'

                        if over_odds not in ['N/A', '-']:
                            all_odds_data.append([match_date_utc, home_team, away_team, league_name, season_info, bookmaker, f"Over {handicap}", over_odds, base_url])
                        
                        if under_odds not in ['N/A', '-']:
                            all_odds_data.append([match_date_utc, home_team, away_team, league_name, season_info, bookmaker, f"Under {handicap}", under_odds, base_url])

                    except NoSuchElementException:
                        continue
                print(f"Over/Under {handicap} 항목의 데이터 수집 완료.")

                if target_row:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", target_row)
                    time.sleep(0.5)
                    target_row.click()
                    print(f"Over/Under {handicap} 항목을 닫았습니다.")
                    time.sleep(1)

            except Exception as e:
                print(f"Over/Under {handicap} 처리 중 오류 발생: {e}")

    except Exception as e:
        print(f"전체 프로세스 중 오류가 발생했습니다: {e}")
    finally:
        driver.quit()

    return all_odds_data

def setup_logging(output_dir: Path) -> logging.Logger:
    """
    로깅 설정
    """
    logger = logging.getLogger('odds_scraper')
    logger.setLevel(logging.INFO)
    
    # 파일 핸들러
    log_file = output_dir / 'processing_log.txt'
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 포맷터
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def find_csv_files(input_dir: Path) -> List[Path]:
    """
    입력 디렉토리에서 모든 CSV 파일 찾기
    """
    csv_files = list(input_dir.rglob('*.csv'))
    return sorted(csv_files)

def load_checkpoint(checkpoint_file: Path) -> Dict:
    """
    체크포인트 파일 로드
    """
    if checkpoint_file.exists():
        with open(checkpoint_file, 'r') as f:
            return json.load(f)
    return {'processed_files': [], 'failed_urls': []}

def save_checkpoint(checkpoint_file: Path, checkpoint_data: Dict):
    """
    체크포인트 저장
    """
    with open(checkpoint_file, 'w') as f:
        json.dump(checkpoint_data, f, indent=2)

def process_url_batch(urls_batch: List[str], worker_id: int, handicaps: List[str], 
                      logger: logging.Logger, headless: bool = True) -> Tuple[List, List]:
    """
    Worker function to process a batch of URLs in a single browser instance
    """
    results = []
    failed_urls = []
    driver = None
    
    try:
        driver = create_driver(headless)
        logger.info(f"Worker {worker_id}: Processing {len(urls_batch)} URLs")
        
        for idx, url in enumerate(urls_batch):
            try:
                logger.info(f"  Worker {worker_id} [{idx+1}/{len(urls_batch)}]: {url}")
                result = scrape_match_and_odds_with_driver(driver, url, handicaps)
                results.extend(result)
                logger.info(f"    ✓ Worker {worker_id}: Collected {len(result)} entries")
                time.sleep(0.5)  # Small delay between requests
            except Exception as e:
                logger.error(f"    ✗ Worker {worker_id}: Failed - {str(e)}")
                failed_urls.append({'url': url, 'error': str(e), 'worker_id': worker_id})
    finally:
        if driver:
            driver.quit()
            logger.info(f"Worker {worker_id}: Browser closed")
    
    return results, failed_urls

def process_csv_file(csv_file: Path, handicaps: List[str], output_dir: Path, 
                     logger: logging.Logger, headless: bool = True, num_workers: int = 1) -> Tuple[List, List]:
    """
    단일 CSV 파일 처리 (병렬 처리 지원)
    """
    all_results = []
    failed_urls = []
    
    try:
        df = pd.read_csv(csv_file)
        urls = df['match_url'].tolist()
        total_urls = len(urls)
        logger.info(f"Processing {csv_file.name}: {total_urls} URLs found with {num_workers} workers")
        
        if num_workers == 1:
            # Sequential processing (backward compatibility)
            for idx, url in enumerate(urls):
                logger.info(f"  [{idx+1}/{total_urls}] Processing: {url}")
                
                try:
                    results = scrape_match_and_odds(url, handicaps, headless)
                    all_results.extend(results)
                    logger.info(f"    ✓ Collected {len(results)} odds entries")
                except Exception as e:
                    logger.error(f"    ✗ Failed: {str(e)}")
                    failed_urls.append({'url': url, 'error': str(e), 'csv_file': str(csv_file)})
                    continue
                
                time.sleep(1)
        else:
            # Parallel processing
            batch_size = (total_urls + num_workers - 1) // num_workers
            url_batches = [urls[i:i+batch_size] for i in range(0, total_urls, batch_size)]
            
            with ThreadPoolExecutor(max_workers=num_workers) as executor:
                futures = {}
                
                for worker_id, batch in enumerate(url_batches):
                    if batch:  # Only submit if batch is not empty
                        future = executor.submit(process_url_batch, batch, worker_id, 
                                                handicaps, logger, headless)
                        futures[future] = worker_id
                
                for future in as_completed(futures):
                    worker_id = futures[future]
                    try:
                        results, failed = future.result()
                        all_results.extend(results)
                        failed_urls.extend(failed)
                        logger.info(f"Worker {worker_id} completed: {len(results)} entries collected")
                    except Exception as e:
                        logger.error(f"Worker {worker_id} failed: {str(e)}")
            
    except Exception as e:
        logger.error(f"Failed to process CSV file {csv_file}: {str(e)}")
        
    return all_results, failed_urls

def create_driver(headless=True):
    """
    WebDriver 인스턴스 생성
    """
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless")
    options.add_argument("--start-maximized")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def scrape_match_and_odds_with_driver(driver, base_url, handicaps_to_scrape):
    """
    기존 driver를 사용하여 URL에서 경기 정보와 핸디캡 배당률 수집
    """
    
    all_odds_data = []
    
    league_name, season_info = parse_url_for_info(base_url)
    target_url = base_url.rstrip('/') + "/#over-under;2"

    try:
        driver.get(target_url)
        wait = WebDriverWait(driver, 20)
        
        try:
            wait.until(EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))).click()
        except TimeoutException:
            pass
        
        try:
            home_team = wait.until(EC.visibility_of_element_located((By.XPATH, "//div[@data-testid='game-host']/p"))).text
            away_team = wait.until(EC.visibility_of_element_located((By.XPATH, "//div[@data-testid='game-guest']/p"))).text
        except TimeoutException:
            home_team, away_team = 'N/A', 'N/A'

        try:
            time_container = wait.until(EC.visibility_of_element_located((By.XPATH, "//div[@data-testid='game-time-item']")))
            date_parts_text = time_container.text.split('\n')
            date_str = f"{date_parts_text[1].strip(',')} {date_parts_text[2]}"
            
            local_dt = datetime.strptime(date_str, "%d %b %Y %H:%M")
            korea_tz = pytz.timezone('Asia/Seoul')
            korea_dt = korea_tz.localize(local_dt)
            utc_dt = korea_dt.astimezone(pytz.utc)
            match_date_utc = utc_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        except (NoSuchElementException, IndexError, ValueError):
            match_date_utc = 'N/A'

        # --- 핸디캡별 배당률 수집 ---
        for handicap in handicaps_to_scrape:
            target_row = None
            try:
                target_row_xpath = f"//div[contains(@class, 'h-9') and .//p[normalize-space(.)='Over/Under {handicap}']]"
                target_row = wait.until(EC.presence_of_element_located((By.XPATH, target_row_xpath)))
                
                driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", target_row)
                time.sleep(1)
                
                wait.until(EC.element_to_be_clickable(target_row)).click()

                expanded_container_xpath = f"{target_row_xpath}/following-sibling::div[1]"
                wait.until(EC.visibility_of_element_located((By.XPATH, expanded_container_xpath)))
                time.sleep(2)

                bookmaker_rows = driver.find_elements(By.XPATH, f"{expanded_container_xpath}//div[contains(@data-testid, 'expanded-row')]")
                
                for row in bookmaker_rows:
                    try:
                        bookmaker = row.find_element(By.XPATH, ".//p[contains(@data-testid, 'bookmaker-name')]").text
                        odds_elements = row.find_elements(By.XPATH, ".//p[@class='odds-text']")
                        
                        over_odds = odds_elements[0].text if len(odds_elements) > 0 else 'N/A'
                        under_odds = odds_elements[1].text if len(odds_elements) > 1 else 'N/A'

                        if over_odds not in ['N/A', '-']:
                            all_odds_data.append([match_date_utc, home_team, away_team, league_name, season_info, bookmaker, f"Over {handicap}", over_odds, base_url])
                        
                        if under_odds not in ['N/A', '-']:
                            all_odds_data.append([match_date_utc, home_team, away_team, league_name, season_info, bookmaker, f"Under {handicap}", under_odds, base_url])

                    except NoSuchElementException:
                        continue

                if target_row:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", target_row)
                    time.sleep(0.5)
                    target_row.click()
                    time.sleep(1)

            except Exception:
                continue

    except Exception as e:
        raise e

    return all_odds_data

def scrape_match_and_odds(base_url, handicaps_to_scrape, headless=True):
    """
    주어진 URL에서 경기 정보와 여러 핸디캡 배당률을 수집하여 반환하는 함수
    (backward compatibility를 위한 wrapper 함수)
    """
    driver = create_driver(headless)
    try:
        return scrape_match_and_odds_with_driver(driver, base_url, handicaps_to_scrape)
    finally:
        driver.quit()

def main():
    parser = argparse.ArgumentParser(description='Scrape odds data from multiple CSV files containing match URLs')
    parser.add_argument('--input-dir', type=str, default='match_urls_complete/by_league/',
                        help='Directory containing CSV files (default: match_urls_complete/by_league/)')
    parser.add_argument('--output-dir', type=str, default='odds_data_output/',
                        help='Directory for output files (default: odds_data_output/)')
    parser.add_argument('--handicaps', type=str, default='+2.5,+3,+3.5',
                        help='Comma-separated handicap values (default: +2.5,+3,+3.5)')
    parser.add_argument('--batch-size', type=int, default=10,
                        help='Number of URLs to process before saving (default: 10)')
    parser.add_argument('--resume', action='store_true',
                        help='Resume from last processed file')
    parser.add_argument('--no-headless', action='store_true',
                        help='Run browser in visible mode (default: headless)')
    parser.add_argument('--test', action='store_true',
                        help='Test mode: process only first CSV file')
    parser.add_argument('--workers', type=int, default=1,
                        help='Number of parallel browser instances (default: 1)')
    
    args = parser.parse_args()
    
    # 경로 설정
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 로깅 설정
    logger = setup_logging(output_dir)
    logger.info("="*50)
    logger.info("Odds Scraper Started")
    logger.info(f"Input directory: {input_dir}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Handicaps: {args.handicaps}")
    logger.info(f"Workers: {args.workers}")
    logger.info("="*50)
    
    # 핸디캡 파싱
    handicaps = [h.strip() for h in args.handicaps.split(',')]
    
    # CSV 파일 찾기
    csv_files = find_csv_files(input_dir)
    if not csv_files:
        logger.error(f"No CSV files found in {input_dir}")
        return
    
    logger.info(f"Found {len(csv_files)} CSV files")
    
    # 테스트 모드
    if args.test:
        test_csv = Path("test.csv")
        if test_csv.exists():
            csv_files = [test_csv]
            logger.info("TEST MODE: Using test.csv")
        else:
            logger.error("TEST MODE: test.csv not found")
            return
    
    # 체크포인트 처리
    checkpoint_file = output_dir / 'checkpoint.json'
    checkpoint_data = load_checkpoint(checkpoint_file) if args.resume else {'processed_files': [], 'failed_urls': []}
    
    # 이미 처리된 파일 필터링
    if args.resume and checkpoint_data['processed_files']:
        processed_set = set(checkpoint_data['processed_files'])
        csv_files = [f for f in csv_files if str(f) not in processed_set]
        logger.info(f"Resuming: {len(processed_set)} files already processed, {len(csv_files)} remaining")
    
    # 실패한 URL 저장용
    all_failed_urls = checkpoint_data.get('failed_urls', [])
    
    # 각 CSV 파일 처리
    for idx, csv_file in enumerate(csv_files, 1):
        logger.info(f"\n[{idx}/{len(csv_files)}] Processing: {csv_file}")
        
        # CSV 파일 처리
        results, failed_urls = process_csv_file(
            csv_file, handicaps, output_dir, logger, 
            headless=not args.no_headless,
            num_workers=args.workers
        )
        
        # 결과 저장
        if results:
            # 리그별 저장 디렉토리 생성
            try:
                relative_path = csv_file.relative_to(input_dir)
                league_output_dir = output_dir / relative_path.parent
            except ValueError:
                # test.csv 등 input_dir 외부 파일 처리
                league_output_dir = output_dir
            
            league_output_dir.mkdir(parents=True, exist_ok=True)
            
            # 리그별 CSV 저장
            output_file = league_output_dir / f"{csv_file.stem}_odds.csv"
            columns = ['match_date', 'home_team', 'away_team', 'league_name', 'season_info', 
                      'bookmaker', 'odd_type', 'odd_value', 'match_url']
            df = pd.DataFrame(results, columns=columns)
            df.to_csv(output_file, index=False, encoding='utf-8-sig')
            logger.info(f"  Saved {len(results)} entries to {output_file}")
        
        # 실패한 URL 추가
        all_failed_urls.extend(failed_urls)
        
        # 체크포인트 업데이트
        checkpoint_data['processed_files'].append(str(csv_file))
        checkpoint_data['failed_urls'] = all_failed_urls
        save_checkpoint(checkpoint_file, checkpoint_data)
    
    # 실패한 URL 저장
    if all_failed_urls:
        failed_file = output_dir / 'failed_urls.json'
        with open(failed_file, 'w') as f:
            json.dump(all_failed_urls, f, indent=2)
        logger.warning(f"\nFailed URLs saved to {failed_file}")
        logger.warning(f"Total failed: {len(all_failed_urls)}")
    
    logger.info("\n" + "="*50)
    logger.info("Processing completed!")
    logger.info("="*50)

# --- 실행 부분 ---
if __name__ == "__main__":
    main()