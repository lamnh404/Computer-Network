#
# Copyright (C) 2025 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course.
#

"""
db.simple_chat_db
~~~~~~~~~~~~~~~~~~~

Simplified database operations for simple chat application.
Uses SQLite to store messages and users.
"""

import sqlite3
import json
import time
import os
from contextlib import contextmanager

# Database file path
DB_PATH = os.path.join(os.path.dirname(__file__), 'p2p_chat.db')


@contextmanager
def get_db_connection():
    """
    Context manager for database connections.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """
    Initialize the database with simplified schema.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Users table
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS users
                       (
                           username
                           TEXT
                           PRIMARY
                           KEY,
                           password
                           TEXT,
                           created_at
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP
                       )
                       ''')

        # Messages table
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS messages
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           username
                           TEXT,
                           content
                           TEXT,
                           channel
                           TEXT
                           DEFAULT
                           'general',
                           timestamp
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP,
                           FOREIGN
                           KEY
                       (
                           username
                       ) REFERENCES users
                       (
                           username
                       )
                           )
                       ''')

        # Active users table to track who is currently in the chat room
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS active_users
                       (
                           username
                           TEXT
                           PRIMARY
                           KEY,
                           last_seen
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP,
                           FOREIGN
                           KEY
                       (
                           username
                       ) REFERENCES users
                       (
                           username
                       )
                           )
                       ''')

        conn.commit()
        print("[DB] Database initialized successfully")
        return True


def save_message(username, msg, channel='general'):
    """
    Save a message to database.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                           INSERT INTO messages (username, content, channel)
                           VALUES (?, ?, ?)
                           ''', (username, msg, channel))
            conn.commit()
            return True
    except Exception as e:
        print("[DB] Error saving message: {}".format(e))
        return False

def load_messages(channel='general', limit=100):
    """
    Load messages from database for a specific channel.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                           SELECT username, content, channel, timestamp
                           FROM messages
                           WHERE channel = ?
                           ORDER BY timestamp DESC
                           LIMIT ?
                           ''', (channel, limit))
            return [dict(row) for row in cursor.fetchall()][::-1]  # Reverse to get chronological order
    except Exception as e:
        print("[DB] Error loading messages: {}".format(e))
        return []

def save_user(username):
    """
    Save a user to database.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                           INSERT
                           OR IGNORE INTO users (username) VALUES (?)
                           ''', (username,))
            conn.commit()
            return True
    except Exception as e:
        print("[DB] Error saving user: {}".format(e))
        return False


def save_user_with_password(username, password):
    """
    Save a user with password to database.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                           INSERT INTO users (username, password)
                           VALUES (?, ?)
                           ''', (username, password))
            conn.commit()
            return True
    except sqlite3.IntegrityError:
        print("[DB] Username already exists: {}".format(username))
        return False
    except Exception as e:
        print("[DB] Error saving user: {}".format(e))
        return False


def verify_user(username, password):
    """
    Verify user credentials.
    Returns True if username and password match, False otherwise.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                           SELECT password
                           FROM users
                           WHERE username = ?
                           ''', (username,))
            row = cursor.fetchone()
            if row and row['password'] == password:
                return True
            return False
    except Exception as e:
        print("[DB] Error verifying user: {}".format(e))
        return False


def get_users():
    """
    Get all users.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT username FROM users ORDER BY username')
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print("[DB] Error getting users: {}".format(e))
        return []

    """
    Save a message to database.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                           INSERT INTO messages (username, content, channel)
                           VALUES (?, ?, ?)
                           ''', (username, content, channel))
            conn.commit()
            return True
    except Exception as e:
        print("[DB] Error saving message: {}".format(e))
        return False


def mark_user_active(username):
    """
    Mark a user as active in the chat room (updates their last_seen timestamp).
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                           INSERT INTO active_users (username, last_seen)
                           VALUES (?, CURRENT_TIMESTAMP) ON CONFLICT(username) 
                DO
                           UPDATE SET last_seen = CURRENT_TIMESTAMP
                           ''', (username,))
            # print("[DB] Marked user as active: {}".format(username))
            conn.commit()
            return True
    except Exception as e:
        print("[DB] Error marking user active: {}".format(e))
        return False


def remove_user_active(username):
    """
    Remove a user from active users list.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM active_users WHERE username = ?', (username,))
            conn.commit()
            return True
    except Exception as e:
        print("[DB] Error removing active user: {}".format(e))
        return False


def get_active_users(timeout_seconds=60):
    """
    Get list of active users (those who have been seen within timeout_seconds).
    Default timeout is 60 seconds.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                           SELECT username, last_seen
                           FROM active_users
                           WHERE datetime(last_seen) > datetime('now', '-' || ? || ' seconds')
                           ORDER BY username
                           ''', (timeout_seconds,))
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print("[DB] Error getting active users: {}".format(e))
        return []


def cleanup_inactive_users(timeout_seconds=60):
    """
    Remove users who haven't been active for more than timeout_seconds.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                           DELETE
                           FROM active_users
                           WHERE datetime(last_seen) <= datetime('now', '-' || ? || ' seconds')
                           ''', (timeout_seconds,))
            deleted = cursor.rowcount
            conn.commit()
            if deleted > 0:
                print("[DB] Cleaned up {} inactive users".format(deleted))
            return True
    except Exception as e:
        print("[DB] Error cleaning up inactive users: {}".format(e))
        return False