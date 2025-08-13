import asyncpg
from configuration.config import Config
from logger.logger import get_logger

class PostgresClient:
    def __init__(self, config: Config = Config()):
        self.config = config.get_database_config()
        self.pool = None
        self.logger = get_logger(__name__)

    def connect(self):
        """ 커넥션 풀 생성 """
        self.pool = asyncpg.create_pool(
            user=self.config.user,
            password=self.config.password,
            database=self.config.database,
            host=self.config.host,
            port=self.config.port,
            min_size=self.config.min_size,
            max_size=self.config.max_size
        )
        self.logger.info("Connected to PostgreSQL")

    def close(self):
        """ 커넥션 풀 종료 """
        if self.pool:
            self.pool.close()
            self.logger.info("Connection pool closed")

    async def fetch(self, query, *args):
        """ SELECT 쿼리 (여러 row 가져오기) """
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                result = await conn.fetch(query, *args)
                return result

    async def fetchrow(self, query, *args):
        """ SELECT 쿼리 (한 row 가져오기) """
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                result = await conn.fetchrow(query, *args)
                return result
