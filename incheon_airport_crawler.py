import time
import json
import re
import base64
import urllib.parse
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

def parse_article(url):
    """상세 페이지 파싱: 제목, 날짜, 본문, 첨부 파일 링크 수집"""
    soup = get_soup(url)
    # 제목
    title = ""
    # 상세 페이지는 상단에 제목 텍스트가 바로 노출됨
    h1 = soup.find(["h1","h2","h3"]) or soup.find("div", class_=re.compile("title|subject"))
    if h1:
        title = h1.get_text(" ", strip=True)
    # 작성일
    date = ""
    meta_text = soup.get_text("\n", strip=True)
    m = re.search(r"작성일\s*([0-9]{4}\.[0-9]{2}\.[0-9]{2})", meta_text)
    if m:
        date = m.group(1)
    # 본문(가장 긴 컨텐츠 영역 추정)
    # 보편적으로 기사 본문은 article, #content, .view 같은 영역. 길이가 가장 긴 텍스트 블록을 선택.
    candidates = []
    for sel in ["article", "#content", ".board", ".view", ".article", ".read", ".cont", ".txt", "body"]:
        for node in soup.select(sel):
            text = node.get_text("\n", strip=True)
            if text:
                candidates.append((len(text), text))
    content = max(candidates, default=(0, ""))[1]

    # 첨부파일 수집 (인천공항 특화 - download.do 링크만 사용)
    attachments = []
    
    # download.do 링크를 통한 첨부파일 수집
    for a in soup.find_all("a", href=True):
        href = a["href"]
        # download.do 링크인 경우 (인천공항 특성상 파일 다운로드 링크)
        if "download.do" in href:
            # 링크 텍스트에서 파일명과 확장자 추출
            link_text = a.get_text(strip=True)
            if link_text and link_text != "미리보기":
                # 파일 확장자 확인
                if re.search(r"\.(hwp|pdf|docx?|xlsx?|pptx?|jpg|jpeg|png|gif|bmp|zip|rar|txt)$", link_text, re.I):
                    # 상대 경로인 경우 절대 경로로 변환
                    if href.startswith('/'):
                        file_url = urljoin(BASE, href)
                    elif href.startswith('http'):
                        file_url = href
                    else:
                        file_url = urljoin(url, href)
                    
                    # 파일명은 링크 텍스트 사용
                    filename = link_text
                    
                    # 중복 제거 (URL 기준)
                    if not any(att["url"] == file_url for att in attachments):
                        attachments.append({
                            "filename": filename,
                            "url": file_url,
                            "type": link_text.split('.')[-1].lower() if '.' in link_text else "unknown"
                        })

    return {
        "title": title or None,
        "date": date or None,
        "url": url,
        "content": content or None,
        "attachments": attachments,
    }

# find_next_page_url 함수 제거 - 더 이상 필요하지 않음

def crawl(max_pages=None, delay=1.0, out_json="incheon_press.json"):
    """
    max_pages: 목록 페이지 몇 쪽까지 순회할지 (None이면 자동으로 모든 페이지 탐색)
    delay: 각 요청 사이 대기(초)
    """
    seen_ids = set()
    articles = []
    current_page = 1

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
    # 옵션 1: 모든 페이지 자동 탐색 (글 항목이 0개가 될 때까지)
    result = crawl(max_pages=None, delay=0.8)
    
    # 옵션 2: 특정 페이지까지만 수집 (예: 10페이지)
    # result = crawl(max_pages=10, delay=0.8)
    
    print(result)
