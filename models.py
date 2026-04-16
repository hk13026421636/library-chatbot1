"""
数据库模型定义
包含：用户表、FAQ分类表、FAQ问答表、馆藏书目表、聊天记录表、反馈表
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """用户表"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='user', comment='角色: user/admin')
    nickname = db.Column(db.String(50), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    chat_histories = db.relationship('ChatHistory', backref='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class FAQCategory(db.Model):
    """FAQ分类表"""
    __tablename__ = 'faq_categories'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=False, unique=True, comment='分类名称')
    description = db.Column(db.String(200), default='', comment='分类描述')
    color = db.Column(db.String(20), default='#5B8A8A')
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    faqs = db.relationship('FAQ', backref='category', lazy='dynamic')


class FAQ(db.Model):
    """FAQ问答对表"""
    __tablename__ = 'faqs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    question = db.Column(db.Text, nullable=False, comment='问题')
    answer = db.Column(db.Text, nullable=False, comment='答案')
    category_id = db.Column(db.Integer, db.ForeignKey('faq_categories.id'), comment='分类ID')
    keywords = db.Column(db.String(500), default='', comment='关键词,逗号分隔')
    hit_count = db.Column(db.Integer, default=0, comment='命中次数')
    is_active = db.Column(db.Boolean, default=True, comment='是否启用')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Book(db.Model):
    """馆藏书目表"""
    __tablename__ = 'books'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(200), nullable=False, index=True, comment='书名')
    author = db.Column(db.String(100), index=True, comment='作者')
    publisher = db.Column(db.String(100), comment='出版社')
    isbn = db.Column(db.String(20), unique=True, comment='ISBN')
    publish_year = db.Column(db.Integer, comment='出版年')
    category = db.Column(db.String(50), comment='学科分类')
    call_number = db.Column(db.String(50), comment='索书号')
    location = db.Column(db.String(100), comment='馆藏位置')
    total_copies = db.Column(db.Integer, default=1, comment='总册数')
    available_copies = db.Column(db.Integer, default=1, comment='可借册数')
    description = db.Column(db.Text, comment='简介')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ChatHistory(db.Model):
    """聊天记录表"""
    __tablename__ = 'chat_histories'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), comment='用户ID')
    session_id = db.Column(db.String(64), default='', comment='会话ID')
    user_message = db.Column(db.Text, nullable=False, comment='用户消息')
    bot_response = db.Column(db.Text, nullable=False, comment='机器人回复')
    response_type = db.Column(db.String(20), default='faq', comment='回复类型')
    matched_faq_id = db.Column(db.Integer, comment='匹配的FAQ ID')
    similarity_score = db.Column(db.Float, comment='相似度分数')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Feedback(db.Model):
    """用户反馈表"""
    __tablename__ = 'feedbacks'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    chat_id = db.Column(db.Integer, db.ForeignKey('chat_histories.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    rating = db.Column(db.Integer, comment='评分1-5')
    comment = db.Column(db.Text, comment='评价内容')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
