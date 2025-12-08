import sqlite3
from pathlib import Path
from typing import Iterable


class QueryBuilder:
    # This is prone to SQL injection, but... do we care if people want to hack their own backups?

    @staticmethod
    def content(domain_prefix: str = "", namespace_prefix: str = "", path_prefix: str = "") -> str:
        """Build SQL query to fetch files based on domain and path prefix."""

        query = f"""
            SELECT fileID, domain, relativePath, flags, file
            FROM Files
            WHERE 1 = 1
        """

        if namespace_prefix:
            query += f" AND domain LIKE '{domain_prefix}%-{namespace_prefix}%'"
        elif domain_prefix:
            query += f" AND domain LIKE '{domain_prefix}%'"
        
        if path_prefix:
            query += f" AND relativePath LIKE '{path_prefix}%'"

        return query
    
    @classmethod
    def content_count(cls, domain_prefix: str, namespace_prefix: str = "",
                      path_prefix: str = "") -> str:
        """Build SQL query to count files based on domain and path prefix."""

        query = f"""
            SELECT COUNT(*)
            FROM (
                {cls.content(domain_prefix, namespace_prefix, path_prefix)}
            )
        """

        return query
    
    @staticmethod
    def all_domains() -> str:
        """Build SQL query to fetch all distinct domains."""

        return """
            select distinct
                case when instr(domain, '-') > 0 then
                    substr(domain, 1, instr(domain, '-') - 1)
                    else domain
                end as domain
            from Files;
        """
    
    @staticmethod
    def all_namespaces(domain: str) -> str:
        """Build SQL query to fetch all distinct namespaces for a given domain."""

        return f"""
            select distinct substr(domain, {len(domain) + 2}) as namespace
            from Files
            where domain like '{domain}-%';
        """

class BackupDB:
    def __init__(self, db_path: str | Path):
        if not isinstance(db_path, Path):
            db_path = Path(db_path)
        
        if not db_path.exists():
            raise FileNotFoundError(f"Database file not found: {db_path}")
        
        self.conn = sqlite3.connect(db_path)
    
    def simple_query(self, query: str) -> list[tuple]:
        """Execute a simple SQL query and return all results."""
        cursor = self.conn.cursor()
        cursor.execute(query)
        return cursor.fetchall()
    
    def buffered_query(self, query: str, buffer_size: int = 1000) -> Iterable[tuple]:
        """Execute the given SQL query and yield results in buffered chunks."""
        cursor = self.conn.cursor()
        cursor.execute(query)
        while True:
            records = cursor.fetchmany(buffer_size)
            if not records:
                break
            for record in records:
                yield record

    def get_content(self, domain_prefix: str = "", namespace_prefix: str = "",
                    path_prefix: str = "") -> Iterable[tuple]:
        """Fetch content records based on filters."""
        query = QueryBuilder.content(domain_prefix, namespace_prefix, path_prefix)
        return self.buffered_query(query)
    
    def get_content_count(self, domain_prefix: str = "", namespace_prefix: str = "",
                          path_prefix: str = "") -> int:
        """Count content records based on filters."""

        query = QueryBuilder.content_count(domain_prefix, namespace_prefix, path_prefix)
        cursor = self.conn.cursor()
        cursor.execute(query)
        count = cursor.fetchone()[0]
        return count

    def get_all_domains(self) -> list[str]:
        """Fetch all distinct domains from the database."""
        query = QueryBuilder.all_domains()
        result = [row[0] for row in self.simple_query(query)]
        return result
    
    def get_namespaces(self, domain: str) -> list[str]:
        """Fetch all distinct domains from the database."""
        query = QueryBuilder.all_namespaces(domain)
        result = [row[0] for row in self.simple_query(query)]
        return result
    
    def close(self) -> None:
        """Close the database connection."""
        self.conn.close()
