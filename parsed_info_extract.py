import json
import re
from bs4 import BeautifulSoup
from datetime import datetime

def extract_table_info(html_content):
    """HTML 테이블에서 자료배포일, 자료작성일, 담당부서 정보를 추출합니다."""
    
    # BeautifulSoup으로 HTML 파싱
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 테이블의 모든 행(tr)을 찾기
    rows = soup.find_all('tr')
    
    release_date = None
    creation_date = None
    department = None
    
    for row in rows:
        # 행의 모든 셀(td)을 찾기
        cells = row.find_all('td')
        
        for i, cell in enumerate(cells):
            cell_text = cell.get_text(strip=True)
            
            # 자료배포일 찾기
            if '자료배포일' in cell_text:
                # 다음 셀에서 날짜 정보 찾기
                if i + 1 < len(cells):
                    next_cell = cells[i + 1]
                    next_text = next_cell.get_text(strip=True)
                    if next_text and next_text != '자료배포일':
                        release_date = next_text
                        print(f"  자료배포일 발견: {release_date}")
            
            # 자료작성일 찾기
            elif '자료작성일' in cell_text:
                # 다음 셀에서 날짜 정보 찾기
                if i + 1 < len(cells):
                    next_cell = cells[i + 1]
                    next_text = next_cell.get_text(strip=True)
                    if next_text and next_text != '자료작성일':
                        creation_date = next_text
                        print(f"  자료작성일 발견: {creation_date}")
            
            # 담당부서 찾기
            elif '담당부서' in cell_text:
                # 다음 셀에서 부서 정보 찾기
                if i + 1 < len(cells):
                    next_cell = cells[i + 1]
                    next_text = next_cell.get_text(strip=True)
                    if next_text and next_text != '담당부서':
                        department = next_text
                        print(f"  담당부서 발견: {department}")
    
    return {
        'release_date': release_date,
        'creation_date': creation_date,
        'department': department
    }

def extract_text_content_from_all_pages(pages):
    """모든 페이지에서 Text 클래스 항목들을 분석하여 제목, 부제목, 본문을 추출합니다."""
    
    title = None
    subtitle = None
    contents = []
    
    # 페이지 번호를 정렬하여 순서대로 처리
    page_numbers = sorted([int(k) for k in pages.keys() if k != '-1'], key=lambda x: x if x >= 0 else float('inf'))
    
    for page_num in page_numbers:
        page_items = pages.get(str(page_num), [])
        
        for item in page_items:
            if isinstance(item, dict) and item.get('class') == 'Text':
                font = item.get('font', '')
                font_size = item.get('font_size', 0)
                content = item.get('content', '').strip()
                
                if not content:
                    continue
                
                # 제목: HY헤드라인M, 폰트 크기 17.5-22
                if font == 'HY헤드라인M' and 17.5 <= font_size <= 22:
                    if not title:  # 첫 번째로 발견된 제목만 저장
                        title = content
                        print(f"    제목 발견: {content}")
                
                # 부제목: HY헤드라인M, 폰트 크기 13.5-17.5
                elif font == 'HY헤드라인M' and 13.5 <= font_size < 17.5:
                    if not subtitle:  # 첫 번째로 발견된 부제목만 저장
                        subtitle = content
                        print(f"    부제목 발견: {content}")
                
                # 본문: 휴먼명조
                elif font == '휴먼명조':
                    contents.append(content)
    
    # 제목이 여러 줄로 나뉘어 있는 경우 연결
    if title and title.endswith(','):
        # 다음 페이지에서 이어지는 제목 찾기
        for page_num in page_numbers:
            page_items = pages.get(str(page_num), [])
            for item in page_items:
                if (isinstance(item, dict) and item.get('class') == 'Text' and 
                    item.get('font') == 'HY헤드라인M' and 
                    17.5 <= item.get('font_size', 0) <= 22):
                    next_content = item.get('content', '').strip()
                    if next_content and next_content != title:
                        title = title + " " + next_content
                        print(f"    제목 연결: {title}")
                        break
            if title and not title.endswith(','):
                break
    
    # 부제목이 여러 줄로 나뉘어 있는 경우 연결
    if subtitle and subtitle.endswith('…'):
        # 다음 페이지에서 이어지는 부제목 찾기
        for page_num in page_numbers:
            page_items = pages.get(str(page_num), [])
            for item in page_items:
                if (isinstance(item, dict) and item.get('class') == 'Text' and 
                    item.get('font') == 'HY헤드라인M' and 
                    13.5 <= item.get('font_size', 0) < 17.5):
                    next_content = item.get('content', '').strip()
                    if next_content and next_content != subtitle:
                        subtitle = subtitle + " " + next_content
                        print(f"    부제목 연결: {subtitle}")
                        break
            if subtitle and not subtitle.endswith('…'):
                break
    
    return {
        'title': title,
        'subtitle': subtitle,
        'contents': contents
    }

def process_hwp_results():
    """hwp_parse_results.json 파일을 읽어서 필요한 정보를 추출합니다."""
    
    try:
        # JSON 파일 읽기
        with open('hwp_parse_results.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        print("JSON 파일을 성공적으로 읽었습니다.")
    except FileNotFoundError:
        print("hwp_parse_results.json 파일을 찾을 수 없습니다.")
        return
    except json.JSONDecodeError:
        print("JSON 파일 형식이 올바르지 않습니다.")
        return
    
    if not isinstance(data, list):
        print("JSON 데이터가 리스트 형태가 아닙니다.")
        return
    
    print(f"총 {len(data)}개의 문서를 처리합니다.")
    
    extracted_results = []
    
    for i, item in enumerate(data):
        filename = item.get('filename', f'unknown_{i}')
        result = item.get('result', {})
        
        print(f"\n처리 중: {filename}")
        
        # pages에서 key가 "-1"인 항목 찾기 (테이블 정보용)
        pages = result.get('pages', {})
        page_minus_one = pages.get('-1', [])
        
        # HTML에서 정보 추출
        extracted_table_info = {}
        if page_minus_one and isinstance(page_minus_one, list):
            # 리스트에서 table_content가 있는 항목 찾기
            table_content = None
            for page_item in page_minus_one:
                if isinstance(page_item, dict) and 'table_content' in page_item:
                    table_content = page_item['table_content']
                    break
            
            if table_content:
                html_content = table_content.get('html', '')
                if html_content:
                    extracted_table_info = extract_table_info(html_content)
        
        # 모든 페이지에서 Text 클래스 항목들 추출
        extracted_text_info = extract_text_content_from_all_pages(pages)
        
        # 결과 저장
        document_info = {
            'filename': filename,
            'release_date': extracted_table_info.get('release_date'),
            'creation_date': extracted_table_info.get('creation_date'),
            'department': extracted_table_info.get('department'),
            'title': extracted_text_info.get('title'),
            'subtitle': extracted_text_info.get('subtitle'),
            'contents': extracted_text_info.get('contents')
        }
        
        extracted_results.append(document_info)
        
        print(f"  추출 완료: 제목={extracted_text_info.get('title', 'None')}, 부제목={extracted_text_info.get('subtitle', 'None')}, 본문={len(extracted_text_info.get('contents', []))}개")
    
    # 결과를 새로운 JSON 파일로 저장
    if extracted_results:
        output_file = "extracted_document_info.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(extracted_results, f, ensure_ascii=False, indent=2)
        
        print(f"\n추출 결과가 {output_file}에 저장되었습니다.")
        print(f"성공적으로 처리된 문서: {len(extracted_results)}개")
        
        # 요약 정보 출력
        print("\n=== 요약 정보 ===")
        print(f"자료배포일 정보가 있는 문서: {len([r for r in extracted_results if r['release_date']])}개")
        print(f"자료작성일 정보가 있는 문서: {len([r for r in extracted_results if r['creation_date']])}개")
        print(f"담당부서 정보가 있는 문서: {len([r for r in extracted_results if r['department']])}개")
        print(f"제목 정보가 있는 문서: {len([r for r in extracted_results if r['title']])}개")
        print(f"부제목 정보가 있는 문서: {len([r for r in extracted_results if r['subtitle']])}개")
        print(f"본문 내용이 있는 문서: {len([r for r in extracted_results if r['contents']])}개")
        
    else:
        print("\n추출된 정보가 없습니다.")

if __name__ == "__main__":
    process_hwp_results()
