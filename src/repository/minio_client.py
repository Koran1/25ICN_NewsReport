import os
from minio import Minio
from minio.error import S3Error
from datetime import datetime

from configuration.config import Config
from logger.logger import get_logger, setup_logging

class MinioClient:
    def __init__(self, config: Config):
        """
        MinioClient 클래스의 생성자입니다.
        MinIO 클라이언트를 초기화합니다.

        :param config: MinIO 설정 객체
        """
        self.config = config.get_minio_config()
        self.logger = get_logger(__name__)
        try:
            self.client = Minio(
                self.config.host + ":" + str(self.config.port),
                access_key=self.config.access_key,
                secret_key=self.config.secret_key,
                secure=self.config.secure
            )
            self.logger.info("MinIO client initialized successfully.")

            # 버킷이 존재하는지 확인하고, 없으면 생성
            bucket_name = self.config.bucket
            found = self.client.bucket_exists(bucket_name)
            if not found:
                self.client.make_bucket(bucket_name)
                self.logger.info(f"Bucket '{bucket_name}' created.")
            else:
                self.logger.info(f"Bucket '{bucket_name}' already exists.")
        except Exception as e:
            self.logger.error(f"Error initializing MinIO client: {e}")
            self.client = None

    def upload_file(self, file_path: str, bucket_name: str = None):
        """
        지정된 파일을 MinIO 버킷에 업로드합니다.

        :param file_path: 업로드할 파일의 로컬 경로
        :param bucket_name: 업로드할 버킷 이름
        """
        if not self.client:
            self.logger.error("MinIO client is not initialized. Aborting upload.")
            return

        if bucket_name is None or bucket_name == "":
            bucket_name = self.config.bucket
            # 버킷이 존재하는지 확인하고, 없으면 생성
            try:
                found = self.client.bucket_exists(bucket_name)
                if not found:
                    self.client.make_bucket(bucket_name)
                    self.logger.info(f"Bucket '{bucket_name}' created.")
                else:
                    self.logger.info(f"Bucket '{bucket_name}' already exists.")
            except S3Error as exc:
                self.logger.error("Error checking for bucket: %s", exc)
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
            self.logger.info(
                f"'{file_path}' is successfully uploaded as "
                f"'{object_name}' to bucket '{bucket_name}'."
            )
        except S3Error as exc:
            self.logger.error("Error occurred during upload: %s", exc)

if __name__ == "__main__":
    # MinIO Uploader 인스턴스 생성
    from configuration.config import MinIOConfig
    minio_config = MinIOConfig()
    minio_config.host = "192.168.109.254"
    minio_config.port = 31345
    minio_config.access_key = "root"
    minio_config.secret_key = "biris.manse"
    minio_config.secure = False  # http를 사용하는 경우 False로 설정

    config = Config()
    config.minio = minio_config

    setup_logging(config)
    minio_uploader = MinioClient(config)

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
