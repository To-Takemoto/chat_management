import asyncio
from typing import Any, Dict, List, Optional
from functools import lru_cache
import structlog
from pydantic import BaseModel, Field
from supabase import create_client, Client
import json
from contextlib import asynccontextmanager

# ロガーの設定
logger = structlog.get_logger()

class SupabaseConfig(BaseModel):
    url: str = Field(..., description="Supabase project URL")
    key: str = Field(..., description="Supabase API key")
    timeout: float = Field(10.0, description="Timeout for Supabase operations in seconds")

class SupabaseHandler:
    def __init__(self, config: SupabaseConfig):
        self.config = config
        self.supabase: Client = create_client(config.url, config.key)

    @asynccontextmanager
    async def supabase_context(self):
        try:
            yield self.supabase
        except Exception as e:
            logger.error("Supabase operation failed", error=str(e))
            raise
        finally:
            # ここに必要なクリーンアップ処理を追加
            pass

    @lru_cache(maxsize=100)
    async def _cached_query(self, table_name: str, query_hash: str):
        async with self.supabase_context() as supabase:
            # query_hashに基づいてクエリを構築する
            # この例では単純化のため、全データを取得していますが、
            # 実際にはquery_hashを解析して適切なクエリを構築する必要があります
            result = await supabase.table(table_name).select("*").execute()
        return result.data

    async def data_exists(
            self,
            table_name: str,
            data: Dict[str, Any],
            check_columns: Optional[List[str]] = None
            ) -> bool:
        """
        キャッシュを利用するので、稀に一致しない可能性があるので要注意
        """
        check_columns = check_columns or list(data.keys())
        query_hash = f"{table_name}:{','.join(check_columns)}:{json.dumps(data, sort_keys=True)}"
        
        try:
            cached_data = await self._cached_query(table_name, query_hash)
            return any(all(item[col] == data[col] for col in check_columns) for item in cached_data)
        except Exception as e:
            logger.error("Error checking data existence", table=table_name, error=str(e))
            return False

    async def insert_data(
            self,
            table_name: str,
            data: Dict[str, Any],
            check_columns: Optional[List[str]] = None,
            hard: bool = False
            ) -> Optional[Dict[str, Any]]:
        """
        同時に実行されると重複の可能性あるので注意
        """
        if not hard and await self.data_exists(table_name, data, check_columns):
            logger.info("Data already exists, skipping insert", table=table_name)
            return None

        try:
            async with self.supabase_context() as supabase:
                result = await supabase.table(table_name).insert(data).execute()
            logger.info("Data inserted successfully", table=table_name)
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error("Error inserting data", table=table_name, error=str(e))
            return None

    async def select_one_record(
            self,
            table_name: str,
            conditions: Optional[Dict[str, Any]] = None,
            fields: Optional[List[str]] = None
            ) -> Optional[Dict[str, Any]]:
        try:
            async with self.supabase_context() as supabase:
                query = supabase.table(table_name)
                if fields:
                    query = query.select(",".join(fields))
                if conditions:
                    for key, value in conditions.items():
                        query = query.eq(key, value)
                result = await query.limit(1).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error("Error selecting record", table=table_name, error=str(e))
            return None

    @lru_cache(maxsize=10)
    async def count_data(self, table_name: str) -> int:
        try:
            async with self.supabase_context() as supabase:
                result = await supabase.table(table_name).select("*", count="exact").execute()
            return result.count
        except Exception as e:
            logger.error("Error counting data", table=table_name, error=str(e))
            return 0

    async def batch_insert(self, table_name: str, data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        try:
            async with self.supabase_context() as supabase:
                result = await supabase.table(table_name).insert(data_list).execute()
            logger.info("Batch insert completed", table=table_name, count=len(data_list))
            return result.data
        except Exception as e:
            logger.error("Error in batch insert", table=table_name, error=str(e))
            return []

    async def update_data(
            self,
            table_name: str,
            data: Dict[str, Any],
            conditions: Dict[str, Any]
            ) -> Optional[Dict[str, Any]]:
        try:
            async with self.supabase_context() as supabase:
                query = supabase.table(table_name).update(data)
                for key, value in conditions.items():
                    query = query.eq(key, value)
                result = await query.execute()
            logger.info("Data updated successfully", table=table_name)
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error("Error updating data", table=table_name, error=str(e))
            return None

    async def delete_record(
            self,
            table_name: str,
            conditions: Dict[str, Any]
            ) -> bool:
        try:
            async with self.supabase_context() as supabase:
                query = supabase.table(table_name).delete()
                for key, value in conditions.items():
                    query = query.eq(key, value)
                await query.execute()
            logger.info("Record deleted successfully", table=table_name)
            return True
        except Exception as e:
            logger.error("Error deleting record", table=table_name, error=str(e))
            return False

# 使用例
async def main():
    config = SupabaseConfig(url="YOUR_SUPABASE_URL", key="YOUR_SUPABASE_KEY")
    handler = SupabaseHandler(config)

    # データの挿入
    user_data = {"name": "John Doe", "age": 30}
    inserted_user = await handler.insert_data("users", user_data)
    logger.info("Inserted user", user=inserted_user)

    # データの取得
    user = await handler.select_one_record("users", {"name": "John Doe"})
    logger.info("Retrieved user", user=user)

    # データのカウント
    count = await handler.count_data("users")
    logger.info("User count", count=count)

if __name__ == "__main__":
    asyncio.run(main())