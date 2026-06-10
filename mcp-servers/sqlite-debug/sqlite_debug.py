"""MCP server for debugging SQLite database."""

import sqlite3
import json
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("sqlite-debug")

# Default database path
DEFAULT_DB_PATH = "/home/mio/fmod/DarkFindV5/api/data/darkfindv5.db"


def get_db(db_path: str = "") -> sqlite3.Connection:
    """Get database connection."""
    path = db_path if db_path else DEFAULT_DB_PATH
    if not Path(path).exists():
        raise FileNotFoundError(f"Database not found: {path}")
    return sqlite3.connect(path)


@mcp.tool()
def query(sql: str, db_path: str = "", params: list = None) -> str:
    """Execute a SQL SELECT query and return results.
    
    Args:
        sql: SQL SELECT query to execute
        db_path: Custom database path (optional)
        params: Query parameters (optional)
    """
    try:
        conn = get_db(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return "Query returned no results"
        
        # Convert to list of dicts
        results = [dict(row) for row in rows]
        
        # Format output
        output = f"Query returned {len(results)} rows:\n\n"
        output += json.dumps(results[:100], indent=2, default=str)
        
        if len(results) > 100:
            output += f"\n\n... and {len(results) - 100} more rows"
        
        return output
    
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
def execute(sql: str, db_path: str = "", params: list = None) -> str:
    """Execute a SQL INSERT/UPDATE/DELETE statement.
    
    Args:
        sql: SQL statement to execute
        db_path: Custom database path (optional)
        params: Query parameters (optional)
    """
    try:
        conn = get_db(db_path)
        cursor = conn.cursor()
        
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        
        return f"Statement executed successfully. {affected} row(s) affected."
    
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
def list_tables(db_path: str = "") -> str:
    """List all tables in the database.
    
    Args:
        db_path: Custom database path (optional)
    """
    try:
        conn = get_db(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        if not tables:
            return "No tables found in database"
        
        return f"Tables ({len(tables)}):\n" + "\n".join(tables)
    
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
def describe_table(table_name: str, db_path: str = "") -> str:
    """Describe the structure of a table.
    
    Args:
        table_name: Name of the table to describe
        db_path: Custom database path (optional)
    """
    try:
        conn = get_db(db_path)
        cursor = conn.cursor()
        
        # Get column info
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        # Get row count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        row_count = cursor.fetchone()[0]
        
        # Get indexes
        cursor.execute(f"PRAGMA index_list({table_name})")
        indexes = cursor.fetchall()
        
        conn.close()
        
        output = f"Table: {table_name}\n"
        output += f"Row count: {row_count}\n\n"
        
        output += "Columns:\n"
        for col in columns:
            pk = " [PRIMARY KEY]" if col[5] else ""
            not_null = " NOT NULL" if col[3] else ""
            default = f" DEFAULT {col[4]}" if col[4] is not None else ""
            output += f"  {col[1]}: {col[2]}{pk}{not_null}{default}\n"
        
        if indexes:
            output += "\nIndexes:\n"
            for idx in indexes:
                output += f"  {idx[1]} (unique: {idx[2]})\n"
        
        return output
    
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
def export_table(table_name: str, db_path: str = "", limit: int = 1000) -> str:
    """Export table data as JSON.
    
    Args:
        table_name: Name of the table to export
        db_path: Custom database path (optional)
        limit: Maximum rows to export (default 1000)
    """
    try:
        conn = get_db(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(f"SELECT * FROM {table_name} LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return f"Table {table_name} is empty"
        
        results = [dict(row) for row in rows]
        
        return f"Exported {len(results)} rows from {table_name}:\n\n" + json.dumps(results, indent=2, default=str)
    
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
def backup_db(db_path: str = "", backup_path: str = "") -> str:
    """Create a backup of the database.
    
    Args:
        db_path: Source database path (optional)
        backup_path: Backup destination path (optional, adds timestamp)
    """
    try:
        source = db_path if db_path else DEFAULT_DB_PATH
        
        if not backup_path:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{source}.{timestamp}.bak"
        
        import shutil
        shutil.copy2(source, backup_path)
        
        return f"Database backed up to: {backup_path}"
    
    except Exception as e:
        return f"Error: {str(e)}"


def main():
    """Run the MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
