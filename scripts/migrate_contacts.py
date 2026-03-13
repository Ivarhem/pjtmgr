"""기존 customers 테이블의 담당자 컬럼 → customer_contacts 테이블로 마이그레이션.

실행: python -m scripts.migrate_contacts
- 기존 sales_contact_*, tax_contact_* 데이터를 customer_contacts 행으로 이전
- 이전된 담당자는 is_default=True로 설정
- customer_contacts 테이블이 비어있을 때만 실행 (중복 방지)
- 이전 완료 후 기존 컬럼은 수동으로 DROP (SQLite 제약으로 자동 DROP 불가)
"""
import sqlite3
import sys


DB_PATH = "sales.db"


def migrate():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # customer_contacts 테이블 존재 확인
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='customer_contacts'")
    if not cur.fetchone():
        print("customer_contacts 테이블이 없습니다. 앱을 먼저 실행하여 테이블을 생성하세요.")
        sys.exit(1)

    # 이미 데이터가 있으면 중단
    cur.execute("SELECT COUNT(*) FROM customer_contacts")
    if cur.fetchone()[0] > 0:
        print("customer_contacts에 이미 데이터가 있습니다. 마이그레이션을 건너뜁니다.")
        return

    # 기존 컬럼 존재 여부 확인
    cur.execute("PRAGMA table_info(customers)")
    columns = {row["name"] for row in cur.fetchall()}
    if "sales_contact_name" not in columns:
        print("기존 담당자 컬럼이 이미 제거된 상태입니다.")
        return

    # 마이그레이션
    cur.execute("SELECT id, sales_contact_name, sales_contact_phone, sales_contact_email, "
                "tax_contact_name, tax_contact_phone, tax_contact_email FROM customers")
    rows = cur.fetchall()
    count = 0
    for row in rows:
        # 영업 담당자
        if row["sales_contact_name"]:
            cur.execute(
                "INSERT INTO customer_contacts (customer_id, contact_type, name, phone, email, is_default) "
                "VALUES (?, '영업', ?, ?, ?, 1)",
                (row["id"], row["sales_contact_name"], row["sales_contact_phone"], row["sales_contact_email"]),
            )
            count += 1
        # 세금계산서 담당자
        if row["tax_contact_name"]:
            cur.execute(
                "INSERT INTO customer_contacts (customer_id, contact_type, name, phone, email, is_default) "
                "VALUES (?, '세금계산서', ?, ?, ?, 1)",
                (row["id"], row["tax_contact_name"], row["tax_contact_phone"], row["tax_contact_email"]),
            )
            count += 1

    conn.commit()
    conn.close()
    print(f"마이그레이션 완료: {count}건의 담당자 데이터를 이전했습니다.")


if __name__ == "__main__":
    migrate()
