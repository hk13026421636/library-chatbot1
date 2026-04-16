"""
系统配置文件
默认使用 MySQL 数据库，请根据实际情况修改连接信息
"""
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = 'your-secret-key-here'

    # ============ MySQL 数据库配置（默认） ============
    # 请根据你的 MySQL 实际信息修改以下配置
    MYSQL_HOST = '127.0.0.1'
    MYSQL_PORT = 3306
    MYSQL_USER = 'root'
    MYSQL_PASSWORD = 'your_mysql_password'       # 改为你的 MySQL 密码
    MYSQL_DB = 'library_chatbot'

    SQLALCHEMY_DATABASE_URI = (
        f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}'
        f'@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}?charset=utf8mb4'
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

    # ============ NLP 配置 ============
    SIMILARITY_THRESHOLD = 0.20       # 余弦相似度阈值
    MAX_RESULTS = 5                   # 匹配返回最大数量

    # ============ 文件上传 ============
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    # ============ 讯飞星火大模型（兜底回答）============
    # 申请地址：https://xinghuo.xfyun.cn
    # 注册后进入控制台 → 我的应用 → 创建应用 → 获取以下三个值
    SPARK_APP_ID = 'your_app_id'          # 填入你的 APPID
    SPARK_API_KEY = 'your_api_key'        # 填入你的 APIKey
    SPARK_API_SECRET = 'your_api_secret'  # 填入你的 APISecret
    SPARK_MODEL = 'v3.0'       # 模型版本：v1.5/v2.0/v3.0/v3.5/v4.0
    SPARK_ENABLED = False      # 填好Key后改为 True 启用
