
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

st.set_page_config(page_title="SRD Moto Credit v1.4 Fix - รวมทุกรุ่น", layout="wide", page_icon="🐒")

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
.estimated-box { background:linear-gradient(135deg,#1E3A5F 0%,#0F172A 100%) !important; border:2px solid #38BDF8 !important; border-radius:16px; padding:20px; }
.step-circle { width:48px; height:48px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:800; }
.step-circle.done { background:#10B981; color:white; }
.step-circle.active { background:#2563EB; color:white; }
.step-circle.pending { background:#0F172A; color:#64748B; border:2px solid #475569; }
.stDownloadButton > button { background:#DC2626 !important; color:white !important; border-radius:12px !important; font-weight:800 !important; border:2px solid #EF4444 !important; height:52px; }
div[data-testid="stButton"] > button[kind="primary"] { background:#2563EB !important; border-radius:12px !important; height:54px; font-weight:800 !important; color:white !important; }
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
  "ราคารถทั้งหมด_backup.csv",
  "/mnt/data/28-8-69_Dynamic_Formulas_Categories.xlsx",
  "/mnt/data/ราคารถทั้งหมด_backup.csv",
  "/mnt/data/data/28-8-69_Dynamic_Formulas_Categories.xlsx",
  "Yamaha_รวมขายทุกตัว_25-8-69_Dynamic_Formulas_Categories.xlsx",
  "/mnt/data/Yamaha_รวมขายทุกตัว_25-8-69_Dynamic_Formulas_Categories.xlsx"
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
    # normalize
    for col in ["ผ่อน12","ผ่อน18","ผ่อน24","ผ่อน30","ผ่อน36","ผ่อน48"]:
     if col in df.columns:
      df[col]=pd.to_numeric(df[col], errors='coerce').fillna(0)
    if len(df)>0:
     return df
   except Exception as e:
    continue
 return pd.DataFrame()

full_price_df=load_combined_excel()

with st.sidebar:
 st.markdown('<div style="display:flex;align-items:center;gap:12px;padding:12px;"><div style="width:54px;height:54px;background:linear-gradient(135deg,#0EA5E9,#06B6D4);border-radius:14px;display:flex;align-items:center;justify-content:center;font-size:30px;">🐒</div><div><div style="color:#FFFFFF;font-weight:800;font-size:18px;">SRD Moto Credit</div><div style="color:#38BDF8;font-size:12px;font-weight:700;">บจก. สิระเดชมอเตอร์เซลล์</div><div style="color:#94A3B8;font-size:11px;">v1.4 Fix • รวมทุกรุ่น</div></div></div>', unsafe_allow_html=True)
 for icon,label,active in [("🏠","แดชบอร์ด",False),("💳","เครื่องคำนวณสินเชื่อ",True),("📄","ใบสมัคร",False),("👥","ลูกค้า",False),("📁","เอกสาร",False),("📊","วิเคราะห์ข้อมูล",False),("🛡️","ความเสี่ยงและนโยบาย",False)]:
  if active: st.markdown(f'<div style="background:#1E3A5F;border:2px solid #38BDF8;border-radius:12px;padding:14px 16px;margin:6px 0;color:#FFFFFF;border-left:5px solid #38BDF8;display:flex;gap:12px;font-weight:800;"><span>{icon}</span> {label}</div>', unsafe_allow_html=True)
  else: st.markdown(f'<div style="padding:14px 16px;margin:6px 0;opacity:0.8;display:flex;gap:12px;color:#F1F5F9;font-weight:600;"><span>{icon}</span> {label}</div>', unsafe_allow_html=True)
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

st.markdown('<div style="background:#1E293B;border:2px solid #334155;border-radius:16px;padding:20px;max-width:1280px;margin:0 auto 16px auto;"><div style="font-size:26px;font-weight:800;color:#FFFFFF;">Motorcycle Loan Credit Engine</div><div style="font-size:15px;font-weight:700;color:#38BDF8;margin-top:6px;">ระบบตรวจสอบสินเชื่อมอเตอร์ไซค์ • รวมทุกรุ่น • พื้นเข้มตัดข้อความชัด • ไม่มีซ้ำ</div></div>', unsafe_allow_html=True)

if 'vehicle_price' not in st.session_state: st.session_state.vehicle_price=54600.0
if 'downpayment' not in st.session_state: st.session_state.downpayment=0.0
if 'tenure' not in st.session_state: st.session_state.tenure=36
if 'flat_rate' not in st.session_state: st.session_state.flat_rate=1.5
if 'processing_fee' not in st.session_state: st.session_state.processing_fee=1000.0

left_col,right_col=st.columns([1.7,1])
with left_col:
 st.markdown('<div class="moto-card">', unsafe_allow_html=True)
 st.markdown(f'<div style="display:flex;align-items:center;gap:14px;margin-bottom:16px;"><div style="width:46px;height:46px;background:#2563EB;border-radius:12px;display:flex;align-items:center;justify-content:center;color:white;font-size:22px;font-weight:800;">🧮</div><div><div style="font-weight:800;font-size:18px;color:#FFFFFF;">เครื่องคำนวณ Flat Rate • {selected_model}</div><div style="font-size:12px;color:#E2E8F0;font-weight:600;">แก้ไข: DB ห้ามแก้ไข ดึงจาก DB เท่านั้น • Manual แก้ได้</div></div></div>', unsafe_allow_html=True)
 
 price_mode=st.radio("🔀 วิธีเลือกราคา (แก้ซ้ำซ้อนแล้ว)", ["📦 เลือกรุ่นจากฐานข้อมูลรวมทุกรุ่น (ดึงจาก DB เท่านั้น ห้ามแก้ไข)", "✏️ ใส่ราคาด้วยตนเอง (Manual) - แก้ได้ทุกช่อง"], index=0)
 
 if price_mode.startswith("📦"):
  if full_price_df.empty:
   st.error("⚠️ ไม่พบไฟล์ฐานข้อมูลในระบบ")
   st.info("บนเครื่องนี้มีไฟล์แล้ว แต่บน Streamlit Cloud ต้องอัปโหลดไฟล์ Excel และ CSV backup ไปที่ GitHub Repo เดียวกับ app.py ด้วย")
   st.markdown("**ไฟล์ที่ต้องอัปโหลดไป GitHub:** `28-8-69_Dynamic_Formulas_Categories.xlsx` และ `ราคารถทั้งหมด_backup.csv`")
   # fallback demo data so UI still works
   model_name="ฟาซซิโอ้ SMK"; def_code="BKF700"; def_price=54600.0; def_down=0.0; def_reg=1000.0; def_int=1.5; def_total_out=1000.0; monthly_instalment=2336.0; loan_amount=54600.0; tenure_db=36
  else:
   st.success(f"✅ โหลดฐานข้อมูลสำเร็จ {len(full_price_df)} รายการ จากไฟล์รวมทุกรุ่น")
   brands=sorted(full_price_df['ยี่ห้อ'].dropna().unique().tolist())
   col_b,col_s=st.columns([1,1.2])
   with col_b: sel_brand=st.selectbox("🏷️ ยี่ห้อ", ["ทั้งหมด"]+brands, key="brand_db")
   with col_s: search_model=st.text_input("🔍 ค้นหารุ่น", "", placeholder="เช่น ฟาซซิโอ้ แกรนด์", key="search_db")
   filtered_df=full_price_df.copy()
   if sel_brand!="ทั้งหมด": filtered_df=filtered_df[filtered_df['ยี่ห้อ']==sel_brand]
   if search_model: filtered_df=filtered_df[filtered_df['รุ่นรถ'].str.contains(search_model, case=False, na=False)]
   models=sorted(filtered_df['รุ่นรถ'].unique().tolist())
   sel_model=st.selectbox(f"🏍️ รุ่นรถ ({len(models)} รุ่น) - ดึงจากฐานข้อมูลเท่านั้น", models, key="model_db")
   model_variants=filtered_df[filtered_df['รุ่นรถ']==sel_model].copy().sort_values('%ดาวน์')
   st.dataframe(model_variants[['รหัสรถ','รุ่นรถ','ยอดจัด','%ดาวน์','ราคาดาวน์','ค่าใช้จ่ายออกรถ','ทะเบียน พรบ ประกัน']], use_container_width=True, height=260)
   down_options=model_variants[['%ดาวน์','ราคาดาวน์','ค่าใช้จ่ายออกรถ','ยอดจัด','ดอกเบี้ยต่อเดือน','รหัสรถ','ทะเบียน พรบ ประกัน','ผ่อน12','ผ่อน24','ผ่อน36','ผ่อน48']].to_dict('records')
   down_labels=[f"{r['%ดาวน์']*100:.0f}% ดาวน์ {r['ราคาดาวน์']:,.0f}บ. • ออกรถ {r['ค่าใช้จ่ายออกรถ']:,.0f}บ. • ทะเบียน {r['ทะเบียน พรบ ประกัน']:,.0f}บ. • รหัส {r['รหัสรถ']}" for r in down_options]
   sel_down_idx=st.selectbox("💵 เลือก % ดาวน์ (จากตารางจริง DB)", range(len(down_labels)), format_func=lambda i: down_labels[i], key="down_db")
   chosen=down_options[sel_down_idx]
   def_price=float(chosen['ยอดจัด']); def_down=float(chosen['ราคาดาวน์']); def_total_out=float(chosen['ค่าใช้จ่ายออกรถ']); def_reg=float(chosen['ทะเบียน พรบ ประกัน']); def_int=float(chosen['ดอกเบี้ยต่อเดือน'])*100; def_code=chosen['รหัสรถ']
   monthly_from_table=float(chosen.get('ผ่อน36',0) or chosen.get('ผ่อน24',0) or 0)
   model_name=sel_model
   st.markdown('<div style="color:#FFFFFF;font-weight:800;font-size:15px;margin:16px 0 8px 0;">📋 ข้อมูลจากฐานข้อมูล (อ่านอย่างเดียว ห้ามแก้ไข)</div>', unsafe_allow_html=True)
   c1,c2,c3=st.columns(3)
   with c1:
    st.markdown(f'<div class="readonly-box"><div class="label">ชื่อรุ่นรถ</div><div class="value">{model_name}</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="readonly-box"><div class="label">ยอดจัด / ราคารถ</div><div class="value">{def_price:,.0f} บาท</div></div>', unsafe_allow_html=True)
   with c2:
    st.markdown(f'<div class="readonly-box"><div class="label">รหัสรถ</div><div class="value">{def_code}</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="readonly-box"><div class="label">ราคาดาวน์</div><div class="value">{def_down:,.0f} บาท</div></div>', unsafe_allow_html=True)
   with c3:
    st.markdown(f'<div class="readonly-box"><div class="label">ทะเบียน พรบ ประกัน</div><div class="value">{def_reg:,.0f} บาท</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="readonly-box"><div class="label">ออกรถได้</div><div class="value">{def_total_out:,.0f} บาท</div></div>', unsafe_allow_html=True)
   c4,c5=st.columns(2)
   with c4: st.markdown(f'<div class="readonly-box"><div class="label">ดอกเบี้ยต่อเดือน</div><div class="value">{def_int:.2f} %</div></div>', unsafe_allow_html=True)
   with c5:
    tenure_db=st.selectbox("📅 ระยะผ่อน (เดือน)", [12,18,24,30,36,48,60,72], index=4, key="tenure_db")
    col_map={12:"ผ่อน12",18:"ผ่อน18",24:"ผ่อน24",30:"ผ่อน30",36:"ผ่อน36",48:"ผ่อน48"}
    if tenure_db in col_map and col_map[tenure_db] in chosen:
     monthly_instalment=float(chosen.get(col_map[tenure_db], monthly_from_table))
    else:
     monthly_instalment=float(monthly_from_table)
   loan_amount=def_price-def_down
   st.session_state.vehicle_price=def_price; st.session_state.downpayment=def_down; st.session_state.processing_fee=def_reg; st.session_state.flat_rate=def_int; st.session_state.tenure=tenure_db
   st.markdown(f'<div class="estimated-box" style="margin-top:16px;"><div style="font-size:34px;font-weight:800;color:#FFFFFF;">{monthly_instalment:,.0f} บาท / เดือน</div><div style="font-size:13px;color:#E2E8F0;margin-top:6px;">{tenure_db} งวด • รหัส {def_code} • ดึงจาก DB เท่านั้น ไม่แสดงสูตร</div></div>', unsafe_allow_html=True)
 else:
  st.markdown('<div style="color:#FEF3C7;font-weight:800;font-size:15px;margin:16px 0 8px 0;background:#422006;padding:10px 14px;border-radius:10px;border:1px solid #92400E;">✏️ โหมด Manual - ใส่ราคาด้วยตนเอง (แก้ได้ทุกช่อง)</div>', unsafe_allow_html=True)
  model_name=st.text_input("ชื่อรุ่นรถ (Manual)", "ฟาซซิโอ้ SMK", key="model_manual")
  c1,c2,c3=st.columns(3)
  with c1: def_price=st.number_input("ยอดจัด / ราคารถ (บาท)", value=54600.0, key="price_manual")
  with c2: def_down=st.number_input("ราคาดาวน์ (บาท)", value=0.0, key="down_manual")
  with c3: def_reg=st.number_input("ทะเบียน พรบ ประกัน (บาท)", value=1000.0, key="reg_manual")
  c4,c5=st.columns(2)
  with c4: def_code=st.text_input("รหัสรถ", "BKF700", key="code_manual")
  with c5: def_int=st.number_input("ดอกเบี้ยต่อเดือน (%)", value=1.5, key="int_manual")
  def_total_out=def_down+def_reg
  c6,c7=st.columns(2)
  with c6:
   vp=st.number_input("💰 ยอดจัด - แก้ได้", value=float(def_price), step=100.0, key="vp_manual")
   tenure=st.selectbox("📅 ระยะผ่อน", [12,18,24,30,36,48,60,72], index=4, key="tenure_manual")
  with c7:
   dp=st.number_input("💵 ดาวน์ - แก้ได้", value=float(def_down), step=100.0, key="dp_manual")
   fr=st.number_input("📈 ดอกเบี้ย (%) - แก้ได้", value=float(def_int), step=0.01, format="%.3f", key="fr_manual")
  pf=def_reg
  loan_amount=vp-dp
  total_interest=loan_amount*(fr/100)*tenure
  monthly_instalment=(loan_amount+total_interest)/tenure if tenure else 0
  st.session_state.vehicle_price=vp; st.session_state.downpayment=dp; st.session_state.processing_fee=pf; st.session_state.flat_rate=fr; st.session_state.tenure=tenure
  st.markdown(f'<div class="estimated-box"><div style="font-size:28px;font-weight:800;color:#FFFFFF;">{monthly_instalment:,.0f} บาท / เดือน</div></div>', unsafe_allow_html=True)

 from reportlab.pdfgen import canvas as pdf_c
 from reportlab.lib.pagesizes import A4
 def gen_pdf(name,model,code,cash,down,reg,out_cost,monthly,term,dsr,verdict,ai_text,extra,b_behavior,spouse_data,guarantor_data,gift):
  buf=io.BytesIO()
  c=pdf_c.Canvas(buf,pagesize=A4)
  c.setFont("Helvetica-Bold",11)
  c.drawString(30,800,f"SRD v1.4 Fix - {model} ({code})")
  c.setFont("Helvetica",9)
  c.drawString(30,785,f"Applicant: {name} | ยอดจัด: {cash:,.0f} ดาวน์: {down:,.0f} ทะเบียน: {reg:,.0f} ออกรถ: {out_cost:,.0f} ค่างวด: {monthly:,.0f} x {term}")
  y=755
  if ai_text:
   c.setFont("Helvetica",8)
   for line in ai_text.split("\n")[:70]:
    if y<30: c.showPage(); y=800
    c.drawString(30,y,line[:110]); y-=11
  c.showPage(); c.save(); buf.seek(0)
  return buf

 col_calc,col_pdf1=st.columns([1.2,1])
 with col_calc: st.button("⚡ คำนวณสินเชื่อ", type="primary", use_container_width=True)
 with col_pdf1:
  pdf1=gen_pdf(st.session_state.get('applicant_name',''), model_name if 'model_name' in locals() else 'Manual', def_code if 'def_code' in locals() else '-', st.session_state.vehicle_price, st.session_state.downpayment, st.session_state.processing_fee, def_total_out if 'def_total_out' in locals() else st.session_state.processing_fee, monthly_instalment, st.session_state.tenure, st.session_state.get('dsr_value',42.3), st.session_state.get('r_verdict',''), st.session_state.get('ai_text',''), st.session_state.get('extra_details',''), st.session_state.get('behavior_context',''), st.session_state.get('spouse_summary',''), st.session_state.get('guarantor_summary',''), st.session_state.get('gift_data',''))
  st.download_button("🔴 ส่งออกเป็น PDF", data=pdf1, file_name=f"SRD_Loan_v14Fix_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf", mime="application/pdf", use_container_width=True)
 st.markdown('</div>', unsafe_allow_html=True)

 # ส่วนที่เหลือคงไว้เหมือนเดิม
 st.markdown('<div class="moto-card" style="background:#422006 !important;border:2px solid #92400E !important;">', unsafe_allow_html=True)
 st.markdown('<div style="font-weight:800;color:#FEF3C7;font-size:17px;">🎁 ของแถมพิเศษ</div>', unsafe_allow_html=True)
 gift_data=st.text_area("🎁 ของแถมพิเศษ", "เช่น หมวกกันน็อค SRD ฟรี", height=80, key="gift")
 st.session_state.gift_data=gift_data
 st.markdown('</div>', unsafe_allow_html=True)

 st.markdown('<div class="moto-card">', unsafe_allow_html=True)
 st.markdown('<div style="font-weight:800;color:#FFFFFF;font-size:17px;">👤 ผู้สมัครหลัก</div>', unsafe_allow_html=True)
 a1,a2=st.columns(2)
 with a1:
  applicant_name=st.text_input("👤 ชื่อผู้กู้", "สมชาย", key="app_name")
  salary=st.number_input("💼 เงินเดือน", value=15000.0, step=500.0, key="salary")
 with a2:
  phone=st.text_input("📞 เบอร์โทร", "081-xxx-xxxx", key="phone")
  extra_income=st.number_input("💰 รายได้เสริม", value=2000.0, step=500.0, key="extra")
 st.session_state.monthly_income=salary+extra_income
 st.session_state.applicant_name=applicant_name
 st.markdown('</div>', unsafe_allow_html=True)

with right_col:
 st.markdown('<div class="moto-card">', unsafe_allow_html=True)
 st.markdown(f'<div style="text-align:center;"><div style="font-size:32px;font-weight:800;color:#FFFFFF;">{st.session_state.get("dsr_value",42.3):.1f}%</div><div style="font-size:11px;color:#E2E8F0;">DSR</div></div>', unsafe_allow_html=True)
 st.markdown('</div>', unsafe_allow_html=True)

st.caption("SRD v1.4 Fix • รวมทุกรุ่น • แก้ซ้ำซ้อน: DB ห้ามแก้ไข Manual แก้ได้ • พื้นเข้มตัดข้อความขาวเด่น • ไม่แสดงสูตร")
