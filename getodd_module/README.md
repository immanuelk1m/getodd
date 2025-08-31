# GetOdd Module - Modularized Odds Scraper

## Module Structure

```
getodd_module/
├── __init__.py       # Package initialization
├── __main__.py       # Entry point for module execution
├── config.py         # Configuration settings and constants
├── utils.py          # Utility functions (logging, file operations)
├── parser.py         # URL parsing functions
├── scraper.py        # Core scraping logic
├── processor.py      # CSV processing and parallel execution
└── main.py           # CLI entry point
```

## Usage

### Run as a module
```bash
python -m getodd_module [options]
```

### Run using the runner script
```bash
python run_scraper.py [options]
```

### Import in Python code
```python
from getodd_module import scrape_match_and_odds, process_csv_file

# Scrape single URL
results = scrape_match_and_odds(url, ['+2.5', '+3'], headless=True)

# Process CSV file
results, failed = process_csv_file(csv_path, handicaps, output_dir, logger)
```

## Command Line Options

- `--input-dir`: Directory containing CSV files (default: match_urls_complete/by_league/)
- `--output-dir`: Directory for output files (default: odds_data_output/)
- `--handicaps`: Comma-separated handicap values (default: +2.5,+3,+3.5)
- `--batch-size`: Number of URLs to process before saving (default: 10)
- `--workers`: Number of parallel browser instances (default: 1)
- `--resume`: Resume from last processed file
- `--no-headless`: Run browser in visible mode
- `--test`: Test mode using test.csv

## Examples

### Test with sample data
```bash
python -m getodd_module --test --workers 3
```

### Process all CSV files with parallel workers
```bash
python -m getodd_module --workers 5 --handicaps "+2.5,+3,+3.5"
```

### Resume interrupted processing
```bash
python -m getodd_module --resume --workers 10
```

## Module Details

### config.py
- Browser settings (user agent, timeouts)
- Default CLI arguments
- XPath selectors for web scraping
- Output file configurations

### utils.py
- `setup_logging()`: Configure logging
- `find_csv_files()`: Discover CSV files
- `load_checkpoint()`: Load progress data
- `save_checkpoint()`: Save progress data

### parser.py
- `parse_url_for_info()`: Extract league and season from URL

### scraper.py
- `create_driver()`: Create Selenium WebDriver
- `scrape_match_and_odds()`: Main scraping function
- `extract_match_info()`: Extract match details
- `extract_odds_for_handicap()`: Extract odds data

### processor.py
- `process_url_batch()`: Worker function for parallel processing
- `process_csv_file()`: Process single CSV with optional parallelism
- `save_results_to_csv()`: Save data to CSV files

### main.py
- CLI argument parsing
- Main orchestration logic
- Checkpoint management
- Progress tracking