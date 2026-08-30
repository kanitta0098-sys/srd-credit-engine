import streamlit as st
import os, io, pandas as pd, math, pathlib
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
st.set_page_config(page_title="SRD Credit Engine Hybrid v1.9", layout="wide", page_icon="🏍️")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;600;700;800&display=swap');
html, body, [class*="css"] { font-family:'Sarabun', sans-serif !important; }
.stApp { background:#0F172A !important; color:#E2E8F0 !important; }
.moto-card { background:#1E293B !important; border:2px solid #334155 !important; border-radius:16px; padding:14px 16px; margin-bottom:12px; }
.yellow-summary { background:linear-gradient(135deg,#FBBF24,#F59E0B) !important; border-radius:12px; padding:12px 14px; color:#000 !important; font-weight:800; border:2px solid #F59E0B; }
.block-container { max-width:1420px !important; padding-top:1rem !important; }
.tag-red { background:#DC2626 !important; color:white !important; border-radius:6px; padding:2px 8px; font-weight:700; font-size:11px; display:inline-block; margin:2px; }
</style>
""", unsafe_allow_html=True)
def evaluate_fraud_rules(vehicle_type, down_pct, employment_type, shared_contracts_count, dsr_val, gps_consent):
    rule_score=0; flags=[]
    high_risk=["Yamaha - Sport","Honda - รถใหม่","PICKUP_4X4","BIGBIKE_PREMIUM","SPORT"]
    unstable=["ฟรีแลนซ์/รับจ้างทั่วไป","ว่างงาน/ไม่มีงานประจำ","FREELANCE","GENERAL_LABOR","UNEMPLOYED"]
    if (any(x in vehicle_type for x in high_risk) or "Sport" in vehicle_type) and down_pct <=5.0 and employment_type in unstable:
        rule_score+=40; flags.append("⚠️ R_MATCH_RISK_01: เสี่ยงดาวน์แลกเงิน")
    if shared_contracts_count>=1:
        rule_score+=50; flags.append("🚨 R_LINKAGE_02: เครือข่ายนายหน้า/จัดซ้อน")
    if (dsr_val>50.0 or down_pct<10.0) and not gps_consent:
        rule_score+=20; flags.append("⚠️ R_HIGH_DSR_NO_TRACKING: DSR>50% หรือดาวน์<10% แต่ไม่มี GPS PDPA")
    if rule_score>=80: verdict="⛔ AUTO REJECT"
    elif rule_score>=50: verdict="🟠 MANUAL REVIEW"
    else: verdict="🟢 AUTO PASS"
    return rule_score, flags, verdict
@st.cache_data
def load_price_backup():
    for cp in ["/mnt/data/price_backup_all_models.csv","/mnt/data/ราคารถทั้งหมด_backup.csv","price_backup_all_models.csv"]:
        if os.path.exists(cp):
            try:
                return pd.read_csv(cp, encoding='utf-8')
            except:
                try:
                    return pd.read_csv(cp, encoding='utf-8-sig')
                except: pass
    return pd.DataFrame({"รุ่นรถ":["ฟาซซิโอ้ SMK","ฟาซซิโอ้ Lite","CLICK 160"],"รหัสรถ":["BKF700","BKFB00","CL160"],"ยอดจัด":[54600,53200,68900],"ดอกเบี้ยต่อเดือน":[0.015,0.015,0.016],"%ดาวน์":[0,0,5],"ราคาดาวน์":[0,0,3445],"ทะเบียน พรบ ประกัน":[1000,1000,1200],"ค่าใช้จ่ายออกรถ":[1000,1000,4645],"ผ่อน12":[5369,5232,0],"ผ่อน18":[3853,3754,0],"ผ่อน24":[3094,3015,0],"ผ่อน30":[2639,2572,0],"ผ่อน36":[2336,2276,0],"ผ่อน48":[1957,1907,0]})
HISTORY_FILE="srd_credit_assessment_history.csv"
def save_record(rec):
    df=pd.DataFrame([rec])
    if not os.path.exists(HISTORY_FILE): df.to_csv(HISTORY_FILE, index=False, encoding='utf-8-sig')
    else: df.to_csv(HISTORY_FILE, mode='a', header=False, index=False, encoding='utf-8-sig')
with st.sidebar:
    st.markdown("### 🏍️ SRD Credit Engine\n**Hybrid v1.9**")
    st.caption("ธีมดำ #0F172A + Field Length Optimized")
    api_key_input=st.text_input("GEMINI API Key", value=st.secrets.get("GEMINI_API_KEY","") if hasattr(st,'secrets') else "", type="password")
    selected_model=None; usable=[]
    if api_key_input:
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key_input.strip())
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    usable.append(m.name.replace("models/",""))
            if usable:
                selected_model=st.selectbox("🤖 โมเดล AI", usable, index=0)
                st.success(f"✅ {selected_model}")
        except Exception as e: st.error(str(e))
    df_price=load_price_backup()
    st.caption(f"📂 Price-Backup: {len(df_price)} รุ่น")
    st.dataframe(df_price[["รุ่นรถ","ยอดจัด","ราคาดาวน์"]].head(10), height=200)
    if st.button("🔄 รีเซ็ตฟอร์มว่าง", use_container_width=True):
        st.session_state.clear(); st.rerun()
    if os.path.exists(HISTORY_FILE):
        dfh=pd.read_csv(HISTORY_FILE, encoding='utf-8-sig')
        st.caption(f"💾 Data Log: {len(dfh)}")
        st.download_button("📥 ดาวน์โหลด CSV", dfh.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig'), file_name=f"SRD_Hybrid_v19_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv")
st.markdown("""<div class="moto-card" style="display:flex;justify-content:space-between;align-items:center;background:linear-gradient(135deg,#0F172A,#1E293B) !important;"><div><div style="font-size:28px;font-weight:800;color:#FFF;">🏍️ SRD Credit Engine</div><div style="font-size:12px;color:#38BDF8;">Hybrid v1.9 • Field Length Optimized • Price-Backup-All-Models • ยอดจัด auto • Term 12/18/24/30/36/48/55/62 แก้ไขได้</div></div><div><span style="background:#065F46;color:#6EE7B7;border-radius:20px;padding:6px 12px;font-size:12px;">● ONLINE</span> <span style="background:#1E3A8A;color:#93C5FD;border-radius:20px;padding:6px 12px;font-size:12px;">v1.9 Hybrid</span></div></div>""", unsafe_allow_html=True)
price_df=load_price_backup()
model_list=price_df["รุ่นรถ"].astype(str).tolist()
price_dict={row["รุ่นรถ"]: row for _, row in price_df.iterrows()}
st.markdown('<div class="moto-card">', unsafe_allow_html=True)
st.subheader("🏍️ ข้อมูลรถและคำนวณค่างวด Flat Rate")
st.caption("ยี่ห้อ/รุ่น ดึงจาก Price-Backup-All-Models • ยอดจัด = ราคาเงินสด - ดาวน์ (auto) • Term แก้ไขได้ 12/18/24/30/36/48/55/62")
r1c1, r1c2, r1c3, r1c4 = st.columns([0.55, 0.15, 0.14, 0.16])
with r1c1:
    brand_model=st.selectbox("ยี่ห้อ/รุ่น (ดึงจาก Price-Backup-All-Models)", options=["[ว่าง] เลือกรุ่นรถ"]+model_list, index=0, key="brand_v19")
    selected_row=price_dict.get(brand_model) if brand_model in price_dict else None
with r1c2:
    code_auto=selected_row["รหัสรถ"] if selected_row is not None else ""
    st.text_input("รหัสรถ", value=str(code_auto), disabled=True, key="code_v19")
with r1c3:
    flat_default=float(selected_row["ดอกเบี้ยต่อเดือน"]*100) if selected_row is not None and pd.notna(selected_row["ดอกเบี้ยต่อเดือน"]) else 0.0
    flat_rate=st.number_input("Flat % /เดือน", value=flat_default, step=0.05, format="%.3f", key="flat_v19")
with r1c4:
    term_options=[12,18,24,30,36,48,55,62]
    term_choice=st.selectbox("Term เดือน (แก้ไขได้)", options=term_options, index=4, key="term_select_v19")
    custom_term=st.checkbox("✏️ กำหนดเอง", key="custom_term_check_v19")
    if custom_term:
        term=st.number_input("Term กำหนดเอง", min_value=6, max_value=84, value=term_choice, step=1, key="term_custom_v19")
    else:
        term=term_choice
r2c1, r2c2, r2c3, r2c4 = st.columns(4)
with r2c1:
    cash_default=float(selected_row["ยอดจัด"]+selected_row["ราคาดาวน์"]) if selected_row is not None and pd.notna(selected_row["ยอดจัด"]) else 0.0
    cash_price=st.number_input("ราคาเงินสด", value=cash_default, step=100.0, key="cash_v19")
with r2c2:
    down_default=float(selected_row["ราคาดาวน์"]) if selected_row is not None and pd.notna(selected_row["ราคาดาวน์"]) else 0.0
    down_payment=st.number_input("ดาวน์", value=down_default, step=100.0, key="down_v19")
with r2c3:
    financing_auto=cash_price-down_payment if cash_price>0 else 0.0
    financing=financing_auto
    st.number_input("ยอดจัด = เงินสด - ดาวน์ (auto)", value=financing_auto, disabled=True, key="fin_auto_v19")
with r2c4:
    reg_default=float(selected_row["ทะเบียน พรบ ประกัน"]) if selected_row is not None and pd.notna(selected_row["ทะเบียน พรบ ประกัน"]) else 0.0
    reg_fee=st.number_input("ทะเบียน/พรบ/ประกัน/อื่นๆ", value=reg_default, step=100.0, key="reg_v19")
r3c1, r3c2, r3c3 = st.columns([0.33,0.33,0.34])
with r3c1:
    monthly_editable=st.number_input("Monthly ⭐ แก้ได้เพื่อปัดขึ้น/ลง", value=0.0, step=1.0, key="monthly_v19")
with r3c2:
    total_debt_editable=st.number_input("Total Debt ✏️ แก้ได้", value=0.0, step=100.0, key="debt_v19")
with r3c3:
    total_now=reg_fee+down_payment
    cost_default=float(selected_row["ค่าใช้จ่ายออกรถ"]) if selected_row is not None and pd.notna(selected_row["ค่าใช้จ่ายออกรถ"]) else total_now
    st.number_input("ค่าใช้จ่ายออกรถ auto", value=cost_default if selected_row is not None else total_now, disabled=True, key="cost_auto_v19")
vehicle_type=st.selectbox("ประเภทรถสำหรับ Rule Engine", ["Honda - รถใหม่","Yamaha - Sport","PICKUP_4X4","BIGBIKE_PREMIUM","SCOOTER_FAMILY","Auto"], key="veh_v19")
if financing>0 and flat_rate>0:
    interest_total=financing*(flat_rate/100)*term
    total_debt_calc=financing+interest_total
    monthly_calc=total_debt_calc/term if term else 0
else:
    interest_total=0; total_debt_calc=total_debt_editable; monthly_calc=monthly_editable
monthly_final=monthly_editable if monthly_editable>0 else monthly_calc
total_debt_final=total_debt_editable if total_debt_editable>0 else total_debt_calc
if monthly_editable>0 and total_debt_editable==0 and term>0:
    total_debt_final=monthly_editable*term
down_pct=(down_payment/cash_price*100) if cash_price>0 else 0
if selected_row is not None:
    col_name=f"ผ่อน{term}"
    if col_name in price_df.columns and pd.notna(selected_row.get(col_name, 0)):
        csv_monthly=float(selected_row[col_name])
        st.info(f"💡 Flat Rate: ยอดจัด {financing:,.0f} × {flat_rate:.3f}% × {term} = ดอกเบี้ย {interest_total:,.0f} | ยอดหนี้ {total_debt_final:,.0f} | ค่างวด {monthly_final:,.2f} | Price-Backup งวด {term} = {csv_monthly:,.0f}")
    else:
        st.info(f"💡 Flat Rate: ยอดจัด {financing:,.0f} × {flat_rate:.3f}% × {term} = ดอกเบี้ย {interest_total:,.0f} | ยอดหนี้ {total_debt_final:,.0f} | ค่างวด {monthly_final:,.2f} | ดาวน์ {down_pct:.1f}%")
else:
    st.info(f"💡 Flat Rate: ยอดจัด {financing:,.0f} × {flat_rate:.3f}% × {term} = ดอกเบี้ย {interest_total:,.0f} | ยอดหนี้ {total_debt_final:,.0f} | ค่างวด {monthly_final:,.2f}")
st.markdown(f'<div class="yellow-summary">Initial Payment: {down_payment:,.0f} + {reg_fee:,.0f} = <span style="font-size:20px;">{total_now:,.0f}</span> | ยอดจัด auto = {cash_price:,.0f} - {down_payment:,.0f} = {financing:,.0f}</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)
st.markdown('<div class="moto-card">', unsafe_allow_html=True)
st.subheader("🏍️ ข้อมูลผู้เช่าซื้อ")
c1, c2, c3 = st.columns([0.4,0.4,0.2])
with c1: f_name=st.text_input("ชื่อ", value="", placeholder="[ว่าง] สมชาย", key="fname_v19")
with c2: l_name=st.text_input("สกุล", value="", placeholder="[ว่าง] ใจดี", key="lname_v19")
with c3: age=st.number_input("อายุ", min_value=0, max_value=80, value=0, key="age_v19")
c1, c2, c3 = st.columns([0.35,0.35,0.3])
with c1: job=st.text_input("อาชีพ", value="", placeholder="[ว่าง]", key="job_v19")
with c2: sup=st.text_input("หัวหน้างาน", value="", placeholder="[ว่าง]", key="sup_v19")
with c3: phone=st.text_input("เบอร์โทร", value="", placeholder="[ว่าง] 081-xxx-xxxx", key="phone_v19")
c1, c2, c3, c4 = st.columns(4)
with c1: residence=st.selectbox("ที่พัก", ["[ว่าง]","บ้านตนเอง/ปลอดภาระ","บ้านตนเอง/ติดผ่อน","บ้านเช่า/หอพัก","บ้านญาติ"], key="res_v19")
with c2: salary=st.number_input("เงินเดือน", value=0, step=500, key="sal_v19")
with c3: extra=st.number_input("รายได้เสริม", value=0, step=500, key="extra_v19")
with c4: emp_type=st.selectbox("ประเภทอาชีพ Rule", ["พนักงานประจำ","เจ้าของกิจการ","ฟรีแลนซ์/รับจ้างทั่วไป","ว่างงาน/ไม่มีงานประจำ"], key="emp_v19")
c1, c2 = st.columns(2)
with c1: debt=st.number_input("หนี้เดิม/เดือน", value=0, step=100, key="debt_v19")
with c2: living=st.number_input("ค่าใช้ชีวิต/เดือน", value=0, step=500, key="live_v19")
total_inc=salary+extra
total_bur=debt+living+monthly_final
dsr=(total_bur/total_inc*100) if total_inc>0 else 0
m1,m2,m3=st.columns(3)
with m1: st.metric("รายได้รวม", f"{total_inc:,.0f}")
with m2: st.metric("ภาระรวม", f"{total_bur:,.0f}")
with m3: st.metric("DSR %", f"{dsr:.1f}%")
st.markdown('</div>', unsafe_allow_html=True)
st.markdown('<div class="moto-card">', unsafe_allow_html=True)
st.subheader("🏍️ บุคคลอ้างอิง")
r1,r2=st.columns(2)
with r1:
    st.markdown("**อ้างอิง 1**")
    c1,c2,c3=st.columns([0.5,0.25,0.25])
    with c1: ref1_name=st.text_input("ชื่อ-สกุล 1", value="", placeholder="[ว่าง]", key="ref1_name_v19", label_visibility="collapsed")
    with c2: ref1_phone=st.text_input("เบอร์ 1", value="", placeholder="เบอร์", key="ref1_phone_v19", label_visibility="collapsed")
    with c3: ref1_rel=st.text_input("สัมพันธ์ 1", value="", placeholder="พี่ชาย", key="ref1_rel_v19", label_visibility="collapsed")
with r2:
    st.markdown("**อ้างอิง 2**")
    c1,c2,c3=st.columns([0.5,0.25,0.25])
    with c1: ref2_name=st.text_input("ชื่อ-สกุล 2", value="", placeholder="[ว่าง]", key="ref2_name_v19", label_visibility="collapsed")
    with c2: ref2_phone=st.text_input("เบอร์ 2", value="", placeholder="เบอร์", key="ref2_phone_v19", label_visibility="collapsed")
    with c3: ref2_rel=st.text_input("สัมพันธ์ 2", value="", placeholder="เพื่อน", key="ref2_rel_v19", label_visibility="collapsed")
st.markdown('</div>', unsafe_allow_html=True)
st.markdown('<div class="moto-card">', unsafe_allow_html=True)
st.subheader("🏍️ คู่สมรส")
spouse_choice=st.radio("สถานะคู่สมรส", ["1 ไม่มีคู่สมรส","2 มีคู่สมรส"], horizontal=True, key="sp_choice_v19")
spouse_summary="ไม่มีคู่สมรส"; sp_name=""; sp_age=0; sp_year=0; sp_child=0; sp_income=0; sp_job=""
if spouse_choice=="2 มีคู่สมรส":
    c1,c2,c3=st.columns([0.4,0.2,0.4])
    with c1: sp_name=st.text_input("1. ชื่อ-สกุล คู่สมรส", value="", placeholder="[ว่าง]", key="sp_name_v19")
    with c2: sp_age=st.number_input("2. อายุ", value=0, key="sp_age_v19")
    with c3: sp_job=st.text_input("6. อาชีพ", value="", placeholder="[ว่าง]", key="sp_job_v19")
    c1,c2,c3=st.columns(3)
    with c1: sp_year=st.number_input("3. จำนวนปีที่สมรส", value=0, key="sp_year_v19")
    with c2: sp_child=st.number_input("4. มีบุตรกี่คน", value=0, key="sp_child_v19")
    with c3: sp_income=st.number_input("5. รายได้คู่สมรส", value=0, step=500, key="sp_inc_v19")
    spouse_summary=f"{sp_name} อายุ {sp_age} สมรส {sp_year} ปี บุตร {sp_child} คน รายได้ {sp_income:,.0f} อาชีพ {sp_job}"
st.markdown('</div>', unsafe_allow_html=True)
st.markdown('<div class="moto-card">', unsafe_allow_html=True)
st.subheader("🏍️ ผู้ค้ำประกัน")
guar_choice=st.radio("สถานะผู้ค้ำประกัน", ["1 ไม่มีผู้ค้ำประกัน","2 มีผู้ค้ำประกัน"], horizontal=True, key="guar_choice_v19")
g_text="ไม่มีผู้ค้ำประกัน"; g_name=""; g_age=0; g_job=""; g_income=0; g_phone=""
if guar_choice=="2 มีผู้ค้ำประกัน":
    c1,c2,c3=st.columns([0.4,0.2,0.4])
    with c1: g_name=st.text_input("1. ชื่อ-สกุล ผู้ค้ำ", value="", placeholder="[ว่าง]", key="g_name_v19")
    with c2: g_age=st.number_input("2. อายุ", value=0, key="g_age_v19")
    with c3: g_phone=st.text_input("5. เบอร์โทร", value="", placeholder="[ว่าง]", key="g_phone_v19")
    c1,c2=st.columns(2)
    with c1: g_job=st.text_input("3. อาชีพผู้ค้ำประกัน", value="", placeholder="[ว่าง]", key="g_job_v19")
    with c2: g_income=st.number_input("4. รายได้ผู้ค้ำประกัน", value=0, step=1000, key="g_inc_v19")
    g_text=f"{g_name} อายุ {g_age} อาชีพ {g_job} รายได้ {g_income:,.0f} เบอร์ {g_phone}"
st.markdown('</div>', unsafe_allow_html=True)
st.markdown('<div class="moto-card">', unsafe_allow_html=True)
st.subheader("🏍️ เช็คลิสต์เอกสาร 6 รายการ")
d1=st.checkbox("1. สำเนาบัตรประชาชน", key="doc1_v19")
d2=st.checkbox("2. ทะเบียนบ้าน", key="doc2_v19")
d3=st.checkbox("3. สลิปเงินเดือน 3 เดือน", key="doc3_v19")
d4=st.checkbox("4. สเตทเม้นท์ 6 เดือน", key="doc4_v19")
d5=st.checkbox("5. ใบจดทะเบียนการค้า", key="doc5_v19")
d6=st.checkbox("6. รูปถ่ายที่พัก / หมุด Google Maps", key="doc6_v19")
attached=[]; missing=[]
for n,c in [("บัตร ปชช",d1),("ทะเบียนบ้าน",d2),("สลิป 3 เดือน",d3),("สเตทเม้นท์ 6 เดือน",d4),("ใบจดทะเบียนการค้า",d5),("รูปที่พัก",d6)]:
    if c: attached.append(n)
    else: missing.append(n)
if attached: st.markdown(" ".join([f"<span class='tag-red'>{a} x</span>" for a in attached]), unsafe_allow_html=True)
uploaded=st.file_uploader("📸 Upload เอกสาร", type=["png","jpg","jpeg","heic","heif","webp"], accept_multiple_files=True, key="upload_v19")
if uploaded:
    bad=[f.name for f in uploaded if f.name.lower().endswith(('.dng','.raw','.arw','.cr2','.cr3','.nef','.orf','.rw2','.raf'))]
    if bad:
        st.error(f"❌ พบไฟล์ RAW/DNG: {', '.join(bad)}")
        uploaded=[f for f in uploaded if not f.name.lower().endswith(('.dng','.raw','.arw','.cr2','.cr3','.nef','.orf','.rw2','.raf'))]
cam=st.camera_input("📷 Take Photo", key="camera_v19")
gps_consent=st.checkbox("✅ ยินยอมให้ติดตามตำแหน่ง (PDPA Compliant)", value=False, key="gps_v19")
workplace=st.text_input("📌 พิกัด Google Maps", value="", placeholder="[ว่าง] https://maps.app.goo.gl/...", key="workplace_v19")
story=st.text_area("🏪 บันทึกบริบทหน้าร้าน", value="", placeholder="[ว่าง]", key="story_v19")
shared_contracts=st.number_input("จำนวนสัญญาที่เชื่อมโยงใน 90 วัน (เครือข่ายนายหน้า)", min_value=0, value=0, key="shared_v19")
st.markdown('</div>', unsafe_allow_html=True)
st.markdown('<div class="moto-card" style="border:2px solid #8B5CF6 !important;">', unsafe_allow_html=True)
st.subheader("🏍️ วิเคราะห์ 13 โมดูลด้วย Ai")
r_score, r_flags, r_verdict = evaluate_fraud_rules(vehicle_type, down_pct, emp_type, shared_contracts, dsr, gps_consent)
colA,colB,colC=st.columns(3)
with colA: st.metric("DSR Meter", f"{dsr:.1f}%"); st.progress(min(1.0, dsr/100) if dsr>0 else 0.0)
with colB: risk_score=int(min(100, dsr*1.2)) if dsr>0 else 0; st.metric("Risk Score", f"{risk_score}/100"); st.progress(risk_score/100)
with colC: st.metric(f"Fraud Score - {r_verdict}", f"{r_score}"); 
for f in r_flags: st.error(f)
st.markdown("**Backend Engine:** Rule Engine `evaluate_fraud_rules()` • Prompt AI 10 หัวข้อ • `load_price_backup()` • PDPA/GPS • Data Log ละเอียด")
if uploaded or cam or st.checkbox("✅ ทดสอบโดยไม่ต้องอัปโหลด", key="test_no_upload_v19"):
    if st.button("🚀 รัน SRD Credit Investigation Engine 13 Modules เต็มระบบ v1.3", type="primary", use_container_width=True, key="run_ai_v19"):
        if not api_key_input or not selected_model:
            st.error("กรุณากรอก API Key")
        else:
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key_input.strip())
                imgs=[]
                if uploaded:
                    for f in uploaded: imgs.append(_compress_mobile(Image.open(f)))
                if cam: imgs.append(_compress_mobile(Image.open(cam)))
                full_prompt = f"""
# SRD CREDIT INVESTIGATION ENGINE Hybrid v1.9 Field Length Optimized
## ROLE: Head of Credit Risk & Fraud Intelligence
[ข้อมูลรถ Flat Rate - Price-Backup-All-Models] รุ่น {brand_model} รหัส {code_auto} ราคา {cash_price} ดาวน์ {down_payment} ({down_pct:.1f}%) ยอดจัด auto {financing} = {cash_price} - {down_payment} Flat {flat_rate:.3f}% Term {term} เดือน (12/18/24/30/36/48/55/62) ค่างวด {monthly_final} ยอดหนี้รวม {total_debt_final} รวมจ่ายวันออกรถ {total_now}
[ผู้กู้] {f_name} {l_name} อายุ {age} อาชีพ {job} หัวหน้างาน {sup} เบอร์ {phone} ที่พัก {residence} เงินเดือน {salary} เสริม {extra} รายได้รวม {total_inc} ภาระรวม {total_bur} DSR {dsr:.1f}% Rule {emp_type}
[พิกัด] {workplace} GPS {gps_consent} Rule {r_score} {r_verdict} Flags {r_flags} Shared {shared_contracts}
[คู่สมรส] {spouse_summary}
[ผู้ค้ำ] {g_text}
[อ้างอิง] {ref1_name} ({ref1_rel}) / {ref2_name} ({ref2_rel})
[เอกสาร] แนบ {', '.join(attached)} ขาด {', '.join(missing)}
[บริบท] {story}
[Price-Backup] {selected_row.to_dict() if selected_row is not None else 'ไม่ได้เลือกรุ่น'}

### REQUIRED OUTPUT 10 หัวข้อ
## 1. CUSTOMER & HOUSEHOLD PROFILE
## 2. IDENTITY & WORKPLACE VERIFICATION
## 3. VERIFIED FACTS vs UNVERIFIED CLAIMS
## 4. MONEY FLOW & CASH FLOW REALITY
## 5. FRAUD, GAMBLING & ASSET RISK CHECK
## 6. GUARANTOR & SPOUSE MITIGATION POWER
## 7. CONTRADICTION TABLE
## 8. RISK SCORING & FINAL DECISION
## 9. 30-SECOND SOFT INTERVIEW
## 10. SUMMARY RECOMMENDATION FOR SALES
"""
                with st.spinner(f"AI ({selected_model}) วิเคราะห์ 13 โมดูล + Term {term} เดือน..."):
                    model_ai=genai.GenerativeModel(selected_model)
                    if imgs: resp=model_ai.generate_content([full_prompt]+imgs)
                    else: resp=model_ai.generate_content(full_prompt)
                    save_record({"Timestamp":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"BrandModel":brand_model,"Code":code_auto,"Cash":cash_price,"Down":down_payment,"DownPct":f"{down_pct:.1f}%","Financing_auto":financing,"Flat":flat_rate,"Term":term,"Monthly":monthly_final,"TotalDebt":total_debt_final,"TotalNow":total_now,"Applicant":f"{f_name} {l_name}","Phone":phone,"DSR":f"{dsr:.1f}%","Spouse":spouse_summary,"Guarantor":g_text,"RuleScore":r_score,"RuleVerdict":r_verdict,"Docs":", ".join(attached),"GPS":workplace,"Story":story})
                    st.success("💾 บันทึก Data Log ละเอียดแล้ว - Hybrid v1.9")
                    st.markdown(f"**Rule Engine:** {r_verdict} Score {r_score} | Term {term} เดือน | ยอดจัด auto {financing:,.0f} = {cash_price:,.0f} - {down_payment:,.0f}")
                    st.markdown(resp.text)
            except Exception as e:
                st.error(f"Error: {e}")
else:
    st.info("อัปโหลดภาพเอกสารหรือถ่ายภาพก่อนรัน AI")
st.markdown('</div>', unsafe_allow_html=True)
st.caption("Hybrid v1.9 • Field Length Optimized: ยี่ห้อ/รุ่น 55% รหัสรถ 15% Flat% 14% Term 16% • ยี่ห้อ/รุ่น ดึงจาก Price-Backup-All-Models • ยอดจัด auto = ราคาเงินสด - ดาวน์ • Term แก้ไขได้ 12/18/24/30/36/48/55/62 • ธีมดำ #0F172A")
