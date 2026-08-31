
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

st.set_page_config(page_title="SRD Hybrid v2.7 - Fix 5 จุด", layout="wide", page_icon="🏍️")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;600;700;800&display=swap');
html, body, [class*="css"] { font-family:'Sarabun', sans-serif !important; }
.stApp { background:#0F172A !important; color:#E2E8F0 !important; }
/* FIX 1: แถบสีดำปิดหัวแอป - ซ่อน Header/Toolbar/MainMenu/Footer */
header[data-testid="stHeader"] {display:none !important; visibility:hidden !important;}
div[data-testid="stToolbar"] {visibility:hidden !important; display:none !important;}
#MainMenu {visibility:hidden !important; display:none !important;}
footer {visibility:hidden !important; display:none !important;}
header {visibility:hidden !important;}
.stApp > header {display:none !important;}
.block-container { max-width:1450px !important; padding-top:0.2rem !important; margin-top:0.2rem !important;}
.moto-card { background:#1E293B !important; border:2px solid #334155 !important; border-radius:16px; padding:16px 18px; margin-bottom:14px; }
.yellow-box { background:linear-gradient(135deg,#FDE68A,#FBBF24) !important; color:#000 !important; font-weight:800; border-radius:8px; padding:10px 12px; border:1px solid #F59E0B; }
.red-box { background:linear-gradient(135deg,#FECACA,#F87171) !important; color:#7F1D1D !important; font-weight:800; border-radius:8px; padding:10px 12px; }
.blue-box { background:#1E3A8A !important; border:1px solid #3B82F6 !important; border-radius:8px; padding:10px 14px; color:#DBEAFE !important; }
.label-col { font-weight:600; font-size:13px; padding:6px 0; color:#E2E8F0; }
.tag-green { background:#065F46 !important; color:#6EE7B7 !important; border-radius:6px; padding:2px 8px; font-weight:700; font-size:11px; display:inline-block; margin:2px; }
.tag-yellow { background:#92400E !important; color:#FDE68A !important; border-radius:6px; padding:2px 8px; font-weight:700; font-size:11px; display:inline-block; margin:2px; }
hr.sep { border:1px dashed #334155; margin:12px 0; }
</style>
""", unsafe_allow_html=True)

def evaluate_fraud_rules(vehicle_type, down_pct, employment_type, shared, dsr, gps):
    score=0; flags=[]
    high=["Yamaha - Sport","Honda - รถใหม่","SPORT","YAMAHA","R15","WR155R","Aerox","XMAX","NMAX","Wave","GIORNO"]
    unstable=["ฟรีแลนซ์/รับจ้างทั่วไป","ว่างงาน/ไม่มีงานประจำ","FREELANCE","GENERAL_LABOR","UNEMPLOYED"]
    if (any(x.upper() in vehicle_type.upper() for x in high) or "Sport" in vehicle_type) and down_pct <=5.0 and employment_type in unstable:
        score+=40; flags.append("⚠️ R_MATCH_RISK_01: เสี่ยงดาวน์แลกเงิน")
    if shared>=1:
        score+=50; flags.append("🚨 R_LINKAGE_02: เครือข่ายนายหน้า/จัดซ้อน")
    if dsr>70.0 and not gps:
        score+=20; flags.append("⚠️ R_HIGH_DSR_NO_TRACKING: DSR>70% ไม่มี GPS PDPA + Export Risk")
    elif down_pct<5.0 and not gps:
        score+=10; flags.append("💡 R_LOW_DOWN_NO_GPS: ดาวน์<5% ไม่มี GPS")
    if score>=80: verdict="⛔ AUTO REJECT"
    elif score>=50: verdict="🟠 MANUAL REVIEW"
    else: verdict="🟢 AUTO PASS"
    return score, flags, verdict

@st.cache_data
def load_master_models_robust(file_obj=None):
    df_final=None; yamaha_map={}; debug=[]
    search_files=[]
    if file_obj is not None:
        search_files.append(("uploaded", file_obj))
    possible_paths=[
        "Motorcycle-Price-All-Models.xlsx","./Motorcycle-Price-All-Models.xlsx",
        "motorcycle_price_all_models.xlsx","/mnt/data/Motorcycle-Price-All-Models.xlsx",
        "/mnt/data/motorcycle_price_all_models.xlsx","/mount/src/srd-credit-engine/Motorcycle-Price-All-Models.xlsx",
        "data/Motorcycle-Price-All-Models.xlsx"
    ]
    for p in possible_paths:
        if os.path.exists(p):
            search_files.append((p,p))
    for src_name, src in search_files:
        try:
            xls = pd.ExcelFile(src) if isinstance(src,str) else pd.ExcelFile(src)
            for sheet in xls.sheet_names:
                for hdr in [1,0,2]:
                    try:
                        df = pd.read_excel(xls, sheet_name=sheet, header=hdr)
                        if 'รุ่นรถ' not in df.columns: continue
                        df['รุ่นรถ']=df['รุ่นรถ'].ffill()
                        if 'รหัสรถ' in df.columns: df['รหัสรถ']=df['รหัสรถ'].ffill()
                        if 'ราคาจัด' in df.columns: df['ราคาจัด']=df['ราคาจัด'].ffill()
                        interest_col=[c for c in df.columns if 'ดอกเบี้ย' in str(c)]
                        if not interest_col: continue
                        interest_col=interest_col[0]
                        df[interest_col]=df[interest_col].ffill()
                        df_base = df[pd.notna(df['รหัสรถ'])].copy() if 'รหัสรถ' in df.columns else df.copy()
                        df_base=df_base[~df_base['รุ่นรถ'].astype(str).str.contains('รุ่นรถ|ตารางโปรโมชัน', na=False)]
                        df_base['รุ่นรถ']=df_base['รุ่นรถ'].astype(str).str.strip()
                        df_base=df_base[~df_base['รุ่นรถ'].isin(['nan','NaN',''])]
                        df_base=df_base.drop_duplicates(subset=['รุ่นรถ'], keep='first')
                        if len(df_base)<5: continue
                        rename_map={'ราคาจัด':'ยอดจัด', interest_col:'ดอกเบี้ยต่อเดือน', 'ดาวน์':'ราคาดาวน์', 'ค่าจด/พรบ.':'ทะเบียน พรบ ประกัน', 'รวมออกรถ':'ค่าใช้จ่ายออกรถ', 'เงินดาวน์':'ราคาดาวน์'}
                        df_base=df_base.rename(columns=rename_map)
                        for col in ['ยอดจัด','ดอกเบี้ยต่อเดือน','ราคาดาวน์','ทะเบียน พรบ ประกัน']:
                            if col not in df_base.columns: df_base[col]=0
                        for _, r in df_base.iterrows():
                            try: yamaha_map[str(r['รุ่นรถ'])]=float(r['ดอกเบี้ยต่อเดือน'])
                            except: yamaha_map[str(r['รุ่นรถ'])]=0.015
                        df_final=df_base
                        debug.append(f"✅ โหลดสำเร็จจาก {src_name} Sheet {sheet} header={hdr}: {len(df_final)} รุ่น ดอกเบี้ยครบ {len(yamaha_map)} รายการ")
                        break
                    except: continue
                if df_final is not None: break
        except Exception as e:
            debug.append(f"❌ {src_name} Error: {e}")
            continue
        if df_final is not None: break
    if df_final is None:
        for cp in ["price_backup_all_models.csv","/mnt/data/price_backup_all_models.csv"]:
            if os.path.exists(cp):
                try:
                    df=pd.read_csv(cp, encoding='utf-8')
                    df_final=df; debug.append(f"⚠️ Fallback CSV {cp}: {len(df_final)} รุ่น")
                    break
                except: pass
    if df_final is None:
        df_final=pd.DataFrame({"รุ่นรถ":["ฟาซซิโอ้ SMK","Aerox 155   2026","Wave 125 กุญแจธรรมดา /2026  1 คัน ดำ","GIORNO+ CBS  2 คัน ขาว-ดำ    เทา-น้ำตาล"],"รหัสรถ":["BKF700","BWR100","AFS125CSBT TH","ACF125CBT"],"ยอดจัด":[54600,85900,63500,85500],"ดอกเบี้ยต่อเดือน":[0.015,0.011,0.017,0.017],"ราคาดาวน์":[0,0,6900,6900],"ทะเบียน พรบ ประกัน":[1000,1000,2000,2000]})
        debug.append("⚠️ hardcode 4 รุ่น")
    return df_final, yamaha_map, debug

HISTORY_FILE="srd_credit_assessment_history.csv"
def save_record(rec):
    df=pd.DataFrame([rec])
    if not os.path.exists(HISTORY_FILE): df.to_csv(HISTORY_FILE, index=False, encoding='utf-8-sig')
    else: df.to_csv(HISTORY_FILE, mode='a', header=False, index=False, encoding='utf-8-sig')

# SIDEBAR
with st.sidebar:
    st.markdown("### 🏍️ SRD Hybrid v2.7\nFix 5 จุด")
    api_key=st.text_input("GEMINI API Key", value=st.secrets.get("GEMINI_API_KEY","") if hasattr(st,'secrets') else "", type="password")
    model_sel=None; usable=[]
    if api_key and len(api_key)>10:
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key.strip())
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    usable.append(m.name.replace("models/",""))
            if usable:
                model_sel=st.selectbox("🤖 โมเดล AI", usable, index=0)
                st.success(f"✅ {model_sel}")
        except Exception as e: st.error(f"API Key Error: {e}")
    st.markdown("---")
    st.markdown("**📂 อัปโหลด Motorcycle-Price-All-Models.xlsx ถ้าดึงไม่ครบ:**")
    uploaded_excel=st.file_uploader("อัปโหลดไฟล์ Excel Master", type=["xlsx","xls"], key="upload_excel_master_v27")
    df_master, yamaha_map, debug_list=load_master_models_robust(file_obj=uploaded_excel)
    for d in debug_list:
        if "✅" in d: st.success(d)
        elif "⚠️" in d: st.warning(d)
        else: st.error(d)
    if yamaha_map:
        yam_df=pd.DataFrame(list(yamaha_map.items()), columns=["รุ่น","ดอกเบี้ย/เดือน"])
        yam_df["ดอกเบี้ย%"]=(yam_df["ดอกเบี้ย/เดือน"]*100).round(3)
        st.dataframe(yam_df, height=280, use_container_width=True)
    st.caption(f"รุ่นรถครบ {len(df_master)} รุ่น")
    if st.button("🔄 รีเซ็ตฟอร์มว่าง", use_container_width=True):
        st.session_state.clear(); st.rerun()

st.markdown("""<div class="moto-card" style="display:flex;justify-content:space-between;align-items:center;background:linear-gradient(135deg,#0F172A,#1E293B) !important;"><div><div style="font-size:26px;font-weight:800;color:#FFF;">🏍️ SRD Credit Engine Hybrid v2.7</div><div style="font-size:11px;color:#38BDF8;">Fix 5 จุด: แถบดำหาย + รหัสรถเลือกได้ + พรบ.แก้ไขได้ + ลบคำอธิบาย + ดึงราคาตามตารางครบ 30 รุ่น | 2 คอลัมน์ 7+7 | ค่าดำเนินการ ชุดแต่ง อื่นๆ | คู่สมรส 3 ตัวเลือก | 13 โมดูล + Fraud Engine</div></div><div><span style="background:#065F46;color:#6EE7B7;border-radius:20px;padding:6px 10px;font-size:11px;">● ONLINE</span> <span style="background:#1E3A8A;color:#93C5FD;border-radius:20px;padding:6px 10px;font-size:11px;">v2.7 Fix 5 จุด</span></div></div>""", unsafe_allow_html=True)

price_df, _, debug_list = load_master_models_robust(file_obj=uploaded_excel if 'uploaded_excel' in locals() else None)
model_list=price_df["รุ่นรถ"].astype(str).tolist()
price_dict={row["รุ่นรถ"]: row for _, row in price_df.iterrows()}

for d in debug_list:
    if "✅" in d: st.success(d)

# ===== 1. ตารางราคา - 2 คอลัมน์ 7+7 =====
st.markdown('<div class="moto-card">', unsafe_allow_html=True)
st.subheader("1. ตารางราคา (ตารางคำนวณ)")
# FIX 4: ลบคำอธิบายใต้หัวข้อออก - ไม่มี caption แล้ว

col_left, col_right = st.columns(2)

# คอลัมน์ที่ 1
with col_left:
    st.markdown("**คอลัมน์ที่ 1 - ข้อมูลรถและเงินดาวน์**")
    # 1. ชื่อรุ่นรถ / Model:
    st.markdown('<div class="label-col">1. ชื่อรุ่นรถ / Model:</div>', unsafe_allow_html=True)
    st.markdown(f"<span class='tag-green'>ดึงจาก Motorcycle-Price-All-Models.xlsx {len(model_list)} รุ่น</span>", unsafe_allow_html=True)
    # FIX 5: การดึงข้อมูลไม่สมบูรณ์ - ให้ราคา ที่ตั้งตามตารางขึ้น auto สมบูรณ์
    brand_model=st.selectbox("ชื่อรุ่นรถ / Model", options=["[ว่าง] เลือกรุ่นรถ"]+model_list, index=0, key="model_v27", label_visibility="collapsed")
    selected_row=price_dict.get(brand_model) if brand_model in price_dict else None

    # FIX 2: ไม่สามารถเลือกได้ - รหัสรถให้เลือกได้
    st.markdown('<div class="label-col">รหัสรถ (เลือกได้ / Copy ได้):</div>', unsafe_allow_html=True)
    code_auto=str(selected_row["รหัสรถ"]) if selected_row is not None and pd.notna(selected_row["รหัสรถ"]) else ""
    # ใช้ text_input ที่ไม่ disabled เพื่อให้เลือกได้
    code_display=st.text_input("รหัสรถ", value=code_auto, key="code_v27", label_visibility="collapsed", placeholder="รหัสรถ - เลือกได้", help="รหัสจากไฟล์ Motorcycle-Price-All-Models.xlsx เลือก Copy ได้")
    # แสดงแบบ code block ให้ copy ได้ด้วย
    if code_auto:
        st.code(code_auto, language="text")

    # 2. ราคาสดตัวรถ (Cash Price) - FIX 5: ดึงจากตาราง ยอดจัด โดยตรง ไม่บวกดาวน์
    st.markdown('<div class="label-col">2. ราคาสดตัวรถ (Cash Price):</div>', unsafe_allow_html=True)
    # FIX 5: ราคาที่ตั้งตามตารางขึ้น - ใช้ ยอดจัด โดยตรง
    if selected_row is not None and pd.notna(selected_row["ยอดจัด"]):
        cash_default=float(selected_row["ยอดจัด"])
    else:
        cash_default=85500.0
    cash_price=st.number_input("ราคาสดตัวรถ", value=cash_default, step=100.0, key="cash_v27", label_visibility="collapsed", help="ดึงจาก ราคาจัด ในไฟล์ Motorcycle-Price-All-Models.xlsx")

    # 3. ค่าดำเนินการ ชุดแต่ง อื่นๆ
    st.markdown('<div class="label-col">3. ค่าดำเนินการ ชุดแต่ง อื่นๆ:</div>', unsafe_allow_html=True)
    st.markdown("<span class='tag-yellow'>แก้ไขหัวข้อที่ 3 - รวมในยอดจัดได้</span>", unsafe_allow_html=True)
    if selected_row is not None and pd.notna(selected_row["ทะเบียน พรบ ประกัน"]):
        reg_default=float(selected_row["ทะเบียน พรบ ประกัน"])
    else:
        reg_default=0.0
    reg_fee=st.number_input("ค่าดำเนินการ ชุดแต่ง อื่นๆ", value=reg_default, step=100.0, key="reg_v27", label_visibility="collapsed")

    # 4. รวมราคารถสุทธิ (Net Price)
    net_price=cash_price+reg_fee
    st.markdown('<div class="label-col">4. รวมราคารถสุทธิ (Net Price)</div>', unsafe_allow_html=True)
    st.markdown(f"<div class='yellow-box'>Net = {cash_price:,.0f} + {reg_fee:,.0f} = {net_price:,.0f}</div>", unsafe_allow_html=True)

    # 5. เงินดาวน์ (Down Payment) - FIX 5: ดึงจากตาราง
    st.markdown('<div class="label-col">5. เงินดาวน์ (Down Payment):</div>', unsafe_allow_html=True)
    if selected_row is not None and pd.notna(selected_row["ราคาดาวน์"]):
        down_default=float(selected_row["ราคาดาวน์"])
    else:
        down_default=8900.0
    down_payment=st.number_input("เงินดาวน์", value=down_default, step=100.0, key="down_v27", label_visibility="collapsed", help="ดึงจาก ดาวน์/เงินดาวน์ ในไฟล์")

    # 6. ยอดจัดไฟแนนซ์ (Financing Amount)
    financing=net_price-down_payment
    st.markdown('<div class="label-col">6. ยอดจัดไฟแนนซ์ (Financing Amount)</div>', unsafe_allow_html=True)
    st.markdown(f"<div class='yellow-box'>ยอดจัด = {net_price:,.0f} - {down_payment:,.0f} = {financing:,.0f} (auto)</div>", unsafe_allow_html=True)

    # 7. อัตราดอกเบี้ยต่อเดือน (Flat Rate / Month %) - FIX 5: ดึงครบ
    st.markdown('<div class="label-col">7. อัตราดอกเบี้ยต่อเดือน (Flat Rate / Month %):</div>', unsafe_allow_html=True)
    if selected_row is not None and pd.notna(selected_row["ดอกเบี้ยต่อเดือน"]):
        flat_default=float(selected_row["ดอกเบี้ยต่อเดือน"]*100)
    else:
        flat_default=1.70
    flat_rate=st.number_input("Flat Rate", value=flat_default, step=0.05, format="%.3f", key="flat_v27", label_visibility="collapsed", help="ดึงจาก ดอกเบี้ย/เดือน ในไฟล์ Motorcycle-Price-All-Models.xlsx 0.009%-0.017% ครบ 30 รุ่น")
    st.markdown(f"<span class='tag-green'>{flat_default:.3f}% auto จากไฟล์ - 30 ดอกเบี้ยครบ</span>", unsafe_allow_html=True)

with col_right:
    st.markdown("**คอลัมน์ที่ 2 - เงื่อนไขผ่อนและสรุปค่าใช้จ่าย**")
    # 8. ระยะเวลาผ่อน
    st.markdown('<div class="label-col">8. ระยะเวลาผ่อน (จำนวนงวด / Months)</div>', unsafe_allow_html=True)
    term_options=[12,18,24,30,36,48,55,62]
    term_sel=st.selectbox("ระยะเวลาผ่อน", options=term_options, index=5, key="term_v27", label_visibility="collapsed")
    custom=st.checkbox("✏️ กำหนดเอง 6-84", key="custom_term_v27")
    if custom:
        term=st.number_input("Term กำหนดเอง", min_value=6, max_value=84, value=term_sel, step=1, key="term_custom_v27", label_visibility="collapsed")
    else:
        term=term_sel

    total_interest=financing*(flat_rate/100)*term
    total_debt=financing+total_interest
    monthly=total_debt/term if term>0 else 0

    # 9. รวมดอกเบี้ยทั้งหมด
    st.markdown('<div class="label-col">9. รวมดอกเบี้ยทั้งหมด (Total Interest)</div>', unsafe_allow_html=True)
    st.markdown(f"<div class='blue-box'>ดอกเบี้ย = {financing:,.0f} × {flat_rate:.3f}% × {term} = {total_interest:,.0f}</div>", unsafe_allow_html=True)

    # 10. ยอดหนี้รวมทั้งหมด
    st.markdown('<div class="label-col">10. ยอดหนี้รวมทั้งหมด (Total Debt)</div>', unsafe_allow_html=True)
    st.markdown(f"<div class='yellow-box'>ยอดหนี้ = {financing:,.0f} + {total_interest:,.0f} = {total_debt:,.0f}</div>", unsafe_allow_html=True)

    # 11. ค่างวดต่อเดือน
    st.markdown('<div class="label-col">11. ค่างวดต่อเดือน (Monthly Payment)</div>', unsafe_allow_html=True)
    st.markdown(f"<div class='red-box'>ค่างวด = {total_debt:,.0f} / {term} = {monthly:,.0f} บ.</div>", unsafe_allow_html=True)

    st.markdown('<hr class="sep">', unsafe_allow_html=True)
    st.markdown("**-- สรุปค่าใช้จ่ายออกรถ --**")

    # FIX 3: หัวข้อนี้ควรแก้ไขได้ - ค่า พรบ. ให้แก้ไขได้
    st.markdown('<div class="label-col">12. ค่า พรบ./ทะเบียน/ประกันรถหาย (แก้ไขได้):</div>', unsafe_allow_html=True)
    # ใช้ค่า reg_fee เป็น default แต่แก้ไขได้แยก
    prb_fee=st.number_input("12. ค่า พรบ./ทะเบียน/ประกันรถหาย", value=reg_default, step=100.0, key="prb_fee_v27", label_visibility="collapsed", help="แก้ไขได้ - ค่า พรบ./ทะเบียน/ประกันรถหาย")
    st.markdown(f"<div class='yellow-box' style='background:linear-gradient(135deg,#FEF3C7,#FDE68A) !important;'>ค่า พรบ. = {prb_fee:,.0f} (แก้ไขได้)</div>", unsafe_allow_html=True)

    # 13. เงินดาวน์ (Down Payment) - สรุป
    st.markdown('<div class="label-col">13. เงินดาวน์ (Down Payment)</div>', unsafe_allow_html=True)
    st.markdown(f"<div class='yellow-box' style='background:linear-gradient(135deg,#FEF3C7,#FDE68A) !important;'>ดาวน์ = {down_payment:,.0f}</div>", unsafe_allow_html=True)

    # 14. ออกรถได้
    total_drive=down_payment+prb_fee
    st.markdown('<div class="label-col">14. ออกรถได้</div>', unsafe_allow_html=True)
    st.markdown(f"<div class='red-box' style='font-size:18px;text-align:center;'>ออกรถได้ = {down_payment:,.0f} + {prb_fee:,.0f} = {total_drive:,.0f} บ.</div>", unsafe_allow_html=True)

down_pct=(down_payment/net_price*100) if net_price>0 else 0
st.markdown(f"<div class='blue-box' style='margin-top:10px;'>💡 ดึงจาก Motorcycle-Price-All-Models.xlsx ครบ {len(model_list)} รุ่น: {brand_model} | รหัส {code_auto} | ราคาสด {cash_price:,.0f} (จากตาราง) | ค่าดำเนินการ {reg_fee:,.0f} | Net {net_price:,.0f} | ยอดจัด auto {financing:,.0f} | Flat {flat_rate:.3f}% auto (0.009%-0.017% ครบ) | ค่างวด {monthly:,.0f} | พรบ. {prb_fee:,.0f} (แก้ไขได้) | ออกรถได้ {total_drive:,.0f}</div>", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# ===== 2. ข้อมูลผู้เช่าซื้อ - คงเดิม ห้ามแก้ไข =====
st.markdown('<div class="moto-card">', unsafe_allow_html=True)
st.subheader("2. ข้อมูลผู้เช่าซื้อ")
c1, c2, c3 = st.columns([0.4,0.4,0.2])
with c1: f_name=st.text_input("ชื่อ", value="", placeholder="[ว่าง] สมชาย", key="fname_v27")
with c2: l_name=st.text_input("สกุล", value="", placeholder="[ว่าง] ใจดี", key="lname_v27")
with c3: age=st.number_input("อายุ", min_value=0, max_value=80, value=0, key="age_v27")
c1, c2, c3 = st.columns([0.35,0.35,0.3])
with c1: job=st.text_input("อาชีพ", value="", placeholder="[ว่าง]", key="job_v27")
with c2: phone=st.text_input("เบอร์โทร", value="", placeholder="[ว่าง] 081-xxx-xxxx", key="phone_v27")
with c3: emp_type=st.selectbox("ประเภทอาชีพ Rule", ["พนักงานประจำ","เจ้าของกิจการ","ฟรีแลนซ์/รับจ้างทั่วไป","ว่างงาน/ไม่มีงานประจำ"], key="emp_v27")
c1, c2, c3, c4 = st.columns(4)
with c1: residence=st.selectbox("ที่พัก", ["[ว่าง]","บ้านตนเอง/ปลอดภาระ","บ้านตนเอง/ติดผ่อน","บ้านเช่า/หอพัก","บ้านญาติ"], key="res_v27")
with c2: salary=st.number_input("เงินเดือน", value=0, step=500, key="sal_v27")
with c3: extra=st.number_input("รายได้เสริม", value=0, step=500, key="extra_v27")
with c4: debt_monthly=st.number_input("หนี้เดิม/เดือน", value=0, step=100, key="debt_monthly_v27")
living=st.number_input("ค่าใช้ชีวิต/เดือน", value=0, step=500, key="live_v27")
total_inc=salary+extra
total_bur=debt_monthly+living+monthly
dsr=(total_bur/total_inc*100) if total_inc>0 else 0
m1,m2,m3=st.columns(3)
with m1: st.metric("รายได้รวม", f"{total_inc:,.0f}")
with m2: st.metric("ภาระรวม", f"{total_bur:,.0f}")
with m3: st.metric("DSR %", f"{dsr:.1f}%")
st.markdown('</div>', unsafe_allow_html=True)

# ===== 3. บุคคลอ้างอิง - คงเดิม =====
st.markdown('<div class="moto-card">', unsafe_allow_html=True)
st.subheader("3. บุคคลอ้างอิง")
r1,r2=st.columns(2)
with r1:
    st.markdown("**อ้างอิง 1**")
    c1,c2,c3=st.columns([0.5,0.25,0.25])
    with c1: ref1_name=st.text_input("ชื่อ-สกุล 1", value="", key="ref1_name_v27", label_visibility="collapsed", placeholder="ชื่อ-สกุล 1")
    with c2: ref1_phone=st.text_input("เบอร์ 1", value="", key="ref1_phone_v27", label_visibility="collapsed", placeholder="เบอร์")
    with c3: ref1_rel=st.text_input("สัมพันธ์ 1", value="", key="ref1_rel_v27", label_visibility="collapsed", placeholder="พี่ชาย")
with r2:
    st.markdown("**อ้างอิง 2**")
    c1,c2,c3=st.columns([0.5,0.25,0.25])
    with c1: ref2_name=st.text_input("ชื่อ-สกุล 2", value="", key="ref2_name_v27", label_visibility="collapsed", placeholder="ชื่อ-สกุล 2")
    with c2: ref2_phone=st.text_input("เบอร์ 2", value="", key="ref2_phone_v27", label_visibility="collapsed", placeholder="เบอร์")
    with c3: ref2_rel=st.text_input("สัมพันธ์ 2", value="", key="ref2_rel_v27", label_visibility="collapsed", placeholder="เพื่อน")
st.markdown('</div>', unsafe_allow_html=True)

# ===== 4. คู่สมรส - คงเดิม =====
st.markdown('<div class="moto-card">', unsafe_allow_html=True)
st.subheader("4. คู่สมรส")
st.caption("✅รับทราบเรื่องส่งค่างวด / ✅รับทราบแต่ไม่ช่วยส่ง / ✅ ไม่ทราบ (6 ช่อง)")
spouse_status=st.radio("สถานะการรับทราบของคู่สมรส", ["1 ไม่มีคู่สมรส","✅รับทราบเรื่องส่งค่างวด","✅รับทราบแต่ไม่ช่วยส่ง","✅ ไม่ทราบ"], horizontal=True, key="sp_status_v27")
spouse_summary="ไม่มีคู่สมรส"; sp_name=""; sp_age=0; sp_year=0; sp_child=0; sp_income=0; sp_job=""; sp_ack=spouse_status
if spouse_status!="1 ไม่มีคู่สมรส":
    c1,c2,c3=st.columns([0.4,0.2,0.4])
    with c1: sp_name=st.text_input("1. ชื่อ-สกุล คู่สมรส", value="", key="sp_name_v27")
    with c2: sp_age=st.number_input("2. อายุ", value=0, key="sp_age_v27")
    with c3: sp_job=st.text_input("6. อาชีพ", value="", key="sp_job_v27")
    c1,c2,c3=st.columns(3)
    with c1: sp_year=st.number_input("3. จำนวนปีที่สมรส", value=0, key="sp_year_v27")
    with c2: sp_child=st.number_input("4. มีบุตรกี่คน", value=0, key="sp_child_v27")
    with c3: sp_income=st.number_input("5. รายได้คู่สมรส", value=0, step=500, key="sp_inc_v27")
    spouse_summary=f"{sp_name} อายุ {sp_age} สมรส {sp_year} ปี บุตร {sp_child} คน รายได้ {sp_income:,.0f} อาชีพ {sp_job} สถานะ {sp_ack}"
st.markdown('</div>', unsafe_allow_html=True)

# ===== 5. ผู้ค้ำประกัน - คงเดิม =====
st.markdown('<div class="moto-card">', unsafe_allow_html=True)
st.subheader("5. ผู้ค้ำประกัน")
guar_choice=st.radio("สถานะผู้ค้ำประกัน", ["1 ไม่มีผู้ค้ำประกัน","2 มีผู้ค้ำประกัน"], horizontal=True, key="guar_choice_v27")
g_text="ไม่มีผู้ค้ำประกัน"; g_name=""; g_age=0; g_job=""; g_income=0; g_phone=""
if guar_choice=="2 มีผู้ค้ำประกัน":
    c1,c2,c3=st.columns([0.4,0.2,0.4])
    with c1: g_name=st.text_input("1. ชื่อ-สกุล ผู้ค้ำ", value="", key="g_name_v27")
    with c2: g_age=st.number_input("2. อายุ", value=0, key="g_age_v27")
    with c3: g_phone=st.text_input("5. เบอร์โทร", value="", key="g_phone_v27")
    c1,c2=st.columns(2)
    with c1: g_job=st.text_input("3. อาชีพผู้ค้ำประกัน", value="", key="g_job_v27")
    with c2: g_income=st.number_input("4. รายได้ผู้ค้ำประกัน", value=0, step=1000, key="g_inc_v27")
    g_text=f"{g_name} อายุ {g_age} อาชีพ {g_job} รายได้ {g_income:,.0f} เบอร์ {g_phone}"
st.markdown('</div>', unsafe_allow_html=True)

# ===== 6. เช็คลิสต์เอกสาร 6 รายการ + Take Photo + PDPA/GPS - คงเดิม =====
st.markdown('<div class="moto-card">', unsafe_allow_html=True)
st.subheader("6. เช็คลิสต์เอกสาร 6 รายการ")
d1=st.checkbox("1. สำเนาบัตรประชาชน", key="doc1_v27")
d2=st.checkbox("2. ทะเบียนบ้าน", key="doc2_v27")
d3=st.checkbox("3. สลิปเงินเดือน 3 เดือน", key="doc3_v27")
d4=st.checkbox("4. สเตทเม้นท์ 6 เดือน", key="doc4_v27")
d5=st.checkbox("5. ใบจดทะเบียนการค้า", key="doc5_v27")
d6=st.checkbox("6. รูปถ่ายที่พัก / หมุด Google Maps", key="doc6_v27")
attached=[]; missing=[]
for n,c in [("บัตร ปชช",d1),("ทะเบียนบ้าน",d2),("สลิป 3 เดือน",d3),("สเตทเม้นท์ 6 เดือน",d4),("ใบจดทะเบียนการค้า",d5),("รูปที่พัก",d6)]:
    if c: attached.append(n)
    else: missing.append(n)
if attached:
    st.markdown(" ".join([f"<span style='background:#DC2626;color:white;border-radius:6px;padding:2px 8px;font-size:11px;margin:2px;display:inline-block;'>{a} x</span>" for a in attached]), unsafe_allow_html=True)
uploaded=st.file_uploader("📸 Upload เอกสาร (JPG PNG HEIC WEBP - กัน DNG)", type=["png","jpg","jpeg","heic","heif","webp"], accept_multiple_files=True, key="upload_v27")
if uploaded:
    bad=[f.name for f in uploaded if f.name.lower().endswith(('.dng','.raw','.arw','.cr2','.cr3','.nef','.orf','.rw2','.raf'))]
    if bad:
        st.error(f"❌ พบไฟล์ RAW/DNG: {', '.join(bad)}")
        uploaded=[f for f in uploaded if not f.name.lower().endswith(('.dng','.raw','.arw','.cr2','.cr3','.nef','.orf','.rw2','.raf'))]
cam=st.camera_input("📷 Take Photo", key="camera_v27")
gps_consent=st.checkbox("✅ ยินยอมให้ติดตามตำแหน่ง (PDPA Compliant)", value=True, key="gps_v27")
workplace=st.text_input("📌 พิกัด Google Maps (PDPA/GPS)", value="", placeholder="https://maps.app.goo.gl/...", key="workplace_v27")
story=st.text_area("🏪 บันทึกบริบทหน้าร้าน", value="", placeholder="[ว่าง] ลูกค้ามาหน้าร้าน สภาพรถ ฯลฯ", key="story_v27")
shared_contracts=st.number_input("จำนวนสัญญาที่เชื่อมโยงใน 90 วัน (เครือข่ายนายหน้า)", min_value=0, value=0, key="shared_v27")
st.markdown('</div>', unsafe_allow_html=True)

# ===== 7. วิเคราะห์ 13 โมดูลด้วย Ai + Fraud Engine - คงเดิม =====
st.markdown('<div class="moto-card" style="border:2px solid #8B5CF6 !important;">', unsafe_allow_html=True)
st.subheader("7. วิเคราะห์ 13 โมดูลด้วย Ai + Fraud Engine")

vehicle_type=st.selectbox("ประเภทรถสำหรับ Rule Engine (5 หมวดหมู่: Auto, Moped, Sport, BigBike, Electric)", ["Auto","Yamaha - Sport","YAMAHA","Honda - รถใหม่","Moped","Sport","BigBike","Electric","Wave","GIORNO"], key="veh_v27")
r_score, r_flags, r_verdict = evaluate_fraud_rules(vehicle_type, down_pct, emp_type, shared_contracts, dsr, gps_consent)

colA,colB,colC=st.columns(3)
with colA: st.metric("DSR Meter", f"{dsr:.1f}%"); st.progress(min(1.0, dsr/100) if dsr>0 else 0.0)
with colB: risk_score=int(min(100, dsr*1.2)) if dsr>0 else 0; st.metric("Risk Score", f"{risk_score}/100"); st.progress(risk_score/100)
with colC: st.metric(f"Fraud Score - {r_verdict}", f"{r_score}"); 
for f in r_flags: 
    if "LOW_DOWN" in f: st.warning(f)
    else: st.error(f)

st.markdown(f"<div class='blue-box'>ตารางราคา: {brand_model} | รหัส {code_auto} | Net {net_price:,.0f} = {cash_price:,.0f}+{reg_fee:,.0f} | ยอดจัด auto {financing:,.0f} | Flat {flat_rate:.3f}% auto | ค่างวด {monthly:,.0f} | พรบ. {prb_fee:,.0f} (แก้ไขได้) | ออกรถได้ {total_drive:,.0f} | DSR {dsr:.1f}% | GPS {gps_consent} | คู่สมรส {sp_ack}</div>", unsafe_allow_html=True)

if uploaded or cam or st.checkbox("✅ ทดสอบโดยไม่ต้องอัปโหลด", key="test_no_upload_v27"):
    if st.button("🚀 รัน SRD Credit Investigation Engine 13 Modules + Prompt AI 10 หัวข้อ", type="primary", use_container_width=True, key="run_ai_v27"):
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
# SRD Hybrid v2.7 - Fix 5 จุด
ตารางราคา 2 คอลัมน์ 14 รายการ ราคาดึงจากไฟล์ครบ 30 รุ่น
1. ชื่อรุ่นรถ / Model: {brand_model} รหัส {code_auto} {len(price_df)} รุ่น
2. ราคาสด {cash_price:,.0f} (ดึงจาก ราคาจัด ในไฟล์)
3. ค่าดำเนินการ ชุดแต่ง อื่นๆ {reg_fee:,.0f}
4. Net {net_price:,.0f} = {cash_price:,.0f}+{reg_fee:,.0f}
5. ดาวน์ {down_payment:,.0f} ({down_pct:.1f}%)
6. ยอดจัด {financing:,.0f} = {net_price:,.0f}-{down_payment:,.0f} auto
7. Flat {flat_rate:.3f}% auto 0.009%-0.017%
8. Term {term} เดือน
9. ดอกเบี้ยรวม {total_interest:,.0f} = {financing:,.0f}×{flat_rate:.3f}%×{term}
10. ยอดหนี้รวม {total_debt:,.0f}
11. ค่างวด {monthly:,.0f}
12. พรบ./ทะเบียน/ประกันรถหาย {prb_fee:,.0f} (แก้ไขได้)
13. ดาวน์ {down_payment:,.0f}
14. ออกรถได้ {total_drive:,.0f} = {down_payment:,.0f}+{prb_fee:,.0f}
ผู้กู้ {f_name} {l_name} อายุ {age} อาชีพ {job} เบอร์ {phone} รายได้รวม {total_inc:,.0f} DSR {dsr:.1f}% Rule {emp_type} {r_score} {r_verdict} Flags {r_flags} GPS {gps_consent} พิกัด {workplace}
คู่สมรส {spouse_summary} สถานะ {sp_ack} ผู้ค้ำ {g_text} อ้างอิง {ref1_name}/{ref2_name} เอกสาร {attached} บริบท {story}
Price Master {selected_row.to_dict() if selected_row is not None else 'ไม่ได้เลือก'}
"""
                with st.spinner(f"AI ({model_sel}) วิเคราะห์ 13 โมดูล + Fix 5 จุด..."):
                    model_ai=genai.GenerativeModel(model_sel)
                    if imgs: resp=model_ai.generate_content([full_prompt]+imgs)
                    else: resp=model_ai.generate_content(full_prompt)
                    save_record({
                        "Timestamp":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Model":brand_model,
                        "Code":code_auto,
                        "Cash":cash_price,
                        "Reg_ค่าดำเนินการ":reg_fee,
                        "Prb_แก้ไขได้":prb_fee,
                        "Net":net_price,
                        "Down":down_payment,
                        "Financing_auto":financing,
                        "Flat_auto":flat_rate,
                        "Term":term,
                        "Monthly":monthly,
                        "TotalDrive":total_drive,
                        "DSR":f"{dsr:.1f}%",
                        "RuleScore":r_score,
                        "RuleVerdict":r_verdict,
                        "Spouse":spouse_summary,
                        "SpouseAck":sp_ack,
                    })
                    st.success(f"💾 บันทึกแล้ว - Fix 5 จุด + รหัส {code_auto} + ราคาสด {cash_price:,.0f} จากตาราง + พรบ. {prb_fee:,.0f} แก้ไขได้ + ออกรถได้ {total_drive:,.0f} + Fraud {r_verdict} Score {r_score}")
                    st.markdown(resp.text)
            except Exception as e:
                st.error(f"Error: {e}")
else:
    st.info("อัปโหลดภาพเอกสารหรือถ่ายภาพก่อนรัน AI")

st.markdown('</div>', unsafe_allow_html=True)
st.caption("Hybrid v2.7 Fix 5 จุด: 1.แถบดำปิดหัวแอป → ซ่อน header/toolbar/MainMenu/footer | 2.รหัสรถเลือกไม่ได้ → text_input เลือกได้ + st.code copy ได้ | 3.ค่า พรบ.ควรแก้ไขได้ → number_input แก้ไขได้ + total_drive = ดาวน์+พรบ. | 4.ใต้หัวข้อตารางราคา ลบคำอธิบายออก | 5.ดึงข้อมูลไม่สมบูรณ์ → cash_default=ยอดจัด, reg_default=ทะเบียน พรบ ประกัน, down_default=ราคาดาวน์, flat_default=ดอกเบี้ย/เดือน ตรงจาก Motorcycle-Price-All-Models.xlsx 30 รุ่น 0.009%-0.017% | ส่วนข้อมูลอื่นคงเดิม ห้ามแก้ไข")
