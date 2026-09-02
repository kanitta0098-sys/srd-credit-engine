
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

st.set_page_config(page_title="SRD Hybrid v3.0 - Fix Model 404 gemini-2.5-flash → 2.0-flash", layout="wide", page_icon="🏍️")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;600;700;800&display=swap');
html, body, [class*="css"] { font-family:'Sarabun', sans-serif !important; }
.stApp { background:#0F172A !important; color:#E2E8F0 !important; }
/* Fix เมนูไม่หาย */
header[data-testid="stHeader"] {background:transparent !important; height:38px !important;}
div[data-testid="stToolbar"] {display:none !important;}
div[data-testid="stHeaderActionElements"] {display:none !important;}
#MainMenu {visibility:hidden !important;}
footer {visibility:hidden !important;}
button[kind="header"] {display:block !important; visibility:visible !important;}
[data-testid="collapsedControl"] {display:block !important; visibility:visible !important;}
.block-container { max-width:1480px !important; padding-top:0.2rem !important; padding-bottom:0.3rem !important;}
/* FIX ตัวหนังสือหัวข้อย่อยเล็ก - เพิ่มขนาดให้พอดี */
.moto-card { background:#1E293B !important; border:2px solid #334155 !important; border-radius:12px; padding:10px 12px !important; margin-bottom:8px !important; }
.moto-card h3 { margin:5px 0 !important; padding:3px 0 !important; font-size:20px !important; font-weight:800 !important; }
.label-col { font-weight:700 !important; font-size:14px !important; padding:4px 0 !important; margin:2px 0 !important; color:#F1F5F9 !important; line-height:1.3 !important; }
.yellow-box { background:linear-gradient(135deg,#FDE68A,#FBBF24) !important; color:#000 !important; font-weight:800; border-radius:6px; padding:7px 10px !important; border:1px solid #F59E0B; font-size:14px !important; }
.red-box { background:linear-gradient(135deg,#FECACA,#F87171) !important; color:#7F1D1D !important; font-weight:800; border-radius:6px; padding:7px 10px !important; font-size:14px !important; }
.blue-box { background:#1E3A8A !important; border:1px solid #3B82F6 !important; border-radius:6px; padding:7px 10px !important; color:#DBEAFE !important; font-size:13px !important; }
.tag-green { background:#065F46 !important; color:#6EE7B7 !important; border-radius:5px; padding:2px 8px !important; font-weight:700; font-size:12px !important; display:inline-block; margin:2px !important; }
.tag-yellow { background:#92400E !important; color:#FDE68A !important; border-radius:5px; padding:2px 8px !important; font-weight:700; font-size:12px !important; display:inline-block; margin:2px !important; }
hr.sep { border:1px dashed #334155; margin:8px 0 !important; }
div[data-baseweb="select"] > div { min-height:36px !important; height:36px !important; padding:4px 6px !important; font-size:14px !important; }
input[type="number"] { height:36px !important; padding:4px 8px !important; font-size:14px !important; }
.stNumberInput, .stSelectbox, .stTextInput { margin-bottom:3px !important; }
div.row-widget.stRadio > div { gap:8px !important; }
/* กระชับตาราง */
.compact-row { display:flex; gap:6px; align-items:center; }
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
        score+=20; flags.append("⚠️ R_HIGH_DSR_NO_TRACKING: DSR>70% ไม่มี GPS")
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
                        debug.append(f"✅ โหลดสำเร็จจาก {src_name} Sheet {sheet} header={hdr}: {len(df_final)} รุ่น")
                        break
                    except: continue
                if df_final is not None: break
        except Exception as e:
            debug.append(f"❌ {src_name} Error: {e}")
            continue
        if df_final is not None: break
    if df_final is None:
        df_final=pd.DataFrame({"รุ่นรถ":["ฟาซซิโอ้ SMK","Aerox 155   2026","Wave 125 กุญแจธรรมดา /2026  1 คัน ดำ","GIORNO+ CBS  2 คัน ขาว-ดำ    เทา-น้ำตาล"],"รหัสรถ":["BKF700","BWR100","AFS125CSBT TH","ACF125CBT"],"ยอดจัด":[49500,85900,63500,85500],"ดอกเบี้ยต่อเดือน":[0.015,0.011,0.017,0.017],"ราคาดาวน์":[0,0,6900,6900],"ทะเบียน พรบ ประกัน":[1000,1000,2000,2000]})
        debug.append("⚠️ hardcode 4 รุ่น")
    return df_final, yamaha_map, debug

HISTORY_FILE="srd_credit_assessment_history.csv"
def save_record(rec):
    df=pd.DataFrame([rec])
    if not os.path.exists(HISTORY_FILE): df.to_csv(HISTORY_FILE, index=False, encoding='utf-8-sig')
    else: df.to_csv(HISTORY_FILE, mode='a', header=False, index=False, encoding='utf-8-sig')

# SIDEBAR - คงเดิม
with st.sidebar:
    st.markdown("### 🏍️ SRD Hybrid v3.0 Fix Model")
    api_key=st.text_input("GEMINI API Key", value=st.secrets.get("GEMINI_API_KEY","") if hasattr(st,'secrets') else "", type="password", help="ใช้ GEMINI API Key จาก https://aistudio.google.com/app/apikey")
    model_sel=None; usable=[]
    # รายการโมเดลที่ยังใช้งานได้ 2026 (แก้ไข Error 404 gemini-2.5-flash is no longer available)
    FALLBACK_MODELS = [
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-1.5-flash",
        "gemini-1.5-flash-latest",
        "gemini-1.5-pro",
        "gemini-1.5-pro-latest",
        "gemini-3-flash-preview",
        "gemini-2.5-flash-lite",
    ]
    if api_key and len(api_key)>10:
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key.strip())
            try:
                for m in genai.list_models():
                    if 'generateContent' in m.supported_generation_methods:
                        name = m.name.replace("models/","")
                        # ข้ามโมเดลที่ Google ประกาศเลิกใช้
                        if "2.5-flash" in name and "lite" not in name:
                            continue
                        if name not in usable:
                            usable.append(name)
            except Exception as e:
                st.warning(f"list_models error: {e} - ใช้ fallback list")
            # รวม fallback ที่ยังใช้ได้
            for fb in FALLBACK_MODELS:
                if fb not in usable:
                    usable.append(fb)
            # เรียงให้ 2.0-flash และ 1.5-flash อยู่บน
            usable = sorted(usable, key=lambda x: (0 if "2.0-flash" in x else 1 if "1.5-flash" in x else 2))
            if usable:
                # default เลือก gemini-2.0-flash หรือ 1.5-flash
                default_idx = 0
                for i, name in enumerate(usable):
                    if "2.0-flash" == name:
                        default_idx = i
                        break
                model_sel=st.selectbox("🤖 โมเดล AI (แก้ 404: 2.5-flash → 2.0-flash/1.5-flash)", usable, index=default_idx)
                st.success(f"✅ {model_sel} พร้อมใช้งาน")
            else:
                model_sel = "gemini-2.0-flash"
                st.warning(f"⚠️ ใช้ fallback {model_sel}")
        except Exception as e: 
            st.error(f"API Key Error: {e}")
            # fallback ยังให้ใช้งานได้
            usable = FALLBACK_MODELS
            model_sel = st.selectbox("🤖 โมเดล AI (fallback)", usable, index=0)
    st.markdown("---")
    uploaded_excel=st.file_uploader("อัปโหลด Motorcycle-Price-All-Models.xlsx", type=["xlsx","xls"], key="upload_excel_master_v29")
    df_master, yamaha_map, debug_list=load_master_models_robust(file_obj=uploaded_excel)
    for d in debug_list:
        if "✅" in d: st.success(d)
    st.caption(f"รุ่นรถครบ {len(df_master)} รุ่น")
    if st.button("🔄 รีเซ็ตฟอร์มว่าง", use_container_width=True):
        st.session_state.clear(); st.rerun()
    st.markdown("---")
    uploaded_excel=st.file_uploader("อัปโหลด Motorcycle-Price-All-Models.xlsx", type=["xlsx","xls"], key="upload_excel_master_v29")
    df_master, yamaha_map, debug_list=load_master_models_robust(file_obj=uploaded_excel)
    for d in debug_list:
        if "✅" in d: st.success(d)
    st.caption(f"รุ่นรถครบ {len(df_master)} รุ่น")
    if st.button("🔄 รีเซ็ตฟอร์มว่าง", use_container_width=True):
        st.session_state.clear(); st.rerun()

st.markdown("""<div class="moto-card" style="display:flex;justify-content:space-between;align-items:center;padding:8px 12px !important;"><div><div style="font-size:22px;font-weight:800;color:#FFF;">🏍️ SRD Credit Engine Hybrid v2.9</div><div style="font-size:12px;color:#38BDF8;">ตัวหนังสือพอดี 14px | ตารางกระชับ 2 คอลัมน์ 7+7 | ราคาสดดึงจาก Motorcycle-Price-All-Models.xlsx ตามรุ่น | ปัดเศษค่างวดขึ้นลงได้ | ค่าดำเนินการ ชุดแต่ง อื่นๆ | คู่สมรส 3 ตัวเลือก | 13 โมดูล + Fraud Engine</div></div><div><span style="background:#065F46;color:#6EE7B7;border-radius:20px;padding:5px 10px;font-size:11px;">● ONLINE</span> <span style="background:#1E3A8A;color:#93C5FD;border-radius:20px;padding:5px 10px;font-size:11px;">v2.9</span></div></div>""", unsafe_allow_html=True)

# FALLBACK API
if 'api_key' not in locals() or not api_key:
    with st.expander("🔑 กรอก GEMINI API Key (กรณีไม่เห็นเมนู Sidebar - กด ☰ มุมซ้ายบน)", expanded=False):
        api_key_main = st.text_input("GEMINI API Key (สำรอง)", value="", type="password", key="api_main_v29")
        if api_key_main:
            api_key = api_key_main
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key.strip())
                if 'model_sel' not in locals() or not model_sel:
                    for m in genai.list_models():
                        if 'generateContent' in m.supported_generation_methods:
                            model_sel = m.name.replace("models/","")
                            break
                st.success(f"✅ API พร้อม - {model_sel if 'model_sel' in locals() else ''}")
            except Exception as e:
                st.error(f"API Error: {e}")

price_df, _, debug_list = load_master_models_robust(file_obj=uploaded_excel if 'uploaded_excel' in locals() else None)
model_list=price_df["รุ่นรถ"].astype(str).tolist()
price_dict={row["รุ่นรถ"]: row for _, row in price_df.iterrows()}

for d in debug_list:
    if "✅" in d: st.success(d)

# ===== 1. ตารางราคา - 2 คอลัมน์ 7+7 - กระชับ + ดึงราคาตามรุ่น =====
st.markdown('<div class="moto-card">', unsafe_allow_html=True)
st.subheader("1. ตารางราคา (ตารางคำนวณ)")

# FIX ราคาสดตัวรถ ไม่ดึงจาก Motorcycle-Price-All-Models - ใช้ session_state force update
if 'last_brand' not in st.session_state:
    st.session_state.last_brand = ""

col_left, col_right = st.columns(2, gap="small")

with col_left:
    st.markdown("**คอลัมน์ที่ 1 - ข้อมูลรถและเงินดาวน์**")
    st.markdown('<div class="label-col">1. ชื่อรุ่นรถ / Model:</div>', unsafe_allow_html=True)
    brand_model=st.selectbox("ชื่อรุ่นรถ / Model", options=["[ว่าง] เลือกรุ่นรถ"]+model_list, index=0, key="model_v29", label_visibility="collapsed")
    selected_row=price_dict.get(brand_model) if brand_model in price_dict else None

    # FIX: เมื่อเลือกรุ่น ให้ดึงราคาตามตารางขึ้น auto ทันที
    if selected_row is not None and brand_model != st.session_state.last_brand:
        st.session_state.cash_v29 = float(selected_row["ยอดจัด"]) if pd.notna(selected_row["ยอดจัด"]) else 0.0
        st.session_state.reg_v29 = float(selected_row["ทะเบียน พรบ ประกัน"]) if pd.notna(selected_row["ทะเบียน พรบ ประกัน"]) else 0.0
        st.session_state.down_v29 = float(selected_row["ราคาดาวน์"]) if pd.notna(selected_row["ราคาดาวน์"]) else 0.0
        st.session_state.flat_v29 = float(selected_row["ดอกเบี้ยต่อเดือน"]*100) if pd.notna(selected_row["ดอกเบี้ยต่อเดือน"]) else 1.5
        st.session_state.code_v29 = str(selected_row["รหัสรถ"]) if pd.notna(selected_row["รหัสรถ"]) else ""
        st.session_state.last_brand = brand_model

    st.markdown('<div class="label-col">รหัสรถ (Copy ได้):</div>', unsafe_allow_html=True)
    code_auto=st.session_state.get('code_v29', str(selected_row["รหัสรถ"]) if selected_row is not None and pd.notna(selected_row["รหัสรถ"]) else "")
    if code_auto:
        st.code(code_auto, language="text")

    st.markdown('<div class="label-col">2. ราคาสดตัวรถ (Cash Price) - ดึงจากไฟล์ตามรุ่น:</div>', unsafe_allow_html=True)
    cash_default=st.session_state.get('cash_v29', float(selected_row["ยอดจัด"]) if selected_row is not None and pd.notna(selected_row["ยอดจัด"]) else 49500.0)
    cash_price=st.number_input("ราคาสดตัวรถ", value=cash_default, step=100.0, key="cash_v29", label_visibility="collapsed", help="ดึงจาก ราคาจัด ใน Motorcycle-Price-All-Models.xlsx ตามรุ่นที่เลือก - แก้ไขได้")

    st.markdown('<div class="label-col">3. ค่าดำเนินการ ชุดแต่ง อื่นๆ:</div>', unsafe_allow_html=True)
    reg_default=st.session_state.get('reg_v29', float(selected_row["ทะเบียน พรบ ประกัน"]) if selected_row is not None and pd.notna(selected_row["ทะเบียน พรบ ประกัน"]) else 0.0)
    reg_fee=st.number_input("ค่าดำเนินการ ชุดแต่ง อื่นๆ", value=reg_default, step=100.0, key="reg_v29", label_visibility="collapsed")

    net_price=cash_price+reg_fee
    st.markdown('<div class="label-col">4. รวมราคารถสุทธิ (Net Price)</div>', unsafe_allow_html=True)
    st.markdown(f"<div class='yellow-box'>Net = {cash_price:,.0f} + {reg_fee:,.0f} = {net_price:,.0f}</div>", unsafe_allow_html=True)

    st.markdown('<div class="label-col">5. เงินดาวน์ (Down Payment):</div>', unsafe_allow_html=True)
    down_default=st.session_state.get('down_v29', float(selected_row["ราคาดาวน์"]) if selected_row is not None and pd.notna(selected_row["ราคาดาวน์"]) else 8900.0)
    down_payment=st.number_input("เงินดาวน์", value=down_default, step=100.0, key="down_v29", label_visibility="collapsed")

    financing=net_price-down_payment
    st.markdown('<div class="label-col">6. ยอดจัดไฟแนนซ์ (Financing Amount)</div>', unsafe_allow_html=True)
    st.markdown(f"<div class='yellow-box'>ยอดจัด = {net_price:,.0f} - {down_payment:,.0f} = {financing:,.0f} (auto)</div>", unsafe_allow_html=True)

    st.markdown('<div class="label-col">7. อัตราดอกเบี้ยต่อเดือน (Flat Rate / Month %):</div>', unsafe_allow_html=True)
    flat_default=st.session_state.get('flat_v29', float(selected_row["ดอกเบี้ยต่อเดือน"]*100) if selected_row is not None and pd.notna(selected_row["ดอกเบี้ยต่อเดือน"]) else 1.5)
    flat_rate=st.number_input("Flat Rate", value=flat_default, step=0.05, format="%.3f", key="flat_v29", label_visibility="collapsed")

with col_right:
    st.markdown("**คอลัมน์ที่ 2 - เงื่อนไขผ่อนและสรุปค่าใช้จ่าย**")
    st.markdown('<div class="label-col">8. ระยะเวลาผ่อน (จำนวนงวด / Months)</div>', unsafe_allow_html=True)
    term_options=[12,18,24,30,36,48,55,62]
    term_sel=st.selectbox("ระยะเวลาผ่อน", options=term_options, index=5, key="term_v29", label_visibility="collapsed")
    custom=st.checkbox("✏️ กำหนดเอง 6-84", key="custom_term_v29")
    term=st.number_input("Term กำหนดเอง", min_value=6, max_value=84, value=term_sel, step=1, key="term_custom_v29", label_visibility="collapsed") if custom else term_sel

    total_interest=financing*(flat_rate/100)*term
    total_debt=financing+total_interest
    monthly_raw=total_debt/term if term>0 else 0

    st.markdown('<div class="label-col">9. รวมดอกเบี้ยทั้งหมด (Total Interest)</div>', unsafe_allow_html=True)
    st.markdown(f"<div class='blue-box'>ดอกเบี้ย = {financing:,.0f} × {flat_rate:.3f}% × {term} = {total_interest:,.0f}</div>", unsafe_allow_html=True)

    st.markdown('<div class="label-col">10. ยอดหนี้รวมทั้งหมด (Total Debt)</div>', unsafe_allow_html=True)
    st.markdown(f"<div class='yellow-box'>ยอดหนี้ = {financing:,.0f} + {total_interest:,.0f} = {total_debt:,.0f}</div>", unsafe_allow_html=True)

    st.markdown('<div class="label-col">11. ค่างวดต่อเดือน (Monthly Payment) - ปัดเศษขึ้นลงได้:</div>', unsafe_allow_html=True)
    round_type=st.selectbox("วิธีปัดเศษค่างวด", options=["ไม่ปัดเศษ","ปัดขึ้น","ปัดลง","ปัดขึ้น 10 บ.","ปัดลง 10 บ.","ปัดขึ้น 100 บ.","ปัดลง 100 บ."], index=0, key="round_type_v29", label_visibility="collapsed")
    if round_type=="ปัดขึ้น": monthly_final=math.ceil(monthly_raw)
    elif round_type=="ปัดลง": monthly_final=math.floor(monthly_raw)
    elif round_type=="ปัดขึ้น 10 บ.": monthly_final=math.ceil(monthly_raw/10)*10
    elif round_type=="ปัดลง 10 บ.": monthly_final=math.floor(monthly_raw/10)*10
    elif round_type=="ปัดขึ้น 100 บ.": monthly_final=math.ceil(monthly_raw/100)*100
    elif round_type=="ปัดลง 100 บ.": monthly_final=math.floor(monthly_raw/100)*100
    else: monthly_final=monthly_raw

    if round_type!="ไม่ปัดเศษ":
        st.markdown(f"<div class='blue-box' style='background:#0F172A !important; border:1px dashed #475569 !important;'>ดิบ = {total_debt:,.0f}/{term} = {monthly_raw:,.2f}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='red-box'>ปัด {round_type} = {monthly_final:,.0f} บ.</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='red-box'>ค่างวด = {total_debt:,.0f}/{term} = {monthly_raw:,.0f} บ.</div>", unsafe_allow_html=True)
    monthly=monthly_final

    st.markdown('<hr class="sep">', unsafe_allow_html=True)
    st.markdown("**-- สรุปค่าใช้จ่ายออกรถ --**")

    st.markdown('<div class="label-col">12. ค่า พรบ./ทะเบียน/ประกันรถหาย (แก้ไขได้):</div>', unsafe_allow_html=True)
    prb_fee=st.number_input("12. ค่า พรบ./ทะเบียน/ประกันรถหาย", value=reg_default, step=100.0, key="prb_fee_v29", label_visibility="collapsed")

    st.markdown('<div class="label-col">13. เงินดาวน์ (Down Payment)</div>', unsafe_allow_html=True)
    st.markdown(f"<div class='yellow-box' style='background:#FEF3C7 !important; color:#000 !important;'>ดาวน์ = {down_payment:,.0f}</div>", unsafe_allow_html=True)

    total_drive=down_payment+prb_fee
    st.markdown('<div class="label-col">14. ออกรถได้</div>', unsafe_allow_html=True)
    st.markdown(f"<div class='red-box' style='text-align:center;'>ออกรถได้ = {down_payment:,.0f} + {prb_fee:,.0f} = {total_drive:,.0f} บ.</div>", unsafe_allow_html=True)

down_pct=(down_payment/net_price*100) if net_price>0 else 0
st.markdown(f"<div class='blue-box' style='margin-top:6px !important;'>💡 {brand_model} | รหัส {code_auto} | ราคาสด {cash_price:,.0f} ดึงจากไฟล์ตามรุ่น | Net {net_price:,.0f} | ยอดจัด {financing:,.0f} | Flat {flat_rate:.3f}% | ค่างวด {monthly_raw:,.2f} → {monthly:,.0f} ({round_type}) | ออกรถได้ {total_drive:,.0f}</div>", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# ===== 2-7 คงเดิม ห้ามแก้ไข =====
st.markdown('<div class="moto-card">', unsafe_allow_html=True)
st.subheader("2. ข้อมูลผู้เช่าซื้อ")
c1, c2, c3 = st.columns([0.4,0.4,0.2])
with c1: f_name=st.text_input("ชื่อ", value="", key="fname_v29")
with c2: l_name=st.text_input("สกุล", value="", key="lname_v29")
with c3: age=st.number_input("อายุ", min_value=0, max_value=80, value=0, key="age_v29")
c1, c2, c3 = st.columns([0.35,0.35,0.3])
with c1: job=st.text_input("อาชีพ", value="", key="job_v29")
with c2: phone=st.text_input("เบอร์โทร", value="", key="phone_v29")
with c3: emp_type=st.selectbox("ประเภทอาชีพ Rule", ["พนักงานประจำ","เจ้าของกิจการ","ฟรีแลนซ์/รับจ้างทั่วไป","ว่างงาน/ไม่มีงานประจำ"], key="emp_v29")
c1, c2, c3, c4 = st.columns(4)
with c1: residence=st.selectbox("ที่พัก", ["[ว่าง]","บ้านตนเอง/ปลอดภาระ","บ้านตนเอง/ติดผ่อน","บ้านเช่า/หอพัก","บ้านญาติ"], key="res_v29")
with c2: salary=st.number_input("เงินเดือน", value=0, step=500, key="sal_v29")
with c3: extra=st.number_input("รายได้เสริม", value=0, step=500, key="extra_v29")
with c4: debt_monthly=st.number_input("หนี้เดิม/เดือน", value=0, step=100, key="debt_monthly_v29")
living=st.number_input("ค่าใช้ชีวิต/เดือน", value=0, step=500, key="live_v29")
total_inc=salary+extra
total_bur=debt_monthly+living+monthly
dsr=(total_bur/total_inc*100) if total_inc>0 else 0
m1,m2,m3=st.columns(3)
with m1: st.metric("รายได้รวม", f"{total_inc:,.0f}")
with m2: st.metric("ภาระรวม", f"{total_bur:,.0f}")
with m3: st.metric("DSR %", f"{dsr:.1f}%")
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="moto-card">', unsafe_allow_html=True)
st.subheader("3. บุคคลอ้างอิง")
r1,r2=st.columns(2)
with r1:
    st.markdown("**อ้างอิง 1**")
    c1,c2,c3=st.columns([0.5,0.25,0.25])
    with c1: ref1_name=st.text_input("ชื่อ-สกุล 1", value="", key="ref1_name_v29", label_visibility="collapsed", placeholder="ชื่อ-สกุล 1")
    with c2: ref1_phone=st.text_input("เบอร์ 1", value="", key="ref1_phone_v29", label_visibility="collapsed", placeholder="เบอร์")
    with c3: ref1_rel=st.text_input("สัมพันธ์ 1", value="", key="ref1_rel_v29", label_visibility="collapsed", placeholder="พี่ชาย")
with r2:
    st.markdown("**อ้างอิง 2**")
    c1,c2,c3=st.columns([0.5,0.25,0.25])
    with c1: ref2_name=st.text_input("ชื่อ-สกุล 2", value="", key="ref2_name_v29", label_visibility="collapsed", placeholder="ชื่อ-สกุล 2")
    with c2: ref2_phone=st.text_input("เบอร์ 2", value="", key="ref2_phone_v29", label_visibility="collapsed", placeholder="เบอร์")
    with c3: ref2_rel=st.text_input("สัมพันธ์ 2", value="", key="ref2_rel_v29", label_visibility="collapsed", placeholder="เพื่อน")
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="moto-card">', unsafe_allow_html=True)
st.subheader("4. คู่สมรส")
spouse_status=st.radio("สถานะการรับทราบของคู่สมรส", ["1 ไม่มีคู่สมรส","✅รับทราบเรื่องส่งค่างวด","✅รับทราบแต่ไม่ช่วยส่ง","✅ ไม่ทราบ"], horizontal=True, key="sp_status_v29")
spouse_summary="ไม่มีคู่สมรส"; sp_ack=spouse_status
if spouse_status!="1 ไม่มีคู่สมรส":
    c1,c2,c3=st.columns([0.4,0.2,0.4])
    with c1: sp_name=st.text_input("1. ชื่อ-สกุล คู่สมรส", value="", key="sp_name_v29")
    with c2: sp_age=st.number_input("2. อายุ", value=0, key="sp_age_v29")
    with c3: sp_job=st.text_input("6. อาชีพ", value="", key="sp_job_v29")
    c1,c2,c3=st.columns(3)
    with c1: sp_year=st.number_input("3. จำนวนปีที่สมรส", value=0, key="sp_year_v29")
    with c2: sp_child=st.number_input("4. มีบุตรกี่คน", value=0, key="sp_child_v29")
    with c3: sp_income=st.number_input("5. รายได้คู่สมรส", value=0, step=500, key="sp_inc_v29")
    spouse_summary=f"{sp_name} อายุ {sp_age} สมรส {sp_year} ปี บุตร {sp_child} คน รายได้ {sp_income:,.0f} อาชีพ {sp_job} สถานะ {sp_ack}"
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="moto-card">', unsafe_allow_html=True)
st.subheader("5. ผู้ค้ำประกัน")
guar_choice=st.radio("สถานะผู้ค้ำประกัน", ["1 ไม่มีผู้ค้ำประกัน","2 มีผู้ค้ำประกัน"], horizontal=True, key="guar_choice_v29")
g_text="ไม่มีผู้ค้ำประกัน"
if guar_choice=="2 มีผู้ค้ำประกัน":
    c1,c2,c3=st.columns([0.4,0.2,0.4])
    with c1: g_name=st.text_input("1. ชื่อ-สกุล ผู้ค้ำ", value="", key="g_name_v29")
    with c2: g_age=st.number_input("2. อายุ", value=0, key="g_age_v29")
    with c3: g_phone=st.text_input("5. เบอร์โทร", value="", key="g_phone_v29")
    c1,c2=st.columns(2)
    with c1: g_job=st.text_input("3. อาชีพผู้ค้ำประกัน", value="", key="g_job_v29")
    with c2: g_income=st.number_input("4. รายได้ผู้ค้ำประกัน", value=0, step=1000, key="g_inc_v29")
    g_text=f"{g_name} อายุ {g_age} อาชีพ {g_job} รายได้ {g_income:,.0f} เบอร์ {g_phone}"
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="moto-card">', unsafe_allow_html=True)
st.subheader("6. เช็คลิสต์เอกสาร 6 รายการ")
d1=st.checkbox("1. สำเนาบัตรประชาชน", key="doc1_v29")
d2=st.checkbox("2. ทะเบียนบ้าน", key="doc2_v29")
d3=st.checkbox("3. สลิปเงินเดือน 3 เดือน", key="doc3_v29")
d4=st.checkbox("4. สเตทเม้นท์ 6 เดือน", key="doc4_v29")
d5=st.checkbox("5. ใบจดทะเบียนการค้า", key="doc5_v29")
d6=st.checkbox("6. รูปถ่ายที่พัก / หมุด Google Maps", key="doc6_v29")
attached=[]; missing=[]
for n,c in [("บัตร ปชช",d1),("ทะเบียนบ้าน",d2),("สลิป 3 เดือน",d3),("สเตทเม้นท์ 6 เดือน",d4),("ใบจดทะเบียนการค้า",d5),("รูปที่พัก",d6)]:
    if c: attached.append(n)
    else: missing.append(n)
uploaded=st.file_uploader("📸 Upload เอกสาร (JPG PNG HEIC WEBP - กัน DNG)", type=["png","jpg","jpeg","heic","heif","webp"], accept_multiple_files=True, key="upload_v29")
if uploaded:
    bad=[f.name for f in uploaded if f.name.lower().endswith(('.dng','.raw','.arw','.cr2','.cr3','.nef','.orf','.rw2','.raf'))]
    if bad:
        st.error(f"❌ พบไฟล์ RAW/DNG: {', '.join(bad)}")
        uploaded=[f for f in uploaded if not f.name.lower().endswith(('.dng','.raw','.arw','.cr2','.cr3','.nef','.orf','.rw2','.raf'))]
cam=st.camera_input("📷 Take Photo", key="camera_v29")
gps_consent=st.checkbox("✅ ยินยอมให้ติดตามตำแหน่ง (PDPA Compliant)", value=True, key="gps_v29")
workplace=st.text_input("📌 พิกัด Google Maps (PDPA/GPS)", value="", key="workplace_v29")
story=st.text_area("🏪 บันทึกบริบทหน้าร้าน", value="", key="story_v29")
shared_contracts=st.number_input("จำนวนสัญญาที่เชื่อมโยงใน 90 วัน (เครือข่ายนายหน้า)", min_value=0, value=0, key="shared_v29")
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="moto-card" style="border:2px solid #8B5CF6 !important;">', unsafe_allow_html=True)
st.subheader("7. วิเคราะห์ 13 โมดูลด้วย Ai + Fraud Engine")
vehicle_type=st.selectbox("ประเภทรถสำหรับ Rule Engine", ["Auto","Yamaha - Sport","YAMAHA","Honda - รถใหม่","Moped","Sport","BigBike","Electric","Wave","GIORNO"], key="veh_v29")
r_score, r_flags, r_verdict = evaluate_fraud_rules(vehicle_type, down_pct, emp_type, shared_contracts, dsr, gps_consent)
colA,colB,colC=st.columns(3)
with colA: st.metric("DSR Meter", f"{dsr:.1f}%"); st.progress(min(1.0, dsr/100) if dsr>0 else 0.0)
with colB: risk_score=int(min(100, dsr*1.2)) if dsr>0 else 0; st.metric("Risk Score", f"{risk_score}/100"); st.progress(risk_score/100)
with colC: st.metric(f"Fraud Score - {r_verdict}", f"{r_score}"); 
for f in r_flags: 
    if "LOW_DOWN" in f: st.warning(f)
    else: st.error(f)
st.markdown(f"<div class='blue-box'>ตารางราคา: {brand_model} | รหัส {code_auto} | Net {net_price:,.0f} | ยอดจัด {financing:,.0f} | Flat {flat_rate:.3f}% | ค่างวด {monthly_raw:,.2f}→{monthly:,.0f} | ออกรถได้ {total_drive:,.0f}</div>", unsafe_allow_html=True)
if uploaded or cam or st.checkbox("✅ ทดสอบโดยไม่ต้องอัปโหลด", key="test_no_upload_v29"):
    if st.button("🚀 รัน SRD Credit Investigation Engine 13 Modules + Prompt AI 10 หัวข้อ", type="primary", use_container_width=True, key="run_ai_v29"):
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
# SRD Hybrid v3.0 Fix Model
รุ่น {brand_model} รหัส {code_auto} ราคาสด {cash_price:,.0f} ดึงจากไฟล์ตามรุ่น Net {net_price:,.0f} ยอดจัด {financing:,.0f} Flat {flat_rate:.3f}% ค่างวด {monthly_raw:,.2f}→{monthly:,.0f} {round_type} ออกรถได้ {total_drive:,.0f}
ผู้กู้ {f_name} {l_name} DSR {dsr:.1f}% {r_verdict} {r_score}
"""
                with st.spinner(f"AI ({model_sel}) วิเคราะห์ 13 โมดูล..."):
                    # FIX 404 This model models/gemini-2.5-flash is no longer available
                    def run_with_fallback(prompt_text, images_list, primary_model):
                        models_to_try = [primary_model] + ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-flash-latest", "gemini-2.0-flash-lite", "gemini-3-flash-preview"]
                        last_err = None
                        for m_name in models_to_try:
                            try:
                                model_ai=genai.GenerativeModel(m_name)
                                if images_list:
                                    resp=model_ai.generate_content([prompt_text]+images_list)
                                else:
                                    resp=model_ai.generate_content(prompt_text)
                                return resp, m_name
                            except Exception as e:
                                err_str = str(e)
                                if "404" in err_str or "is no longer available" in err_str or "not found" in err_str.lower():
                                    last_err = e
                                    continue
                                else:
                                    raise e
                        raise last_err if last_err else Exception("All models failed")
                    resp, used_model = run_with_fallback(full_prompt, imgs, model_sel)
                    if used_model != model_sel:
                        st.warning(f"⚠️ {model_sel} ไม่พร้อมใช้งาน (404) - สลับไปใช้ {used_model} อัตโนมัติ")
                        model_sel = used_model
                    save_record({
                        "Timestamp":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Model":brand_model,
                        "Code":code_auto,
                        "Cash":cash_price,
                        "Net":net_price,
                        "Down":down_payment,
                        "Financing_auto":financing,
                        "Flat_auto":flat_rate,
                        "Term":term,
                        "MonthlyRaw":monthly_raw,
                        "RoundType":round_type,
                        "MonthlyFinal":monthly,
                        "TotalDrive":total_drive,
                        "DSR":f"{dsr:.1f}%",
                        "RuleScore":r_score,
                        "RuleVerdict":r_verdict,
                    })
                    st.success(f"💾 บันทึกแล้ว - {brand_model} ราคาสด {cash_price:,.0f} ตามรุ่น + ค่างวด {monthly:,.0f}")
                    st.markdown(resp.text)
            except Exception as e:
                st.error(f"Error: {e}")
else:
    st.info("อัปโหลดภาพเอกสารหรือถ่ายภาพก่อนรัน AI")
st.markdown('</div>', unsafe_allow_html=True)
# FIX: คำอธิบายส่วนท้ายนำออกได้ - ลบ st.caption ยาวออกแล้ว
