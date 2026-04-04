"""
core_logic.py — 分單底層邏輯
從 run_script_v6.py 提取，支援 inject_price_map() 動態更新售價對照
"""

from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfReader, PdfWriter
from io import BytesIO
import os, re, copy
import pdfplumber
from collections import defaultdict

# ── 字型路徑（Windows 優先，fallback Linux）────────────────────────────────
import platform
if platform.system() == "Windows":
    _FONT_CANDIDATES = [
        r"C:\Windows\Fonts\msjhbd.ttc",   # 微軟正黑體 Bold
        r"C:\Windows\Fonts\msjh.ttc",
        r"C:\Windows\Fonts\mingliu.ttc",
    ]
else:
    _FONT_CANDIDATES = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    ]

FONT_PATH = next((p for p in _FONT_CANDIDATES if os.path.exists(p)), None)

# ── 動態售價對照（由 UI 注入）─────────────────────────────────────────────
_PRICE_MAP_KINDS: dict[int, str] = {}
_GIFT_RULES: dict = {}

def inject_price_map(pm: dict):
    global _PRICE_MAP_KINDS
    _PRICE_MAP_KINDS = {int(k): v.get("kind", "") for k, v in pm.items()}

def inject_gift_rules(rules: dict):
    global _GIFT_RULES
    _GIFT_RULES = rules

# ── normalize ─────────────────────────────────────────────────────────────────
def N(s):
    for f, t in [('⼩','小'),('⽑','毛'),('⽇','日'),('Ｘ','X'),('＋','+'),
                 ('⽤','用'),('⾝','身'),('橘','橘'),('逆','逆'),('齡','齡'),
                 ('奇','奇'),('蹟','蹟'),('亮','亮'),('豐','豐'),('盈','盈'),
                 ('澤','澤'),('護','護'),('髮','髮'),('乳','乳'),('冰','冰'),
                 ('河','河'),('抗','抗'),('痘','痘'),('敏','敏'),('浴','浴'),
                 ('爆','爆'),('綠','綠'),('夜','夜'),('間','間'),('瓶','瓶'),
                 ('洗','洗'),('紫','紫'),('淨','淨'),('拋','拋'),('煥','煥')]:
        s = s.replace(f, t)
    for f, t in [('０','0'),('１','1'),('２','2'),('３','3'),('４','4'),
                 ('５','5'),('６','6'),('７','7'),('８','8'),('９','9')]:
        s = s.replace(f, t)
    for i in range(26):
        s = s.replace(chr(0xFF21+i), chr(65+i))
    return s

# ── 性別判斷 ──────────────────────────────────────────────────────────────────
F_CH = set('芸芳婷玲娟雯慧珍秀美麗惠玉鳳嫻淑婉媛嬌瑩瑜瑄筠茹欣怡宜君品佳柔')
M_CH = set('豪傑偉強勇剛宏峰毅威哲明志仁義德廷秉揚博賢')

def gender(name):
    n = name.strip()
    if '先生' in n: return 'male'
    if '小姐' in n: return 'female'
    f = sum(1 for c in n[1:] if c in F_CH)
    m = sum(1 for c in n[1:] if c in M_CH)
    return 'female' if f > m else 'male'

# ── 商品行提取 ────────────────────────────────────────────────────────────────
def extract_line_items(page, y_min=610):
    ws = page.extract_words()
    seq_rows = sorted(
        [(w['top'], int(w['text'])) for w in ws
         if 35 <= w['x0'] <= 50 and y_min < w['top'] < 950
         and re.match(r'^\d+$', w['text'])],
        key=lambda x: x[0]
    )
    if not seq_rows:
        return []

    # 動態偵測欄位 x 座標（應對有無「商品圖片」欄的版面差異）
    def find_header_x(keywords, default):
        candidates = [w for w in ws
                      if any(kw in w['text'] for kw in keywords)
                      and w['top'] < y_min + 50]
        if candidates:
            return max(candidates, key=lambda w: w['top'])['x0']
        return default

    spec_col_x  = find_header_x(['規格'],     295)
    qty_col_x   = find_header_x(['訂購數量'],  425)
    price_col_x = find_header_x(['單筆金額'],  470)

    items = []
    for idx, (seq_top, seq_num) in enumerate(seq_rows):
        t_min = seq_top - 15
        t_max = seq_rows[idx+1][0] - 5 if idx+1 < len(seq_rows) else seq_top + 80

        price_words = [w['text'] for w in ws
                       if price_col_x - 10 <= w['x0'] <= price_col_x + 50 and t_min <= w['top'] <= t_max
                       and w['text'].startswith('$')]
        price = 0
        if price_words:
            try: price = int(price_words[0].replace('$','').replace(',',''))
            except: pass

        qty_words = [w['text'] for w in ws
                     if qty_col_x - 5 <= w['x0'] <= qty_col_x + 25 and t_min <= w['top'] <= t_max
                     and re.match(r'^\d+$', w['text'])]
        qty = int(qty_words[0]) if qty_words else 1

        spec_ws = [(w['top'], N(w['text'])) for w in ws
                   if spec_col_x - 5 <= w['x0'] <= qty_col_x - 5 and t_min <= w['top'] <= t_max
                   and w['text'] not in ('規格','訂購數量')]
        spec_ws.sort()
        parts = [t for _, t in spec_ws if not re.match(r'^\d+$', t)]
        merged = []
        for part in parts:
            if merged and not re.search(r'[+X\d]$', merged[-1]) \
               and not re.match(r'^[爆豐奇逆夜日早晚冰抗淨水草亮]', part):
                merged[-1] += part
            else:
                merged.append(part)
        spec_raw = ' '.join(merged)
        items.append(dict(seq=seq_num, price=price, qty=qty, spec_raw=spec_raw))

    return items

# ── 從商品行推導贈品 spec ─────────────────────────────────────────────────────
def parse_from_items(items):
    gr = or_ = pw = pu = dou = bai = 0
    sh_dou = sh_bai = ec = la = cd_pw = cd_pu = 0

    def has(pat, s): return bool(re.search(pat, s))

    for item in items:
        p = item['price']
        q = item['qty']
        s = item['spec_raw']

        if p == 880:
            if has(r'綠|奇蹟|日用小綠', s): gr += q
            else: or_ += q
        elif p == 1520:
            if has(r'奇蹟小綠瓶X2|日用小綠瓶X2|綠瓶X2', s) and not has(r'橘', s): gr += 2*q
            elif has(r'逆齡小橘瓶X2|夜間小橘瓶X2|橘瓶X2', s) and not has(r'綠', s): or_ += 2*q
            else: gr += q; or_ += q
        elif p == 2850:
            if has(r'橘X4|逆齡小橘瓶X4', s) and not has(r'綠', s): or_ += 4*q
            elif has(r'綠X4|奇蹟小綠瓶X4', s) and not has(r'橘', s): gr += 4*q
            else: gr += 2*q; or_ += 2*q
        elif p == 1350:
            if has(r'爆毛小粉洗|小粉洗', s): pw += q
            if has(r'豐盈小紫|小紫', s): pu += q
            if has(r'奇蹟小綠|小綠|日用小綠', s): gr += q
            if has(r'逆齡小橘|小橘|夜間小橘|夜用小橘', s): or_ += q
        elif p == 1360:
            if has(r'爆毛小粉洗X2|小粉洗X2', s): pw += 2*q
            elif has(r'豐盈小紫洗X2|小紫洗X2|豐盈小紫X2', s): pu += 2*q
            elif has(r'爆毛小粉洗.*豐盈小紫洗|小粉洗.*小紫洗', s): pw += q; pu += q
            elif has(r'爆毛小粉洗.*草本|小粉洗.*草本', s): pw += q; cd_pw += q
            elif has(r'豐盈小紫洗.*亮澤|小紫洗.*亮澤', s): pu += q; cd_pu += q
            elif has(r'草本護髮乳X2|草本平衡潤髮乳X2', s): cd_pw += 2*q
            elif has(r'亮澤護髮乳X2|亮澤.*X2', s): cd_pu += 2*q
            elif has(r'草本護髮乳|草本平衡', s) and has(r'小粉洗|爆毛小粉', s): pw += q; cd_pw += q
            elif has(r'亮澤護髮乳|極潤亮澤', s) and has(r'小紫洗|豐盈小紫', s): pu += q; cd_pu += q
            elif has(r'豐盈小紫洗髮精|豐盈小紫洗', s) and has(r'極潤亮澤', s): pu += q; cd_pu += q
            elif has(r'豐盈小紫洗髮精|豐盈小紫洗', s): pu += 2*q
            elif has(r'爆毛小粉洗髮精|爆毛小粉洗', s) and has(r'草本', s): pw += q; cd_pw += q
            elif has(r'爆毛小粉洗髮精|爆毛小粉洗', s): pw += 2*q
            elif has(r'極潤亮澤潤髮乳', s): cd_pu += 2*q
            elif has(r'草本平衡潤髮乳', s): cd_pw += 2*q
            elif has(r'小粉', s) and has(r'小紫', s): pw += q; pu += q
        elif p == 780:
            if has(r'爆毛小粉洗|小粉洗', s): pw += q
            elif has(r'豐盈小紫洗|小紫洗|豐盈小紫', s): pu += q
            elif has(r'草本護髮乳|草本平衡', s): cd_pw += q
            elif has(r'亮澤護髮乳|極潤亮澤', s): cd_pu += q
        elif p == 785:
            if has(r'水光嫩白沐|水光沐', s): sh_bai += q
            else: sh_dou += q
        elif p == 1370:
            if has(r'水光.*淨痘|淨痘.*水光', s): sh_dou += q; sh_bai += q
            elif has(r'水光沐.*X2|水光嫩白沐X2', s): sh_bai += 2*q
            elif has(r'淨痘沐.*X2|淨痘舒敏沐X2', s): sh_dou += 2*q
            else: sh_dou += q; sh_bai += q
        elif p == 950:
            if has(r'冰河煥白|白乳|煥白乳', s): bai += q
            else: dou += q
        elif p == 1860:
            if has(r'冰河煥白.*X2|白乳X2', s) and not has(r'抗痘|痘乳', s): bai += 2*q
            elif has(r'抗痘拋光.*X2|痘乳X2', s) and not has(r'冰河|白乳', s): dou += 2*q
            else: dou += q; bai += q
        elif p == 1395:
            if has(r'早C|活氧瓶|抗痘拋光|水楊酸', s): ec += q; dou += q
            else: la += q; bai += q
        elif p == 1576:
            if has(r'冰河煥白|白乳|水光嫩白沐', s): bai += q; sh_bai += q
            else: dou += q; sh_dou += q
        elif p == 689:
            if has(r'早C|活氧瓶', s): ec += q
            else: la += q
        elif p == 1248:
            if has(r'早C.*晚A|晚A.*早C', s): ec += q; la += q
            elif has(r'早C.*X2|活氧瓶X2', s): ec += 2*q
            elif has(r'晚A.*X2|凍齡瓶X2|緊緻瓶X2', s): la += 2*q
            else: ec += q; la += q
        elif p == 2184:
            if has(r'早C.*X2.*晚A|晚A.*X2.*早C|早C.*晚A.*X2', s): ec += 2*q; la += 2*q
            elif has(r'早C.*X4|活氧瓶X4', s): ec += 4*q
            elif has(r'晚A.*X4|凍齡瓶X4', s): la += 4*q
            else: ec += 2*q; la += 2*q
        elif p == 2420:
            sh_dou += 4*q
        elif p == 2380:
            pw += 2*q; pu += 2*q

    sm = gr + or_
    lo = dou + bai
    sh = sh_dou + sh_bai
    cd = 1 if (cd_pw or cd_pu) else 0
    return dict(sm=sm, gr=gr, or_=or_, lo=lo, dou=dou, bai=bai,
                sh=sh, sh_bai=sh_bai, sh_dou=sh_dou,
                pw=pw, pu=pu, cd=cd, cd_pu=cd_pu, cd_pw=cd_pw,
                earlyC=ec, lateA=la)

# ── 特殊單摘要 ────────────────────────────────────────────────────────────────
def special_summary(items):
    """
    把商品行列表轉成人類可讀的品項組合摘要
    例如：痘乳2+橘1、白乳1+早C1、兩沐+痘乳1
    """
    parts = []
    for item in items:
        p = item['price']; q = item['qty']; s = item['spec_raw']
        def has(pat): return bool(re.search(pat, s))
        name = None

        # ── 精粹 ──
        if p == 880:
            name = f'綠{q}' if has(r'綠|奇蹟|日用小綠') else f'橘{q}'
        elif p == 1520:
            if has(r'綠') and not has(r'橘'): name = f'綠2' if q==1 else f'綠{2*q}'
            elif has(r'橘') and not has(r'綠'): name = f'橘2' if q==1 else f'橘{2*q}'
            else: name = f'綠1+橘1' if q==1 else f'(綠1+橘1)×{q}'
        elif p == 2850:
            if has(r'橘.*X4') and not has(r'綠'): name = f'橘4'
            elif has(r'綠.*X4') and not has(r'橘'): name = f'綠4'
            else: name = f'綠2+橘2'
        elif p == 1350:
            if has(r'小粉洗|爆毛小粉'):
                if has(r'奇蹟小綠|日用小綠|小綠瓶') and not has(r'橘'): name = '粉洗1+綠1'
                elif has(r'逆齡小橘|奇蹟小橘|夜間小橘|小橘瓶') or has(r'橘'): name = '粉洗1+橘1'
                else: name = '粉洗+精粹'
            elif has(r'小紫|豐盈小紫'):
                if has(r'奇蹟小綠|日用小綠|小綠瓶') and not has(r'橘'): name = '紫洗1+綠1'
                elif has(r'逆齡小橘|奇蹟小橘|夜間小橘|小橘瓶') or has(r'橘'): name = '紫洗1+橘1'
                else: name = '紫洗+精粹'
            else: name = '洗+精粹'

        # ── 慕斯 ──
        elif p == 689:
            name = f'早C{q}' if has(r'早C|活氧') else f'晚A{q}'
        elif p == 1248:
            if has(r'早C.*X2|活氧.*X2'): name = f'早C{2*q}'
            elif has(r'晚A.*X2|凍齡.*X2'): name = f'晚A{2*q}'
            else: name = f'早C{q}+晚A{q}'
        elif p == 2184:
            if has(r'早C.*X4|活氧.*X4'): name = f'早C{4*q}'
            elif has(r'晚A.*X4|凍齡.*X4'): name = f'晚A{4*q}'
            else: name = f'早C{2*q}+晚A{2*q}'

        # ── 乳液 ──
        elif p == 950:
            name = f'白乳{q}' if has(r'冰河煥白|白乳|煥白') else f'痘乳{q}'
        elif p == 1860:
            if has(r'冰河煥白.*X2|白乳X2') and not has(r'抗痘|痘乳'): name = f'白乳{2*q}'
            elif has(r'抗痘拋光.*X2|痘乳X2') and not has(r'冰河|白乳'): name = f'痘乳{2*q}'
            else: name = f'白乳{q}+痘乳{q}'
        elif p == 1395:
            name = f'早C{q}+痘乳{q}' if has(r'早C|活氧|抗痘拋光|水楊酸') else f'晚A{q}+白乳{q}'
        elif p == 1576:
            name = f'白乳{q}+水光沐{q}' if has(r'冰河煥白|白乳|水光嫩白') else f'痘乳{q}+淨痘沐{q}'

        # ── 洗髮 ──
        elif p == 780:
            if has(r'爆毛小粉洗|小粉洗'): name = f'粉洗{q}'
            elif has(r'豐盈小紫洗|小紫洗|豐盈小紫'): name = f'紫洗{q}'
            elif has(r'草本護髮|草本平衡'): name = f'粉潤{q}'
            elif has(r'亮澤護髮|極潤亮澤'): name = f'紫潤{q}'
            else: name = f'洗髮{q}'
        elif p == 1360:
            if has(r'小粉洗X2|爆毛小粉洗X2'): name = f'粉洗{2*q}'
            elif has(r'小紫洗X2|豐盈小紫洗X2'): name = f'紫洗{2*q}'
            elif has(r'小粉洗.*草本|草本.*小粉洗'): name = f'粉洗{q}+粉潤{q}'
            elif has(r'小紫洗.*亮澤|亮澤.*小紫洗'): name = f'紫洗{q}+紫潤{q}'
            elif has(r'小粉.*小紫|小紫.*小粉'): name = f'粉洗{q}+紫洗{q}'
            elif has(r'草本.*X2'): name = f'粉潤{2*q}'
            elif has(r'亮澤.*X2'): name = f'紫潤{2*q}'
            else: name = f'洗潤{q}'
        elif p == 2380:
            name = f'粉洗2+紫洗2' if q==1 else f'(粉洗2+紫洗2)×{q}'

        # ── 沐浴 ──
        elif p == 785:
            name = f'水光沐{q}' if has(r'水光嫩白|水光沐') else f'淨痘沐{q}'
        elif p == 1370:
            if has(r'水光沐.*X2|水光嫩白.*X2'): name = f'水光沐{2*q}'
            elif has(r'淨痘沐.*X2|淨痘舒敏.*X2'): name = f'淨痘沐{2*q}'
            else: name = f'淨痘沐{q}+水光沐{q}'
        elif p == 2420:
            if has(r'水光沐.*X4'): name = f'水光沐4'
            elif has(r'淨痘沐.*X4'): name = f'淨痘沐4'
            else: name = f'淨痘沐2+水光沐2'

        else:
            name = f'${p}×{q}' if q > 1 else f'${p}'

        if name: parts.append(name)

    return ' + '.join(parts) if parts else '？'

# ── 贈品判斷（動態讀取 config，固定邏輯判分類） ─────────────────────────────
def gift(sp, gnd, disc_val):
    sm=sp['sm']; dou=sp['dou']; bai=sp['bai']; lo=sp['lo']
    sh=sp['sh']; sh_bai=sp['sh_bai']; sh_dou=sp['sh_dou']
    pw=sp['pw']; pu=sp['pu']; cd=sp['cd']; cd_pu=sp['cd_pu']; cd_pw=sp['cd_pw']
    ec=sp['earlyC']; la=sp['lateA']
    gr=sp['gr']; oor=sp['or_']
    G = 'female' if gnd == 'female' else 'male'
    non50 = (disc_val != 0 and disc_val != 50)

    def g(cat):
        """查詢贈品規則：依分類+性別，若無規則回傳空字串"""
        rule = _GIFT_RULES.get(cat)
        if not rule:
            return cat, '請人工確認\n找不到贈品規則'
        # 乳液系列依 non50 折扣切換
        if non50 and cat in ('白乳X2','痘乳X2','乳液1+1','2+2乳液'):
            return cat, rule.get(G, rule.get('female', ''))
        return cat, rule.get(G, rule.get('female', ''))

    if ec >= 1 and la >= 1:
        total = ec + la
        if total == 2: return g('1+1慕斯')
        if total == 4: return g('2+2慕斯')
        return '特殊單', '請人工確認\n慕斯數量異常'
    if ec >= 1 and la == 0:
        if dou >= 1 and bai == 0 and sm == 0 and sh == 0 and pw == 0 and pu == 0:
            return g('早C+痘乳')
        if dou == 0 and bai == 0 and sm == 0 and sh == 0 and pw == 0 and pu == 0:
            if ec == 2: return g('黃色慕斯X2')
            if ec == 4: return g('黃色慕斯X4')
        return '特殊單', '請人工確認\n早C混搭'
    if la >= 1 and ec == 0:
        if bai >= 1 and dou == 0 and sm == 0 and sh == 0 and pw == 0 and pu == 0:
            return g('晚A+白乳')
        if bai == 0 and dou == 0 and sm == 0 and sh == 0 and pw == 0 and pu == 0:
            if la == 2: return g('紫色慕斯X2')
            if la == 4: return g('紫色慕斯X4')
        return '特殊單', '請人工確認\n晚A混搭'

    if bai == 2 and dou == 0 and sh == 0 and sm == 0 and pw == 0 and pu == 0:
        return g('白乳X2')
    if dou == 2 and bai == 0 and sh == 0 and sm == 0 and pw == 0 and pu == 0:
        return g('痘乳X2')
    if bai == 1 and dou == 0 and sh == 0 and sm == 0 and pw == 0 and pu == 0:
        return g('白乳X1')
    if dou == 1 and bai == 0 and sh == 0 and sm == 0 and pw == 0 and pu == 0:
        return g('痘乳X1')
    if bai == 1 and dou == 1 and sh == 0 and sm == 0 and pw == 0 and pu == 0:
        return g('乳液1+1')
    if lo >= 4 and sh == 0 and sm == 0 and pw == 0 and pu == 0:
        return g('2+2乳液')
    if dou >= 1 and sh_dou >= 1 and bai == 0 and sh_bai == 0 and sm == 0 and pw == 0 and pu == 0:
        return g('痘乳+淨痘沐')
    if bai >= 1 and sh_bai >= 1 and dou == 0 and sh_dou == 0 and sm == 0 and pw == 0 and pu == 0:
        return g('白乳+水光沐')
    if lo >= 1 and sm >= 1:
        return '特殊單', '請人工確認\n乳液+精粹混搭'

    if sh >= 4 and lo == 0 and sm == 0 and pw == 0 and pu == 0:
        return '特殊單', '請人工確認\n沐浴X4組合'
    if sh >= 2 and lo == 0 and sm == 0 and pw == 0 and pu == 0:
        return g('兩沐')
    if sh == 1 and lo == 0 and sm == 0 and pw == 0 and pu == 0:
        return g('一沐')

    if sm == 4 and pw == 0 and pu == 0 and lo == 0 and sh == 0:
        if gr == 2 and oor == 2: return g('綠2+橘2精粹')
        if oor == 4: return g('橘4精粹')
        return g('綠4精粹')
    if sm == 2 and pw == 0 and pu == 0 and lo == 0 and sh == 0 and cd == 0:
        if oor == 2: return g('橘2精粹')
        if gr == 2:  return g('綠2精粹')
        return g('1+1精粹')
    if sm == 1 and pw == 0 and pu == 0 and lo == 0 and sh == 0:
        return g('1小矮')

    if pw == 1 and sm >= 1 and sm <= 2 and pu == 0 and lo == 0 and sh == 0 and cd == 0:
        if gr >= 1 and oor >= 1: return g('粉+綠+橘')
        if oor >= 1: return g('粉+橘')
        return g('粉+綠')
    if pu == 1 and sm >= 1 and sm <= 2 and pw == 0 and lo == 0 and sh == 0 and cd == 0:
        if gr >= 1 and oor >= 1: return g('紫+綠+橘')
        if oor >= 1: return g('紫+橘')
        return g('紫+綠')

    if pw >= 1 and pu >= 1 and sm == 0 and lo == 0 and sh == 0 and cd == 0:
        return g('粉洗+紫洗')
    if pw == 2 and pu == 0 and sm == 0 and lo == 0 and sh == 0 and cd == 0:
        return g('粉洗X2')
    if pu == 2 and pw == 0 and sm == 0 and lo == 0 and sh == 0 and cd == 0:
        return g('紫洗X2')
    if pw >= 1 and cd_pw >= 1 and pu == 0 and cd_pu == 0 and sm == 0 and lo == 0 and sh == 0:
        return g('粉洗+粉潤')
    if pu >= 1 and cd_pu >= 1 and pw == 0 and cd_pw == 0 and sm == 0 and lo == 0 and sh == 0:
        return g('紫洗+紫潤')
    if pw == 1 and pu == 0 and sm == 0 and lo == 0 and sh == 0 and cd == 0:
        return g('小粉洗X1')
    if pu == 1 and pw == 0 and sm == 0 and lo == 0 and sh == 0 and cd == 0:
        return g('小紫洗X1')

    return '特殊單', '請人工確認\n品項請確認'

# ── 渲染標籤圖片 ──────────────────────────────────────────────────────────────
def wrap_text(text, font, max_width):
    lines = []
    while text:
        lo, hi = 1, len(text)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if font.getbbox(text[:mid])[2] <= max_width: lo = mid
            else: hi = mid - 1
        lines.append(text[:lo])
        text = text[lo:]
    return lines

def render_label(cat, gift_text, is_special, print_gift=True, pt_w=155, pt_h=170, dpi=150):
    scale = dpi / 72.0
    W, H = int(pt_w * scale), int(pt_h * scale)
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([2, 2, W-3, H-3], radius=int(7*scale),
                            fill=(255, 255, 255, 240), outline=(0, 0, 0), width=2)

    if FONT_PATH:
        f_cat  = ImageFont.truetype(FONT_PATH, int(10*scale))
        f_body = ImageFont.truetype(FONT_PATH, int(15*scale))
        f_sum  = ImageFont.truetype(FONT_PATH, int(17*scale))
        f_big  = ImageFont.truetype(FONT_PATH, int(20*scale))
    else:
        f_cat = f_body = f_sum = f_big = ImageFont.load_default()

    margin = int(8*scale)

    if is_special:
        # 特殊單：無論有無選贈品，永遠只顯示兩行
        draw.text((int(8*scale), int(6*scale)), '【特殊單】', font=f_cat, fill=(180, 60, 0))
        draw.text((margin, int(30*scale)), '請人工確認', font=f_big, fill=(180, 60, 0))
    elif not print_gift:
        # 一般單不列印贈品：只顯示分類大字
        lines = wrap_text(f'【{cat}】', f_big, W - margin * 2)
        y = int(H/2 - len(lines)*24*scale/2)
        for line in lines:
            draw.text((margin, y), line, font=f_big, fill=(0, 0, 0))
            y += int(24*scale)
    else:
        draw.text((int(8*scale), int(6*scale)), f'【{cat}】', font=f_cat, fill=(0, 0, 0))
        y = int(24*scale)
        for line in wrap_text(gift_text, f_body, W - margin*2)[:8]:
            draw.text((margin, y), line, font=f_body, fill=(0, 0, 0))
            y += int(19*scale)

    buf = BytesIO()
    img.save(buf, 'PNG')
    buf.seek(0)
    return buf.getvalue()

def add_image_to_page(writer, page_idx, png_bytes, x, y, w, h):
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.utils import ImageReader
    buf = BytesIO()
    pw2 = float(writer.pages[page_idx].mediabox.width)
    ph2 = float(writer.pages[page_idx].mediabox.height)
    c = rl_canvas.Canvas(buf, pagesize=(pw2, ph2))
    c.drawImage(ImageReader(BytesIO(png_bytes)), x, y, width=w, height=h, mask='auto')
    c.save()
    buf.seek(0)
    writer.pages[page_idx].merge_page(PdfReader(buf).pages[0])

# ── 主解析流程 ────────────────────────────────────────────────────────────────
def parse_pdf(pdf_in: str) -> list[dict]:
    reader = PdfReader(pdf_in)
    orders = []

    with pdfplumber.open(pdf_in) as pdf:
        total_pages = len(pdf.pages)
        i = 0
        while i < total_pages:
            page = pdf.pages[i]
            text = page.extract_text() or ''
            if len(text.strip()) < 50:
                i += 1
                continue

            m = re.search(r'#(\w+)\s', text)
            if not m:
                i += 1
                continue

            oid = m.group(1)
            page_indices = [i]

            j = i + 1
            while j < total_pages:
                next_text = pdf.pages[j].extract_text() or ''
                next_has_oid = bool(re.search(r'#\w{8,}\s', next_text))
                next_has_content = bool(re.search(r'總計|訂單金額|\$[\d,]+', next_text))
                if not next_has_oid and next_has_content:
                    page_indices.append(j)
                    j += 1
                else:
                    break

            buyer = ''
            bm = re.search(r'收件⼈：(.+)|收件人：(.+)', text)
            if bm: buyer = next(x for x in bm.groups() if x).strip().split()[0]
            dm = re.search(r'訂單折扣\s*(-\$[\d,]+)', text)
            disc_str = dm.group(1) if dm else None
            disc_val = int(disc_str.replace('-$','').replace(',','')) if disc_str else 0

            all_items = []
            for pi_idx, pi in enumerate(page_indices):
                y_min = 610 if pi_idx == 0 else 50
                all_items.extend(extract_line_items(pdf.pages[pi], y_min=y_min))

            sp = parse_from_items(all_items)
            gnd = gender(buyer)
            cat, gft = gift(sp, gnd, disc_val)

            if disc_val > 158:
                cat = '特殊單'; gft = f'請人工確認\n折扣 {disc_str}'
            elif disc_val != 0 and disc_val != 50 and cat != '特殊單':
                gft = gft + f'  折{disc_str}'

            if cat == '特殊單' and all_items and disc_val <= 158:
                summary = special_summary(all_items)
                gft = f'請人工確認\n{summary}'

            orders.append(dict(
                idx=i, oid=oid, buyer=buyer, gnd=gnd,
                disc_val=disc_val, disc_str=disc_str or '無',
                sp=sp, cat=cat, gift=gft, special=(cat=='特殊單'),
                page_indices=page_indices
            ))
            i = j

    return orders

# ── PDF 輸出 ──────────────────────────────────────────────────────────────────
def generate_pdfs(orders: list[dict], pdf_in: str, out_dir: str, print_gift: bool) -> list[str]:
    reader = PdfReader(pdf_in)
    groups = defaultdict(list)
    for o in orders:
        groups[o['cat']].append(o)

    # 排序：一般分類照名稱，特殊單排最後
    sorted_cats = sorted(groups.keys(), key=lambda c: (c == '特殊單', c))
    pad = len(str(len(sorted_cats)))  # 決定前綴位數（例如 10 個以上用 2 位）

    output_files = []
    for num, cat in enumerate(sorted_cats, 1):
        ords = groups[cat]
        writer = PdfWriter()
        page_map = []
        for o in ords:
            first_writer_idx = len(writer.pages)
            for pi in o['page_indices']:
                writer.add_page(copy.copy(reader.pages[pi]))
            page_map.append((o, first_writer_idx))

        for o, writer_idx in page_map:
            ph2 = float(writer.pages[writer_idx].mediabox.height)
            png = render_label(o['cat'], o['gift'], o['special'],
                               print_gift=print_gift, pt_w=148, pt_h=172, dpi=150)
            add_image_to_page(writer, writer_idx, png, 432, ph2 - 210, 148, 172)

        safe = re.sub(r'[/\\ ⚠️]+', '_', cat).strip('_')
        prefix = str(num).zfill(pad)
        out_path = os.path.join(out_dir, f'{prefix}_{safe}.pdf')
        with open(out_path, 'wb') as f:
            writer.write(f)
        output_files.append(out_path)

    return output_files
