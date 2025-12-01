import os
import socket
import datetime
from flask import Flask
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

app = Flask(__name__)

# --- 1. 資料庫設定 (第一性原則：從環境變數讀取配置，不寫死在代碼裡) ---
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'secret')
DB_HOST = os.getenv('DB_HOST', 'localhost') # 在 Docker 裡這會變成 'database'
DB_NAME = os.getenv('DB_NAME', 'my_app_db')

# 連線字串 (ConnectionString)
DATABASE_URI = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"

# --- 2. 初始化 SQLAlchemy ---
# echo=False 代表不印出每條 SQL (生產環境設定)
engine = create_engine(DATABASE_URI, echo=False)
Base = declarative_base()

# 定義資料表模型 (Schema)
class AccessLog(Base):
    __tablename__ = 'access_logs'
    
    id = Column(Integer, primary_key=True)
    user_name = Column(String(50))
    container_id = Column(String(50))
    access_time = Column(DateTime, default=datetime.datetime.now)

# 自動建立資料表 (如果不存在)
# 這裡包含等待 DB 啟動的重試邏輯會更好，但在 Docker Compose 有 depends_on 暫時足夠
try:
    Base.metadata.create_all(engine)
    print("✅ 資料庫連線成功，資料表已就緒")
except Exception as e:
    print(f"❌ 資料庫連線失敗: {e}")

# 建立 Session 工廠
Session = sessionmaker(bind=engine)

@app.route('/')
def hello():
    user_name = os.getenv('USER_NAME', 'Guest')
    container_id = socket.gethostname()
    
    # --- 3. 寫入資料庫 ---
    session = Session()
    try:
        new_log = AccessLog(user_name=user_name, container_id=container_id)
        session.add(new_log)
        session.commit()
        log_id = new_log.id
    except Exception as e:
        session.rollback()
        return f"Database Error: {e}"
    finally:
        session.close()

    return f"Hello {user_name}! 你的訪問已被存入 MariaDB (ID: {log_id}) 由容器 {container_id} 處理。\n"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)