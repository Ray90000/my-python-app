import os
import socket
import datetime
import time
from flask import Flask
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import OperationalError

app = Flask(__name__)

# --- 1. 配置設定 ---
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'secret')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_NAME = os.getenv('DB_NAME', 'my_app_db')

DATABASE_URI = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"

# --- 2. 關鍵改進：等待資料庫就緒 (Wait for DB) ---
# Time Complexity: O(1) - 最多嘗試固定次數 (MAX_RETRIES)，不會無限迴圈
# Space Complexity: O(1)
def get_db_engine(max_retries=10, delay=3):
    """
    在 Docker 環境中，資料庫啟動通常比 App 慢。
    此函數會阻塞程式執行，直到資料庫連線成功或超過重試次數。
    """
    current_try = 0
    while current_try < max_retries:
        try:
            # 嘗試建立 Engine 並連線
            engine = create_engine(DATABASE_URI, echo=False)
            # 實際戳一下資料庫看活著沒
            with engine.connect() as connection:
                print("✅ [GCP] 資料庫連線成功！")
                return engine
        except OperationalError:
            current_try += 1
            print(f"⚠️ 資料庫尚未就緒，等待 {delay} 秒後重試... ({current_try}/{max_retries})")
            time.sleep(delay)
    
    # 如果重試多次都失敗，拋出錯誤讓容器崩潰重啟 (Let it crash)
    raise Exception("❌ 無法連線到資料庫，請檢查 MariaDB 容器狀態。")

# 取得 Engine (這行會卡住，直到 DB 準備好)
engine = get_db_engine()
Base = declarative_base()

# --- 3. 定義模型 (順序正確：先畫圖) ---
class AccessLog(Base):
    __tablename__ = 'access_logs'
    
    id = Column(Integer, primary_key=True)
    user_name = Column(String(50))
    container_id = Column(String(50))
    access_time = Column(DateTime, default=datetime.datetime.now)

# --- 4. 建立資料表 (順序正確：後蓋房) ---
try:
    Base.metadata.create_all(engine)
    print("✅ 資料表 'access_logs' 檢查/建立完成")
except Exception as e:
    print(f"❌ 建立資料表失敗 (這不應該發生): {e}")

Session = sessionmaker(bind=engine)

@app.route('/')
def hello():
    user_name = os.getenv('USER_NAME', 'Guest')
    container_id = socket.gethostname()
    
    session = Session()
    try:
        new_log = AccessLog(user_name=user_name, container_id=container_id)
        session.add(new_log)
        session.commit()
        log_id = new_log.id
        msg = f"Hello {user_name}! GCP 部署成功！ID: {log_id} (Container: {container_id})\n"
    except Exception as e:
        session.rollback()
        msg = f"Database Error: {e}"
    finally:
        session.close()

    return msg

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```csv