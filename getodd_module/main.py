"""
Main CLI entry point for the odds scraper
"""

import argparse
import pandas as pd
from pathlib import Path

from .config import (
    DEFAULT_HANDICAPS, DEFAULT_INPUT_DIR, DEFAULT_OUTPUT_DIR, 
    DEFAULT_BATCH_SIZE, DEFAULT_WORKERS, CHECKPOINT_FILE,
    COMBINED_ODDS_FILE, COMBINED_ODDS_PARTIAL_FILE, CSV_COLUMNS, CSV_ENCODING
)
from .utils import (
    setup_logging, find_csv_files, load_checkpoint, 
    save_checkpoint, save_failed_urls
)
from .processor import process_csv_file, save_results_to_csv


def parse_arguments():
    """
    Parse command line arguments
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description='Scrape odds data from multiple CSV files containing match URLs'
    )
    parser.add_argument('--input-dir', type=str, default=DEFAULT_INPUT_DIR,
                        help=f'Directory containing CSV files (default: {DEFAULT_INPUT_DIR})')
    parser.add_argument('--output-dir', type=str, default=DEFAULT_OUTPUT_DIR,
                        help=f'Directory for output files (default: {DEFAULT_OUTPUT_DIR})')
    parser.add_argument('--handicaps', type=str, default=DEFAULT_HANDICAPS,
                        help=f'Comma-separated handicap values (default: {DEFAULT_HANDICAPS})')
    parser.add_argument('--batch-size', type=int, default=DEFAULT_BATCH_SIZE,
                        help=f'Number of URLs to process before saving (default: {DEFAULT_BATCH_SIZE})')
    parser.add_argument('--resume', action='store_true',
                        help='Resume from last processed file')
    parser.add_argument('--no-headless', action='store_true',
                        help='Run browser in visible mode (default: headless)')
    parser.add_argument('--test', action='store_true',
                        help='Test mode: process only test.csv')
    parser.add_argument('--workers', type=int, default=DEFAULT_WORKERS,
                        help=f'Number of parallel browser instances (default: {DEFAULT_WORKERS})')
    
    return parser.parse_args()


def main():
    """
    Main function orchestrating the scraping process
    """
    args = parse_arguments()
    
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
    checkpoint_file = output_dir / CHECKPOINT_FILE
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
            save_results_to_csv(results, output_file, logger)
        
        # 실패한 URL 추가
        all_failed_urls.extend(failed_urls)
        
        # 체크포인트 업데이트
        checkpoint_data['processed_files'].append(str(csv_file))
        checkpoint_data['failed_urls'] = all_failed_urls
        save_checkpoint(checkpoint_file, checkpoint_data)
    
    # 실패한 URL 저장
    failed_file = save_failed_urls(output_dir, all_failed_urls)
    if failed_file:
        logger.warning(f"\nFailed URLs saved to {failed_file}")
        logger.warning(f"Total failed: {len(all_failed_urls)}")
    
    logger.info("\n" + "="*50)
    logger.info("Processing completed!")
    logger.info("="*50)


if __name__ == "__main__":
    main()