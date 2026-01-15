from flask import Flask, render_template, request
import sqlite3
import os

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "tracks.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    search_query = request.args.get('q', '')
    conn = get_db_connection()
    
    if search_query:
        tracks = conn.execute('SELECT * FROM tracks WHERE title LIKE ?', ('%' + search_query + '%',)).fetchall()
    else:
        tracks = conn.execute('SELECT * FROM tracks').fetchall()
    
    conn.close()
    return render_template('index.html', tracks=tracks, search_query=search_query)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
