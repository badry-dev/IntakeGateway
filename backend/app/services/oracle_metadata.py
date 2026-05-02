"""Oracle metadata service for querying table schema information.

Provides utilities to query Oracle's system views for table and column metadata,
used for field type detection and validation during column mapping configuration.
"""

import logging

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.schemas.column_mapping import OracleColumn

logger = logging.getLogger(__name__)


def get_table_columns(db: Session, table_name: str) -> list[OracleColumn]:
    """
    Query Oracle USER_TAB_COLUMNS to get table column metadata.

    Args:
        db: Database session
        table_name: Name of the table (case-insensitive, converted to uppercase)

    Returns:
        List of OracleColumn objects with column metadata

    Raises:
        PermissionError: If user lacks permissions to query USER_TAB_COLUMNS
        ValueError: If table not found
    """
    # Convert to uppercase as Oracle system views expect uppercase
    table_name_upper = table_name.upper()

    logger.info(f"Getting columns for table: {table_name_upper}")

    try:
        # Build query with direct string (some Oracle drivers have issues with parameter binding)
        # Sanitize table name to prevent SQL injection
        if not table_name_upper.isalnum() and "_" not in table_name_upper:
            raise ValueError(f"Invalid table name: {table_name}")

        sql_query = f"""
            SELECT
                COLUMN_NAME,
                DATA_TYPE,
                NULLABLE,
                CHAR_LENGTH,
                DATA_LENGTH
            FROM USER_TAB_COLUMNS
            WHERE TABLE_NAME = '{table_name_upper}'
            ORDER BY COLUMN_ID
        """

        query = text(sql_query)
        logger.debug(f"Executing query for table {table_name_upper}")
        result = db.execute(query)
        rows = result.fetchall()

        logger.info(f"Query returned {len(rows) if rows else 0} rows for {table_name_upper}")

        if not rows:
            logger.warning(f"No columns found for table {table_name_upper}")
            # Return empty list instead of raising error - let caller decide
            return []

        columns = []
        for row in rows:
            column_name, data_type, nullable, char_length, data_length = row

            # Parse nullable value (Y/N in Oracle)
            is_nullable = nullable == "Y"

            # Determine max length based on data type
            max_length = None
            if data_type in ("VARCHAR2", "CHAR"):
                max_length = char_length
            elif data_type in ("NUMBER"):
                # For NUMBER type, data_length contains precision info
                max_length = data_length

            column = OracleColumn(
                column_name=column_name,
                data_type=data_type,
                nullable=is_nullable,
                max_length=max_length,
            )
            columns.append(column)

        logger.info(f"Retrieved {len(columns)} columns from table {table_name_upper}")
        return columns

    except SQLAlchemyError as e:
        # Check if it's a permission error
        error_msg = str(e)
        logger.error(f"SQLAlchemy error querying {table_name_upper}: {error_msg}")

        if "ORA-00942" in error_msg:  # Table or view does not exist
            logger.warning(f"Table {table_name_upper} not found")
            return []
        elif (
            "ORA-00904" in error_msg or "ORA-01031" in error_msg
        ):  # Invalid column or insufficient privileges
            logger.warning(f"Permission denied querying {table_name_upper}")
            raise PermissionError(f"Insufficient privileges to query table '{table_name}'")
        elif "DPY-3010" in error_msg or "DPI-1047" in error_msg:
            # Connection mode not supported - likely needs Oracle Instant Client
            logger.error(
                f"Database connection error (requires Oracle Instant Client for thick mode): {error_msg}"
            )
            return []  # Return empty list - let frontend show error
        else:
            logger.error(f"Database error querying {table_name_upper}: {error_msg}")
            raise

    except Exception as e:
        # Generic fallback for any other errors
        error_msg = str(e)
        logger.error(f"Unexpected error querying {table_name_upper}: {error_msg}")
        if "DPY-3010" in error_msg or "DPI-1047" in error_msg:
            return []  # Connection error - return empty list
        raise


def table_exists(db: Session, table_name: str) -> bool:
    """
    Check if a table exists in the database.

    Args:
        db: Database session
        table_name: Name of the table

    Returns:
        True if table exists, False otherwise
    """
    try:
        table_name_upper = table_name.upper()
        query = text("""
            SELECT COUNT(*)
            FROM USER_TABLES
            WHERE TABLE_NAME = :table_name
        """)
        result = db.execute(query, {"table_name": table_name_upper})
        count = result.scalar()
        return count > 0
    except Exception as e:
        logger.error(f"Error checking table existence: {str(e)}")
        return False


def get_table_row_count(db: Session, table_name: str) -> int:
    """
    Get approximate row count for a table (using Oracle internal stats).

    Args:
        db: Database session
        table_name: Name of the table

    Returns:
        Approximate row count

    Raises:
        ValueError: If table not found
    """
    try:
        table_name_upper = table_name.upper()
        query = text("""
            SELECT NUM_ROWS
            FROM USER_TABLES
            WHERE TABLE_NAME = :table_name
        """)
        result = db.execute(query, {"table_name": table_name_upper})
        row_count = result.scalar()

        if row_count is None:
            raise ValueError(f"Table '{table_name}' not found")

        return row_count or 0
    except SQLAlchemyError as e:
        logger.error(f"Error getting row count for {table_name}: {str(e)}")
        raise ValueError(f"Could not retrieve row count for table '{table_name}'")


def get_column_info(db: Session, table_name: str, column_name: str) -> OracleColumn | None:
    """
    Get detailed information about a specific column.

    Args:
        db: Database session
        table_name: Name of the table
        column_name: Name of the column

    Returns:
        OracleColumn object if found, None otherwise
    """
    try:
        table_name_upper = table_name.upper()
        column_name_upper = column_name.upper()

        query = text("""
            SELECT
                COLUMN_NAME,
                DATA_TYPE,
                NULLABLE,
                CHAR_LENGTH,
                DATA_LENGTH
            FROM USER_TAB_COLUMNS
            WHERE TABLE_NAME = :table_name
            AND COLUMN_NAME = :column_name
        """)

        result = db.execute(
            query, {"table_name": table_name_upper, "column_name": column_name_upper}
        )
        row = result.fetchone()

        if not row:
            return None

        column_name, data_type, nullable, char_length, data_length = row

        is_nullable = nullable == "Y"
        max_length = char_length if data_type in ("VARCHAR2", "CHAR") else data_length

        return OracleColumn(
            column_name=column_name,
            data_type=data_type,
            nullable=is_nullable,
            max_length=max_length,
        )

    except Exception as e:
        logger.error(f"Error getting column info: {str(e)}")
        return None


def validate_column_exists(db: Session, table_name: str, column_name: str) -> bool:
    """
    Validate that a column exists in a table.

    Args:
        db: Database session
        table_name: Name of the table
        column_name: Name of the column

    Returns:
        True if column exists, False otherwise
    """
    column_info = get_column_info(db, table_name, column_name)
    return column_info is not None


# Type mapping from Oracle types to Python/API types
ORACLE_TYPE_MAPPING = {
    "VARCHAR2": "string",
    "VARCHAR": "string",
    "CHAR": "string",
    "NVARCHAR2": "string",
    "NCHAR": "string",
    "CLOB": "string",
    "NUMBER": "number",
    "INTEGER": "number",
    "INT": "number",
    "DECIMAL": "number",
    "FLOAT": "number",
    "BINARY_FLOAT": "number",
    "BINARY_DOUBLE": "number",
    "DATE": "date",
    "TIMESTAMP": "timestamp",
    "TIMESTAMP WITH TIME ZONE": "timestamp",
    "TIMESTAMP WITH LOCAL TIME ZONE": "timestamp",
    "BLOB": "binary",
    "LONG": "string",
    "LONG RAW": "binary",
}


def get_oracle_type_category(oracle_type: str) -> str:
    """
    Get type category (string, number, date, timestamp, binary) for an Oracle type.

    Args:
        oracle_type: Oracle data type (e.g., VARCHAR2, NUMBER, DATE)

    Returns:
        Type category
    """
    oracle_type_upper = oracle_type.upper().strip()
    return ORACLE_TYPE_MAPPING.get(oracle_type_upper, "unknown")
