from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class ReportBody(BaseModel):
    """기사 본문 정보"""
    header: Optional[List[str]] = Field(description="기사 헤더", default_factory=list)
    sub_header: Optional[List[str]] = Field(alias="sub-header", description="기사 서브 헤더", default_factory=list)
    content: Optional[List[str]] = Field(description="기사 본문 내용", default_factory=list)


class Table(BaseModel):
    """테이블 정보"""
    table_html: str = Field(description="테이블 HTML")

class Report(BaseModel):
    """개별 기사 정보"""
    title: str = Field(description="기사 제목")
    date: str = Field(description="기사 날짜")
    url: str = Field(description="기사 URL")
    body: ReportBody = Field(description="기사 본문")
    tables: List[Table] = Field(description="기사 내 테이블 데이터", default_factory=list)


class PressData(BaseModel):
    """인천공항 관련 기사 데이터"""
    total_count: int = Field(description="총 기사 수")
    reports: List[Report] = Field(alias="articles", description="기사 목록")


def load_press_data_from_file(file_path: str) -> PressData:
    """
    JSON 파일에서 기사 데이터를 로드합니다.
    
    Args:
        file_path (str): JSON 파일 경로
        
    Returns:
        PressData: 로드된 기사 데이터
        
    Raises:
        FileNotFoundError: 파일을 찾을 수 없는 경우
        ValueError: JSON 파싱 오류가 있는 경우
    """
    import json
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        # Pydantic 모델로 검증 및 변환
        press_data = PressData(**data)
        return press_data
        
    except FileNotFoundError:
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON 파싱 오류: {e}")
    except Exception as e:
        raise ValueError(f"데이터 로드 오류: {e}")


# 사용 예시
if __name__ == "__main__":
    # 파일에서 데이터 로드
    try:
        press_data = load_press_data_from_file("incheon_press.json")
        print(f"총 {press_data.total_count}개의 기사를 로드했습니다.")
        print(f"크롤링 시간: {press_data.crawled_at}")
        
        # 첫 번째 기사 정보 출력
        if press_data.articles:
            first_article = press_data.articles[0]
            print(f"\n첫 번째 기사:")
            print(f"제목: {first_article.title}")
            print(f"날짜: {first_article.date}")
            print(f"URL: {first_article.url}")
            print(f"헤더: {first_article.body.header}")
            print(f"서브헤더: {first_article.body.sub_header}")
            print(f"본문 길이: {len(first_article.body.content)} 문단")
            print(f"테이블 수: {len(first_article.tables)}개")
            
    except Exception as e:
        print(f"오류 발생: {e}")
