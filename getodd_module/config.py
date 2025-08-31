"""
Configuration settings for the odds scraper
"""

# Browser configuration
BROWSER_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
BROWSER_TIMEOUT = 20
WAIT_DELAY = 0.5
SCROLL_PAUSE = 1
EXPAND_PAUSE = 2

# Default CLI arguments
DEFAULT_HANDICAPS = '+2.5,+3,+3.5'
DEFAULT_INPUT_DIR = 'match_urls_complete/by_league/'
DEFAULT_OUTPUT_DIR = 'odds_data_output/'
DEFAULT_BATCH_SIZE = 10
DEFAULT_WORKERS = 1

# Timezone settings
KOREA_TZ = 'Asia/Seoul'
UTC_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
DATE_PARSE_FORMAT = "%d %b %Y %H:%M"

# Output settings
CSV_ENCODING = 'utf-8-sig'
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'

# File names
CHECKPOINT_FILE = 'checkpoint.json'
COMBINED_ODDS_FILE = 'combined_odds.csv'
COMBINED_ODDS_PARTIAL_FILE = 'combined_odds_partial.csv'
FAILED_URLS_FILE = 'failed_urls.json'
PROCESSING_LOG_FILE = 'processing_log.txt'

# CSV columns
CSV_COLUMNS = [
    'match_date', 
    'home_team', 
    'away_team', 
    'league_name', 
    'season_info', 
    'bookmaker', 
    'odd_type', 
    'odd_value', 
    'match_url'
]

# XPath selectors
XPATH_SELECTORS = {
    'cookie_button': "onetrust-accept-btn-handler",
    'home_team': "//div[@data-testid='game-host']/p",
    'away_team': "//div[@data-testid='game-guest']/p",
    'time_container': "//div[@data-testid='game-time-item']",
    'target_row': "//div[contains(@class, 'h-9') and .//p[normalize-space(.)='Over/Under {}']]",
    'expanded_container': "{}/following-sibling::div[1]",
    'bookmaker_rows': "{}//div[contains(@data-testid, 'expanded-row')]",
    'bookmaker_name': ".//p[contains(@data-testid, 'bookmaker-name')]",
    'odds_text': ".//p[@class='odds-text']"
}