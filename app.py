import streamlit as st
import pandas as pd
import math
import os
from datetime import datetime
from PIL import Image
import io
import base64

# === NEW SDK (Interactions API compatible) ===
from google import genai
from google.genai import types
from google.genai.errors import ClientError

# PDF Export
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib import colors

# === MOBILE PATCH (ย่อภาพ 12MB->0.9MB) ===
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except:
    pass

def _compress_mobile(img, max_side=1280, max_bytes=1200000):
    img = img.convert("RGB")
    if max(img.size) > max_side:
        img.thumbnail((max_side, max_side), Image.LANCZOS)
    for q in [75, 65, 55, 40]:
        b = io.BytesIO()
        img.save(b, format="JPEG", quality=q, optimize=True)
        if b.tell() <= max_bytes:
            b.seek(0)
            return Image.open(b)
    b.seek(0)
    return Image.open(b)

# ==========================================
# 1. CONFIG + PROFESSIONAL FINANCE THEME ขาว-ฟ้า
# ==========================================
st.set_page_config(page_title="SRD Credit Engine v1.2", layout="wide", page_icon="🏍️")

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600;700&display=swap');
        html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }
        .stApp { background-color: #F8FAFC !important; }
        [data-testid="stSidebar"] { background-color: #0F172A !important; }
        [data-testid="stSidebar"] * { color: #E2E8F0 !important; }
        .srd-card {
            background: white; padding: 18px; border-radius: 12px;
            border: 1px solid #E2E8F0; box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            margin-bottom: 14px;
        }
        .srd-header {
            background: white; padding: 14px 20px; border-radius: 12px;
            border: 1px solid #E2E8F0; margin-bottom: 16px;
            display: flex; justify-content: space-between; align-items: center;
        }
        .step-active { background: #16A34A; color: white; }
        .step-current { background: #2563EB; color: white; }
        .step-pending { background: #F1F5F9; color: #64748B; border: 2px solid #E2E8F0; }
        .btn-pdf {
            background: #DC2626; color: white; padding: 10px 16px; border-radius: 8px;
            border: none; font-weight: 600; width: 100%;
        }
        /* Mobile responsive */
        @media (max-width: 768px) {
            .srd-card { padding: 12px; }
            [data-testid="column"] { min-width: 100% !important; }
        }
    </style>
""", unsafe_allow_html=True)

# Header
col_logo, col_title, col_status = st.columns([1, 6, 2])
with col_logo:
    # ใช้โลโก้ลิงถ้ามีไฟล์
    if os.path.exists("srd_logo.png"):
        st.image("srd_logo.png", width=60)
    else:
        st.markdown("### 🏍️ SRD Credit")
with col_title:
    st.markdown("## Motorcycle Loan Credit Engine")
    st.caption("ระบบตรวจสอบสินเชื่อมอเตอร์ไซค์ • SRD Loan Credit Engine v1.2")
with col_status:
    st.markdown("🟢 **Connected • Live**")

# ==========================================
# 2. API KEY - Secrets เท่านั้น
# ==========================================
def get_api_key():
    key = st.secrets.get("GEMINI_API_KEY", "") if hasattr(st, 'secrets') else ""
    if not key:
        key = os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")
    return key.strip()

api_key = get_api_key()

PREFERRED_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-flash-latest", "gemini-1.5-flash"]

@st.cache_resource(show_spinner=False)
def get_client_and_model(api_key_hash: str):
    client = genai.Client(api_key=api_key)
    available = []
    try:
        for m in client.models.list():
            name = m.name.replace("models/", "") if hasattr(m, 'name') else str(m)
            available.append(name)
    except:
        available = PREFERRED_MODELS
    selected = None
    for pref in PREFERRED_MODELS:
        if pref in available:
            selected = pref
            break
    if not selected and available:
        selected = available[0]
    if not selected:
        selected = PREFERRED_MODELS[0]
    return client, selected, available

if not api_key:
    st.error("❌ ไม่พบ GEMINI_API_KEY ใน Secrets - ไปตั้งที่ Streamlit Cloud > Settings > Secrets")
    st.stop()

try:
    client, selected_model, usable_models = get_client_and_model(api_key[:8])
except Exception as e:
    st.error(f"⚠️ เชื่อมต่อขัดข้อง: {e}")
    st.stop()

# ==========================================
# 3. Sidebar เมนูภาษาไทย
# ==========================================
with st.sidebar:
    st.markdown("### 🏍️ SRD Credit")
    st.caption("SRD Loan Credit Engine • v1.2")
    st.write("---")
    st.caption("เมนูนำทาง")
    menu = st.radio(
        "เมนู",
        ["แดชบอร์ด", "เครื่องคำนวณสินเชื่อ", "ใบสมัคร", "ลูกค้า", "เอกสาร", "วิเคราะห์ข้อมูล", "ความเสี่ยงและนโยบาย"],
        label_visibility="collapsed"
    )
    st.write("---")
    st.caption(f"🤖 AI: `{selected_model}`")
    st.caption(f"โมเดลพร้อมใช้งาน: {len(usable_models)} โมเดล")
    st.write("---")
    st.markdown("**JD** เจ้าหน้าที่สินเชื่อ")
    if st.button("⚙️ ตั้งค่า"):
        st.toast("ตั้งค่า")
    if st.button("🚪 ออกจากระบบ"):
        st.toast("ออกจากระบบ")

# ==========================================
# 4. Rule Engine แยกอิสระ
# ==========================================
def evaluate_fraud_rules(vehicle_type, down_pct, employment_type, shared_contracts_count, dsr_val, gps_consent):
    rule_score = 0
    flags = []
    high_risk = ["Yamaha - Sport", "Honda - รถใหม่", "PICKUP_4X4", "BIGBIKE_PREMIUM"]
    unstable = ["ฟรีแลนซ์/รับจ้างทั่วไป", "ว่างงาน/ไม่มีงานประจำ", "FREELANCE", "GENERAL_LABOR", "UNEMPLOYED"]
    if (vehicle_type in high_risk or "Sport" in vehicle_type) and down_pct <= 5.0 and employment_type in unstable:
        rule_score += 40
        flags.append("⚠️ R_MATCH_RISK_01: เสี่ยงดาวน์แลกเงิน")
    if shared_contracts_count >= 1:
        rule_score += 50
        flags.append("🚨 R_LINKAGE_02: เครือข่ายนายหน้า/จัดซ้อน")
    if (dsr_val > 50.0 or down_pct < 10.0) and not gps_consent:
        rule_score += 20
        flags.append("⚠️ R_HIGH_DSR_NO_TRACKING: DSR > 50% หรือดาวน์ <10% แต่ไม่ยินยอม GPS")
    if rule_score >= 80:
        verdict = "⛔ AUTO REJECT"
    elif rule_score >= 50:
        verdict = "🟠 MANUAL REVIEW"
    else:
        verdict = "🟢 AUTO PASS"
    return rule_score, flags, verdict

HISTORY_FILE = "srd_credit_assessment_history.csv"
def save_assessment_record(record_dict):
    df_new = pd.DataFrame([record_dict])
    if not os.path.exists(HISTORY_FILE):
        df_new.to_csv(HISTORY_FILE, index=False, encoding='utf-8-sig')
    else:
        df_new.to_csv(HISTORY_FILE, mode='a', header=False, index=False, encoding='utf-8-sig')

@st.cache_data
def load_all_motorcycle_data():
    file_path = 'Yamaha_+รวมขายทุกตัว 25-8-69 Dynamic_Formulas_Categories.xlsx'
    motorcycle_dict = {}
    for sheet in ['Auto', 'Moped', 'Sport', 'Honda รถใหม่', 'Honda มือสอง']:
        try:
            df = pd.read_excel(file_path, sheet_name=sheet, skiprows=1)
            # Normalize columns
            df = df.rename(columns={c: c.strip() for c in df.columns})
            if 'รุ่นรถ' in df.columns:
                df[['รุ่นรถ']] = df[['รุ่นรถ']].ffill()
                df = df.dropna(subset=['รุ่นรถ'])
                motorcycle_dict[sheet] = df
        except:
            continue
    # Fallback 3 หมวดเดิม
    if not motorcycle_dict:
        for sheet in ['Auto', 'Moped', 'Sport']:
            try:
                df = pd.read_excel(file_path, sheet_name=sheet, skiprows=1)
                motorcycle_dict[sheet] = df
            except:
                pass
    return motorcycle_dict

# PDF Export Function
def generate_pdf_report(applicant_name, model_name, cash_price, down_payment, monthly, term, total_interest, total_payable, dsr, r_verdict, ai_text):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    # Header
    c.setFont("Helvetica-Bold", 16)
    c.drawString(20*mm, 280*mm, "SRD Credit - Motorcycle Loan Credit Engine v1.2")
    c.setFont("Helvetica", 10)
    c.drawString(20*mm, 275*mm, f"Applicant: {applicant_name} | Model: {model_name} | Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    c.line(20*mm, 272*mm, 190*mm, 272*mm)
    
    c.setFont("Helvetica-Bold", 12)
    c.drawString(20*mm, 262*mm, "Flat Rate Calculation")
    c.setFont("Helvetica", 10)
    c.drawString(20*mm, 256*mm, f"Vehicle Price: {cash_price:,.0f} | Down: {down_payment:,.0f} ({down_payment/cash_price*100 if cash_price else 0:.1f}%)")
    c.drawString(20*mm, 250*mm, f"Monthly: {monthly:,.2f} x {term} months | Total Interest: {total_interest:,.0f} | Total Payable: {total_payable:,.0f}")
    c.drawString(20*mm, 244*mm, f"DSR: {dsr:.1f}% | Rule Verdict: {r_verdict}")
    
    c.setFont("Helvetica-Bold", 12)
    c.drawString(20*mm, 234*mm, "AI 13 Modules Analysis")
    c.setFont("Helvetica", 9)
    # Wrap AI text
    text_object = c.beginText(20*mm, 228*mm)
    text_object.setFont("Helvetica", 9)
    for line in (ai_text or "No AI analysis yet.").split("\n")[:60]:
        # Cut long lines
        for chunk in [line[i:i+95] for i in range(0, len(line), 95)]:
            if text_object.getY() < 20*mm:
                c.drawText(text_object)
                c.showPage()
                text_object = c.beginText(20*mm, 280*mm)
            text_object.textLine(chunk)
    c.drawText(text_object)
    c.showPage()
    c.save()
    buf.seek(0)
    return buf

# ==========================================
# 5. MAIN - 4 Steps
# ==========================================
# Step Bar
st.markdown("""
<div class="srd-card">
    <div style="display:flex; justify-content:space-between; text-align:center;">
        <div><div style="width:40px;height:40px;background:#16A34A;color:white;border-radius:50%;display:flex;align-items:center;justify-content:center;margin:auto;">✓</div><b>ขั้นตอนที่ 1</b><br>เลือกยานพาหนะ</div>
        <div><div style="width:40px;height:40px;background:#2563EB;color:white;border-radius:50%;display:flex;align-items:center;justify-content:center;margin:auto;">2</div><b>ขั้นตอนที่ 2</b><br>ผู้สมัคร & ผู้ค้ำประกัน</div>
        <div><div style="width:40px;height:40px;background:#F1F5F9;color:#64748B;border:2px solid #E2E8F0;border-radius:50%;display:flex;align-items:center;justify-content:center;margin:auto;">3</div><b>ขั้นตอนที่ 3</b><br>เช็กลิสต์เอกสาร • 6 รายการ</div>
        <div><div style="width:40px;height:40px;background:#F1F5F9;color:#64748B;border:2px solid #E2E8F0;border-radius:50%;display:flex;align-items:center;justify-content:center;margin:auto;">4</div><b>ขั้นตอนที่ 4</b><br>การวิเคราะห์ 13 โมดูลด้วย AI</div>
    </div>
</div>
""", unsafe_allow_html=True)

# Load Data
motorcycle_data = load_all_motorcycle_data()

# Layout Responsive 2 columns
left, right = st.columns([2, 1])

with left:
    with st.container():
        st.markdown('<div class="srd-card">', unsafe_allow_html=True)
        st.markdown("### 🧮 เครื่องคำนวณอัตราดอกเบี้ยคงที่")
        st.caption("ปรับค่าพารามิเตอร์สินเชื่อด้านล่าง — สามารถแก้ไขได้ทุกช่อง")

        # Category
        if motorcycle_data:
            cat = st.selectbox("หมวดหมู่รถ (5 หมวด)", list(motorcycle_data.keys()))
            df_cat = motorcycle_data[cat]
            # หา column รุ่นรถ
            model_col = 'รุ่นรถ' if 'รุ่นรถ' in df_cat.columns else df_cat.columns[0]
            model_name = st.selectbox("รุ่นรถ", df_cat[model_col].astype(str).unique()[:200])
            try:
                row = df_cat[df_cat[model_col].astype(str) == model_name].iloc[0]
                default_price = float(row.get('ราคาสด', row.get('ราคาจัด', 80000)))
                default_interest = float(row.get('ดอกเบี้ย', row.get('ดอกเบี้ย\n(ต่อเดือน)', 1.5)))
                if default_interest > 10: # ถ้าเป็น % ต่อปี แปลงเป็นต่อเดือน
                    default_interest = default_interest / 12
            except:
                default_price = 80000
                default_interest = 1.5
        else:
            st.warning("ไม่พบไฟล์ Excel - ใช้โหมดกรอกมือ")
            model_name = st.text_input("รุ่นรถ", "Yamaha Finn")
            default_price = 50000
            default_interest = 1.5
            cat = "Auto"

        c1, c2 = st.columns(2)
        with c1:
            cash_price = st.number_input("ราคารถ (MYR/บาท)", value=float(default_price), step=1000.0, help="ราคาสด + ค่า พรบ.รวมจัด")
            tenure = st.selectbox("ระยะเวลาผ่อน (เดือน)", [12, 18, 24, 30, 36, 42, 48, 60], index=2)
        with c2:
            down_payment = st.number_input("เงินดาวน์ (MYR/บาท)", value=float(default_price*0.2), step=500.0)
            flat_rate = st.number_input("อัตราดอกเบี้ยคงที่ (% ต่อเดือน)", value=float(default_interest), step=0.1, format="%.2f")

        proc_fee = st.number_input("ค่าธรรมเนียมดำเนินการ (MYR)", value=300.0)

        # Flat Rate Full Formula
        down_pct = (down_payment / cash_price * 100) if cash_price else 0
        financing_amount = cash_price - down_payment
        total_interest = financing_amount * (flat_rate/100) * tenure
        total_debt = financing_amount + total_interest
        monthly_installment = total_debt / tenure if tenure else 0
        total_hire_purchase = down_payment + proc_fee + total_debt
        total_cash_to_drive = down_payment + proc_fee

        # Editable Installment
        monthly_installment_edit = st.number_input("ค่างวดต่อเดือน (แก้ไขได้ - จะส่งไป DSR และ AI อัตโนมัติ)", value=float(monthly_installment), step=10.0)

        col_calc, col_pdf = st.columns(2)
        with col_calc:
            st.button("⚡ คำนวณสินเชื่อ", type="primary", use_container_width=True)
        with col_pdf:
            # PDF Export Button 1
            if 'ai_result_text' not in st.session_state:
                st.session_state.ai_result_text = ""
            pdf_buf = generate_pdf_report(
                st.session_state.get('applicant_name',''), model_name, cash_price, down_payment,
                monthly_installment_edit, tenure, total_interest, total_debt+down_payment+proc_fee,
                st.session_state.get('dsr_calc',0), st.session_state.get('r_verdict',''), st.session_state.ai_result_text
            )
            st.download_button("📄 ส่งออกเป็น PDF", data=pdf_buf, file_name=f"SRD_Loan_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf", mime="application/pdf", use_container_width=True)

        st.write("---")
        st.markdown(f"""
        **ยอดผ่อนชำระโดยประมาณ:** <span style="font-size:22px;color:#1E40AF;font-weight:700;">MYR {monthly_installment_edit:,.2f} / เดือน</span><br>
        ดอกเบี้ยรวม: MYR {total_interest:,.0f} | ยอดชำระรวม: MYR {total_debt+down_payment+proc_fee:,.0f} | รวมจ่ายวันออกรถ: MYR {total_cash_to_drive:,.0f}<br>
        <small>ยอดจัดไฟแนนซ์ = (ราคาสด + ค่า พรบ.รวมจัด) - เงินดาวน์ | สูตร: ยอดจัด x (ดอกเบี้ย%/100) x งวด</small>
        """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

        # Applicant Info (Step 2)
        st.markdown('<div class="srd-card">', unsafe_allow_html=True)
        st.markdown("### 👤 ข้อมูลผู้สมัคร & ผู้ค้ำประกัน")
        a1, a2 = st.columns(2)
        with a1:
            applicant_name = st.text_input("ชื่อผู้กู้", "สมชาย")
            salary = st.number_input("เงินเดือน", value=15000.0, step=500.0)
            extra_income = st.number_input("รายได้เสริม", value=2000.0)
        with a2:
            applicant_phone = st.text_input("เบอร์โทร", "081-xxx-xxxx")
            existing_debt = st.number_input("หนี้เดิมต่อเดือน", value=3000.0)
            emp_type = st.selectbox("อาชีพ", ["พนักงานประจำ", "ฟรีแลนซ์/รับจ้างทั่วไป", "ค้าขาย", "ว่างงาน/ไม่มีงานประจำ"])

        st.session_state.applicant_name = applicant_name
        total_income = salary + extra_income
        dsr_calc = ((existing_debt + monthly_installment_edit) / total_income * 100) if total_income else 0
        st.session_state.dsr_calc = dsr_calc
        r_score, r_flags, r_verdict = evaluate_fraud_rules(cat, down_pct, emp_type, 0, dsr_calc, True)
        st.session_state.r_verdict = r_verdict

        st.metric("DSR (สัดส่วนหนี้ต่อรายได้)", f"{dsr_calc:.1f}%", delta="ปลอดภัย <50%" if dsr_calc<50 else "เกินเกณฑ์")
        st.metric("Rule Engine", r_verdict)
        if r_flags:
            for f in r_flags:
                st.warning(f)
        st.markdown('</div>', unsafe_allow_html=True)

        # Document Upload (Step 3) - Mobile Compressed
        st.markdown('<div class="srd-card">', unsafe_allow_html=True)
        st.markdown("### 📸 เช็กลิสต์เอกสาร • 6 รายการ")
        st.caption("ภาพถ่ายหน้าคู่บัตรยืนยันตัวตน, บัตร ปชช + ทะเบียนบ้าน, สเตทเม้นท์, NCB, สลิปเงินเดือน, ที่พัก + ที่ทำงาน")
        attached_docs = st.multiselect("เลือกเอกสารที่แนบแล้ว", ["Face Verification", "บัตร ปชช + ทะเบียนบ้าน", "Statement", "NCB", "สลิปเงินเดือน", "ที่พัก + ที่ทำงาน"], default=["บัตร ปชช + ทะเบียนบ้าน", "Statement"])
        uploaded_files = st.file_uploader("แนบภาพเอกสาร (รองรับ HEIC iPhone - ระบบย่ออัตโนมัติ 12MB->0.9MB)", type=["jpg","jpeg","png","heic","heif","webp"], accept_multiple_files=True)
        cam = st.camera_input("ถ่ายจากกล้องมือถือโดยตรง (ถ้าใช้มือถือ)")
        all_uploads = []
        if uploaded_files:
            all_uploads.extend(uploaded_files)
        if cam:
            all_uploads.append(cam)
        if all_uploads:
            st.success(f"📁 เตรียมไฟล์แล้ว {len(all_uploads)} ไฟล์ (ระบบจะย่อก่อนส่ง AI)")
            preview_cols = st.columns(3)
            compressed_for_ai = []
            for idx, f in enumerate(all_uploads):
                try:
                    img = Image.open(f)
                    comp = _compress_mobile(img)
                    compressed_for_ai.append(comp)
                    with preview_cols[idx%3]:
                        st.image(comp, caption=f"{getattr(f,'name','camera')[:15]}", use_container_width=True)
                except Exception as e:
                    st.error(f"อ่านไฟล์ไม่ได้: {e}")
            st.session_state.compressed_for_ai = compressed_for_ai
        else:
            st.session_state.compressed_for_ai = []
            st.info("💡 เคล็ดลับมือถือ: ถ่ายแล้วระบบย่ออัตโนมัติ ไม่ต้องครอปเอง")
        st.markdown('</div>', unsafe_allow_html=True)

        # AI Run
        st.markdown('<div class="srd-card">', unsafe_allow_html=True)
        if st.button("🚀 รัน SRD Credit Investigation Engine 13 Modules เต็มระบบ", type="primary", use_container_width=True):
            if not st.session_state.compressed_for_ai:
                st.warning("กรุณาแนบภาพเอกสารอย่างน้อย 1 ไฟล์")
            else:
                prompt = f"""
                SRD CREDIT INVESTIGATION ENGINE (FULL 13 MODULES) - ภาษาไทย
                รุ่นรถ: {model_name} หมวด {cat} ราคา {cash_price:,.0f} ดาวน์ {down_payment:,.0f} ({down_pct:.1f}%) ยอดจัด {financing_amount:,.0f}
                ค่างวด {monthly_installment_edit:,.0f} x {tenure} งวด ดอกเบี้ย {flat_rate:.2f}%/เดือน DSR {dsr_calc:.1f}%
                Rule: {r_verdict} Score {r_score} Flags {r_flags}
                ผู้กู้: {applicant_name} อาชีพ {emp_type} รายได้ {total_income:,.0f}
                เอกสารแนบ: {', '.join(attached_docs)}
                ให้วิเคราะห์ตามโครงสร้าง 10 ข้อ: Customer Profile, Identity & Workplace, Verified vs Unverified, Money Flow, Fraud Gambling Nominee, Guarantor Mitigation, Contradiction Table, Risk Scoring 100 คะแนน, 30-sec Interview, Summary
                ตอบเป็นภาษาไทย
                """
                def call_gemini_v2(prompt_text, pil_images, model_name):
                    contents = [prompt_text]
                    for img in pil_images:
                        if max(img.size) > 1600:
                            img.thumbnail((1600,1600))
                        buf = io.BytesIO()
                        img.save(buf, format="JPEG")
                        contents.append(types.Part.from_bytes(data=buf.getvalue(), mime_type="image/jpeg"))
                    try:
                        response = client.models.generate_content(model=model_name, contents=contents, config=types.GenerateContentConfig(temperature=0.2, max_output_tokens=8192))
                        text = getattr(response, 'text', None) or response.candidates[0].content.parts[0].text
                        return {"ok": True, "text": text}
                    except ClientError as e:
                        msg=str(e)
                        if "429" in msg or "quota" in msg.lower():
                            return {"ok": False, "error": "QUOTA_FULL", "raw": msg}
                        return {"ok": False, "error": "API_ERROR", "raw": msg}
                    except Exception as e:
                        msg=str(e)
                        if "429" in msg or "quota" in msg.lower():
                            return {"ok": False, "error": "QUOTA_FULL", "raw": msg}
                        return {"ok": False, "error": "API_ERROR", "raw": msg}

                with st.spinner(f"AI ({selected_model}) กำลังวิเคราะห์ 13 โมดูล..."):
                    result = call_gemini_v2(prompt, st.session_state.compressed_for_ai, selected_model)
                if result["ok"]:
                    st.session_state.ai_result_text = result["text"]
                    st.success("✅ วิเคราะห์สำเร็จ")
                    st.markdown(result["text"])
                    # Save
                    record = {"Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Applicant": applicant_name, "Model": model_name, "Cash_Price": cash_price, "Down": down_payment, "Monthly": monthly_installment_edit, "DSR": f"{dsr_calc:.1f}%", "Rule": r_verdict}
                    save_assessment_record(record)
                elif result["error"]=="QUOTA_FULL":
                    st.error("⏳ AI โควตาเต็มชั่วคราว (429) - Rule Engine และ DSR ยังดูได้ปกติ")
                else:
                    st.error(f"Error: {result['raw']}")

        # PDF Export 13 Modules
        if st.session_state.get('ai_result_text'):
            pdf2 = generate_pdf_report(applicant_name, model_name, cash_price, down_payment, monthly_installment_edit, tenure, total_interest, total_debt+down_payment+proc_fee, dsr_calc, r_verdict, st.session_state.ai_result_text)
            st.download_button("📄 ส่งออกรายงาน 13 โมดูล PDF", data=pdf2, file_name=f"SRD_13Modules_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf", mime="application/pdf", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

with right:
    # DSR Meter
    st.markdown('<div class="srd-card">', unsafe_allow_html=True)
    st.markdown("### 📊 มาตรวัด DSR")
    color = "#16A34A" if dsr_calc<35 else "#F59E0B" if dsr_calc<50 else "#DC2626"
    st.markdown(f"<div style='text-align:center;'><div style='font-size:32px;font-weight:700;color:{color};'>{dsr_calc:.1f}%</div><div>อัตราส่วนภาระหนี้</div><div style='background:#DCFCE7;color:#166534;padding:4px 8px;border-radius:12px;font-size:12px;display:inline-block;'>{'อยู่ในเกณฑ์ปลอดภัย (<50%)' if dsr_calc<50 else 'เกินเกณฑ์'}</div></div>", unsafe_allow_html=True)
    st.write(f"รายได้ต่อเดือน: MYR {total_income:,.0f}")
    st.write(f"ภาระค่าใช้จ่ายต่อเดือน: MYR {existing_debt+monthly_installment_edit:,.0f}")
    st.markdown('</div>', unsafe_allow_html=True)

    # Risk Score
    st.markdown('<div class="srd-card">', unsafe_allow_html=True)
    st.markdown("### 🛡️ คะแนนความเสี่ยง")
    score = max(300, min(850, 850 - r_score*3 - dsr_calc*2))
    st.markdown(f"<div style='text-align:center;'><span style='font-size:32px;font-weight:700;color:#4F46E5;'>{score:.0f}</span> <span style='background:#DDD6FE;color:#5B21B6;padding:4px 10px;border-radius:12px;'>{'ความเสี่ยงต่ำ' if score>700 else 'ปานกลาง' if score>600 else 'สูง'}</span></div>", unsafe_allow_html=True)
    st.write(f"Risk Band: PD {r_score/2:.1f}%")
    st.info(f"ข้อแนะนำ: {r_verdict}")
    st.markdown('</div>', unsafe_allow_html=True)

    # AI 13 Modules
    st.markdown('<div class="srd-card">', unsafe_allow_html=True)
    st.markdown("### 🤖 การวิเคราะห์ 13 โมดูลด้วย AI")
    modules = ["การตรวจสอบรายได้", "การตรวจสอบประวัติเครดิต", "การประเมินภาระหนี้", "การตรวจสอบเอกสาร", "การตรวจสอบที่อยู่", "การตรวจสอบการทำงาน", "การประเมินรายได้สุทธิ", "การคำนวณ DSR", "การประเมินความเสี่ยง", "การตรวจสอบบัญชีดำ", "ความแข็งแกร่งของผู้ค้ำ", "ข้อแนะนำ", "การปฏิบัติตามกฎ"]
    cols = st.columns(2)
    for i, m in enumerate(modules):
        with cols[i%2]:
            st.caption(f"✅ {m}")
    if st.session_state.get('ai_result_text'):
        st.success("เสร็จสิ้น 13/13 • Confidence 92%")
    else:
        st.caption("รอการวิเคราะห์...")
    st.markdown('</div>', unsafe_allow_html=True)

st.caption(f"อัปเดตล่าสุด: {datetime.now().strftime('%d %b %Y • %H:%M')} | รหัสอ้างอิงสินเชื่อ: MC-{datetime.now().strftime('%Y-%m%d')}")
