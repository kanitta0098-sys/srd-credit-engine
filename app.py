import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
import numpy as np

# ==========================================
# 1. ตั้งค่าหน้าตาเว็บแอป และ API Key
# ==========================================
st.set_page_config(page_title="SRD Credit Investigation Engine", layout="wide", page_icon="🏍️")
st.title("🏍️ SRD Credit Investigation Engine (V2 - Auto Calc)")
st.caption("ระบบวิเคราะห์ความสามารถทางการเงินและตรวจจับความเสี่ยงสินเชื่อ (ดึงค่างวดอัตโนมัติ)")

# ใส่ Gemini API Key ของคุณที่นี่
GEMINI_API_KEY = "ใส่_API_KEY_ของคุณที่นี่"
genai.configure(api_key=GEMINI_API_KEY)

# ==========================================
# 2. ฟังก์ชันดึงข้อมูลจากไฟล์ Excel ตารางราคารถ
# ==========================================
@st.cache_data
def load_motorcycle_data():
    file_path = 'Yamaha_+รวมขายทุกตัว 25-8-69 Dynamic_Formulas_Categories.xlsx'
    motorcycle_dict = {}
    
    try:
        # 1. โหลดข้อมูล Yamaha (แผ่น Auto เป็นตัวอย่าง)
        df_yamaha = pd.read_excel(file_path, sheet_name='Auto', skiprows=1)
        # เปลี่ยนชื่อคอลัมน์ให้อ่านง่าย
        df_yamaha = df_yamaha.rename(columns={
            'ตารางผ่อน': '12', 'Unnamed: 9': '18', 'Unnamed: 10': '24', 
            'Unnamed: 11': '30', 'Unnamed: 12': '36', 'Unnamed: 13': '48'
        })
        df_yamaha = df_yamaha.drop(0) # ทิ้งแถวแรกที่เป็น header ซ้ำ
        df_yamaha[['รุ่นรถ', 'ราคาจัด', 'ดอกเบี้ย\n(ต่อเดือน)']] = df_yamaha[['รุ่นรถ', 'ราคาจัด', 'ดอกเบี้ย\n(ต่อเดือน)']].ffill()
        df_yamaha = df_yamaha.dropna(subset=['รุ่นรถ'])
        motorcycle_dict['Yamaha - Auto'] = df_yamaha

        # 2. โหลดข้อมูล Honda
        df_honda = pd.read_excel(file_path, sheet_name='รถใหม่_Honda', skiprows=1)
        df_honda = df_honda.rename(columns={
            'ตารางผ่อน': '12', 'Unnamed: 8': '24', 'Unnamed: 9': '36', 'Unnamed: 10': '48'
        })
        df_honda = df_honda.drop(0)
        df_honda[['รุ่นรถ', 'ราคาจัด', 'ดอกเบี้ย\n(ต่อเดือน)']] = df_honda[['รุ่นรถ', 'ราคาจัด', 'ดอกเบี้ย\n(ต่อเดือน)']].ffill()
        df_honda = df_honda.dropna(subset=['รุ่นรถ'])
        # เปลี่ยนชื่อคอลัมน์เงินดาวน์ให้ตรงกับ Yamaha
        if 'เงินดาวน์' in df_honda.columns:
            df_honda = df_honda.rename(columns={'เงินดาวน์': 'ดาวน์'})
            
        motorcycle_dict['Honda - ใหม่'] = df_honda
        
        return motorcycle_dict
    except Exception as e:
        st.error(f"ไม่สามารถโหลดไฟล์ Excel ได้: {e}")
        return None

# โหลดข้อมูลรถเตรียมไว้
motorcycle_data = load_motorcycle_data()

# ==========================================
# 3. จัดแบ่งหน้าจอเป็น 2 ฝั่ง
# ==========================================
col1, col2 = st.columns([1.2, 1])

with col1:
    st.subheader("🛒 1. เลือกรุ่นรถและคำนวณค่างวด")
    
    # --- ส่วนเลือกรถ ---
    new_installment = 0
    if motorcycle_data:
        brand_category = st.selectbox("เลือกหมวดหมู่รถ", list(motorcycle_data.keys()))
        df_selected = motorcycle_data[brand_category]
        
        # ดึงรายชื่อรุ่นรถที่ไม่ซ้ำกัน
        models = df_selected['รุ่นรถ'].unique().tolist()
        selected_model = st.selectbox("เลือกรุ่นรถ", models)
        
        # กรองข้อมูลเฉพาะรุ่นที่เลือก
        df_model = df_selected[df_selected['รุ่นรถ'] == selected_model]
        
        # เลือกเงินดาวน์ที่มีให้เลือกในรุ่นนั้น
        down_payments = df_model['ดาวน์'].unique().tolist()
        selected_down = st.selectbox("เลือกเงินดาวน์ (บาท)", [int(x) for x in down_payments if pd.notna(x)])
        
        # กรองให้เหลือแถวเดียวที่ตรงกับรุ่นและดาวน์
        final_row = df_model[df_model['ดาวน์'] == selected_down].iloc[0]
        
        # เลือกระยะเวลาผ่อน (เช็คว่ามีคอลัมน์ไหนบ้าง)
        term_options = [col for col in ['12', '18', '24', '30', '36', '48'] if col in final_row.index and pd.notna(final_row[col])]
        selected_term = st.selectbox("ระยะเวลาผ่อน (งวด)", term_options)
        
        # ดึงค่างวดออกมา
        new_installment = final_row[selected_term]
        
        st.info(f"🏍️ **รถที่เลือก:** {selected_model} | **ยอดดาวน์:** ฿{selected_down:,} | **ส่งงวดละ:** ฿{new_installment:,.0f} x {selected_term} เดือน")
    else:
        # กรณีไม่มีไฟล์ Excel ให้กรอกมือ
        new_installment = st.number_input("ค่างวดรถใหม่ที่ขอจัด (บาท)", value=1890, step=100)

    st.write("---")
    st.subheader("📊 2. คำนวณความสามารถทางการเงิน (Math Engine)")
    
    col_a, col_b = st.columns(2)
    with col_a:
        salary = st.number_input("ฐานเงินเดือนประจำสุทธิ (บาท)", value=21000, step=500)
        extra_income = st.number_input("รายได้เสริมที่พิสูจน์ได้ (บาท)", value=5100, step=500)
    with col_b:
        existing_debt = st.number_input("หนี้ในระบบ / โอนออกประจำ (บาท)", value=5000, step=500)
        living_cost = st.number_input("ค่าครองชีพมาตรฐาน (บาท)", value=7000, step=500)

    # คำนวณสูตรตามตาราง SRD Calculator
    total_income = salary + extra_income
    total_debt_all = existing_debt + new_installment
    dsr = (total_debt_all / total_income) * 100 if total_income > 0 else 0
    multiplier = salary / new_installment if new_installment > 0 else 0
    net_free_cash = total_income - (existing_debt + living_cost + new_installment)

    st.markdown("### สรุปความสามารถทางการเงิน")
    st.markdown(f"**รวมรายได้:** `{total_income:,.0f}` บาท")
    st.markdown(f"**สัดส่วนภาระหนี้ต่อรายได้ (DSR):** `{dsr:.1f}%` *(เกณฑ์: ไม่ควรเกิน 35-50%)*")
    st.markdown(f"**เงินเดือนต่อค่างวด (Multiplier):** `{multiplier:.1f} เท่า` *(เกณฑ์: > 2.5 เท่า)*")
    st.markdown(f"**เงินคงเหลือสุทธิ (Net Free Cash):** `{net_free_cash:,.0f} บาท`")

    # ประเมินผลเบื้องต้น
    if net_free_cash > 0 and dsr <= 50:
        st.success("🟢 PASS (ความสามารถทางการเงินผ่านเกณฑ์เบื้องต้น)")
    else:
        st.error("🔴 HIGH RISK / CONDITIONAL (ภาระหนี้สูงหรือเงินเหลือไม่พอ)")

with col2:
    st.subheader("🔍 3. AI วิเคราะห์ Statement & ความเสี่ยง")
    
    uploaded_file = st.file_uploader("อัปโหลดภาพ Statement หรือสลิปเงินเดือน", type=["png", "jpg", "jpeg"])
    customer_story = st.text_area("ข้อมูลประกอบ/คำให้การลูกค้า (ถ้ามี)", placeholder="เช่น ลูกค้าแจ้งว่าขายของหน้าร้าน คนที่มาด้วยเป็นพี่ชาย...", height=150)

    if uploaded_file and st.button("🚀 เริ่มวิเคราะห์ความเสี่ยงด้วย AI", type="primary", use_container_width=True):
        if GEMINI_API_KEY == "ใส่_API_KEY_ของคุณที่นี่":
            st.error("AQ.Ab8RN6LlskBivIktEyXkIZTplOe3FlyAO4ECgJUvE6Wn7gimHQ")
        else:
            image = Image.open(uploaded_file)
            st.image(image, caption="เอกสารที่อัปโหลด", use_container_width=True)

            prompt = f"""
            คุณคือ Head of Credit Risk & Fraud Intelligence — SRD Motor Finance
            ใช้หลักการห้ามสรุปว่าทุจริตจากสัญญาณเดียว ให้ประเมินภาพรวม:
            1. แยกรายได้จริง (Verified Income) ออกจากเงินหมุน
            2. ตรวจสอบพฤติกรรมเงินเข้า-ออก (Cash Flow Behavior)
            3. ตรวจสอบสัญญาณผิดปกติ เช่น การโอนถี่ช่วงดึก หรือแพตเทิร์นเสี่ยง
            4. สรุปผลความเสี่ยง (Risk Score 0-100) และคำถามสัมภาษณ์ 3 ข้อสำหรับเจ้าหน้าที่

            ข้อมูลทางการเงินของผู้กู้:
            - รวมรายได้: {total_income} บาท
            - ค่างวดรถใหม่: {new_installment} บาท
            - ข้อมูลเพิ่มเติม: {customer_story}
            """

            with st.spinner("AI กำลังวิเคราะห์เอกสารและพฤติกรรม..."):
                try:
                    model = genai.GenerativeModel("gemini-1.5-flash")
                    response = model.generate_content([prompt, image])
                    st.write("---")
                    st.markdown("### 📋 ผลการวิเคราะห์จาก AI")
                    st.markdown(response.text)
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาด: {e}")