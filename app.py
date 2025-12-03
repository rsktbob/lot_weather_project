import streamlit as st
import urllib3
import sqlite3
import requests
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.features import DivIcon
from datetime import datetime

# --- 設定 ---
API_KEY = 'CWA-6D04DE83-83D8-40C0-BE15-5B6EFC667058'
DB_NAME = 'data.db'

# --- 台灣各縣市經緯度中心點 (手動對照表) ---
CITY_COORDS = {
    "基隆市": [25.13, 121.74],
    "臺北市": [25.09, 121.56],
    "新北市": [24.95, 121.48], # 稍微往下移一點避免跟台北重疊
    "桃園市": [24.93, 121.25],
    "新竹市": [24.80, 120.97],
    "新竹縣": [24.70, 121.10],
    "苗栗縣": [24.50, 120.90],
    "臺中市": [24.15, 120.68],
    "彰化縣": [24.00, 120.45],
    "南投縣": [23.90, 120.95],
    "雲林縣": [23.70, 120.43],
    "嘉義市": [23.48, 120.45],
    "嘉義縣": [23.45, 120.60], # 移往山區一點
    "臺南市": [23.15, 120.25],
    "高雄市": [22.80, 120.45], # 移往中間
    "屏東縣": [22.45, 120.60],
    "宜蘭縣": [24.60, 121.70],
    "花蓮縣": [23.80, 121.50],
    "臺東縣": [22.90, 121.10],
    "澎湖縣": [23.57, 119.60],
    "金門縣": [24.44, 118.33],
    "連江縣": [26.15, 119.93]
}

# --- 資料庫處理 (保持不變) ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS forecast_36h (
            location TEXT PRIMARY KEY,
            wx TEXT,
            min_t INTEGER,
            max_t INTEGER,
            pop INTEGER,
            ci TEXT,
            update_time TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_data_to_db(data_36h):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    for item in data_36h:
        c.execute('''
            INSERT OR REPLACE INTO forecast_36h (location, wx, min_t, max_t, pop, ci, update_time)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (item['location'], item['wx'], item['min_t'], item['max_t'], item['pop'], item['ci'], datetime.now()))
    conn.commit()
    conn.close()

def get_data_from_db():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql('SELECT * FROM forecast_36h', conn)
    conn.close()
    return df

# --- API 抓取 (簡化為只抓 36小時供地圖使用) ---
def fetch_data():
    url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001?Authorization={API_KEY}&format=JSON"
    try:
        # 忽略不安全連線的警告
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # 加入 verify=False 來略過 SSL 檢查
        r = requests.get(url, verify=False)
        
        data = r.json()
        parsed = []
        if data['success'] == 'true':
            for loc in data['records']['location']:
                # 取最近 12 小時
                we = loc['weatherElement']
                parsed.append({
                    'location': loc['locationName'],
                    'wx': we[0]['time'][0]['parameter']['parameterName'], # Wx
                    'pop': we[1]['time'][0]['parameter']['parameterName'], # PoP
                    'min_t': int(we[2]['time'][0]['parameter']['parameterName']), # MinT
                    'max_t': int(we[4]['time'][0]['parameter']['parameterName']), # MaxT
                    'ci': we[3]['time'][0]['parameter']['parameterName'] # CI
                })
        return parsed
    except Exception as e:
        st.error(f"API 錯誤: {e}")
        return None

# --- 地圖輔助功能 ---
def get_color(temp):
    """根據溫度決定顏色"""
    if temp < 15: return '#3182ce' # 藍 (冷)
    if temp < 20: return '#38a169' # 綠 (涼)
    if temp < 28: return '#dd6b20' # 橘 (暖)
    return '#e53e3e' # 紅 (熱)

def create_taiwan_map(df):
    # 建立地圖中心點 (台灣中心)
    m = folium.Map(location=[23.7, 121.0], zoom_start=8, tiles="CartoDB positron")

    for index, row in df.iterrows():
        city = row['location']
        if city in CITY_COORDS:
            lat, lon = CITY_COORDS[city]
            avg_temp = (row['min_t'] + row['max_t']) / 2
            color = get_color(avg_temp)
            
            # 1. 建立圓圈標記 (點下去會有詳細資訊)
            folium.CircleMarker(
                location=[lat, lon],
                radius=15,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.3,
                popup=folium.Popup(f"<b>{city}</b><br>{row['wx']}<br>氣溫: {row['min_t']}-{row['max_t']}°C<br>降雨: {row['pop']}%", max_width=200)
            ).add_to(m)

            # 2. 建立文字標籤 (模仿氣象署直接顯示溫度數字)
            # 使用 DivIcon 寫 HTML
            folium.Marker(
                location=[lat, lon],
                icon=DivIcon(
                    icon_size=(150,36),
                    icon_anchor=(75, 12), # 調整文字位置使其居中
                    html=f"""
                        <div style="
                            font-size: 14px; 
                            font-weight: bold; 
                            color: {color}; 
                            text-align: center;
                            text-shadow: 1px 1px 2px white;">
                            {int(avg_temp)}°C
                        </div>
                    """
                )
            ).add_to(m)
            
            # 3. 顯示縣市名稱 (字比較小，顯示在溫度下方)
            folium.Marker(
                location=[lat - 0.08, lon], # 稍微往下偏一點
                icon=DivIcon(
                    icon_size=(150,36),
                    icon_anchor=(75, 12),
                    html=f"""
                        <div style="font-size: 10px; color: #555; text-align: center; text-shadow: 1px 1px 0px white;">
                            {city}
                        </div>
                    """
                )
            ).add_to(m)

    return m

# --- 主程式 ---
def main():
    st.set_page_config(page_title="台灣氣象地圖", page_icon="🗺️", layout="wide")
    
    init_db()

    # 側邊欄控制
    with st.sidebar:
        st.title("控制面板")
        if st.button("🔄 更新氣象資料", type="primary"):
            with st.spinner("下載中..."):
                data = fetch_data()
                if data:
                    save_data_to_db(data)
                    st.success("更新完成！")
                    st.rerun()
        
        st.info("地圖顯示的是未來 12 小時的「平均氣溫」。")

    # 讀取資料
    df = get_data_from_db()

    st.title("🗺️ 台灣氣溫分布圖 (仿氣象署風格)")
    st.caption(f"資料來源：CWA Open Data | 本地資料庫：{DB_NAME}")

    if df.empty:
        st.warning("資料庫為空，請點擊左側「更新氣象資料」")
    else:
        # 版面配置：左邊地圖 (70%)，右邊表格 (30%)
        col_map, col_table = st.columns([7, 3])

        with col_map:
            map_obj = create_taiwan_map(df)
            st_folium(map_obj, width="100%", height=600)

        with col_table:
            st.subheader("詳細數據列表")
            
            # 簡單的顏色格式化函式
            def highlight_temp(val):
                temp = int(val.split('-')[0]) # 取最低溫來判斷
                color = get_color(temp)
                return f'color: {color}; font-weight: bold'

            # 整理顯示用的 DataFrame
            display_df = df[['location', 'min_t', 'max_t', 'wx', 'pop']].copy()
            display_df['氣溫範圍'] = display_df.apply(lambda x: f"{x['min_t']}-{x['max_t']}", axis=1)
            display_df = display_df.rename(columns={'location': '縣市', 'wx': '天氣', 'pop': '降雨%'})
            display_df = display_df[['縣市', '氣溫範圍', '天氣', '降雨%']]

            st.dataframe(
                display_df, 
                height=600,
                hide_index=True,
                use_container_width=True
            )

if __name__ == "__main__":
    main()