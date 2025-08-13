import time
import json
import re
import base64
import urllib.parse
import os
from urllib.parse import urljoin, urlparse, parse_qs
import requests
from bs4 import BeautifulSoup

BASE = "https://www.airport.kr"
LIST_URL = "https://www.airport.kr/co_ko/664/subview.do"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; IncheonPressCrawler/1.0; +https://www.example.com/botinfo)"
}

session = requests.Session()
session.headers.update(HEADERS)

def build_subview_url(page: int) -> str:
    """
    인천공항 보도자료 페이지의 URL을 동적으로 생성합니다.
    Base64 인코딩을 사용하여 페이지 번호에 따른 URL을 만듭니다.
    """
    # 1) 내부 실제 리스트 경로 + 쿼리
    inner_path = f"/bbs/co_ko/84/artclList.do?page={page}&findType=&findWord=&findClSeq=&findOpnwrd=&rgsBgndeStr=&rgsEnddeStr=&tempRow=&"
    # 2) 쿼리 부분을 URL-인코딩
    inner_encoded = urllib.parse.quote(inner_path, safe="")
    # 3) 'fnct1|@@|' 접두어 붙이고 Base64 인코딩
    payload = f"fnct1|@@|{inner_encoded}".encode("utf-8")
    enc_b64 = base64.b64encode(payload).decode("utf-8")
    # 4) 최종적으로 enc를 URL-인코딩해서 subview.do에 붙이기
    enc_param = urllib.parse.quote(enc_b64, safe="")
    return f"{LIST_URL}?enc={enc_param}"

def get_soup(url):
    resp = session.get(url, timeout=20)
    resp.raise_for_status()
    # 공공기관 사이트는 대부분 UTF-8. 혹시 모를 인코딩 문제 대비:
    if not resp.encoding or resp.encoding.lower() == "iso-8859-1":
        resp.encoding = resp.apparent_encoding
    return BeautifulSoup(resp.text, "html.parser")

def extract_articles_from_list(soup):
    """목록 페이지에서 (제목, 상세URL) 등 1차 정보를 뽑는다."""
    rows = []
    # 게시글 리스트 영역 찾기
    table = soup.find("div", id=lambda x: x and "bbs" in x.lower()) or soup
    # 제목 링크: /bbs/co_ko/84/{id}/artclView.do
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/bbs/co_ko/84/" in href and href.endswith("/artclView.do"):
            title = a.get_text(strip=True)
            url = urljoin(BASE, href)
            # 같은 링크가 여러 번 나올 수 있어 중복 제거용으로 id 추출
            m = re.search(r"/bbs/co_ko/84/(\d+)/artclView\.do", href)
            art_id = m.group(1) if m else url
            rows.append({"id": art_id, "title": title, "url": url})
    # 중복 제거 (id 기준)
    uniq = {}
    for r in rows:
        uniq[r["id"]] = r
    return list(uniq.values())

def clean_title(title):
    """title에서 작성일, 조회수 정보를 제거하고 실제 제목만 남깁니다."""
    if not title:
        return None
    
    # "작성일", "조회수" 이후의 내용 제거
    patterns = [
        r'\s*작성일\s*\d{4}\.\d{2}\.\d{2}\s*조회수\s*\d+.*$',
        r'\s*작성일\s*\d{4}\.\d{2}\.\d{2}.*$',
        r'\s*조회수\s*\d+.*$'
    ]
    
    cleaned_title = title
    for pattern in patterns:
        cleaned_title = re.sub(pattern, '', cleaned_title, flags=re.IGNORECASE)
    
    return cleaned_title.strip()

def extract_title_from_content(content):
    """content에서 제목을 추출합니다."""
    if not content:
        return None
    
    # content의 첫 번째 줄에서 제목 추출
    lines = content.split('\n')
    if lines:
        first_line = lines[0].strip()
        # "작성일" 이전까지가 제목
        title_match = re.match(r'^(.+?)(?:\s*작성일\s*\d{4}\.\d{2}\.\d{2})', first_line)
        if title_match:
            return clean_title(title_match.group(1).strip())
        else:
            # 작성일 패턴이 없으면 첫 번째 줄 전체를 제목으로
            return clean_title(first_line)
    
    return None

def clean_content(content):
    """content에서 제목, 작성일, 조회수 부분을 제거합니다."""
    if not content:
        return content
    
    lines = content.split('\n')
    cleaned_lines = []
    
    # 작성일, 조회수 관련 라인들을 건너뛰기
    skip_next_line = False
    
    for i, line in enumerate(lines):
        # 작성일, 조회수 라인 건너뛰기
        if line.strip() == '작성일' or line.strip() == '조회수':
            skip_next_line = True
            continue
        
        # 작성일, 조회수 다음 라인 (날짜, 숫자) 건너뛰기
        if skip_next_line:
            skip_next_line = False
            continue
        
        # 날짜 패턴이 있는 라인 건너뛰기
        if re.search(r'^\d{4}\.\d{2}\.\d{2}$', line.strip()):
            continue
        
        # 조회수 숫자 라인 건너뛰기
        if re.search(r'^\d+$', line.strip()) and i > 0 and lines[i-1].strip() == '조회수':
            continue
        
        # 첫 번째 줄에서 제목 부분 제거 (작성일 이전까지)
        if i == 0:
            # "작성일" 이전까지의 제목 부분 제거
            title_end = re.search(r'작성일\s*\d{4}\.\d{2}\.\d{2}', line)
            if title_end:
                # 작성일 이후 내용이 있으면 추가
                remaining = line[title_end.end():].strip()
                if remaining and not re.search(r'조회수\s*\d+', remaining):
                    cleaned_lines.append(remaining)
            else:
                # 작성일 패턴이 없으면 조회수 이후 내용만 추가
                view_count_end = re.search(r'조회수\s*\d+', line)
                if view_count_end:
                    remaining = line[view_count_end.end():].strip()
                    if remaining:
                        cleaned_lines.append(remaining)
        else:
            # 나머지 줄들은 그대로 추가
            cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines).strip()

def parse_body_structure(content_node):
    """본문을 header, sub-header, content로 분류합니다."""
    if not content_node:
        return {"header": None, "sub-header": None, "content": None}
    
    # 전체 텍스트를 먼저 추출
    full_text = content_node.get_text(strip=True)
    
    # header: color가 있는 span, p 태그들 찾기
    header_elements = []
    header_texts = set()  # header 텍스트들을 set으로 관리
    
    for tag in content_node.find_all(['span', 'p']):
        style = tag.get('style', '')
        if 'color:' in style.lower():
            text = tag.get_text(strip=True)
            if text:
                header_elements.append(text)
                header_texts.add(text)
    
    # header 텍스트들을 하나로 합치기
    header_combined = ' '.join(header_elements) if header_elements else ""
    
    # content: 전체 텍스트에서 header 텍스트 제거
    content_text = full_text
    for header_text in header_texts:
        content_text = content_text.replace(header_text, "")
    
    # content 텍스트 정리 (연속된 공백 제거)
    content_text = re.sub(r'\s+', ' ', content_text).strip()
    
    # header와 content를 문장 단위로 분리
    def split_sentences(text):
        if not text:
            return None
        
        # 문장 단위로 분리 (마침표, 느낌표, 물음표 기준)
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences if sentences else None
    
    header_sentences = split_sentences(header_combined)
    content_sentences = split_sentences(content_text)
    
    return {
        "header": header_sentences,
        "sub-header": None,  # sub-header는 null로 설정
        "content": content_sentences
    }

def parse_tables(content_node):
    """테이블 정보를 수집합니다."""
    if not content_node:
        return []
    
    tables = []
    
    for table in content_node.find_all('table'):
        table_data = {
            'table_html': str(table),
            'table_text': table.get_text('\n', strip=True),
            'table_data': []
        }
        
        # 테이블 데이터를 2차원 배열로 변환
        for row in table.find_all('tr'):
            row_data = []
            for cell in row.find_all(['td', 'th']):
                cell_text = cell.get_text(strip=True)
                row_data.append(cell_text)
            if row_data:  # 빈 행은 제외
                table_data['table_data'].append(row_data)
        
        tables.append(table_data)
    
    return tables

def parse_article(url):
    """상세 페이지 파싱: 제목, 날짜, 본문, 첨부 파일 링크 수집"""
    soup = get_soup(url)
    
    # 제목
    title = ""
    h1 = soup.find(["h1","h2","h3"]) or soup.find("div", class_=re.compile("title|subject"))
    if h1:
        title = h1.get_text(" ", strip=True)
    
    # 작성일
    date = ""
    meta_text = soup.get_text("\n", strip=True)
    m = re.search(r"작성일\s*([0-9]{4}\.[0-9]{2}\.[0-9]{2})", meta_text)
    if m:
        date = m.group(1)
    
    # 본문 영역 찾기 - <div class="con">만 사용
    main_content_node = soup.find("div", class_="con")
    
    # body 구조화 (header, sub-header, content 분류)
    body = parse_body_structure(main_content_node) if main_content_node else {"header": None, "sub-header": None, "content": None}
    
    # 테이블 정보 수집
    tables = parse_tables(main_content_node) if main_content_node else []
    
    # 첨부파일 수집
    attachments = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "download.do" in href:
            link_text = a.get_text(strip=True)
            if link_text and link_text != "미리보기":
                if re.search(r"\.(hwp|pdf|docx?|xlsx?|pptx?|jpg|jpeg|png|gif|bmp|zip|rar|txt)$", link_text, re.I):
                    if href.startswith('/'):
                        file_url = urljoin(BASE, href)
                    elif href.startswith('http'):
                        file_url = href
                    else:
                        file_url = urljoin(url, href)
                    
                    filename = link_text
                    if not any(att["url"] == file_url for att in attachments):
                        attachments.append({
                            "filename": filename,
                            "url": file_url,
                            "type": link_text.split('.')[-1].lower() if '.' in link_text else "unknown"
                        })

    # 데이터 정리
    if not title:
        # content가 리스트인 경우 문자열로 변환
        content_text = body.get("content", "")
        if isinstance(content_text, list):
            content_text = '\n'.join(content_text) if content_text else ""
        extracted_title = extract_title_from_content(content_text)
        if extracted_title:
            title = extracted_title
    
    if title:
        title = clean_title(title)
    
    # content 정리는 parse_body_structure에서 이미 처리됨
    # body["content"]는 이미 리스트 형태로 정리되어 있음
    
    return {
        "title": title or None,
        "date": date or None,
        "url": url,
        "body": body,
        "tables": tables,
        "attachments": attachments,
    }


def crawl(max_pages=None, delay=1.0, out_json="incheon_press.json", start_page=1):
    """
    max_pages: 목록 페이지 몇 쪽까지 순회할지 (None이면 자동으로 모든 페이지 탐색)
    delay: 각 요청 사이 대기(초)
    start_page: 시작 페이지 번호 (이어서 크롤링할 때 사용)
    """
    seen_ids = set()
    articles = []
    current_page = start_page
    
    # 1페이지부터 시작하는 경우 기존 데이터 백업
    if start_page == 1 and os.path.exists(out_json):
        backup_filename = f"{out_json}.backup_{time.strftime('%Y%m%d_%H%M%S')}"
        try:
            import shutil
            shutil.copy2(out_json, backup_filename)
            print(f"DEBUG: 기존 데이터 백업 완료: {backup_filename}")
        except Exception as e:
            print(f"DEBUG: 백업 실패: {e}")
    
    # 기존 파일이 있으면 로드해서 이어서 크롤링
    if start_page > 1 and os.path.exists(out_json):
        try:
            with open(out_json, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
                articles = existing_data.get("articles", [])
                # 기존 ID들을 seen_ids에 추가
                for article in articles:
                    if "url" in article:
                        # URL에서 ID 추출
                        m = re.search(r"/bbs/co_ko/84/(\d+)/artclView\.do", article["url"])
                        if m:
                            seen_ids.add(m.group(1))
            print(f"DEBUG: 기존 데이터 로드 완료 - {len(articles)}개 보도자료, {len(seen_ids)}개 ID")
        except Exception as e:
            print(f"DEBUG: 기존 파일 로드 실패: {e}")
            # 실패하면 새로 시작
            articles = []
            seen_ids = set()

    while True:
        # 동적으로 URL 생성
        if current_page == 1:
            page_url = LIST_URL
        else:
            page_url = build_subview_url(current_page)
        
        print(f"DEBUG: {current_page}페이지 크롤링 중... URL: {page_url}")
        
        try:
            soup = get_soup(page_url)
        except Exception as e:
            print(f"DEBUG: {current_page}페이지 접근 실패: {e}")
            break
        
        # 목록에서 글 링크 수집
        items = extract_articles_from_list(soup)
        print(f"DEBUG: {current_page}페이지에서 {len(items)}개 보도자료 발견")
        
        # 글 항목이 0개가 되면 자동 중단
        if not items:
            print(f"DEBUG: {current_page}페이지에 보도자료가 없어서 자동 중단")
            break
            
        # 상세 수집
        for it in items:
            if it["id"] in seen_ids:
                continue
            seen_ids.add(it["id"])
            try:
                data = parse_article(it["url"])
            except Exception as e:
                data = {"title": it["title"], "url": it["url"], "error": str(e)}
            articles.append(data)
            time.sleep(delay)

        # max_pages 제한이 있으면 체크
        if max_pages and current_page >= max_pages:
            print(f"DEBUG: 최대 페이지 수({max_pages})에 도달하여 중단")
            break
            
        current_page += 1
        time.sleep(delay)
        
        print(f"DEBUG: 현재까지 수집된 보도자료: {len(articles)}개")

    # JSON 형식으로 저장
    output_data = {
        "crawled_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_count": len(articles),
        "articles": articles
    }
    
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    return {"count": len(articles), "json": out_json}

if __name__ == "__main__":
    # ===== 크롤링 옵션 설정 =====
    
    # 옵션 1: 1페이지부터 새로 시작 (기존 데이터 백업 후 새로 크롤링)
    # result = crawl(max_pages=None, delay=1.0, start_page=1)
    
    # 옵션 2: 특정 페이지까지만 수집 (예: 10페이지)
    # result = crawl(max_pages=10, delay=0.8, start_page=1)
    
    # 옵션 3: 특정 페이지부터 이어서 크롤링 (기존 데이터 유지)
    # result = crawl(max_pages=None, delay=1.0, start_page=334)
    
    # 옵션 4: 테스트용 (1페이지만)
    result = crawl(max_pages=1, delay=0.5, start_page=1)
    