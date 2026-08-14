import streamlit as st
import requests
import time
from zhipuai import ZhipuAI

st.set_page_config(page_title="智能地块潜力分析", layout="wide")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    [data-testid="stAppViewContainer"] { background-color: #F3F4F6; }
    [data-testid="stForm"] {
        background-color: #FFFFFF; border: 1px solid #E5E7EB;
        border-radius: 12px; padding: 24px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); margin-bottom: 2rem;
    }
    [data-testid="stFormSubmitButton"] > button {
        background-color: #2563EB; color: white !important; border-radius: 8px;
        height: 45px; font-weight: 600; width: 150px; border: none; float: right;
    }
    [data-testid="stFormSubmitButton"] > button:hover {
        background-color: #1D4ED8; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    [data-testid="metric-container"] {
        background-color: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 8px;
        padding: 20px; box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
    }
    [data-testid="stMetricValue"] { font-size: 24px; color: #111827; font-weight: 700; }
    .report-card {
        background-color: #FFFFFF; padding: 30px; border-radius: 12px; border-left: 6px solid #2563EB;
        font-size: 16px; line-height: 1.8; color: #374151; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    .streamlit-expanderHeader { font-weight: 600; color: #374151; }
    </style>
""", unsafe_allow_html=True)

ZHIPU_API_KEY = "2040bad6a4de457db8783082ea9120bc.FDSw7nPPtfv8KCaD"
client = ZhipuAI(api_key=ZHIPU_API_KEY)

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
        headers = {"User-Agent": "PropTech_Feasibility_App/1.0"}
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
    headers = {"User-Agent": "PropTech_Feasibility_App/1.0"}
    
    poi_details = {"地铁与铁路站": [], "学校与教育机构": [], "医院与医疗设施": [], "购物商场": []}
    
    for url in overpass_endpoints:
        try:
            response = requests.post(url, data=overpass_query, headers=headers, timeout=50)
            if response.status_code == 200:
                data = response.json()
                for element in data.get('elements', []):
                    tags = element.get('tags', {})
                    name = tags.get('name:zh', tags.get('name', '未命名设施'))
                    if name == '未命名设施':
                        continue
                        
                    if tags.get('railway') == 'station': 
                        poi_details["地铁与铁路站"].append(name)
                    elif tags.get('amenity') in ['school', 'university', 'college']: 
                        poi_details["学校与教育机构"].append(name)
                    elif tags.get('amenity') in ['hospital', 'clinic']: 
                        poi_details["医院与医疗设施"].append(name)
                    elif tags.get('shop') == 'mall': 
                        poi_details["购物商场"].append(name)
                        
                for key in poi_details:
                    poi_details[key] = list(set(poi_details[key]))
                    
                return poi_details
        except:
            continue
            
    return None

def generate_ai_report(address, poi_data, official_name):
    system_prompt = """
    你是一位专业的香港地产开发顾问。请根据提供的客观地块属性（周边设施），撰写一份「地块初步评估报告」。
    报告必须包含以下重点：
    1. 【核心区位研判】：根据地理位置判断开发的基础条件。
    2. 【交通与生活机能】：客观描述提供的数据，必须提及具体的车站或商场名称。
    3. 【开发潜力建议】：推测适合发展的物业类型并给出商业建议。
    
    【绝对纪律要求】：
    - 必须基于确切的客观数据，禁止脑补实时行情或自行虚构周边的设施与成交数据。没有数据直接说没有。
    - 如果名单显示设施为“无”，必须在分析中客观指出“缺乏该项数据支持”。
    
    请用专业的繁体中文撰写，字数 500 字以内，排版必须清晰、分段明确，严禁使用任何表情符号。
    """
    user_prompt = f"目标地块：{official_name}\n\n"
    
    user_prompt += "周边设施名单：\n"
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
            temperature=0.1
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"AI API 连线失败，真实错误讯息如下：\n\n`{str(e)}`"

st.title("智能地块潜力分析仪表板")
st.markdown("##### 整合空间数据 (GIS) 与大型语言模型，自动生成地段价值评估。")

with st.form("input_card"):
    st.markdown("**新建分析任务**")
    
    target_address = st.text_input(
        "输入目标地块 (必填)", 
        placeholder="请输入地块关键字 (例如: 旺角, 科学园)...",
        label_visibility="collapsed"
    )
    
    search_radius = st.slider("选择周边 POI 分析半径 (米)", min_value=500, max_value=5000, value=1000, step=500)
    
    start_btn = st.form_submit_button("执行可行性分析")

if start_btn and target_address:
    with st.spinner("正在进行地理空间定位..."):
        lat, lon, official_name = get_coordinates(target_address)
        
    if lat is None or lon is None:
        st.error(f"❌ 无法在地图上定位「{target_address}」。请尝试更换更准确的关键字。")
        st.stop()
        
    st.success(f"锁定目标：{official_name} (Lat: {lat:.4f}, Lon: {lon:.4f})")
    
    with st.spinner(f"正在抓取半径 {search_radius}m 内详细设施名单..."):
        poi_data = fetch_poi_data(lat, lon, radius=search_radius)
        
    if poi_data is None:
        st.error("获取周边设施数据失败 (免费节点超时或被限流)。对于过大的搜索半径，建议缩小范围后重新执行分析。")
        st.stop()
        
    st.markdown(f"### 周边设施分布 ({search_radius}m 半径)")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("地铁与铁路站", f"{len(poi_data['地铁与铁路站'])}")
    kpi2.metric("学校与教育机构", f"{len(poi_data['学校与教育机构'])}")
    kpi3.metric("医院与医疗设施", f"{len(poi_data['医院与医疗设施'])}")
    kpi4.metric("购物商场", f"{len(poi_data['购物商场'])}")
    
    with st.expander("点击展开：周边详细设施名单"):
        for category, items in poi_data.items():
            if items:
                st.markdown(f"**{category}**：{', '.join(items)}")
            else:
                st.markdown(f"**{category}**：无")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown("### AI 智慧开发评估报告")
    with st.spinner("系统正在基于各项核心客观数据生成报告..."):
        report = generate_ai_report(target_address, poi_data, official_name)
        st.markdown(f'<div class="report-card">{report}</div>', unsafe_allow_html=True)
