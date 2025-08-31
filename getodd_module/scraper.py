"""
Core scraping functionality for odds data collection
"""

import time
from datetime import datetime
from typing import List
import pytz
import os
import shutil
import subprocess
import platform
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

from .config import (
    BROWSER_USER_AGENT, BROWSER_TIMEOUT, WAIT_DELAY, SCROLL_PAUSE, EXPAND_PAUSE,
    KOREA_TZ, UTC_FORMAT, DATE_PARSE_FORMAT, XPATH_SELECTORS
)
from .parser import parse_url_for_info


def cleanup_chromedriver_processes():
    """Kill any stuck chromedriver processes"""
    if platform.system() == "Darwin":  # macOS
        try:
            # Kill chromedriver processes - use -9 for force kill
            subprocess.run(["pkill", "-9", "-f", "chromedriver"], capture_output=True, timeout=5)
            # Kill headless Chrome processes
            subprocess.run(["pkill", "-9", "-f", "Chrome.*--headless"], capture_output=True, timeout=5)
            time.sleep(1)
        except:
            pass
    elif platform.system() == "Linux":
        try:
            subprocess.run(["pkill", "-9", "-f", "chromedriver"], capture_output=True, timeout=5)
            subprocess.run(["pkill", "-9", "-f", "chrome.*--headless"], capture_output=True, timeout=5)
            time.sleep(1)
        except:
            pass


def force_quit_driver(driver):
    """
    Force quit driver with multiple fallback methods
    
    Args:
        driver: WebDriver instance to quit
    """
    if not driver:
        return
    
    try:
        # Try normal quit first
        driver.quit()
    except:
        pass
    
    try:
        # Try to kill the service process directly
        if hasattr(driver, 'service') and hasattr(driver.service, 'process'):
            if driver.service.process:
                try:
                    driver.service.process.terminate()
                    time.sleep(0.5)
                    if driver.service.process.poll() is None:
                        driver.service.process.kill()
                except:
                    pass
    except:
        pass
    
    # Final cleanup at system level
    cleanup_chromedriver_processes()


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
        options.add_argument("--headless=new")  # Use new headless mode
    
    # 서버 환경을 위한 필수 옵션들
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-setuid-sandbox")
    options.add_argument("--disable-features=VizDisplayCompositor")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(f"user-agent={BROWSER_USER_AGENT}")
    
    # GCP 환경을 위한 추가 옵션
    if platform.system() == "Linux":
        options.add_argument("--disable-features=NetworkService")
        options.add_argument("--disable-features=VizDisplayCompositor")
        options.add_argument("--no-zygote")  # GCP에서 도움이 될 수 있음
    
    # Remove problematic options for macOS
    # options.add_argument("--memory-pressure-off")  # Can cause issues on macOS
    # options.add_argument("--single-process")  # Problematic with newer Chrome
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--disable-features=TranslateUI")
    options.add_argument("--disable-ipc-flooding-protection")
    
    # Add stability options for macOS
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-background-networking")
    options.add_argument("--safebrowsing-disable-auto-update")
    options.add_argument("--disable-sync")
    options.add_argument("--metrics-recording-only")
    options.add_argument("--disable-default-apps")
    options.add_argument("--no-first-run")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--disable-features=TranslateUI,BlinkGenPropertyTrees")
    options.add_argument("--force-color-profile=srgb")
    
    # 추가 안정성 옵션
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_experimental_option("prefs", {
        "profile.default_content_setting_values.notifications": 2,
        "profile.default_content_settings.popups": 0,
        "profile.managed_default_content_settings.images": 1,  # Enable images (2 can cause issues)
        "download.default_directory": "/tmp",
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": False
    })
    
    # macOS specific stability settings
    options.add_experimental_option('w3c', True)
    options.add_experimental_option('detach', False)
    
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
    
    # Create driver with error handling
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            driver = webdriver.Chrome(service=service, options=options)
            # Set page load strategy and timeouts
            driver.set_page_load_timeout(30)
            driver.implicitly_wait(10)
            return driver
        except Exception as e:
            if attempt < max_attempts - 1:
                time.sleep(2)  # Wait before retry
                continue
            raise e


def is_driver_alive(driver: webdriver.Chrome) -> bool:
    """
    Check if the driver is still alive and responsive
    
    Args:
        driver: WebDriver instance
        
    Returns:
        True if driver is alive, False otherwise
    """
    try:
        # Try to get current URL - simple check that doesn't change state
        _ = driver.current_url
        return True
    except:
        return False


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
    
    # Check if driver is still alive before proceeding
    if not is_driver_alive(driver):
        raise WebDriverException("Driver connection lost - needs restart")
    
    league_name, season_info = parse_url_for_info(base_url)
    target_url = base_url.rstrip('/') + "/#over-under;2"

    try:
        driver.get(target_url)
        
        # Wait for page to load
        wait_for_page_ready(driver)
        
        wait = WebDriverWait(driver, BROWSER_TIMEOUT)
        
        # 쿠키 동의 버튼 처리
        try:
            cookie_btn = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.ID, XPATH_SELECTORS['cookie_button']))
            )
            cookie_btn.click()
            time.sleep(0.5)
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


def wait_for_page_ready(driver: webdriver.Chrome, timeout: int = 10) -> bool:
    """
    Wait for page to be fully loaded
    
    Args:
        driver: WebDriver instance
        timeout: Maximum wait time
        
    Returns:
        True if page is ready, False otherwise
    """
    try:
        # Wait for document ready state
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        # Additional wait for dynamic content
        time.sleep(1)
        return True
    except:
        return False


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
    
    # Wait for page to be ready
    wait_for_page_ready(driver)
    
    # 팀 이름 추출 (더 관대한 대기)
    try:
        # Try multiple selectors
        home_team = None
        away_team = None
        
        # Wait for any team element to be present first
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//span[contains(@class, 'participant')]"))
            )
        except:
            pass
        
        # Now try to get team names
        try:
            home_team = wait.until(
                EC.presence_of_element_located((By.XPATH, XPATH_SELECTORS['home_team']))
            ).text
        except:
            # Fallback selector
            try:
                home_team = driver.find_element(By.XPATH, "//div[@class='odds-header']//span[1]").text
            except:
                pass
        
        try:
            away_team = wait.until(
                EC.presence_of_element_located((By.XPATH, XPATH_SELECTORS['away_team']))
            ).text
        except:
            # Fallback selector
            try:
                away_team = driver.find_element(By.XPATH, "//div[@class='odds-header']//span[2]").text
            except:
                pass
        
        match_info['home_team'] = home_team if home_team else 'N/A'
        match_info['away_team'] = away_team if away_team else 'N/A'
        
    except Exception:
        match_info['home_team'] = 'N/A'
        match_info['away_team'] = 'N/A'

    # 날짜 추출 (더 관대한 대기)
    try:
        time_container = None
        # Try with shorter timeout first
        try:
            time_container = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, XPATH_SELECTORS['time_container']))
            )
        except:
            # Try alternative selector
            try:
                time_container = driver.find_element(By.XPATH, "//div[contains(@class, 'date')]")
            except:
                pass
        
        if time_container:
            date_parts_text = time_container.text.split('\n')
            date_str = f"{date_parts_text[1].strip(',')} {date_parts_text[2]}"
            
            local_dt = datetime.strptime(date_str, DATE_PARSE_FORMAT)
            korea_tz = pytz.timezone(KOREA_TZ)
            korea_dt = korea_tz.localize(local_dt)
            utc_dt = korea_dt.astimezone(pytz.utc)
            match_info['match_date_utc'] = utc_dt.strftime(UTC_FORMAT)
        else:
            match_info['match_date_utc'] = 'N/A'
    except (IndexError, ValueError, AttributeError):
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