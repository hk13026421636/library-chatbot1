"""
NLP 文本处理引擎
核心技术：jieba 中文分词 + TF-IDF 特征提取 + 余弦相似度匹配
"""
import os
import re
import jieba
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class NLPEngine:
    """自然语言处理引擎"""

    def __init__(self, threshold=0.20):
        self.threshold = threshold
        self.stopwords = set()
        self.vectorizer = None
        self.tfidf_matrix = None
        self.faq_list = []
        self._load_stopwords()
        self._load_custom_dict()

    # ─────────── 初始化 ───────────

    def _load_custom_dict(self):
        """加载图书馆领域自定义词典，提升专业术语分词准确性"""
        domain_words = [
            '图书馆', '借阅证', '读者证', '校园卡',
            '借阅', '续借', '还书', '超期', '逾期', '罚款',
            '馆藏', '馆际互借', '文献传递',
            '开馆', '闭馆', '开馆时间', '闭馆时间',
            '自习室', '阅览室', '电子阅览室', '研讨室', '书库',
            '电子资源', '数据库', '知网', '万方', '维普', '超星',
            '索书号', '分类号', 'OPAC',
            '预约', '挂失', '补办', '存包柜',
            '打印', '复印', '扫描', '无线网络', 'WiFi',
        ]
        for w in domain_words:
            jieba.add_word(w)

    def _load_stopwords(self):
        """加载停用词表"""
        path = os.path.join(BASE_DIR, 'stopwords.txt')
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    w = line.strip()
                    if w:
                        self.stopwords.add(w)
        base = {
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人',
            '都', '一', '上', '也', '很', '到', '说', '要', '去', '你',
            '会', '着', '没有', '看', '好', '自己', '这', '他', '她',
            '吗', '吧', '啊', '呢', '哦', '嗯', '呀', '哈', '哪',
            '什么', '请问', '请', '谢谢', '你好', '想', '能', '可以',
            '怎么', '怎样', '如何', '为什么', '哪里', '多少', '几',
            '一个', '一些', '这个', '那个', '一下',
        }
        self.stopwords.update(base)

    # ─────────── 文本预处理 ───────────

    def tokenize(self, text):
        """
        文本预处理流程：
        1. 清洗特殊字符，保留中英文和数字
        2. jieba 精确分词
        3. 去除停用词
        """
        text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', ' ', text)
        text = text.lower().strip()
        words = jieba.lcut(text)
        return [w for w in words if w.strip() and w not in self.stopwords]

    # ─────────── TF-IDF 索引构建 ───────────

    def build_index(self, faq_list):
        """
        对 FAQ 知识库建立 TF-IDF 索引
        faq_list: [{'id', 'question', 'answer', 'category', 'keywords'}, ...]
        """
        self.faq_list = faq_list
        if not faq_list:
            return

        corpus = []
        for faq in faq_list:
            # 将问题 + 关键词合并作为索引文本，提升召回
            combined = faq['question']
            kw = faq.get('keywords', '')
            if kw:
                combined += ' ' + kw.replace(',', ' ').replace('，', ' ')
            tokens = self.tokenize(combined)
            corpus.append(' '.join(tokens))

        self.vectorizer = TfidfVectorizer(
            token_pattern=r'(?u)\b\w+\b',
            max_features=8000,
            ngram_range=(1, 2),
            min_df=1,
            max_df=0.95,
            sublinear_tf=True,
        )
        self.tfidf_matrix = self.vectorizer.fit_transform(corpus)

    # ─────────── 余弦相似度匹配 ───────────

    def match(self, query, top_k=5):
        """
        计算用户问题与知识库的余弦相似度，返回 Top-K 匹配结果
        返回: [(faq_dict, score), ...]
        """
        if self.vectorizer is None or self.tfidf_matrix is None:
            return []

        tokens = self.tokenize(query)
        if not tokens:
            return []

        q_vec = self.vectorizer.transform([' '.join(tokens)])
        sims = cosine_similarity(q_vec, self.tfidf_matrix).flatten()

        indices = sims.argsort()[::-1][:top_k]
        results = []
        for idx in indices:
            score = float(sims[idx])
            if score >= self.threshold:
                results.append((self.faq_list[idx].copy(), round(score, 4)))
        return results

    # ─────────── 意图识别 ───────────

    def detect_intent(self, query):
        """
        基于规则的意图识别
        返回: greeting / book_search / faq / unknown
        """
        q = query.strip()

        # 问候
        greetings = ['你好', '您好', '嗨', '在吗', '早上好', '下午好',
                     '晚上好', 'hello', 'hi', '有人吗', '在不在']
        for g in greetings:
            if g in q.lower():
                return 'greeting'

        # 先排除FAQ类的借阅咨询（怎么借书、借书流程、借书规则等）
        faq_about_borrow = [
            '怎么借', '如何借', '怎样借', '借书流程', '借书规则',
            '借书手续', '办理借', '借阅规', '借阅流', '借阅手',
            '可以借几', '能借几', '借几本', '借多久', '借期',
            '续借', '还书', '超期', '逾期', '过期', '罚款',
            '丢了', '丢失', '遗失', '损坏', '赔偿',
            '预约图书', '馆际互借',
        ]
        for kw in faq_about_borrow:
            if kw in q:
                return 'faq'

        # 书目查询
        book_kws = [
            '查书', '找书', '搜书', '有没有这本', '有没有一本',
            '书名', '作者是', '哪本书', '查找图书', '搜索图书',
            '查询图书', '推荐书', '想看', '想借一本', '找一本',
            '馆藏查询', '库存',
        ]
        for kw in book_kws:
            if kw in q:
                return 'book_search'

        # 包含书名号 → 书目查询
        if '《' in q and '》' in q:
            return 'book_search'

        # 包含"有没有...书" 的模式
        if '有没有' in q and ('书' in q or '本' in q):
            return 'book_search'

        return 'faq'

    # ─────────── 书目查询关键词提取 ───────────

    def extract_book_query(self, query):
        """从查询中提取书名/作者/关键词"""
        # 书名号
        m = re.findall(r'《(.+?)》', query)
        if m:
            return m[0], 'title'

        # 作者
        for pat in [r'作者(?:是|为|叫)?[:：]?\s*(.+?)(?:的|$)',
                    r'(.+?)(?:写的|著的|的书)']:
            hit = re.search(pat, query)
            if hit:
                return hit.group(1).strip(), 'author'

        # 去掉意图词，剩余作为关键词
        noise = ['查书', '找书', '搜书', '借书', '有没有', '有吗',
                 '帮我', '请', '我想', '查找', '搜索', '查询',
                 '想看', '想借', '找一本', '图书', '书']
        cleaned = query
        for w in noise:
            cleaned = cleaned.replace(w, '')
        cleaned = cleaned.strip()
        return cleaned if cleaned else query, 'keyword'
