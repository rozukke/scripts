import sqlite3
from tatoebatools import ParallelCorpus

DB_PATH = "tatoeba_cmn_eng.db"
BATCH_SIZE = 5000

def create_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Enable WAL mode for faster inserts
    cur.execute("PRAGMA journal_mode=WAL;")
    cur.execute("PRAGMA synchronous=NORMAL;")

    # Metadata table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sentence_pairs (
            id INTEGER PRIMARY KEY,
            source_id INTEGER,
            target_id INTEGER
        );
    """)

    # FTS5 tables storing actual text
    cur.execute("DROP TABLE IF EXISTS cmn_fts;")
    cur.execute("DROP TABLE IF EXISTS eng_fts;")
    cur.execute("CREATE VIRTUAL TABLE cmn_fts USING fts5(text, tokenize='unicode61');")
    cur.execute("CREATE VIRTUAL TABLE eng_fts USING fts5(text, tokenize='unicode61');")

    conn.commit()
    conn.close()

def ingest():
    print("Starting Tatoeba ingestion…")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    pc = ParallelCorpus("cmn", "eng")

    batch_meta = []
    batch_cmn = []
    batch_eng = []

    rowid = 0
    total = 0

    for source, target in pc:
        rowid += 1
        batch_meta.append((rowid, source.sentence_id, target.sentence_id))
        batch_cmn.append((source.text,))
        batch_eng.append((target.text,))

        if len(batch_meta) >= BATCH_SIZE:
            cur.executemany("INSERT INTO sentence_pairs(id, source_id, target_id) VALUES (?, ?, ?);", batch_meta)
            cur.executemany("INSERT INTO cmn_fts(text) VALUES (?);", batch_cmn)
            cur.executemany("INSERT INTO eng_fts(text) VALUES (?);", batch_eng)
            conn.commit()

            total += len(batch_meta)
            print(f"Inserted {total} sentence pairs…")

            batch_meta.clear()
            batch_cmn.clear()
            batch_eng.clear()

    # Insert remaining
    if batch_meta:
        cur.executemany("INSERT INTO sentence_pairs(id, source_id, target_id) VALUES (?, ?, ?);", batch_meta)
        cur.executemany("INSERT INTO cmn_fts(text) VALUES (?);", batch_cmn)
        cur.executemany("INSERT INTO eng_fts(text) VALUES (?);", batch_eng)
        conn.commit()
        total += len(batch_meta)
        print(f"Inserted final {len(batch_meta)} rows. Total: {total}")

    conn.close()
    print("Ingestion complete.")

def query(word, lang="cmn"):
    """
    Query the FTS tables for sentences containing `word`.
    Returns a list of dicts: {"rowid", "source_id", "target_id", "cmn", "eng"}
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    if lang not in ("cmn", "eng"):
        raise ValueError("lang must be 'cmn' or 'eng'")

    table = "cmn_fts" if lang == "cmn" else "eng_fts"

    # FTS5 MATCH query
    rows = cur.execute(
        f"SELECT rowid FROM {table} WHERE text LIKE ? AND length(text) BETWEEN 6 AND 35 ORDER BY RANDOM() LIMIT 1;",
        (f"%{word}%",)
    ).fetchall()

    results = []
    for (rowid,) in rows:
        src_id, tgt_id = cur.execute(
            "SELECT source_id, target_id FROM sentence_pairs WHERE id=?;", (rowid,)
        ).fetchone()

        cmn_text = cur.execute("SELECT text FROM cmn_fts WHERE rowid=?;", (rowid,)).fetchone()[0]
        eng_text = cur.execute("SELECT text FROM eng_fts WHERE rowid=?;", (rowid,)).fetchone()[0]

        results.append({
            "rowid": rowid,
            "source_id": src_id,
            "target_id": tgt_id,
            "cmn": cmn_text,
            "eng": eng_text,
        })

    conn.close()
    return results

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ingest and query Tatoeba cmn->eng sentences in SQLite")
    parser.add_argument("--init", action="store_true", help="Create DB and ingest all sentences")
    parser.add_argument("--query", type=str, help="Word to search for")
    parser.add_argument("--lang", choices=["cmn", "eng"], default="cmn", help="Language to search in")

    args = parser.parse_args()

    if args.init:
        create_db()
        ingest()

    if args.query:
        results = query(args.query, lang=args.lang)
        for r in results:
            print(f"[CMN {r['source_id']}] {r['cmn']}")
            print(f"[ENG {r['target_id']}] {r['eng']}")
            print("---")
