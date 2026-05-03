import re
import datetime as _dt
import os

path = 'i:/網頁/my-fate-web-new/app.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update generate_ai_text function
new_func = """def generate_ai_text(api_key: str, model_name: str, module_name: str, payload: dict, selected_books: list[str], is_master: bool = False) -> str:
    # 這裡的 api_key 主要是用於 sidebar 設定，若 st.secrets 已設定則可選
    if not api_key and "GOOGLE_API_KEY" not in st.secrets and "GEMINI_API_KEY" not in st.secrets:
        return "NO_API_KEY"
    
    # 若使用者在 sidebar 輸入了 key，優先使用
    if api_key:
        genai.configure(api_key=api_key)
    
    # 取得當前台灣時間 (UTC+8)
    now_tw = (_dt.datetime.utcnow() + _dt.timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")

    def json_serial(obj):
        if hasattr(obj, 'isoformat'): return obj.isoformat()
        if hasattr(obj, 'text'): return obj.text
        return str(obj)

    star_info = ""
    if "main_person" in payload and payload["main_person"].get("ziwei_chart"):
        star_info += "【主命主星曜】\\n" + "\\n".join([f"{p['name']}主星={'、'.join(p['major_stars'])}" for p in payload["main_person"]["ziwei_chart"].get('palaces', [])]) + "\\n"
    if "partner_person" in payload and payload["partner_person"].get("ziwei_chart"):
        star_info += "【對象星曜】\\n" + "\\n".join([f"{p['name']}主星={'、'.join(p['major_stars'])}" for p in payload["partner_person"]["ziwei_chart"].get('palaces', [])]) + "\\n"

    if not is_master:
        # 【新版白話文＋八字用神大綱】
        prompt = f\"\"\"
        你現在是一位親切、直白且專業的現代命理分析師。
        請根據這份【專屬生命地圖解析】大綱，產出一份白話文風格的測算結果。
        
        【系統資訊】：
        - [登錄時間]: {now_tw}
        
        【客人資料】：
        - [客人姓名]: {payload["main_person"]["person"].name}
        - [八字命盤]: 
            - 年柱: {payload["main_person"]["pillars"]["year"].text}
            - 月柱: {payload["main_person"]["pillars"]["month"].text}
            - 日柱: {payload["main_person"]["pillars"]["day"].text}
            - 時柱: {payload["main_person"]["pillars"]["hour"].text}
        
        【解析要求】：
        1. 語氣要現代、口語化，像是朋友間的深度對話，禁止使用「汝」、「吾」、「汝的內在驅動力」或「見父母宮」等文言文詞彙。
        2. 請根據命盤推算出客人的 [八字用神]，並針對該用神提供 [八字用神專屬建議內容]。
        3. ### 【天命密碼】：用白話點出客人的性格核心優勢與潛在挑戰。
        4. ### 【命運預告】：針對 2026 年提供一個具體的轉折點預告（不給具體月份與解法，引導後續諮詢）。
        5. ### 【用神建議】：詳細說明 [八字用神] 對客人的重要性，並給出具體的「用神補強建議」。
        6. 最後強制加上：✨ **【想解鎖完整的「破局戰術」與「運勢攻略」？】** ✨ 請截圖此畫面並點擊下方 LINE 連結預約大師！
        \"\"\"
    else:
        books = "、".join(selected_books) if selected_books else "（未指定）"
        # 【大師深度模式 - 也要改為白話專業風格】
        prompt = f\"\"\"
        你是一位頂級命理分析師。模組：{module_name}。
        請給出包含靈魂共振、命理金箔、破局戰術的深度解析。
        請使用現代、直白且富有洞見的語氣，禁止使用陳舊文言文（如「汝」、「吾」）。
        參考學理：{books}。
        
        【系統資訊】：
        - [登錄時間]: {now_tw}
        
        【客人資料】：
        - [客人姓名]: {payload["main_person"]["person"].name}
        - [八字命盤]: {payload["main_person"]["pillars"]["year"].text}, {payload["main_person"]["pillars"]["month"].text}, {payload["main_person"]["pillars"]["day"].text}, {payload["main_person"]["pillars"]["hour"].text}
        {star_info}
        \"\"\"

    result = get_bazi_analysis(prompt, model_name=model_name)
    return result if result else "🚨 大師目前閉關中，請稍後再試。" """

# Replace function
pattern = re.compile(r'def generate_ai_text\(.*?\).*?return result if result else \".*?\"', re.DOTALL)
content = pattern.sub(new_func, content)

# 2. Update UI to show timestamp
old_ui = """                st.markdown(f"### 🖋️ 大師論斷：{module_name}")
                st.markdown(f"<div class='report-card'>{result}</div>", unsafe_allow_html=True)"""
new_ui = """                now_tw = (_dt.datetime.utcnow() + _dt.timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')
                st.info(f"🕒 測算登錄時間：{now_tw}")
                st.markdown(f"### 🖋️ 大師論斷：{module_name}")
                st.markdown(f"<div class='report-card'>{result}</div>", unsafe_allow_html=True)"""
content = content.replace(old_ui, new_ui)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
