"""
GetOdd - Odds data scraper package

A modular web scraping tool for collecting sports betting odds data
from multiple sources with parallel processing support.
"""

__version__ = "1.0.0"
__author__ = "GetOdd Team"

# Import key functions for external use
from .scraper import scrape_match_and_odds, create_driver
from .processor import process_csv_file, process_url_batch
from .parser import parse_url_for_info
from .utils import setup_logging, find_csv_files

__all__ = [
    'scrape_match_and_odds',
    'create_driver',
    'process_csv_file',
    'process_url_batch',
    'parse_url_for_info',
    'setup_logging',
    'find_csv_files',
]