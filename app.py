"""
高校图书馆智能问答机器人系统
技术栈: Python 3.11 + Flask + MySQL + jieba + TF-IDF + 余弦相似度
"""
import os, json, uuid
from datetime import datetime
from flask import (Flask, render_template, request, jsonify,
                   redirect, url_for, flash, send_file)
from flask_login import (LoginManager, login_user, logout_user,
                         login_required, current_user)

from config import Config
from models import db, User, FAQ, FAQCategory, Book, ChatHistory, Feedback
from nlp_engine import NLPEngine

# 讯飞星火大模型（兜底回答）
spark_client = None
if Config.SPARK_ENABLED:
    try:
        from spark_api import SparkAPI
        spark_client = SparkAPI(
            app_id=Config.SPARK_APP_ID,
            api_key=Config.SPARK_API_KEY,
            api_secret=Config.SPARK_API_SECRET,
            model_version=Config.SPARK_MODEL
        )
        print('[AI] 讯飞星火大模型已启用')
    except Exception as e:
        print(f'[AI] 讯飞星火加载失败: {e}')

SPARK_SYSTEM_PROMPT = """你是一个高校图书馆的智能咨询助手，名叫"小知"。
请用简洁友好的语气回答用户的问题。
如果问题和图书馆相关，请基于常识给出有帮助的回答。
如果问题完全和图书馆无关（比如天气、做饭、写作业等），也可以简单回答，但最后加一句"如果有图书馆相关的问题也可以随时问我哦"。
回答控制在200字以内。"""

# ════════════════════════ 初始化 ════════════════════════

app = Flask(__name__)
app.config.from_object(Config)

os.makedirs(os.path.join(os.path.dirname(__file__), 'instance'), exist_ok=True)
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

nlp = NLPEngine(threshold=Config.SIMILARITY_THRESHOLD)


@login_manager.user_loader
def load_user(uid):
    return db.session.get(User, int(uid))


def refresh_nlp_index():
    """重新从数据库加载FAQ，构建TF-IDF索引"""
    with app.app_context():
        rows = FAQ.query.filter_by(is_active=True).all()
        data = []
        for r in rows:
            data.append({
                'id': r.id,
                'question': r.question,
                'answer': r.answer,
                'category': r.category.name if r.category else '',
                'keywords': r.keywords or '',
            })
        nlp.build_index(data)
        print(f'[NLP] 索引已构建，共 {len(data)} 条FAQ')


# ════════════════════════ 页面路由 ════════════════════════

@app.route('/')
def index():
    return redirect(url_for('chat') if current_user.is_authenticated else url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('chat'))
    if request.method == 'POST':
        u = User.query.filter_by(username=request.form.get('username', '').strip()).first()
        if u and u.check_password(request.form.get('password', '')):
            login_user(u, remember=True)
            return redirect(url_for('chat'))
        flash('用户名或密码错误', 'error')
    return render_template('login.html')


@app.route('/register', methods=['POST'])
def register():
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    pw = request.form.get('password', '')
    pw2 = request.form.get('confirm_password', '')

    if not all([username, email, pw]):
        flash('请填写完整信息', 'error')
        return redirect(url_for('login'))
    if pw != pw2:
        flash('两次密码不一致', 'error')
        return redirect(url_for('login'))
    if len(pw) < 6:
        flash('密码至少6位', 'error')
        return redirect(url_for('login'))
    if User.query.filter_by(username=username).first():
        flash('用户名已存在', 'error')
        return redirect(url_for('login'))

    u = User(username=username, email=email, nickname=username)
    u.set_password(pw)
    db.session.add(u)
    db.session.commit()
    login_user(u, remember=True)
    flash('注册成功', 'success')
    return redirect(url_for('chat'))


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/chat')
@login_required
def chat():
    cats = FAQCategory.query.order_by(FAQCategory.sort_order).all()
    hot = FAQ.query.filter_by(is_active=True).order_by(FAQ.hit_count.desc()).limit(8).all()
    return render_template('chat.html', categories=cats, hot_faqs=hot)


@app.route('/admin')
@login_required
def admin():
    if current_user.role != 'admin':
        flash('无管理权限', 'error')
        return redirect(url_for('chat'))
    cats = FAQCategory.query.order_by(FAQCategory.sort_order).all()
    faqs = FAQ.query.order_by(FAQ.id.desc()).all()
    books = Book.query.order_by(Book.id.desc()).limit(200).all()
    users = User.query.order_by(User.id).all()
    stats = {
        'faq_count': FAQ.query.count(),
        'book_count': Book.query.count(),
        'user_count': User.query.count(),
        'chat_count': ChatHistory.query.count(),
    }
    return render_template('admin.html', categories=cats, faqs=faqs,
                           books=books, users=users, stats=stats)


# ════════════════════════ 核心问答API ════════════════════════

@app.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    msg = request.get_json().get('message', '').strip()
    if not msg:
        return jsonify({'error': '请输入问题'}), 400

    intent = nlp.detect_intent(msg)
    resp = {}

    if intent == 'greeting':
        name = current_user.nickname or current_user.username
        resp = {
            'type': 'greeting',
            'message': f'{name}你好呀，我是图书馆智能助手小知。有什么关于图书馆的问题尽管问我，我会尽力帮你解答。',
            'suggestions': ['图书馆几点开门', '怎么借书', '帮我查一本书']
        }

    elif intent == 'book_search':
        kw, stype = nlp.extract_book_query(msg)
        books = _search_books(kw, stype)
        if books:
            resp = {
                'type': 'book_result',
                'message': f'为你找到 {len(books)} 本与「{kw}」相关的图书',
                'books': books,
            }
        else:
            resp = {
                'type': 'book_empty',
                'message': f'暂时没有找到与「{kw}」相关的图书，你可以换个关键词试试，或者到一楼服务台向工作人员咨询。',
                'suggestions': ['怎么推荐图书馆买书', '馆际互借是什么怎么用']
            }

    else:  # faq
        results = nlp.match(msg, top_k=3)
        if results:
            best, score = results[0]
            faq_obj = db.session.get(FAQ, best['id'])
            if faq_obj:
                faq_obj.hit_count = (faq_obj.hit_count or 0) + 1
                db.session.commit()

            related = [{'question': r[0]['question']} for r in results[1:]]
            resp = {
                'type': 'faq_answer',
                'message': best['answer'],
                'matched_question': best['question'],
                'category': best['category'],
                'score': round(min(score * 3.2, 0.99), 4),
                'related': related,
            }
        else:
            # FAQ匹配不到 → 尝试调用讯飞星火大模型兜底
            if spark_client:
                try:
                    ai_answer = spark_client.chat(msg, system_prompt=SPARK_SYSTEM_PROMPT, timeout=15)
                    if ai_answer:
                        resp = {
                            'type': 'ai_answer',
                            'message': ai_answer,
                            'suggestions': ['图书馆开馆时间', '怎么借书', '怎么使用知网']
                        }
                    else:
                        resp = {
                            'type': 'fallback',
                            'message': '这个问题我暂时还不太能回答。你可以换一种说法再试试，或者看看下面这些常见问题。如果还是找不到答案，建议到一楼服务台咨询工作人员。',
                            'suggestions': ['图书馆开馆时间', '怎么借书', '怎么使用知网', '自习室在哪里']
                        }
                except Exception as e:
                    print(f'[AI] 调用失败: {e}')
                    resp = {
                        'type': 'fallback',
                        'message': '这个问题我暂时还不太能回答。你可以换一种说法再试试，或者看看下面这些常见问题。',
                        'suggestions': ['图书馆开馆时间', '怎么借书', '怎么使用知网', '自习室在哪里']
                    }
            else:
                resp = {
                    'type': 'fallback',
                    'message': '这个问题我暂时还不太能回答。你可以换一种说法再试试，或者看看下面这些常见问题有没有你想了解的。如果还是找不到答案，建议到一楼服务台咨询工作人员。',
                    'suggestions': ['图书馆开馆时间', '怎么借书', '怎么使用知网', '自习室在哪里']
                }

    # 保存记录
    rec = ChatHistory(
        user_id=current_user.id,
        session_id=str(uuid.uuid4())[:8],
        user_message=msg,
        bot_response=resp.get('message', ''),
        response_type=resp.get('type', 'unknown'),
        matched_faq_id=results[0][0]['id'] if intent == 'faq' and 'results' in dir() and results else None,
        similarity_score=resp.get('score'),
    )
    db.session.add(rec)
    db.session.commit()
    resp['chat_id'] = rec.id
    return jsonify(resp)


@app.route('/api/history')
@login_required
def api_history():
    page = request.args.get('page', 1, type=int)
    q = ChatHistory.query.filter_by(user_id=current_user.id).order_by(ChatHistory.created_at.desc())
    p = q.paginate(page=page, per_page=20, error_out=False)
    return jsonify({
        'records': [{
            'id': r.id,
            'user_message': r.user_message,
            'bot_response': r.bot_response,
            'type': r.response_type,
            'score': r.similarity_score,
            'time': r.created_at.strftime('%Y-%m-%d %H:%M'),
        } for r in p.items],
        'total': p.total, 'pages': p.pages,
    })


@app.route('/api/feedback', methods=['POST'])
@login_required
def api_feedback():
    d = request.get_json()
    fb = Feedback(chat_id=d.get('chat_id'), user_id=current_user.id,
                  rating=d.get('rating'), comment=d.get('comment', ''))
    db.session.add(fb)
    db.session.commit()
    return jsonify({'message': '感谢反馈'})


@app.route('/api/faq/category/<int:cid>')
@login_required
def api_faq_by_cat(cid):
    rows = FAQ.query.filter_by(category_id=cid, is_active=True).all()
    return jsonify([{'id': r.id, 'question': r.question, 'answer': r.answer} for r in rows])


# ════════════════════════ 管理API ════════════════════════

@app.route('/api/admin/faq', methods=['POST'])
@login_required
def admin_add_faq():
    if current_user.role != 'admin':
        return jsonify({'error': '无权限'}), 403
    d = request.get_json()
    f = FAQ(question=d['question'], answer=d['answer'],
            category_id=d.get('category_id'), keywords=d.get('keywords', ''))
    db.session.add(f)
    db.session.commit()
    refresh_nlp_index()
    return jsonify({'message': '添加成功', 'id': f.id})


@app.route('/api/admin/faq/<int:fid>', methods=['PUT'])
@login_required
def admin_update_faq(fid):
    if current_user.role != 'admin':
        return jsonify({'error': '无权限'}), 403
    f = FAQ.query.get_or_404(fid)
    d = request.get_json()
    f.question = d.get('question', f.question)
    f.answer = d.get('answer', f.answer)
    f.category_id = d.get('category_id', f.category_id)
    f.keywords = d.get('keywords', f.keywords)
    db.session.commit()
    refresh_nlp_index()
    return jsonify({'message': '修改成功'})


@app.route('/api/admin/faq/<int:fid>', methods=['DELETE'])
@login_required
def admin_delete_faq(fid):
    if current_user.role != 'admin':
        return jsonify({'error': '无权限'}), 403
    db.session.delete(FAQ.query.get_or_404(fid))
    db.session.commit()
    refresh_nlp_index()
    return jsonify({'message': '已删除'})


@app.route('/api/admin/faq/import', methods=['POST'])
@login_required
def admin_import_faq():
    if current_user.role != 'admin':
        return jsonify({'error': '无权限'}), 403
    file = request.files.get('file')
    if not file:
        return jsonify({'error': '请上传文件'}), 400
    try:
        raw = json.loads(file.read().decode('utf-8'))
        items = raw.get('faqs', raw if isinstance(raw, list) else [])
        n = 0
        for item in items:
            cat = None
            cn = item.get('category')
            if cn:
                cat = FAQCategory.query.filter_by(name=cn).first()
            db.session.add(FAQ(
                question=item['question'], answer=item['answer'],
                category_id=cat.id if cat else None,
                keywords=item.get('keywords', '')))
            n += 1
        db.session.commit()
        refresh_nlp_index()
        return jsonify({'message': f'成功导入 {n} 条'})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/admin/faq/export')
@login_required
def admin_export_faq():
    if current_user.role != 'admin':
        return jsonify({'error': '无权限'}), 403
    data = [{'question': f.question, 'answer': f.answer,
             'category': f.category.name if f.category else '',
             'keywords': f.keywords or ''} for f in FAQ.query.all()]
    path = os.path.join(Config.UPLOAD_FOLDER, 'faq_export.json')
    with open(path, 'w', encoding='utf-8') as fp:
        json.dump({'faqs': data}, fp, ensure_ascii=False, indent=2)
    return send_file(path, as_attachment=True, download_name='faq_export.json')


@app.route('/api/admin/book', methods=['POST'])
@login_required
def admin_add_book():
    if current_user.role != 'admin':
        return jsonify({'error': '无权限'}), 403
    d = request.get_json()
    b = Book(title=d['title'], author=d.get('author',''), publisher=d.get('publisher',''),
             isbn=d.get('isbn',''), publish_year=d.get('publish_year'),
             category=d.get('category',''), call_number=d.get('call_number',''),
             location=d.get('location',''), total_copies=d.get('total_copies',1),
             available_copies=d.get('available_copies',1), description=d.get('description',''))
    db.session.add(b)
    db.session.commit()
    return jsonify({'message': '添加成功', 'id': b.id})


@app.route('/api/admin/book/<int:bid>', methods=['DELETE'])
@login_required
def admin_delete_book(bid):
    if current_user.role != 'admin':
        return jsonify({'error': '无权限'}), 403
    db.session.delete(Book.query.get_or_404(bid))
    db.session.commit()
    return jsonify({'message': '已删除'})


@app.route('/api/admin/stats')
@login_required
def admin_stats():
    if current_user.role != 'admin':
        return jsonify({'error': '无权限'}), 403
    type_dist = dict(db.session.query(
        ChatHistory.response_type, db.func.count(ChatHistory.id)
    ).group_by(ChatHistory.response_type).all())
    hot = FAQ.query.order_by(FAQ.hit_count.desc()).limit(10).all()
    return jsonify({
        'type_distribution': type_dist,
        'hot_faqs': [{'question': f.question, 'hits': f.hit_count or 0} for f in hot],
    })


# ════════════════════════ 用户管理API ════════════════════════

@app.route('/api/admin/users')
@login_required
def admin_list_users():
    """获取所有用户列表"""
    if current_user.role != 'admin':
        return jsonify({'error': '无权限'}), 403
    users = User.query.order_by(User.id).all()
    return jsonify([{
        'id': u.id, 'username': u.username, 'email': u.email,
        'nickname': u.nickname or '', 'role': u.role,
        'created_at': u.created_at.strftime('%Y-%m-%d %H:%M') if u.created_at else ''
    } for u in users])


@app.route('/api/admin/user', methods=['POST'])
@login_required
def admin_add_user():
    """管理员添加用户"""
    if current_user.role != 'admin':
        return jsonify({'error': '无权限'}), 403
    d = request.get_json()
    if not d.get('username') or not d.get('password'):
        return jsonify({'error': '用户名和密码不能为空'}), 400
    if User.query.filter_by(username=d['username']).first():
        return jsonify({'error': '用户名已存在'}), 400
    u = User(username=d['username'], email=d.get('email', f"{d['username']}@stu.edu.cn"),
             nickname=d.get('nickname', d['username']), role=d.get('role', 'user'))
    u.set_password(d['password'])
    db.session.add(u)
    db.session.commit()
    return jsonify({'message': '添加成功', 'id': u.id})


@app.route('/api/admin/user/<int:uid>', methods=['PUT'])
@login_required
def admin_update_user(uid):
    """管理员修改用户信息"""
    if current_user.role != 'admin':
        return jsonify({'error': '无权限'}), 403
    u = User.query.get_or_404(uid)
    d = request.get_json()
    if d.get('nickname'):
        u.nickname = d['nickname']
    if d.get('email'):
        u.email = d['email']
    if d.get('role') and d['role'] in ('user', 'admin'):
        u.role = d['role']
    if d.get('password'):
        u.set_password(d['password'])
    db.session.commit()
    return jsonify({'message': '修改成功'})


@app.route('/api/admin/user/<int:uid>', methods=['DELETE'])
@login_required
def admin_delete_user(uid):
    """管理员删除用户"""
    if current_user.role != 'admin':
        return jsonify({'error': '无权限'}), 403
    if uid == current_user.id:
        return jsonify({'error': '不能删除自己'}), 400
    u = User.query.get_or_404(uid)
    ChatHistory.query.filter_by(user_id=uid).delete()
    db.session.delete(u)
    db.session.commit()
    return jsonify({'message': '已删除'})


# ════════════════════════ 辅助函数 ════════════════════════

def _search_books(keyword, search_type='keyword'):
    q = Book.query
    if search_type == 'title':
        q = q.filter(Book.title.contains(keyword))
    elif search_type == 'author':
        q = q.filter(Book.author.contains(keyword))
    else:
        q = q.filter(db.or_(
            Book.title.contains(keyword),
            Book.author.contains(keyword),
            Book.category.contains(keyword),
            Book.isbn.contains(keyword),
            Book.description.contains(keyword),
        ))
    rows = q.limit(10).all()
    return [{
        'title': b.title, 'author': b.author, 'publisher': b.publisher,
        'isbn': b.isbn, 'year': b.publish_year, 'location': b.location,
        'call_number': b.call_number, 'category': b.category,
        'available': b.available_copies, 'total': b.total_copies,
        'status': '可借' if b.available_copies > 0 else '已借完',
    } for b in rows]


# ════════════════════════ 数据库初始化 ════════════════════════

def init_database():
    """初始化数据库：自动创建MySQL数据库 → 删旧表 → 建表 → 导入模拟数据"""
    # ---- 第一步：确保 MySQL 中数据库已存在 ----
    from config import Config
    import pymysql
    try:
        conn = pymysql.connect(
            host=Config.MYSQL_HOST,
            port=Config.MYSQL_PORT,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            charset='utf8mb4'
        )
        cursor = conn.cursor()
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{Config.MYSQL_DB}` "
            f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        conn.commit()
        cursor.close()
        conn.close()
        print(f'[DB] 数据库 {Config.MYSQL_DB} 已就绪')
    except Exception as e:
        print(f'[DB] 创建数据库失败: {e}')
        print('[DB] 请检查 config.py 中的 MySQL 连接配置是否正确')
        return

    # ---- 第二步：建表并导入数据 ----
    with app.app_context():
        # 先检查是否已有用户数据（说明之前成功初始化过）
        try:
            if User.query.first():
                print('[DB] 数据已存在，跳过初始化')
                return
        except Exception:
            # 表不存在或结构不对，需要重建
            pass

        # 删掉所有旧表，重新按 models.py 的定义创建（保证字段完全一致）
        print('[DB] 正在重建数据库表...')
        db.drop_all()
        db.create_all()
        print('[DB] 数据库表创建完成')

        print('[DB] 初始化数据库...')
        # 用户
        admin = User(username='admin', email='admin@library.edu.cn', role='admin', nickname='管理员')
        admin.set_password('admin123')
        db.session.add(admin)
        tester = User(username='reader01', email='reader01@stu.edu.cn', nickname='张同学')
        tester.set_password('123456')
        db.session.add(tester)

        # FAQ
        with open(os.path.join(os.path.dirname(__file__), 'data', 'faq_data.json'), 'r', encoding='utf-8') as f:
            faq_data = json.load(f)

        cat_map = {}
        for i, c in enumerate(faq_data['categories']):
            obj = FAQCategory(name=c['name'], description=c['description'],
                              color=c['color'], sort_order=i)
            db.session.add(obj)
            db.session.flush()
            cat_map[c['name']] = obj.id

        for item in faq_data['faqs']:
            db.session.add(FAQ(
                question=item['question'], answer=item['answer'],
                category_id=cat_map.get(item.get('category')),
                keywords=item.get('keywords', '')))

        # 书目
        with open(os.path.join(os.path.dirname(__file__), 'data', 'books_data.json'), 'r', encoding='utf-8') as f:
            for b in json.load(f)['books']:
                db.session.add(Book(**b))

        db.session.commit()
        print(f'[DB] 初始化完成: {len(faq_data["faqs"])} 条FAQ, '
              f'{len(cat_map)} 个分类, 2 个用户')


# ════════════════════════ 启动入口 ════════════════════════

if __name__ == '__main__':
    init_database()
    refresh_nlp_index()
    print('\n' + '=' * 56)
    print('   图书馆智能问答机器人系统已启动')
    print('   访问地址: http://127.0.0.1:5000')
    print('   管理员: admin / admin123')
    print('   测试用户: reader01 / 123456')
    print('=' * 56 + '\n')
    app.run(debug=True, host='0.0.0.0', port=5000)
