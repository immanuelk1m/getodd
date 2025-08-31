"""
URL parsing functions for extracting league and season information
"""

import re
from typing import Tuple


def parse_url_for_info(url: str) -> Tuple[str, str]:
    """
    URL에서 리그 이름과 시즌 정보를 정규표현식을 사용하여 더 안정적으로 추출하는 함수.
    'league-name-YYYY-YYYY' 와 'league-name-YYYY' 형식을 모두 지원.
    
    Args:
        url: 파싱할 URL
        
    Returns:
        (리그 이름, 시즌 정보) 튜플
    """
    try:
        # URL에서 불필요한 부분 제거
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
        # 예: jupiler-league-2020-2021 또는 allsvenskan-2020
        pattern = re.compile(r'^(.+?)-(\\d{4}(?:-\\d{4})?)$')
        match = pattern.match(league_season_slug)
        
        if match:
            # 그룹 1: 리그 이름 슬러그, 그룹 2: 시즌 정보
            league_name_slug = match.group(1)
            season_info = match.group(2)
            
            # 하이픈을 공백으로 바꾸고 첫 글자 대문자로
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


def extract_match_id(url: str) -> str:
    """
    URL에서 매치 ID 추출
    
    Args:
        url: 매치 URL
        
    Returns:
        매치 ID 또는 'N/A'
    """
    try:
        # URL의 마지막 부분에서 매치 ID 추출
        # 예: https://www.oddsportal.com/.../kalmar-jonkoping-zVSIDrhH/
        match_id = url.rstrip('/').split('-')[-1]
        return match_id if match_id else 'N/A'
    except Exception:
        return 'N/A'