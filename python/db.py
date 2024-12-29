import sqlite3

def setup():
    global con, cur
    con = sqlite3.connect('smstweet.db')
    cur = con.cursor()
    res = cur.execute("SELECT name FROM sqlite_master WHERE name='users'")
    # users table does not currently exist, set it up
    if res.fetchone() is None:
        query = """
            CREATE TABLE users (
                phone TEXT PRIMARY KEY NOT NULL,
                bearer TEXT NOT NULL,
                bearerExpiration TIMESTAMP NOT NULL,
                refresh TEXT NOT NULL,
                refreshExpiration TIMESTAMP NOT NULL
        );
        """
        cur.execute(query)

def close():
    con.close()

def insert(phone, btoken, rtoken):
    query = "INSERT INTO users VALUES (?, ?, DATETIME(CURRENT_TIMESTAMP, '+2 hours'), ?, DATETIME(CURRENT_TIMESTAMP, '+6 months'))"
    cur.execute(query, [phone, btoken, rtoken])
    con.commit()

def delete(phone):
    query = 'DELETE FROM users WHERE phone = ?'
    cur.execute(query, [phone])
    con.commit()

def select(phone):
    query = 'SELECT * FROM users WHERE phone = ?'
    res = cur.execute(query, [phone])
    return res.fetchone()

def print_db():
    res = cur.execute("SELECT * FROM users")
    for s in res.fetchall():
        print(s)
    
