"""
Utility functions for file operations and logging
"""

import json
import logging
from pathlib import Path
from typing import List, Dict
from .config import LOG_FORMAT, PROCESSING_LOG_FILE


def setup_logging(output_dir: Path) -> logging.Logger:
    """
    로깅 설정
    
    Args:
        output_dir: 로그 파일을 저장할 디렉토리
        
    Returns:
        설정된 Logger 인스턴스
    """
    logger = logging.getLogger('odds_scraper')
    logger.setLevel(logging.INFO)
    
    # 기존 핸들러 제거 (중복 방지)
    logger.handlers.clear()
    
    # 파일 핸들러
    log_file = output_dir / PROCESSING_LOG_FILE
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 포맷터
    formatter = logging.Formatter(LOG_FORMAT)
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


def find_csv_files(input_dir: Path) -> List[Path]:
    """
    입력 디렉토리에서 모든 CSV 파일 찾기
    
    Args:
        input_dir: CSV 파일을 검색할 디렉토리
        
    Returns:
        정렬된 CSV 파일 경로 리스트
    """
    csv_files = list(input_dir.rglob('*.csv'))
    return sorted(csv_files)


def load_checkpoint(checkpoint_file: Path) -> Dict:
    """
    체크포인트 파일 로드
    
    Args:
        checkpoint_file: 체크포인트 파일 경로
        
    Returns:
        체크포인트 데이터 딕셔너리
    """
    if checkpoint_file.exists():
        with open(checkpoint_file, 'r') as f:
            return json.load(f)
    return {'processed_files': [], 'failed_urls': []}


def save_checkpoint(checkpoint_file: Path, checkpoint_data: Dict):
    """
    체크포인트 저장
    
    Args:
        checkpoint_file: 체크포인트 파일 경로
        checkpoint_data: 저장할 체크포인트 데이터
    """
    with open(checkpoint_file, 'w') as f:
        json.dump(checkpoint_data, f, indent=2)


def save_failed_urls(output_dir: Path, failed_urls: List[Dict], filename: str = 'failed_urls.json'):
    """
    실패한 URL 목록 저장
    
    Args:
        output_dir: 출력 디렉토리
        failed_urls: 실패한 URL 정보 리스트
        filename: 저장할 파일명
    """
    if failed_urls:
        failed_file = output_dir / filename
        with open(failed_file, 'w') as f:
            json.dump(failed_urls, f, indent=2)
        return failed_file
    return None