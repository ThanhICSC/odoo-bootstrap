"""
PostgreSQL database utilities.
"""

from __future__ import annotations

import subprocess

from odoo_bootstrap.core.exceptions import DatabaseError
from odoo_bootstrap.core.logger import get_logger
from odoo_bootstrap.core.models import DatabaseConfig

logger = get_logger("database")


def get_psql_connection(config: DatabaseConfig):
    """Return a psycopg2 connection to the given database config."""
    try:
        import psycopg2

        return psycopg2.connect(
            host=config.host,
            port=config.port,
            user=config.user,
            password=config.password,
            dbname=config.name or "postgres",
            connect_timeout=5,
        )
    except Exception as e:
        raise DatabaseError(f"Cannot connect to PostgreSQL: {e}") from e


def database_exists(config: DatabaseConfig) -> bool:
    """Return True if the database exists."""
    try:
        pg_config = DatabaseConfig(
            host=config.host,
            port=config.port,
            user=config.user,
            password=config.password,
            name="postgres",
        )
        conn = get_psql_connection(pg_config)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (config.name,))
            return cur.fetchone() is not None
    except Exception:
        return False
    finally:
        try:
            conn.close()
        except Exception:
            pass


def create_database(config: DatabaseConfig) -> None:
    """Create a new database if it does not already exist."""
    if database_exists(config):
        logger.info(f"Database {config.name} already exists")
        return
    try:
        pg_config = DatabaseConfig(
            host=config.host,
            port=config.port,
            user=config.user,
            password=config.password,
            name="postgres",
        )
        conn = get_psql_connection(pg_config)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(f'CREATE DATABASE "{config.name}" OWNER "{config.user}"')
        logger.info(f"Database {config.name} created")
    except Exception as e:
        raise DatabaseError(f"Failed to create database {config.name}: {e}") from e
    finally:
        try:
            conn.close()
        except Exception:
            pass


def drop_database(config: DatabaseConfig) -> None:
    """Drop a database if it exists."""
    if not database_exists(config):
        logger.info(f"Database {config.name} does not exist, skipping drop")
        return
    try:
        pg_config = DatabaseConfig(
            host=config.host,
            port=config.port,
            user=config.user,
            password=config.password,
            name="postgres",
        )
        conn = get_psql_connection(pg_config)
        conn.autocommit = True
        with conn.cursor() as cur:
            # Terminate existing connections
            cur.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = %s AND pid <> pg_backend_pid()",
                (config.name,),
            )
            cur.execute(f'DROP DATABASE IF EXISTS "{config.name}"')
        logger.info(f"Database {config.name} dropped")
    except Exception as e:
        raise DatabaseError(f"Failed to drop database {config.name}: {e}") from e
    finally:
        try:
            conn.close()
        except Exception:
            pass


def pg_dump(
    config: DatabaseConfig,
    output_file: str,
    format: str = "c",
) -> None:
    """Dump a database using pg_dump."""
    env = {
        "PGPASSWORD": config.password,
        "PATH": "/usr/bin:/usr/local/bin:/bin",
    }
    cmd = [
        "pg_dump",
        f"--host={config.host}",
        f"--port={config.port}",
        f"--username={config.user}",
        f"--format={format}",
        f"--file={output_file}",
        config.name,
    ]
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        raise DatabaseError(f"pg_dump failed: {result.stderr}")
    logger.info(f"Database {config.name} dumped to {output_file}")


def pg_restore(
    config: DatabaseConfig,
    input_file: str,
) -> None:
    """Restore a database from a pg_dump file."""
    env = {
        "PGPASSWORD": config.password,
        "PATH": "/usr/bin:/usr/local/bin:/bin",
    }
    cmd = [
        "pg_restore",
        f"--host={config.host}",
        f"--port={config.port}",
        f"--username={config.user}",
        f"--dbname={config.name}",
        "--no-owner",
        "--no-privileges",
        input_file,
    ]
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        raise DatabaseError(f"pg_restore failed: {result.stderr}")
    logger.info(f"Database {config.name} restored from {input_file}")


def postgres_is_reachable(
    host: str = "localhost", port: int = 5432, user: str = "odoo", password: str = "odoo"
) -> bool:
    """Quick check if PostgreSQL is reachable."""
    try:
        config = DatabaseConfig(host=host, port=port, user=user, password=password, name="postgres")
        conn = get_psql_connection(config)
        conn.close()
        return True
    except Exception:
        return False
