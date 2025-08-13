import json
import pandas as pd
from datetime import datetime

def create_excel_from_json():
    """JSON 파일의 데이터를 읽어서 Excel 파일을 생성합니다."""
    
    # JSON 파일 읽기
    try:
        with open('document_analysis.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        print("JSON 파일을 성공적으로 읽었습니다.")
    except FileNotFoundError:
        print("document_analysis.json 파일을 찾을 수 없습니다.")
        return
    except json.JSONDecodeError:
        print("JSON 파일 형식이 올바르지 않습니다.")
        return
    
    # 분석된 파일들 가져오기
    analyzed_files = data.get('analyzed_files', [])
    
    if not analyzed_files:
        print("분석된 파일 데이터가 없습니다.")
        return
    
    print(f"총 {len(analyzed_files)}개의 파일 데이터를 처리합니다.")
    
    # 필요한 컬럼만 추출하여 DataFrame 생성
    excel_data = []
    
    for file_info in analyzed_files:
        excel_data.append({
            'filename': file_info.get('filename', ''),
            'date': file_info.get('date', ''),
            'title': file_info.get('title', '')
        })
    
    # DataFrame 생성
    df = pd.DataFrame(excel_data)
    
    # 날짜순으로 정렬 (날짜가 있는 경우만)
    df_with_date = df[df['date'] != ''].copy()
    df_without_date = df[df['date'] == ''].copy()
    
    # 날짜가 있는 파일들을 날짜순으로 정렬
    if not df_with_date.empty:
        df_with_date['date'] = pd.to_datetime(df_with_date['date'])
        df_with_date = df_with_date.sort_values('date')
        df_with_date['date'] = df_with_date['date'].dt.strftime('%Y-%m-%d')
    
    # 최종 DataFrame 생성 (날짜순 정렬된 파일들 + 날짜가 없는 파일들)
    final_df = pd.concat([df_with_date, df_without_date], ignore_index=True)
    
    # Excel 파일로 저장
    output_filename = '문서_특징_정리.xlsx'
    
    try:
        with pd.ExcelWriter(output_filename, engine='openpyxl') as writer:
            # 메인 데이터 시트
            final_df.to_excel(writer, sheet_name='문서목록', index=False)
            
            # 요약 정보 시트
            summary_data = {
                '항목': ['총 파일 수', '날짜 추출 가능', '날짜 추출 불가'],
                '수량': [
                    len(final_df),
                    len(df_with_date),
                    len(df_without_date)
                ]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='요약정보', index=False)
        
        print(f"Excel 파일이 성공적으로 생성되었습니다: {output_filename}")
        print(f"날짜 추출 가능: {len(df_with_date)}개")
        print(f"날짜 추출 불가: {len(df_without_date)}개")
        
        # 날짜가 없는 파일들 출력
        if not df_without_date.empty:
            print("\n날짜를 추출할 수 없는 파일들:")
            for _, row in df_without_date.iterrows():
                print(f"  - {row['filename']}")
        
    except Exception as e:
        print(f"Excel 파일 생성 중 오류가 발생했습니다: {e}")

if __name__ == "__main__":
    create_excel_from_json()
