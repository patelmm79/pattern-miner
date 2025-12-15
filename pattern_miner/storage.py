# pattern_miner/storage.py
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import asyncpg
import logging

logger = logging.getLogger(__name__)


class Storage:
    """Storage for pattern analysis results - supports both in-memory and PostgreSQL"""

    def __init__(self, config):
        self.config = config
        self.use_database = config.use_database
        self._pool: Optional[asyncpg.Pool] = None

        # Fallback in-memory storage
        self._results = {}

    async def initialize(self):
        """Initialize database connection pool if using PostgreSQL"""
        if not self.use_database:
            logger.info("Using in-memory storage (database disabled)")
            return

        try:
            # Build connection string
            if self.config.database_url:
                connection_string = self.config.database_url
            else:
                connection_string = (
                    f"postgresql://{self.config.db_user}:{self.config.db_password}"
                    f"@{self.config.db_host}:{self.config.db_port}/{self.config.db_name}"
                )

            # Create connection pool
            self._pool = await asyncpg.create_pool(
                connection_string,
                min_size=2,
                max_size=10,
                command_timeout=60
            )

            logger.info(f"Connected to PostgreSQL database: {self.config.db_name}")

            # Ensure tables exist
            await self._ensure_tables()

        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            logger.warning("Falling back to in-memory storage")
            self.use_database = False
            self._pool = None

    async def _ensure_tables(self):
        """Create tables if they don't exist"""
        if not self._pool:
            return

        create_table_sql = """
        CREATE TABLE IF NOT EXISTS pattern_analyses (
            analysis_id TEXT PRIMARY KEY,
            repository TEXT NOT NULL,
            results JSONB NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS idx_analyses_repository
            ON pattern_analyses(repository);

        CREATE INDEX IF NOT EXISTS idx_analyses_created_at
            ON pattern_analyses(created_at DESC);

        CREATE INDEX IF NOT EXISTS idx_analyses_patterns
            ON pattern_analyses USING GIN ((results->'patterns'));
        """

        async with self._pool.acquire() as conn:
            await conn.execute(create_table_sql)
            logger.info("Database tables verified/created")

    async def close(self):
        """Close database connection pool"""
        if self._pool:
            await self._pool.close()
            logger.info("Database connection pool closed")

    async def store_analysis(
        self,
        analysis_id: str,
        repository: str,
        results: Dict[str, Any]
    ) -> None:
        """Store analysis results"""

        if self.use_database and self._pool:
            try:
                async with self._pool.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO pattern_analyses (analysis_id, repository, results)
                        VALUES ($1, $2, $3)
                        ON CONFLICT (analysis_id)
                        DO UPDATE SET
                            results = $3,
                            updated_at = NOW()
                        """,
                        analysis_id,
                        repository,
                        json.dumps(results)
                    )
                logger.info(f"Stored analysis {analysis_id} for {repository} in database")
            except Exception as e:
                logger.error(f"Failed to store analysis in database: {e}")
                # Fallback to in-memory
                self._store_in_memory(analysis_id, repository, results)
        else:
            self._store_in_memory(analysis_id, repository, results)

    def _store_in_memory(self, analysis_id: str, repository: str, results: Dict[str, Any]):
        """Store in memory"""
        self._results[analysis_id] = {
            "repository": repository,
            "results": results,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def get_analysis(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve analysis results by ID"""

        if self.use_database and self._pool:
            try:
                async with self._pool.acquire() as conn:
                    row = await conn.fetchrow(
                        """
                        SELECT repository, results, created_at, updated_at
                        FROM pattern_analyses
                        WHERE analysis_id = $1
                        """,
                        analysis_id
                    )

                    if row:
                        return {
                            "repository": row["repository"],
                            "results": json.loads(row["results"]),
                            "created_at": row["created_at"].isoformat(),
                            "updated_at": row["updated_at"].isoformat()
                        }
            except Exception as e:
                logger.error(f"Failed to get analysis from database: {e}")

        # Fallback to in-memory
        return self._results.get(analysis_id)

    async def get_all_analyses(
        self,
        repository: Optional[str] = None,
        pattern_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get all stored analyses with optional filtering

        Args:
            repository: Filter by repository name
            pattern_type: Filter by pattern type
            limit: Maximum number of results to return

        Returns:
            List of analysis results
        """

        if self.use_database and self._pool:
            try:
                async with self._pool.acquire() as conn:
                    query = "SELECT analysis_id, repository, results, created_at FROM pattern_analyses WHERE 1=1"
                    params = []
                    param_count = 1

                    if repository:
                        query += f" AND repository = ${param_count}"
                        params.append(repository)
                        param_count += 1

                    if pattern_type:
                        query += f" AND results->'patterns' @> $${param_count}::jsonb"
                        params.append(json.dumps([{"type": pattern_type}]))
                        param_count += 1

                    query += f" ORDER BY created_at DESC LIMIT ${param_count}"
                    params.append(limit)

                    rows = await conn.fetch(query, *params)

                    return [
                        {
                            "analysis_id": row["analysis_id"],
                            "repository": row["repository"],
                            "results": json.loads(row["results"]),
                            "timestamp": row["created_at"].isoformat()
                        }
                        for row in rows
                    ]
            except Exception as e:
                logger.error(f"Failed to get analyses from database: {e}")

        # Fallback to in-memory
        results = []
        for analysis_id, data in self._results.items():
            # Apply filters
            if repository and data.get("repository") != repository:
                continue

            if pattern_type:
                patterns = data.get("results", {}).get("patterns", [])
                if not any(p.get("type") == pattern_type for p in patterns):
                    continue

            results.append({
                "analysis_id": analysis_id,
                **data
            })

            if len(results) >= limit:
                break

        return results

    async def delete_analysis(self, analysis_id: str) -> bool:
        """Delete analysis results"""

        if self.use_database and self._pool:
            try:
                async with self._pool.acquire() as conn:
                    result = await conn.execute(
                        "DELETE FROM pattern_analyses WHERE analysis_id = $1",
                        analysis_id
                    )
                    return result == "DELETE 1"
            except Exception as e:
                logger.error(f"Failed to delete analysis from database: {e}")

        # Fallback to in-memory
        if analysis_id in self._results:
            del self._results[analysis_id]
            return True
        return False

    async def get_statistics(self) -> Dict[str, Any]:
        """Get storage statistics"""

        if self.use_database and self._pool:
            try:
                async with self._pool.acquire() as conn:
                    stats = await conn.fetchrow(
                        """
                        SELECT
                            COUNT(*) as total_analyses,
                            COUNT(DISTINCT repository) as unique_repositories
                        FROM pattern_analyses
                        """
                    )

                    # Get pattern types
                    pattern_rows = await conn.fetch(
                        """
                        SELECT DISTINCT jsonb_array_elements(results->'patterns')->>'type' as pattern_type
                        FROM pattern_analyses
                        WHERE results->'patterns' IS NOT NULL
                        """
                    )

                    return {
                        "total_analyses": stats["total_analyses"],
                        "unique_repositories": stats["unique_repositories"],
                        "pattern_types": [row["pattern_type"] for row in pattern_rows if row["pattern_type"]],
                        "storage_type": "postgresql"
                    }
            except Exception as e:
                logger.error(f"Failed to get statistics from database: {e}")

        # Fallback to in-memory
        total_analyses = len(self._results)
        repositories = set()
        pattern_types = set()

        for data in self._results.values():
            repositories.add(data.get("repository"))
            patterns = data.get("results", {}).get("patterns", [])
            for pattern in patterns:
                pattern_types.add(pattern.get("type"))

        return {
            "total_analyses": total_analyses,
            "unique_repositories": len(repositories),
            "pattern_types": list(pattern_types),
            "storage_type": "in_memory"
        }
