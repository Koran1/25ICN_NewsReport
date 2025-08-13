import os
from minio import Minio
from minio.error import S3Error
from datetime import datetime

class MinioUploader:
    def __init__(self, endpoint, access_key, secret_key, secure=False):
        """
        MinioUploader 클래스의 생성자입니다.
        MinIO 클라이언트를 초기화합니다.

        :param endpoint: MinIO 서버 주소
        :param access_key: 사용자 ID
        :param secret_key: 사용자 비밀번호
        :param secure: True for https, False for http
        """
        try:
            self.client = Minio(
                endpoint,
                access_key=access_key,
                secret_key=secret_key,
                secure=secure
            )
            print("MinIO client initialized successfully.")
        except Exception as e:
            print(f"Error initializing MinIO client: {e}")
            self.client = None

    def upload_file(self, file_path, bucket_name="new-reports"):
        """
        지정된 파일을 MinIO 버킷에 업로드합니다.

        :param file_path: 업로드할 파일의 로컬 경로
        :param bucket_name: 업로드할 버킷 이름
        """
        if not self.client:
            print("MinIO client is not initialized. Aborting upload.")
            return

        # 버킷이 존재하는지 확인하고, 없으면 생성
        try:
            found = self.client.bucket_exists(bucket_name)
            if not found:
                self.client.make_bucket(bucket_name)
                print(f"Bucket '{bucket_name}' created.")
            else:
                print(f"Bucket '{bucket_name}' already exists.")
        except S3Error as exc:
            print("Error checking for bucket:", exc)
            return

        # 저장될 객체 이름 생성 (년월/파일명)
        current_year_month = datetime.now().strftime("%Y%m")
        file_name = os.path.basename(file_path)
        object_name = f"{current_year_month}/{file_name}"

        # 파일 업로드
        try:
            self.client.fput_object(
                bucket_name, object_name, file_path,
            )
            print(
                f"'{file_path}' is successfully uploaded as "
                f"'{object_name}' to bucket '{bucket_name}'."
            )
        except S3Error as exc:
            print("Error occurred during upload: ", exc)

if __name__ == "__main__":
    # MinIO Uploader 인스턴스 생성
    minio_uploader = MinioUploader(
        "192.168.109.254:31345",
        access_key="root",
        secret_key="biris.manse",
        secure=False  # http를 사용하는 경우 False로 설정
    )

    # 업로더가 성공적으로 초기화되었는지 확인
    if minio_uploader.client:
        # 테스트용 더미 파일 생성
        test_file = "test_upload_file.txt"
        with open(test_file, "w") as f:
            f.write("This is a test file for MinIO upload.")

        # 파일 업로드 메소드 호출
        minio_uploader.upload_file(test_file)

        # 테스트용 파일 삭제
        os.remove(test_file)
