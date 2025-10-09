from sqlalchemy import text
from database.connection import engine

def table_exists(conn, name: str) -> bool:
    return conn.execute(text(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=:n"
    ), {"n": name}).fetchone() is not None

def column_exists(conn, table: str, col: str) -> bool:
    rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return any(r[1] == col for r in rows)

def run():
    with engine.begin() as conn:
        # 1) module_permissions
        if not table_exists(conn, "module_permissions"):
            conn.execute(text("""
                CREATE TABLE module_permissions (
                    id INTEGER PRIMARY KEY,
                    employee_id INTEGER NOT NULL,
                    module VARCHAR(50) NOT NULL,
                    can_view BOOLEAN NOT NULL DEFAULT 1,
                    can_edit BOOLEAN NOT NULL DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_perm_employee_module ON module_permissions(employee_id, module)"
            ))

        # 2) employees.role
        if not column_exists(conn, "employees", "password_hash"):
            conn.execute(text("ALTER TABLE employees ADD COLUMN password_hash VARCHAR(255)"))

if __name__ == "__main__":
    run()
