
import streamlit as st
import os, io, pandas as pd, math
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

st.set_page_config(page_title="SRD Credit Engine Hybrid v2.0", layout="wide", page_icon="🏍️")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;600;700;800&display=swap');
html, body, [class*="css"] { font-family:'Sarabun', sans-serif !important; }
.stApp { background:#0F172A !important; color:#E2E8F0 !important; }
.moto-card { background:#1E293B !important; border:2px solid #334155 !important; border-radius:16px; padding:14px 16px; margin-bottom:12px; }
.yellow-summary { background:linear-gradient(135deg,#FBBF24,#F59E0B) !important; border-radius:12px; padding:12px 14px; color:#000 !important; font-weight:800; border:2px solid #F59E0B; }
.blue-info { background:#1E3A8A !important; border:2px solid #3B82F6 !important; border-radius:10px; padding:10px; color:#DBEAFE !important; }
.tag-red { background:#DC2626 !important; color:white !important; border-radius:6px; padding:2px 8px; font-weight:700; font-size:11px; display:inline-block; margin:2px; }
.tag-green { background:#065F46 !important; color:#6EE7B7 !important; border-radius:6px; padding:2px 8px; font-weight:700; font-size:11px; display:inline-block; margin:2px; }
.block-container { max-width:1420px !important; padding-top:1rem !important; }
</style>
""", unsafe_allow_html=True)

def evaluate_fraud_rules(vehicle_type, down_pct, employment_type, shared_contracts_count, dsr_val, gps_consent):
    rule_score=0; flags=[]
    high_risk=["Yamaha - Sport","Honda - รถใหม่","PICKUP_4X4","BIGBIKE_PREMIUM","SPORT","R15","WR155R","Aerox"]
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
def load_price_backup_complete():
    # 1. ลองหาไฟล์ Master ก่อน - Motorcycle-Price-All-Models.xlsx
    master_paths=[
        "/mnt/data/Motorcycle-Price-All-Models.xlsx",
        "Motorcycle-Price-All-Models.xlsx",
        "/mount/src/srd-credit-engine/Motorcycle-Price-All-Models.xlsx",
        "/mnt/data/motorcycle_price_all_models.xlsx",
        "/mnt/data/data/28-8-69_Dynamic_Formulas_Categories.xlsx"
    ]
    df_final=None
    for mp in master_paths:
        if os.path.exists(mp):
            try:
                # อ่านแบบ header=1 (แถวที่ 2 เป็นหัวตารางจริง)
                df=pd.read_excel(mp, sheet_name=0, header=1)
                # ต้องมีคอลัมน์ รุ่นรถ
                if 'รุ่นรถ' in df.columns:
                    # Forward Fill ชื่อรุ่นที่ว่าง (เพราะ 1 รุ่นมี 4 แถวตาม %ดาวน์)
                    df['รุ่นรถ']=df['รุ่นรถ'].ffill()
                    df['รหัสรถ']=df['รหัสรถ'].ffill()
                    df['ราคาจัด']=df['ราคาจัด'].ffill()
                    # คอลัมน์ดอกเบี้ยอาจชื่อ ดอกเบี้ย\n(ต่อเดือน)
                    interest_col=[c for c in df.columns if 'ดอกเบี้ย' in str(c)][0]
                    df[interest_col]=df[interest_col].ffill()
                    # กรองเอาเฉพาะ %ดาวน์ = 0% เป็น Base Price
                    df_base=df[df['%ดาวน์']==0].copy()
                    # ลบแถวที่เป็นหัวตารางซ้ำ
                    df_base=df_base[~df_base['รุ่นรถ'].astype(str).str.contains('รุ่นรถ|ตารางโปรโมชัน', na=False)]
                    df_base['รุ่นรถ']=df_base['รุ่นรถ'].astype(str).str.strip()
                    df_base=df_base[df_base['รุ่นรถ']!='nan']
                    df_base=df_base.drop_duplicates(subset=['รุ่นรถ','รหัสรถ'], keep='first')
                    # Rename ให้เป็นมาตรฐานเดียวกับ CSV
                    rename_map={
                        'ราคาจัด':'ยอดจัด',
                        interest_col:'ดอกเบี้ยต่อเดือน',
                        'ดาวน์':'ราคาดาวน์',
                        'ค่าจด/พรบ.':'ทะเบียน พรบ ประกัน',
                        'รวมออกรถ':'ค่าใช้จ่ายออกรถ'
                    }
                    df_base=df_base.rename(columns=rename_map)
                    # เลือกเฉพาะคอลัมน์ที่ต้องการ
                    keep_cols=['รุ่นรถ','รหัสรถ','ยอดจัด','ดอกเบี้ยต่อเดือน','%ดาวน์','ราคาดาวน์','ทะเบียน พรบ ประกัน','ค่าใช้จ่ายออกรถ']
                    # เพิ่มคอลัมน์ผ่อนถ้ามี
                    for c in ['ตารางผ่อน','Unnamed: 9','Unnamed: 10','Unnamed: 11','Unnamed: 12','Unnamed: 13']:
                        if c in df_base.columns:
                            keep_cols.append(c)
                    df_final=df_base
                    break
            except Exception as e:
                st.warning(f"อ่าน {mp} ไม่ได้: {e}")
                continue
    # Fallback CSV ถ้าไม่มี Excel
    if df_final is None or df_final.empty:
        for cp in ["/mnt/data/price_backup_all_models.csv","/mnt/data/ราคารถทั้งหมด_backup.csv","price_backup_all_models.csv"]:
            if os.path.exists(cp):
                try:
                    df=pd.read_csv(cp, encoding='utf-8')
                    df_final=df
                    break
                except:
                    try:
                        df=pd.read_csv(cp, encoding='utf-8-sig')
                        df_final=df
                        break
                    except: pass
    if df_final is None or df_final.empty:
        df_final=pd.DataFrame({
            "รุ่นรถ":["ฟาซซิโอ้ SMK","ฟาซซิโอ้ Lite","Aerox 155 2026"],
            "รหัสรถ":["BKF700","BKFB00","BWR100"],
            "ยอดจัด":[54600,53200,85900],
            "ดอกเบี้ยต่อเดือน":[0.015,0.015,0.011],
            "%ดาวน์":[0,0,0],
            "ราคาดาวน์":[0,0,0],
            "ทะเบียน พรบ ประกัน":[1000,1000,1000],
            "ค่าใช้จ่ายออกรถ":[1000,1000,1000]
        })
    return df_final

HISTORY_FILE="srd_credit_assessment_history.csv"
def save_record(rec):
    df=pd.DataFrame([rec])
    if not os.path.exists(HISTORY_FILE): df.to_csv(HISTORY_FILE, index=False, encoding='utf-8-sig')
    else: df.to_csv(HISTORY_FILE, mode='a', header=False, index=False, encoding='utf-8-sig')

with st.sidebar:
    st.markdown("### 🏍️ SRD Credit Engine\n**Hybrid v2.0**")
    st.caption("ดึงจาก Motorcycle-Price-All-Models.xlsx • ยอดจัด auto • ดอกเบี้ย Yamaha auto")
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
    df_price=load_price_backup_complete()
    st.caption(f"📂 Motorcycle-Price-All-Models: {len(df_price)} รุ่น (ครบ)")
    if not df_price.empty:
        st.dataframe(df_price[["รุ่นรถ","ยอดจัด","ดอกเบี้ยต่อเดือน","ราคาดาวน์"]].head(15), height=300)
        # แสดงดอกเบี้ย Yamaha แยก
        st.markdown("**💡 ดอกเบี้ย Yamaha auto:**")
        yamaha_df=df_price[df_price["รุ่นรถ"].astype(str).str.contains("ฟาซซิโอ้|แกรนด์|เอ็นแม็ก|Aerox|ฟินน์|WR|PG-1|R15", na=False)]
        if not yamaha_df.empty:
            st.dataframe(yamaha_df[["รุ่นรถ","ดอกเบี้ยต่อเดือน"]].head(10), height=150)
    if st.button("🔄 รีเซ็ตฟอร์มว่าง", use_container_width=True):
        st.session_state.clear(); st.rerun()
    if os.path.exists(HISTORY_FILE):
        dfh=pd.read_csv(HISTORY_FILE, encoding='utf-8-sig')
        st.caption(f"💾 Data Log: {len(dfh)}")
        st.download_button("📥 ดาวน์โหลด CSV", dfh.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig'), file_name=f"SRD_Hybrid_v20_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv")

st.markdown("""<div class="moto-card" style="display:flex;justify-content:space-between;align-items:center;background:linear-gradient(135deg,#0F172A,#1E293B) !important;"><div><div style="font-size:28px;font-weight:800;color:#FFF;">🏍️ SRD Credit Engine</div><div style="font-size:12px;color:#38BDF8;">Hybrid v2.0 • ดึงจาก Motorcycle-Price-All-Models.xlsx • ยอดจัด auto = ราคาเงินสด - ดาวน์ • ดอกเบี้ย Yamaha auto ไม่ต้องจำ</div></div><div><span style="background:#065F46;color:#6EE7B7;border-radius:20px;padding:6px 12px;font-size:12px;">● ONLINE</span> <span style="background:#1E3A8A;color:#93C5FD;border-radius:20px;padding:6px 12px;font-size:12px;">v2.0 Yamaha Auto</span></div></div>""", unsafe_allow_html=True)

price_df=load_price_backup_complete()
model_list=price_df["รุ่นรถ"].astype(str).tolist()
price_dict={row["รุ่นรถ"]: row for _, row in price_df.iterrows()}

st.markdown('<div class="moto-card">', unsafe_allow_html=True)
st.subheader("🏍️ ข้อมูลรถและคำนวณค่างวด Flat Rate")
st.caption("ยี่ห้อ/รุ่น ดึงจาก Motorcycle-Price-All-Models.xlsx • ยอดจัด auto = ราคาเงินสด - ดาวน์ • ดอกเบี้ย Yamaha auto ไม่ต้องจำ")

r1c1, r1c2, r1c3, r1c4 = st.columns([0.50, 0.15, 0.15, 0.20])
with r1c1:
    brand_model=st.selectbox("ยี่ห้อ/รุ่น (ดึงจาก Motorcycle-Price-All-Models.xlsx ครบทุกยี่ห้อ)", options=["[ว่าง] เลือกรุ่นรถ"]+model_list, index=0, key="brand_v20")
    selected_row=price_dict.get(brand_model) if brand_model in price_dict else None
with r1c2:
    code_auto=selected_row["รหัสรถ"] if selected_row is not None else ""
    st.text_input("รหัสรถ", value=str(code_auto), disabled=True, key="code_v20")
with r1c3:
    flat_default=float(selected_row["ดอกเบี้ยต่อเดือน"]*100) if selected_row is not None and pd.notna(selected_row["ดอกเบี้ยต่อเดือน"]) else 0.0
    flat_rate=st.number_input("Flat % /เดือน (auto จากไฟล์ Yamaha)", value=flat_default, step=0.05, format="%.3f", key="flat_v20", help="ดึงจาก Motorcycle-Price-All-Models.xlsx อัตโนมัติ - ฝ่ายขายไม่ต้องจำ")
    if selected_row is not None:
        st.markdown(f"<span class='tag-green'>ดอกเบี้ย {flat_default:.3f}% auto</span>", unsafe_allow_html=True)
with r1c4:
    term_options=[12,18,24,30,36,48,55,62]
    term_choice=st.selectbox("Term เดือน (12/18/24/30/36/48/55/62 แก้ไขได้)", options=term_options, index=4, key="term_select_v20")
    custom_term=st.checkbox("✏️ กำหนดเอง 6-84 เดือน", key="custom_term_check_v20")
    if custom_term:
        term=st.number_input("Term กำหนดเอง", min_value=6, max_value=84, value=term_choice, step=1, key="term_custom_v20")
    else:
        term=term_choice

r2c1, r2c2, r2c3, r2c4 = st.columns(4)
with r2c1:
    # ราคาเงินสด auto = ยอดจัด + ราคาดาวน์ (จากไฟล์)
    cash_default=float(selected_row["ยอดจัด"]+selected_row["ราคาดาวน์"]) if selected_row is not None and pd.notna(selected_row["ยอดจัด"]) and pd.notna(selected_row["ราคาดาวน์"]) else 0.0
    cash_price=st.number_input("ราคาเงินสด (auto จากไฟล์)", value=cash_default, step=100.0, key="cash_v20", help="auto = ยอดจัด + ราคาดาวน์ จาก Motorcycle-Price-All-Models.xlsx")
with r2c2:
    down_default=float(selected_row["ราคาดาวน์"]) if selected_row is not None and pd.notna(selected_row["ราคาดาวน์"]) else 0.0
    down_payment=st.number_input("ดาวน์ (auto จากไฟล์)", value=down_default, step=100.0, key="down_v20", help="ดึงจากไฟล์ ถ้าลูกค้าดาวน์เพิ่ม แก้ได้")
with r2c3:
    # ยอดจัด = เงินสด - ดาวน์ (ควรใส่ราคา auto)
    financing_auto=cash_price-down_payment if cash_price>0 else 0.0
    if financing_auto<0:
        st.error("ดาวน์เกินราคาเงินสด!")
        financing_auto=0
    financing=financing_auto
    st.number_input("ยอดจัด = เงินสด - ดาวน์ (auto)", value=financing_auto, disabled=True, key="fin_auto_v20", help="คำนวณ auto ไม่ต้องกรอกเอง")
    st.markdown(f"<span class='tag-green'>auto: {cash_price:,.0f} - {down_payment:,.0f} = {financing_auto:,.0f}</span>", unsafe_allow_html=True)
with r2c4:
    reg_default=float(selected_row["ทะเบียน พรบ ประกัน"]) if selected_row is not None and pd.notna(selected_row["ทะเบียน พรบ ประกัน"]) else 0.0
    reg_fee=st.number_input("ทะเบียน/พรบ/ประกัน/อื่นๆ (auto)", value=reg_default, step=100.0, key="reg_v20")

r3c1, r3c2, r3c3 = st.columns([0.33,0.33,0.34])
with r3c1:
    monthly_editable=st.number_input("Monthly ⭐ แก้ได้เพื่อปัดขึ้น/ลง", value=0.0, step=1.0, key="monthly_edit_v20")
with r3c2:
    total_debt_editable=st.number_input("Total Debt ✏️ แก้ได้", value=0.0, step=100.0, key="total_debt_edit_v20")
with r3c3:
    total_now=reg_fee+down_payment
    cost_default=float(selected_row["ค่าใช้จ่ายออกรถ"]) if selected_row is not None and pd.notna(selected_row["ค่าใช้จ่ายออกรถ"]) else total_now
    st.number_input("ค่าใช้จ่ายออกรถ auto = ดาวน์+ทะเบียน", value=cost_default if selected_row is not None else total_now, disabled=True, key="cost_auto_v20")

vehicle_type=st.selectbox("ประเภทรถสำหรับ Rule Engine", ["Auto (ดึงจากไฟล์)","Honda - รถใหม่","Yamaha - Sport","YAMAHA","SCOOTER_FAMILY","Moped","Sport","PICKUP_4X4"], key="veh_v20")

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

# แสดงเปรียบเทียบกับไฟล์
if selected_row is not None:
    st.markdown(f'<div class="blue-info">💡 <b>ดึงจาก Motorcycle-Price-All-Models.xlsx:</b> รุ่น {brand_model} | ยอดจัด {selected_row["ยอดจัด"]:,.0f} | ดาวน์ {selected_row["ราคาดาวน์"]:,.0f} | ดอกเบี้ย {flat_rate:.3f}% | ทะเบียน {reg_fee:,.0f} | <b>ยอดจัด auto = {cash_price:,.0f} - {down_payment:,.0f} = {financing:,.0f}</b> | ฝ่ายขายไม่ต้องจำดอกเบี้ย Yamaha</div>', unsafe_allow_html=True)
    st.info(f"💡 คำนวณ Flat Rate: ยอดจัด {financing:,.0f} × {flat_rate:.3f}% × {term} = ดอกเบี้ยรวม {interest_total:,.0f} | ยอดหนี้รวม {total_debt_final:,.0f} | ค่างวด {monthly_final:,.2f} | ดาวน์ {down_pct:.1f}%")
else:
    st.info(f"💡 คำนวณ Flat Rate: ยอดจัด {financing:,.0f} × {flat_rate:.3f}% × {term} = ดอกเบี้ยรวม {interest_total:,.0f} | ยอดหนี้รวม {total_debt_final:,.0f} | ค่างวด {monthly_final:,.2f}")

st.markdown(f'<div class="yellow-summary">Initial Payment Summary: ดาวน์ {down_payment:,.0f} + ทะเบียน {reg_fee:,.0f} = <span style="font-size:20px;">{total_now:,.0f}</span> | ยอดจัด auto = ราคาเงินสด - ดาวน์ = {cash_price:,.0f} - {down_payment:,.0f} = {financing:,.0f} | ดอกเบี้ย Yamaha auto {flat_rate:.3f}% ไม่ต้องจำ</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# ข้อมูลผู้เช่าซื้อ - Field Length Optimized
st.markdown('<div class="moto-card">', unsafe_allow_html=True)
st.subheader("🏍️ ข้อมูลผู้เช่าซื้อ")
c1, c2, c3 = st.columns([0.4,0.4,0.2])
with c1: f_name=st.text_input("ชื่อ", value="", placeholder="[ว่าง] สมชาย", key="fname_v20")
with c2: l_name=st.text_input("สกุล", value="", placeholder="[ว่าง] ใจดี", key="lname_v20")
with c3: age=st.number_input("อายุ", min_value=0, max_value=80, value=0, key="age_v20")
c1, c2, c3 = st.columns([0.35,0.35,0.3])
with c1: job=st.text_input("อาชีพ", value="", placeholder="[ว่าง]", key="job_v20")
with c2: sup=st.text_input("หัวหน้างาน", value="", placeholder="[ว่าง]", key="sup_v20")
with c3: phone=st.text_input("เบอร์โทร", value="", placeholder="[ว่าง] 081-xxx-xxxx", key="phone_v20")
c1, c2, c3, c4 = st.columns(4)
with c1: residence=st.selectbox("ที่พัก", ["[ว่าง]","บ้านตนเอง/ปลอดภาระ","บ้านตนเอง/ติดผ่อน","บ้านเช่า/หอพัก","บ้านญาติ"], key="res_v20")
with c2: salary=st.number_input("เงินเดือน", value=0, step=500, key="sal_v20")
with c3: extra=st.number_input("รายได้เสริม", value=0, step=500, key="extra_v20")
with c4: emp_type=st.selectbox("ประเภทอาชีพ Rule", ["พนักงานประจำ","เจ้าของกิจการ","ฟรีแลนซ์/รับจ้างทั่วไป","ว่างงาน/ไม่มีงานประจำ"], key="emp_v20")
c1, c2 = st.columns(2)
with c1: debt_monthly=st.number_input("หนี้เดิม/เดือน", value=0, step=100, key="debt_monthly_v20")
with c2: living=st.number_input("ค่าใช้ชีวิต/เดือน", value=0, step=500, key="live_v20")
total_inc=salary+extra
total_bur=debt_monthly+living+monthly_final
dsr=(total_bur/total_inc*100) if total_inc>0 else 0
m1,m2,m3=st.columns(3)
with m1: st.metric("รายได้รวม", f"{total_inc:,.0f}")
with m2: st.metric("ภาระรวม", f"{total_bur:,.0f}")
with m3: st.metric("DSR %", f"{dsr:.1f}%")
st.markdown('</div>', unsafe_allow_html=True)

# บุคคลอ้างอิง, คู่สมรส, ผู้ค้ำ, เช็คลิสต์ - ย่อให้สั้น
st.markdown('<div class="moto-card">', unsafe_allow_html=True)
st.subheader("🏍️ บุคคลอ้างอิง / คู่สมรส / ผู้ค้ำ")
r1,r2=st.columns(2)
with r1:
    st.markdown("**อ้างอิง 1**")
    c1,c2,c3=st.columns([0.5,0.25,0.25])
    with c1: ref1_name=st.text_input("ชื่อ-สกุล 1", value="", placeholder="[ว่าง]", key="ref1_name_v20", label_visibility="collapsed")
    with c2: ref1_phone=st.text_input("เบอร์ 1", value="", placeholder="เบอร์", key="ref1_phone_v20", label_visibility="collapsed")
    with c3: ref1_rel=st.text_input("สัมพันธ์ 1", value="", placeholder="พี่ชาย", key="ref1_rel_v20", label_visibility="collapsed")
with r2:
    st.markdown("**อ้างอิง 2**")
    c1,c2,c3=st.columns([0.5,0.25,0.25])
    with c1: ref2_name=st.text_input("ชื่อ-สกุล 2", value="", placeholder="[ว่าง]", key="ref2_name_v20", label_visibility="collapsed")
    with c2: ref2_phone=st.text_input("เบอร์ 2", value="", placeholder="เบอร์", key="ref2_phone_v20", label_visibility="collapsed")
    with c3: ref2_rel=st.text_input("สัมพันธ์ 2", value="", placeholder="เพื่อน", key="ref2_rel_v20", label_visibility="collapsed")

spouse_choice=st.radio("สถานะคู่สมรส", ["1 ไม่มีคู่สมรส","2 มีคู่สมรส"], horizontal=True, key="sp_choice_v20")
spouse_summary="ไม่มีคู่สมรส"; sp_name=""; sp_age=0; sp_year=0; sp_child=0; sp_income=0; sp_job=""
if spouse_choice=="2 มีคู่สมรส":
    c1,c2,c3=st.columns([0.4,0.2,0.4])
    with c1: sp_name=st.text_input("1. ชื่อ-สกุล คู่สมรส", value="", key="sp_name_v20")
    with c2: sp_age=st.number_input("2. อายุ", value=0, key="sp_age_v20")
    with c3: sp_job=st.text_input("6. อาชีพ", value="", key="sp_job_v20")
    c1,c2,c3=st.columns(3)
    with c1: sp_year=st.number_input("3. ปีสมรส", value=0, key="sp_year_v20")
    with c2: sp_child=st.number_input("4. บุตร", value=0, key="sp_child_v20")
    with c3: sp_income=st.number_input("5. รายได้", value=0, step=500, key="sp_inc_v20")
    spouse_summary=f"{sp_name} อายุ {sp_age} สมรส {sp_year} ปี บุตร {sp_child} คน รายได้ {sp_income:,.0f} อาชีพ {sp_job}"

guar_choice=st.radio("สถานะผู้ค้ำประกัน", ["1 ไม่มีผู้ค้ำประกัน","2 มีผู้ค้ำประกัน"], horizontal=True, key="guar_choice_v20")
g_text="ไม่มีผู้ค้ำประกัน"; g_name=""; g_age=0; g_job=""; g_income=0; g_phone=""
if guar_choice=="2 มีผู้ค้ำประกัน":
    c1,c2,c3=st.columns([0.4,0.2,0.4])
    with c1: g_name=st.text_input("1. ชื่อ-สกุล ผู้ค้ำ", value="", key="g_name_v20")
    with c2: g_age=st.number_input("2. อายุ", value=0, key="g_age_v20")
    with c3: g_phone=st.text_input("5. เบอร์โทร", value="", key="g_phone_v20")
    c1,c2=st.columns(2)
    with c1: g_job=st.text_input("3. อาชีพผู้ค้ำ", value="", key="g_job_v20")
    with c2: g_income=st.number_input("4. รายได้ผู้ค้ำ", value=0, step=1000, key="g_inc_v20")
    g_text=f"{g_name} อายุ {g_age} อาชีพ {g_job} รายได้ {g_income:,.0f} เบอร์ {g_phone}"
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="moto-card">', unsafe_allow_html=True)
st.subheader("🏍️ เช็คลิสต์เอกสาร 6 รายการ + Upload")
d1=st.checkbox("1. สำเนาบัตรประชาชน", key="doc1_v20")
d2=st.checkbox("2. ทะเบียนบ้าน", key="doc2_v20")
d3=st.checkbox("3. สลิปเงินเดือน 3 เดือน", key="doc3_v20")
d4=st.checkbox("4. สเตทเม้นท์ 6 เดือน", key="doc4_v20")
d5=st.checkbox("5. ใบจดทะเบียนการค้า", key="doc5_v20")
d6=st.checkbox("6. รูปถ่ายที่พัก / หมุด Google Maps", key="doc6_v20")
attached=[]; missing=[]
for n,c in [("บัตร ปชช",d1),("ทะเบียนบ้าน",d2),("สลิป 3 เดือน",d3),("สเตทเม้นท์ 6 เดือน",d4),("ใบจดทะเบียนการค้า",d5),("รูปที่พัก",d6)]:
    if c: attached.append(n)
    else: missing.append(n)
if attached: st.markdown(" ".join([f"<span class='tag-red'>{a} x</span>" for a in attached]), unsafe_allow_html=True)
uploaded=st.file_uploader("📸 Upload เอกสาร (200MB) JPG PNG HEIC WEBP - กัน DNG", type=["png","jpg","jpeg","heic","heif","webp"], accept_multiple_files=True, key="upload_v20")
if uploaded:
    bad=[f.name for f in uploaded if f.name.lower().endswith(('.dng','.raw','.arw','.cr2','.cr3','.nef','.orf','.rw2','.raf'))]
    if bad:
        st.error(f"❌ พบไฟล์ RAW/DNG: {', '.join(bad)} - เปลี่ยนที่มือถือเป็น JPG")
        uploaded=[f for f in uploaded if not f.name.lower().endswith(('.dng','.raw','.arw','.cr2','.cr3','.nef','.orf','.rw2','.raf'))]
cam=st.camera_input("📷 Take Photo", key="camera_v20")
gps_consent=st.checkbox("✅ ยินยอมให้ติดตามตำแหน่ง (PDPA Compliant)", value=False, key="gps_v20")
workplace=st.text_input("📌 พิกัด Google Maps", value="", placeholder="[ว่าง] https://maps.app.goo.gl/...", key="workplace_v20")
story=st.text_area("🏪 บันทึกบริบทหน้าร้าน", value="", placeholder="[ว่าง]", key="story_v20")
shared_contracts=st.number_input("จำนวนสัญญาที่เชื่อมโยงใน 90 วัน (เครือข่ายนายหน้า)", min_value=0, value=0, key="shared_v20")
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="moto-card" style="border:2px solid #8B5CF6 !important;">', unsafe_allow_html=True)
st.subheader("🏍️ วิเคราะห์ 13 โมดูลด้วย Ai")
r_score, r_flags, r_verdict = evaluate_fraud_rules(vehicle_type, down_pct, emp_type, shared_contracts, dsr, gps_consent)
colA,colB,colC=st.columns(3)
with colA: st.metric("DSR Meter", f"{dsr:.1f}%"); st.progress(min(1.0, dsr/100) if dsr>0 else 0.0)
with colB: risk_score=int(min(100, dsr*1.2)) if dsr>0 else 0; st.metric("Risk Score", f"{risk_score}/100"); st.progress(risk_score/100)
with colC: st.metric(f"Fraud Score - {r_verdict}", f"{r_score}"); 
for f in r_flags: st.error(f)
st.markdown("**Backend:** Rule Engine + Prompt AI 10 หัวข้อ + Motorcycle-Price-All-Models.xlsx + PDPA + Data Log")

if uploaded or cam or st.checkbox("✅ ทดสอบโดยไม่ต้องอัปโหลด", key="test_no_upload_v20"):
    if st.button("🚀 รัน SRD Credit Investigation Engine 13 Modules", type="primary", use_container_width=True, key="run_ai_v20"):
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
# SRD CREDIT INVESTIGATION ENGINE Hybrid v2.0 - Yamaha Auto Interest
## ROLE: Head of Credit Risk & Fraud Intelligence
[ข้อมูลรถ Flat Rate - Motorcycle-Price-All-Models.xlsx] รุ่น {brand_model} รหัส {code_auto} ราคา {cash_price} ดาวน์ {down_payment} ({down_pct:.1f}%) ยอดจัด auto {financing} = {cash_price} - {down_payment} Flat {flat_rate:.3f}% Term {term} เดือน (12/18/24/30/36/48/55/62) ค่างวด {monthly_final} ยอดหนี้รวม {total_debt_final} รวมจ่ายวันออกรถ {total_now} | ดอกเบี้ย Yamaha auto จากไฟล์ ไม่ต้องจำ
[ผู้กู้] {f_name} {l_name} อายุ {age} อาชีพ {job} เบอร์ {phone} ที่พัก {residence} เงินเดือน {salary} เสริม {extra} รายได้รวม {total_inc} ภาระรวม {total_bur} DSR {dsr:.1f}% Rule {emp_type}
[พิกัด] {workplace} GPS {gps_consent} Rule {r_score} {r_verdict} Flags {r_flags}
[คู่สมรส] {spouse_summary}
[ผู้ค้ำ] {g_text}
[อ้างอิง] {ref1_name} ({ref1_rel}) / {ref2_name} ({ref2_rel})
[เอกสาร] แนบ {', '.join(attached)} ขาด {', '.join(missing)}
[บริบท] {story}
[Price-Backup] {selected_row.to_dict() if selected_row is not None else 'ไม่ได้เลือกรุ่น'}
"""
                with st.spinner(f"AI ({selected_model}) วิเคราะห์ 13 โมดูล + Yamaha auto {flat_rate:.3f}%..."):
                    model_ai=genai.GenerativeModel(selected_model)
                    if imgs: resp=model_ai.generate_content([full_prompt]+imgs)
                    else: resp=model_ai.generate_content(full_prompt)
                    save_record({"Timestamp":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"BrandModel":brand_model,"Code":code_auto,"Cash":cash_price,"Down":down_payment,"DownPct":f"{down_pct:.1f}%","Financing_auto":financing,"Flat_auto":flat_rate,"Term":term,"Monthly":monthly_final,"TotalDebt":total_debt_final,"TotalNow":total_now,"Applicant":f"{f_name} {l_name}","DSR":f"{dsr:.1f}%","RuleScore":r_score,"RuleVerdict":r_verdict,"Docs":", ".join(attached),"GPS":workplace})
                    st.success("💾 บันทึก Data Log แล้ว - Hybrid v2.0 - ยอดจัด auto + ดอกเบี้ย Yamaha auto")
                    st.markdown(f"**Rule Engine:** {r_verdict} Score {r_score} | ยอดจัด auto {financing:,.0f} = {cash_price:,.0f} - {down_payment:,.0f} | ดอกเบี้ย auto {flat_rate:.3f}%")
                    st.markdown(resp.text)
            except Exception as e:
                st.error(f"Error: {e}")
else:
    st.info("อัปโหลดภาพเอกสารหรือถ่ายภาพก่อนรัน AI")
st.markdown('</div>', unsafe_allow_html=True)
st.caption("Hybrid v2.0 • ดึงจาก Motorcycle-Price-All-Models.xlsx • ยอดจัด auto = ราคาเงินสด - ดาวน์ • ดอกเบี้ย Yamaha auto (0.015, 0.014, 0.0129, 0.011, 0.009) ไม่ต้องจำ • Field Length Optimized")
