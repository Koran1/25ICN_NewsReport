"""
Main entry point for Smart News application.
Handles configuration loading, logger initialization, and main application logic.
"""

import argparse
import json
from configuration.config import Config
from logger.logger import get_logger, setup_logging
from parser.table_parser import parse_html_table
from repository.pg_client import PostgresClient
from schema.entity.press_article_entity import load_press_data_from_file

class Main:
    def __init__(self, config_path: str = None):
        self.config = self.load_configuration(config_path)
        self.logger_manager = setup_logging(self.config)
        self.logger = get_logger(__name__)
        self.pg_client = None
        self.logger.info("smart-news initialized")
        
    def load_configuration(self, config_path: str = None) -> Config:
        """
        Load application configuration from YAML file.
        
        Args:
            config_path: Path to the configuration file.
        
        Returns:
            Config instance with loaded settings.
            
        Raises:
            FileNotFoundError: If config file doesn't exist.
            Exception: If there's an error loading configuration.
        """
        try:
            config = Config.load_from_file(config_path)
            return config
        except FileNotFoundError as e:
            print(f"Configuration file not found: {e}")
            print("Using default configuration values")
            return Config()
        except Exception as e:
            print(f"Error loading configuration: {e}")
            print("Using default configuration values")
            return Config()

    def connect_to_database(self):
        self.pg_client = PostgresClient(self.config)
        self.pg_client.connect()

    def run(self) -> None:
        self.logger_manager.log_app_startup()
        self.logger_manager.log_config_summary()
        self.connect_to_database()

        press_data = load_press_data_from_file("incheon_press.json")
        # 로드된 데이터 정보 출력
        self.logger.info(f"✅ 데이터 로드 성공!")
        self.logger.info(f"📊 총 기사 수: {press_data.total_count:,}개")
        
        # 기사 목록 요약
        if press_data.reports:
            self.logger.info(f"\n📰 기사 목록 (처음 5개):")
            for i, report in enumerate(press_data.reports[:5], 1):
                self.logger.info(f"  {i}. {report.title[:50]}...")
                self.logger.info(f"     📅 {report.date} | 🔗 {report.url}")
                self.logger.info(f"     📝 본문: {len(report.body.content)} 문단")
                self.logger.info(f"     📊 테이블: {len(report.tables)}개")
                self.logger.info(f"")
            
            if len(press_data.reports) > 5:
                self.logger.info(f"  ... 및 {len(press_data.reports) - 5}개 더")
        
        for report in press_data.reports:
            if report.tables:
                self.logger.info(f"url: {report.url}")
                for table in report.tables:
                    self.logger.info(f"--------------------------------")
                    table_data = parse_html_table(table.table_html)
                    self.logger.info(f"파싱 결과:")
                    self.logger.info(f"\n{json.dumps(table_data, ensure_ascii=False, indent=2)}")
                    self.logger.info(f"")



if __name__ == "__main__":
    """
    args:
        --config: Path to the configuration file.
    """
    parser = argparse.ArgumentParser(description="Smart News Application")
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to the configuration file (e.g., config/config.yml)"
    )
    args = parser.parse_args()
    
    main = Main(config_path=args.config)
    main.run()
