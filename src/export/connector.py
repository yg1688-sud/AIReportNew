"""SQL Server connection management via pymssql."""

import os
import time

import structlog

log = structlog.get_logger()


def _resolve_env(value: str) -> str:
    """Resolve ${ENV_VAR} reference to its actual value."""
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        return os.environ.get(value[2:-1], "")
    return value


class ConnectionError(Exception):
    """Raised when SQL Server connection fails."""


class QueryTimeoutError(Exception):
    """Raised when a query exceeds the configured timeout."""


class SQLServerConnector:
    """Context-managed pymssql connection wrapper."""

    def __init__(self, config, overrides: dict | None = None):
        """Initialize with ExportConfig and optional per-group overrides.

        Args:
            config: ExportConfig with root-level connection settings.
            overrides: Optional dict with any of server, port, database,
                       username, password, timeout to override config values.
        """
        self.config = config
        self._overrides = overrides or {}
        self._conn = None
        self._connected_at: float = 0.0
        self._cursor = None

    def _resolve(self, key: str, default):
        """Return override value if set, otherwise config default."""
        val = self._overrides.get(key)
        if val is None or val == "" or val == 0:
            return default
        return val

    def __enter__(self):
        try:
            import pymssql
            self._connected_at = time.time()

            server = self._resolve("server", self.config.server)
            port = self._resolve("port", self.config.port)
            database = self._resolve("database", self.config.database)
            username = self._resolve("username", self.config.username)
            password = _resolve_env(self._resolve("password", self.config.password))
            timeout = self._resolve("timeout", self.config.timeout)

            self._conn = pymssql.connect(
                server=server,
                port=port,
                database=database,
                user=username,
                password=password,
                login_timeout=timeout,
                timeout=timeout,
                charset="UTF-8",
            )
            self._cursor = self._conn.cursor()
            log.info("db.connected", server=server, port=port, database=database)
            return self
        except Exception as e:
            raise ConnectionError(
                f"无法连接 SQL Server ({self.config.server}:{self.config.port}): {e}"
            ) from e

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
        elapsed = time.time() - self._connected_at
        log.info("db.disconnected", elapsed=round(elapsed, 2))
        return False  # Don't suppress exceptions

    def execute(self, query: str, params: tuple = None):
        """Execute a parameterized SQL query and return the cursor.

        Uses parameterized queries to prevent SQL injection.
        """
        try:
            start = time.time()
            if params:
                self._cursor.execute(query, params)
            else:
                self._cursor.execute(query)
            elapsed = time.time() - start
            log.info("db.query_executed", elapsed=round(elapsed, 3))
            return self._cursor
        except Exception as e:
            raise ConnectionError(f"查询执行失败: {e}") from e

    def fetch_all_as_dicts(self) -> list[dict]:
        """Fetch all rows as list of dicts from the cursor."""
        if not self._cursor:
            return []

        columns = [col[0] for col in self._cursor.description] if self._cursor.description else []
        rows = self._cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows] if rows else []

    def fetch_value(self) -> float:
        """Fetch a single scalar value from the cursor."""
        if not self._cursor:
            return 0.0
        row = self._cursor.fetchone()
        return float(row[0]) if row and row[0] is not None else 0.0
