import streamlit as st
from PIL import Image
import pandas as pd
import math
import os
import io
import base64
import requests
import json
from datetime import datetime

# ==========================================
# 1. ตั้งค่าหน้าตาเว็บแอป และ Theme สีขาว
# ==========================================
st.set_page_config(page_title="SRD Credit Investigation Engine", layout="wide", page_icon="🏍️")

st.markdown("""
    <style>
        .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] { background-color: #FFFFFF !important; }
        [data-testid="stSidebar"] { background-color: #F8F9FA !important; border-right: 1px solid #E9ECEF !important; }
        h1, h2, h3, h4, h5, h6, p, span, label, li, .stMarkdown { color: #1A1A1A !important; }
        .stCaption, [data-testid="stCaptionContainer"] p { color: #495057 !important; font-size: 0.88rem !important; }
        table { width: 100% !important; border-collapse: collapse !important; margin: 12px 0 !important; background-color: #FFFFFF !important; }
        th { background-color: #F1F3F5 !important; color: #212529 !important; font-weight: 700 !important; border: 1px solid #DEE2E6 !important; padding: 10px 14px !important; }
        td { color: #212529 !important; border: 1px solid #DEE2E6 !important; padding: 9px 14px !important; }
        .alert-pdpa { background-color: #FFF3CD !important; color: #664D03 !important; padding: 12px !important; border-radius: 8px !important; border-left: 5px solid #FFC107 !important; margin: 10px 0 !important; }
    </style>
""", unsafe_allow_html=True)

if "history_log" not in st.session_state:
    st.session_state["history_log"] = []

st.title("🏍️ SRD Credit Investigation Engine")
st.caption("ระบบคำนวณค่างวด Flat Rate + ตรวจเอกสารยืนยันตัวตน/พิกัดงาน/PDPA + AI 13 โมดูล — บจก. สิระเดชมอเตอร์เซลล์")

# ==========================================
# 2. ฟังก์ชันยิง Google Gemini API โดยตรง
# ==========================================
def call_gemini_api(api_key, model_name, prompt_text, pil_images):
    clean_key = api_key.strip()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={clean_key}"
    
    parts = [{"text": prompt_text}]
    for img in pil_images:
        buf = io.BytesIO()
        img.convert('RGB').save(buf, format="JPEG", quality=85)
        parts.append({
            "inline_data": {
                "mime_type": "image/jpeg",
                "data": base64.b64encode(buf.getvalue()).decode("utf-8")
            }
        })
        
    payload = {"contents": [{"parts": parts}]}
    res = requests.post(url, headers={"Content-Type": "application/json"}, json=payload, timeout=120)
    
    if res.status_code != 200:
        err_msg = res.json().get('error', {}).get('message', res.text)
        raise Exception(f"HTTP {res.status_code}: {err_msg}")
        
    return res.json()["candidates"][0]["content"]["parts"][0]["text"]

# ดึง Key จาก Streamlit Secrets อัตโนมัติ (ถ้ามี)
default_api_key = ""
if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
    default_api_key = st.secrets["GEMINI_API_KEY"]

# เมนูด้านข้าง (Sidebar)
with st.sidebar:
    st.header("⚙️ การตั้งค่าระบบ")
    api_key_input = st.text_input(
        "Google Gemini API Key", 
        value=default_api_key, 
        type="password", 
        placeholder="AIzaSy...",
        help="รับรหัสฟรีจาก aistudio.google.com"
    )
    selected_model = st.selectbox("🤖 โมเดล AI พร้อมใช้งาน", ["gemini-2.0-flash", "gemini-1.5-flash"], index=0)

    if api_key_input:
        st.success(f"✅ พร้อมใช้งาน: {selected_model}")
    else:
        st.warning("⚠️ กรุณากรอก Gemini API Key (ขึ้นต้นด้วย AIzaSy...)")

    st.write("---")
    st.subheader("💾 ฐานข้อมูลการประเมิน (Data Log)")
    log_count = len(st.session_state["history_log"])
    st.caption(f"บันทึกแล้วทั้งหมด: {log_count} รายการ")

    if log_count > 0:
        df_log = pd.DataFrame(st.session_state["history_log"])
        st.download_button(
            label="📥 ดาวน์โหลดประวัติ (CSV)",
            data=df_log.to_csv(index=False).encode('utf-8-sig'),
            file_name=f"SRD_Evaluations_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True
        )

# ==========================================
# 3. Rule Engine ตรวจจับทุจริตจัดตั้ง
# ==========================================
def evaluate_fraud_rules(vehicle_type, down_pct, employment_type, shared_contracts_count, dsr_val, gps_consent):
    rule_score = 0
    flags = []
    if ("Sport" in vehicle_type or "รถใหม่" in vehicle_type) and down_pct <= 5.0 and employment_type in ["ฟรีแลนซ์/รับจ้างทั่วไป", "ว่างงาน/ไม่มีงานประจำ"]:
        rule_score += 40
        flags.append("⚠️ เสี่ยงดาวน์แลกเงิน (รถสปอร์ต/ตลาด + ดาวน์ ≤5% + อาชีพไม่นิ่ง)")
    if shared_contracts_count >= 1:
        rule_score += 50
        flags.append("🚨 พบความเชื่อมโยงกับสัญญาอื่นใน 90 วัน")
    if (dsr_val > 50.0 or down_pct < 10.0) and not gps_consent:
        rule_score += 20
        flags.append("⚠️ DSR > 50% หรือดาวน์ < 10% แต่ยังไม่มียินยอม GPS")

    verdict = "⛔ AUTO REJECT" if rule_score >= 80 else ("🟠 MANUAL REVIEW" if rule_score >= 50 else "🟢 AUTO PASS")
    return rule_score, flags, verdict

# ==========================================
# 4. โหลดข้อมูลตารางราคารถ
# ==========================================
@st.cache_data
def load_all_motorcycle_data():
    file_path = 'Yamaha_+รวมขายทุกตัว 25-8-69 Dynamic_Formulas_Categories.xlsx'
    if not os.path.exists(file_path):
        return {}
    motorcycle_dict = {}
    for sheet in ['Auto', 'Moped', 'Sport']:
        try:
            df = pd.read_excel(file_path, sheet_name=sheet, skiprows=1)
            df = df.rename(columns={'รุ่นรถ': 'รุ่นรถ', 'ราคาจัด': 'ราคาสด', 'ดอกเบี้ย\n(ต่อเดือน)': 'ดอกเบี้ย', 'ดาวน์': 'เงินดาวน์', 'ค่าจด/พรบ.': 'ค่าจด'})
            df[['รุ่นรถ', 'ราคาสด', 'ดอกเบี้ย']] = df[['รุ่นรถ', 'ราคาสด', 'ดอกเบี้ย']].ffill()
            motorcycle_dict[f"Yamaha - {sheet}"] = df.dropna(subset=['รุ่นรถ'])
        except Exception:
            pass
    for sheet, name in [('รถใหม่_Honda', 'Honda - รถใหม่'), ('รถมือสอง_Honda', 'Honda - รถมือสอง')]:
        try:
            df_h = pd.read_excel(file_path, sheet_name=sheet, skiprows=1)
            f_col = 'เลขเครื่อง' if 'เลขเครื่อง' in df_h.columns else 'รุ่นรถ'
            df_h = df_h.rename(columns={f_col: 'รุ่นรถ', 'ราคาจัด': 'ราคาสด', 'ดอกเบี้ย\n(ต่อเดือน)': 'ดอกเบี้ย', 'เงินดาวน์': 'เงินดาวน์', 'ค่าจด/พรบ.': 'ค่าจด'})
            df_h[['รุ่นรถ', 'ราคาสด', 'ดอกเบี้ย']] = df_h[['รุ่นรถ', 'ราคาสด', 'ดอกเบี้ย']].ffill()
            motorcycle_dict[name] = df_h.dropna(subset=['รุ่นรถ'])
        except Exception:
            pass
    return motorcycle_dict

motorcycle_data = load_all_motorcycle_data()

# ==========================================
# 5. ส่วนแสดงผลหลัก 2 คอลัมน์
# ==========================================
col_calc, col_ai = st.columns([1.1, 1.2])

with col_calc:
    st.subheader("🛵 1. ข้อมูลรถและคำนวณค่างวด Flat Rate")
    category = "Honda - รถใหม่" if "Honda - รถใหม่" in motorcycle_data else ("Yamaha - Auto" if motorcycle_data else "ทั่วไป")
    if motorcycle_data:
        category = st.selectbox("เลือกหมวดหมู่รถ", list(motorcycle_data.keys()))
        df_cat = motorcycle_data[category]
        selected_model_name = st.selectbox("เลือกรุ่นรถ", df_cat['รุ่นรถ'].unique().tolist())
        row_preset = df_cat[df_cat['รุ่นรถ'] == selected_model_name].iloc[0]
        def_model = str(selected_model_name)
        def_cash = int(row_preset['ราคาสด']) if pd.notna(row_preset['ราคาสด']) else 85500
        rate_val = row_preset.get('ดอกเบี้ย', 0.017)
        def_interest = float(rate_val * 100) if rate_val < 0.1 else float(rate_val)
        def_reg = int(row_preset['ค่าจด']) if 'ค่าจด' in row_preset and pd.notna(row_preset['ค่าจด']) else 1000
    else:
        def_model = "GIORNO+ CBS 2 คัน ขาว-ดำ เทา-น้ำตาล"
        def_cash = 85500
        def_interest = 1.70
        def_reg = 1000

    c1, c2 = st.columns(2)
    with c1:
        model_name = st.text_input("ชื่อรุ่นรถ", value=def_model)
        # แก้ไขจุด Type Error: กำหนดค่า int และ step แบบ int ล้วน
        cash_price = st.number_input("ราคาสดตัวรถ (บาท)", value=int(def_cash), min_value=0, step=100)
        fee_in_loan = st.number_input("ค่า พรบ./ทะเบียน (รวมในยอดจัด)", value=0, min_value=0, step=500)
        down_payment = st.number_input("เงินดาวน์ (บาท)", value=5000, min_value=0, step=500)
    with c2:
        # ช่องนี้เป็น float ล้วน
        interest_rate_pm = st.number_input("ดอกเบี้ย Flat Rate (%/เดือน)", value=float(def_interest), min_value=0.0, step=0.05, format="%.2f")
        term_months = st.selectbox("ระยะเวลาผ่อน (งวด)", [12, 18, 24, 30, 36, 42, 48, 60], index=0)
        fee_separate = st.number_input("ค่า พรบ./ทะเบียน (จ่ายแยกวันออกรถ)", value=int(def_reg), min_value=0, step=500)

    # คำนวณค่างวด Flat Rate
    net_price = cash_price + fee_in_loan
    down_pct = (down_payment / cash_price) * 100 if cash_price > 0 else 0
    financing_amount = max(0, net_price - down_payment)
    total_interest = financing_amount * (interest_rate_pm / 100.0) * term_months
    total_debt = financing_amount + total_interest
    calc_installment = math.ceil(total_debt / term_months) if term_months > 0 else 0
    
    st.write("---")
    monthly_installment = st.number_input("✏️ ยอดค่างวดจัดเก็บจริง (บาท/เดือน)", value=int(calc_installment), min_value=0, step=50)
    actual_total_debt = monthly_installment * term_months
    total_hire_purchase = down_payment + fee_separate + actual_total_debt
    total_cash_to_drive = down_payment + fee_separate

    st.markdown(f"""
    | โครงสร้างราคาและสินเชื่อเช่าซื้อ | จำนวนเงิน (บาท) |
    | :--- | :--- |
    | **1. รวมราคารถสุทธิ (Net Price)** | `{net_price:,.0f}` บาท |
    | **2. ยอดจัดไฟแนนซ์ (Financing Amount)** | `{financing_amount:,.0f}` บาท *(ดาวน์ {down_pct:.1f}%)* |
    | **3. ดอกเบี้ยรวม ({interest_rate_pm:.2f}% x {term_months} งวด)** | `{total_interest:,.0f}` บาท |
    | **4. ยอดหนี้รวมทั้งสิ้น (Total Debt)** | `{actual_total_debt:,.0f}` บาท |
    | 🏍️ **ค่างวดที่เรียกเก็บต่อเดือน** | **`{monthly_installment:,.0f}` บาท / เดือน** |
    | 🔑 **รวมจ่ายวันออกรถ (เงินดาวน์ + ทะเบียน)** | **`{total_cash_to_drive:,.0f}` บาท** |
    | 🏆 **ยอดเช่าซื้อรวมทั้งสัญญา (Total Hire Purchase)** | **`{total_hire_purchase:,.0f}` บาท** |
    """)

    st.write("---")
    st.subheader("👤 2. ข้อมูลผู้กู้ (Applicant)")
    u1, u2 = st.columns(2)
    with u1:
        applicant_name = st.text_input("ชื่อ-นามสกุล ผู้กู้", value="สมชาย ใจดี")
        applicant_age = st.number_input("อายุ (ปี)", min_value=18, max_value=80, value=28, step=1)
        emp_type = st.selectbox("ประเภทอาชีพ", ["พนักงานประจำ/มีสลิป", "ข้าราชการ/รัฐวิสาหกิจ", "เจ้าของกิจการ/ค้าขายหน้าร้าน", "ฟรีแลนซ์/รับจ้างทั่วไป", "ว่างงาน/ไม่มีงานประจำ"])
        salary = st.number_input("ฐานเงินเดือน/รายได้หลัก (บาท)", value=18000, min_value=0, step=500)
    with u2:
        applicant_phone = st.text_input("เบอร์โทรศัพท์ผู้กู้", value="081-xxxxxxx")
        residence_status = st.selectbox("สถานะที่พักอาศัย", ["บ้านตนเอง/ปลอดภาระ", "บ้านตนเอง/ติดผ่อน", "บ้านพักสวัสดิการ", "บ้านญาติ/ครอบครัว", "บ้านเช่า/หอพัก"])
        extra_income = st.number_input("รายได้เสริมที่พิสูจน์ได้ (บาท)", value=3000, min_value=0, step=500)
        existing_debt = st.number_input("หนี้เดิม/โอนออกประจำ (บาท)", value=3000, min_value=0, step=500)

    total_income_applicant = salary + extra_income
    dsr_calc = ((existing_debt + monthly_installment) / total_income_applicant * 100) if total_income_applicant > 0 else 0

    st.write("---")
    if dsr_calc > 50.0 or down_pct < 10.0:
        st.markdown(f"""<div class="alert-pdpa">⚠️ <b>เงื่อนไขความเสี่ยง:</b> DSR = {dsr_calc:.1f}% หรือ ดาวน์ = {down_pct:.1f}% แนะนำให้ยืนยอม GPS ตาม PDPA</div>""", unsafe_allow_html=True)

    gps_pdpa_consent = st.checkbox("✅ ลูกค้ายินยอมเงื่อนไขสินเชื่อ / ตรวจสอบพิกัด GPS ตาม พ.ร.บ. คุ้มครองข้อมูลส่วนบุคคล (PDPA)", value=True if (dsr_calc > 50.0 or down_pct < 10.0) else False)
    shared_history = st.number_input("ความเชื่อมโยงสัญญาอื่นใน 90 วัน (เบอร์/ที่อยู่ตรงกัน)", min_value=0, value=0, step=1)
    r_score, r_flags, r_verdict = evaluate_fraud_rules(category, down_pct, emp_type, shared_history, dsr_calc, gps_pdpa_consent)

    # คู่สมรส
    st.write("---")
    has_spouse = st.checkbox("💍 ข้อมูลคู่สมรส (Spouse)", value=False)
    spouse_summary = "ไม่มีข้อมูลคู่สมรส / โสด"
    if has_spouse:
        sp1, sp2 = st.columns(2)
        with sp1:
            spouse_name = st.text_input("ชื่อ-นามสกุล คู่สมรส", value="")
            spouse_status = st.selectbox("สถานะสมรส", ["จดทะเบียนสมรส", "อยู่กินกันฉันสามีภริยา (ไม่จดทะเบียน)", "หย่าร้าง / แยกกันอยู่"])
            spouse_job = st.text_input("อาชีพคู่สมรส", value="พนักงานบริษัท")
        with sp2:
            spouse_income = st.number_input("รายได้คู่สมรส (บาท/เดือน)", value=15000, min_value=0, step=1000)
            spouse_debt = st.number_input("ภาระหนี้คู่สมรส (บาท/เดือน)", value=2000, min_value=0, step=500)
            spouse_support = st.radio("ร่วมรับผิดชอบค่างวดหรือไม่", ["ร่วมส่งค่างวด", "รับรู้แต่ไม่ร่วมส่ง", "ไม่รับรู้การซื้อรถ"], horizontal=True)
        spouse_summary = f"คู่สมรส: {spouse_name} ({spouse_status}) | อาชีพ: {spouse_job} | รายได้: {spouse_income:,.0f} | หนี้: {spouse_debt:,.0f} | การผ่อน: {spouse_support}"

    # คนค้ำ
    has_guarantor = st.checkbox("👥 มีคนค้ำประกัน (Guarantor)", value=True)
    g_text = "ไม่มีคนค้ำประกัน"
    if has_guarantor:
        gc1, gc2 = st.columns(2)
        with gc1:
            g_name = st.text_input("ชื่อ-นามสกุล คนค้ำ", value="สมศรี ใจดี")
            g_rel = st.selectbox("ความสัมพันธ์", ["บิดา/มารดา", "คู่สมรส", "พี่น้องแท้ๆ", "เพื่อนร่วมงาน/นายจ้าง", "คนรู้จัก"])
            g_job = st.text_input("อาชีพคนค้ำ", value="พนักงานประจำ")
        with gc2:
            g_phone = st.text_input("เบอร์คนค้ำ", value="089-xxxxxxx")
            g_inc = st.number_input("รายได้คนค้ำ (บาท)", value=22000, min_value=0, step=1000)
            g_house = st.selectbox("ที่อยู่คนค้ำ", ["บ้านเดียวกับผู้กู้", "มีบ้านตนเอง", "บ้านเช่า"])
        g_text = f"คนค้ำ: {g_name} ({g_rel}) | โทร: {g_phone} | อาชีพ: {g_job} | รายได้: {g_inc:,.0f} | ที่อยู่: {g_house}"

with col_ai:
    st.subheader("📋 3. เอกสารยืนยันตัวตน & ตรวจสอบหน้าร้าน")
    c_doc1 = st.checkbox("1. 📸 เซลฟี่หน้าร้านคู่บัตร ปชช. ตัวจริง", value=True)
    c_doc2 = st.checkbox("2. 📑 บัตรประชาชน + สำเนาทะเบียนบ้าน", value=True)
    c_doc3 = st.checkbox("3. 🏦 รายการเดินบัญชีธนาคาร (Statement)", value=True)
    c_doc4 = st.checkbox("4. 💵 สลิปเงินเดือน / ทะเบียนการค้า", value=True)
    c_doc5 = st.checkbox("5. 📍 รูปแผงค้า/สต็อกสินค้า/ที่ทำงานจริง", value=True if emp_type in ["ฟรีแลนซ์/รับจ้างทั่วไป", "เจ้าของกิจการ/ค้าขายหน้าร้าน"] else False)

    workplace_location_note = st.text_input("📌 พิกัด Google Maps หรือสถานที่ทำงาน/ที่พักจริง", placeholder="เช่น https://maps.app.goo.gl/...")

    st.write("---")
    st.subheader("🔍 4. อัปโหลดภาพเอกสาร & AI วิเคราะห์ 13 โมดูล")
    uploaded_files = st.file_uploader("อัปโหลดภาพเอกสารทั้งหมด", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
    customer_story = st.text_area("บันทึกบริบทหน้าร้าน / พฤติกรรมลูกค้า", placeholder="เช่น ลูกค้ามากับครอบครัว ยืนยันตัวตนเรียบร้อย...", height=70)

    if uploaded_files and st.button("🚀 รันระบบวิเคราะห์ความเสี่ยง (AI Engine)", type="primary", use_container_width=True):
        if not api_key_input:
            st.error("⚠️ กรุณากรอก Google Gemini API Key ในแถบด้านซ้ายก่อนกดวิเคราะห์")
        else:
            try:
                images_to_send = [Image.open(f) for f in uploaded_files]

                full_srd_prompt = f"""
# SRD CREDIT INVESTIGATION ENGINE (FULL 13 MODULES)
ระบบวิเคราะห์สินเชื่อเชิงพฤติกรรมและตรวจจับการทุจริต — บจก. สิระเดชมอเตอร์เซลล์

[ข้อมูลสินเชื่อ]
- รุ่นรถ: {model_name} ({category}) | ราคาสด: {cash_price:,.0f} | เงินดาวน์: {down_payment:,.0f} ({down_pct:.1f}%)
- ยอดจัด: {financing_amount:,.0f} | ดอกเบี้ย: {interest_rate_pm:.2f}%/เดือน | ค่างวด: {monthly_installment:,.0f} x {term_months} งวด
- ยอดหนี้รวม: {actual_total_debt:,.0f} | ยอดเช่าซื้อรวมทั้งสัญญา: {total_hire_purchase:,.0f} | รวมจ่ายวันออกรถ: {total_cash_to_drive:,.0f}

[ข้อมูลผู้สมัคร]
- ผู้กู้: {applicant_name} ({applicant_age} ปี) โทร: {applicant_phone} ที่พัก: {residence_status}
- อาชีพ: {emp_type} | เงินเดือน {salary:,.0f} | รายได้เสริม {extra_income:,.0f} | หนี้เดิม {existing_debt:,.0f} | DSR: {dsr_calc:.1f}%
- พิกัดทำงาน: {workplace_location_note} | ยินยอม GPS (PDPA): {gps_pdpa_consent}
- Rule Engine: {r_score} คะแนน | ผลประเมิน: {r_verdict}
- คู่สมรส: {spouse_summary} | คนค้ำ: {g_text}
- บริบทหน้าร้าน: {customer_story}

ออกรายงานผล 10 หัวข้อตามมาตรฐาน SRD Finance:
1. CUSTOMER PROFILE
2. IDENTITY & WORKPLACE VERIFICATION (ตรวจสอบภาพถ่ายเซลฟี่หน้าร้านคู่บัตร และพิกัดงานจริง)
3. VERIFIED FACTS vs UNVERIFIED CLAIMS
4. MONEY FLOW REALITY (วิเคราะห์กระแสเงินสดเทียบยอดเช่าซื้อ)
5. FRAUD & ASSET RISK CHECK (ตรวจสเตทเม้นหาการพนัน/โอนดึก/เสี่ยงจัดซ้อน/ส่งออกข้ามแดน)
6. GUARANTOR & SPOUSE POWER
7. CONTRADICTION TABLE (ตารางเปรียบเทียบความขัดแย้งของข้อมูล)
8. RISK SCORING (100 คะแนน) พร้อมผลการตัดสิน (PASS / CONDITIONAL / REJECT)
9. 30-SECOND SOFT INTERVIEW (คำถามสัมภาษณ์โทนบริการสำหรับผู้กู้และคนค้ำ)
10. SALES RECOMMENDATION (แนวทางปิดการขายอย่างปลอดภัย)
"""
                with st.spinner(f"AI ({selected_model}) กำลังประมวลผล 13 โมดูล..."):
                    ai_report = call_gemini_api(api_key_input, selected_model, full_srd_prompt, images_to_send)
                    st.session_state["last_ai_report"] = ai_report
                    
                    st.session_state["history_log"].append({
                        "วันที่-เวลา": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "ชื่อผู้กู้": applicant_name,
                        "เบอร์โทร": applicant_phone,
                        "รุ่นรถ": model_name,
                        "ราคาสด": cash_price,
                        "เงินดาวน์": down_payment,
                        "ค่างวด": monthly_installment,
                        "จำนวนงวด": term_months,
                        "DSR (%)": round(dsr_calc, 1),
                        "ผล Rule Engine": r_verdict
                    })
                    st.rerun()

            except Exception as e:
                st.error(f"เกิดข้อผิดพลาดในการประมวลผล: {e}")

    if "last_ai_report" in st.session_state:
        st.write("---")
        st.markdown("### 📋 รายงานผลการประเมินสินเชื่อเชิงลึก (SRD Engine Report)")
        st.markdown(st.session_state["last_ai_report"])