import psycopg
import os
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.getenv("DATABASE_URL")

try:
    # 连接数据库
    with psycopg.connect(DB_URL, autocommit=True) as conn:
        with conn.cursor() as cur:
            # 查找所有跟 checkpoint 相关的表并删除
            cur.execute("""
                DROP TABLE IF EXISTS checkpoints CASCADE;
                DROP TABLE IF EXISTS checkpoint_writes CASCADE;
                DROP TABLE IF EXISTS checkpoint_blobs CASCADE;
                DROP TABLE IF EXISTS checkpoint_migrations CASCADE;
            """)
            print("✅ 数据库状态表已彻底清空！重启 main_api.py 即可。")
except Exception as e:
    print(f"❌ 清除失败: {e}")