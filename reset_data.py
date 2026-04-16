"""
数据重置脚本 - 清空数据库并导入大量模拟数据
使用方法：python reset_data.py
功能：清空所有表 → 导入120+条FAQ → 导入10000+本图书 → 创建用户
"""
import os
import json
import random
from datetime import datetime

# 必须在导入app之前设置
import sys
sys.path.insert(0, os.path.dirname(__file__))

from app import app, db, nlp
from models import User, FAQCategory, FAQ, Book, ChatHistory, Feedback
from config import Config


def reset_all():
    with app.app_context():
        print('[重置] 正在重建所有数据表...')
        db.drop_all()
        db.create_all()
        print('[重置] 数据表重建完成')

        # ==================== 创建用户 ====================
        print('[用户] 创建用户...')
        admin = User(username='admin', email='admin@library.edu.cn', role='admin', nickname='管理员')
        admin.set_password('admin123')
        db.session.add(admin)

        for i in range(1, 6):
            u = User(username=f'reader{i:02d}', email=f'reader{i:02d}@stu.edu.cn', nickname=f'测试用户{i}')
            u.set_password('123456')
            db.session.add(u)
        db.session.commit()
        print('[用户] 创建完成: 1个管理员 + 5个测试用户')

        # ==================== 导入FAQ ====================
        print('[FAQ] 导入FAQ知识库...')
        faq_path = os.path.join(os.path.dirname(__file__), 'data', 'faq_data.json')
        with open(faq_path, 'r', encoding='utf-8') as f:
            faq_data = json.load(f)

        cat_map = {}
        for i, c in enumerate(faq_data['categories']):
            obj = FAQCategory(name=c['name'], description=c['description'],
                              color=c['color'], sort_order=i)
            db.session.add(obj)
            db.session.flush()
            cat_map[c['name']] = obj.id

        for item in faq_data['faqs']:
            faq = FAQ(
                question=item['question'],
                answer=item['answer'],
                category_id=cat_map.get(item.get('category')),
                keywords=item.get('keywords', ''),
                hit_count=random.randint(0, 200)
            )
            db.session.add(faq)
        db.session.commit()
        faq_count = FAQ.query.count()
        print(f'[FAQ] 导入完成: {faq_count} 条FAQ, {len(cat_map)} 个分类')

        # ==================== 导入基础图书 ====================
        print('[图书] 导入基础图书数据...')
        books_path = os.path.join(os.path.dirname(__file__), 'data', 'books_data.json')
        with open(books_path, 'r', encoding='utf-8') as f:
            for b in json.load(f)['books']:
                db.session.add(Book(**b))
        db.session.commit()

        # ==================== 批量生成图书 ====================
        print('[图书] 正在批量生成10000+本图书数据，请稍等...')
        generate_mass_books()
        book_count = Book.query.count()
        print(f'[图书] 导入完成: 共 {book_count} 本图书')

        # ==================== 重建NLP索引 ====================
        print('[NLP] 重建索引...')
        from app import refresh_nlp_index
        refresh_nlp_index()

        print()
        print('=' * 50)
        print(f'  数据重置完成！')
        print(f'  FAQ: {faq_count} 条')
        print(f'  图书: {book_count} 本')
        print(f'  用户: 6 个 (admin/admin123, reader01~05/123456)')
        print('=' * 50)


def generate_mass_books():
    """批量生成大量模拟图书数据"""

    # ===== 计算机类 =====
    cs_books = [
        ("Python程序设计", ["张三", "李四", "王五", "赵六", "刘七"]),
        ("Java程序设计基础", ["陈明", "王刚", "李强", "赵伟", "孙杰"]),
        ("C语言程序设计", ["谭浩强", "王志坚", "张铭", "刘畅", "周明"]),
        ("C++面向对象程序设计", ["郑莉", "董渊", "何洁月", "王强", "李明"]),
        ("数据结构", ["严蔚敏", "吴伟民", "陈越", "殷人昆", "耿国华"]),
        ("数据结构与算法", ["王红梅", "胡明", "邹永林", "张铭", "刘峰"]),
        ("操作系统原理", ["汤小丹", "梁红兵", "庞丽萍", "张尧学", "陈向群"]),
        ("计算机组成原理", ["唐朔飞", "白中英", "蒋本珊", "王诚", "袁春风"]),
        ("计算机网络技术", ["谢希仁", "吴功宜", "张曾科", "王志文", "蔡开裕"]),
        ("数据库原理与应用", ["王珊", "萨师煊", "史嘉权", "何玉洁", "李建中"]),
        ("软件工程导论", ["张海藩", "牟永敏", "齐治昌", "朱少民", "邹欣"]),
        ("人工智能导论", ["王万良", "蔡自兴", "龚怡宏", "朱福喜", "林尧瑞"]),
        ("机器学习基础", ["周志华", "李航", "刘铁岩", "邱锡鹏", "张志华"]),
        ("深度学习原理", ["伊恩·古德费洛", "花书", "邱锡鹏", "阿斯顿·张", "李沐"]),
        ("自然语言处理", ["何晗", "宗成庆", "冯志伟", "刘挺", "赵铁军"]),
        ("计算机图形学", ["孙家广", "胡事民", "倪明田", "吴恩达", "唐泽圣"]),
        ("编译原理", ["陈火旺", "刘春林", "蒋宗礼", "张素琴", "王生原"]),
        ("密码学与网络安全", ["杨义先", "王育民", "卢开澄", "张焕国", "冯登国"]),
        ("Linux系统管理", ["鸟哥", "刘遄", "王达", "马哥", "杨明华"]),
        ("Web前端开发技术", ["陆凌牛", "刘德山", "Flanagan", "黄勇", "阮一峰"]),
        ("移动应用开发", ["郭霖", "任玉刚", "鸿洋", "李刚", "明日科技"]),
        ("云计算与大数据", ["刘鹏", "陆嘉恒", "林子雨", "王珊", "孟小峰"]),
        ("物联网技术概论", ["吴功宜", "马建", "刘云浩", "桂小林", "王志良"]),
        ("区块链技术原理", ["邹均", "张海宁", "长铗", "韩锋", "杨保华"]),
        ("网络爬虫开发", ["崔庆才", "韦玮", "范传辉", "刘硕", "宋天龙"]),
        ("数据挖掘概念与技术", ["韩家炜", "Jiawei Han", "范明", "孟小峰", "王珊"]),
        ("信息检索导论", ["王斌", "Christopher Manning", "花芳", "张敏", "刘奕群"]),
        ("计算机视觉", ["马少平", "Richard Szeliski", "章毓晋", "贾云得", "艾海舟"]),
        ("算法设计与分析", ["王晓东", "屈婉玲", "刘田", "张立昂", "陈国良"]),
        ("离散数学", ["耿素云", "屈婉玲", "张立昂", "左孝凌", "朱保平"]),
    ]

    # ===== 文学类 =====
    lit_books = [
        ("红楼梦", "曹雪芹"), ("西游记", "吴承恩"), ("水浒传", "施耐庵"), ("三国演义", "罗贯中"),
        ("围城", "钱锺书"), ("活着", "余华"), ("平凡的世界", "路遥"), ("白鹿原", "陈忠实"),
        ("三体", "刘慈欣"), ("人生", "路遥"), ("许三观卖血记", "余华"), ("兄弟", "余华"),
        ("骆驼祥子", "老舍"), ("茶馆", "老舍"), ("边城", "沈从文"), ("呐喊", "鲁迅"),
        ("彷徨", "鲁迅"), ("子夜", "茅盾"), ("家", "巴金"), ("雷雨", "曹禺"),
        ("穆斯林的葬礼", "霍达"), ("尘埃落定", "阿来"), ("长恨歌", "王安忆"), ("繁花", "金宇澄"),
        ("芙蓉镇", "古华"), ("黄金时代", "王小波"), ("废都", "贾平凹"), ("秦腔", "贾平凹"),
        ("额尔古纳河右岸", "迟子建"), ("推拿", "毕飞宇"), ("蛙", "莫言"), ("红高粱家族", "莫言"),
        ("檀香刑", "莫言"), ("丰乳肥臀", "莫言"), ("生死疲劳", "莫言"), ("狼图腾", "姜戎"),
        ("百年孤独", "加西亚·马尔克斯"), ("霍乱时期的爱情", "加西亚·马尔克斯"),
        ("1984", "乔治·奥威尔"), ("动物农场", "乔治·奥威尔"),
        ("老人与海", "海明威"), ("了不起的盖茨比", "菲茨杰拉德"),
        ("傲慢与偏见", "简·奥斯汀"), ("简爱", "夏洛蒂·勃朗特"),
        ("巴黎圣母院", "雨果"), ("悲惨世界", "雨果"),
        ("安娜·卡列尼娜", "托尔斯泰"), ("战争与和平", "托尔斯泰"),
        ("罪与罚", "陀思妥耶夫斯基"), ("卡拉马佐夫兄弟", "陀思妥耶夫斯基"),
        ("变形记", "卡夫卡"), ("城堡", "卡夫卡"),
        ("追风筝的人", "卡勒德·胡赛尼"), ("小王子", "圣埃克苏佩里"),
        ("挪威的森林", "村上春树"), ("海边的卡夫卡", "村上春树"),
        ("人间失格", "太宰治"), ("雪国", "川端康成"),
    ]

    # ===== 数学类 =====
    math_books = [
        ("高等数学", ["同济大学数学系", "华东师大", "北大数学系", "陈文灯", "李永乐"]),
        ("线性代数", ["同济大学", "居余马", "李永乐", "张宇", "汤家凤"]),
        ("概率论与数理统计", ["浙大", "陈希孺", "盛骤", "茆诗松", "何书元"]),
        ("数学分析", ["华东师大", "陈纪修", "卓里奇", "裴礼文", "梅加强"]),
        ("实变函数", ["周民强", "胡适耕", "夏道行", "程其襄", "郑维行"]),
        ("复变函数", ["西安交大", "钟玉泉", "方企勤", "余家荣", "史济怀"]),
        ("常微分方程", ["王高雄", "丁同仁", "李勇", "阿诺尔德", "东来"]),
        ("偏微分方程", ["陈恕行", "谷超豪", "李大潜", "姜礼尚", "周蜀林"]),
        ("数值分析", ["李庆扬", "关治", "蒋尔雄", "颜庆津", "林成森"]),
        ("运筹学", ["钱颂迪", "胡富昌", "孙文瑜", "刘桂真", "韩继业"]),
        ("拓扑学", ["尤承业", "Armstrong", "Munkres", "熊金城", "江泽涵"]),
        ("抽象代数", ["聂灵沼", "丘维声", "张禾瑞", "姚慕生", "Artin"]),
        ("数论导引", ["华罗庚", "潘承洞", "柯召", "陈景润", "闵嗣鹤"]),
        ("组合数学", ["Richard Brualdi", "卢开澄", "柳柏濂", "万大庆", "林寿"]),
        ("图论", ["王树禾", "Bondy", "Diestel", "耿素云", "张先迪"]),
    ]

    # ===== 经济管理类 =====
    econ_books = [
        ("微观经济学", ["高鸿业", "曼昆", "范里安", "平狄克", "张维迎"]),
        ("宏观经济学", ["高鸿业", "曼昆", "多恩布什", "布兰查德", "萨克斯"]),
        ("政治经济学", ["逄锦聚", "宋涛", "张维达", "吴树青", "卫兴华"]),
        ("会计学原理", ["陈国辉", "葛家澍", "戴德明", "刘永泽", "唐国平"]),
        ("财务管理", ["荆新", "王化成", "刘淑莲", "陆正飞", "张先治"]),
        ("管理学原理", ["周三多", "罗宾斯", "斯蒂芬·罗宾斯", "芮明杰", "王凤彬"]),
        ("市场营销学", ["吴健安", "菲利普·科特勒", "郭国庆", "纪宝成", "符国群"]),
        ("国际贸易理论", ["薛荣久", "海闻", "克鲁格曼", "张玉卿", "杨全发"]),
        ("金融学", ["黄达", "兹维·博迪", "米什金", "陈雨露", "曹龙骐"]),
        ("统计学", ["贾俊平", "袁卫", "曾五一", "David Moore", "李金昌"]),
        ("投资学", ["兹维·博迪", "威廉·夏普", "刘红忠", "张亦春", "赵锡军"]),
        ("保险学", ["魏华林", "孙祁祥", "王绪瑾", "许谨良", "李学峰"]),
        ("电子商务概论", ["白东蕊", "邵兵家", "杨坚争", "黄敏学", "李洪心"]),
        ("人力资源管理", ["加里·德斯勒", "陈维政", "董克用", "林新奇", "赵曙明"]),
        ("供应链管理", ["马士华", "苏尼尔·乔普拉", "陈荣秋", "刘伟", "宋华"]),
    ]

    # ===== 物理化学类 =====
    phys_chem = [
        ("大学物理", ["马文蔚", "赵凯华", "张三慧", "吴百诗", "卢德馨"]),
        ("量子力学", ["曾谨言", "格里菲斯", "周世勋", "陈鄂生", "苏汝铉"]),
        ("电磁学", ["赵凯华", "梁昆淼", "郭硕鸿", "陈秉乾", "贾瑞皋"]),
        ("热力学与统计物理", ["汪志诚", "林宗涵", "苏汝铉", "北大物理", "王竹溪"]),
        ("普通化学", ["浙大", "赵士铎", "华彤文", "北大化学", "申泮文"]),
        ("有机化学", ["邢其毅", "汪小兰", "高鸿宾", "曾昭琼", "胡宏纹"]),
        ("无机化学", ["宋天佑", "武汉大学", "北师大", "大连理工", "张祖德"]),
        ("分析化学", ["武汉大学", "华中师大", "李发美", "林树昌", "孙毓庆"]),
        ("物理化学", ["傅献彩", "朱文涛", "李松林", "沈文霞", "姚天扬"]),
        ("材料科学基础", ["胡赓祥", "蔡珣", "余永宁", "石德珂", "刘智恩"]),
    ]

    # ===== 外语类 =====
    lang_books = [
        ("大学英语综合教程", ["李荫华", "夏国佐", "王大伟", "束定芳", "季佩英"]),
        ("新视野大学英语", ["郑树棠", "胡壮麟", "总主编", "外研社", "周富强"]),
        ("英语语法新思维", ["张满胜", "薄冰", "章振邦", "张道真", "赖世雄"]),
        ("英语词汇学教程", ["汪榕培", "王德春", "陆国强", "张维友", "胡壮麟"]),
        ("英美文学选读", ["吴伟仁", "刘炳善", "陈嘉", "王守仁", "李公昭"]),
        ("日语综合教程", ["陈小芬", "皮细庚", "周平", "彭广陆", "曹大峰"]),
        ("基础韩国语", ["刘吉文", "金重燮", "崔博光", "林从纲", "太平武"]),
        ("法语综合教程", ["范晓雷", "毛意忠", "马晓宏", "陈建伟", "曹德明"]),
        ("德语综合教程", ["梁敏", "聂黎曦", "朱建华", "殷桐生", "王京平"]),
        ("翻译理论与实践", ["张培基", "陈宏薇", "冯庆华", "许渊冲", "庄绎传"]),
    ]

    # ===== 历史哲学类 =====
    hist_phil = [
        ("中国近现代史纲要", ["本书编写组", "高教出版社", "沙健孙", "李捷", "王顺生"]),
        ("中国通史", ["白寿彝", "范文澜", "翦伯赞", "吕思勉", "钱穆"]),
        ("世界通史", ["齐世荣", "吴于廑", "斯塔夫里阿诺斯", "王斯德", "刘祚昌"]),
        ("西方哲学史", ["赵敦华", "罗素", "梯利", "斯通普夫", "张志伟"]),
        ("中国哲学史", ["冯友兰", "北大哲学系", "郭齐勇", "方立天", "张岱年"]),
        ("马克思主义基本原理", ["本书编写组", "高教出版社", "陈先达", "庄福龄", "杨耕"]),
        ("逻辑学", ["金岳霖", "何向东", "陈波", "王路", "宋文坚"]),
        ("伦理学", ["罗国杰", "王海明", "唐凯麟", "魏英敏", "万俊人"]),
        ("美学原理", ["叶朗", "朱光潜", "宗白华", "李泽厚", "彭富春"]),
        ("社会学概论", ["郑杭生", "费孝通", "王思斌", "陆学艺", "李强"]),
    ]

    # ===== 教育心理类 =====
    edu_psy = [
        ("教育学原理", ["王道俊", "扈中平", "全国十二所", "叶澜", "袁振国"]),
        ("教育心理学", ["陈琦", "张大均", "皮连生", "冯忠良", "莫雷"]),
        ("普通心理学", ["彭聃龄", "梁宁建", "黄希庭", "叶奕乾", "张春兴"]),
        ("发展心理学", ["林崇德", "朱智贤", "桑标", "雷雳", "周宗奎"]),
        ("社会心理学", ["金盛华", "侯玉波", "周晓虹", "乐国安", "沙莲香"]),
        ("心理测量学", ["郑日昌", "金瑜", "戴海琦", "漆书青", "缪小春"]),
        ("课程与教学论", ["王本陆", "钟启泉", "张华", "丛立新", "靳玉乐"]),
        ("中外教育史", ["吴式颖", "孙培青", "王炳照", "郭齐家", "滕大春"]),
        ("教育研究方法", ["裴娣娜", "刘良华", "袁振国", "叶澜", "陈向明"]),
        ("学前教育学", ["黄人颂", "刘晓东", "庞丽娟", "虞永平", "朱家雄"]),
    ]

    # ===== 法学类 =====
    law_books = [
        ("法理学", ["张文显", "沈宗灵", "朱景文", "孙国华", "舒国滢"]),
        ("宪法学", ["许崇德", "周叶中", "林来梵", "韩大元", "胡锦光"]),
        ("民法学", ["王利明", "魏振瀛", "梁慧星", "江平", "王泽鉴"]),
        ("刑法学", ["张明楷", "高铭暄", "马克昌", "陈兴良", "周光权"]),
        ("行政法与行政诉讼法", ["姜明安", "罗豪才", "应松年", "马怀德", "杨建顺"]),
        ("商法学", ["范健", "赵旭东", "施天涛", "王保树", "覃有土"]),
        ("民事诉讼法", ["江伟", "张卫平", "宋朝武", "谭秋桂", "常怡"]),
        ("刑事诉讼法", ["陈光中", "陈瑞华", "宋英辉", "程荣斌", "徐静村"]),
        ("国际法", ["梁西", "王铁崖", "邵津", "贺其治", "周鲠生"]),
        ("知识产权法", ["吴汉东", "刘春田", "李明德", "郑成思", "王迁"]),
    ]

    publishers = [
        "清华大学出版社", "北京大学出版社", "高等教育出版社", "人民邮电出版社",
        "机械工业出版社", "电子工业出版社", "科学出版社", "中国人民大学出版社",
        "复旦大学出版社", "浙江大学出版社", "武汉大学出版社", "中国法制出版社",
        "人民文学出版社", "商务印书馆", "中华书局", "外语教学与研究出版社",
        "上海外语教育出版社", "译林出版社", "中信出版社", "法律出版社",
        "作家出版社", "南海出版公司", "湖南文艺出版社", "江苏凤凰文艺出版社",
        "上海译文出版社", "北京师范大学出版社", "华东师范大学出版社",
        "西安交通大学出版社", "东南大学出版社", "同济大学出版社",
    ]

    locations_map = {
        "计算机": ("三楼A区", "三楼B区"),
        "文学": ("二楼C区", "二楼D区"),
        "数学": ("三楼C区",),
        "经济学": ("二楼A区",),
        "管理学": ("二楼A区",),
        "物理": ("三楼D区",),
        "化学": ("三楼D区",),
        "材料": ("三楼D区",),
        "外语": ("二楼F区",),
        "历史": ("二楼E区",),
        "哲学": ("二楼B区",),
        "教育学": ("二楼B区",),
        "心理学": ("二楼B区",),
        "法学": ("二楼A区",),
    }

    call_number_prefixes = {
        "计算机": "TP3", "文学": "I2", "数学": "O1", "经济学": "F0",
        "管理学": "C93", "物理": "O4", "化学": "O6", "材料": "TB3",
        "外语": "H31", "历史": "K", "哲学": "B", "教育学": "G4",
        "心理学": "B84", "法学": "D9",
    }

    isbn_set = set()
    book_id = 100  # 从100开始编号避免和基础数据冲突
    batch = []

    def gen_isbn():
        while True:
            isbn = f"978{''.join([str(random.randint(0,9)) for _ in range(10)])}"
            if isbn not in isbn_set:
                isbn_set.add(isbn)
                return isbn

    def add_books(title_base, authors, category, editions_range=(1,4)):
        nonlocal book_id
        for author in (authors if isinstance(authors, list) else [authors]):
            for ed in range(random.randint(*editions_range)):
                book_id += 1
                year = random.randint(2005, 2024)
                suffix = f"（第{ed+1}版）" if ed > 0 else ""
                title = f"{title_base}{suffix}"
                pub = random.choice(publishers)
                cat = category
                locs = locations_map.get(cat, ("二楼A区",))
                loc = random.choice(locs)
                prefix = call_number_prefixes.get(cat, "Z")
                call_num = f"{prefix}{random.randint(1,999)}/{book_id}"
                total = random.randint(1, 8)
                avail = random.randint(0, total)
                batch.append(Book(
                    title=title, author=author, publisher=pub,
                    isbn=gen_isbn(), publish_year=year,
                    category=cat, call_number=call_num,
                    location=loc, total_copies=total,
                    available_copies=avail,
                    description=f"{title} - {author} 编著"
                ))

    # 生成计算机类图书
    for title, authors in cs_books:
        add_books(title, authors, "计算机", (1, 3))

    # 文学类
    for title, author in lit_books:
        for _ in range(random.randint(1, 3)):
            book_id += 1
            pub = random.choice(["人民文学出版社", "译林出版社", "上海译文出版社", "南海出版公司", "中信出版社", "作家出版社", "江苏凤凰文艺出版社", "湖南文艺出版社"])
            total = random.randint(2, 10)
            batch.append(Book(
                title=title, author=author, publisher=pub,
                isbn=gen_isbn(), publish_year=random.randint(2000, 2024),
                category="文学", call_number=f"I2{random.randint(1,999)}/{book_id}",
                location=random.choice(["二楼C区", "二楼D区"]),
                total_copies=total, available_copies=random.randint(0, total),
                description=f"{title} - {author}"
            ))

    # 数学类
    for title, authors in math_books:
        add_books(title, authors, "数学", (1, 3))

    # 经济管理类
    for title, authors in econ_books:
        add_books(title, authors, "经济学", (1, 3))

    # 物理化学
    for title, authors in phys_chem:
        cat = "化学" if "化学" in title else ("材料" if "材料" in title else "物理")
        add_books(title, authors, cat, (1, 3))

    # 外语类
    for title, authors in lang_books:
        add_books(title, authors, "外语", (1, 3))

    # 历史哲学
    for title, authors in hist_phil:
        cat = "哲学" if "哲学" in title or "马克思" in title or "逻辑" in title or "伦理" in title or "美学" in title else ("历史" if "史" in title else "哲学")
        if "社会学" in title:
            cat = "哲学"
        add_books(title, authors, cat, (1, 3))

    # 教育心理
    for title, authors in edu_psy:
        cat = "心理学" if "心理" in title else "教育学"
        add_books(title, authors, cat, (1, 3))

    # 法学
    for title, authors in law_books:
        add_books(title, authors, "法学", (1, 3))

    # ===== 补充到10000本 =====
    extra_titles = {
        "计算机": ["Python数据分析实战", "Java高级编程", "前端框架实战", "微服务架构设计",
                   "DevOps实践指南", "容器技术入门", "React开发实战", "Spring Boot实战",
                   "Redis设计与实现", "MySQL数据库管理", "MongoDB实战", "Nginx核心知识",
                   "Git版本控制", "Docker容器技术", "Kubernetes实战", "TCP/IP详解",
                   "HTTP权威指南", "JavaScript高级程序设计", "Vue.js实战", "Go语言编程",
                   "Rust程序设计", "Scala函数式编程", "Swift开发入门", "Kotlin实战",
                   "Unity游戏开发", "Unreal引擎实战", "嵌入式系统设计", "FPGA原理与设计",
                   "单片机原理与应用", "信号与系统", "数字信号处理", "图像处理基础"],
        "文学": ["诗经选注", "楚辞选读", "唐诗三百首", "宋词三百首", "元曲三百首",
                 "古文观止", "世说新语", "资治通鉴", "史记", "论语译注",
                 "庄子选读", "道德经", "孟子", "大学中庸", "诗词格律"],
        "数学": ["数学建模", "模糊数学", "随机过程", "矩阵分析", "泛函分析",
                 "微分几何", "代数几何", "数论基础", "最优化方法", "博弈论"],
        "经济学": ["产业经济学", "区域经济学", "劳动经济学", "发展经济学", "计量经济学",
                   "制度经济学", "行为经济学", "环境经济学", "农业经济学", "公共经济学"],
    }

    extra_authors = ["张伟", "王芳", "李娜", "刘洋", "陈静", "杨敏", "赵勇", "黄海", "周涛",
                     "吴强", "郑浩", "孙明", "马超", "朱磊", "胡斌", "林峰", "何颖", "高翔"]

    while len(batch) < 10000:
        cat = random.choice(list(extra_titles.keys()))
        title_base = random.choice(extra_titles[cat])
        author = random.choice(extra_authors)
        book_id += 1
        year = random.randint(2008, 2024)
        pub = random.choice(publishers)
        locs = locations_map.get(cat, ("二楼A区",))
        prefix = call_number_prefixes.get(cat, "Z")
        total = random.randint(1, 6)
        batch.append(Book(
            title=f"{title_base}", author=author, publisher=pub,
            isbn=gen_isbn(), publish_year=year,
            category=cat, call_number=f"{prefix}{random.randint(1,999)}/{book_id}",
            location=random.choice(locs),
            total_copies=total, available_copies=random.randint(0, total),
            description=f"{title_base} - {author} 编著"
        ))

    # 分批提交
    for i in range(0, len(batch), 500):
        db.session.add_all(batch[i:i+500])
        db.session.commit()
        print(f'  已导入 {min(i+500, len(batch))}/{len(batch)} 本...')


if __name__ == '__main__':
    reset_all()
