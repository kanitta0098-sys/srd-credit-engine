
import streamlit as st
import os, io, pandas as pd
from datetime import datetime
from PIL import Image
try:
    import pillow_heif; pillow_heif.register_heif_opener()
except: pass
def _compress_mobile(img, max_side=1280, max_bytes=1200000):
    img=img.convert("RGB")
    if max(img.size)>max_side: img.thumbnail((max_side,max_side), Image.LANCZOS)
    for q in [75,65,55,40]:
        b=io.BytesIO(); img.save(b, format="JPEG", quality=q, optimize=True)
        if b.tell()<=max_bytes: b.seek(0); return Image.open(b)
    b.seek(0); return Image.open(b)

st.set_page_config(page_title="SRD Credit Engine Hybrid v2.1 - Single Calculator", layout="wide", page_icon="🏍️")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;600;700;800&display=swap');
html, body, [class*="css"] { font-family:'Sarabun', sans-serif !important; }
.stApp { background:#0F172A !important; color:#E2E8F0 !important; }
.moto-card { background:#1E293B !important; border:2px solid #334155 !important; border-radius:16px; padding:16px 18px; margin-bottom:14px; }
.calc-table { width:100%; border-collapse:collapse; }
.calc-table td { padding:8px 12px; border:1px solid #334155; font-size:14px; }
.calc-table tr:nth-child(even) { background:#0F172A; }
.calc-table tr:nth-child(odd) { background:#1E293B; }
.calc-yellow { background:linear-gradient(135deg,#FDE68A,#FBBF24) !important; color:#000 !important; font-weight:800; }
.calc-red { background:linear-gradient(135deg,#FCA5A5,#F87171) !important; color:#7F1D1D !important; font-weight:800; }
.result-bold { font-weight:800; font-size:16px; color:#FBBF24; }
.block-container { max-width:1200px !important; padding-top:1rem !important; }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_master_models():
    paths=[
        "/mnt/data/Motorcycle-Price-All-Models.xlsx",
        "Motorcycle-Price-All-Models.xlsx",
        "/mount/src/srd-credit-engine/Motorcycle-Price-All-Models.xlsx",
        "/mnt/data/motorcycle_price_all_models.xlsx"
    ]
    df_final=None
    for p in paths:
        if os.path.exists(p):
            try:
                df=pd.read_excel(p, sheet_name=0, header=1)
                if 'รุ่นรถ' in df.columns:
                    df['รุ่นรถ']=df['รุ่นรถ'].ffill()
                    df['รหัสรถ']=df['รหัสรถ'].ffill()
                    df['ราคาจัด']=df['ราคาจัด'].ffill()
                    interest_col=[c for c in df.columns if 'ดอกเบี้ย' in str(c)][0]
                    df[interest_col]=df[interest_col].ffill()
                    df_base=df[df['%ดาวน์']==0].copy()
                    df_base=df_base[~df_base['รุ่นรถ'].astype(str).str.contains('รุ่นรถ|ตารางโปรโมชัน', na=False)]
                    df_base['รุ่นรถ']=df_base['รุ่นรถ'].astype(str).str.strip()
                    df_base=df_base[df_base['รุ่นรถ']!='nan']
                    df_base=df_base.drop_duplicates(subset=['รุ่นรถ'], keep='first')
                    rename_map={'ราคาจัด':'ยอดจัด', interest_col:'ดอกเบี้ยต่อเดือน', 'ดาวน์':'ราคาดาวน์', 'ค่าจด/พรบ.':'ทะเบียน พรบ ประกัน', 'รวมออกรถ':'ค่าใช้จ่ายออกรถ'}
                    df_base=df_base.rename(columns=rename_map)
                    df_final=df_base
                    break
            except Exception as e:
                continue
    if df_final is None:
        # fallback csv
        for cp in ["/mnt/data/price_backup_all_models.csv"]:
            if os.path.exists(cp):
                df=pd.read_csv(cp, encoding='utf-8')
                df_final=df
                break
    if df_final is None:
        df_final=pd.DataFrame({"รุ่นรถ":["ฟาซซิโอ้ SMK"],"รหัสรถ":["BKF700"],"ยอดจัด":[54600],"ดอกเบี้ยต่อเดือน":[0.015],"ราคาดาวน์":[0],"ทะเบียน พรบ ประกัน":[1000]})
    return df_final

def evaluate_fraud_rules(vehicle_type, down_pct, employment_type, shared, dsr, gps):
    score=0; flags=[]
    high=["Yamaha - Sport","Honda","SPORT","R15","WR155R","Aerox"]
    unstable=["ฟรีแลนซ์/รับจ้างทั่วไป","ว่างงาน/ไม่มีงานประจำ"]
    if any(x in vehicle_type for x in high) and down_pct<=5.0 and employment_type in unstable:
        score+=40; flags.append("⚠️ ดาวน์แลกเงิน")
    if shared>=1:
        score+=50; flags.append("🚨 เครือข่ายนายหน้า")
    if (dsr>50.0 or down_pct<10.0) and not gps:
        score+=20; flags.append("⚠️ DSR>50% หรือดาวน์<10% ไม่มี GPS")
    if score>=80: verdict="⛔ AUTO REJECT"
    elif score>=50: verdict="🟠 MANUAL REVIEW"
    else: verdict="🟢 AUTO PASS"
    return score, flags, verdict

HISTORY_FILE="srd_credit_assessment_history.csv"
def save_record(rec):
    df=pd.DataFrame([rec])
    if not os.path.exists(HISTORY_FILE): df.to_csv(HISTORY_FILE, index=False, encoding='utf-8-sig')
    else: df.to_csv(HISTORY_FILE, mode='a', header=False, index=False, encoding='utf-8-sig')

# SIDEBAR
with st.sidebar:
    st.markdown("### 🏍️ SRD Hybrid v2.1\nSingle Calculator")
    api_key=st.text_input("GEMINI API Key", value=st.secrets.get("GEMINI_API_KEY","") if hasattr(st,'secrets') else "", type="password")
    model_sel=None; usable=[]
    if api_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key.strip())
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    usable.append(m.name.replace("models/",""))
            if usable:
                model_sel=st.selectbox("🤖 โมเดล AI", usable, index=0)
                st.success(f"✅ {model_sel}")
        except Exception as e: st.error(str(e))
    df_master=load_master_models()
    st.caption(f"📂 Motorcycle-Price-All-Models: {len(df_master)} รุ่น")
    st.dataframe(df_master[["รุ่นรถ","ยอดจัด","ดอกเบี้ยต่อเดือน"]].head(10), height=200)

# HEADER
st.markdown("""<div class="moto-card" style="display:flex;justify-content:space-between;align-items:center;background:linear-gradient(135deg,#0F172A,#1E293B) !important;"><div><div style="font-size:26px;font-weight:800;color:#FFF;">🏍️ SRD Credit Engine Hybrid v2.1</div><div style="font-size:12px;color:#38BDF8;">เครื่องคำนวณค่างวดเดี่ยว (Interactive Single Calculator) + Motorcycle-Price-All-Models.xlsx + ยอดจัด auto • ดอกเบี้ย Yamaha auto</div></div><div><span style="background:#065F46;color:#6EE7B7;border-radius:20px;padding:6px 12px;font-size:12px;">● ONLINE</span> <span style="background:#1E3A8A;color:#93C5FD;border-radius:20px;padding:6px 12px;font-size:12px;">v2.1 Single Calc</span></div></div>""", unsafe_allow_html=True)

# === Interactive Single Calculator - ตามภาพที่แนบ ===
st.markdown('<div class="moto-card">', unsafe_allow_html=True)
st.subheader("เครื่องคำนวณค่างวดเดี่ยว (Interactive Single Calculator)")
st.caption("ตามภาพที่แนบ - ช่องว่างแบบเหมาะสม - ดึงจาก Motorcycle-Price-All-Models หรือมีตัวเลือกว่าง - แก้ไขตัวเลขได้")

price_df=load_master_models()
model_list=price_df["รุ่นรถ"].astype(str).tolist()
price_dict={row["รุ่นรถ"]: row for _, row in price_df.iterrows()}

# Row 1: ชื่อรุ่นรถ / Model: (คำสั่ง) ดึงข้อมูลงาน Motorcycle-Price-All-Models หรือมีตัวเลือกว่าง
c1, c2 = st.columns([0.45, 0.55])
with c1:
    st.markdown("**ชื่อรุ่นรถ / Model:** (คำสั่ง) ดึงข้อมูลงาน Motorcycle-Price-All-Models หรือมีตัวเลือกว่าง")
with c2:
    brand_model=st.selectbox("ชื่อรุ่นรถ / Model", options=["[ว่าง] เลือกรุ่นรถ"]+model_list, index=0, key="model_single_v21", label_visibility="collapsed")
    selected_row=price_dict.get(brand_model) if brand_model in price_dict else None

# Row 2: ราคาสดตัวรถ (Cash Price): ช่องว่างแบบเหมาะสม
c1, c2 = st.columns([0.45, 0.55])
with c1:
    st.markdown("**ราคาสดตัวรถ (Cash Price):** (คำสั่ง) ช่องว่างแบบเหมาะสม")
with c2:
    cash_default=float(selected_row["ยอดจัด"]+selected_row["ราคาดาวน์"]) if selected_row is not None and pd.notna(selected_row["ยอดจัด"]) else 85500.0
    cash_price=st.number_input("ราคาสดตัวรถ", value=cash_default, step=100.0, key="cash_single_v21", label_visibility="collapsed")

# Row 3: บวกค่า พรบ./ทะเบียน/ประกันรถหาย (รวมในยอดจัด): ช่องว่างแบบเหมาะสม
c1, c2 = st.columns([0.45, 0.55])
with c1:
    st.markdown("**บวกค่า พรบ./ทะเบียน/ประกันรถหาย (รวมในยอดจัด):** (คำสั่ง) ช่องว่างแบบเหมาะสม")
with c2:
    reg_default=float(selected_row["ทะเบียน พรบ ประกัน"]) if selected_row is not None and pd.notna(selected_row["ทะเบียน พรบ ประกัน"]) else 0.0
    reg_fee=st.number_input("พรบ ทะเบียน ประกัน", value=reg_default, step=100.0, key="reg_single_v21", label_visibility="collapsed")

# Row 4: รวมราคารถสุทธิ (Net Price): ราคาสดตัวรถ+พรบ./ทะเบียน/ประกันรถหาย = ผลลัพธ์
net_price=cash_price+reg_fee
c1, c2 = st.columns([0.45, 0.55])
with c1:
    st.markdown("**รวมราคารถสุทธิ (Net Price):** (คำสั่ง) ราคาสดตัวรถ+พรบ./ทะเบียน/ประกันรถหาย = ผลลัพธ์")
with c2:
    st.markdown(f"<div class='calc-yellow' style='padding:8px 12px;border-radius:8px;'>รวมราคารถสุทธิ = {cash_price:,.0f} + {reg_fee:,.0f} = <b>{net_price:,.0f}</b></div>", unsafe_allow_html=True)

# Row 5: เงินดาวน์ (Down Payment): ช่องว่างแบบเหมาะสม
c1, c2 = st.columns([0.45, 0.55])
with c1:
    st.markdown("**เงินดาวน์ (Down Payment):** (คำสั่ง) ช่องว่างแบบเหมาะสม")
with c2:
    down_default=float(selected_row["ราคาดาวน์"]) if selected_row is not None and pd.notna(selected_row["ราคาดาวน์"]) else 8900.0
    down_payment=st.number_input("เงินดาวน์", value=down_default, step=100.0, key="down_single_v21", label_visibility="collapsed")

# Row 6: ยอดจัดไฟแนนซ์ (Financing Amount): /รวมราคารถสุทธิ (Net Price)
financing=net_price-down_payment
c1, c2 = st.columns([0.45, 0.55])
with c1:
    st.markdown("**ยอดจัดไฟแนนซ์ (Financing Amount):** /รวมราคารถสุทธิ (Net Price) - ดาวน์ = ผลลัพธ์")
with c2:
    st.markdown(f"<div class='calc-yellow' style='padding:8px 12px;border-radius:8px;'>ยอดจัด = {net_price:,.0f} - {down_payment:,.0f} = <b>{financing:,.0f}</b> (auto)</div>", unsafe_allow_html=True)

# Row 7: อัตราดอกเบี้ยต่อเดือน (Flat Rate / Month %): ดึงข้อมูลงาน Motorcycle-Price-All-Models หรือมีตัวเลือกว่าง
c1, c2 = st.columns([0.45, 0.55])
with c1:
    st.markdown("**อัตราดอกเบี้ยต่อเดือน (Flat Rate / Month %):** (คำสั่ง) ดึงข้อมูลงาน Motorcycle-Price-All-Models หรือมีตัวเลือกว่าง")
with c2:
    flat_default=float(selected_row["ดอกเบี้ยต่อเดือน"]*100) if selected_row is not None and pd.notna(selected_row["ดอกเบี้ยต่อเดือน"]) else 1.70
    flat_rate=st.number_input("Flat Rate %", value=flat_default, step=0.05, format="%.2f", key="flat_single_v21", label_visibility="collapsed", help="ดึงจาก Motorcycle-Price-All-Models.xlsx auto - ไม่ต้องจำ")
    st.caption(f"ดอกเบี้ย auto {flat_default:.2f}% จากไฟล์ Yamaha" if selected_row is not None else "เลือกยี่ห้อ/รุ่นเพื่อดึงดอกเบี้ย auto")

# Row 8: ระยะเวลาผ่อน (จำนวนงวด / Months): สามารถแก้ไขตัวเลขได้
c1, c2 = st.columns([0.45, 0.55])
with c1:
    st.markdown("**ระยะเวลาผ่อน (จำนวนงวด / Months):** (คำสั่ง) สามารถแก้ไขตัวเลขได้ 12/18/24/30/36/48/55/62")
with c2:
    term_options=[12,18,24,30,36,48,55,62]
    col_t1, col_t2 = st.columns([0.6,0.4])
    with col_t1:
        term_sel=st.selectbox("Term", options=term_options, index=5, key="term_single_v21", label_visibility="collapsed")
    with col_t2:
        custom=st.checkbox("✏️ กำหนดเอง", key="custom_term_single_v21")
    if custom:
        term=st.number_input("Term กำหนดเอง", min_value=6, max_value=84, value=term_sel, step=1, key="term_custom_single_v21", label_visibility="collapsed")
    else:
        term=term_sel

# Row 9: รวมดอกเบี้ยทั้งหมด (Total Interest): อัตราดอกเบี้ยต่อเดือน * ระยะเวลาผ่อน = ผลลัพธ์
total_interest=financing*(flat_rate/100)*term
c1, c2 = st.columns([0.45, 0.55])
with c1:
    st.markdown("**รวมดอกเบี้ยทั้งหมด (Total Interest):** (คำสั่ง) Flat%*Months = ผลลัพธ์")
with c2:
    st.markdown(f"<div style='padding:8px 12px;border-radius:8px;background:#1E3A8A;color:#DBEAFE;'>รวมดอกเบี้ย = {financing:,.0f} × {flat_rate:.2f}% × {term} = <b>{total_interest:,.0f}</b></div>", unsafe_allow_html=True)

# Row 10: ยอดหนี้รวมทั้งหมด (Total Debt): ยอดจัด + รวมดอกเบี้ย
total_debt=financing+total_interest
c1, c2 = st.columns([0.45, 0.55])
with c1:
    st.markdown("**ยอดหนี้รวมทั้งหมด (Total Debt):** (คำสั่ง) ยอดจัด+รวมดอกเบี้ย")
with c2:
    st.markdown(f"<div class='calc-yellow' style='padding:8px 12px;border-radius:8px;'>ยอดหนี้รวม = {financing:,.0f} + {total_interest:,.0f} = <b>{total_debt:,.0f}</b></div>", unsafe_allow_html=True)

# Row 11: ค่างวดต่อเดือน (Monthly Payment): ยอดหนี้รวม/จำนวนงวด = ผลลัพธ์
monthly=total_debt/term if term>0 else 0
c1, c2 = st.columns([0.45, 0.55])
with c1:
    st.markdown("**ค่างวดต่อเดือน (Monthly Payment):** (คำสั่ง) Total Debt/Months = ผลลัพธ์")
with c2:
    st.markdown(f"<div class='calc-red' style='padding:8px 12px;border-radius:8px;font-size:18px;'>ค่างวดต่อเดือน = {total_debt:,.0f} / {term} = <b>{monthly:,.0f}</b> บาท</div>", unsafe_allow_html=True)

# Row 12-13: ค่า พรบ./ทะเบียน/ประกันรถหาย (คำสั่ง) ช่องว่างแบบเหมาะสม + เงินดาวน์ ช่องว่างแบบเหมาะสม (ซ้ำตามภาพ)
st.markdown("---")
st.caption("ส่วนล่างตามภาพ: ค่า พรบ./ทะเบียน/ประกันรถหาย + เงินดาวน์ + ออกรถได้")
c1, c2 = st.columns([0.45, 0.55])
with c1:
    st.markdown("**ค่า พรบ./ทะเบียน/ประกันรถหาย** (คำสั่ง) ช่องว่างแบบเหมาะสม")
with c2:
    reg_fee2=st.number_input("พรบ ทะเบียน ประกัน ล่าง", value=reg_fee, step=100.0, key="reg2_single_v21", label_visibility="collapsed")

c1, c2 = st.columns([0.45, 0.55])
with c1:
    st.markdown("**เงินดาวน์ (Down Payment):** (คำสั่ง) ช่องว่างแบบเหมาะสม")
with c2:
    down2=st.number_input("เงินดาวน์ล่าง", value=down_payment, step=100.0, key="down2_single_v21", label_visibility="collapsed")

# Row 14: ออกรถได้ = ดาวน์+พรบ.ทะเบียน/ประกัน = ผลลัพธ์
total_drive=down2+reg_fee2
c1, c2 = st.columns([0.45, 0.55])
with c1:
    st.markdown("**ออกรถได้** (คำสั่ง) = ช่อง ดาวน์+ช่อง พรบ.ทะเบียน/ประกัน = ผลลัพธ์")
with c2:
    st.markdown(f"<div class='calc-red' style='padding:10px 12px;border-radius:8px;font-size:20px;text-align:center;'>ออกรถได้ = {down2:,.0f} + {reg_fee2:,.0f} = <b>{total_drive:,.0f}</b> บาท</div>", unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# Summary table matching image
st.markdown('<div class="moto-card">', unsafe_allow_html=True)
st.markdown("**สรุปตามภาพที่แนบ - ตารางเครื่องคำนวณค่างวดเดี่ยว**")
summary_df=pd.DataFrame([
    ["ชื่อรุ่นรถ / Model:", brand_model],
    ["ราคาสดตัวรถ (Cash Price):", f"{cash_price:,.0f}"],
    ["บวกค่า พรบ./ทะเบียน/ประกันรถหาย (รวมในยอดจัด):", f"{reg_fee:,.0f}"],
    ["รวมราคารถสุทธิ (Net Price):", f"{net_price:,.0f}"],
    ["เงินดาวน์ (Down Payment):", f"{down_payment:,.0f}"],
    ["ยอดจัดไฟแนนซ์ (Financing Amount):", f"{financing:,.0f}"],
    ["อัตราดอกเบี้ยต่อเดือน (Flat Rate / Month %):", f"{flat_rate:.2f}%"],
    ["ระยะเวลาผ่อน (จำนวนงวด / Months):", f"{term}"],
    ["รวมดอกเบี้ยทั้งหมด (Total Interest):", f"{total_interest:,.0f}"],
    ["ยอดหนี้รวมทั้งหมด (Total Debt):", f"{total_debt:,.0f}"],
    ["ค่างวดต่อเดือน (Monthly Payment):", f"{monthly:,.0f}"],
    ["ค่า พรบ./ทะเบียน/ประกันรถหาย", f"{reg_fee2:,.0f}"],
    ["เงินดาวน์ (Down Payment):", f"{down2:,.0f}"],
    ["ออกรถได้", f"{total_drive:,.0f}"]
], columns=["รายการ","จำนวน"])
st.table(summary_df)
st.markdown('</div>', unsafe_allow_html=True)

# Backend Engine ยังคงอยู่ด้านล่าง
st.markdown('<div class="moto-card" style="border:2px solid #8B5CF6 !important;">', unsafe_allow_html=True)
st.subheader("🏍️ ข้อมูลผู้เช่าซื้อ + วิเคราะห์ 13 โมดูลด้วย Ai")
st.caption("ต่อจากเครื่องคำนวณค่างวดเดี่ยว - Field Length Optimized")

c1, c2, c3 = st.columns([0.4,0.4,0.2])
with c1: f_name=st.text_input("ชื่อ", value="", placeholder="[ว่าง] สมชาย", key="fname_v21")
with c2: l_name=st.text_input("สกุล", value="", placeholder="[ว่าง] ใจดี", key="lname_v21")
with c3: age=st.number_input("อายุ", min_value=0, max_value=80, value=0, key="age_v21")
c1, c2, c3 = st.columns([0.35,0.35,0.3])
with c1: job=st.text_input("อาชีพ", value="", placeholder="[ว่าง]", key="job_v21")
with c2: phone=st.text_input("เบอร์โทร", value="", placeholder="[ว่าง] 081-xxx-xxxx", key="phone_v21")
with c3: emp_type=st.selectbox("ประเภทอาชีพ Rule", ["พนักงานประจำ","เจ้าของกิจการ","ฟรีแลนซ์/รับจ้างทั่วไป","ว่างงาน/ไม่มีงานประจำ"], key="emp_v21")

c1, c2, c3, c4 = st.columns(4)
with c1: residence=st.selectbox("ที่พัก", ["[ว่าง]","บ้านตนเอง/ปลอดภาระ","บ้านเช่า/หอพัก"], key="res_v21")
with c2: salary=st.number_input("เงินเดือน", value=0, step=500, key="sal_v21")
with c3: extra=st.number_input("รายได้เสริม", value=0, step=500, key="extra_v21")
with c4: debt_monthly=st.number_input("หนี้เดิม/เดือน", value=0, step=100, key="debt_monthly_v21")

total_inc=salary+extra
total_bur=debt_monthly+monthly
dsr=(total_bur/total_inc*100) if total_inc>0 else 0
down_pct=(down_payment/net_price*100) if net_price>0 else 0
r_score, r_flags, r_verdict=evaluate_fraud_rules("Auto", down_pct, emp_type, 0, dsr, False)

colA,colB,colC=st.columns(3)
with colA: st.metric("DSR Meter", f"{dsr:.1f}%")
with colB: st.metric("Risk Score", f"{int(min(100, dsr*1.2))}/100")
with colC: st.metric(f"Fraud Score - {r_verdict}", f"{r_score}")

st.markdown("---")
st.subheader("📸 อัปโหลดเอกสาร + เช็คลิสต์")
d1=st.checkbox("1. สำเนาบัตรประชาชน", key="doc1_v21")
d2=st.checkbox("2. ทะเบียนบ้าน", key="doc2_v21")
d3=st.checkbox("3. สลิปเงินเดือน", key="doc3_v21")
d4=st.checkbox("4. สเตทเม้นท์ 6 เดือน", key="doc4_v21")
attached=[n for n,c in [("บัตร ปชช",d1),("ทะเบียนบ้าน",d2),("สลิป",d3),("สเตทเม้นท์",d4)] if c]

uploaded=st.file_uploader("📸 Upload เอกสาร", type=["png","jpg","jpeg","heic","heif","webp"], accept_multiple_files=True, key="upload_v21")
if uploaded:
    bad=[f.name for f in uploaded if f.name.lower().endswith(('.dng','.raw','.arw','.cr2','.cr3','.nef'))]
    if bad:
        st.error(f"❌ พบไฟล์ RAW/DNG: {', '.join(bad)}")
        uploaded=[f for f in uploaded if not f.name.lower().endswith(('.dng','.raw','.arw','.cr2','.cr3','.nef'))]
cam=st.camera_input("📷 Take Photo", key="camera_v21")
workplace=st.text_input("📌 พิกัด Google Maps", value="", key="workplace_v21")
story=st.text_area("🏪 บันทึกบริบทหน้าร้าน", value="", key="story_v21")

if uploaded or cam or st.checkbox("✅ ทดสอบโดยไม่ต้องอัปโหลด", key="test_no_upload_v21"):
    if st.button("🚀 รัน SRD Credit Investigation Engine 13 Modules", type="primary", use_container_width=True, key="run_ai_v21"):
        if not api_key or not model_sel:
            st.error("กรุณากรอก API Key")
        else:
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key.strip())
                imgs=[]
                if uploaded:
                    for f in uploaded: imgs.append(_compress_mobile(Image.open(f)))
                if cam: imgs.append(_compress_mobile(Image.open(cam)))
                full_prompt=f"""
# SRD Hybrid v2.1 - Interactive Single Calculator
รุ่น {brand_model} ราคาสด {cash_price} + พรบ {reg_fee} = Net {net_price} ดาวน์ {down_payment} ยอดจัด {financing} = {net_price}-{down_payment} Flat {flat_rate}% Term {term} ดอกเบี้ยรวม {total_interest} ยอดหนี้รวม {total_debt} ค่างวด {monthly} ออกรถได้ {total_drive} = {down2}+{reg_fee2}
ผู้กู้ {f_name} {l_name} อายุ {age} อาชีพ {job} เบอร์ {phone} รายได้รวม {total_inc} DSR {dsr:.1f}% Rule {r_score} {r_verdict}
เอกสาร {attached} พิกัด {workplace} บริบท {story}
"""
                with st.spinner(f"AI ({model_sel}) วิเคราะห์..."):
                    model_ai=genai.GenerativeModel(model_sel)
                    if imgs: resp=model_ai.generate_content([full_prompt]+imgs)
                    else: resp=model_ai.generate_content(full_prompt)
                    save_record({"Timestamp":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"BrandModel":brand_model,"Cash":cash_price,"Reg":reg_fee,"Net":net_price,"Down":down_payment,"Financing":financing,"Flat":flat_rate,"Term":term,"TotalInterest":total_interest,"TotalDebt":total_debt,"Monthly":monthly,"TotalDrive":total_drive,"Applicant":f"{f_name} {l_name}","DSR":f"{dsr:.1f}%","RuleVerdict":r_verdict})
                    st.success(f"💾 บันทึกแล้ว - ยอดจัด auto {financing:,.0f} = {net_price:,.0f}-{down_payment:,.0f} | ดอกเบี้ย Yamaha auto {flat_rate:.2f}%")
                    st.markdown(resp.text)
            except Exception as e:
                st.error(f"Error: {e}")
else:
    st.info("อัปโหลดภาพเอกสารก่อนรัน AI")

st.markdown('</div>', unsafe_allow_html=True)
st.caption("Hybrid v2.1 • Interactive Single Calculator ตามภาพที่แนบ • ชื่อรุ่นรถ ดึงจาก Motorcycle-Price-All-Models.xlsx • ราคาสด ช่องว่างเหมาะสม • พรบ/ทะเบียน ช่องว่างเหมาะสม • Net Price = ราคาสด+พรบ = ผลลัพธ์ • ดาวน์ ช่องว่างเหมาะสม • ยอดจัด = Net-ดาวน์ • Flat Rate ดึงจากไฟล์หรือว่าง • Term แก้ไขได้ 12/18/24/30/36/48/55/62 • Total Interest = Flat*Months • Total Debt = Financing+Interest • Monthly = Debt/Months • พรบ/ทะเบียน ช่องว่างเหมาะสม • ดาวน์ ช่องว่างเหมาะสม • ออกรถได้ = ดาวน์+พรบ = ผลลัพธ์")
