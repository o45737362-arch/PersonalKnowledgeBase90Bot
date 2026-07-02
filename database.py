import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional

DB_FILE = 'knowledge.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            tags TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    ''')
    
    c.execute('''
        CREATE INDEX IF NOT EXISTS idx_user_id ON notes(user_id)
    ''')
    
    c.execute('''
        CREATE INDEX IF NOT EXISTS idx_tags ON notes(tags)
    ''')
    
    conn.commit()
    conn.close()

def add_note(user_id: int, title: str, content: str, tags: List[str] = None) -> Optional[int]:
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        now = datetime.now().isoformat()
        tags_json = json.dumps(tags) if tags else '[]'
        
        c.execute('''
            INSERT INTO notes (user_id, title, content, tags, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, title, content, tags_json, now, now))
        
        note_id = c.lastrowid
        conn.commit()
        conn.close()
        
        return note_id
    except Exception as e:
        print(f"Error adding note: {e}")
        return None

def get_notes(user_id: int, limit: int = 50) -> List[Dict]:
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        c.execute('''
            SELECT id, title, content, tags, created_at, updated_at
            FROM notes
            WHERE user_id = ?
            ORDER BY updated_at DESC
            LIMIT ?
        ''', (user_id, limit))
        
        rows = c.fetchall()
        conn.close()
        
        notes = []
        for row in rows:
            notes.append({
                'id': row[0],
                'title': row[1],
                'content': row[2],
                'tags': json.loads(row[3]) if row[3] else [],
                'created_at': row[4],
                'updated_at': row[5]
            })
        
        return notes
    except Exception as e:
        print(f"Error getting notes: {e}")
        return []

def search_notes(user_id: int, query: str) -> List[Dict]:
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        # Search in title and content
        c.execute('''
            SELECT id, title, content, tags, created_at, updated_at
            FROM notes
            WHERE user_id = ? 
            AND (title LIKE ? OR content LIKE ?)
            ORDER BY updated_at DESC
        ''', (user_id, f'%{query}%', f'%{query}%'))
        
        rows = c.fetchall()
        conn.close()
        
        notes = []
        for row in rows:
            notes.append({
                'id': row[0],
                'title': row[1],
                'content': row[2],
                'tags': json.loads(row[3]) if row[3] else [],
                'created_at': row[4],
                'updated_at': row[5]
            })
        
        return notes
    except Exception as e:
        print(f"Error searching notes: {e}")
        return []

def get_note_by_id(user_id: int, note_id: int) -> Optional[Dict]:
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        c.execute('''
            SELECT id, title, content, tags, created_at, updated_at
            FROM notes
            WHERE user_id = ? AND id = ?
        ''', (user_id, note_id))
        
        row = c.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row[0],
                'title': row[1],
                'content': row[2],
                'tags': json.loads(row[3]) if row[3] else [],
                'created_at': row[4],
                'updated_at': row[5]
            }
        return None
    except Exception as e:
        print(f"Error getting note: {e}")
        return None

def update_note(user_id: int, note_id: int, content: str) -> bool:
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        now = datetime.now().isoformat()
        
        c.execute('''
            UPDATE notes
            SET content = ?, updated_at = ?
            WHERE user_id = ? AND id = ?
        ''', (content, now, user_id, note_id))
        
        conn.commit()
        affected = c.rowcount
        conn.close()
        
        return affected > 0
    except Exception as e:
        print(f"Error updating note: {e}")
        return False

def delete_note(user_id: int, note_id: int) -> bool:
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        c.execute('''
            DELETE FROM notes
            WHERE user_id = ? AND id = ?
        ''', (user_id, note_id))
        
        conn.commit()
        affected = c.rowcount
        conn.close()
        
        return affected > 0
    except Exception as e:
        print(f"Error deleting note: {e}")
        return False

def get_tags(user_id: int) -> Dict[str, int]:
    try:
        notes = get_notes(user_id, limit=1000)
        tag_counts = {}
        
        for note in notes:
            for tag in note.get('tags', []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        return tag_counts
    except Exception as e:
        print(f"Error getting tags: {e}")
        return {}

def get_notes_by_tag(user_id: int, tag: str) -> List[Dict]:
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        c.execute('''
            SELECT id, title, content, tags, created_at, updated_at
            FROM notes
            WHERE user_id = ? AND tags LIKE ?
            ORDER BY updated_at DESC
        ''', (user_id, f'%"{tag}"%'))
        
        rows = c.fetchall()
        conn.close()
        
        notes = []
        for row in rows:
            notes.append({
                'id': row[0],
                'title': row[1],
                'content': row[2],
                'tags': json.loads(row[3]) if row[3] else [],
                'created_at': row[4],
                'updated_at': row[5]
            })
        
        return notes
    except Exception as e:
        print(f"Error getting notes by tag: {e}")
        return []

def get_stats(user_id: int) -> Dict:
    try:
        notes = get_notes(user_id, limit=1000)
        
        if not notes:
            return {}
        
        total_notes = len(notes)
        
        # Tag stats
        tag_counts = {}
        for note in notes:
            for tag in note.get('tags', []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        # Today's notes
        today = datetime.now().date().isoformat()
        today_notes = sum(1 for note in notes if note['created_at'][:10] == today)
        
        # Average length
        total_length = sum(len(note['content']) for note in notes)
        avg_length = round(total_length / total_notes) if total_notes > 0 else 0
        
        # Most used tag
        most_used_tag = max(tag_counts.items(), key=lambda x: x[1]) if tag_counts else ('None', 0)
        
        return {
            'total_notes': total_notes,
            'total_tags': len(tag_counts),
            'today_notes': today_notes,
            'avg_length': avg_length,
            'most_used_tag': most_used_tag[0],
            'most_used_count': most_used_tag[1],
            'tags': tag_counts
        }
    except Exception as e:
        print(f"Error getting stats: {e}")
        return {}
