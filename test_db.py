from app.database import get_connection


with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT id, name, country FROM ports")
        ports = cur.fetchall()

        for port in ports:
            print(port)
