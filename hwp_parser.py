import copy
import io
import json, requests, zipfile
import time
import os
import glob

base_url = "http://192.168.101.20:9892"
SEND_URL = f"{base_url}/parse"
STATUS_URL = f"{base_url}/status?task_id="
LOAD_URL = f"{base_url}/load?task_id="

def get_hwp_files():
    """raw 폴더에서 HWP 파일들을 가져옵니다."""
    raw_dir = "raw"
    hwp_files = glob.glob(os.path.join(raw_dir, "*.hwp"))
    return hwp_files

def process_hwp_file(file_path):
    """단일 HWP 파일을 처리합니다."""
    print(f"처리 중: {os.path.basename(file_path)}")
    
    try:
        # 파일 크기 확인
        file_size = os.path.getsize(file_path)
        print(f"  파일 크기: {file_size:,} bytes")
        
        # 파일을 binary 모드로 열어서 업로드
        with open(file_path, 'rb') as f:
            # 파일 내용을 메모리에 로드
            file_content = f.read()
            print(f"  파일 읽기 완료: {len(file_content):,} bytes")
            
            files = {'file': (os.path.basename(file_path), file_content, 'application/octet-stream')}
            
            print(f"  API 서버로 업로드 중...")
            res = requests.post(url=SEND_URL, files=files)
            content = json.loads(res.content.decode("utf-8"))

            if "message" in content.keys(): 
                # 작업 요청 시 에러 발생 시, response json에 message 키 존재함.
                # message에 에러 메세지 존재
                raise RuntimeError(content["message"])

            task_uuid = content["task_uuid"]
            print(f"  작업 ID: {task_uuid}")

            # 작업 상태 확인
            while True:
                check_status = requests.get(url=STATUS_URL+task_uuid)
                check_status = json.loads(check_status.content.decode("utf-8"))
                task_status = check_status["status"]
                
                if task_status == "SUCCESS" or task_status == "FAILURE":
                    break
                
                time.sleep(0.5)

            if task_status == "FAILURE":
                print(f"  작업 실패: {os.path.basename(file_path)}")
                return None

            print(f"  결과 다운로드 중...")
            # 결과 다운로드
            final_res = requests.get(url=LOAD_URL+task_uuid)
            
            # ZIP 파일 처리
            zip_content = io.BytesIO(final_res.content)
            zip_content_cp = copy.copy(zip_content)
            zip_archive = zipfile.ZipFile(zip_content_cp)

            json_zip_file = [zip_name for zip_name in zip_archive.filelist if "text.json" in zip_name.filename][0]
            json_path = zip_archive.extract(json_zip_file)

            del zip_content_cp

            # JSON 결과 읽기
            results = json.load(open(json_path, "r", encoding="utf-8-sig"))
            
            # 임시 파일 정리
            os.remove(json_path)
            
            print(f"  처리 완료: {os.path.basename(file_path)}")
            return results
            
    except Exception as e:
        print(f"  오류 발생 ({os.path.basename(file_path)}): {e}")
        return None

def main():
    """메인 함수: 모든 HWP 파일을 처리합니다."""
    hwp_files = get_hwp_files()
    
    if not hwp_files:
        print("raw 폴더에서 HWP 파일을 찾을 수 없습니다.")
        return
    
    print(f"총 {len(hwp_files)}개의 HWP 파일을 처리합니다.")
    
    results = []
    
    for file_path in hwp_files:
        result = process_hwp_file(file_path)
        if result:
            results.append({
                'filename': os.path.basename(file_path),
                'result': result
            })
    
    # 결과를 JSON 파일로 저장
    if results:
        output_file = "hwp_parse_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n처리 결과가 {output_file}에 저장되었습니다.")
        print(f"성공적으로 처리된 파일: {len(results)}개")
    else:
        print("\n처리된 파일이 없습니다.")

if __name__ == "__main__":
    main()