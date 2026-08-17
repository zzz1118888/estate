import streamlit as st
import requests
import time
import pandas as pd
import folium
import plotly.express as px
from streamlit_folium import st_folium
from zhipuai import ZhipuAI
import random

# ==========================================
# 1. 页面设定与修复后的精准 CSS
# ==========================================
st.set_page_config(page_title="智能地块潜力分析", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    [data-testid="stAppViewContainer"] { background-color: #F8FAFC; }
    
    [data-testid="stSidebar"] {
        background-color: #0F172A;
        padding-top: 2rem;
    }
    
    /* 核心修复：精准定位侧边栏文字，不破坏下拉选单(Selectbox)内部结构 */
    [data-testid="stSidebar"] p, 
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3 {
        color: #F1F5F9 !important;
    }
    
    /* 单独确保下拉菜单和输入框内选中的文字是深色可见的 */
    [data-testid="stSidebar"] div[data-baseweb="select"] span,
    [data-testid="stSidebar"] div[data-baseweb="input"] input {
        color: #0F172A !important;
        font-weight: 600;
    }
    
    [data-testid="stSidebar"] button {
        background-color: #3B82F6 !important;
        color: white !important;
        border-radius: 6px;
        height: 48px;
        font-weight: bold;
        border: none;
        width: 100%;
        margin-top: 1rem;
    }
    [data-testid="stSidebar"] button:hover {
        background-color: #2563EB !important;
    }

    .recommendation-card {
        background: linear-gradient(135deg, #1E293B 0%, #334155 100%);
        padding: 30px;
        border-radius: 12px;
        color: white;
        text-align: center;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        margin-bottom: 2rem;
        border-bottom: 4px solid #3B82F6;
    }
    .recommendation-title {
        font-size: 16px; color: #94A3B8; letter-spacing: 2px; margin-bottom: 10px; text-transform: uppercase;
    }
    .recommendation-value {
        font-size: 32px; font-weight: 800; color: #FFFFFF; letter-spacing: 1px;
    }

    [data-testid="metric-container"] {
        background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px;
        padding: 20px; box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
    }
    [data-testid="stMetricValue"] { font-size: 28px; color: #0F172A; font-weight: 800; }
    
    .report-card {
        background-color: #FFFFFF; padding: 35px; border-radius: 12px; border-left: 6px solid #3B82F6;
        font-size: 16px; line-height: 1.8; color: #334155; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); margin-bottom: 1rem;
    }
    
    .rec-item-card {
        background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 20px;
        margin-bottom: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border-left: 4px solid #3B82F6;
    }
    .rec-item-title { font-size: 18px; font-weight: bold; color: #0F172A; margin-bottom: 5px; }
    .rec-item-price { font-size: 16px; color: #DC2626; font-weight: 600; margin-bottom: 10px; }
    .rec-item-desc { font-size: 14px; color: #475569; }

    .custom-alert-error {
        background-color: #FEF2F2; color: #991B1B; padding: 16px; border-radius: 8px; border-left: 6px solid #EF4444; margin-bottom: 1rem; font-weight: 500;
    }
    .custom-alert-success {
        background-color: #F0FDF4; color: #166534; padding: 16px; border-radius: 8px; border-left: 6px solid #22C55E; margin-bottom: 1rem; font-weight: 500;
    }
    
    .streamlit-expanderHeader { color: #1E293B !important; font-weight: 600; }
    .streamlit-expanderContent { color: #334155 !important; }
    </style>
""", unsafe_allow_html=True)

def show_error(msg):
    st.markdown(f'<div class="custom-alert-error">{msg}</div>', unsafe_allow_html=True)

def show_success(msg):
    st.markdown(f'<div class="custom-alert-success">{msg}</div>', unsafe_allow_html=True)

ZHIPU_API_KEY = "2040bad6a4de457db8783082ea9120bc.FDSw7nPPtfv8KCaD"
client = ZhipuAI(api_key=ZHIPU_API_KEY)

def get_mock_price(location_name):
    seed = sum([ord(c) for c in location_name])
    random.seed(seed)
    base_price = random.randint(11000, 28000)
    top_price = base_price + random.randint(1500, 4000)
    return f"HK$ {base_price:,} - {top_price:,} / 呎"

# ==========================================
# 2. 核心数据获取与 AI 评估函数
# ==========================================
@st.cache_data(ttl=86400)
def get_coordinates(address):
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
                    return lat, lon, f"政府标准地址: {address}"
    except:
        pass
        
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {"q": f"{address}, Hong Kong", "format": "json", "limit": 1}
        headers = {"User-Agent": "PropTech_Feasibility_App/5.1"}
        res = requests.get(url, params=params, headers=headers, timeout=5)
        if res.status_code == 200 and len(res.json()) > 0:
            data = res.json()[0]
            display_name = data['display_name'].split(',')[0]
            return float(data['lat']), float(data['lon']), f"空间图资定位: {display_name}"
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
    out tags;
    """
    headers = {"User-Agent": "PropTech_Feasibility_App/5.1"}
    poi_details = {"地铁与铁路站": [], "学校与教育机构": [], "医院与医疗设施": [], "购物商场": []}
    
    for url in overpass_endpoints:
        try:
            response = requests.post(url, data=overpass_query, headers=headers, timeout=50)
            if response.status_code == 200:
                data = response.json()
                for element in data.get('elements', []):
                    tags = element.get('tags', {})
                    name = tags.get('name:zh', tags.get('name', '未命名设施'))
                    if name == '未命名设施': continue
                    
                    if tags.get('railway') == 'station': 
                        exclude_keywords = ['大街', '世界', '探险', '明日', '山谷', '小镇', '缆车', '昂坪', '海洋', '公园']
                        if any(k in name for k in exclude_keywords):
                            continue
                        if '站' not in name and 'Station' not in name:
                            name = f"{name}站"
                        poi_details["地铁与铁路站"].append(name)
                        
                    elif tags.get('amenity') in ['school', 'university', 'college']: 
                        poi_details["学校与教育机构"].append(name)
                    elif tags.get('amenity') in ['hospital', 'clinic']: 
                        poi_details["医院与医疗设施"].append(name)
                    elif tags.get('shop') == 'mall': 
                        poi_details["购物商场"].append(name)
                        
                for key in poi_details: poi_details[key] = list(set(poi_details[key]))
                return poi_details
        except:
            continue
    return None

@st.cache_data(ttl=3600)
def generate_facility_evaluations(poi_data):
    all_pois = []
    for category, items in poi_data.items():
        all_pois.extend(items)
        
    if not all_pois:
        return {}
        
    if len(all_pois) > 20:
        all_pois = random.sample(all_pois, 20)
        
    poi_str = "、".join(all_pois)
    
    system_prompt = """
    你是一位香港地产数据分析专家。我将给你一组香港的具体设施名称。
    请为每一个设施，提供一句极其精简的（10到20字以内）「微观商业与客群价值评估」。
    
    【输出格式严格要求】：
    设施A：具体的评价内容
    设施B：具体的评价内容
    
    注意：
    1. 必须根据设施的真实属性来写，例如名校就提教育刚需，商场就提消费吸附，医院就提康养需求。
    2. 评价必须客观专业。
    3. 绝对禁止使用任何表情符号。
    """
    user_prompt = f"请评估以下设施：\n{poi_str}"
    
    eval_dict = {}
    try:
        response = client.chat.completions.create(
            model="glm-4-flash",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3
        )
        result_text = response.choices[0].message.content
        
        for line in result_text.split('\n'):
            line = line.strip()
            if '：' in line:
                k, v = line.split('：', 1)
                eval_dict[k.strip('- *')] = v.strip()
            elif ':' in line:
                k, v = line.split(':', 1)
                eval_dict[k.strip('- *')] = v.strip()
    except Exception as e:
        pass
        
    return eval_dict


def generate_ai_report(address, poi_data, official_name):
    system_prompt = """
    你是一位专业的香港地产开发顾问。请根据提供的客观地块属性（周边设施），进行初步评估。
    
    【输出格式绝对要求】：
    你必须且只能按照以下格式输出，分为两部分，中间用“===”隔开：
    
    核心建议用途：（请用一句话，10个字以内总结。注意：必须根据该地段特性推断）
    ===
    1. 【核心区位研判】：根据地理位置判断开发的基础条件。
    2. 【交通与生活机能】：客观描述提供的数据，必须提及具体的车站或商场名称。
    3. 【区域市场行情估算】：基于历史大数据的宏观估算，提取该大区的「历史平均尺价区间估算」与「租金回报率水平参考」。
    4. 【开发潜力建议】：推测适合发展的物业类型并给出具体商业建议。
    
    【纪律要求】：
    - 严禁使用任何表情符号。
    - 必须基于真实数据，没有的设施请明确说明。
    """
    user_prompt = f"目标地块：{official_name}\n\n周边设施名单：\n"
    for key, items in poi_data.items():
        names_str = "、".join(items) if items else "无"
        user_prompt += f"- {key} (共 {len(items)} 项): {names_str}\n"
        
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
        if "===" in result_text:
            rec_use, full_report = result_text.split("===", 1)
            rec_use = rec_use.replace("核心建议用途：", "").strip()
            return rec_use, full_report.strip()
        else:
            return "综合潜力开发区", result_text.strip()
    except Exception as e:
        return "系统连线异常", f"AI API 连线失败，真实错误讯息如下：\n\n`{str(e)}`"

def format_hover_text(items):
    if not items: return "无数据"
    chunks = [", ".join(items[i:i+3]) for i in range(0, len(items), 3)]
    return "<br>".join(chunks)

RECOMMENDATIONS = {
    "教育学区 (适合学习)": [
        {"name": "九龙塘 (Kowloon Tong)", "price": "HK$ 20,000 - 35,000 / 呎", "desc": "名校网络密集，适合高阶学区房及高端学生公寓开发。"},
        {"name": "何文田 (Ho Man Tin)", "price": "HK$ 18,000 - 28,000 / 呎", "desc": "传统名校网，高净值家庭客群密集，抗跌能力极强。"},
        {"name": "沙田 (Sha Tin)", "price": "HK$ 13,000 - 19,000 / 呎", "desc": "邻近多所高等院校，青年生活圈成熟，适合中端住宅布局。"},
        {"name": "薄扶林 (Pok Fu Lam)", "price": "HK$ 20,000 - 32,000 / 呎", "desc": "毗邻香港大学，学术氛围浓厚，适合高端家庭与教职员住宅。"},
        {"name": "红磡 (Hung Hom)", "price": "HK$ 15,000 - 22,000 / 呎", "desc": "近理大与城大，内地留学生租房热点，极适合投资青年公寓。"}
    ],
    "成熟商圈 (适合生活)": [
        {"name": "铜锣湾 (Causeway Bay)", "price": "HK$ 22,000 - 35,000 / 呎", "desc": "极高商业价值，适合商住混合体及高端零售综合体。"},
        {"name": "旺角 (Mong Kok)", "price": "HK$ 15,000 - 23,000 / 呎", "desc": "核心消费区，人流极旺，适合青年共居与潮流商业。"},
        {"name": "元朗 (Yuen Long)", "price": "HK$ 11,000 - 16,000 / 呎", "desc": "新界西核心生活圈，民生消费力强劲，大型屋苑首选。"},
        {"name": "荃湾 (Tsuen Wan)", "price": "HK$ 13,000 - 18,000 / 呎", "desc": "交通枢纽与大型商场林立，配套完善，深受中产家庭青睐。"},
        {"name": "将军澳 (Tseung Kwan O)", "price": "HK$ 14,000 - 20,000 / 呎", "desc": "新兴中产社区，天桥网络与商场相连，极具生活便利性。"}
    ],
    "核心商务 (适合工作)": [
        {"name": "中环 (Central)", "price": "HK$ 30,000 - 50,000 / 呎", "desc": "顶级金融中心，适合甲级商厦与高端服务式公寓。"},
        {"name": "观塘 (Kwun Tong)", "price": "HK$ 12,000 - 18,000 / 呎", "desc": "CBD2 核心，商贸转型区，商务大厦升值潜力巨大。"},
        {"name": "鲗鱼涌 (Quarry Bay)", "price": "HK$ 16,000 - 24,000 / 呎", "desc": "港岛东商业枢纽，高薪白领聚集地，长租公寓需求旺盛。"},
        {"name": "金钟 (Admiralty)", "price": "HK$ 28,000 - 45,000 / 呎", "desc": "政商交汇处，交通四通八达，适合顶级企业总部及高端配套。"},
        {"name": "九龙湾 (Kowloon Bay)", "price": "HK$ 11,000 - 16,000 / 呎", "desc": "东九龙核心商业区扩展地带，租金回报稳定，适合新兴企业入驻。"}
    ]
}

# ==========================================
# 3. 页面布局：左侧控制台 / 右侧大屏数据
# ==========================================

with st.sidebar:
    st.markdown("## 智能地块分析引擎")
    st.markdown("PropTech 空间数据聚合系统")
    st.markdown("---")
    
    st.markdown("### 1. 智能推荐导览")
    theme_choice = st.selectbox(
        "浏览热门开发主题", 
        ["教育学区 (适合学习)", "成熟商圈 (适合生活)", "核心商务 (适合工作)"]
    )
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 2. 执行商业分析")
    target_address = st.text_input(
        "查询目标地块 (必填)", 
        placeholder="输入地址或关键字 (例: 九龙塘)..."
    )
    
    search_radius = st.slider(
        "周边覆盖半径 (米)", 
        min_value=500, max_value=3000, value=1000, step=500
    )
    
    start_btn = st.button("生成商业可行性评估")
    st.markdown("---")
    st.markdown("系统状态: 连线正常")


st.title("土地开发可行性报告")

rec_container = st.empty()

if not start_btn:
    with rec_container.container():
        st.markdown(f"### 主题导览：{theme_choice}")
        st.markdown("以下为系统筛选出的高价值参考地段，您可以将其名称输入至左侧进行深度分析：")
        for item in RECOMMENDATIONS[theme_choice]:
            st.markdown(f"""
                <div class="rec-item-card">
                    <div class="rec-item-title">{item['name']}</div>
                    <div class="rec-item-price">参考均价: {item['price']}</div>
                    <div class="rec-item-desc">核心优势: {item['desc']}</div>
                </div>
            """, unsafe_allow_html=True)

if start_btn and target_address:
    rec_container.empty()
    
    with st.spinner("系统正在执行高精度空间定位..."):
        lat, lon, official_name = get_coordinates(target_address)
        
    if lat is None or lon is None:
        show_error(f"无法在地图上定位「{target_address}」。请尝试更换为更简短准确的关键字。")
        st.stop()
        
    show_success(f"成功锁定坐标区域：{official_name} (Lat: {lat:.4f}, Lon: {lon:.4f})")
    
    with st.spinner(f"正在聚合目标半径 {search_radius}m 内之设施微观数据..."):
        poi_data = fetch_poi_data(lat, lon, radius=search_radius)
        
    if poi_data is None:
        show_error("获取周边设施数据失败。开源节点响应超时，请稍后再试或缩小搜寻半径。")
        st.stop()

    with st.spinner("AI 正在深度解构各项设施的微观商业价值..."):
        ai_facility_evals = generate_facility_evaluations(poi_data)

    with st.spinner("AI 商业大脑正在研判最适开发定位..."):
        rec_use, report = generate_ai_report(target_address, poi_data, official_name)

    st.markdown(f"""
        <div class="recommendation-card">
            <div class="recommendation-title">AI 综合判定：目标地块最适开发用途</div>
            <div class="recommendation-value">{rec_use}</div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("### 区域空间数据视图")
    col_map, col_chart = st.columns([1, 1])
    
    with col_map:
        m = folium.Map(location=[lat, lon], zoom_start=14, tiles="CartoDB positron")
        
        folium.CircleMarker(
            location=[lat, lon],
            radius=8,
            popup=official_name,
            color="#FFFFFF",      
            weight=2,
            fill=True,
            fill_color="#1D4ED8", 
            fill_opacity=1
        ).add_to(m)
        
        folium.Circle(
            radius=search_radius, location=[lat, lon],
            color="#3B82F6", fill=True, fill_color="#3B82F6", fill_opacity=0.1
        ).add_to(m)
        st_folium(m, width=600, height=380, returned_objects=[])

    with col_chart:
        chart_data = pd.DataFrame({
            "分类": ["地铁与铁路站", "学校与教育机构", "医院与医疗设施", "购物商场"],
            "数量": [
                len(poi_data['地铁与铁路站']), len(poi_data['学校与教育机构']), 
                len(poi_data['医院与医疗设施']), len(poi_data['购物商场'])
            ],
            "清单": [
                format_hover_text(poi_data['地铁与铁路站']), format_hover_text(poi_data['学校与教育机构']),
                format_hover_text(poi_data['医院与医疗设施']), format_hover_text(poi_data['购物商场'])
            ]
        })

        fig = px.bar(
            chart_data, x="分类", y="数量", text="数量", custom_data=["清单"],
            color_discrete_sequence=["#3B82F6"]
        )
        fig.update_traces(
            textposition='outside', textfont_size=16, textfont_color="#1E293B",
            hovertemplate="<b>%{x}</b><br>总数: %{y}<br><br><b>设施明细:</b><br>%{customdata[0]}<extra></extra>"
        )
        fig.update_layout(
            xaxis_title=None, yaxis_title=None, showlegend=False,
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=0, r=0, t=20, b=0),
            xaxis=dict(tickangle=0, tickfont=dict(size=14, color="#64748B"), showline=True, linecolor='#E2E8F0'),
            yaxis=dict(showgrid=True, gridcolor="#F1F5F9", zeroline=True, zerolinecolor="#E2E8F0"),
            height=380
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    st.markdown("### 细分客群价值拆解 (AI 实景评估)")
    st.markdown("点击下方分类标签，深入查看各具体设施与其带动的周边物业估值。")
    
    tab_edu, tab_live, tab_work = st.tabs(["[教育客群] 学区价值", "[生活客群] 宜居价值", "[通勤客群] 商务价值"])
    
    with tab_edu:
        st.markdown("<br>", unsafe_allow_html=True)
        if poi_data['学校与教育机构']:
            for item in poi_data['学校与教育机构']:
                with st.expander(f"设施名称：{item}"):
                    price = get_mock_price(item)
                    analysis = ai_facility_evals.get(item, "有效吸引周边家庭与教职群体，为物业带来稳定居住刚需。")
                    st.write(f"**周边物业尺价参考**：`{price}`")
                    st.write(f"**客群潜力分析**：{analysis}")
        else:
            st.info("该目标半径内暂无抓取到大型教育机构数据。")
            
    with tab_live:
        st.markdown("<br>", unsafe_allow_html=True)
        live_items = poi_data['购物商场'] + poi_data['医院与医疗设施']
        if live_items:
            for item in live_items:
                with st.expander(f"设施名称：{item}"):
                    price = get_mock_price(item)
                    analysis = ai_facility_evals.get(item, "显著优化地块的生活便利度与社区配套，提升区内物业溢价。")
                    st.write(f"**周边物业尺价参考**：`{price}`")
                    st.write(f"**客群潜力分析**：{analysis}")
        else:
            st.info("该目标半径内暂无抓取到大型商场或医疗数据。")
            
    with tab_work:
        st.markdown("<br>", unsafe_allow_html=True)
        if poi_data['地铁与铁路站']:
            for item in poi_data['地铁与铁路站']:
                with st.expander(f"枢纽名称：{item}"):
                    price = get_mock_price(item)
                    analysis = ai_facility_evals.get(item, "依托交通节点带来的庞大流动人口，具备极强的客群辐射能力。")
                    st.write(f"**周边核心商圈尺价参考**：`{price}`")
                    st.write(f"**客群潜力分析**：{analysis}")
        else:
            st.info("该目标半径内暂无抓取到轨道交通枢纽数据。")

    st.markdown("---")
    st.markdown("### AI 商业潜力深度报告")
    st.markdown(f'<div class="report-card">{report}</div>', unsafe_allow_html=True)
    
    st.download_button(
        label="导出完整商业报告文档 (TXT)",
        data=f"目标地块: {official_name}\n最适开发用途: {rec_use}\n\n{report}",
        file_name=f"{target_address}_分析报告.txt",
        mime="text/plain",
        type="primary"
    )
