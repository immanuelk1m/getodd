"""
Processing logic for CSV files and parallel execution
"""

import time
import pandas as pd
from pathlib import Path
from typing import List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

from .config import CSV_COLUMNS, CSV_ENCODING, WAIT_DELAY
from .scraper import create_driver, scrape_match_and_odds_with_driver, scrape_match_and_odds


def process_url_batch(urls_batch: List[str], worker_id: int, handicaps: List[str], 
                      logger: logging.Logger, headless: bool = True) -> Tuple[List, List]:
    """
    Worker function to process a batch of URLs in a single browser instance
    
    Args:
        urls_batch: URL 리스트
        worker_id: 워커 ID
        handicaps: 핸디캡 리스트
        logger: Logger 인스턴스
        headless: 헤드리스 모드 여부
        
    Returns:
        (결과 리스트, 실패한 URL 리스트) 튜플
    """
    results = []
    failed_urls = []
    driver = None
    
    try:
        driver = create_driver(headless)
        logger.info(f"Worker {worker_id}: Processing {len(urls_batch)} URLs")
        
        for idx, url in enumerate(urls_batch):
            retry_count = 0
            max_retries = 3
            success = False
            
            while retry_count < max_retries and not success:
                try:
                    logger.info(f"  Worker {worker_id} [{idx+1}/{len(urls_batch)}]: {url}")
                    if retry_count > 0:
                        logger.info(f"    Retry attempt {retry_count}/{max_retries}")
                    
                    result = scrape_match_and_odds_with_driver(driver, url, handicaps)
                    results.extend(result)
                    logger.info(f"    ✓ Worker {worker_id}: Collected {len(result)} entries")
                    success = True
                    time.sleep(WAIT_DELAY)  # Small delay between requests
                    
                except Exception as e:
                    retry_count += 1
                    error_msg = str(e)
                    
                    if retry_count < max_retries:
                        logger.warning(f"    ⚠ Worker {worker_id}: Attempt {retry_count} failed - {error_msg[:100]}")
                        time.sleep(2 * retry_count)  # Exponential backoff
                        
                        # 드라이버 재시작 (심각한 오류의 경우)
                        if "Stacktrace" in error_msg or "chrome not reachable" in error_msg.lower():
                            try:
                                driver.quit()
                                logger.info(f"    Worker {worker_id}: Restarting browser...")
                                driver = create_driver(headless)
                            except:
                                pass
                    else:
                        logger.error(f"    ✗ Worker {worker_id}: Failed after {max_retries} attempts")
                        failed_urls.append({'url': url, 'error': error_msg[:200], 'worker_id': worker_id})
    finally:
        if driver:
            driver.quit()
            logger.info(f"Worker {worker_id}: Browser closed")
    
    return results, failed_urls


def process_csv_file(csv_file: Path, handicaps: List[str], output_dir: Path, 
                     logger: logging.Logger, headless: bool = True, 
                     num_workers: int = 1) -> Tuple[List, List]:
    """
    단일 CSV 파일 처리 (병렬 처리 지원)
    
    Args:
        csv_file: CSV 파일 경로
        handicaps: 핸디캡 리스트
        output_dir: 출력 디렉토리
        logger: Logger 인스턴스
        headless: 헤드리스 모드 여부
        num_workers: 병렬 워커 수
        
    Returns:
        (전체 결과 리스트, 실패한 URL 리스트) 튜플
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


def save_results_to_csv(results: List, output_file: Path, logger: logging.Logger = None):
    """
    결과를 CSV 파일로 저장
    
    Args:
        results: 저장할 데이터 리스트
        output_file: 출력 파일 경로
        logger: Logger 인스턴스 (optional)
    """
    if results:
        df = pd.DataFrame(results, columns=CSV_COLUMNS)
        df.to_csv(output_file, index=False, encoding=CSV_ENCODING)
        if logger:
            logger.info(f"  Saved {len(results)} entries to {output_file}")


def merge_partial_results(output_dir: Path, partial_file: str, final_file: str, 
                         logger: logging.Logger = None):
    """
    부분 결과 파일들을 최종 파일로 병합
    
    Args:
        output_dir: 출력 디렉토리
        partial_file: 부분 파일명
        final_file: 최종 파일명
        logger: Logger 인스턴스 (optional)
    """
    partial_path = output_dir / partial_file
    final_path = output_dir / final_file
    
    if partial_path.exists():
        df_partial = pd.read_csv(partial_path)
        if final_path.exists():
            df_final = pd.read_csv(final_path)
            df_combined = pd.concat([df_final, df_partial], ignore_index=True)
        else:
            df_combined = df_partial
            
        df_combined.to_csv(final_path, index=False, encoding=CSV_ENCODING)
        partial_path.unlink()  # 부분 파일 삭제
        
        if logger:
            logger.info(f"Merged partial results into {final_path}")