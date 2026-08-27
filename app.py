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
        .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
            background-color: #FFFFFF !important;
        }
        [data-testid="stSidebar"] {
            background-color: #F8F9FA !important;
            border-right: 1px solid #E9ECEF !important;
        }
        h1, h2, h3, h4, h5, h6, p, span, label, li, .stMarkdown {
            color: #1A1A1A !important;
        }
        .stCaption, [data-testid="stCaptionContainer"] p {
            color: #495057 !important;
            font-size: 0.88rem !important;
        }
        table {
            width: 100% !important;
            border-collapse: collapse !important;
            margin: 12px 0 !important;
            background-color: #FFFFFF !important;
        }
        th {
            background-color: #F1F3F5 !important;
            color: #212529 !important;
            font-weight: 700 !important;
            border: 1px solid #DEE2E6 !important;
            padding: 10px 14px !important;
        }
        td {
            color: #212529 !important;
            border: 1px solid #DEE2E6 !important;
            padding: 9px 14px !important;
        }
        .alert-pdpa {
            background-color: #FFF3CD !important;
            color: #664D03 !important;
            padding: 12px !important;
            border-radius: 8px !important;
            border-left: 5px solid #FFC107 !important;
            margin: 10px 0 !important;
        }
    </style>
""", unsafe_allow_html=True)

st.title("🏍️ SRD Credit Investigation Engine")
st.caption("ระบบคำนวณค่างวด Flat Rate + ตรวจเอกสารยืนยันตัวตน/พิกัดงาน/PDPA + AI 13 โมดูล — บจก. สิระเดชมอเตอร์เซลล์")

# ฟังก์ชันเชื่อมต่อ Gemini API ผ่าน REST ตรง (รองรับ Key ทุกรูปแบบรวมถึง AQ.)
def call_gemini_rest_api(api_key, model_name, prompt_text, pil_images):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key.strip()}"
    
    parts = [{"text": prompt_text}]
    
    for img in pil_images:
        buffered = io.BytesIO()
        img_converted = img.convert('RGB')
        img_converted.save(buffered, format="JPEG", quality=85)
        img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
        parts.append({
            "inline_data": {
                "mime_type": "image/jpeg",
                "data": img_b64
            }
        })
        
    payload = {
        "contents": [
            {
                "parts": parts
            }
        ]
    }
    
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=90)
    
    if response.status_code != 200:
        err_msg = response.json().get('error', {}).get('message', response.text)
        raise Exception(f"HTTP {response.status_code}: {err_msg}")
        
    res_data = response.json()
    return res_data["candidates"][0]["content"]["parts"][0]["text"]

# ดึง Key จาก Streamlit Secrets (ถ้ามี)
default_api_key = ""
if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
    default_api_key = st.secrets["GEMINI_API_KEY"]

# เมนูด้านข้าง (Sidebar)
with st.sidebar:
    st.header("⚙️ การตั้งค่าระบบ")
    api_key_input = st.text_input(
        "AQ.Ab8RN6J002bqfjJqJDFq-S68ViFRJmP0RWwuJgvgKBj58CO9ag", 
        value=default_api_key,
        type="password", 
        placeholder="AQ.Ab8RN6J002bqfjJqJDFq-S68ViFRJmP0RWwuJgvgKBj58CO9ag",
        help="AQ.Ab8RN6J002bqfjJqJDFq-S68ViFRJmP0RWwuJgvgKBj58CO9ag"
    )

    model_options = ['gemini-2.5-flash', 'gemini-1.5-flash', 'gemini-2.0-flash', 'gemini-1.5-pro']
    selected_model = st.selectbox("🤖 โมเดล AI ที่ใช้งาน", model_options, index=0)

    if api_key_input:
        st.success("✅ พร้อมใช้งาน")
    else:
        st.warning("⚠️ กรุณากรอก API Key ในช่องด้านบน")

# ==========================================
# 2. Rule Engine: ตรวจจับทุจริตจัดตั้ง
# ==========================================
def evaluate_fraud_rules(vehicle_type, down_pct, employment_type, shared_contracts_count, dsr_val, gps_consent):
    rule_score = 0
    flags = []
    high_risk_categories = ["Yamaha - Sport", "Honda - รถใหม่", "PICKUP_4X4", "BIGBIKE_PREMIUM"]
    unstable_jobs = ["ฟรีแลนซ์/รับจ้างทั่วไป", "ว่างงาน/ไม่มีงานประจำ", "FREELANCE", "GENERAL_LABOR", "UNEMPLOYED"]
    
    if (vehicle_type in high_risk_categories or "Sport" in vehicle_type) and down_pct <= 5.0 and employment_type in unstable_jobs:
        rule_score += 40
        flags.append("⚠️ R_MATCH_RISK_01: เสี่ยงดาวน์แลกเงิน (รถสปอร์ต/ตลาด + ดาวน์ ≤5% + อาชีพไม่นิ่ง)")
        
    if shared_contracts_count >= 1:
        rule_score += 50
        flags.append("🚨 R_LINKAGE_02: เครือข่ายนายหน้า/จัดซ้อน (พบความเชื่อมโยงกับสัญญาอื่นใน 90 วัน)")
        
    if (dsr_val > 50.0 or down_pct < 10.0) and not gps_consent:
        rule_score += 20
        flags.append("⚠️ R_HIGH_DSR_NO_TRACKING: DSR > 50% หรือดาวน์ < 10% แต่ยังไม่มียินยอมยืนยันสถานที่/GPS ตาม PDPA")

    if rule_score >= 80:
        rule_verdict = "⛔ AUTO REJECT (เสี่ยงทุจริตจัดตั้งสูงมาก)"
    elif rule_score >= 50:
        rule_verdict = "🟠 MANUAL REVIEW (ต้องส่งฝ่ายสินเชื่อตรวจเชิงลึก)"
    else:
        rule_verdict = "🟢 AUTO PASS (ผ่านเกณฑ์ความเสี่ยงจัดตั้งเบื้องต้น)"
        
    return rule_score, flags, rule_verdict

# ==========================================
# 3. โหลดข้อมูลตารางราคารถ
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
            df = df.rename(columns={'รุ่นรถ': 'รุ่นรถ', 'ราคาจัด': 'ราคาสด', 'ดอกเบี้ย\n(ต่อเดือน)': 'ดอกเบี้ย', 'ดาวน์': 'เงินดาวน์', 'ค่าจด/พรบ.': 'ค่าจด', 'รวมออกรถ': 'รวมออกรถ'})
            df[['รุ่นรถ', 'ราคาสด', 'ดอกเบี้ย']] = df[['รุ่นรถ', 'ราคาสด', 'ดอกเบี้ย']].ffill()
            df = df.dropna(subset=['รุ่นรถ'])
            motorcycle_dict[f"Yamaha - {sheet}"] = df
        except Exception:
            pass

    for sheet, name in [('รถใหม่_Honda', 'Honda - รถใหม่'), ('รถมือสอง_Honda', 'Honda - รถมือสอง')]:
        try:
            df_h = pd.read_excel(file_path, sheet_name=sheet, skiprows=1)
            first_col = 'เลขเครื่อง' if 'เลขเครื่อง' in df_h.columns else 'รุ่นรถ'
            df_h = df_h.rename(columns={first_col: 'รุ่นรถ', 'ราคาจัด': 'ราคาสด', 'ดอกเบี้ย\n(ต่อเดือน)': 'ดอกเบี้ย', 'เงินดาวน์': 'เงินดาวน์', 'ค่าจด/พรบ.': 'ค่าจด', 'รวมออกรถ': 'รวมออกรถ'})
            df_h[['รุ่นรถ', 'ราคาสด', 'ดอกเบี้ย']] = df_h[['รุ่นรถ', 'ราคาสด', 'ดอกเบี้ย']].ffill()
            df_h = df_h.dropna(subset=['รุ่นรถ'])
            motorcycle_dict[name] = df_h
        except Exception:
            pass

    return motorcycle_dict

motorcycle_data = load_all_motorcycle_data()

# ==========================================
# 4. หน้าจอหลัก (2 คอลัมน์)
# ==========================================
col_calc, col_ai = st.columns([1.1, 1.2])

with col_calc:
    st.subheader("🛵 1. ข้อมูลรถและคำนวณค่างวด Flat Rate")
    
    category = "Yamaha - Auto"
    if motorcycle_data:
        category = st.selectbox("เลือกหมวดหมู่รถ", list(motorcycle_data.keys()))
        df_cat = motorcycle_data[category]
        selected_model_name = st.selectbox("เลือกรุ่นรถ", df_cat['รุ่นรถ'].unique().tolist())
        row_preset = df_cat[df_cat['รุ่นรถ'] == selected_model_name].iloc[0]
        
        default_model_name = str(selected_model_name)
        default_cash_price = int(row_preset['ราคาสด']) if pd.notna(row_preset['ราคาสด']) else 60000
        rate_val = row_preset.get('ดอกเบี้ย', 0.015)
        default_interest = float(rate_val * 100) if rate_val < 0.1 else float(rate_val)
        default_reg_fee = int(row_preset['ค่าจด']) if 'ค่าจด' in row_preset and pd.notna(row_preset['ค่าจด']) else 1000
    else:
        default_model_name = "แกรนด์ฟีลาโน่ Edi+SMK"
        default_cash_price = 76200
        default_interest = 1.50
        default_reg_fee = 1000

    c1, c2 = st.columns(2)
    with c1:
        model_name = st.text_input("ชื่อรุ่นรถ", value=default_model_name)
        cash_price = st.number_input("ราคาสดตัวรถ (บาท)", value=int(default_cash_price), step=1000)
        fee_in_loan = st.number_input("ค่า พรบ./ทะเบียน (รวมในยอดจัด)", value=0, step=500)
        down_payment = st.number_input("เงินดาวน์ (บาท)", value=5000, step=500)
    with c2:
        interest_rate_pm = st.number_input("ดอกเบี้ย Flat Rate (%/เดือน)", value=float(default_interest), step=0.05, format="%.2f")
        term_months = st.selectbox("ระยะเวลาผ่อน (งวด)", [12, 18, 24, 30, 36, 42, 48, 60], index=4)
        fee_separate = st.number_input("ค่า พรบ./ทะเบียน (จ่ายแยกวันออกรถ)", value=int(default_reg_fee), step=500)

    # คำนวณ Flat Rate
    net_price = cash_price + fee_in_loan
    down_pct = (down_payment / cash_price) * 100 if cash_price > 0 else 0
    financing_amount = max(0, net_price - down_payment)
    total_interest = financing_amount * (interest_rate_pm / 100.0) * term_months
    total_debt = financing_amount + total_interest
    calc_installment = math.ceil(total_debt / term_months) if term_months > 0 else 0
    
    st.write("---")
    col_inst1, col_inst2 = st.columns(2)
    with col_inst1:
        st.info(f"💡 **ค่างวดคำนวณตามสูตร:** `{calc_installment:,.0f}` บาท/เดือน")
    with col_inst2:
        monthly_installment = st.number_input("✏️ ยอดค่างวดจัดเก็บจริง (แก้ไขได้)", value=int(calc_installment), step=50)

    # ยอดรวมเช่าซื้อทั้งสัญญา
    actual_total_debt = monthly_installment * term_months
    total_hire_purchase = down_payment + fee_separate + actual_total_debt
    total_cash_to_drive = down_payment + fee_separate

    # ตารางสรุปโครงสร้างเช่าซื้อ
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
        applicant_age = st.number_input("อายุ (ปี)", min_value=18, max_value=80, value=28)
        emp_type = st.selectbox("ประเภทอาชีพ", ["พนักงานประจำ/มีสลิป", "ข้าราชการ/รัฐวิสาหกิจ", "เจ้าของกิจการ/ค้าขายหน้าร้าน", "ฟรีแลนซ์/รับจ้างทั่วไป", "ว่างงาน/ไม่มีงานประจำ"])
        salary = st.number_input("ฐานเงินเดือน/รายได้หลัก (บาท)", value=18000, step=500)
    with u2:
        applicant_phone = st.text_input("เบอร์โทรศัพท์ผู้กู้", value="081-xxxxxxx")
        residence_status = st.selectbox("สถานะที่พักอาศัย", ["บ้านตนเอง/ปลอดภาระ", "บ้านตนเอง/ติดผ่อน", "บ้านพักสวัสดิการ", "บ้านญาติ/ครอบครัว", "บ้านเช่า/หอพัก"])
        extra_income = st.number_input("รายได้เสริมที่พิสูจน์ได้ (บาท)", value=3000, step=500)
        existing_debt = st.number_input("หนี้เดิม/โอนออกประจำ (บาท)", value=3000, step=500)

    # คำนวณ DSR
    total_income_applicant = salary + extra_income
    dsr_calc = ((existing_debt + monthly_installment) / total_income_applicant * 100) if total_income_applicant > 0 else 0

    st.write("---")
    st.markdown("🔒 **เงื่อนไขยืนยันสินค้าเช่าซื้อ / ติดตามตำแหน่ง (มาตรฐาน PDPA)**")
    
    if dsr_calc > 50.0 or down_pct < 10.0:
        st.markdown(f"""
        <div class="alert-pdpa">
            ⚠️ <b>เงื่อนไขพิเศษความเสี่ยง:</b> ลูกค้ามี DSR = {dsr_calc:.1f}% (>50%) หรือ เงินดาวน์ = {down_pct:.1f}% (<10%)<br>
            <i>แนะนำให้ทำบันทึก "ยินยอมยืนยันสถานที่และติดตั้งอุปกรณ์ติดตามตำแหน่ง (GPS)" เพื่อลดความเสี่ยงการจัดรถส่งต่อ/ข้ามแดน</i>
        </div>
        """, unsafe_allow_html=True)

    gps_pdpa_consent = st.checkbox(
        "✅ ลูกค้ายินยอมให้ยืนยันสินค้าเช่าซื้อตามเงื่อนไขสินเชื่อ / ยืนยันสถานที่และติดตั้งอุปกรณ์ติดตามตำแหน่ง (GPS) ผ่านช่องทางออนไลน์ ตาม พ.ร.บ. คุ้มครองข้อมูลส่วนบุคคล (PDPA)", 
        value=True if (dsr_calc > 50.0 or down_pct < 10.0) else False
    )

    shared_history = st.number_input("ความเชื่อมโยงสัญญาอื่นใน 90 วัน (เบอร์/ที่อยู่ตรงกัน)", min_value=0, value=0, step=1)
    r_score, r_flags, r_verdict = evaluate_fraud_rules(category, down_pct, emp_type, shared_history, dsr_calc, gps_pdpa_consent)

    # ข้อมูลคู่สมรส
    st.write("---")
    has_spouse = st.checkbox("💍 ข้อมูลคู่สมรส (Spouse)", value=False)
    spouse_summary = "ไม่มีข้อมูลคู่สมรส / โสด"
    if has_spouse:
        st.caption("ข้อมูลคู่สมรสช่วยเพิ่มความน่าเชื่อถือและความสามารถในการผ่อนชำระของครัวเรือน")
        sp1, sp2 = st.columns(2)
        with sp1:
            spouse_name = st.text_input("ชื่อ-นามสกุล คู่สมรส", value="")
            spouse_status = st.selectbox("สถานะสมรส", ["จดทะเบียนสมรส", "อยู่กินกันฉันสามีภริยา (ไม่จดทะเบียน)", "หย่าร้าง / แยกกันอยู่"])
            spouse_job = st.text_input("อาชีพคู่สมรส", value="พนักงานบริษัท")
        with sp2:
            spouse_income = st.number_input("รายได้คู่สมรส (บาท/เดือน)", value=15000, step=1000)
            spouse_debt = st.number_input("ภาระหนี้คู่สมรส (บาท/เดือน)", value=2000, step=500)
            spouse_support = st.radio("ร่วมรับผิดชอบค่างวดหรือไม่", ["ร่วมส่งค่างวด", "รับรู้แต่ไม่ร่วมส่ง", "ไม่รับรู้การซื้อรถ"], horizontal=True)
        spouse_summary = f"คู่สมรส: {spouse_name} ({spouse_status}) | อาชีพ: {spouse_job} | รายได้: {spouse_income:,.0f} บาท | หนี้: {spouse_debt:,.0f} บาท | สถานะการผ่อน: {spouse_support}"

    # ข้อมูลคนค้ำประกัน
    st.write("---")
    has_guarantor = st.checkbox("👥 มีคนค้ำประกัน (Guarantor)", value=True)
    g_text = "ไม่มีคนค้ำประกัน"
    if has_guarantor:
        gc1, gc2 = st.columns(2)
        with gc1:
            g_name = st.text_input("ชื่อ-นามสกุล คนค้ำประกัน", value="สมศรี ใจดี")
            g_rel = st.selectbox("ความสัมพันธ์คนค้ำ", ["บิดา/มารดา (สายเลือดตรง)", "คู่สมรส", "พี่น้องแท้ๆ", "เพื่อนร่วมงาน/นายจ้าง", "คนรู้จักทั่วไป"])
            g_job = st.text_input("อาชีพคนค้ำ", value="พนักงานประจำ / ข้าราชการ")
        with gc2:
            g_phone = st.text_input("เบอร์โทรคนค้ำ", value="089-xxxxxxx")
            g_inc = st.number_input("รายได้สุทธิคนค้ำ (บาท)", value=22000, step=1000)
            g_house = st.selectbox("ที่อยู่อาศัยคนค้ำ", ["อยู่บ้านเดียวกับผู้กู้", "มีบ้านของตนเอง", "บ้านเช่า"])
        g_text = f"คนค้ำ: {g_name} ({g_rel}) | โทร: {g_phone} | อาชีพ: {g_job} | รายได้: {g_inc:,.0f} บาท | ที่อยู่: {g_house}"

    # บุคคลอ้างอิง
    st.write("---")
    st.subheader("📞 3. บุคคลอ้างอิง (References)")
    rf1, rf2 = st.columns(2)
    with rf1:
        ref1_name = st.text_input("บุคคลอ้างอิงคนที่ 1 (ชื่อ-สกุล)", value="สมศักดิ์ ใจดี")
        ref1_rel = st.text_input("ความสัมพันธ์ 1", value="พี่ชาย")
        ref1_tel = st.text_input("เบอร์โทร 1", value="086-xxxxxxx")
    with rf2:
        ref2_name = st.text_input("บุคคลอ้างอิงคนที่ 2 (ชื่อ-สกุล)", value="สมใจ มิตรแท้")
        ref2_rel = st.text_input("ความสัมพันธ์ 2", value="หัวหน้างาน")
        ref2_tel = st.text_input("เบอร์โทร 2", value="082-xxxxxxx")
    ref_summary = f"อ้างอิง 1: {ref1_name} ({ref1_rel} - {ref1_tel}) | อ้างอิง 2: {ref2_name} ({ref2_rel} - {ref2_tel})"

with col_ai:
    st.subheader("📋 4. เช็คลิสต์เอกสารสำคัญ & ตรวจสอบหน้าร้าน")
    
    c_doc1 = st.checkbox("1. 📸 ภาพถ่ายยืนยันตัวตนหน้าร้าน (Identity Selfie คู่บัตร ปชช. ตัวจริง)", value=True)
    c_doc2 = st.checkbox("2. 📑 บัตรประชาชน + สำเนาทะเบียนบ้าน", value=True)
    c_doc3 = st.checkbox("3. 🏦 รายการเดินบัญชีธนาคาร (Statement ย้อนหลัง)", value=True)
    c_doc4 = st.checkbox("4. 📊 หน้าตรวจสอบประวัติเครดิตบูโร (NCB Report)", value=False)
    c_doc5 = st.checkbox("5. 💵 สลิปเงินเดือน / หนังสือรับรองรายได้ / ทะเบียนการค้า", value=True)
    c_doc6 = st.checkbox("6. 📍 รูปถ่ายที่พักอาศัย + หมุด Google Maps / รูปสต็อกสินค้า-แผงค้าจริง", value=True if emp_type in ["ฟรีแลนซ์/รับจ้างทั่วไป", "เจ้าของกิจการ/ค้าขายหน้าร้าน"] else False)

    workplace_location_note = st.text_input("📌 พิกัด Google Maps หรือสถานที่ทำงาน/ที่พักจริง", placeholder="เช่น https://maps.app.goo.gl/... หรือ หน้าร้านตลาดสดเทศบาล ซอย 3")

    attached_docs = []
    missing_docs = []
    for doc_name, is_checked in [
        ("ภาพเซลฟี่คู่บัตรหน้าร้าน (Identity Verification)", c_doc1),
        ("บัตรประชาชน+ทะเบียนบ้าน", c_doc2),
        ("สเตทเม้นธนาคาร", c_doc3),
        ("หน้าตรวจ NCB", c_doc4),
        ("สลิปเงินเดือน/หลักฐานรายได้", c_doc5),
        ("พิกัดที่ทำงาน/รูปสต็อกแผงค้า (Workplace Verification)", c_doc6)
    ]:
        if is_checked:
            attached_docs.append(doc_name)
        else:
            missing_docs.append(doc_name)

    doc_status_text = f"เอกสารที่แนบครบ: {', '.join(attached_docs) if attached_docs else 'ไม่มี'} | เอกสารที่ยังขาด: {', '.join(missing_docs) if missing_docs else 'ไม่มี (ครบสมบูรณ์)'}"
    st.caption(f"📁 **สถานะเอกสาร:** {doc_status_text}")

    st.write("---")
    st.subheader("🔍 5. อัปโหลดภาพเอกสาร & AI วิเคราะห์ 13 โมดูล")
    
    uploaded_files = st.file_uploader(
        "อัปโหลดเอกสารทั้งหมด (เซลฟี่หน้าร้าน, Statement, สลิป, บัตร ปชช., รูปสต็อก/แผงค้า)", 
        type=["png", "jpg", "jpeg"], 
        accept_multiple_files=True
    )
    
    customer_story = st.text_area(
        "บันทึกบริบทหน้าร้าน / พฤติกรรมลูกค้า", 
        placeholder="เช่น ลูกค้ามากับคุณแม่และคู่สมรส เซลฟี่หน้าร้านคู่บัตรเรียบร้อย แจ้งว่าจะนำรถไปใช้วิ่งไปทำงานโรงงาน...", 
        height=80
    )

    if uploaded_files:
        st.caption(f"📁 แนบไฟล์ภาพแล้ว {len(uploaded_files)} ไฟล์")

    if uploaded_files and st.button("🚀 รันระบบวิเคราะห์ความเสี่ยง (AI Engine)", type="primary", use_container_width=True):
        if not api_key_input:
            st.error("⚠️ กรุณากรอก Gemini API Key ในแถบด้านซ้ายก่อนกดวิเคราะห์")
        else:
            try:
                images_to_send = [Image.open(f) for f in uploaded_files]

                full_srd_prompt = f"""
# SRD CREDIT INVESTIGATION ENGINE (FULL 13 MODULES)
## ระบบวิเคราะห์สินเชื่อเชิงพฤติกรรมและตรวจจับการทุจริต — บริษัท สิระเดชมอเตอร์เซลล์ จำกัด

### ROLE & PRINCIPLES
คุณคือ “Head of Credit Risk & Fraud Intelligence — SRD Motor Finance”
- เป้าหมาย: อนุมัติลูกค้าที่มีเจตนาและสามารถผ่อนได้จริง พร้อมดักจับขบวนการทุจริตจัดตั้ง
- หลักการ: ห้ามเชื่อข้อมูลแหล่งเดียว (Cross-Validation ทุกจุด) | ห้ามสรุปว่าทุจริตจากสัญญาณเดียว (ดู Pattern) | วิเคราะห์ Customer Story ความสอดคล้อง

---

[ข้อมูลโครงสร้างสินเชื่อเช่าซื้อ]
- รุ่นรถ: {model_name} (กลุ่ม {category})
- ราคาสด: {cash_price:,.0f} บาท | เงินดาวน์: {down_payment:,.0f} บาท ({down_pct:.1f}%)
- ยอดจัดไฟแนนซ์: {financing_amount:,.0f} บาท | ดอกเบี้ย: {interest_rate_pm:.2f}% ต่อเดือน
- ค่างวดที่เรียกเก็บจริง: {monthly_installment:,.0f} บาท x {term_months} งวด
- ยอดหนี้รวมทั้งสิ้น: {actual_total_debt:,.0f} บาท
- 🏆 ยอดเช่าซื้อรวมทั้งสัญญา (ดาวน์ + ทะเบียน + ค่างวดทุกงวด): {total_hire_purchase:,.0f} บาท
- รวมจ่ายวันออกรถ: {total_cash_to_drive:,.0f} บาท

[ข้อมูลผู้กู้และมาตรการควบคุมความเสี่ยง]
- ผู้กู้: {applicant_name} (อายุ {applicant_age} ปี) | โทร: {applicant_phone} | ที่พัก: {residence_status}
- อาชีพ: {emp_type} | เงินเดือน {salary:,.0f} บาท | เสริม {extra_income:,.0f} บาท | หนี้เดิม {existing_debt:,.0f} บาท | DSR: {dsr_calc:.1f}%
- พิกัด/สถานที่ทำงานจริง: {workplace_location_note if workplace_location_note else 'ไม่ระบุพิกัด'}
- เงื่อนไขติดตามตำแหน่ง (GPS / PDPA Tracking): {'ยินยอมให้ติดตามตำแหน่งตามเงื่อนไขสินเชื่อ (PDPA Compliant)' if gps_pdpa_consent else 'ไม่มียินยอม GPS'}
- ผลประเมิน Rule Engine: Score = {r_score}, Verdict = {r_verdict}, Flags = {r_flags}
- ข้อมูลคู่สมรส: {spouse_summary}
- ข้อมูลคนค้ำประกัน: {g_text}
- บุคคลอ้างอิง: {ref_summary}
- สถานะเช็คลิสต์เอกสาร: {doc_status_text}
- คำให้การและพฤติกรรมหน้าร้าน: {customer_story}

---

### REQUIRED OUTPUT (สรุปรายงานตามโครงสร้าง 10 ข้อนี้)

## 1. CUSTOMER & HOUSEHOLD PROFILE
- สรุปตัวตน อาชีพ รายได้แท้จริงของผู้กู้ คู่สมรส และคนค้ำประกัน

## 2. IDENTITY & WORKPLACE VERIFICATION (MODULE 01, 02, 03)
- ตรวจสอบภาพถ่ายเซลฟี่หน้าร้านคู่บัตรประชาชน (ยืนยันว่าผู้สมัคร = คนในบัตร = ผู้ใช้รถจริง)
- ตรวจสอบความสมเหตุสมผลของพิกัดที่ทำงาน/ภาพสต็อกสินค้า-แผงค้า ({workplace_location_note}) กับอาชีพที่ระบุ

## 3. VERIFIED FACTS vs UNVERIFIED CLAIMS (ตรวจสอบตามเช็คลิสต์)
- ระบุข้อเท็จจริงที่มีเอกสารยืนยัน เทียบกับรายการที่ยังขาดเอกสาร ({', '.join(missing_docs) if missing_docs else 'เอกสารครบ'})

## 4. MONEY FLOW & CASH FLOW REALITY (MODULE 04 & 05)
- สรุป Money In -> Money Out -> Money Remain (ประเมินว่าเงินเพียงพอกับค่างวด {monthly_installment:,.0f} บาท และยอดเช่าซื้อรวม {total_hire_purchase:,.0f} บาท หรือไม่)

## 5. FRAUD, GAMBLING & ASSET RISK CHECK (MODULE 06, 07, 08, 09)
- **Gambling:** ตรวจสอบความถี่ เวลาโอนดึก และ Money Cycling
- **Nominee / Handover / Export Risk:** ประเมินความเสี่ยงดาวน์แลกเงิน หรือการส่งรถข้ามแดน และผลกระทบของการมี/ไม่มีความยินยอม GPS ติดตามรถตาม PDPA
- **Double Financing:** ความผิดปกติของเอกสาร

## 6. GUARANTOR & SPOUSE MITIGATION POWER
- ประเมินพลังการหักล้างจุดอ่อนของผู้กู้โดยคนค้ำและคู่สมรส

## 7. CONTRADICTION TABLE (MODULE 12)
| มิติข้อมูล | แหล่งที่ 1 | แหล่งที่ 2 | ผลเปรียบเทียบ | ระดับความขัดแย้ง |

## 8. RISK SCORING & FINAL DECISION (MODULE 13 - 100 คะแนน)
- Identity (15), Residence (10), Employment (15), Income (15), Cash Flow (15), Credit/NCB (10), Gambling/Distress (10), Nominee (5), Double Financing (5)
- หักลบความเสี่ยงด้วย Guarantor/Spouse Deduction และมาตรการ GPS Tracking
- **ผลการตัดสิน:** 🟢 PASS (0-20) / 🟡 PASS WITH CONTROL (21-40) / 🟠 CONDITIONAL (41-60) / 🔴 HIGH RISK (61-75) / ⛔ REJECT (76-100)

## 9. 30-SECOND SOFT INTERVIEW (คำถามโทนบริการ ไม่สอบสวน)
- คำถามผู้ซื้อ 2 ข้อ (ถามเส้นทางใช้งานจริง / รอบตัดบิลที่สะดวกชำระ)
- คำถามคนค้ำประกัน 1 ข้อ (ถามความผูกพันเชิงบวก)

## 10. SUMMARY RECOMMENDATION FOR SALES
- สรุปแนวทางปิดการขายอย่างปลอดภัยสำหรับเซลส์
"""

                with st.spinner(f"AI ({selected_model}) กำลังประมวลผล 13 โมดูล..."):
                    ai_response_text = call_gemini_rest_api(api_key_input, selected_model, full_srd_prompt, images_to_send)
                    st.session_state["last_ai_report"] = ai_response_text

            except Exception as e:
                st.error(f"เกิดข้อผิดพลาดในการประมวลผล: {e}")

    if "last_ai_report" in st.session_state:
        st.write("---")
        st.markdown("### 📋 รายงานผลการประเมินสินเชื่อเชิงลึก (SRD Engine Report)")
        st.markdown(st.session_state["last_ai_report"])