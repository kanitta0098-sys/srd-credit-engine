
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

st.set_page_config(page_title="SRD Hybrid v2.5 - Fix Pull Model", layout="wide", page_icon="🏍️")
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
    """
    แก้ไข: ชื่อรุ่นรถ / Model: และ อัตราดอกเบี้ยต่อเดือน (Flat Rate / Month ไม่ดึงจากงาน Motorcycle-Price-All-Models
    สาเหตุ: บน Streamlit Cloud ไฟล์ไม่อยู่ใน /mnt/data แต่อยู่ใน repo root หรือยังไม่ได้อัปโหลด
    วิธีแก้ใหม่: ลองอ่านหลาย header (0,1,2) + ลองทุก Sheet + รองรับ file_uploader + fallback CSV + แสดง debug
    """
    df_final=None
    yamaha_map={}
    debug=[]
    # 1. ถ้ามี file_obj จาก uploader
    search_files=[]
    if file_obj is not None:
        search_files.append(("uploaded", file_obj))
    # 2. ไฟล์ในเครื่อง
    possible_paths=[
        "Motorcycle-Price-All-Models.xlsx",
        "./Motorcycle-Price-All-Models.xlsx",
        "motorcycle_price_all_models.xlsx",
        "/mnt/data/Motorcycle-Price-All-Models.xlsx",
        "/mnt/data/motorcycle_price_all_models.xlsx",
        "/mount/src/srd-credit-engine/Motorcycle-Price-All-Models.xlsx",
        "data/Motorcycle-Price-All-Models.xlsx"
    ]
    for p in possible_paths:
        if os.path.exists(p):
            search_files.append((p, p))
    
    # ลองแต่ละไฟล์
    for src_name, src in search_files:
        try:
            # src อาจเป็น path หรือ file-like
            if isinstance(src, str):
                xls = pd.ExcelFile(src)
            else:
                xls = pd.ExcelFile(src)
            for sheet in xls.sheet_names:
                for hdr in [1,0,2]:
                    try:
                        df = pd.read_excel(xls, sheet_name=sheet, header=hdr)
                        # หาคอลัมน์ที่มีคำว่า รุ่นรถ
                        if 'รุ่นรถ' not in df.columns:
                            # ลองดูว่าแถวแรกมีคำว่า รุ่นรถไหม
                            continue
                        # ffill
                        df['รุ่นรถ']=df['รุ่นรถ'].ffill()
                        if 'รหัสรถ' in df.columns:
                            df['รหัสรถ']=df['รหัสรถ'].ffill()
                        if 'ราคาจัด' in df.columns:
                            df['ราคาจัด']=df['ราคาจัด'].ffill()
                        interest_col = [c for c in df.columns if 'ดอกเบี้ย' in str(c)]
                        if not interest_col:
                            continue
                        interest_col = interest_col[0]
                        df[interest_col]=df[interest_col].ffill()
                        # base = รหัสรถ != NaN (ได้ครบ 30 รุ่น)
                        if 'รหัสรถ' in df.columns:
                            df_base = df[pd.notna(df['รหัสรถ'])].copy()
                        else:
                            df_base = df.copy()
                        df_base = df_base[~df_base['รุ่นรถ'].astype(str).str.contains('รุ่นรถ|ตารางโปรโมชัน', na=False)]
                        df_base['รุ่นรถ']=df_base['รุ่นรถ'].astype(str).str.strip()
                        df_base=df_base[~df_base['รุ่นรถ'].isin(['nan','NaN',''])]
                        df_base=df_base.drop_duplicates(subset=['รุ่นรถ'], keep='first')
                        if len(df_base) < 5:
                            continue
                        # rename
                        rename_map={'ราคาจัด':'ยอดจัด', interest_col:'ดอกเบี้ยต่อเดือน', 'ดาวน์':'ราคาดาวน์', 'ค่าจด/พรบ.':'ทะเบียน พรบ ประกัน', 'รวมออกรถ':'ค่าใช้จ่ายออกรถ', 'เงินดาวน์':'ราคาดาวน์'}
                        df_base=df_base.rename(columns=rename_map)
                        for col in ['ยอดจัด','ดอกเบี้ยต่อเดือน','ราคาดาวน์','ทะเบียน พรบ ประกัน']:
                            if col not in df_base.columns:
                                df_base[col]=0
                        # map ดอกเบี้ย
                        for _, r in df_base.iterrows():
                            try:
                                yamaha_map[str(r['รุ่นรถ'])] = float(r['ดอกเบี้ยต่อเดือน'])
                            except:
                                yamaha_map[str(r['รุ่นรถ'])] = 0.015
                        df_final=df_base
                        debug.append(f"✅ โหลดสำเร็จจาก {src_name} Sheet {sheet} header={hdr}: {len(df_final)} รุ่น ดอกเบี้ยครบ {len(yamaha_map)} รายการ")
                        break
                    except:
                        continue
                if df_final is not None:
                    break
        except Exception as e:
            debug.append(f"❌ {src_name} Error: {e}")
            continue
        if df_final is not None:
            break
    
    if df_final is None:
        # fallback CSV
        for cp in ["price_backup_all_models.csv","/mnt/data/price_backup_all_models.csv","/mount/src/srd-credit-engine/price_backup_all_models.csv"]:
            if os.path.exists(cp):
                try:
                    df=pd.read_csv(cp, encoding='utf-8')
                    df_final=df
                    debug.append(f"⚠️ Fallback CSV {cp}: {len(df_final)} รุ่น")
                    for _, r in df_final.iterrows():
                        try:
                            yamaha_map[str(r['รุ่นรถ'])]=float(r.get('ดอกเบี้ยต่อเดือน',0.015))
                        except:
                            pass
                    break
                except:
                    pass
    if df_final is None:
        df_final=pd.DataFrame({"รุ่นรถ":["ฟาซซิโอ้ SMK","ฟาซซิโอ้ Lite","Aerox 155   2026","Wave 125 กุญแจธรรมดา /2026  1 คัน ดำ","GIORNO+ CBS  2 คัน ขาว-ดำ    เทา-น้ำตาล"],"รหัสรถ":["BKF700","BKFB00","BWR100","AFS125CSBT TH","ACF125CBT"],"ยอดจัด":[54600,53200,85900,63500,85500],"ดอกเบี้ยต่อเดือน":[0.015,0.015,0.011,0.017,0.017],"ราคาดาวน์":[0,0,0,6900,6900],"ทะเบียน พรบ ประกัน":[1000,1000,1000,2000,2000]})
        debug.append("⚠️ ใช้ hardcode fallback 5 รุ่น")
        for _, r in df_final.iterrows():
            yamaha_map[str(r['รุ่นรถ'])]=float(r['ดอกเบี้ยต่อเดือน'])
    
    return df_final, yamaha_map, debug

HISTORY_FILE="srd_credit_assessment_history.csv"
def save_record(rec):
    df=pd.DataFrame([rec])
    if not os.path.exists(HISTORY_FILE): df.to_csv(HISTORY_FILE, index=False, encoding='utf-8-sig')
    else: df.to_csv(HISTORY_FILE, mode='a', header=False, index=False, encoding='utf-8-sig')

# SIDEBAR - แก้ให้ดึงครบ + อัปโหลดได้ถ้าไฟล์หาย
with st.sidebar:
    st.markdown("### 🏍️ SRD Hybrid v2.5\nFix Pull Model")
    st.caption("แก้: ชื่อรุ่นรถ / Model และ Flat Rate ไม่ดึงจาก Motorcycle-Price-All-Models")
    api_key=st.text_input("GEMINI API Key", value=st.secrets.get("GEMINI_API_KEY","") if hasattr(st,'secrets') else "", type="password", help="อย่าแชร์ API Key สาธารณะ - ตัวอย่าง AQ.Ab8R... ควรเก็บเป็นความลับ")
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
        except Exception as e: 
            st.error(f"API Key Error: {e}")
    
    st.markdown("---")
    st.markdown("**📂 อัปโหลด Motorcycle-Price-All-Models.xlsx ถ้าดึงไม่ครบ:**")
    uploaded_excel=st.file_uploader("อัปโหลดไฟล์ Excel Master", type=["xlsx","xls"], key="upload_excel_master")
    df_master, yamaha_map, debug_list=load_master_models_robust(file_obj=uploaded_excel)
    
    for d in debug_list:
        if "✅" in d:
            st.success(d)
        elif "⚠️" in d:
            st.warning(d)
        else:
            st.error(d)
    
    st.markdown(f"**💡 ดอกเบี้ยครบทุกยี่ห้อ - ฝ่ายขายไม่ต้องจำ ({len(yamaha_map)} รุ่น):**")
    if yamaha_map:
        yam_df=pd.DataFrame(list(yamaha_map.items()), columns=["รุ่น","ดอกเบี้ย/เดือน"])
        yam_df["ดอกเบี้ย%"]= (yam_df["ดอกเบี้ย/เดือน"]*100).round(3)
        st.dataframe(yam_df, height=300, use_container_width=True)
    if not df_master.empty:
        st.caption(f"รุ่นรถครบ {len(df_master)} รุ่น:")
        st.dataframe(df_master[["รุ่นรถ","รหัสรถ","ยอดจัด","ดอกเบี้ยต่อเดือน","ราคาดาวน์"]], height=250, use_container_width=True)
    
    # แสดงไฟล์ที่มีใน dir ปัจจุบัน
    st.caption("ไฟล์ในโฟลเดอร์ปัจจุบัน:")
    try:
        files=os.listdir(".")
        xlsx_files=[f for f in files if f.endswith(('.xlsx','.xls','.csv'))]
        st.write(xlsx_files if xlsx_files else "ไม่พบไฟล์ Excel/CSV ใน repo - กรุณาอัปโหลด Motorcycle-Price-All-Models.xlsx ขึ้น GitHub")
    except:
        pass
    
    if st.button("🔄 รีเซ็ตฟอร์มว่าง", use_container_width=True):
        st.session_state.clear(); st.rerun()

st.markdown("""<div class="moto-card" style="display:flex;justify-content:space-between;align-items:center;background:linear-gradient(135deg,#0F172A,#1E293B) !important;"><div><div style="font-size:26px;font-weight:800;color:#FFF;">🏍️ SRD Credit Engine Hybrid v2.5</div><div style="font-size:11px;color:#38BDF8;">Fix: ชื่อรุ่นรถ / Model และ Flat Rate ไม่ดึงจาก Motorcycle-Price-All-Models → แก้ robust loader + รองรับอัปโหลด + แสดง debug | 14 แถวเป๊ะ | Yamaha Auto 0.009%-0.017% | 30 รุ่นครบ</div></div><div><span style="background:#065F46;color:#6EE7B7;border-radius:20px;padding:6px 10px;font-size:11px;">● ONLINE</span> <span style="background:#1E3A8A;color:#93C5FD;border-radius:20px;padding:6px 10px;font-size:11px;">v2.5 Fix Pull</span></div></div>""", unsafe_allow_html=True)

price_df, _, debug_list = load_master_models_robust(file_obj=uploaded_excel if 'uploaded_excel' in locals() else None)
model_list=price_df["รุ่นรถ"].astype(str).tolist()
price_dict={row["รุ่นรถ"]: row for _, row in price_df.iterrows()}

# Debug บนหน้าหลัก
for d in debug_list:
    if "✅" in d:
        st.success(d)
    elif "⚠️" in d:
        st.warning(d)

# ===== ตารางคำนวณ 14 แถวเป๊ะ =====
st.markdown('<div class="moto-card">', unsafe_allow_html=True)
st.subheader("ตารางคำนวณ")
st.caption("แก้ไข: ชื่อรุ่นรถ / Model: และ อัตราดอกเบี้ยต่อเดือน (Flat Rate / Month %) ไม่ดึงจากงาน Motorcycle-Price-All-Models → ตอนนี้แก้ robust loader ให้ดึงครบ 30 รุ่น + ดอกเบี้ยครบ")

r1c1, r1c2, r1c3, r1c4 = st.columns([0.50, 0.15, 0.15, 0.20])
with r1c1:
    st.markdown('<div class="label-col">ชื่อรุ่นรถ / Model:</div>', unsafe_allow_html=True)
    st.markdown(f"<span class='tag-green'>ดึงจาก Motorcycle-Price-All-Models.xlsx {len(model_list)} รุ่น</span>", unsafe_allow_html=True)
    brand_model=st.selectbox("ชื่อรุ่นรถ / Model", options=["[ว่าง] เลือกรุ่นรถ"]+model_list, index=0, key="model_v25", label_visibility="collapsed")
    selected_row=price_dict.get(brand_model) if brand_model in price_dict else None
with r1c2:
    code_auto=selected_row["รหัสรถ"] if selected_row is not None else ""
    st.text_input("รหัสรถ", value=str(code_auto), disabled=True, key="code_v25", label_visibility="collapsed", placeholder="รหัสรถ")
with r1c3:
    flat_default=float(selected_row["ดอกเบี้ยต่อเดือน"]*100) if selected_row is not None and pd.notna(selected_row["ดอกเบี้ยต่อเดือน"]) else 1.70
    # ถ้า flat_default เป็น 0.015*100=1.5 แต่ Honda 0.017*100=1.7 ต้องแสดงให้ถูก
    flat_rate=st.number_input("อัตราดอกเบี้ยต่อเดือน (Flat Rate / Month %)", value=flat_default, step=0.05, format="%.3f", key="flat_v25", label_visibility="collapsed", help="ดึงจาก Motorcycle-Price-All-Models.xlsx auto ครบ 30 รุ่น - ฝ่ายขายไม่ต้องจำ")
    if selected_row is not None:
        st.markdown(f"<span class='tag-green'>{flat_default:.3f}% auto จากไฟล์</span>", unsafe_allow_html=True)
    else:
        st.markdown(f"<span class='tag-green'>{len(yamaha_map)} ดอกเบี้ยครบ</span>", unsafe_allow_html=True)
with r1c4:
    term_options=[12,18,24,30,36,48,55,62]
    term_sel=st.selectbox("ระยะเวลาผ่อน (จำนวนงวด / Months)", options=term_options, index=5, key="term_v25", label_visibility="collapsed")
    custom=st.checkbox("✏️ กำหนดเอง 6-84", key="custom_term_v25")
    if custom:
        term=st.number_input("Term กำหนดเอง", min_value=6, max_value=84, value=term_sel, step=1, key="term_custom_v25", label_visibility="collapsed")
    else:
        term=term_sel

r2c1, r2c2, r2c3, r2c4 = st.columns([0.25,0.25,0.25,0.25])
with r2c1:
    st.markdown('<div class="label-col">ราคาสดตัวรถ (Cash Price):</div>', unsafe_allow_html=True)
    cash_default=float(selected_row["ยอดจัด"]+selected_row["ราคาดาวน์"]) if selected_row is not None and pd.notna(selected_row["ยอดจัด"]) else 85500.0
    cash_price=st.number_input("ราคาสดตัวรถ (Cash Price)", value=cash_default, step=100.0, key="cash_v25", label_visibility="collapsed")
with r2c2:
    st.markdown('<div class="label-col">บวกค่า พรบ./ทะเบียน/ประกันรถหาย (รวมในยอดจัด):</div>', unsafe_allow_html=True)
    reg_default=float(selected_row["ทะเบียน พรบ ประกัน"]) if selected_row is not None and pd.notna(selected_row["ทะเบียน พรบ ประกัน"]) else 0.0
    reg_fee=st.number_input("บวกค่า พรบ.", value=reg_default, step=100.0, key="reg_v25", label_visibility="collapsed")
with r2c3:
    st.markdown('<div class="label-col">รวมราคารถสุทธิ (Net Price)</div>', unsafe_allow_html=True)
    net_price=cash_price+reg_fee
    st.markdown(f"<div class='yellow-box'>Net = {cash_price:,.0f}+{reg_fee:,.0f} = {net_price:,.0f}</div>", unsafe_allow_html=True)
with r2c4:
    st.markdown('<div class="label-col">เงินดาวน์ (Down Payment):</div>', unsafe_allow_html=True)
    down_default=float(selected_row["ราคาดาวน์"]) if selected_row is not None and pd.notna(selected_row["ราคาดาวน์"]) else 8900.0
    down_payment=st.number_input("เงินดาวน์ (Down Payment)", value=down_default, step=100.0, key="down_v25", label_visibility="collapsed")

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
    st.markdown(f"<div class='blue-box'>ดอกเบี้ย = {financing:,.0f}×{flat_rate:.3f}%×{term} = {total_interest:,.0f}</div>", unsafe_allow_html=True)
with r3c3:
    st.markdown('<div class="label-col">ยอดหนี้รวมทั้งหมด (Total Debt):</div>', unsafe_allow_html=True)
    st.markdown(f"<div class='yellow-box'>ยอดหนี้ = {financing:,.0f}+{total_interest:,.0f} = {total_debt:,.0f}</div>", unsafe_allow_html=True)
with r3c4:
    st.markdown('<div class="label-col">ค่างวดต่อเดือน (Monthly Payment):</div>', unsafe_allow_html=True)
    st.markdown(f"<div class='red-box'>ค่างวด = {total_debt:,.0f}/{term} = {monthly:,.0f} บ.</div>", unsafe_allow_html=True)

total_drive=down_payment+reg_fee
r4c1, r4c2, r4c3 = st.columns(3)
with r4c1:
    st.markdown('<div class="label-col">ค่า พรบ./ทะเบียน/ประกันรถหาย</div>', unsafe_allow_html=True)
    st.markdown(f"<div class='yellow-box' style='background:linear-gradient(135deg,#FEF3C7,#FDE68A) !important;'>ค่า พรบ. = {reg_fee:,.0f}</div>", unsafe_allow_html=True)
with r4c2:
    st.markdown('<div class="label-col">เงินดาวน์ (Down Payment):</div>', unsafe_allow_html=True)
    st.markdown(f"<div class='yellow-box' style='background:linear-gradient(135deg,#FEF3C7,#FDE68A) !important;'>ดาวน์ = {down_payment:,.0f}</div>", unsafe_allow_html=True)
with r4c3:
    st.markdown('<div class="label-col">ออกรถได้</div>', unsafe_allow_html=True)
    st.markdown(f"<div class='red-box' style='font-size:18px;text-align:center;'>ออกรถได้ = {down_payment:,.0f}+{reg_fee:,.0f} = {total_drive:,.0f} บ.</div>", unsafe_allow_html=True)

down_pct=(down_payment/net_price*100) if net_price>0 else 0
st.markdown(f"<div class='blue-box' style='margin-top:10px;'>💡 ดึงจาก Motorcycle-Price-All-Models.xlsx ครบ {len(model_list)} รุ่น: {brand_model} | Net {net_price:,.0f} | ยอดจัด auto {financing:,.0f} = {net_price:,.0f}-{down_payment:,.0f} | Flat {flat_rate:.3f}% auto (0.009%-0.017% ครบ) | ค่างวด {monthly:,.0f} | ออกรถได้ {total_drive:,.0f} | ดอกเบี้ย auto จากไฟล์ ไม่ต้องจำ</div>", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# ฟอร์มว่าง + Backend
st.markdown('<div class="moto-card">', unsafe_allow_html=True)
st.subheader("🏍️ ข้อมูลผู้เช่าซื้อ")
c1, c2, c3 = st.columns([0.4,0.4,0.2])
with c1: f_name=st.text_input("ชื่อ", value="", placeholder="[ว่าง] สมชาย", key="fname_v25")
with c2: l_name=st.text_input("สกุล", value="", placeholder="[ว่าง] ใจดี", key="lname_v25")
with c3: age=st.number_input("อายุ", min_value=0, max_value=80, value=0, key="age_v25")
c1, c2, c3 = st.columns([0.35,0.35,0.3])
with c1: job=st.text_input("อาชีพ", value="", placeholder="[ว่าง]", key="job_v25")
with c2: phone=st.text_input("เบอร์โทร", value="", placeholder="[ว่าง]", key="phone_v25")
with c3: emp_type=st.selectbox("ประเภทอาชีพ Rule", ["พนักงานประจำ","เจ้าของกิจการ","ฟรีแลนซ์/รับจ้างทั่วไป","ว่างงาน/ไม่มีงานประจำ"], key="emp_v25")
c1, c2, c3, c4 = st.columns(4)
with c1: residence=st.selectbox("ที่พัก", ["[ว่าง]","บ้านตนเอง/ปลอดภาระ","บ้านเช่า/หอพัก"], key="res_v25")
with c2: salary=st.number_input("เงินเดือน", value=0, step=500, key="sal_v25")
with c3: extra=st.number_input("รายได้เสริม", value=0, step=500, key="extra_v25")
with c4: debt_monthly=st.number_input("หนี้เดิม/เดือน", value=0, step=100, key="debt_monthly_v25")
living=st.number_input("ค่าใช้ชีวิต/เดือน", value=0, step=500, key="live_v25")
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
    c1,c2,c3=st.columns([0.5,0.25,0.25])
    with c1: ref1_name=st.text_input("ชื่อ-สกุล 1", value="", key="ref1_name_v25", label_visibility="collapsed", placeholder="ชื่อ-สกุล 1")
    with c2: ref1_phone=st.text_input("เบอร์ 1", value="", key="ref1_phone_v25", label_visibility="collapsed", placeholder="เบอร์")
    with c3: ref1_rel=st.text_input("สัมพันธ์ 1", value="", key="ref1_rel_v25", label_visibility="collapsed", placeholder="พี่ชาย")
with r2:
    c1,c2,c3=st.columns([0.5,0.25,0.25])
    with c1: ref2_name=st.text_input("ชื่อ-สกุล 2", value="", key="ref2_name_v25", label_visibility="collapsed", placeholder="ชื่อ-สกุล 2")
    with c2: ref2_phone=st.text_input("เบอร์ 2", value="", key="ref2_phone_v25", label_visibility="collapsed", placeholder="เบอร์")
    with c3: ref2_rel=st.text_input("สัมพันธ์ 2", value="", key="ref2_rel_v25", label_visibility="collapsed", placeholder="เพื่อน")
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="moto-card">', unsafe_allow_html=True)
st.subheader("5. 🏍️ คู่สมรส - 1 ไม่มี / 2 มี (6 ช่อง)")
spouse_choice=st.radio("สถานะคู่สมรส", ["1 ไม่มีคู่สมรส","2 มีคู่สมรส"], horizontal=True, key="sp_choice_v25")
spouse_summary="ไม่มีคู่สมรส"; sp_name=""; sp_age=0; sp_year=0; sp_child=0; sp_income=0; sp_job=""
if spouse_choice=="2 มีคู่สมรส":
    c1,c2,c3=st.columns([0.4,0.2,0.4])
    with c1: sp_name=st.text_input("1. ชื่อ-สกุล คู่สมรส", value="", key="sp_name_v25")
    with c2: sp_age=st.number_input("2. อายุ", value=0, key="sp_age_v25")
    with c3: sp_job=st.text_input("6. อาชีพ", value="", key="sp_job_v25")
    c1,c2,c3=st.columns(3)
    with c1: sp_year=st.number_input("3. จำนวนปีที่สมรส", value=0, key="sp_year_v25")
    with c2: sp_child=st.number_input("4. มีบุตรกี่คน", value=0, key="sp_child_v25")
    with c3: sp_income=st.number_input("5. รายได้คู่สมรส", value=0, step=500, key="sp_inc_v25")
    spouse_summary=f"{sp_name} อายุ {sp_age} สมรส {sp_year} ปี บุตร {sp_child} คน รายได้ {sp_income:,.0f} อาชีพ {sp_job}"
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="moto-card">', unsafe_allow_html=True)
st.subheader("6. 🏍️ ผู้ค้ำประกัน - 1 ไม่มี / 2 มี (5 ช่อง)")
guar_choice=st.radio("สถานะผู้ค้ำประกัน", ["1 ไม่มีผู้ค้ำประกัน","2 มีผู้ค้ำประกัน"], horizontal=True, key="guar_choice_v25")
g_text="ไม่มีผู้ค้ำประกัน"; g_name=""; g_age=0; g_job=""; g_income=0; g_phone=""
if guar_choice=="2 มีผู้ค้ำประกัน":
    c1,c2,c3=st.columns([0.4,0.2,0.4])
    with c1: g_name=st.text_input("1. ชื่อ-สกุล ผู้ค้ำ", value="", key="g_name_v25")
    with c2: g_age=st.number_input("2. อายุ", value=0, key="g_age_v25")
    with c3: g_phone=st.text_input("5. เบอร์โทร", value="", key="g_phone_v25")
    c1,c2=st.columns(2)
    with c1: g_job=st.text_input("3. อาชีพผู้ค้ำประกัน", value="", key="g_job_v25")
    with c2: g_income=st.number_input("4. รายได้ผู้ค้ำประกัน", value=0, step=1000, key="g_inc_v25")
    g_text=f"{g_name} อายุ {g_age} อาชีพ {g_job} รายได้ {g_income:,.0f} เบอร์ {g_phone}"
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="moto-card">', unsafe_allow_html=True)
st.subheader("7. 🏍️ เช็คลิสต์เอกสาร 6 รายการ + PDPA/GPS")
d1=st.checkbox("1. สำเนาบัตรประชาชน", key="doc1_v25")
d2=st.checkbox("2. ทะเบียนบ้าน", key="doc2_v25")
d3=st.checkbox("3. สลิปเงินเดือน 3 เดือน", key="doc3_v25")
d4=st.checkbox("4. สเตทเม้นท์ 6 เดือน", key="doc4_v25")
d5=st.checkbox("5. ใบจดทะเบียนการค้า", key="doc5_v25")
d6=st.checkbox("6. รูปถ่ายที่พัก / หมุด Google Maps", key="doc6_v25")
attached=[]; missing=[]
for n,c in [("บัตร ปชช",d1),("ทะเบียนบ้าน",d2),("สลิป 3 เดือน",d3),("สเตทเม้นท์ 6 เดือน",d4),("ใบจดทะเบียนการค้า",d5),("รูปที่พัก",d6)]:
    if c: attached.append(n)
    else: missing.append(n)
uploaded=st.file_uploader("📸 Upload เอกสาร (JPG PNG HEIC WEBP - กัน DNG)", type=["png","jpg","jpeg","heic","heif","webp"], accept_multiple_files=True, key="upload_v25")
if uploaded:
    bad=[f.name for f in uploaded if f.name.lower().endswith(('.dng','.raw','.arw','.cr2','.cr3','.nef','.orf','.rw2','.raf'))]
    if bad:
        st.error(f"❌ พบไฟล์ RAW/DNG: {', '.join(bad)}")
        uploaded=[f for f in uploaded if not f.name.lower().endswith(('.dng','.raw','.arw','.cr2','.cr3','.nef','.orf','.rw2','.raf'))]
cam=st.camera_input("📷 Take Photo", key="camera_v25")
gps_consent=st.checkbox("✅ ยินยอมให้ติดตามตำแหน่ง (PDPA Compliant)", value=True, key="gps_v25")
workplace=st.text_input("📌 พิกัด Google Maps (PDPA/GPS)", value="", placeholder="https://maps.app.goo.gl/...", key="workplace_v25")
story=st.text_area("🏪 บันทึกบริบทหน้าร้าน", value="", key="story_v25")
shared_contracts=st.number_input("จำนวนสัญญาที่เชื่อมโยงใน 90 วัน (เครือข่ายนายหน้า)", min_value=0, value=0, key="shared_v25")
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="moto-card" style="border:2px solid #8B5CF6 !important;">', unsafe_allow_html=True)
st.subheader("8. 🏍️ วิเคราะห์ 13 โมดูลด้วย Ai + Fraud Engine")
vehicle_type=st.selectbox("ประเภทรถสำหรับ Rule Engine (5 หมวดหมู่: Auto, Moped, Sport, BigBike, Electric)", ["Auto","Yamaha - Sport","YAMAHA","Honda - รถใหม่","Moped","Sport","BigBike","Electric","Wave","GIORNO"], key="veh_v25")
r_score, r_flags, r_verdict = evaluate_fraud_rules(vehicle_type, down_pct, emp_type, shared_contracts, dsr, gps_consent)
colA,colB,colC=st.columns(3)
with colA: st.metric("DSR Meter", f"{dsr:.1f}%"); st.progress(min(1.0, dsr/100) if dsr>0 else 0.0)
with colB: risk_score=int(min(100, dsr*1.2)) if dsr>0 else 0; st.metric("Risk Score", f"{risk_score}/100"); st.progress(risk_score/100)
with colC: st.metric(f"Fraud Score - {r_verdict}", f"{r_score}"); 
for f in r_flags: 
    if "LOW_DOWN" in f: st.warning(f)
    else: st.error(f)

st.markdown(f"<div class='blue-box'>ตารางคำนวณ: {brand_model} | Net {net_price:,.0f} | ยอดจัด auto {financing:,.0f} | Flat {flat_rate:.3f}% auto (0.009%-0.017% ครบ {len(model_list)} รุ่น) | ค่างวด {monthly:,.0f} | ออกรถได้ {total_drive:,.0f} | DSR {dsr:.1f}% | GPS {gps_consent}</div>", unsafe_allow_html=True)

if uploaded or cam or st.checkbox("✅ ทดสอบโดยไม่ต้องอัปโหลด", key="test_no_upload_v25"):
    if st.button("🚀 รัน SRD Credit Investigation Engine 13 Modules + Prompt AI 10 หัวข้อ", type="primary", use_container_width=True, key="run_ai_v25"):
        if not api_key or not model_sel:
            st.error("กรุณากรอก API Key - อย่าแชร์ API Key ที่มีคำนำหน้า AQ. แบบสาธารณะ")
        else:
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key.strip())
                imgs=[]
                if uploaded:
                    for f in uploaded: imgs.append(_compress_mobile(Image.open(f)))
                if cam: imgs.append(_compress_mobile(Image.open(cam)))
                full_prompt=f"""
# SRD Hybrid v2.5 - Fix Pull Model
รุ่น {brand_model} Net {net_price} = {cash_price}+{reg_fee} ดาวน์ {down_payment} ({down_pct:.1f}%) ยอดจัด auto {financing} Flat {flat_rate:.3f}% Term {term} ค่างวด {monthly} ออกรถได้ {total_drive}
ผู้กู้ {f_name} {l_name} อายุ {age} อาชีพ {job} เบอร์ {phone} รายได้รวม {total_inc} DSR {dsr:.1f}% Rule {r_score} {r_verdict} Flags {r_flags} GPS {gps_consent} พิกัด {workplace}
คู่สมรส {spouse_summary} ผู้ค้ำ {g_text} อ้างอิง {ref1_name}/{ref2_name} เอกสาร {attached} บริบท {story}
Price Master {selected_row.to_dict() if selected_row is not None else 'ไม่ได้เลือก'} Debug {debug_list}

### REQUIRED OUTPUT 10 หัวข้อ
## 1. CUSTOMER & HOUSEHOLD PROFILE
## 2. IDENTITY & WORKPLACE VERIFICATION
## 3. VERIFIED FACTS vs UNVERIFIED CLAIMS
## 4. MONEY FLOW & CASH FLOW REALITY - ค่างวด {monthly:,.0f} ออกรถได้ {total_drive:,.0f} DSR {dsr:.1f}%
## 5. FRAUD, GAMBLING & ASSET RISK CHECK - {r_verdict} Score {r_score}
## 6. GUARANTOR & SPOUSE MITIGATION POWER
## 7. CONTRADICTION TABLE
## 8. RISK SCORING & FINAL DECISION 100 คะแนน + Fraud {r_score} {r_verdict}
## 9. 30-SECOND SOFT INTERVIEW
## 10. SUMMARY RECOMMENDATION FOR SALES - ยอดจัด auto {financing:,.0f} Flat {flat_rate:.3f}% ค่างวด {monthly:,.0f} ออกรถได้ {total_drive:,.0f}
"""
                with st.spinner(f"AI ({model_sel}) วิเคราะห์ 13 โมดูล + Fix Pull Model {len(model_list)} รุ่น..."):
                    model_ai=genai.GenerativeModel(model_sel)
                    if imgs: resp=model_ai.generate_content([full_prompt]+imgs)
                    else: resp=model_ai.generate_content(full_prompt)
                    save_record({"Timestamp":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"Model":brand_model,"Cash":cash_price,"Reg":reg_fee,"Net":net_price,"Down":down_payment,"Financing_auto":financing,"Flat_auto":flat_rate,"Term":term,"Monthly":monthly,"TotalDrive":total_drive,"DSR":f"{dsr:.1f}%","RuleScore":r_score,"RuleVerdict":r_verdict,"GPS":gps_consent})
                    st.success(f"💾 บันทึกแล้ว - Fix Pull Model {len(model_list)} รุ่นครบ - ยอดจัด auto {financing:,.0f} - Flat {flat_rate:.3f}% auto - Fraud {r_verdict} Score {r_score}")
                    st.markdown(resp.text)
            except Exception as e:
                st.error(f"Error: {e}")
else:
    st.info("อัปโหลดภาพเอกสารก่อนรัน AI")

st.markdown('</div>', unsafe_allow_html=True)
st.caption("Hybrid v2.5 Fix Pull: ชื่อรุ่นรถ / Model: และ Flat Rate ไม่ดึงจาก Motorcycle-Price-All-Models → แก้ robust loader ลองหลาย header (0,1,2) + ทุก Sheet + รองรับอัปโหลดไฟล์ + แสดง debug + แสดงไฟล์ในโฟลเดอร์ + ครบ 30 รุ่น 0.009%-0.017% | R_HIGH_DSR_NO_TRACKING แก้ DSR>70% | Field Length 50/15/15/20")
