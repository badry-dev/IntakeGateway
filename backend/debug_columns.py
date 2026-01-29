#!/usr/bin/env python
"""Debug script to test Oracle column retrieval"""

import sys
import oracledb
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Enable thick mode for oracledb
try:
    oracledb.init_oracle_client()
    print("Oracle Instant Client initialized in thick mode")
except Exception as e:
    print(f"Warning: Could not initialize thick mode: {e}")
    print("Attempting to continue without thick mode...")

# Create engine - remove thick_mode from URL
url = settings.sqlalchemy_url.replace("&thick_mode=true", "").replace("?thick_mode=true", "")
print(f"Connecting to: {url}")

try:
    engine = create_engine(url, echo=False)

    # Create session
    Session = sessionmaker(bind=engine)
    db = Session()

    # Test query
    table_name = "XX_PRODUCTS_TEMP"
    table_name_upper = table_name.upper()

    print(f"\n{'='*60}")
    print(f"Testing query for table: {table_name_upper}")
    print(f"{'='*60}\n")

    try:
        query = text("""
            SELECT 
                COLUMN_NAME,
                DATA_TYPE,
                NULLABLE,
                CHAR_LENGTH,
                DATA_LENGTH
            FROM USER_TAB_COLUMNS
            WHERE TABLE_NAME = :table_name
            ORDER BY COLUMN_ID
        """)
        
        print(f"Executing query with parameter: table_name={table_name_upper}")
        result = db.execute(query, {"table_name": table_name_upper})
        rows = result.fetchall()
        
        print(f"\nRetrieved {len(rows)} rows")
        
        if rows:
            print(f"\nColumn information:")
            for i, row in enumerate(rows):
                print(f"  {i+1}. {row[0]:30} {row[1]:15} Nullable={row[2]}")
        else:
            print("\nNo rows returned! Table not found.")
            
    except Exception as e:
        print(f"Query Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()

except Exception as e:
    print(f"Connection Error: {e}")
    import traceback
    traceback.print_exc()
