import streamlit as st
import requests
import time
import pandas as pd
import folium
import plotly.express as px
from streamlit_folium import st_folium
from zhipuai import ZhipuAI
import random
import re

# ==========================================
# 1. 頁面設定與精準 CSS
# ==========================================
st.set_page_config(page_title="智能地塊潛力分析", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    /* 保持 header 可見，以便喚出左側邊欄 */
    
    /* 整個主背景強制淺色 */
    [data-testid="stAppViewContainer"] { background-color: #F8FAFC !important; }
    
    /* ==========================================
       【終極防禦】：全面狙擊 Dark Mode 的白字現象
       強制主畫面的文字全部為深色，無視系統主題
       ========================================== */
    
    /* 1. 主畫面：強制所有普通文字變成深色 */
    [data-testid="stMainBlock"] .stMarkdown p, 
    [data-testid="stMainBlock"] .stMarkdown li, 
    [data-testid="stMainBlock"] .stMarkdown span {
        color: #334155 !important;
    }
    
    /* 2. 主畫面標題 */
    [data-testid="stMainBlock"] .stMarkdown h1, 
    [data-testid="stMainBlock"] .stMarkdown h2, 
    [data-testid="stMainBlock"] .stMarkdown h3 {
        color: #1E293B !important;
    }
    
    /* 3. Tabs 標籤文字 */
    button[data-baseweb="tab"] p, 
    button[data-baseweb="tab"] span {
        color: #1E293B !important;
        font-weight: 600 !important;
    }
    
    /* 4. Expander (折疊面板) 標題與內容 */
    [data-testid="stExpander"] summary p, 
    [data-testid="stExpander"] summary span {
        color: #1E293B !important;
        font-weight: bold !important;
    }
    [data-testid="stExpander"] div[role="region"] p {
        color: #334155 !important;
    }
    
    /* 5. Metrics 數據卡片 */
    [data-testid="stMetricLabel"] p {
        color: #475569 !important;
    }
    [data-testid="stMetricValue"] div {
        color: #0F172A !important;
    }
    
    /* 6. 提示框 (st.info) */
    .stAlert p {
        color: #1E293B !important;
    }
    
    /* ==========================================
       側邊欄與特例保護 (必須維持白色或自定義顏色)
       ========================================== */
    
    /* 側邊欄背景設定為深色 */
    [data-testid="stSidebar"] {
        background-color: #0F172A !important;
        padding-top: 2rem;
    }
    
    /* 側邊欄文字必須是白色 */
    [data-testid="stSidebar"] .stMarkdown p,
    [data-testid="stSidebar"] .stMarkdown h1,
    [data-testid="stSidebar"] .stMarkdown h2,
    [data-testid="stSidebar"] .stMarkdown h3,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
        color: #F1F5F9 !important;
    }
    
    /* 側邊欄的輸入框文字保持深色 */
    [data-testid="stSidebar"] div[data-baseweb="input"] input,
    [data-testid="stSidebar"] div[data-baseweb="select"] div {
        color: #0F172A !important;
    }
    
    /* 按鈕美化 */
    div.stButton > button {
        background-color: #3B82F6 !important;
        border-radius: 6px;
        height: 48px;
        border: none;
        width: 100%;
        margin-top: 1rem;
    }
    div.stButton > button p {
        color: #FFFFFF !important; /* 按鈕文字永遠白色 */
        font-weight: bold !important;
    }
    div.stButton > button:hover {
        background-color: #2563EB !important;
    }

    /* 頂部深色數據卡片 (確保文字不會被覆蓋) */
    .recommendation-card {
        background: linear-gradient(135deg, #1E293B 0%, #334155 100%);
        padding: 30px;
        border-radius: 12px;
        text-align: center;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        margin-bottom: 2rem;
        border-bottom: 4px solid #3B82F6;
    }
    .recommendation-title {
        font-size: 16px; color: #94A3B8 !important; letter-spacing: 2px; margin-bottom: 10px; text-transform: uppercase;
    }
    .recommendation-value {
        font-size: 32px; font-weight: 800; color: #FFFFFF !important; letter-spacing: 1px;
    }

    /* 報告與列表區塊 */
    .report-card {
        background-color: #FFFFFF; padding: 35px; border-radius: 12px; border-left: 6px solid #3B82F6;
        font-size: 16px; line-height: 1.8; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); margin-bottom: 1rem;
    }
    .report-card h3 { font-size: 20px; color: #1E293B !important; margin-top: 20px; margin-bottom: 15px; border-bottom: 1px solid #E2E8F0; padding-bottom: 5px; }
    .report-card ul { padding-left: 20px; margin-bottom: 20px; color: #334155 !important; }
    .report-card li { margin-bottom: 10px; color: #334155 !important; }
    
    .rec-item-card {
        background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 20px;
        margin-bottom: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border-left: 4px solid #3B82F6;
    }
    .rec-item-title { font-size: 18px; font-weight: bold; color: #0F172A !important; margin-bottom: 5px; }
    .rec-item-price { font-size: 16px; color: #DC2626 !important; font-weight: 600; margin-bottom: 10px; }
    .rec-item-desc { font-size: 14px; color: #475569 !important; }

    .custom-alert-error {
        background-color: #FEF2F2; color: #991B1B !important; padding: 16px; border-radius: 8px; border-left: 6px solid #EF4444; margin-bottom: 1rem; font-weight: 500;
    }
    .custom-alert-success {
        background-color: #F0FDF4; color: #166534 !important; padding: 16px; border-radius: 8px; border-left: 6px solid #22C55E; margin-bottom: 1rem; font-weight: 500;
    }
    </style>
""", unsafe_allow_html=True)

def show_error(msg):
    st.markdown(f'<div class="custom-alert-error">{msg}</div>', unsafe_allow_html=True)

def show_success(msg):
    st.markdown(f'<div class="custom-alert-success">{msg}</div>', unsafe_allow_html=True)

ZHIPU_API_KEY = "2040bad6a4de457db8783082ea9120bc.FDSw7nPPtfv8KCaD"
client = ZhipuAI(api_key=ZHIPU_API_KEY)

# ==========================================
# 2. 數據處理與動態生成引擎
# ==========================================
@st.cache_data(ttl=86400)
def get_coordinates(address):
    demo_locations = {
        "九龙塘": (22.3372, 114.1752), "九龍塘": (22.3372, 114.1752), "Kowloon Tong": (22.3372, 114.1752),
        "何文田": (22.3160, 114.1795), "Ho Man Tin": (22.3160, 114.1795),
        "沙田": (22.3784, 114.1870), "Sha Tin": (22.3784, 114.1870),
        "薄扶林": (22.2618, 114.1317), "Pok Fu Lam": (22.2618, 114.1317),
        "红磡": (22.3023, 114.1833), "紅磡": (22.3023, 114.1833), "Hung Hom": (22.3023, 114.1833),
        "铜锣湾": (22.2800, 114.1850), "銅鑼灣": (22.2800, 114.1850), "Causeway Bay": (22.2800, 114.1850),
        "旺角": (22.3204, 114.1698), "Mong Kok": (22.3204, 114.1698),
        "元朗": (22.4445, 114.0222), "Yuen Long": (22.4445, 114.0222),
        "荃湾": (22.3713, 114.1144), "荃灣": (22.3713, 114.1144), "Tsuen Wan": (22.3713, 114.1144),
        "将军澳": (22.3119, 114.2569), "將軍澳": (22.3119, 114.2569), "Tseung Kwan O": (22.3119, 114.2569),
        "中环": (22.2819, 114.1581), "中環": (22.2819, 114.1581), "Central": (22.2819, 114.1581),
        "观塘": (22.3142, 114.2266), "觀塘": (22.3142, 114.2266), "Kwun Tong": (22.3142, 114.2266),
        "鲗鱼涌": (22.2842, 114.2118), "鰂魚涌": (22.2842, 114.2118), "Quarry Bay": (22.2842, 114.2118),
        "金钟": (22.2796, 114.1655), "金鐘": (22.2796, 114.1655), "Admiralty": (22.2796, 114.1655),
        "九龙湾": (22.3234, 114.2104), "九龍灣": (22.3234, 114.2104), "Kowloon Bay": (22.3234, 114.2104),
        "乌溪沙": (22.4276, 114.2443), "烏溪沙": (22.4276, 114.2443), "Wu Kai Sha": (22.4276, 114.2443),
        "迪士尼": (22.3129, 114.0412), "Disneyland": (22.3129, 114.0412),
        "海洋公园": (22.2460, 114.1749), "海洋公園": (22.2460, 114.1749), "Ocean Park": (22.2460, 114.1749),
        "科学园": (22.4277, 114.2123), "科學園": (22.4277, 114.2123), "Science Park": (22.4277, 114.2123),
        "数码港": (22.2599, 114.1311), "數碼港": (22.2599, 114.1311), "Cyberport": (22.2599, 114.1311)
    }

    clean_address = address.replace(" ", "").replace("站", "").replace("香港", "")
    
    for key in demo_locations:
        if key in clean_address or clean_address in key:
            lat, lon = demo_locations[key]
            return lat, lon, f"高精度內置定位: {key}"

    try:
        url = "https://www.als.ogcio.gov.hk/lookup"
        headers = {"Accept": "application/json", "User-Agent": "Mozilla/5.0"}
        params = {"q": address, "n": 1}
        res = requests.get(url, params=params, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if "SuggestedAddress" in data and len(data["SuggestedAddress"]) > 0:
                suggested = data["SuggestedAddress"][0]["Address"]["PremisesAddress"]
                geo_info = suggested.get("GeospatialInformation", [])
                if geo_info:
                    lat = float(geo_info[0]["Latitude"])
                    lon = float(geo_info[0]["Longitude"])
                    return lat, lon, f"政府標準地址: {address}"
    except:
        pass
        
    try:
        url = "https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates"
        params = {"f": "json", "singleLine": f"{address}, Hong Kong", "maxLocations": 1}
        res = requests.get(url, params=params, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if data.get("candidates") and len(data["candidates"]) > 0:
                candidate = data["candidates"][0]
                lat = candidate["location"]["y"]
                lon = candidate["location"]["x"]
                display_name = candidate["address"]
                return float(lat), float(lon), f"ArcGIS 智能定位: {display_name}"
    except:
        pass
        
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {"q": f"{address}, Hong Kong", "format": "json", "limit": 1}
        headers = {"User-Agent": "PropTech_Feasibility_App/18.0"}
        res = requests.get(url, params=params, headers=headers, timeout=5)
        if res.status_code == 200 and len(res.json()) > 0:
            data = res.json()[0]
            display_name = data['display_name'].split(',')[0]
            return float(data['lat']), float(data['lon']), f"空間圖資定位: {display_name}"
    except:
        pass
        
    return None, None, None

@st.cache_data(ttl=3600)
def fetch_poi_data(lat, lon, radius=1000):
    overpass_endpoints = [
        "https://overpass.kumi.systems/api/interpreter",
        "https://lz4.overpass-api.de/api/interpreter",
        "http://overpass-api.de/api/interpreter"
    ]
    
    overpass_query = f"""
    [out:json][timeout:45];
    (
      nwr["railway"="station"](around:{radius},{lat},{lon});
      nwr["amenity"="school"](around:{radius},{lat},{lon});
      nwr["amenity"="university"](around:{radius},{lat},{lon});
      nwr["amenity"="college"](around:{radius},{lat},{lon});
      nwr["amenity"="hospital"](around:{radius},{lat},{lon});
      nwr["amenity"="clinic"](around:{radius},{lat},{lon});
      nwr["shop"="mall"](around:{radius},{lat},{lon});
    );
    out center tags;
    """
    headers = {"User-Agent": "PropTech_Feasibility_App/18.0"}
    poi_details = {"地鐵與鐵路站": {}, "學校與教育機構": {}, "醫院與醫療設施": {}, "購物商場": {}}
    
    for url in overpass_endpoints:
        try:
            response = requests.post(url, data=overpass_query, headers=headers, timeout=50)
            if response.status_code == 200:
                data = response.json()
                for element in data.get('elements', []):
                    tags = element.get('tags', {})
                    name = tags.get('name:zh', tags.get('name', '未命名设施'))
                    if name == '未命名设施' or name == '未命名設施': continue
                    
                    p_lat = element.get('lat', element.get('center', {}).get('lat'))
                    p_lon = element.get('lon', element.get('center', {}).get('lon'))
                    if not p_lat or not p_lon: continue
                    
                    if tags.get('railway') == 'station': 
                        exclude_keywords = ['大街', '世界', '探險', '明日', '山谷', '小鎮', '纜車', '昂坪', '海洋', '公園', '探险', '缆车', '小镇']
                        if any(k in name for k in exclude_keywords):
                            continue
                        if '站' not in name and 'Station' not in name:
                            name = f"{name}站"
                        poi_details["地鐵與鐵路站"][name] = (p_lat, p_lon)
                        
                    elif tags.get('amenity') in ['school', 'university', 'college']: 
                        poi_details["學校與教育機構"][name] = (p_lat, p_lon)
                    elif tags.get('amenity') in ['hospital', 'clinic']: 
                        poi_details["醫院與醫療設施"][name] = (p_lat, p_lon)
                    elif tags.get('shop') == 'mall': 
                        poi_details["購物商場"][name] = (p_lat, p_lon)
                        
                return poi_details
        except:
            continue
    return None

def get_mock_price(location_name):
    seed = sum([ord(c) for c in location_name])
    random.seed(seed)
    base_price = random.randint(11000, 28000)
    top_price = base_price + random.randint(1500, 4000)
    return f"HK$ {base_price:,} - {top_price:,} / 呎"

def get_dynamic_analysis(location_name, category):
    seed = sum([ord(c) for c in location_name])
    random.seed(seed)
    
    pools = {
        "edu": [
            f"「{location_name}」的光環能有效吸引周邊家庭與教職群體，為鄰近物業帶來穩定的居住剛需。",
            f"依托「{location_name}」的優質學術氛圍，極大增強了該區域家庭客群長期持有的意願，具備保值空間。",
            f"鄰近「{location_name}」可帶動周邊文教、培訓及青年公寓等衍生商業形態，長線投資潛力深厚。"
        ],
        "live": [
            f"「{location_name}」的存在顯著優化了地塊的生活便利度與社區配套，是提升區內物業溢價的關鍵。",
            f"充沛的商業與民生配套（如「{location_name}」）大幅增強該地段的宜居屬性，支撐周邊租金回報。",
            f"憑藉「{location_name}」強勁的區域消費吸附力，可為混合型商業地產開發提供穩定的人流保障。"
        ],
        "work": [
            f"依托「{location_name}」帶來的龐大流動人口，具備極強的客群輻射能力，適合佈局高溢價商業配套。",
            f"「{location_name}」強大的通勤賦能顯著縮短跨區時間成本，是吸引高淨值白領階層進駐的絕對優勢。",
            f"交通樞紐如「{location_name}」向來是TOD開發的核心，賦予地塊無可替代的商業流動性。"
        ]
    }
    return random.choice(pools.get(category, pools["live"]))

def generate_ai_report(address, poi_data, official_name):
    system_prompt = """
    你是一位專業的香港地產開發顧問。請根據提供的客觀地塊屬性（周邊設施），進行深度商業評估。
    
    【輸出格式絕對要求】：
    你必須且只能按照以下格式輸出，分為三部分，中間用“===”隔開。
    ！！請務必使用繁體中文（Traditional Chinese）回答！！
    
    核心建議用途：（請用一句話，15個字以內總結）
    ===
    居住潛力指數：XX
    商務潛力指數：XX
    教育潛力指數：XX
    ===
    ### 核心區位研判
    - （請提供第一點深度分析，結合具體地理位置或設施說明，約30-50字）
    - （請提供第二點深度分析，結合具體地理位置或設施說明，約30-50字）
    
    ### 交通與生活機能
    - （請具體點出最核心的車站或商場，並分析其帶來的流動人口優勢，約30-50字）
    - （請分析周邊生活機能的輻射範圍及對物業溢價的影響，約30-50字）
    
    ### 區域市場估算
    - **平均呎價預計**：HK$ XX,XXX - XX,XXX
    - **租金回報預計**：約 X.X%
    
    ### 開發潛力建議
    - （請提供一項具體的商業開發或住宅規劃建議，約30-50字）
    - （請提供一項針對目標客群的精準營銷建議，約30-50字）
    
    【紀律要求】：
    1. 第三部分的報告必須嚴格使用 Markdown 的 ### 標題與 - 列表格式，層次分明。
    2. 每個 bullet point (-) 請寫一段完整的句子（約 30-50 字），內容需具體豐富，不要只寫幾個單詞！
    3. 第二部分的指數必須是 0 到 100 之間的純數字。
    4. 全文必須使用繁體中文，且不要使用任何表情符號。
    """
    
    user_prompt = f"目標地塊：{official_name}\n\n周邊設施名單：\n"
    for key, items_dict in poi_data.items():
        names = list(items_dict.keys())
        names_str = "、".join(names) if names else "無"
        user_prompt += f"- {key} (共 {len(names)} 項): {names_str}\n"
        
    try:
        response = client.chat.completions.create(
            model="glm-4-flash",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.6 
        )
        result_text = response.choices[0].message.content
        
        parts = result_text.split("===")
        rec_use = "綜合潛力開發區"
        scores = {'live': 60, 'work': 60, 'edu': 60}
        report = result_text
        
        if len(parts) >= 3:
            rec_use = parts[0].replace("核心建議用途：", "").strip()
            live_m = re.search(r'居住.*?(\d+)', parts[1])
            work_m = re.search(r'商務.*?(\d+)', parts[1])
            edu_m = re.search(r'教育.*?(\d+)', parts[1])
            if live_m: scores['live'] = int(live_m.group(1))
            if work_m: scores['work'] = int(work_m.group(1))
            if edu_m: scores['edu'] = int(edu_m.group(1))
            report = parts[2].strip()
            
        return rec_use, scores, report
    except Exception as e:
        return "系統連線異常", {'live': 0, 'work': 0, 'edu': 0}, f"AI API 連線失敗：\n\n`{str(e)}`"

def format_hover_text(items):
    names = list(items.keys())
    if not names: return "無數據"
    display_items = names[:8]
    chunks = ["、".join(display_items[i:i+2]) for i in range(0, len(display_items), 2)]
    hover_str = "<br>".join(chunks)
    if len(names) > 8: hover_str += f"<br><br><i>...等共 {len(names)} 項 (詳見下方)</i>"
    return hover_str

RECOMMENDATIONS = {
    "教育學區 (適合學習)": [
        {"name": "九龍塘 (Kowloon Tong)", "price": "HK$ 20,000 - 35,000 / 呎", "desc": "名校網絡密集，適合高階學區房及高端學生公寓開發。"},
        {"name": "何文田 (Ho Man Tin)", "price": "HK$ 18,000 - 28,000 / 呎", "desc": "傳統名校網，高淨值家庭客群密集，抗跌能力極強。"},
        {"name": "沙田 (Sha Tin)", "price": "HK$ 13,000 - 19,000 / 呎", "desc": "鄰近多所高等院校，青年生活圈成熟，適合中端住宅佈局。"}
    ],
    "成熟商圈 (適合生活)": [
        {"name": "銅鑼灣 (Causeway Bay)", "price": "HK$ 22,000 - 35,000 / 呎", "desc": "極高商業價值，適合商住混合體及高端零售綜合體。"},
        {"name": "旺角 (Mong Kok)", "price": "HK$ 15,000 - 23,000 / 呎", "desc": "核心消費區，人流極旺，適合青年共居與潮流商業。"},
        {"name": "元朗 (Yuen Long)", "price": "HK$ 11,000 - 16,000 / 呎", "desc": "新界西核心生活圈，民生消費力強勁，大型屋苑首選。"}
    ],
    "核心商務 (適合工作)": [
        {"name": "中環 (Central)", "price": "HK$ 30,000 - 50,000 / 呎", "desc": "頂級金融中心，適合甲級商廈與高端服務式公寓。"},
        {"name": "觀塘 (Kwun Tong)", "price": "HK$ 12,000 - 18,000 / 呎", "desc": "CBD2 核心，商貿轉型區，商務大廈升值潛力巨大。"},
        {"name": "鰂魚涌 (Quarry Bay)", "price": "HK$ 16,000 - 24,000 / 呎", "desc": "港島東商業樞紐，高薪白領聚集地，長租公寓需求旺盛。"}
    ]
}

# ==========================================
# 3. 頁面佈局：左側控制台 / 右側大屏數據
# ==========================================

with st.sidebar:
    st.markdown("## 智能地塊分析引擎")
    st.markdown("PropTech 空間數據聚合系統")
    st.markdown("---")
    
    st.markdown("### 1. 智能推薦導覽")
    theme_choice = st.selectbox(
        "瀏覽熱門開發主題", 
        ["教育學區 (適合學習)", "成熟商圈 (適合生活)", "核心商務 (適合工作)"]
    )
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 2. 執行商業分析")
    target_address = st.text_input(
        "查詢目標地塊 (必填)", 
        placeholder="輸入地址或關鍵字 (例: 九龍塘)..."
    )
    
    search_radius = st.slider(
        "周邊覆蓋半徑 (米)", 
        min_value=500, max_value=3000, value=1000, step=500
    )
    
    start_btn = st.button("生成商業可行性評估")
    st.markdown("---")
    st.markdown("系統狀態: 連線正常")


st.title("土地開發可行性報告")

rec_container = st.empty()

if not start_btn:
    with rec_container.container():
        st.markdown(f"### 主題導覽：{theme_choice}")
        st.markdown("以下為系統篩選出的高價值參考地段，您可以將其名稱輸入至左側進行深度分析：")
        for item in RECOMMENDATIONS[theme_choice]:
            st.markdown(f"""
                <div class="rec-item-card">
                    <div class="rec-item-title">{item['name']}</div>
                    <div class="rec-item-price">參考均價: {item['price']}</div>
                    <div class="rec-item-desc">核心優勢: {item['desc']}</div>
                </div>
            """, unsafe_allow_html=True)

if start_btn and target_address:
    rec_container.empty()
    
    with st.spinner("系統正在執行高精度空間定位..."):
        lat, lon, official_name = get_coordinates(target_address)
        
    if lat is None or lon is None:
        show_error(f"無法在地圖上定位「{target_address}」。請嘗試更換為更簡短準確的關鍵字。")
        st.stop()
        
    show_success(f"成功鎖定座標區域：{official_name} (Lat: {lat:.4f}, Lon: {lon:.4f})")
    
    with st.spinner(f"正在聚合目標半徑 {search_radius}m 內之設施微觀數據..."):
        poi_data = fetch_poi_data(lat, lon, radius=search_radius)
        
    if poi_data is None:
        show_error("獲取周邊設施數據失敗。開源節點響應超時，請稍後再試或縮小搜尋半徑。")
        st.stop()

    with st.spinner("AI 商業大腦正在深度推演各類潛力指數..."):
        rec_use, scores, report = generate_ai_report(target_address, poi_data, official_name)

    st.markdown(f"""
        <div class="recommendation-card">
            <div class="recommendation-title">AI 綜合判定：目標地塊最適開發用途</div>
            <div class="recommendation-value">{rec_use}</div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("### AI 潛力雷達評分")
    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        st.metric("居住宜居度", f"{scores['live']} / 100")
        st.progress(scores['live'] / 100)
    with col_s2:
        st.metric("商務發展度", f"{scores['work']} / 100")
        st.progress(scores['work'] / 100)
    with col_s3:
        st.metric("教育配套度", f"{scores['edu']} / 100")
        st.progress(scores['edu'] / 100)
    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("### 區域空間數據視圖")
    col_map, col_chart = st.columns([1, 1])
    
    with col_map:
        m = folium.Map(location=[lat, lon], zoom_start=14, tiles="CartoDB positron")
        
        folium.CircleMarker(
            location=[lat, lon], radius=8, popup=official_name,
            color="#FFFFFF", weight=2, fill=True, fill_color="#1D4ED8", fill_opacity=1
        ).add_to(m)
        
        folium.Circle(
            radius=search_radius, location=[lat, lon],
            color="#3B82F6", fill=True, fill_color="#3B82F6", fill_opacity=0.1
        ).add_to(m)
        
        color_map = {
            "地鐵與鐵路站": "#EF4444", 
            "學校與教育機構": "#10B981", 
            "醫院與醫療設施": "#8B5CF6", 
            "購物商場": "#F59E0B"     
        }
        
        for category, items_dict in poi_data.items():
            for name, coords in items_dict.items():
                folium.CircleMarker(
                    location=[coords[0], coords[1]],
                    radius=5,
                    popup=f"{category}: {name}",
                    color="#FFFFFF", weight=1,
                    fill=True, fill_color=color_map[category], fill_opacity=0.9
                ).add_to(m)
                
        st_folium(m, width=600, height=380, returned_objects=[])

    with col_chart:
        chart_data = pd.DataFrame({
            "分類": ["地鐵與鐵路站", "學校與教育機構", "醫院與醫療設施", "購物商場"],
            "數量": [
                len(poi_data['地鐵與鐵路站']), len(poi_data['學校與教育機構']), 
                len(poi_data['醫院與醫療設施']), len(poi_data['購物商場'])
            ],
            "清單": [
                format_hover_text(poi_data['地鐵與鐵路站']), format_hover_text(poi_data['學校與教育機構']),
                format_hover_text(poi_data['醫院與醫療設施']), format_hover_text(poi_data['購物商場'])
            ]
        })

        fig = px.bar(
            chart_data, x="分類", y="數量", text="數量", custom_data=["清單"],
            color_discrete_sequence=["#3B82F6"]
        )
        fig.update_traces(
            textposition='outside', textfont_size=16, textfont_color="#1E293B",
            hovertemplate="<b>%{x}</b><br>總數: %{y}<br><br><b>設施明細:</b><br>%{customdata[0]}<extra></extra>",
            hoverlabel=dict(align="left")
        )
        fig.update_layout(
            xaxis_title=None, yaxis_title=None, showlegend=False,
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=0, r=0, t=20, b=0),
            xaxis=dict(tickangle=0, tickfont=dict(size=14, color="#64748B"), showline=True, linecolor='#E2E8F0', fixedrange=True),
            yaxis=dict(showgrid=True, gridcolor="#F1F5F9", zeroline=True, zerolinecolor="#E2E8F0", fixedrange=True),
            height=380, dragmode=False
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    st.markdown("### 細分客群價值拆解")
    st.markdown("點擊下方分類標籤，深入查看各具體設施與其帶動的周邊物業估值。")
    
    tab_edu, tab_live, tab_work = st.tabs(["學區價值", "宜居價值", "商務價值"])
    
    with tab_edu:
        st.markdown("<br>", unsafe_allow_html=True)
        if poi_data['學校與教育機構']:
            for item in poi_data['學校與教育機構'].keys():
                with st.expander(f"設施名稱：{item}"):
                    price = get_mock_price(item)
                    analysis = get_dynamic_analysis(item, "edu")
                    st.write(f"**周邊物業呎價參考**：`{price}`")
                    st.write(f"**客群潛力分析**：{analysis}")
        else:
            st.info("該目標半徑內暫無抓取到大型教育機構數據。")
            
    with tab_live:
        st.markdown("<br>", unsafe_allow_html=True)
        live_items = list(poi_data['購物商場'].keys()) + list(poi_data['醫院與醫療設施'].keys())
        if live_items:
            for item in live_items:
                with st.expander(f"設施名稱：{item}"):
                    price = get_mock_price(item)
                    analysis = get_dynamic_analysis(item, "live")
                    st.write(f"**周邊物業呎價參考**：`{price}`")
                    st.write(f"**客群潛力分析**：{analysis}")
        else:
            st.info("該目標半徑內暫無抓取到大型商場或醫療數據。")
            
    with tab_work:
        st.markdown("<br>", unsafe_allow_html=True)
        if poi_data['地鐵與鐵路站']:
            for item in poi_data['地鐵與鐵路站'].keys():
                with st.expander(f"樞紐名稱：{item}"):
                    price = get_mock_price(item)
                    analysis = get_dynamic_analysis(item, "work")
                    st.write(f"**周邊核心商圈呎價參考**：`{price}`")
                    st.write(f"**客群潛力分析**：{analysis}")
        else:
            st.info("該目標半徑內暫無抓取到軌道交通樞紐數據。")

    st.markdown("---")
    st.markdown("### AI 商業潛力深度報告")
    
    st.markdown(f'<div class="report-card">\n\n{report}\n\n</div>', unsafe_allow_html=True)
    
    st.download_button(
        label="導出完整商業報告文檔 (TXT)",
        data=f"目標地塊: {official_name}\n最適開發用途: {rec_use}\n\n{report}",
        file_name=f"{target_address}_分析報告.txt",
        mime="text/plain",
        type="primary"
    )
