"""Optional MySQL adapter for the same evidence schema; SQLite remains the local default."""
from __future__ import annotations
import re
from urllib.parse import urlparse,unquote
from app.registry import ROOT


class MySQLConnection:
    def __init__(self,url):
        import pymysql
        parsed = urlparse(url)
        if not parsed.path.strip('/'):
            raise ValueError('MySQL URL 必须指定已创建的数据库')
        try:
            self.raw = pymysql.connect(host=parsed.hostname or 'localhost',port=parsed.port or 3306,
                user=unquote(parsed.username or ''),password=unquote(parsed.password or ''),
                database=parsed.path.strip('/'),charset='utf8mb4',autocommit=False,
                connect_timeout=15,read_timeout=60,write_timeout=60)
            self.execute('SET FOREIGN_KEY_CHECKS=1')
            sql = (ROOT/'database/schema.mysql.sql').read_text(encoding='utf-8')
            sql = re.sub(r'^--.*$','',sql,flags=re.M)
            for statement in sql.split(';'):
                if statement.strip():
                    self.execute(statement)
            self.raw.commit()
        except Exception:
            if hasattr(self,'raw'):
                self.raw.close()
            # Never echo connection URL, password, or driver DSN exceptions.
            raise RuntimeError('MySQL 连接或建表失败，请检查配置、权限及数据库版本') from None

    def execute(self,sql,params=()):
        if sql=='PRAGMA foreign_key_check':
            cursor = self.raw.cursor()
            cursor.execute('SELECT @@FOREIGN_KEY_CHECKS')
            if cursor.fetchone()[0]!=1:
                raise RuntimeError('MySQL 外键检查被禁用')
            cursor.execute('SELECT 1 WHERE FALSE')
            return cursor
        if 'INSERT OR IGNORE INTO ' in sql:
            table = re.search(r'INSERT OR IGNORE INTO (\w+)',sql).group(1)
            first_key = 'bundle_id' if table in ('tag_definition','label_definition','tag_label_binding','rule_definition') else 'id'
            sql = sql.replace('INSERT OR IGNORE INTO ','INSERT INTO ') + f' ON DUPLICATE KEY UPDATE {first_key}={first_key}'
        cursor = self.raw.cursor()
        cursor.execute(sql.replace('?','%s'),params)
        return cursor

    def __enter__(self):
        return self

    def __exit__(self,kind,value,traceback):
        if kind:
            self.raw.rollback()
        else:
            self.raw.commit()

    def close(self):
        self.raw.close()
