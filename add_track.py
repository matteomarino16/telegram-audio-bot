import sqlite3
import sys

def add_track(title, file_id):
    conn = sqlite3.connect("tracks.db")
    cur = conn.cursor()
    
    try:
        cur.execute("INSERT INTO tracks (title, file_id) VALUES (?, ?)", (title, file_id))
        conn.commit()
        print(f"✅ Traccia aggiunta con successo: '{title}'")
    except Exception as e:
        print(f"❌ Errore durante l'inserimento: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    print("--- Aggiungi Traccia al Database ---")
    if len(sys.argv) == 3:
        title = sys.argv[1]
        file_id = sys.argv[2]
    else:
        title = input("Inserisci il titolo della canzone: ").strip()
        file_id = input("Inserisci il file_id (copialo dal bot Telegram): ").strip()
    
    if title and file_id:
        add_track(title, file_id)
    else:
        print("⚠️ Titolo e file_id sono obbligatori!")
