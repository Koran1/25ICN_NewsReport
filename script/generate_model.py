import argparse
import json
import os
from pathlib import Path
from datamodel_code_generator import generate, InputFileType

def generate_code_from_schema(schema_dir: str, output_prefix: str = None):
    """
    지정된 디렉토리와 모든 하위 디렉토리에서 JSON 스키마 파일을 스캔하여 
    Python 모델을 생성합니다.
    스키마 파일 내의 'x-python-package'와 'x-python-class-name' 메타데이터를 사용하여
    출력 경로와 클래스 이름을 결정합니다.
    """
    schema_path = Path(schema_dir)
    if not schema_path.is_dir():
        print(f"오류: '{schema_dir}'에서 디렉토리를 찾을 수 없습니다.")
        return

    print(f"'{schema_dir}' 디렉토리와 하위 디렉토리에서 스키마를 찾는 중...")
    for schema_file in schema_path.rglob("*.json"):
        print(f"파일 처리 중: {schema_file}...")
        try:
            with open(schema_file, "r", encoding="utf-8") as f:
                schema_data = json.load(f)

            package_path_str = schema_data.get("x-python-package")
            class_name = schema_data.get("x-python-class-name")

            if not package_path_str or not class_name:
                print(f"  '{schema_file}' 건너뛰기: 'x-python-package' 또는 'x-python-class-name'을 찾을 수 없습니다.")
                continue

            # 패키지 경로를 디렉토리 경로로 변환
            # e.g., "new_report.schema.entity" -> "new_report/schema/entity"
            output_dir_base = Path(package_path_str.replace('.', '/'))
            
            if output_prefix:
                output_dir = Path(output_prefix) / output_dir_base
            else:
                output_dir = output_dir_base

            # 스키마 파일 이름(확장자 제외)을 사용하여 출력 파일 이름 생성
            # e.g., "new_report_entity.json" -> "new_report_entity.py"
            output_file = output_dir / f"{schema_file.stem}.py"

            # 출력 디렉토리가 존재하지 않으면 생성
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # 패키지 디렉토리에 __init__.py 파일 생성
            init_base = Path(output_prefix) if output_prefix else Path('.')
            parts = package_path_str.split('.')
            for i in range(len(parts)):
                init_path = init_base / '/'.join(parts[:i+1]) / '__init__.py'
                init_path.parent.mkdir(parents=True, exist_ok=True)
                init_path.touch(exist_ok=True)

            print(f"  모델 생성 중 -> {output_file}")
            generate(
                input_=schema_file,
                input_file_type=InputFileType.JsonSchema,
                output=output_file,
                class_name=class_name
            )
            print(f"  '{class_name}' 클래스가 '{output_file}'에 성공적으로 생성되었습니다.")

        except json.JSONDecodeError:
            print(f"  '{schema_file}' 건너뛰기: 잘못된 JSON 형식입니다.")
        except Exception as e:
            print(f"  '{schema_file}' 처리 중 오류 발생: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="JSON 스키마로부터 Python 모델을 생성합니다.")
    parser.add_argument(
        "schema_dir",
        type=str,
        help="JSON 스키마 파일이 포함된 디렉토리입니다."
    )
    parser.add_argument(
        "--output-prefix",
        type=str,
        default=None,
        help="생성된 코드의 출력 디렉토리에 대한 접두사입니다."
    )
    args = parser.parse_args()
    generate_code_from_schema(args.schema_dir, args.output_prefix)
