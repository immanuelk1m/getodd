"""
Core scraping functionality for odds data collection
"""

import time
from datetime import datetime
from typing import List
import pytz
import os
import shutil
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from .config import (
    BROWSER_USER_AGENT, BROWSER_TIMEOUT, WAIT_DELAY, SCROLL_PAUSE, EXPAND_PAUSE,
    KOREA_TZ, UTC_FORMAT, DATE_PARSE_FORMAT, XPATH_SELECTORS
)
from .parser import parse_url_for_info


def create_driver(headless: bool = True) -> webdriver.Chrome:
    """
    WebDriver 인스턴스 생성
    
    Args:
        headless: 헤드리스 모드 여부
        
    Returns:
        Chrome WebDriver 인스턴스
    """
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless")
    options.add_argument("--start-maximized")
    options.add_argument(f"user-agent={BROWSER_USER_AGENT}")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    
    # Chromium/Chrome 드라이버 자동 감지
    chrome_driver_path = None
    
    # 1. chromium-chromedriver 확인 (Ubuntu/Debian)
    if os.path.exists("/usr/bin/chromedriver"):
        chrome_driver_path = "/usr/bin/chromedriver"
    # 2. snap chromium-chromedriver 확인
    elif os.path.exists("/snap/bin/chromium.chromedriver"):
        chrome_driver_path = "/snap/bin/chromium.chromedriver"
    # 3. 일반 chromedriver 확인
    elif shutil.which("chromedriver"):
        chrome_driver_path = shutil.which("chromedriver")
    
    if chrome_driver_path:
        # 시스템에 설치된 chromedriver 사용
        service = Service(chrome_driver_path)
    else:
        # webdriver-manager로 자동 다운로드 (폴백)
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            service = Service(ChromeDriverManager().install())
        except Exception:
            raise Exception("ChromeDriver not found. Please install chromium-chromedriver or google-chrome-stable")
    
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def scrape_match_and_odds_with_driver(driver: webdriver.Chrome, base_url: str, 
                                      handicaps_to_scrape: List[str]) -> List:
    """
    기존 driver를 사용하여 URL에서 경기 정보와 핸디캡 배당률 수집
    
    Args:
        driver: WebDriver 인스턴스
        base_url: 스크래핑할 URL
        handicaps_to_scrape: 수집할 핸디캡 리스트
        
    Returns:
        수집된 배당률 데이터 리스트
    """
    all_odds_data = []
    
    league_name, season_info = parse_url_for_info(base_url)
    target_url = base_url.rstrip('/') + "/#over-under;2"

    try:
        driver.get(target_url)
        wait = WebDriverWait(driver, BROWSER_TIMEOUT)
        
        # 쿠키 동의 버튼 처리
        try:
            wait.until(EC.element_to_be_clickable((By.ID, XPATH_SELECTORS['cookie_button']))).click()
        except TimeoutException:
            pass
        
        # 매치 정보 추출
        match_info = extract_match_info(driver, wait)
        
        # 각 핸디캡별 배당률 수집
        for handicap in handicaps_to_scrape:
            odds_data = extract_odds_for_handicap(
                driver, wait, handicap, match_info, 
                league_name, season_info, base_url
            )
            all_odds_data.extend(odds_data)

    except Exception as e:
        raise e

    return all_odds_data


def extract_match_info(driver: webdriver.Chrome, wait: WebDriverWait) -> dict:
    """
    매치 기본 정보 추출
    
    Args:
        driver: WebDriver 인스턴스
        wait: WebDriverWait 인스턴스
        
    Returns:
        매치 정보 딕셔너리
    """
    match_info = {}
    
    # 팀 이름 추출
    try:
        match_info['home_team'] = wait.until(
            EC.visibility_of_element_located((By.XPATH, XPATH_SELECTORS['home_team']))
        ).text
        match_info['away_team'] = wait.until(
            EC.visibility_of_element_located((By.XPATH, XPATH_SELECTORS['away_team']))
        ).text
    except TimeoutException:
        match_info['home_team'] = 'N/A'
        match_info['away_team'] = 'N/A'

    # 날짜 추출
    try:
        time_container = wait.until(
            EC.visibility_of_element_located((By.XPATH, XPATH_SELECTORS['time_container']))
        )
        date_parts_text = time_container.text.split('\n')
        date_str = f"{date_parts_text[1].strip(',')} {date_parts_text[2]}"
        
        local_dt = datetime.strptime(date_str, DATE_PARSE_FORMAT)
        korea_tz = pytz.timezone(KOREA_TZ)
        korea_dt = korea_tz.localize(local_dt)
        utc_dt = korea_dt.astimezone(pytz.utc)
        match_info['match_date_utc'] = utc_dt.strftime(UTC_FORMAT)
    except (NoSuchElementException, IndexError, ValueError):
        match_info['match_date_utc'] = 'N/A'
        
    return match_info


def extract_odds_for_handicap(driver: webdriver.Chrome, wait: WebDriverWait, 
                              handicap: str, match_info: dict, 
                              league_name: str, season_info: str, 
                              base_url: str) -> List:
    """
    특정 핸디캡에 대한 배당률 추출
    
    Args:
        driver: WebDriver 인스턴스
        wait: WebDriverWait 인스턴스
        handicap: 핸디캡 값
        match_info: 매치 정보
        league_name: 리그 이름
        season_info: 시즌 정보
        base_url: 매치 URL
        
    Returns:
        배당률 데이터 리스트
    """
    odds_data = []
    target_row = None
    
    try:
        # 핸디캡 행 찾기
        target_row_xpath = XPATH_SELECTORS['target_row'].format(handicap)
        target_row = wait.until(EC.presence_of_element_located((By.XPATH, target_row_xpath)))
        
        # 스크롤 및 클릭하여 확장
        driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", target_row)
        time.sleep(SCROLL_PAUSE)
        wait.until(EC.element_to_be_clickable(target_row)).click()

        # 확장된 컨테이너 대기
        expanded_container_xpath = XPATH_SELECTORS['expanded_container'].format(target_row_xpath)
        wait.until(EC.visibility_of_element_located((By.XPATH, expanded_container_xpath)))
        time.sleep(EXPAND_PAUSE)

        # 북메이커별 배당률 추출
        bookmaker_rows_xpath = XPATH_SELECTORS['bookmaker_rows'].format(expanded_container_xpath)
        bookmaker_rows = driver.find_elements(By.XPATH, bookmaker_rows_xpath)
        
        for row in bookmaker_rows:
            try:
                bookmaker = row.find_element(By.XPATH, XPATH_SELECTORS['bookmaker_name']).text
                odds_elements = row.find_elements(By.XPATH, XPATH_SELECTORS['odds_text'])
                
                over_odds = odds_elements[0].text if len(odds_elements) > 0 else 'N/A'
                under_odds = odds_elements[1].text if len(odds_elements) > 1 else 'N/A'

                if over_odds not in ['N/A', '-']:
                    odds_data.append([
                        match_info['match_date_utc'], 
                        match_info['home_team'], 
                        match_info['away_team'], 
                        league_name, 
                        season_info, 
                        bookmaker, 
                        f"Over {handicap}", 
                        over_odds, 
                        base_url
                    ])
                
                if under_odds not in ['N/A', '-']:
                    odds_data.append([
                        match_info['match_date_utc'], 
                        match_info['home_team'], 
                        match_info['away_team'], 
                        league_name, 
                        season_info, 
                        bookmaker, 
                        f"Under {handicap}", 
                        under_odds, 
                        base_url
                    ])

            except NoSuchElementException:
                continue

        # 행 닫기
        if target_row:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", target_row)
            time.sleep(WAIT_DELAY)
            target_row.click()
            time.sleep(SCROLL_PAUSE)

    except Exception:
        pass  # 해당 핸디캡이 없는 경우 무시
        
    return odds_data


def scrape_match_and_odds(base_url: str, handicaps_to_scrape: List[str], 
                         headless: bool = True) -> List:
    """
    주어진 URL에서 경기 정보와 여러 핸디캡 배당률을 수집하여 반환하는 함수
    (backward compatibility를 위한 wrapper 함수)
    
    Args:
        base_url: 스크래핑할 URL
        handicaps_to_scrape: 수집할 핸디캡 리스트
        headless: 헤드리스 모드 여부
        
    Returns:
        수집된 배당률 데이터 리스트
    """
    driver = create_driver(headless)
    try:
        return scrape_match_and_odds_with_driver(driver, base_url, handicaps_to_scrape)
    finally:
        driver.quit()