# modules/data_management/migrations.py
def migrate_employees_contact_columns(engine):
    # ใช้ transaction อัตโนมัติ
    with engine.begin() as conn:
        cols = [row[1] for row in conn.exec_driver_sql("PRAGMA table_info(employees)").fetchall()]
        if "email" not in cols:
            conn.exec_driver_sql("ALTER TABLE employees ADD COLUMN email VARCHAR")
            conn.exec_driver_sql("CREATE UNIQUE INDEX IF NOT EXISTS uq_employees_email ON employees(email)")
        if "phone_number" not in cols:
            conn.exec_driver_sql("ALTER TABLE employees ADD COLUMN phone_number VARCHAR")
            conn.exec_driver_sql("CREATE UNIQUE INDEX IF NOT EXISTS uq_employees_phone_number ON employees(phone_number)")

