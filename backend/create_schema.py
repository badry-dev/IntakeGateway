#!/usr/bin/env python3
"""Create database schema"""
import oracledb
from app.core.config import settings

# Initialize thick mode
oracledb.init_oracle_client(lib_dir=r'C:\oracle\instantclient_23_0')

# Connect
conn = oracledb.connect(
    user=settings.ORACLE_USER,
    password=settings.ORACLE_PASSWORD,
    dsn=f'{settings.ORACLE_HOST}:{settings.ORACLE_PORT}/{settings.ORACLE_SERVICE_NAME}'
)
cursor = conn.cursor()

print("Creating database schema...")

# Create sequences
sequences = [
    "CREATE SEQUENCE task_seq START WITH 1 INCREMENT BY 1",
    "CREATE SEQUENCE task_run_seq START WITH 1 INCREMENT BY 1",
    "CREATE SEQUENCE task_schedule_seq START WITH 1 INCREMENT BY 1",
    "CREATE SEQUENCE column_mapping_seq START WITH 1 INCREMENT BY 1",
    "CREATE SEQUENCE task_log_seq START WITH 1 INCREMENT BY 1",
    "CREATE SEQUENCE task_run_log_seq START WITH 1 INCREMENT BY 1",
]

tables = [
    """CREATE TABLE task (
        id NUMBER PRIMARY KEY,
        name VARCHAR2(200) NOT NULL UNIQUE,
        description CLOB NULL,
        connection_id NUMBER NULL,
        http_method VARCHAR2(10) DEFAULT 'GET' NOT NULL,
        endpoint_path VARCHAR2(1000) NOT NULL,
        query_params_json CLOB NULL,
        headers_json CLOB NULL,
        body_json CLOB NULL,
        record_path VARCHAR2(400) NULL,
        dest_table VARCHAR2(200) NOT NULL,
        batch_size NUMBER DEFAULT 500 NOT NULL,
        is_active NUMBER(1) DEFAULT 1 NOT NULL,
        created_at TIMESTAMP DEFAULT SYSTIMESTAMP,
        updated_at TIMESTAMP NULL
    )""",
    """CREATE TABLE task_run (
        id NUMBER PRIMARY KEY,
        task_id NUMBER NOT NULL,
        status VARCHAR2(30) DEFAULT 'PENDING' NOT NULL,
        rows_fetched NUMBER DEFAULT 0,
        rows_inserted NUMBER DEFAULT 0,
        error_count NUMBER DEFAULT 0,
        warning_count NUMBER DEFAULT 0,
        started_at TIMESTAMP DEFAULT SYSTIMESTAMP,
        ended_at TIMESTAMP NULL,
        CONSTRAINT fk_task_run_task_id FOREIGN KEY (task_id) REFERENCES task(id) ON DELETE CASCADE
    )""",
    """CREATE TABLE task_schedule (
        id NUMBER PRIMARY KEY,
        task_id NUMBER NOT NULL,
        cron_expression VARCHAR2(50) NOT NULL,
        is_active NUMBER(1) DEFAULT 1 NOT NULL,
        last_run_date TIMESTAMP NULL,
        next_run_date TIMESTAMP NULL,
        created_at TIMESTAMP DEFAULT SYSTIMESTAMP,
        updated_at TIMESTAMP NULL,
        CONSTRAINT fk_task_schedule_task_id FOREIGN KEY (task_id) REFERENCES task(id) ON DELETE CASCADE,
        CONSTRAINT uk_task_schedule_task_id UNIQUE (task_id)
    )""",
    """CREATE TABLE column_mapping (
        id NUMBER PRIMARY KEY,
        task_id NUMBER NOT NULL,
        source_field VARCHAR2(255) NOT NULL,
        dest_column VARCHAR2(255) NOT NULL,
        transform_rules CLOB NULL,
        is_active NUMBER(1) DEFAULT 1 NOT NULL,
        created_at TIMESTAMP DEFAULT SYSTIMESTAMP,
        updated_at TIMESTAMP NULL,
        CONSTRAINT fk_column_mapping_task_id FOREIGN KEY (task_id) REFERENCES task(id) ON DELETE CASCADE,
        CONSTRAINT uk_column_mapping_task_source UNIQUE (task_id, source_field)
    )""",
    """CREATE TABLE task_log (
        id NUMBER PRIMARY KEY,
        task_run_id NUMBER NOT NULL,
        step_name VARCHAR2(50) NULL,
        message VARCHAR2(1000) NULL,
        details CLOB NULL,
        created_at TIMESTAMP DEFAULT SYSTIMESTAMP,
        CONSTRAINT fk_task_log_run_id FOREIGN KEY (task_run_id) REFERENCES task_run(id) ON DELETE CASCADE
    )""",
    """CREATE TABLE task_run_log (
        id NUMBER PRIMARY KEY,
        task_run_id NUMBER NOT NULL,
        row_number NUMBER NULL,
        column_name VARCHAR2(255) NULL,
        error_type VARCHAR2(50) NULL,
        error_message VARCHAR2(1000) NULL,
        source_value CLOB NULL,
        created_at TIMESTAMP DEFAULT SYSTIMESTAMP,
        CONSTRAINT fk_task_run_log_run_id FOREIGN KEY (task_run_id) REFERENCES task_run(id) ON DELETE CASCADE
    )""",
]

triggers = [
    """CREATE OR REPLACE TRIGGER task_bi
    BEFORE INSERT ON task
    FOR EACH ROW
    BEGIN
      IF :new.id IS NULL THEN
        SELECT task_seq.NEXTVAL INTO :new.id FROM dual;
      END IF;
    END;""",
    """CREATE OR REPLACE TRIGGER task_run_bi
    BEFORE INSERT ON task_run
    FOR EACH ROW
    BEGIN
      IF :new.id IS NULL THEN
        SELECT task_run_seq.NEXTVAL INTO :new.id FROM dual;
      END IF;
    END;""",
    """CREATE OR REPLACE TRIGGER task_schedule_bi
    BEFORE INSERT ON task_schedule
    FOR EACH ROW
    BEGIN
      IF :new.id IS NULL THEN
        SELECT task_schedule_seq.NEXTVAL INTO :new.id FROM dual;
      END IF;
    END;""",
    """CREATE OR REPLACE TRIGGER column_mapping_bi
    BEFORE INSERT ON column_mapping
    FOR EACH ROW
    BEGIN
      IF :new.id IS NULL THEN
        SELECT column_mapping_seq.NEXTVAL INTO :new.id FROM dual;
      END IF;
    END;""",
    """CREATE OR REPLACE TRIGGER task_log_bi
    BEFORE INSERT ON task_log
    FOR EACH ROW
    BEGIN
      IF :new.id IS NULL THEN
        SELECT task_log_seq.NEXTVAL INTO :new.id FROM dual;
      END IF;
    END;""",
    """CREATE OR REPLACE TRIGGER task_run_log_bi
    BEFORE INSERT ON task_run_log
    FOR EACH ROW
    BEGIN
      IF :new.id IS NULL THEN
        SELECT task_run_log_seq.NEXTVAL INTO :new.id FROM dual;
      END IF;
    END;""",
]

indexes = [
    "CREATE INDEX ix_task_is_active_updated_at ON task(is_active, updated_at)",
    "CREATE INDEX ix_task_run_task_id ON task_run(task_id)",
    "CREATE INDEX ix_task_run_status ON task_run(task_id, status)",
    "CREATE INDEX ix_task_run_created ON task_run(started_at DESC)",
    "CREATE INDEX ix_task_schedule_is_active ON task_schedule(is_active)",
    "CREATE INDEX ix_task_schedule_next_run ON task_schedule(next_run_date)",
    "CREATE INDEX ix_column_mapping_task_id ON column_mapping(task_id)",
    "CREATE INDEX ix_column_mapping_is_active ON column_mapping(is_active)",
    "CREATE INDEX ix_task_log_run_id ON task_log(task_run_id)",
    "CREATE INDEX ix_task_run_log_run_id ON task_run_log(task_run_id)",
]

# Execute all
for stmt in sequences + tables + triggers + indexes:
    try:
        cursor.execute(stmt)
        print("  ✓ Success")
    except Exception as e:
        if 'ORA-00955' in str(e) or 'ORA-04043' in str(e):
            print("  ⚠ Already exists")
        else:
            print(f"  ✗ Error: {e}")

conn.commit()
cursor.close()
conn.close()
print("\n✅ Database schema created successfully!")
