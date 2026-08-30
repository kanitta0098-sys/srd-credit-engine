
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

st.set_page_config(page_title="SRD Hybrid v2.3 - ตารางคำนวณ + Yamaha Auto", layout="wide", page_icon="🏍️")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;600;700;800&display=swap');
html, body, [class*="css"] { font-family:'Sarabun', sans-serif !important; }
.stApp { background:#0F172A !important; color:#E2E8F0 !important; }
.moto-card { background:#1E293B !important; border:2px solid #334155 !important; border-radius:16px; padding:14px 16px; margin-bottom:12px; }
.yellow-box { background:linear-gradient(135deg,#FDE68A,#FBBF24) !important; color:#000 !important; font-weight:800; border-radius:8px; padding:10px 12px; border:1px solid #F59E0B; }
.red-box { background:linear-gradient(135deg,#FECACA,#F87171) !important; color:#7F1D1D !important; font-weight:800; border-radius:8px; padding:10px 12px; }
.blue-box { background:#1E3A8A !important; border:1px solid #3B82F6 !important; border-radius:8px; padding:8px 12px; color:#DBEAFE !important; }
.label-col { font-weight:600; font-size:13px; padding:7px 0; color:#E2E8F0; }
.tag-green { background:#065F46 !important; color:#6EE7B7 !important; border-radius:6px; padding:2px 8px; font-weight:700; font-size:11px; display:inline-block; margin:2px; }
.block-container { max-width:1420px !important; padding-top:0.6rem !important; }
</style>
""", unsafe_allow_html=True)

# === Backend Engine: evaluate_fraud_rules() เต็มระบบ ===
def evaluate_fraud_rules(vehicle_type, down_pct, employment_type, shared_contracts_count, dsr_val, gps_consent):
    rule_score=0; flags=[]
    high_risk=["Yamaha - Sport","Honda - รถใหม่","PICKUP_4X4","BIGBIKE_PREMIUM","SPORT","YAMAHA","R15","WR155R","Aerox","XMAX","NMAX"]
    unstable=["ฟรีแลนซ์/รับจ้างทั่วไป","ว่างงาน/ไม่มีงานประจำ","FREELANCE","GENERAL_LABOR","UNEMPLOYED"]
    if (any(x in vehicle_type.upper() for x in [h.upper() for h in high_risk]) or "Sport" in vehicle_type) and down_pct <=5.0 and employment_type in unstable:
        rule_score+=40
        flags.append("⚠️ R_MATCH_RISK_01: เสี่ยงดาวน์แลกเงิน (รถสปอร์ต/ตลาด + ดาวน์ ≤5% + อาชีพไม่นิ่ง)")
    if shared_contracts_count>=1:
        rule_score+=50
        flags.append("🚨 R_LINKAGE_02: เครือข่ายนายหน้า/จัดซ้อน (พบความเชื่อมโยงกับสัญญาอื่นใน 90 วัน)")
    if (dsr_val>50.0 or down_pct<10.0) and not gps_consent:
        rule_score+=20
        flags.append("⚠️ R_HIGH_DSR_NO_TRACKING: DSR>50% หรือดาวน์<10% แต่ไม่มี GPS PDPA + Export Risk")
    if rule_score>=80: verdict="⛔ AUTO REJECT (เสี่ยงทุจริตจัดตั้งสูงมาก)"
    elif rule_score>=50: verdict="🟠 MANUAL REVIEW (ต้องส่งฝ่ายสินเชื่อตรวจเชิงลึก)"
    else: verdict="🟢 AUTO PASS (ผ่านเกณฑ์ความเสี่ยงจัดตั้งเบื้องต้น)"
    return rule_score, flags, verdict

@st.cache_data
def load_master_models():
    paths=[
        "/mnt/data/Motorcycle-Price-All-Models.xlsx",
        "Motorcycle-Price-All-Models.xlsx",
        "/mount/src/srd-credit-engine/Motorcycle-Price-All-Models.xlsx",
        "/mnt/data/motorcycle_price_all_models.xlsx"
    ]
    df_final=None
    yamaha_interest_map={}
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
                    # สร้าง map ดอกเบี้ย Yamaha
                    for _, r in df_base.iterrows():
                        name=str(r['รุ่นรถ'])
                        if any(k in name for k in ["ฟาซซิโอ้","แกรนด์","เอ็นแม็ก","XMAX","Aerox","ฟินน์","WR","PG-1","R15","GIORNO"]):
                            yamaha_interest_map[name]=float(r['ดอกเบี้ยต่อเดือน'])
                    df_final=df_base
                    break
            except Exception as e:
                continue
    if df_final is None:
        for cp in ["/mnt/data/price_backup_all_models.csv"]:
            if os.path.exists(cp):
                df=pd.read_csv(cp, encoding='utf-8')
                df_final=df
                break
    if df_final is None:
        df_final=pd.DataFrame({"รุ่นรถ":["ฟาซซิโอ้ SMK","Aerox 155 2026"],"รหัสรถ":["BKF700","BWR100"],"ยอดจัด":[54600,85900],"ดอกเบี้ยต่อเดือน":[0.015,0.011],"ราคาดาวน์":[0,0],"ทะเบียน พรบ ประกัน":[1000,1000]})
    return df_final, yamaha_interest_map

@st.cache_data
def load_all_categories():
    # 5 หมวดหมู่จากไฟล์งาน Motorcycle-Price-All-Models
    return ["Auto", "Moped", "Sport", "BigBike", "Electric"]

HISTORY_FILE="srd_credit_assessment_history.csv"
def save_record(rec):
    df=pd.DataFrame([rec])
    if not os.path.exists(HISTORY_FILE): df.to_csv(HISTORY_FILE, index=False, encoding='utf-8-sig')
    else: df.to_csv(HISTORY_FILE, mode='a', header=False, index=False, encoding='utf-8-sig')

# SIDEBAR - แสดงดอกเบี้ย Yamaha auto ให้ฝ่ายขายไม่ต้องจำ
with st.sidebar:
    st.markdown("### 🏍️ SRD Hybrid v2.3\nตารางคำนวณ + Yamaha Auto")
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
    df_master, yamaha_map=load_master_models()
    st.caption(f"📂 Motorcycle-Price-All-Models: {len(df_master)} รุ่น ครบ - 5 หมวดหมู่")
    st.markdown("**💡 ดอกเบี้ย Yamaha auto - ฝ่ายขายไม่ต้องจำ:**")
    if yamaha_map:
        yam_df=pd.DataFrame(list(yamaha_map.items()), columns=["รุ่น","ดอกเบี้ย/เดือน"])
        yam_df["ดอกเบี้ย%"]=yam_df["ดอกเบี้ย/เดือน"]*100
        st.dataframe(yam_df.head(15), height=250)
    else:
        if not df_master.empty:
            st.dataframe(df_master[["รุ่นรถ","ดอกเบี้ยต่อเดือน"]].head(10), height=200)
    cats=load_all_categories()
    st.caption(f"🏷️ 5 หมวดหมู่: {', '.join(cats)}")
    if st.button("🔄 รีเซ็ตฟอร์มว่าง", use_container_width=True):
        st.session_state.clear(); st.rerun()

st.markdown("""<div class="moto-card" style="display:flex;justify-content:space-between;align-items:center;background:linear-gradient(135deg,#0F172A,#1E293B) !important;"><div><div style="font-size:26px;font-weight:800;color:#FFF;">🏍️ SRD Credit Engine Hybrid v2.3</div><div style="font-size:11px;color:#38BDF8;">ตารางคำนวณ 14 แถวเป๊ะ • ดึงจาก Motorcycle-Price-All-Models.xlsx • ยอดจัด auto = Net - ดาวน์ • ดอกเบี้ย Yamaha auto 0.009%-0.015% ไม่ต้องจำ • Field Length Optimized • Backend Fraud + PDPA/GPS + 5 หมวดหมู่ • Prompt AI 10 หัวข้อ</div></div><div><span style="background:#065F46;color:#6EE7B7;border-radius:20px;padding:6px 10px;font-size:11px;">● ONLINE</span> <span style="background:#1E3A8A;color:#93C5FD;border-radius:20px;padding:6px 10px;font-size:11px;">v2.3 Yamaha Auto</span></div></div>""", unsafe_allow_html=True)

price_df, _ = load_master_models()
model_list=price_df["รุ่นรถ"].astype(str).tolist()
price_dict={row["รุ่นรถ"]: row for _, row in price_df.iterrows()}

# ===== ตารางคำนวณ 14 แถวเป๊ะ - ปรับความยาวแต่ละช่องเหมาะสม =====
st.markdown('<div class="moto-card">', unsafe_allow_html=True)
st.subheader("ตารางคำนวณ")
st.caption("ปรับความยาวแต่ละช่องตามความเหมาะสม ไม่ยาวเกินไป ไม่สั้นเกินไป - ดึงจาก Motorcycle-Price-All-Models หรือมีตัวเลือกว่าง - แก้ไขตัวเลขได้ - ดอกเบี้ย Yamaha auto")

# ใช้ columns แบบ Field Length Optimized: 50% label, 15% code, 15% flat, 20% term - ตามที่เคยขอ 55/15/14/16
r1c1, r1c2, r1c3, r1c4 = st.columns([0.50, 0.15, 0.15, 0.20])
with r1c1:
    st.markdown('<div class="label-col">ชื่อรุ่นรถ / Model:</div>', unsafe_allow_html=True)
    brand_model=st.selectbox("ชื่อรุ่นรถ / Model", options=["[ว่าง] เลือกรุ่นรถ"]+model_list, index=0, key="model_v23", label_visibility="collapsed")
    selected_row=price_dict.get(brand_model) if brand_model in price_dict else None
with r1c2:
    code_auto=selected_row["รหัสรถ"] if selected_row is not None else ""
    st.text_input("รหัสรถ", value=str(code_auto), disabled=True, key="code_v23", label_visibility="collapsed", placeholder="รหัสรถ")
with r1c3:
    flat_default=float(selected_row["ดอกเบี้ยต่อเดือน"]*100) if selected_row is not None and pd.notna(selected_row["ดอกเบี้ยต่อเดือน"]) else 1.70
    flat_rate=st.number_input("Flat %", value=flat_default, step=0.05, format="%.2f", key="flat_v23", label_visibility="collapsed", help="ดอกเบี้ย Yamaha auto จาก Motorcycle-Price-All-Models.xlsx - ฝ่ายขายไม่ต้องจำ")
    if selected_row is not None:
        st.markdown(f"<span class='tag-green'>{flat_default:.2f}% auto</span>", unsafe_allow_html=True)
with r1c4:
    term_options=[12,18,24,30,36,48,55,62]
    term_sel=st.selectbox("ระยะเวลาผ่อน", options=term_options, index=5, key="term_v23", label_visibility="collapsed")
    custom=st.checkbox("✏️ กำหนดเอง 6-84", key="custom_term_v23")
    if custom:
        term=st.number_input("Term กำหนดเอง", min_value=6, max_value=84, value=term_sel, step=1, key="term_custom_v23", label_visibility="collapsed")
    else:
        term=term_sel

# แถว 2-6: ราคาสด, พรบ., Net, ดาวน์, ยอดจัด - Field Length Optimized 4 ช่องเท่ากัน
r2c1, r2c2, r2c3, r2c4 = st.columns([0.25,0.25,0.25,0.25])
with r2c1:
    st.markdown('<div class="label-col">ราคาสดตัวรถ (Cash Price):</div>', unsafe_allow_html=True)
    cash_default=float(selected_row["ยอดจัด"]+selected_row["ราคาดาวน์"]) if selected_row is not None and pd.notna(selected_row["ยอดจัด"]) else 85500.0
    cash_price=st.number_input("ราคาสดตัวรถ (Cash Price)", value=cash_default, step=100.0, key="cash_v23", label_visibility="collapsed")
with r2c2:
    st.markdown('<div class="label-col">บวกค่า พรบ./ทะเบียน/ประกันรถหาย (รวมในยอดจัด):</div>', unsafe_allow_html=True)
    reg_default=float(selected_row["ทะเบียน พรบ ประกัน"]) if selected_row is not None and pd.notna(selected_row["ทะเบียน พรบ ประกัน"]) else 0.0
    reg_fee=st.number_input("บวกค่า พรบ.", value=reg_default, step=100.0, key="reg_v23", label_visibility="collapsed")
with r2c3:
    st.markdown('<div class="label-col">รวมราคารถสุทธิ (Net Price)</div>', unsafe_allow_html=True)
    net_price=cash_price+reg_fee
    st.markdown(f"<div class='yellow-box'>Net = {cash_price:,.0f}+{reg_fee:,.0f} = {net_price:,.0f}</div>", unsafe_allow_html=True)
with r2c4:
    st.markdown('<div class="label-col">เงินดาวน์ (Down Payment):</div>', unsafe_allow_html=True)
    down_default=float(selected_row["ราคาดาวน์"]) if selected_row is not None and pd.notna(selected_row["ราคาดาวน์"]) else 8900.0
    down_payment=st.number_input("เงินดาวน์ (Down Payment)", value=down_default, step=100.0, key="down_v23", label_visibility="collapsed")

# แถว 3: ยอดจัด, ดอกเบี้ยรวม, ยอดหนี้รวม, ค่างวด
financing=net_price-down_payment
total_interest=financing*(flat_rate/100)*term
total_debt=financing+total_interest
monthly=total_debt/term if term>0 else 0

r3c1, r3c2, r3c3, r3c4 = st.columns(4)
with r3c1:
    st.markdown('<div class="label-col">ยอดจัดไฟแนนซ์ (Financing Amount)</div>', unsafe_allow_html=True)
    st.markdown(f"<div class='yellow-box'>ยอดจัด = {net_price:,.0f}-{down_payment:,.0f} = {financing:,.0f} (auto)</div>", unsafe_allow_html=True)
with r3c2:
    st.markdown('<div class="label-col">รวมดอกเบี้ยทั้งหมด (Total Interest):</div>', unsafe_allow_html=True)
    st.markdown(f"<div class='blue-box'>ดอกเบี้ย = {financing:,.0f}×{flat_rate:.2f}%×{term} = {total_interest:,.0f}</div>", unsafe_allow_html=True)
with r3c3:
    st.markdown('<div class="label-col">ยอดหนี้รวมทั้งหมด (Total Debt):</div>', unsafe_allow_html=True)
    st.markdown(f"<div class='yellow-box'>ยอดหนี้ = {financing:,.0f}+{total_interest:,.0f} = {total_debt:,.0f}</div>", unsafe_allow_html=True)
with r3c4:
    st.markdown('<div class="label-col">ค่างวดต่อเดือน (Monthly Payment):</div>', unsafe_allow_html=True)
    st.markdown(f"<div class='red-box'>ค่างวด = {total_debt:,.0f}/{term} = {monthly:,.0f} บ.</div>", unsafe_allow_html=True)

# แถว 4: ค่า พรบ., เงินดาวน์, ออกรถได้ - ตามรายการ 3 แถวสุดท้าย (ไม่ซ้ำ input)
total_drive=down_payment+reg_fee
r4c1, r4c2, r4c3 = st.columns(3)
with r4c1:
    st.markdown('<div class="label-col">ค่า พรบ./ทะเบียน/ประกันรถหาย</div>', unsafe_allow_html=True)
    st.markdown(f"<div class='yellow-box' style='background:linear-gradient(135deg,#FEF3C7,#FDE68A) !important;'>ค่า พรบ./ทะเบียน/ประกันรถหาย = {reg_fee:,.0f}</div>", unsafe_allow_html=True)
with r4c2:
    st.markdown('<div class="label-col">เงินดาวน์ (Down Payment):</div>', unsafe_allow_html=True)
    st.markdown(f"<div class='yellow-box' style='background:linear-gradient(135deg,#FEF3C7,#FDE68A) !important;'>เงินดาวน์ = {down_payment:,.0f}</div>", unsafe_allow_html=True)
with r4c3:
    st.markdown('<div class="label-col">ออกรถได้</div>', unsafe_allow_html=True)
    st.markdown(f"<div class='red-box' style='font-size:18px;text-align:center;'>ออกรถได้ = {down_payment:,.0f}+{reg_fee:,.0f} = {total_drive:,.0f} บ.</div>", unsafe_allow_html=True)

down_pct=(down_payment/net_price*100) if net_price>0 else 0
st.markdown(f"<div class='blue-box' style='margin-top:10px;'>💡 ดึงจาก Motorcycle-Price-All-Models.xlsx: รุ่น {brand_model} | ยอดจัด auto {financing:,.0f} = {net_price:,.0f}-{down_payment:,.0f} | ดอกเบี้ย Yamaha auto {flat_rate:.2f}% (ไม่ต้องจำ) | Net {net_price:,.0f} = {cash_price:,.0f}+{reg_fee:,.0f} | ค่างวด {monthly:,.0f} | ออกรถได้ {total_drive:,.0f}</div>", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# ===== ฟอร์มว่าง 3-7 + Backend Engine ครบ =====
st.markdown('<div class="moto-card">', unsafe_allow_html=True)
st.subheader("🏍️ ข้อมูลผู้เช่าซื้อ")
st.caption("ฟอร์มว่าง - ปรับความยาวช่องตามความเหมาะสม ไม่ยาวเกินไป ไม่สั้นเกินไป")
c1, c2, c3 = st.columns([0.4,0.4,0.2])
with c1: f_name=st.text_input("ชื่อ", value="", placeholder="[ว่าง] สมชาย", key="fname_v23")
with c2: l_name=st.text_input("สกุล", value="", placeholder="[ว่าง] ใจดี", key="lname_v23")
with c3: age=st.number_input("อายุ", min_value=0, max_value=80, value=0, key="age_v23")
c1, c2, c3 = st.columns([0.35,0.35,0.3])
with c1: job=st.text_input("อาชีพ", value="", placeholder="[ว่าง]", key="job_v23")
with c2: phone=st.text_input("เบอร์โทร", value="", placeholder="[ว่าง] 081-xxx-xxxx", key="phone_v23")
with c3: emp_type=st.selectbox("ประเภทอาชีพ Rule", ["พนักงานประจำ","เจ้าของกิจการ","ฟรีแลนซ์/รับจ้างทั่วไป","ว่างงาน/ไม่มีงานประจำ"], key="emp_v23")
c1, c2, c3, c4 = st.columns(4)
with c1: residence=st.selectbox("ที่พัก", ["[ว่าง]","บ้านตนเอง/ปลอดภาระ","บ้านตนเอง/ติดผ่อน","บ้านเช่า/หอพัก","บ้านญาติ"], key="res_v23")
with c2: salary=st.number_input("เงินเดือน", value=0, step=500, key="sal_v23")
with c3: extra=st.number_input("รายได้เสริม", value=0, step=500, key="extra_v23")
with c4: debt_monthly=st.number_input("หนี้เดิม/เดือน", value=0, step=100, key="debt_monthly_v23")
living=st.number_input("ค่าใช้ชีวิต/เดือน", value=0, step=500, key="live_v23")
total_inc=salary+extra
total_bur=debt_monthly+living+monthly
dsr=(total_bur/total_inc*100) if total_inc>0 else 0
m1,m2,m3=st.columns(3)
with m1: st.metric("รายได้รวม", f"{total_inc:,.0f}")
with m2: st.metric("ภาระรวม", f"{total_bur:,.0f}")
with m3: st.metric("DSR %", f"{dsr:.1f}%")
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="moto-card">', unsafe_allow_html=True)
st.subheader("4. 🏍️ บุคคลอ้างอิง")
r1,r2=st.columns(2)
with r1:
    st.markdown("**อ้างอิง 1**")
    c1,c2,c3=st.columns([0.5,0.25,0.25])
    with c1: ref1_name=st.text_input("ชื่อ-สกุล 1", value="", key="ref1_name_v23", label_visibility="collapsed", placeholder="ชื่อ-สกุล 1")
    with c2: ref1_phone=st.text_input("เบอร์ 1", value="", key="ref1_phone_v23", label_visibility="collapsed", placeholder="เบอร์")
    with c3: ref1_rel=st.text_input("สัมพันธ์ 1", value="", key="ref1_rel_v23", label_visibility="collapsed", placeholder="พี่ชาย")
with r2:
    st.markdown("**อ้างอิง 2**")
    c1,c2,c3=st.columns([0.5,0.25,0.25])
    with c1: ref2_name=st.text_input("ชื่อ-สกุล 2", value="", key="ref2_name_v23", label_visibility="collapsed", placeholder="ชื่อ-สกุล 2")
    with c2: ref2_phone=st.text_input("เบอร์ 2", value="", key="ref2_phone_v23", label_visibility="collapsed", placeholder="เบอร์")
    with c3: ref2_rel=st.text_input("สัมพันธ์ 2", value="", key="ref2_rel_v23", label_visibility="collapsed", placeholder="เพื่อน")
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="moto-card">', unsafe_allow_html=True)
st.subheader("5. 🏍️ คู่สมรส")
st.caption("ช่องติ๊กสถานะชัดเจน: 1 ไม่มีคู่สมรส / 2 มีคู่สมรส (6 ช่อง)")
spouse_choice=st.radio("สถานะคู่สมรส", ["1 ไม่มีคู่สมรส","2 มีคู่สมรส"], horizontal=True, key="sp_choice_v23")
spouse_summary="ไม่มีคู่สมรส"; sp_name=""; sp_age=0; sp_year=0; sp_child=0; sp_income=0; sp_job=""
if spouse_choice=="2 มีคู่สมรส":
    c1,c2,c3=st.columns([0.4,0.2,0.4])
    with c1: sp_name=st.text_input("1. ชื่อ-สกุล คู่สมรส", value="", key="sp_name_v23")
    with c2: sp_age=st.number_input("2. อายุ", value=0, key="sp_age_v23")
    with c3: sp_job=st.text_input("6. อาชีพ", value="", key="sp_job_v23")
    c1,c2,c3=st.columns(3)
    with c1: sp_year=st.number_input("3. จำนวนปีที่สมรส", value=0, key="sp_year_v23")
    with c2: sp_child=st.number_input("4. มีบุตรกี่คน", value=0, key="sp_child_v23")
    with c3: sp_income=st.number_input("5. รายได้คู่สมรส", value=0, step=500, key="sp_inc_v23")
    spouse_summary=f"{sp_name} อายุ {sp_age} สมรส {sp_year} ปี บุตร {sp_child} คน รายได้ {sp_income:,.0f} อาชีพ {sp_job}"
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="moto-card">', unsafe_allow_html=True)
st.subheader("6. 🏍️ ผู้ค้ำประกัน")
st.caption("ช่องติ๊กสถานะชัดเจน: 1 ไม่มีผู้ค้ำ / 2 มีผู้ค้ำ (5 ช่อง)")
guar_choice=st.radio("สถานะผู้ค้ำประกัน", ["1 ไม่มีผู้ค้ำประกัน","2 มีผู้ค้ำประกัน"], horizontal=True, key="guar_choice_v23")
g_text="ไม่มีผู้ค้ำประกัน"; g_name=""; g_age=0; g_job=""; g_income=0; g_phone=""
if guar_choice=="2 มีผู้ค้ำประกัน":
    c1,c2,c3=st.columns([0.4,0.2,0.4])
    with c1: g_name=st.text_input("1. ชื่อ-สกุล ผู้ค้ำ", value="", key="g_name_v23")
    with c2: g_age=st.number_input("2. อายุ", value=0, key="g_age_v23")
    with c3: g_phone=st.text_input("5. เบอร์โทร", value="", key="g_phone_v23")
    c1,c2=st.columns(2)
    with c1: g_job=st.text_input("3. อาชีพผู้ค้ำประกัน", value="", key="g_job_v23")
    with c2: g_income=st.number_input("4. รายได้ผู้ค้ำประกัน", value=0, step=1000, key="g_inc_v23")
    g_text=f"{g_name} อายุ {g_age} อาชีพ {g_job} รายได้ {g_income:,.0f} เบอร์ {g_phone}"
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="moto-card">', unsafe_allow_html=True)
st.subheader("7. 🏍️ เช็คลิสต์เอกสาร 6 รายการ + PDPA/GPS")
d1=st.checkbox("1. สำเนาบัตรประชาชน", key="doc1_v23")
d2=st.checkbox("2. ทะเบียนบ้าน", key="doc2_v23")
d3=st.checkbox("3. สลิปเงินเดือน 3 เดือน", key="doc3_v23")
d4=st.checkbox("4. สเตทเม้นท์ 6 เดือน", key="doc4_v23")
d5=st.checkbox("5. ใบจดทะเบียนการค้า", key="doc5_v23")
d6=st.checkbox("6. รูปถ่ายที่พัก / หมุด Google Maps", key="doc6_v23")
attached=[]; missing=[]
for n,c in [("บัตร ปชช",d1),("ทะเบียนบ้าน",d2),("สลิป 3 เดือน",d3),("สเตทเม้นท์ 6 เดือน",d4),("ใบจดทะเบียนการค้า",d5),("รูปที่พัก",d6)]:
    if c: attached.append(n)
    else: missing.append(n)
if attached:
    st.markdown(" ".join([f"<span style='background:#DC2626;color:white;border-radius:6px;padding:2px 8px;font-size:11px;margin:2px;display:inline-block;'>{a} x</span>" for a in attached]), unsafe_allow_html=True)
uploaded=st.file_uploader("📸 Upload เอกสาร (JPG PNG HEIC WEBP - กัน DNG 200MB)", type=["png","jpg","jpeg","heic","heif","webp"], accept_multiple_files=True, key="upload_v23")
if uploaded:
    bad=[f.name for f in uploaded if f.name.lower().endswith(('.dng','.raw','.arw','.cr2','.cr3','.nef','.orf','.rw2','.raf'))]
    if bad:
        st.error(f"❌ พบไฟล์ RAW/DNG: {', '.join(bad)} - เปลี่ยนที่มือถือเป็น JPG")
        uploaded=[f for f in uploaded if not f.name.lower().endswith(('.dng','.raw','.arw','.cr2','.cr3','.nef','.orf','.rw2','.raf'))]
cam=st.camera_input("📷 Take Photo", key="camera_v23")
gps_consent=st.checkbox("✅ ยินยอมให้ติดตามตำแหน่ง (PDPA Compliant) - สำหรับ DSR>50% หรือดาวน์<10% ต้องมี GPS", value=False, key="gps_v23")
workplace=st.text_input("📌 พิกัด Google Maps (PDPA/GPS Consent)", value="", placeholder="[ว่าง] https://maps.app.goo.gl/... หรือ lat, lng", key="workplace_v23")
story=st.text_area("🏪 บันทึกบริบทหน้าร้าน", value="", placeholder="[ว่าง] ลูกค้ามาหน้าร้าน สภาพรถ ฯลฯ", key="story_v23")
shared_contracts=st.number_input("จำนวนสัญญาที่เชื่อมโยงใน 90 วัน (เครือข่ายนายหน้า)", min_value=0, value=0, key="shared_v23")
st.markdown('</div>', unsafe_allow_html=True)

# 8. วิเคราะห์ 13 โมดูล + Prompt AI เชิงลึก 10 หัวข้อ
st.markdown('<div class="moto-card" style="border:2px solid #8B5CF6 !important;">', unsafe_allow_html=True)
st.subheader("8. 🏍️ วิเคราะห์ 13 โมดูลด้วย Ai - Prompt AI เชิงลึก 10 หัวข้อ")
st.caption("นำ Prompt AI เชิงลึก 10 หัวข้อกลับมาใช้ในโมดูลที่ 8 + ฝังฟังก์ชัน evaluate_fraud_rules() + 5 หมวดหมู่ + PDPA/GPS Consent + พิกัด Google Maps")

vehicle_type=st.selectbox("ประเภทรถสำหรับ Rule Engine (5 หมวดหมู่: Auto, Moped, Sport, BigBike, Electric)", ["Auto (ดึงจากไฟล์)","Yamaha - Sport","YAMAHA","Honda - รถใหม่","SCOOTER_FAMILY","Moped","Sport","BigBike","Electric"], key="veh_v23")
r_score, r_flags, r_verdict = evaluate_fraud_rules(vehicle_type, down_pct, emp_type, shared_contracts, dsr, gps_consent)

colA,colB,colC=st.columns(3)
with colA: 
    st.metric("DSR Meter", f"{dsr:.1f}%")
    st.progress(min(1.0, dsr/100) if dsr>0 else 0.0)
with colB: 
    risk_score=int(min(100, dsr*1.2)) if dsr>0 else 0
    st.metric("Risk Score", f"{risk_score}/100")
    st.progress(risk_score/100)
with colC: 
    st.metric(f"Fraud Score - {r_verdict}", f"{r_score}")
    for f in r_flags: st.error(f)

st.markdown("**Backend Engine 5 หมวดหมู่:** Auto, Moped, Sport, BigBike, Electric + Rule Engine `evaluate_fraud_rules()` จับทุจริตจัดตั้ง/ดาวน์แลกเงิน/เครือข่ายนายหน้า/Export Risk/DSR>50% No GPS → Fraud Score + Verdict ⛔ AUTO REJECT / 🟠 MANUAL REVIEW / 🟢 AUTO PASS")
st.markdown(f"<div class='blue-box'>ตารางคำนวณ: {brand_model} | Net {net_price:,.0f} = {cash_price:,.0f}+{reg_fee:,.0f} | ยอดจัด auto {financing:,.0f} = {net_price:,.0f}-{down_payment:,.0f} | Flat Yamaha auto {flat_rate:.2f}% | Term {term} | ค่างวด {monthly:,.0f} | ออกรถได้ {total_drive:,.0f} | 5 หมวดหมู่ {vehicle_type}</div>", unsafe_allow_html=True)

if uploaded or cam or st.checkbox("✅ ทดสอบโดยไม่ต้องอัปโหลด", key="test_no_upload_v23"):
    if st.button("🚀 รัน SRD Credit Investigation Engine 13 Modules เต็มระบบ + Prompt AI 10 หัวข้อ", type="primary", use_container_width=True, key="run_ai_v23"):
        if not api_key or not model_sel:
            st.error("กรุณากรอก API Key ในแถบด้านซ้าย")
        else:
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key.strip())
                imgs=[]
                if uploaded:
                    for f in uploaded: imgs.append(_compress_mobile(Image.open(f)))
                if cam: imgs.append(_compress_mobile(Image.open(cam)))
                full_prompt=f"""
# SRD CREDIT INVESTIGATION ENGINE Hybrid v2.3 - ตารางคำนวณ 14 แถวเป๊ะ + Yamaha Auto Interest + Prompt AI 10 หัวข้อ
## ROLE: Head of Credit Risk & Fraud Intelligence — SRD Motor Finance บริษัท สิระเดชมอเตอร์เซลล์ จำกัด
- เป้าหมาย: อนุมัติลูกค้าที่มีเจตนาและสามารถผ่อนได้จริง พร้อมดักจับขบวนการทุจริตจัดตั้ง
- หลักการ: ห้ามเชื่อข้อมูลแหล่งเดียว (Cross-Validation ทุกจุด) | ห้ามสรุปว่าทุจริตจากสัญญาณเดียว (ดู Pattern) | วิเคราะห์ Customer Story ความสอดคล้อง
- 5 หมวดหมู่รถ: Auto, Moped, Sport, BigBike, Electric

### 1. ตารางคำนวณ 14 แถวเป๊ะ (ดึงจาก Motorcycle-Price-All-Models.xlsx)
- ชื่อรุ่นรถ / Model: {brand_model} (รหัส {selected_row['รหัสรถ'] if selected_row is not None else ''}) - ดึงจากไฟล์ Master ครบ {len(price_df)} รุ่น - ฝ่ายขายไม่ต้องจำดอกเบี้ย Yamaha
- ราคาสดตัวรถ (Cash Price): {cash_price:,.0f} บาท - ช่องว่างแบบเหมาะสม
- บวกค่า พรบ./ทะเบียน/ประกันรถหาย (รวมในยอดจัด): {reg_fee:,.0f} บาท - ช่องว่างแบบเหมาะสม
- รวมราคารถสุทธิ (Net Price): {net_price:,.0f} = {cash_price:,.0f}+{reg_fee:,.0f} = ผลลัพธ์
- เงินดาวน์ (Down Payment): {down_payment:,.0f} บาท ({down_pct:.1f}%) - ช่องว่างแบบเหมาะสม
- ยอดจัดไฟแนนซ์ (Financing Amount): {financing:,.0f} = {net_price:,.0f}-{down_payment:,.0f} = ผลลัพธ์ auto (ควรใส่ราคา auto)
- อัตราดอกเบี้ยต่อเดือน (Flat Rate / Month %): {flat_rate:.2f}% - ดึงจาก Motorcycle-Price-All-Models.xlsx auto - Yamaha ได้เปรียบไม่ต้องจำ (ฟาซซิโอ้ 0.015, แกรนด์ 0.014, NMAX 0.0129, Aerox 0.011, WR155R/R15 0.009)
- ระยะเวลาผ่อน (จำนวนงวด / Months): {term} เดือน (12/18/24/30/36/48/55/62 แก้ไขได้)
- รวมดอกเบี้ยทั้งหมด (Total Interest): {total_interest:,.0f} = {financing:,.0f}×{flat_rate:.2f}%×{term} = ผลลัพธ์
- ยอดหนี้รวมทั้งหมด (Total Debt): {total_debt:,.0f} = {financing:,.0f}+{total_interest:,.0f} = ผลลัพธ์
- ค่างวดต่อเดือน (Monthly Payment): {monthly:,.0f} = {total_debt:,.0f}/{term} = ผลลัพธ์
- ค่า พรบ./ทะเบียน/ประกันรถหาย: {reg_fee:,.0f} บาท
- เงินดาวน์ (Down Payment): {down_payment:,.0f} บาท
- ออกรถได้: {total_drive:,.0f} = {down_payment:,.0f}+{reg_fee:,.0f} = ผลลัพธ์

[ข้อมูลผู้กู้] {f_name} {l_name} อายุ {age} อาชีพ {job} เบอร์ {phone} ที่พัก {residence} เงินเดือน {salary:,.0f} เสริม {extra:,.0f} รายได้รวม {total_inc:,.0f} หนี้เดิม {debt_monthly:,.0f} ภาระรวม {total_bur:,.0f} DSR {dsr:.1f}% Rule {emp_type} Down% {down_pct:.1f}% 5 หมวดหมู่ {vehicle_type}
[Rule Engine] Score {r_score} Verdict {r_verdict} Flags {r_flags} Shared {shared_contracts} GPS Consent {gps_consent} พิกัด Google Maps {workplace} PDPA/GPS
[คู่สมรส] {spouse_summary} (6 ช่อง: ชื่อ-สกุล, อายุ, จำนวนปีสมรส, บุตร, รายได้, อาชีพ)
[ผู้ค้ำ] {g_text} (5 ช่อง: ชื่อ-สกุล, อายุ, อาชีพ, รายได้, เบอร์)
[อ้างอิง] {ref1_name} ({ref1_rel}-{ref1_phone}) / {ref2_name} ({ref2_rel}-{ref2_phone})
[เอกสาร] แนบ {', '.join(attached)} ขาด {', '.join(missing)}
[บริบทหน้าร้าน] {story}
[Price Master] {selected_row.to_dict() if selected_row is not None else 'ไม่ได้เลือกรุ่นจาก Motorcycle-Price-All-Models.xlsx'}

---
### REQUIRED OUTPUT - Prompt AI เชิงลึก 10 หัวข้อ กลับมาใช้ในโมดูลที่ 8:

## 1. CUSTOMER & HOUSEHOLD PROFILE
- สรุปตัวตน อาชีพ รายได้แท้จริงของผู้กู้ คู่สมรส (6 ช่อง) และคนค้ำประกัน (5 ช่อง) ความสามารถในการผ่อน {monthly:,.0f} บาท/เดือน และออกรถได้ {total_drive:,.0f} บาท

## 2. IDENTITY & WORKPLACE VERIFICATION (MODULE 01,02,03)
- ตรวจสอบภาพถ่ายเซลฟี่หน้าร้านคู่บัตรประชาชน (ยืนยันว่าผู้สมัคร = คนในบัตร = ผู้ใช้รถจริง)
- ตรวจสอบความสมเหตุสมผลของพิกัดที่ทำงาน/ภาพสต็อกสินค้า-แผงค้า ({workplace}) กับอาชีพที่ระบุ + PDPA/GPS Consent {gps_consent}

## 3. VERIFIED FACTS vs UNVERIFIED CLAIMS
- ระบุข้อเท็จจริงที่มีเอกสารยืนยัน เทียบกับรายการที่ยังขาดเอกสาร ({', '.join(missing) if missing else 'เอกสารครบ'}) ตามเช็คลิสต์ 6 รายการ

## 4. MONEY FLOW & CASH FLOW REALITY (MODULE 04 & 05)
- สรุป Money In -> Money Out -> Money Remain (ประเมินว่าเงินเพียงพอกับค่างวด {monthly:,.0f} บาท ยอดจัด {financing:,.0f} บาท ยอดหนี้รวม {total_debt:,.0f} บาท และออกรถได้ {total_drive:,.0f} บาท หรือไม่) DSR {dsr:.1f}%

## 5. FRAUD, GAMBLING & ASSET RISK CHECK (MODULE 06,07,08,09)
- Gambling: ตรวจสอบความถี่ เวลาโอนดึก และ Money Cycling (ห้ามตัดสินจากเศษสตางค์รายการเดียว)
- Nominee / Handover / Export Risk: ประเมินความเสี่ยงดาวน์แลกเงิน หรือการส่งรถข้ามแดน และผลกระทบของการมี/ไม่มีความยินยอม GPS ติดตามรถตาม PDPA (Score {r_score} Verdict {r_verdict} Flags {r_flags})
- Double Financing: ความผิดปกติของเอกสาร

## 6. GUARANTOR & SPOUSE MITIGATION POWER
- ประเมินพลังการหักล้างจุดอ่อนของผู้กู้โดยคนค้ำ (5 ช่อง) และคู่สมรส (6 ช่อง) (เช่น ผู้กู้งานอิสระแต่คนค้ำมั่นคง/คู่สมรสช่วยส่ง)

## 7. CONTRADICTION TABLE (MODULE 12)
| มิติข้อมูล | แหล่งที่ 1 | แหล่งที่ 2 | ผลเปรียบเทียบ | ระดับความขัดแย้ง |
| ตารางคำนวณ 14 แถว vs เอกสารจริง

## 8. RISK SCORING & FINAL DECISION (MODULE 13 - 100 คะแนน)
- Identity (15), Residence (10), Employment (15), Income (15), Cash Flow (15), Credit/NCB (10), Gambling/Distress (10), Nominee (5), Double Financing (5)
- หักลบความเสี่ยงด้วย Guarantor/Spouse Deduction และมาตรการ GPS Tracking PDPA {gps_consent}
- **ผลการตัดสิน:** 🟢 PASS (0-20) / 🟡 PASS WITH CONTROL (21-40) / 🟠 CONDITIONAL (41-60) / 🔴 HIGH RISK (61-75) / ⛔ REJECT (76-100) + Fraud Score {r_score} Verdict {r_verdict}

## 9. 30-SECOND SOFT INTERVIEW (คำถามโทนบริการ ไม่สอบสวน)
- คำถามผู้ซื้อ 2 ข้อ (ถามเส้นทางใช้งานจริง / รอบตัดบิลที่สะดวกชำระ {monthly:,.0f} บาท)
- คำถามคนค้ำประกัน 1 ข้อ (ถามความผูกพันเชิงบวก)

## 10. SUMMARY RECOMMENDATION FOR SALES
- สรุปแนวทางปิดการขายอย่างปลอดภัยสำหรับเซลส์ พร้อมตารางคำนวณ 14 แถว ยอดจัด auto {financing:,.0f} ดอกเบี้ย Yamaha auto {flat_rate:.2f}% ค่างวด {monthly:,.0f} ออกรถได้ {total_drive:,.0f} 5 หมวดหมู่ {vehicle_type} PDPA/GPS {gps_consent} พิกัด {workplace}
"""
                with st.spinner(f"AI ({model_sel}) วิเคราะห์ 13 โมดูล + Prompt AI 10 หัวข้อ + Fraud Score {r_score} + Yamaha auto {flat_rate:.2f}%..."):
                    model_ai=genai.GenerativeModel(model_sel)
                    if imgs: resp=model_ai.generate_content([full_prompt]+imgs)
                    else: resp=model_ai.generate_content(full_prompt)
                    save_record({
                        "Timestamp":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Model":brand_model,
                        "Cash":cash_price,
                        "Reg":reg_fee,
                        "Net":net_price,
                        "Down":down_payment,
                        "DownPct":f"{down_pct:.1f}%",
                        "Financing_auto":financing,
                        "Flat_auto":flat_rate,
                        "Term":term,
                        "TotalInterest":total_interest,
                        "TotalDebt":total_debt,
                        "Monthly":monthly,
                        "TotalDrive":total_drive,
                        "Applicant":f"{f_name} {l_name}",
                        "Phone":phone,
                        "DSR":f"{dsr:.1f}%",
                        "RuleScore":r_score,
                        "RuleVerdict":r_verdict,
                        "Spouse":spouse_summary,
                        "Guarantor":g_text,
                        "Docs":", ".join(attached),
                        "GPS":workplace,
                        "GPSConsent":gps_consent,
                        "Category":vehicle_type,
                        "Story":story
                    })
                    st.success(f"💾 บันทึก Data Log ละเอียดแล้ว - ตารางคำนวณ 14 แถวเป๊ะ + ยอดจัด auto {financing:,.0f} + ดอกเบี้ย Yamaha auto {flat_rate:.2f}% + Fraud {r_verdict} Score {r_score} + 5 หมวดหมู่ + PDPA/GPS")
                    st.markdown(f"**Rule Engine:** {r_verdict} Score {r_score} | ตารางคำนวณ: Net {net_price:,.0f} - Down {down_payment:,.0f} = Financing auto {financing:,.0f} | Flat Yamaha auto {flat_rate:.2f}% | ค่างวด {monthly:,.0f} | ออกรถได้ {total_drive:,.0f} | DSR {dsr:.1f}% | PDPA/GPS {gps_consent}")
                    st.markdown(resp.text)
            except Exception as e:
                st.error(f"Error: {e}")
else:
    st.info("อัปโหลดภาพเอกสารหรือถ่ายภาพก่อนรัน AI - ระบบ PDPA/GPS Consent + พิกัด Google Maps + 5 หมวดหมู่ + Fraud Engine พร้อม")

st.markdown('</div>', unsafe_allow_html=True)
st.caption("Hybrid v2.3 • ตารางคำนวณ 14 แถวเป๊ะ: ชื่อรุ่นรถ / Model: / ราคาสดตัวรถ (Cash Price): / บวกค่า พรบ./ทะเบียน/ประกันรถหาย (รวมในยอดจัด): / รวมราคารถสุทธิ (Net Price) / เงินดาวน์ (Down Payment): / ยอดจัดไฟแนนซ์ (Financing Amount) / อัตราดอกเบี้ยต่อเดือน (Flat Rate / Month %): / ระยะเวลาผ่อน (จำนวนงวด / Months) / รวมดอกเบี้ยทั้งหมด (Total Interest): / ยอดหนี้รวมทั้งหมด (Total Debt): / ค่างวดต่อเดือน (Monthly Payment): / ค่า พรบ./ทะเบียน/ประกันรถหาย / เงินดาวน์ (Down Payment): / ออกรถได้ • ปรับความยาวช่องเหมาะสม ไม่ยาวเกินไป ไม่สั้นเกินไป 50/15/15/20 • ดอกเบี้ย Yamaha auto 0.009%-0.015% จาก Motorcycle-Price-All-Models.xlsx ฝ่ายขายไม่ต้องจำ • Prompt AI เชิงลึก 10 หัวข้อกลับมาใช้ในโมดูลที่ 8 • evaluate_fraud_rules() + Fraud Score + Verdict ⛔/🟠/🟢 • 5 หมวดหมู่ Auto/Moped/Sport/BigBike/Electric • PDPA/GPS Consent + พิกัด Google Maps")
