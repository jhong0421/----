import sqlite3
import logging

class DB:
    def __init__(self):
        self.logger = logging.getLogger('db')
        
    def get_connection(self):
        """取得資料庫連接並自動管理事務"""
        conn = sqlite3.connect('main.db')
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        return conn