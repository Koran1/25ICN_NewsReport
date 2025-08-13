from bs4 import BeautifulSoup
from typing import Dict, List, Union
import json


def parse_html_table(html_content: str) -> Dict[str, Union[List[str], List[List[str]]]]:
    """
    HTML 테이블을 파싱해서 header와 row 데이터를 추출합니다.
    
    Args:
        html_content (str): HTML 문자열
        
    Returns:
        Dict[str, Union[List[str], List[List[str]]]]: 
            - header: 테이블 헤더 리스트
            - row: 테이블 행 데이터 리스트
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 테이블 찾기
    table = soup.find('table')
    if not table:
        return {"header": [], "row": []}
    
    # 병합 셀(colspan/rowspan) 확장을 포함한 정규화
    thead = table.find('thead')
    tbody = table.find('tbody')

    def normalize_rows(tr_elements) -> List[List[str]]:
        grid: List[List[str]] = []
        for row_index, tr in enumerate(tr_elements):
            # 해당 row가 이미 이전 rowspan 확장으로 채워졌을 수 있으므로 보장
            while len(grid) <= row_index:
                grid.append([])

            current_row = grid[row_index]

            # 현재 행에서 사용할 시작 열 인덱스는 비어있는 첫 칸부터
            def next_free_col(start_col: int) -> int:
                col = start_col
                while col < len(current_row) and current_row[col] != "":
                    col += 1
                return col

            col_index = next_free_col(0)

            cells = tr.find_all(['th', 'td'])
            for cell in cells:
                content = extract_cell_content(cell)
                colspan = int(cell.get('colspan', 1) or 1)
                rowspan = int(cell.get('rowspan', 1) or 1)

                # 다음 사용 가능한 컬럼부터 배치
                col_index = next_free_col(col_index)

                # 현재 행 길이 보장
                if len(current_row) < col_index + colspan:
                    current_row.extend([""] * (col_index + colspan - len(current_row)))

                # rowspan/colspan 확장하여 동일 내용 채우기
                for r_offset in range(rowspan):
                    target_row_index = row_index + r_offset
                    while len(grid) <= target_row_index:
                        grid.append([])
                    target_row = grid[target_row_index]
                    if len(target_row) < col_index + colspan:
                        target_row.extend([""] * (col_index + colspan - len(target_row)))

                    for c in range(col_index, col_index + colspan):
                        if target_row[c] == "":
                            target_row[c] = content

                # 다음 셀 위치로 이동
                col_index = col_index + colspan

        return grid

    header: List[str] = []
    rows: List[List[str]] = []

    if thead:
        thead_trs = thead.find_all('tr')
        header_grid = normalize_rows(thead_trs)
        if header_grid:
            header = header_grid[0]

        # 본문 행들 수집: tbody가 있으면 tbody만, 없으면 thead 제외 나머지 tr
        if tbody:
            body_trs = tbody.find_all('tr')
        else:
            all_trs = table.find_all('tr')
            body_trs = [tr for tr in all_trs if tr.find_parent('thead') is None]
        # 헤더가 다단인 경우(두 번째 헤더 행들)를 rows의 선두에 포함
        rows = header_grid[1:] if len(header_grid) > 1 else []
        rows.extend(normalize_rows(body_trs))
    else:
        # thead가 없으면 모든 tr을 정규화 후 첫 행을 헤더로 사용
        all_trs = table.find_all('tr')
        grid = normalize_rows(all_trs)
        if grid:
            header = grid[0]
            rows = grid[1:]

    return {"header": header, "row": rows}


def extract_cell_content(cell) -> str:
    """
    테이블 셀의 내용을 추출합니다. 텍스트와 이미지 정보를 포함합니다.
    
    Args:
        cell: BeautifulSoup 셀 요소
        
    Returns:
        str: 추출된 셀 내용
    """
    content_parts = []
    
    # 이미지 정보 추출
    images = cell.find_all('img')
    for img in images:
        src = img.get('src', '')
        alt = img.get('alt', '')
        title = img.get('title', '')
        
        if src:
            if alt and alt != '.':
                content_parts.append(f"[이미지: {alt}]")
            elif title:
                content_parts.append(f"[이미지: {title}]")
            else:
                content_parts.append("[이미지]")
    
    # 텍스트 내용 추출
    text_content = cell.get_text(strip=True)
    if text_content:
        content_parts.append(text_content)
    
    # 내용이 없는 경우 빈 문자열 반환
    if not content_parts:
        return ""
    
    return " ".join(content_parts)


def parse_html_table_from_file(file_path: str) -> Dict[str, Union[List[str], List[List[str]]]]:
    """
    HTML 파일에서 테이블을 파싱합니다.
    
    Args:
        file_path (str): HTML 파일 경로
        
    Returns:
        Dict[str, Union[List[str], List[List[str]]]]: 파싱된 테이블 데이터
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            html_content = file.read()
        return parse_html_table(html_content)
    except Exception as e:
        print(f"파일 읽기 오류: {e}")
        return {"header": [], "row": []}


def save_table_to_json(table_data: Dict[str, Union[List[str], List[List[str]]]], 
                      output_file: str) -> None:
    """
    테이블 데이터를 JSON 파일로 저장합니다.
    
    Args:
        table_data (Dict): 파싱된 테이블 데이터
        output_file (str): 출력 JSON 파일 경로
    """
    try:
        with open(output_file, 'w', encoding='utf-8') as file:
            json.dump(table_data, file, ensure_ascii=False, indent=2)
        print(f"테이블 데이터가 {output_file}에 저장되었습니다.")
    except Exception as e:
        print(f"JSON 저장 오류: {e}")


def process_bodydata_folder(bodydata_path: str = "bodydata") -> None:
    """
    bodydata 폴더의 모든 HTML 파일을 처리해서 테이블을 파싱하고 JSON 파일로 저장합니다.
    
    Args:
        bodydata_path (str): bodydata 폴더 경로
    """
    import os
    import glob
    
    # HTML 파일들 찾기
    html_files = glob.glob(os.path.join(bodydata_path, "*.html"))
    
    if not html_files:
        print(f"{bodydata_path} 폴더에서 HTML 파일을 찾을 수 없습니다.")
        return
    
    print(f"총 {len(html_files)}개의 HTML 파일을 처리합니다...")
    
    for html_file in html_files:
        print(f"\n처리 중: {os.path.basename(html_file)}")
        
        # HTML 파일에서 테이블 파싱
        table_data = parse_html_table_from_file(html_file)
        
        if not table_data["header"] and not table_data["row"]:
            print("  - 테이블을 찾을 수 없습니다.")
            continue
        
        # 출력 JSON 파일명 생성 (HTML 파일명에서 확장자 제거)
        base_name = os.path.splitext(os.path.basename(html_file))[0]
        json_filename = f"{base_name}.json"
        
        # JSON 파일로 저장
        save_table_to_json(table_data, json_filename)
        print(f"  - {len(table_data['row'])}개 행의 테이블 데이터를 {json_filename}에 저장했습니다.")


def create_complex_merged_table_html() -> str:
    """
    복잡한 병합 케이스 (rowspan=2, colspan=2, colspan=2) 를 포함한 예제 테이블을 생성합니다.
    구조:
    | rowspan2 | colspan2 | colspan2 |
    |          |  col  col|  col  col|
    | data data data data data |
    """
    return """
    <table border="1">
        <thead>
            <tr>
                <th rowspan="2">고정열</th>
                <th colspan="2">그룹A</th>
                <th colspan="2">그룹B</th>
            </tr>
            <tr>
                <th>컬럼A1</th>
                <th>컬럼A2</th>
                <th>컬럼B1</th>
                <th>컬럼B2</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>행1-고정</td>
                <td>행1-A1</td>
                <td>행1-A2</td>
                <td>행1-B1</td>
                <td>행1-B2</td>
            </tr>
            <tr>
                <td>행2-고정</td>
                <td>행2-A1</td>
                <td>행2-A2</td>
                <td>행2-B1</td>
                <td>행2-B2</td>
            </tr>
        </tbody>
    </table>
    """


def create_body_rowspan_colspan_html() -> str:
    """
    tbody 내부에 rowspan=2, colspan=2가 동시에 존재하는 예제 테이블을 생성합니다.
    기대 정규화 결과:
    Row1: ["공통", "공통", "r1c3", "r1c4"]
    Row2: ["공통", "공통", "r2c3", "r2c4"]
    """
    return """
    <table border=\"1\">
        <thead>
            <tr>
                <th>c1</th>
                <th>c2</th>
                <th>c3</th>
                <th>c4</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td rowspan=\"2\" colspan=\"2\">공통</td>
                <td>r1c3</td>
                <td>r1c4</td>
            </tr>
            <tr>
                <td>r2c3</td>
                <td>r2c4</td>
            </tr>
        </tbody>
    </table>
    """


# 사용 예시
if __name__ == "__main__":
    # bodydata 폴더의 모든 HTML 파일 처리
    print("=== bodydata 폴더 HTML 파일 테이블 파싱 시작 ===")
    process_bodydata_folder()
    
    print("\n=== 복합 병합 테이블 테스트 ===")
    complex_html = create_complex_merged_table_html()
    complex_result = parse_html_table(complex_html)
    print(json.dumps(complex_result, ensure_ascii=False, indent=2))
    expected_header = [
        "고정열", "그룹A", "그룹A", "그룹B", "그룹B"
    ]
    expected_rows_head = [
        ["고정열", "컬럼A1", "컬럼A2", "컬럼B1", "컬럼B2"]
    ]
    expected_rows_body = [
        ["행1-고정", "행1-A1", "행1-A2", "행1-B1", "행1-B2"],
        ["행2-고정", "행2-A1", "행2-A2", "행2-B1", "행2-B2"]
    ]
    # rows는 다단 헤더의 2번째 행이 선두에 포함되므로 이를 분리하여 검증
    head_ok = complex_result["row"][:1] == expected_rows_head
    body_ok = complex_result["row"][1:] == expected_rows_body
    header_ok = complex_result["header"] == expected_header
    print(f"검증 - header:{header_ok}, head-row:{head_ok}, body:{body_ok}")

    print("\n=== tbody 내 rowspan/colspan 동시 테스트 ===")
    body_rc_html = create_body_rowspan_colspan_html()
    body_rc_result = parse_html_table(body_rc_html)
    print(json.dumps(body_rc_result, ensure_ascii=False, indent=2))
    expected_header_body_rc = ["c1", "c2", "c3", "c4"]
    expected_rows_body_rc = [
        ["공통", "공통", "r1c3", "r1c4"],
        ["공통", "공통", "r2c3", "r2c4"]
    ]
    header_ok_body_rc = body_rc_result["header"] == expected_header_body_rc
    rows_ok_body_rc = body_rc_result["row"] == expected_rows_body_rc
    print(f"검증 - header:{header_ok_body_rc}, rows:{rows_ok_body_rc}")

    print("\n=== 샘플 HTML 테이블 파싱 테스트 ===")
    # HTML 문자열 예시
    sample_html = """
    <table>
        <thead>
            <tr>
                <th>이름</th>
                <th>나이</th>
                <th>직업</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>김철수</td>
                <td>25</td>
                <td>개발자</td>
            </tr>
            <tr>
                <td>이영희</td>
                <td>30</td>
                <td>디자이너</td>
            </tr>
        </tbody>
    </table>
    """
    
    # 테이블 파싱
    result = parse_html_table(sample_html)
    print("파싱 결과:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    # JSON 파일로 저장
    save_table_to_json(result, "parsed_table.json")
