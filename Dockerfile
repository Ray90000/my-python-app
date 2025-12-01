# 使用輕量版 Python
FROM python:3.10-slim

WORKDIR /app

# 安裝 Flask, SQLAlchemy (ORM), PyMySQL (驅動)
# 這是最 Pythonic 的組合，不需要編譯 C 語言擴展，安裝最快
RUN pip install flask sqlalchemy pymysql cryptography

COPY . .

CMD ["python", "app.py"]