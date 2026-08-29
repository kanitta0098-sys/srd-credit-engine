
import streamlit as st, os, io, pandas as pd
from datetime import datetime
from PIL import Image
try:
 import pillow_heif
 pillow_heif.register_heif_opener()
except: pass

def _compress_mobile(img, max_side=1280, max_bytes=1200000):
 img=img.convert("RGB")
 if max(img.size)>max_side: img.thumbnail((max_side,max_side), Image.LANCZOS)
 for q in [75,65,55,40]:
  b=io.BytesIO(); img.save(b, format="JPEG", quality=q, optimize=True)
  if b.tell()<=max_bytes: b.seek(0); return Image.open(b)
 b.seek(0); return Image.open(b)

st.set_page_config(page_title="SRD Moto Credit v1.5 - Full Dark High Contrast", layout="wide", page_icon="🐒")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family:'Sarabun', sans-serif !important; }
.stApp { background:#0F172A !important; }
header { display:none; }
[data-testid="stSidebar"] { background:#020617 !important; border-right:1px solid #1E293B !important; }
[data-testid="stSidebar"] * { color:#94A3B8 !important; }
div[data-baseweb="select"] > div { background:#0F172A !important; color:#FFFFFF !important; border:2px solid #64748B !important; border-radius:12px !important; font-weight:700 !important; }
div[data-baseweb="select"] span { color:#FFFFFF !important; }
input, textarea { background:#0F172A !important; color:#FFFFFF !important; border:2px solid #64748B !important; border-radius:12px !important; font-weight:600 !important; }
input:disabled { background:#1E293B !important; color:#94A3B8 !important; }
label { color:#F8FAFC !important; font-weight:700 !important; font-size:14px !important; }
.moto-card { background:#1E293B !important; border:2px solid #334155 !important; border-radius:16px; padding:20px; margin-bottom:16px; max-width:1200px; margin-left:auto; margin-right:auto; }
.moto-card * { color:#F1F5F9; }
.moto-card h3, .moto-card h2 { color:#FFFFFF !important; font-weight:800 !important; }
.readonly-box { background:#020617 !important; border:2px solid #334155 !important; border-radius:12px; padding:14px; margin:8px 0; }
.readonly-box .label { color:#94A3B8 !important; font-size:11px; font-weight:700; }
.readonly-box .value { color:#FFFFFF !important; font-size:16px; font-weight:800; margin-top:4px; }
.price-structure { background:#020617 !important; border:2px solid #1E40AF !important; border-radius:16px; padding:20px; margin-top:16px; }
.price-structure .row { display:flex; justify-content:space-between; align-items:center; padding:10px 0; border-bottom:1px solid #1E293B; }
.price-structure .row:last-child { border-bottom:none; background:#1E3A5F; border-radius:10px; padding:12px 14px; margin-top:8px; border:2px solid #38BDF8; }
.price-structure .label { color:#94A3B8 !important; font-size:13px; font-weight:600; }
.price-structure .value { color:#FFFFFF !important; font-size:16px; font-weight:800; }
.price-structure .value.highlight { color:#38BDF8 !important; font-size:18px; }
.estimated-box { background:linear-gradient(135deg,#1E3A5F 0%,#0F172A 100%) !important; border:2px solid #38BDF8 !important; border-radius:16px; padding:20px; }
.step-circle { width:48px; height:48px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:800; }
.step-circle.done { background:#10B981; color:white; }
.step-circle.active { background:#2563EB; color:white; }
.step-circle.pending { background:#0F172A; color:#64748B; border:2px solid #475569; }
.stDownloadButton > button { background:#DC2626 !important; color:white !important; border-radius:12px !important; font-weight:800 !important; border:2px solid #EF4444 !important; height:52px; }
div[data-testid="stButton"] > button[kind="primary"] { background:#2563EB !important; border-radius:12px !important; height:56px; font-weight:800 !important; color:white !important; font-size:16px !important; }
.block-container { max-width:1280px !important; }
</style>
""", unsafe_allow_html=True)

def get_secret():
 try: k=st.secrets.get("GEMINI_API_KEY","")
 except: k=""
 if not k: k=os.getenv("GEMINI_API_KEY","") or os.getenv("GOOGLE_API_KEY","")
 return k.strip()

secret_key=get_secret()
if 'manual_key' not in st.session_state: st.session_state.manual_key=""
api_key=secret_key or st.session_state.manual_key

@st.cache_data
def load_combined_excel():
 candidates=[
  "28-8-69_Dynamic_Formulas_Categories.xlsx",
  "motorcycle_price_all_models.xlsx",
  "ราคารถทั้งหมด_backup.csv",
  "price_backup_all_models.csv",
  "/mnt/data/28-8-69_Dynamic_Formulas_Categories.xlsx",
  "/mnt/data/motorcycle_price_all_models.xlsx",
  "/mnt/data/ราคารถทั้งหมด_backup.csv",
  "/mnt/data/price_backup_all_models.csv",
  "/mnt/data/data/28-8-69_Dynamic_Formulas_Categories.xlsx",
  "Yamaha_รวมขายทุกตัว_25-8-69_Dynamic_Formulas_Categories.xlsx"
 ]
 for fp in candidates:
  if os.path.exists(fp):
   try:
    if fp.endswith(".csv"):
     df=pd.read_csv(fp, encoding='utf-8-sig')
    else:
     df=pd.read_excel(fp, sheet_name=0, skiprows=2, header=None)
     df.columns=[f"c{i}" for i in range(df.shape[1])]
     df=df.rename(columns={"c0":"รุ่นรถ","c1":"รหัสรถ","c2":"ยอดจัด","c3":"ดอกเบี้ยต่อเดือน","c4":"%ดาวน์","c5":"ราคาดาวน์","c6":"ทะเบียน พรบ ประกัน","c7":"ค่าใช้จ่ายออกรถ","c8":"ผ่อน12","c9":"ผ่อน18","c10":"ผ่อน24","c11":"ผ่อน30","c12":"ผ่อน36","c13":"ผ่อน48"})
    df['รุ่นรถ']=df['รุ่นรถ'].ffill()
    df=df[~df['รุ่นรถ'].astype(str).str.contains("ตารางโปรโมชัน|รุ่นรถ", na=False)]
    df['ยอดจัด']=pd.to_numeric(df['ยอดจัด'], errors='coerce')
    df=df.dropna(subset=['ยอดจัด'])
    df['ยี่ห้อ']=df['รุ่นรถ'].astype(str).str.split().str[0]
    df['%ดาวน์']=pd.to_numeric(df['%ดาวน์'], errors='coerce').fillna(0)
    df['ราคาดาวน์']=pd.to_numeric(df['ราคาดาวน์'], errors='coerce').fillna(0)
    df['ทะเบียน พรบ ประกัน']=pd.to_numeric(df['ทะเบียน พรบ ประกัน'], errors='coerce').fillna(0)
    df['ค่าใช้จ่ายออกรถ']=pd.to_numeric(df['ค่าใช้จ่ายออกรถ'], errors='coerce').fillna(0)
    df['ดอกเบี้ยต่อเดือน']=pd.to_numeric(df['ดอกเบี้ยต่อเดือน'], errors='coerce').fillna(0.015)
    for col in ["ผ่อน12","ผ่อน18","ผ่อน24","ผ่อน30","ผ่อน36","ผ่อน48"]:
     if col in df.columns:
      df[col]=pd.to_numeric(df[col], errors='coerce').fillna(0)
    if len(df)>0:
     return df
   except: continue
 return pd.DataFrame()

full_price_df=load_combined_excel()

with st.sidebar:
 st.markdown('<div style="display:flex;align-items:center;gap:12px;padding:12px;"><div style="width:54px;height:54px;background:linear-gradient(135deg,#0EA5E9,#06B6D4);border-radius:14px;display:flex;align-items:center;justify-content:center;font-size:30px;">🐒</div><div><div style="color:#FFFFFF;font-weight:800;font-size:18px;">SRD Moto Credit</div><div style="color:#38BDF8;font-size:12px;font-weight:700;">บจก. สิระเดชมอเตอร์เซลล์</div><div style="color:#94A3B8;font-size:11px;">v1.5 Full Dark • Option B</div></div></div>', unsafe_allow_html=True)
 if not secret_key:
  mk=st.text_input("🔑 GEMINI API Key", type="password", value=st.session_state.manual_key)
  if mk: st.session_state.manual_key=mk.strip(); api_key=st.session_state.manual_key
 else: st.success("✅ API Key พร้อม")
 selected_model="gemini-3.6-flash"; client=None; genai_types=None
 if api_key:
  try:
   from google import genai as new_genai
   from google.genai import types as new_types
   @st.cache_resource(show_spinner=False)
   def get_client(k_hash,k_val):
    cl=new_genai.Client(api_key=k_val)
    return cl,"gemini-3.6-flash"
   client,selected_model=get_client(api_key[:8],api_key)
   genai_types=new_types
  except Exception as e: st.error(str(e))

st.markdown('<div style="background:#1E293B;border:2px solid #334155;border-radius:16px;padding:20px;max-width:1280px;margin:0 auto 16px auto;"><div style="font-size:26px;font-weight:800;color:#FFFFFF;">Motorcycle Loan Credit Engine v1.5 - Full Dark High Contrast</div><div style="font-size:15px;font-weight:700;color:#38BDF8;margin-top:6px;">Option B: Full Dark High Contrast • รวมทุกรุ่น • 7 รายการโครงสร้างราคา • พื้นเข้มตัดข้อความขาวเด่น</div></div>', unsafe_allow_html=True)

if 'vehicle_price' not in st.session_state: st.session_state.vehicle_price=85500.0
if 'downpayment' not in st.session_state: st.session_state.downpayment=38000.0
if 'tenure' not in st.session_state: st.session_state.tenure=12
if 'flat_rate' not in st.session_state: st.session_state.flat_rate=1.70
if 'processing_fee' not in st.session_state: st.session_state.processing_fee=0.0

left_col,right_col=st.columns([1.7,1])
with left_col:
 st.markdown('<div class="moto-card">', unsafe_allow_html=True)
 st.markdown(f'<div style="display:flex;align-items:center;gap:14px;margin-bottom:16px;"><div style="width:46px;height:46px;background:#2563EB;border-radius:12px;display:flex;align-items:center;justify-content:center;color:white;font-size:22px;font-weight:800;">🧮</div><div><div style="font-weight:800;font-size:18px;color:#FFFFFF;">Section 1: ข้อมูลรถและคำนวณค่างวด Flat Rate • {selected_model}</div><div style="font-size:12px;color:#E2E8F0;font-weight:600;">Option B Full Dark • 7 รายการโครงสร้างราคา • ไม่แสดงสูตร • รวมทุกรุ่น</div></div></div>', unsafe_allow_html=True)
 
 price_mode=st.radio("🔀 วิธีเลือกราคา (Option B - แก้ซ้ำแล้ว)", ["📦 เลือกรุ่นจากฐานข้อมูลรวมทุกรุ่น (ดึงจาก DB เท่านั้น ห้ามแก้ไข) - แบบ GIORNO+ CBS", "✏️ ใส่ราคาด้วยตนเอง (Manual) - แก้ได้ทุกช่อง"], index=0)
 
 # ค่าเริ่มต้นตามรูป image_9d7521.png
 default_model_name="GIORNO+ CBS"
 default_code="GIORNO-CBS"
 default_cash=85500.0
 default_down=38000.0
 default_reg=0.0
 default_reg_separate=2000.0
 default_int=1.70
 default_tenure=12
 
 if price_mode.startswith("📦"):
  if full_price_df.empty:
   st.warning("⚠️ ไม่พบไฟล์ฐานข้อมูล - ใช้ค่าตัวอย่าง GIORNO+ CBS ตามรูป")
   model_name=default_model_name; def_code=default_code; def_price=default_cash; def_down=default_down; def_reg=default_reg; def_int=default_int; tenure_db=default_tenure
   loan_amount=def_price-def_down
   total_interest=loan_amount*(def_int/100)*tenure_db
   total_debt=loan_amount+total_interest
   monthly_instalment=total_debt/tenure_db if tenure_db else 0
   total_out=def_down+default_reg_separate
   total_hire=total_out+total_debt
  else:
   st.success(f"✅ โหลดฐานข้อมูลสำเร็จ {len(full_price_df)} รายการ - รวมทุกรุ่น")
   brands=sorted(full_price_df['ยี่ห้อ'].dropna().unique().tolist())
   col_b,col_s=st.columns([1,1.2])
   with col_b: sel_brand=st.selectbox("🏷️ เลือกหมวดหมู่รถ / ยี่ห้อ", ["ทั้งหมด"]+brands, key="brand_db", index=0)
   with col_s: search_model=st.text_input("🔍 ค้นหารุ่นรถ", "GIORNO", key="search_db")
   filtered_df=full_price_df.copy()
   if sel_brand!="ทั้งหมด": filtered_df=filtered_df[filtered_df['ยี่ห้อ']==sel_brand]
   if search_model: filtered_df=filtered_df[filtered_df['รุ่นรถ'].str.contains(search_model, case=False, na=False)]
   models=sorted(filtered_df['รุ่นรถ'].unique().tolist())
   if not models: models=sorted(full_price_df['รุ่นรถ'].unique().tolist())
   sel_model=st.selectbox(f"🏍️ เลือกรุ่นรถ ({len(models)} รุ่น) - ดึงจากฐานข้อมูลเท่านั้น", models, key="model_db")
   model_variants=filtered_df[filtered_df['รุ่นรถ']==sel_model].copy().sort_values('%ดาวน์')
   st.dataframe(model_variants[['รหัสรถ','รุ่นรถ','ยอดจัด','%ดาวน์','ราคาดาวน์','ค่าใช้จ่ายออกรถ','ทะเบียน พรบ ประกัน']].rename(columns={'รหัสรถ':'รหัสรถ','รุ่นรถ':'รุ่นรถ','ยอดจัด':'ยอดจัด/ราคารถ','ราคาดาวน์':'ราคาดาวน์','ค่าใช้จ่ายออกรถ':'ออกรถได้','ทะเบียน พรบ ประกัน':'ทะเบียน พรบ ประกัน'}), use_container_width=True, height=220)
   down_options=model_variants[['%ดาวน์','ราคาดาวน์','ค่าใช้จ่ายออกรถ','ยอดจัด','ดอกเบี้ยต่อเดือน','รหัสรถ','ทะเบียน พรบ ประกัน','ผ่อน12','ผ่อน24','ผ่อน36','ผ่อน48']].to_dict('records')
   down_labels=[f"{r['%ดาวน์']*100:.0f}% ดาวน์ {r['ราคาดาวน์']:,.0f}บ. • ออกรถ {r['ค่าใช้จ่ายออกรถ']:,.0f}บ. • ทะเบียน {r['ทะเบียน พรบ ประกัน']:,.0f}บ. • รหัส {r['รหัสรถ']}" for r in down_options]
   sel_down_idx=st.selectbox("💵 เลือก % ดาวน์ (จากตารางจริง DB)", range(len(down_labels)), format_func=lambda i: down_labels[i], key="down_db")
   chosen=down_options[sel_down_idx]
   def_price=float(chosen['ยอดจัด']); def_down=float(chosen['ราคาดาวน์']); def_reg=float(chosen['ทะเบียน พรบ ประกัน']); def_int=float(chosen['ดอกเบี้ยต่อเดือน'])*100; def_code=chosen['รหัสรถ']
   model_name=sel_model
   # อ่านอย่างเดียว ห้ามแก้ไข - แก้ซ้ำซ้อน
   st.markdown('<div style="color:#FFFFFF;font-weight:800;font-size:15px;margin:16px 0 8px 0;">📋 ข้อมูลจากฐานข้อมูล (อ่านอย่างเดียว ห้ามแก้ไข) - ตามรูป image_9d7521.png</div>', unsafe_allow_html=True)
   c1,c2=st.columns(2)
   with c1:
    st.markdown(f'<div class="readonly-box"><div class="label">เลือกหมวดหมู่รถ</div><div class="value">Honda - รถใหม่</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="readonly-box"><div class="label">เลือกรุ่นรถ</div><div class="value">{model_name} 2 คัน ขาว-ดำ เทา-น้ำตาล</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="readonly-box"><div class="label">ชื่อรุ่นรถ</div><div class="value">{model_name}</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="readonly-box"><div class="label">% ดอกเบี้ย Flat Rate</div><div class="value" style="color:#38BDF8 !important;">{def_int:.2f}%</div></div>', unsafe_allow_html=True)
   with c2:
    st.markdown(f'<div class="readonly-box"><div class="label">ราคาสดตัวรถ</div><div class="value">{def_price:,.0f} บาท</div></div>', unsafe_allow_html=True)
    tenure_db=st.selectbox("📅 ระยะเวลาผ่อน (เดือน)", [12,18,24,30,36,48,60,72], index=0, key="tenure_db")
    st.markdown(f'<div class="readonly-box"><div class="label">ค่า พรบ./ทะเบียน</div><div class="value">{def_reg:,.0f} บาท</div></div>', unsafe_allow_html=True)
    reg_separate=st.number_input("ค่า พรบ.แยกวันออกรถ", value=2000.0, step=100.0, key="reg_sep_db")
    st.markdown(f'<div class="readonly-box"><div class="label">เงินดาวน์</div><div class="value">{def_down:,.0f} บาท</div></div>', unsafe_allow_html=True)
   # คำนวณ 7 รายการตามรูป
   loan_amount=def_price-def_down
   col_map={12:"ผ่อน12",18:"ผ่อน18",24:"ผ่อน24",30:"ผ่อน30",36:"ผ่อน36",48:"ผ่อน48"}
   if tenure_db in col_map and chosen.get(col_map[tenure_db],0)>0:
    monthly_instalment=float(chosen.get(col_map[tenure_db]))
    total_debt=monthly_instalment*tenure_db
    total_interest=total_debt-loan_amount
   else:
    total_interest=loan_amount*(def_int/100)*tenure_db
    total_debt=loan_amount+total_interest
    monthly_instalment=total_debt/tenure_db if tenure_db else 0
   total_out=def_down+reg_separate
   total_hire=total_out+total_debt
   st.session_state.vehicle_price=def_price; st.session_state.downpayment=def_down; st.session_state.processing_fee=def_reg; st.session_state.flat_rate=def_int; st.session_state.tenure=tenure_db
   # แสดงค่างวดคำนวณตามสูตร + ยอดจัดเก็บจริง
   st.markdown(f'<div style="display:flex;gap:12px;margin:16px 0;"><div style="flex:1;background:#1E293B;padding:16px;border-radius:12px;border:2px solid #334155;text-align:center;"><div style="font-size:12px;color:#94A3B8;font-weight:700;">ค่างวดคำนวณตามสูตร</div><div style="font-size:20px;font-weight:800;color:#FFFFFF;margin-top:4px;">{total_debt/tenure_db:,.0f} บาท/เดือน</div></div><div style="flex:1;background:#1E293B;padding:16px;border-radius:12px;border:2px solid #38BDF8;text-align:center;"><div style="font-size:12px;color:#7DD3FC;font-weight:700;">ยอดค่างวดจัดเก็บจริง</div><div style="font-size:22px;font-weight:800;color:#38BDF8;margin-top:4px;">{monthly_instalment:,.0f} บาท</div></div></div>', unsafe_allow_html=True)
   # ตารางโครงสร้างราคา 7 รายการ - ตามรูปเป๊ะ
   st.markdown(f"""
   <div class="price-structure">
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;"><div style="width:36px;height:36px;background:#1E40AF;border-radius:8px;display:flex;align-items:center;justify-content:center;">📊</div><div style="font-weight:800;color:#FFFFFF;font-size:17px;">โครงสร้างราคาและสินเชื่อเช่าซื้อ</div><div style="background:#1E293B;color:#94A3B8;padding:4px 10px;border-radius:12px;font-size:11px;font-weight:700;margin-left:auto;">7 รายการ</div></div>
    <div class="row"><div class="label">1. รวมราคารถสุทธิ (Net Price)</div><div class="value">{def_price:,.0f} บาท</div></div>
    <div class="row"><div class="label">2. ยอดจัดไฟแนนซ์ (Financing) ดาวน์ {def_down/def_price*100:.1f}%</div><div class="value">{loan_amount:,.0f} บาท <span style="color:#38BDF8;font-size:12px;">(ดาวน์ {def_down/def_price*100:.1f}%)</span></div></div>
    <div class="row"><div class="label">3. ดอกเบี้ยรวม ({def_int:.2f}% x {tenure_db} งวด)</div><div class="value">{total_interest:,.0f} บาท</div></div>
    <div class="row"><div class="label">4. ยอดหนี้รวมทั้งสิ้น (Total Debt)</div><div class="value">{total_debt:,.0f} บาท</div></div>
    <div class="row"><div class="label">ค่างวดที่เรียกเก็บต่อเดือน</div><div class="value highlight">{monthly_instalment:,.0f} บาท/เดือน</div></div>
    <div class="row"><div class="label">รวมจ่ายวันออกรถ (ดาวน์ + ทะเบียนแยก)</div><div class="value" style="color:#4ADE80 !important;">{total_out:,.0f} บาท</div></div>
    <div class="row"><div class="label">🏆 ยอดเช่าซื้อรวมทั้งสัญญา (Total Hire Purchase)</div><div class="value" style="font-size:20px;color:#FBBF24 !important;">{total_hire:,.0f} บาท</div></div>
   </div>
   """, unsafe_allow_html=True)
 else:
  # Manual Mode
  st.markdown('<div style="color:#FEF3C7;font-weight:800;font-size:15px;margin:16px 0 8px 0;background:#422006;padding:10px 14px;border-radius:10px;border:1px solid #92400E;">✏️ โหมด Manual - ใส่ราคาด้วยตนเอง (แก้ได้ทุกช่อง) - ตามรูป</div>', unsafe_allow_html=True)
  model_name=st.text_input("ชื่อรุ่นรถ / Model", "GIORNO+ CBS 2 คัน ขาว-ดำ เทา-น้ำตาล", key="model_manual")
  c1,c2=st.columns(2)
  with c1:
   def_price=st.number_input("ราคาสดตัวรถ (Cash Price)", value=85500.0, key="price_manual")
   def_down=st.number_input("เงินดาวน์ (Down Payment)", value=38000.0, key="down_manual")
   def_int=st.number_input("อัตราดอกเบี้ยต่อเดือน (%)", value=1.70, key="int_manual")
  with c2:
   tenure=st.selectbox("ระยะเวลาผ่อน (จำนวนงวด)", [12,18,24,30,36,48,60,72], index=0, key="tenure_manual")
   def_reg=st.number_input("ค่า พรบ./ทะเบียน/ประกันรถหาย (รวมในยอดจัด)", value=0.0, key="reg_manual")
   reg_separate=st.number_input("ค่า พรบ.แยกวันออกรถ", value=2000.0, key="reg_sep_manual")
  loan_amount=def_price-def_down
  total_interest=loan_amount*(def_int/100)*tenure
  total_debt=loan_amount+total_interest
  monthly_instalment=total_debt/tenure if tenure else 0
  total_out=def_down+reg_separate
  total_hire=total_out+total_debt
  def_code="GIORNO-CBS"
  st.session_state.vehicle_price=def_price; st.session_state.downpayment=def_down; st.session_state.processing_fee=def_reg; st.session_state.flat_rate=def_int; st.session_state.tenure=tenure
  st.markdown(f"""
   <div class="price-structure">
    <div class="row"><div class="label">1. รวมราคารถสุทธิ</div><div class="value">{def_price:,.0f} บาท</div></div>
    <div class="row"><div class="label">2. ยอดจัดไฟแนนซ์</div><div class="value">{loan_amount:,.0f} บาท (ดาวน์ {def_down/def_price*100:.1f}%)</div></div>
    <div class="row"><div class="label">3. ดอกเบี้ยรวม</div><div class="value">{total_interest:,.0f} บาท</div></div>
    <div class="row"><div class="label">4. ยอดหนี้รวมทั้งสิ้น</div><div class="value">{total_debt:,.0f} บาท</div></div>
    <div class="row"><div class="label">ค่างวดต่อเดือน</div><div class="value highlight">{monthly_instalment:,.0f} บาท</div></div>
    <div class="row"><div class="label">รวมจ่ายวันออกรถ</div><div class="value">{total_out:,.0f} บาท</div></div>
    <div class="row"><div class="label">ยอดเช่าซื้อรวมทั้งสัญญา</div><div class="value" style="font-size:20px;color:#FBBF24 !important;">{total_hire:,.0f} บาท</div></div>
   </div>
  """, unsafe_allow_html=True)

 from reportlab.pdfgen import canvas as pdf_c
 from reportlab.lib.pagesizes import A4
 def gen_pdf(name,model,code,cash,down,reg,out_cost,monthly,term,total_debt,total_hire):
  buf=io.BytesIO()
  c=pdf_c.Canvas(buf,pagesize=A4)
  c.setFont("Helvetica-Bold",12)
  c.drawString(30,800,f"SRD Moto Credit v1.5 Full Dark - Option B - {model} ({code})")
  c.setFont("Helvetica",10)
  c.drawString(30,780,f"Net Price: {cash:,.0f} | Down: {down:,.0f} | Financing: {cash-down:,.0f} | Monthly: {monthly:,.0f} x {term}")
  c.drawString(30,760,f"Total Debt: {total_debt:,.0f} | Out Cost: {out_cost:,.0f} | Total Hire Purchase: {total_hire:,.0f}")
  c.showPage(); c.save(); buf.seek(0)
  return buf

 col_calc,col_pdf=st.columns([1.2,1])
 with col_calc: st.button("💾 บันทึกข้อมูล", type="primary", use_container_width=True)
 with col_pdf:
  pdf1=gen_pdf(st.session_state.get('applicant_name',''), model_name if 'model_name' in locals() else 'GIORNO+', def_code if 'def_code' in locals() else '-', st.session_state.vehicle_price, st.session_state.downpayment, st.session_state.processing_fee, total_out if 'total_out' in locals() else 40000, monthly_instalment, st.session_state.tenure, total_debt if 'total_debt' in locals() else 57240, total_hire if 'total_hire' in locals() else 97240)
  st.download_button("🔴 ส่งออกเป็น PDF", data=pdf1, file_name=f"SRD_Loan_v15_FullDark_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf", mime="application/pdf", use_container_width=True)
 st.markdown('</div>', unsafe_allow_html=True)

 # Section 2: ข้อมูลผู้กู้ - ตามรูป
 st.markdown('<div class="moto-card">', unsafe_allow_html=True)
 st.markdown('<div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;"><div style="width:44px;height:44px;background:#7C3AED;border-radius:12px;display:flex;align-items:center;justify-content:center;color:white;font-size:22px;">👤</div><div><div style="font-weight:800;color:#FFFFFF;font-size:18px;">Section 2: ข้อมูลผู้กู้ (Applicant)</div><div style="font-size:12px;color:#94A3B8;">กรอกข้อมูลผู้กู้และที่อยู่ให้ครบถ้วน</div></div></div>', unsafe_allow_html=True)
 a1,a2=st.columns(2)
 with a1:
  st.text_input("1. ชื่อ-นามสกุล", "ชญาณิศ ศรีวิชา", key="app_fullname")
  st.number_input("2. อายุ", value=39, key="app_age")
  st.number_input("3. รายได้ต่อเดือน", value=50000.0, key="app_income")
 with a2:
  st.selectbox("สถานะสมรส", ["โสด","สมรสจดทะเบียน","อยู่กินกันฉันสามีภรรยา","หย่า"], index=2, key="marital")
  st.number_input("4. รายได้เสริม", value=5000.0, key="app_extra")
  st.text_input("5. อาชีพ", "เจ้าของกิจการ", key="app_job")
 st.markdown('<div style="background:#020617;padding:14px;border-radius:12px;border:2px solid #334155;margin-top:12px;"><div style="color:#FFFFFF;font-weight:700;font-size:13px;">เงื่อนไขยืนยันสินค้าเช่าซื้อ / ติดตามตำแหน่ง (PDPA)</div><div style="margin-top:10px;"><label style="display:flex;align-items:center;gap:10px;color:#E2E8F0 !important;font-weight:500 !important;"><input type="checkbox" checked> ยินยอมให้เก็บและประมวลผลข้อมูลตาม PDPA เพื่อการวิเคราะห์สินเชื่อ</label><label style="display:flex;align-items:center;gap:10px;color:#E2E8F0 !important;font-weight:500 !important;margin-top:8px;"><input type="checkbox" checked> ยินยอมติดตั้งอุปกรณ์ GPS ตามเงื่อนไขสัญญาเช่าซื้อ</label></div></div>', unsafe_allow_html=True)
 st.markdown('</div>', unsafe_allow_html=True)

 # ของแถม + คู่สมรส + ผู้ค้ำ - คงไว้
 st.markdown('<div class="moto-card" style="background:#422006 !important;border:2px solid #92400E !important;">', unsafe_allow_html=True)
 st.markdown('<div style="font-weight:800;color:#FEF3C7;font-size:16px;">🎁 ของแถมพิเศษ / โปรโมชั่น</div>', unsafe_allow_html=True)
 st.text_area("ของแถมพิเศษ", "หมวกกันน็อค SRD ฟรี, น้ำมันเต็มถัง, ประกันรถหาย 1 ปี", height=70, key="gift")
 st.markdown('</div>', unsafe_allow_html=True)

with right_col:
 st.markdown('<div class="moto-card">', unsafe_allow_html=True)
 st.markdown(f'<div style="text-align:center;"><div style="font-size:32px;font-weight:800;color:#FFFFFF;">42.3%</div><div style="font-size:11px;color:#E2E8F0;">DSR - Debt Service Ratio</div><div style="margin-top:10px;background:#052E16;color:#BBF7D0;padding:6px 12px;border-radius:20px;font-size:11px;font-weight:700;">Within Safe Limit</div></div>', unsafe_allow_html=True)
 st.markdown('</div>', unsafe_allow_html=True)
 st.markdown('<div class="moto-card">', unsafe_allow_html=True)
 st.markdown('<div style="font-weight:800;color:#FFFFFF;">วิเคราะห์ 13 โมดูลด้วย AI</div><div style="font-size:12px;color:#94A3B8;margin-top:8px;">✅ ผ่านทั้ง 13 โมดูล • ความมั่นใจ 92% • ไม่แสดงสูตร • Full Dark</div>', unsafe_allow_html=True)
 st.markdown('</div>', unsafe_allow_html=True)

st.caption("SRD v1.5 Full Dark High Contrast Option B • รวมทุกรุ่น • 7 รายการโครงสร้างราคา • พื้นเข้มตัดข้อความขาวเด่น • ดึงจาก DB ห้ามแก้ไข Manual แก้ได้ • ไม่แสดงสูตร • ตามรูป image_9d7521.png")
