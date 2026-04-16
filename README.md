# 高校图书馆智能问答机器人系统

基于 FAQ 知识库的高校图书馆智能问答系统，采用 jieba 中文分词 + TF-IDF + 余弦相似度实现问句匹配。

## 技术栈

| 层次     | 技术                    |
| -------- | ----------------------- |
| 后端框架 | Python 3.11 + Flask     |
| 数据库   | MySQL 5.7+ (PyMySQL)    |
| 中文分词 | jieba                   |
| 特征提取 | TF-IDF (scikit-learn)   |
| 问句匹配 | 余弦相似度              |
| 前端     | HTML + CSS + JavaScript |

## 系统五大功能模块

1. **知识库管理模块** — FAQ 增删改查、分类管理、批量导入导出
2. **文本处理模块** — jieba 分词、停用词过滤、TF-IDF 特征向量化
3. **问答匹配模块** — 余弦相似度计算、阈值筛选、Top-K 排序
4. **书目查询模块** — 意图识别 + 书名/作者/关键词模糊检索
5. **用户交互模块** — 对话式 Web 界面、历史记录、用户反馈

---

## 安装与启动

### 1. 创建 MySQL 数据库

登录 MySQL，执行：

```sql
CREATE DATABASE library_chatbot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 2. 创建 Conda 虚拟环境

```bash
conda create -n library_bot python=3.11 -y
conda activate library_bot
```
cd library_chatbot
1、python -m venv venv
venv\Scripts\activate
2、 pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
3、 config.py，把 MYSQL_PASSWORD 改成123456
4、运行： python reset_data.py
5、系统python app.py


### 3. 安装依赖

```bash
cd library_chatbot
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 4. 修改数据库配置

打开 `config.py`，修改以下内容为你实际的 MySQL 信息：

```python
MYSQL_HOST = '127.0.0.1'
MYSQL_PORT = 3306
MYSQL_USER = 'root'
MYSQL_PASSWORD = 'your_password'   # 改成你的密码
MYSQL_DB = 'library_chatbot'
```

### 5. 启动系统

```bash
python app.py
```

看到以下输出表示启动成功：

```
========================================================
   图书馆智能问答机器人系统已启动
   访问地址: http://127.0.0.1:5000
   管理员: admin / admin123
   测试用户: reader01 / 123456
========================================================
```

### 6. 打开浏览器

访问 http://127.0.0.1:5000

---

## 账号

| 用户名   | 密码     | 角色                 |
| -------- | -------- | -------------------- |
| admin    | admin123 | 管理员（可进入后台） |
| reader01 | 123456   | 普通读者             |

也可在登录页注册新账号。

---

## 测试用例

### FAQ 问答

| 输入               | 预期回复         |
| ------------------ | ---------------- |
| 图书馆什么时候开门 | 返回开馆时间信息 |
| 怎么借书           | 返回借阅流程     |
| 一次能借多少本     | 返回借阅数量限制 |
| 怎么续借           | 返回续借方式     |
| 知网怎么用         | 返回知网使用方法 |
| 自习室在几楼       | 返回位置信息     |
| 书过期了怎么办     | 返回超期处理方案 |
| 能在图书馆吃东西吗 | 返回饮食规定     |
| 图书馆能充电吗     | 返回充电相关信息 |

### 书目查询

| 输入               | 预期回复           |
| ------------------ | ------------------ |
| 帮我查一下《三体》 | 返回三体馆藏信息   |
| 有没有Python的书   | 返回Python相关图书 |
| 周志华写的书       | 返回《机器学习》   |
| 找一本高等数学     | 返回高数教材       |
| 有没有数据库的书   | 返回数据库相关图书 |

---

## 项目结构

```
library_chatbot/
├── app.py              # Flask 主应用（路由 + API）
├── config.py           # 配置文件（MySQL 连接等）
├── models.py           # 数据库 ORM 模型
├── nlp_engine.py       # NLP 引擎（分词+TF-IDF+余弦相似度）
├── stopwords.txt       # 停用词表
├── requirements.txt    # Python 依赖
├── README.md           # 说明文档
├── data/
│   ├── faq_data.json   # FAQ 模拟数据（37条，6个分类）
│   └── books_data.json # 馆藏书目模拟数据（25本）
├── templates/
│   ├── login.html      # 登录注册页
│   ├── chat.html       # 对话页
│   └── admin.html      # 管理后台
├── uploads/            # 文件上传目录
└── instance/           # 运行时目录
```

---

## 模拟数据

系统内置 37 条 FAQ（6个分类）和 25 本馆藏图书，首次启动时自动写入 MySQL。

| FAQ 分类 | 数量 |
| -------- | ---- |
| 开馆信息 | 4 条 |
| 借阅服务 | 9 条 |
| 馆藏分布 | 5 条 |
| 电子资源 | 5 条 |
| 读者服务 | 7 条 |
| 规章制度 | 5 条 |

---

## 常见问题

**Q: 启动报 ModuleNotFoundError**
```bash
conda activate library_bot
pip install -r requirements.txt
```

**Q: 连接 MySQL 报错**
确认 MySQL 服务已启动，且 `config.py` 中的账号密码正确，数据库已创建。

**Q: 如何调整匹配精度**
修改 `config.py` 中 `SIMILARITY_THRESHOLD`，默认 0.20。增大更严格，减小更宽松。

执行结果：
![登录界面](01_login.png)
![对话界面](02_chat.png)