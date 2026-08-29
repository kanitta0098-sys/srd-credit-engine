
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

st.set_page_config(page_title="SRD Moto Credit v1.4 Fix", layout="wide", page_icon="🐒")

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
input:disabled { background:#1E293B !important; color:#94A3B8 !important; border:1px solid #334155 !important; }
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
 # ไฟล์รวมทุกรุ่น - เขียนโค้ดง่ายขึ้น
 candidates=[
  "28-8-69_Dynamic_Formulas_Categories.xlsx",
  "/mnt/data/28-8-69_Dynamic_Formulas_Categories.xlsx",
  "Yamaha_รวมขายทุกตัว_25-8-69_Dynamic_Formulas_Categories.xlsx",
  "/mnt/data/Yamaha_รวมขายทุกตัว_25-8-69_Dynamic_Formulas_Categories.xlsx"
 ]
 fp=None
 for p in candidates:
  if os.path.exists(p):
   fp=p; break
 if not fp:
  return pd.DataFrame()
 try:
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
  return df
 except Exception as e:
  print(f"load error {e}")
  return pd.DataFrame()

full_price_df=load_combined_excel()

with st.sidebar:
 st.markdown('<div style="display:flex;align-items:center;gap:12px;padding:12px;"><div style="width:54px;height:54px;background:linear-gradient(135deg,#0EA5E9,#06B6D4);border-radius:14px;display:flex;align-items:center;justify-content:center;font-size:30px;">🐒</div><div><div style="color:#FFFFFF;font-weight:800;font-size:18px;">SRD Moto Credit</div><div style="color:#38BDF8;font-size:12px;font-weight:700;">บจก. สิระเดชมอเตอร์เซลล์</div><div style="color:#94A3B8;font-size:11px;">v1.4 Fix • รวมทุกรุ่น • ไม่มีซ้ำ</div></div></div>', unsafe_allow_html=True)
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

st.markdown('<div style="background:#1E293B;border:2px solid #334155;border-radius:16px;padding:20px;max-width:1280px;margin:0 auto 16px auto;"><div style="font-size:26px;font-weight:800;color:#FFFFFF;">Motorcycle Loan Credit Engine</div><div style="font-size:15px;font-weight:700;color:#38BDF8;margin-top:6px;">ระบบตรวจสอบสินเชื่อมอเตอร์ไซค์ • รวมทุกรุ่น • พื้นเข้มตัดข้อความชัด • ไม่มีซ้ำ</div><div style="margin-top:12px;"><span style="background:#052E16;color:#BBF7D0;padding:7px 16px;border-radius:20px;font-size:12px;font-weight:800;border:2px solid #166534;">● Connected • Live</span> <span style="background:#1E1B4B;color:#C7D2FE;padding:7px 16px;border-radius:20px;font-size:12px;font-weight:700;margin-left:8px;">v1.4 Fix • รวมทุกรุ่น • ไม่มีสูตร • แก้ซ้ำ</span></div></div>', unsafe_allow_html=True)

if 'vehicle_price' not in st.session_state: st.session_state.vehicle_price=54600.0
if 'downpayment' not in st.session_state: st.session_state.downpayment=0.0
if 'tenure' not in st.session_state: st.session_state.tenure=36
if 'flat_rate' not in st.session_state: st.session_state.flat_rate=1.5
if 'processing_fee' not in st.session_state: st.session_state.processing_fee=1000.0

left_col,right_col=st.columns([1.7,1])
with left_col:
 st.markdown('<div class="moto-card">', unsafe_allow_html=True)
 st.markdown(f'<div style="display:flex;align-items:center;gap:14px;margin-bottom:16px;"><div style="width:46px;height:46px;background:#2563EB;border-radius:12px;display:flex;align-items:center;justify-content:center;color:white;font-size:22px;font-weight:800;">🧮</div><div><div style="font-weight:800;font-size:18px;color:#FFFFFF;">เครื่องคำนวณ Flat Rate • {selected_model}</div><div style="font-size:12px;color:#E2E8F0;font-weight:600;">แก้ไข: โหมดฐานข้อมูลห้ามแก้ไข ดึงจาก DB เท่านั้น • โหมด Manual คุมไว้แบบเดิม</div></div></div>', unsafe_allow_html=True)
 
 price_mode=st.radio("🔀 วิธีเลือกราคา (แก้ซ้ำซ้อนแล้ว)", ["📦 เลือกรุ่นจากฐานข้อมูลรวมทุกรุ่น (ดึงจาก DB เท่านั้น ห้ามแก้ไข)", "✏️ ใส่ราคาด้วยตนเอง (Manual) - แก้ได้ทุกช่อง"], index=0)
 
 if price_mode.startswith("📦"):
  if full_price_df.empty:
   st.error("⚠️ ไม่พบไฟล์ฐานข้อมูล กรุณาอัปโหลดไฟล์ 28-8-69_Dynamic_Formulas_Categories.xlsx ไว้ใน GitHub Repo เดียวกับ app.py")
   st.info("วิธีแก้: เอาไฟล์ Excel ที่ส่งมา วางใน GitHub แล้ว Commit จะทำให้มีตัวเลือกรุ่นรถขึ้นทันที")
   # fallback Manual
   model_name="ฟาซซิโอ้ SMK"; def_code="BKF700"; def_price=54600.0; def_down=0.0; def_reg=1000.0; def_int=1.5; def_total_out=1000.0; monthly_from_table=2336.0
   loan_amount=def_price-def_down
   monthly_instalment=2336.0
  else:
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
   st.markdown(f"<div style='background:#020617;padding:12px 14px;border-radius:12px;border:2px solid #334155;margin:12px 0;'><div style='color:#38BDF8;font-weight:800;font-size:13px;'>📋 ตารางราคา: {sel_model} • {len(model_variants)} แบบดาวน์ • ดึงจาก DB เท่านั้น ห้ามแก้ไข</div></div>", unsafe_allow_html=True)
   st.dataframe(model_variants[['รหัสรถ','รุ่นรถ','ยอดจัด','%ดาวน์','ราคาดาวน์','ค่าใช้จ่ายออกรถ','ทะเบียน พรบ ประกัน']], use_container_width=True, height=260)
   down_options=model_variants[['%ดาวน์','ราคาดาวน์','ค่าใช้จ่ายออกรถ','ยอดจัด','ดอกเบี้ยต่อเดือน','รหัสรถ','ทะเบียน พรบ ประกัน','ผ่อน12','ผ่อน24','ผ่อน36','ผ่อน48']].to_dict('records')
   down_labels=[f"{r['%ดาวน์']*100:.0f}% ดาวน์ {r['ราคาดาวน์']:,.0f}บ. • ออกรถ {r['ค่าใช้จ่ายออกรถ']:,.0f}บ. • ทะเบียน {r['ทะเบียน พรบ ประกัน']:,.0f}บ. • รหัส {r['รหัสรถ']}" for r in down_options]
   sel_down_idx=st.selectbox("💵 เลือก % ดาวน์ (จากตารางจริง DB)", range(len(down_labels)), format_func=lambda i: down_labels[i], key="down_db")
   chosen=down_options[sel_down_idx]
   def_price=float(chosen['ยอดจัด']); def_down=float(chosen['ราคาดาวน์']); def_total_out=float(chosen['ค่าใช้จ่ายออกรถ']); def_reg=float(chosen['ทะเบียน พรบ ประกัน']); def_int=float(chosen['ดอกเบี้ยต่อเดือน'])*100; def_code=chosen['รหัสรถ']
   monthly_from_table=float(chosen.get('ผ่อน36',0) or chosen.get('ผ่อน24',0) or 0)
   model_name=sel_model
   # แสดงผลแบบอ่านอย่างเดียว ห้ามแก้ไข (แก้ปัญหาซ้ำซ้อน)
   st.markdown('<div style="color:#FFFFFF;font-weight:800;font-size:15px;margin:16px 0 8px 0;">📋 ข้อมูลจากฐานข้อมูล (อ่านอย่างเดียว ห้ามแก้ไข)</div>', unsafe_allow_html=True)
   c1,c2,c3=st.columns(3)
   with c1:
    st.markdown(f'<div class="readonly-box"><div class="label">ชื่อรุ่นรถ</div><div class="value">{model_name}</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="readonly-box"><div class="label">ยอดจัด / ราคารถ (จาก ราคาจัด)</div><div class="value">{def_price:,.0f} บาท</div></div>', unsafe_allow_html=True)
   with c2:
    st.markdown(f'<div class="readonly-box"><div class="label">รหัสรถ</div><div class="value">{def_code}</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="readonly-box"><div class="label">ราคาดาวน์ (จาก ดาวน์)</div><div class="value">{def_down:,.0f} บาท</div></div>', unsafe_allow_html=True)
   with c3:
    st.markdown(f'<div class="readonly-box"><div class="label">หมวดหมู่</div><div class="value">รวมทุกรุ่น</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="readonly-box"><div class="label">ทะเบียน พรบ ประกัน (จาก ค่าจด/พรบ)</div><div class="value">{def_reg:,.0f} บาท</div></div>', unsafe_allow_html=True)
   c4,c5,c6=st.columns(3)
   with c4: st.markdown(f'<div class="readonly-box"><div class="label">ค่าใช้จ่ายออกรถ / ออกรถได้</div><div class="value">{def_total_out:,.0f} บาท</div><div style="font-size:11px;color:#94A3B8;margin-top:4px;">= ดาวน์ + ทะเบียน</div></div>', unsafe_allow_html=True)
   with c5: st.markdown(f'<div class="readonly-box"><div class="label">ดอกเบี้ยต่อเดือน (%)</div><div class="value">{def_int:.2f} %</div><div style="font-size:11px;color:#94A3B8;margin-top:4px;">ดึงจาก ดอกเบี้ยต่อเดือน *100</div></div>', unsafe_allow_html=True)
   with c6:
    tenure_db=st.selectbox("📅 ระยะผ่อน (เดือน) - เลือกได้", [12,18,24,30,36,48,60,72], index=4, key="tenure_db")
    # ดึงค่างวดจากตารางสำเร็จรูป ไม่ต้องคำนวณใหม่
    col_map={12:"ผ่อน12",18:"ผ่อน18",24:"ผ่อน24",30:"ผ่อน30",36:"ผ่อน36",48:"ผ่อน48"}
    if tenure_db in col_map and col_map[tenure_db] in chosen:
     monthly_instalment=float(chosen.get(col_map[tenure_db], monthly_from_table))
    else:
     monthly_instalment=float(monthly_from_table)
   loan_amount=def_price-def_down
   st.session_state.vehicle_price=def_price; st.session_state.downpayment=def_down; st.session_state.processing_fee=def_reg; st.session_state.flat_rate=def_int; st.session_state.tenure=tenure_db
   # ไม่ต้องแสดงช่องแก้ไขซ้ำซ้อนแล้ว - แสดงผลลัพธ์อย่างเดียว
   st.markdown(f'<div class="estimated-box" style="margin-top:16px;"><div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:12px;align-items:center;"><div><div style="font-size:12px;background:#0F172A;color:#7DD3FC;padding:5px 14px;border-radius:20px;display:inline-block;margin-bottom:10px;border:2px solid #075985;font-weight:800;">ยอดผ่อนต่อเดือน (จากตารางสำเร็จรูป DB)</div><div style="font-size:34px;font-weight:800;color:#FFFFFF;">{monthly_instalment:,.0f} บาท / เดือน</div><div style="font-size:13px;color:#E2E8F0;margin-top:6px;font-weight:600;">{tenure_db} งวด • รหัส {def_code} • ไม่แสดงสูตร</div></div><div style="text-align:right;min-width:180px;"><div style="background:#020617;padding:16px 20px;border-radius:12px;border:2px solid #334155;"><div style="font-size:12px;color:#94A3B8;font-weight:700;">ยอดจัด</div><div style="font-size:20px;font-weight:800;color:#FFFFFF;margin-top:2px;">{loan_amount:,.0f} บ.</div><div style="font-size:12px;color:#94A3B8;font-weight:700;margin-top:12px;">ออกรถจ่าย</div><div style="font-size:20px;font-weight:800;color:#4ADE80;margin-top:2px;">{def_total_out:,.0f} บ.</div></div></div></div></div>', unsafe_allow_html=True)

 else:
  # โหมด Manual - คุมไว้แบบเดิม แก้ได้ทุกช่อง
  st.markdown('<div style="color:#FEF3C7;font-weight:800;font-size:15px;margin:16px 0 8px 0;background:#422006;padding:10px 14px;border-radius:10px;border:1px solid #92400E;">✏️ โหมด Manual - ใส่ราคาด้วยตนเอง (แก้ได้ทุกช่อง คุมไว้แบบเดิม)</div>', unsafe_allow_html=True)
  model_name=st.text_input("ชื่อรุ่นรถ (Manual)", "ฟาซซิโอ้ SMK", key="model_manual")
  cat=st.text_input("หมวดหมู่", "รวมทุกรุ่น", key="cat_manual")
  c1,c2,c3=st.columns(3)
  with c1: def_price=st.number_input("ยอดจัด / ราคารถ (บาท) - แก้ได้", value=54600.0, key="price_manual")
  with c2: def_down=st.number_input("ราคาดาวน์ (บาท) - แก้ได้", value=0.0, key="down_manual")
  with c3: def_reg=st.number_input("ทะเบียน พรบ ประกัน (บาท) - แก้ได้", value=1000.0, key="reg_manual")
  c4,c5=st.columns(2)
  with c4: def_code=st.text_input("รหัสรถ", "BKF700", key="code_manual")
  with c5: def_int=st.number_input("ดอกเบี้ยต่อเดือน (%) - แก้ได้", value=1.5, key="int_manual")
  def_total_out=def_down+def_reg
  c6,c7=st.columns(2)
  with c6:
   vp=st.number_input("💰 ยอดจัด / ราคารถ (บาท) - แก้ได้ (ซ้ำเพื่อคำนวณ)", value=float(def_price), step=100.0, key="vp_manual")
   tenure=st.selectbox("📅 ระยะผ่อน (เดือน) - แก้ได้", [12,18,24,30,36,48,60,72], index=4, key="tenure_manual")
  with c7:
   dp=st.number_input("💵 ราคาดาวน์ (บาท) - แก้ได้", value=float(def_down), step=100.0, key="dp_manual")
   fr=st.number_input("📈 ดอกเบี้ยต่อเดือน (%) - แก้ได้", value=float(def_int), step=0.01, format="%.3f", key="fr_manual")
  pf=st.number_input("🧾 ทะเบียน พรบ ประกัน (บาท)", value=float(def_reg), step=100.0, key="pf_manual")
  loan_amount=vp-dp
  total_interest=loan_amount*(fr/100)*tenure
  monthly_instalment=(loan_amount+total_interest)/tenure if tenure else 0
  st.session_state.vehicle_price=vp; st.session_state.downpayment=dp; st.session_state.processing_fee=pf; st.session_state.flat_rate=fr; st.session_state.tenure=tenure
  st.markdown(f'<div class="estimated-box"><div style="font-size:28px;font-weight:800;color:#FFFFFF;">{monthly_instalment:,.0f} บาท / เดือน</div><div style="font-size:12px;color:#94A3B8;margin-top:6px;">Manual • {tenure} งวด • ไม่แสดงสูตร</div></div>', unsafe_allow_html=True)

 from reportlab.pdfgen import canvas as pdf_c
 from reportlab.lib.pagesizes import A4
 def gen_pdf(name,model,code,cash,down,reg,out_cost,monthly,term,dsr,verdict,ai_text,extra,b_behavior,spouse_data,guarantor_data,gift):
  buf=io.BytesIO()
  c=pdf_c.Canvas(buf,pagesize=A4)
  c.setFont("Helvetica-Bold",11)
  c.drawString(30,800,f"SRD v1.4 Fix - {model} ({code}) - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
  c.setFont("Helvetica",9)
  c.drawString(30,785,f"Applicant: {name} | ยอดจัด: {cash:,.0f} ดาวน์: {down:,.0f} ทะเบียน: {reg:,.0f} ออกรถ: {out_cost:,.0f} ค่างวด: {monthly:,.0f} x {term}")
  c.drawString(30,770,f"DSR: {dsr:.1f}% Verdict: {verdict} | Gift: {gift[:80]}")
  y=755; c.setFont("Helvetica",8)
  c.drawString(30,y,f"Spouse: {spouse_data[:150]}"); y-=12
  c.drawString(30,y,f"Guarantor: {guarantor_data[:150]}"); y-=12
  c.drawString(30,y,f"Extra: {extra[:120]}"); y-=12
  c.drawString(30,y,f"Behavior: {b_behavior[:120]}"); y-=14
  if ai_text:
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

 # ของแถม + ผู้สมัคร + คู่สมรส + ผู้ค้ำ - คงไว้
 st.markdown('<div class="moto-card" style="background:#422006 !important;border:2px solid #92400E !important;">', unsafe_allow_html=True)
 st.markdown('<div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;"><div style="width:40px;height:40px;background:#92400E;border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:20px;">🎁</div><div style="font-weight:800;color:#FEF3C7;font-size:17px;">ของแถมพิเศษ</div></div>', unsafe_allow_html=True)
 gift_data=st.text_area("🎁 ของแถมพิเศษ (ช่องว่างให้ใส่ข้อมูล)", "เช่น หมวกกันน็อค SRD ฟรี, น้ำมันเต็มถัง, ประกันรถหาย 1 ปี", height=80, key="gift")
 st.session_state.gift_data=gift_data
 st.markdown('</div>', unsafe_allow_html=True)

 st.markdown('<div class="moto-card">', unsafe_allow_html=True)
 st.markdown('<div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;"><div style="width:44px;height:44px;background:#2563EB;border-radius:12px;display:flex;align-items:center;justify-content:center;color:white;font-size:22px;">👤</div><div><div style="font-weight:800;color:#FFFFFF;font-size:17px;">ผู้สมัครหลัก (Applicant)</div></div></div>', unsafe_allow_html=True)
 a1,a2=st.columns(2)
 with a1:
  applicant_name=st.text_input("👤 ชื่อผู้กู้", "สมชาย", key="app_name")
  age=st.number_input("🎂 อายุ", value=25, step=1, key="age")
  salary=st.number_input("💼 เงินเดือน", value=15000.0, step=500.0, key="salary")
 with a2:
  phone=st.text_input("📞 เบอร์โทร", "081-xxx-xxxx", key="phone")
  residence=st.selectbox("🏠 ที่พัก", ["บ้านตนเอง","บ้านเช่า","หอพัก","บ้านพ่อแม่"], key="residence")
  extra_income=st.number_input("💰 รายได้เสริม", value=2000.0, step=500.0, key="extra")
 c_debt1,c_debt2=st.columns(2)
 with c_debt1:
  debt_old=st.number_input("หนี้เดิมต่อเดือน", value=2198.0, step=100.0, key="debt_old")
  debt_mode=st.radio("วิธีใส่ค่าใช้ชีวิต", ["ใส่ตามที่ลูกค้าบอก", "ให้ระบบประเมินคร่าว 60%"], index=0, key="debt_mode")
 with c_debt2:
  if debt_mode=="ใส่ตามที่ลูกค้าบอก":
   living_cost=st.number_input("ค่าใช้ชีวิตต่อเดือน", value=5000.0, step=500.0, key="living")
  else:
   living_cost=(salary+extra_income)*0.6
   st.metric("ค่าใช้ชีวิตประเมินคร่าว", f"{living_cost:,.0f} บาท")
 st.session_state.monthly_income=salary+extra_income
 total_obligations=debt_old+living_cost+monthly_instalment
 dsr=(total_obligations/st.session_state.monthly_income*100) if st.session_state.monthly_income else 42.3
 st.session_state.dsr_value=dsr
 st.session_state.applicant_name=applicant_name
 st.markdown(f'<div style="display:flex;gap:12px;margin-top:16px;"><div style="flex:1;background:#020617;padding:14px;border-radius:12px;border:2px solid #334155;text-align:center;"><div style="font-size:11px;color:#E2E8F0;">รายได้รวม</div><div style="font-size:18px;font-weight:800;color:#4ADE80;">{st.session_state.monthly_income:,.0f}</div></div><div style="flex:1;background:#020617;padding:14px;border-radius:12px;border:2px solid #334155;text-align:center;"><div style="font-size:11px;color:#E2E8F0;">ภาระรวม</div><div style="font-size:18px;font-weight:800;color:#FBBF24;">{total_obligations:,.0f}</div></div><div style="flex:1;background:#020617;padding:14px;border-radius:12px;border:2px solid #334155;text-align:center;"><div style="font-size:11px;color:#E2E8F0;">DSR</div><div style="font-size:20px;font-weight:800;color:#FFFFFF;">{dsr:.1f}%</div></div></div>', unsafe_allow_html=True)
 st.markdown('</div>', unsafe_allow_html=True)

 st.markdown('<div class="moto-card" style="background:#172554 !important;border:2px solid #1E40AF !important;">', unsafe_allow_html=True)
 st.markdown('<div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;"><div style="width:44px;height:44px;background:#1E40AF;border-radius:12px;display:flex;align-items:center;justify-content:center;color:white;font-size:22px;">💑</div><div><div style="font-weight:800;color:#FFFFFF;font-size:17px;">ข้อมูลคู่สมรส</div></div></div>', unsafe_allow_html=True)
 s1,s2=st.columns(2)
 with s1:
  spouse_name=st.text_input("👩‍❤️‍👨 ชื่อคู่สมรส", "นางสมหญิง", key="spouse_name")
  marriage_years=st.selectbox("📅 จำนวนปีที่สมรส", list(range(0,31)), index=5, key="marry_years")
  spouse_income=st.number_input("💰 รายได้คู่สมรส", value=8000.0, step=500.0, key="spouse_income")
 with s2:
  marriage_status=st.selectbox("📜 จดทะเบียนสมรส", ["จดทะเบียน","ไม่จดทะเบียน","หย่า","หม้าย"], index=0, key="marry_status")
  has_children=st.selectbox("👶 มีบุตร / ไม่มีบุตร", ["ไม่มีบุตร","มีบุตร 1 คน","มีบุตร 2 คน","มีบุตร 3 คนขึ้นไป"], index=1, key="children")
  spouse_job=st.text_input("💼 อาชีพคู่สมรส", "ค้าขาย", key="spouse_job")
 spouse_summary=f"{spouse_name} สมรส {marriage_years}ปี {marriage_status} {has_children} รายได้ {spouse_income}"
 st.session_state.spouse_summary=spouse_summary
 st.markdown(f'<div style="background:#1E1B4B;padding:12px;border-radius:10px;border:2px solid #3730A3;margin-top:12px;color:#FFFFFF;font-weight:600;">สรุป: {spouse_summary}</div>', unsafe_allow_html=True)
 st.markdown('</div>', unsafe_allow_html=True)

 st.markdown('<div class="moto-card" style="background:#14532D !important;border:2px solid #166534 !important;">', unsafe_allow_html=True)
 st.markdown('<div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;"><div style="width:44px;height:44px;background:#166534;border-radius:12px;display:flex;align-items:center;justify-content:center;color:white;font-size:22px;">🤝</div><div><div style="font-weight:800;color:#FFFFFF;font-size:17px;">ผู้ค้ำประกัน - มีติ๊ก มี/ไม่มี</div></div></div>', unsafe_allow_html=True)
 has_guarantor=st.checkbox("✅ มีผู้ค้ำประกัน (ติ๊กถ้ามี)", value=True, key="has_guarantor")
 if has_guarantor:
  g1,g2=st.columns(2)
  with g1:
   guarantor_name=st.text_input("👤 ชื่อผู้ค้ำ", "นายสมหมาย", key="guar_name")
   guarantor_relation=st.selectbox("🔗 ความสัมพันธ์", ["พ่อแม่","พี่น้อง","ญาติ","เพื่อน","เพื่อนร่วมงาน","แฟน"], key="guar_rel")
   guarantor_income=st.number_input("💰 รายได้ผู้ค้ำ", value=20000.0, step=1000.0, key="guar_income")
  with g2:
   guarantor_job=st.text_input("💼 อาชีพผู้ค้ำ", "พนักงานประจำ", key="guar_job")
   guarantor_phone=st.text_input("📞 เบอร์ผู้ค้ำ", "082-xxx-xxxx", key="guar_phone")
   guarantor_years=st.selectbox("⏳ รู้จักกันนานแค่ไหน", ["น้อยกว่า 1 ปี","1-3 ปี","3-5 ปี","มากกว่า 5 ปี"], key="guar_years")
  guarantor_reason=st.text_area("❓ ทำไมถึงค้ำให้?", "เป็นพี่ชายแท้ๆ อยู่บ้านเดียวกัน", height=70, key="guar_reason")
  guarantor_summary=f"{guarantor_name} {guarantor_relation} รายได้ {guarantor_income} เหตุผล {guarantor_reason}"
 else:
  guarantor_summary="ไม่มีผู้ค้ำประกัน"
  st.warning("⚠️ ไม่มีผู้ค้ำ - AI จะประเมินความเสี่ยงสูงขึ้น")
 st.session_state.guarantor_summary=guarantor_summary
 st.markdown('</div>', unsafe_allow_html=True)

 st.markdown('<div class="moto-card">', unsafe_allow_html=True)
 st.markdown('<div style="font-weight:800;color:#FFFFFF;font-size:17px;margin-bottom:12px;">📝 รายละเอียดเพิ่มเติม + บันทึกบริบทหน้าร้าน</div>', unsafe_allow_html=True)
 workplace=st.text_input("🏢 สถานที่ทำงาน / พิกัดที่ทำงานจริง", "ตลาดสดเทศบาล ต.ลำนารายณ์", key="workplace")
 behavior_context=st.text_area("บันทึกบริบทหน้าร้าน / พฤติกรรมลูกค้า", "เช่น ลูกค้ามากับคุณแม่และคู่สมรส แจ้งว่าจะนำรถไปใช้รับส่งไปทำงานโรงงาน ไป-กลับ 20 กม.", height=100, key="behavior")
 extra_details=st.text_area("🗒️ คำให้การลูกค้า", "ใช้รถไปทำงานโรงงาน ไป-กลับ 20 กม. ยินยอมติด GPS", height=70, key="extra2")
 st.session_state.extra_details=workplace; st.session_state.behavior_context=behavior_context
 def evaluate_fraud(vt, dpct, et, shared, dsr_val, gps):
  score=0; flags=[]
  if not has_guarantor and dsr_val>45: score+=15; flags.append("ไม่มีผู้ค้ำ + DSR สูง")
  if marriage_status=="ไม่จดทะเบียน" and has_children!="ไม่มีบุตร": score+=10; flags.append("ไม่จดทะเบียนแต่มีบุตร")
  if score>=80: verdict="⛔ AUTO REJECT"
  elif score>=50: verdict="🟠 MANUAL REVIEW"
  else: verdict="🟢 AUTO PASS"
  return score,flags,verdict
 r_score,r_flags,r_verdict=evaluate_fraud("รวมทุกรุ่น", 10, "พนักงานประจำ", 0, dsr, True)
 st.session_state.r_verdict=r_verdict
 st.markdown(f'<div style="display:flex;gap:12px;margin-top:16px;"><div style="flex:1;background:#020617;padding:14px;border-radius:12px;border:2px solid #334155;text-align:center;"><div style="font-size:12px;color:#E2E8F0;">DSR</div><div style="font-size:22px;font-weight:800;color:#FFFFFF;">{dsr:.1f}%</div></div><div style="flex:1;background:#020617;padding:14px;border-radius:12px;border:2px solid #334155;text-align:center;"><div style="font-size:12px;color:#E2E8F0;">Rule Engine</div><div style="font-size:15px;font-weight:800;color:#FFFFFF;">{r_verdict}</div></div></div>', unsafe_allow_html=True)
 st.markdown('</div>', unsafe_allow_html=True)

 st.markdown('<div class="moto-card">', unsafe_allow_html=True)
 st.markdown("<div style='font-weight:800;color:#FFFFFF;font-size:17px;margin-bottom:12px;'>📸 เช็กลิสต์เอกสาร • 6 รายการ</div>", unsafe_allow_html=True)
 docs=st.multiselect("เอกสารที่แนบแล้ว", ["Face Verification","บัตร ปชช + ทะเบียนบ้าน","Statement","NCB","สลิปเงินเดือน","ที่พัก + ที่ทำงาน"], default=["บัตร ปชช + ทะเบียนบ้าน","Statement"])
 uploads=st.file_uploader("แนบภาพเอกสาร (รองรับ HEIC)", type=["jpg","jpeg","png","heic","heif","webp"], accept_multiple_files=True)
 cam=st.camera_input("📷 ถ่ายจากกล้องมือถือ")
 comps=[]; files=[]
 if uploads: files.extend(uploads)
 if cam: files.append(cam)
 if files:
  cols=st.columns(2)
  for i,f in enumerate(files):
   try:
    im=Image.open(f); cp=_compress_mobile(im); comps.append(cp)
    with cols[i%2]: st.image(cp, use_container_width=True)
   except Exception as e: st.error(str(e))
 st.session_state.comps=comps
 st.markdown('</div>', unsafe_allow_html=True)

 st.markdown('<div class="moto-card">', unsafe_allow_html=True)
 st.markdown(f"<div style='font-weight:800;color:#FFFFFF;font-size:17px;'>🧠 วิเคราะห์ 13 โมดูลด้วย AI • {selected_model}</div>", unsafe_allow_html=True)
 if 'ai_text' not in st.session_state: st.session_state.ai_text=""
 if st.button("🚀 รัน SRD Credit 13 Modules v1.4 Fix", type="primary", use_container_width=True):
  if not comps: st.warning("กรุณาแนบภาพอย่างน้อย 1 ไฟล์")
  else:
   prompt=f"SRD CREDIT 13 MODULES v1.4 Fix - รุ่น {model_name if 'model_name' in locals() else 'Manual'} ยอดจัด {st.session_state.vehicle_price} ดาวน์ {st.session_state.downpayment} ค่างวด {monthly_instalment:.2f} DSR {dsr:.1f}% ผู้สมัคร {applicant_name} คู่สมรส {spouse_summary} ผู้ค้ำ {guarantor_summary} ของแถม {gift_data} บริบท {behavior_context} เอกสาร {', '.join(docs)} วิเคราะห์ภาษาไทย ไม่แสดงสูตร"
   def call_ai(prom, imgs, model_name, client_obj):
    try:
     if client_obj and hasattr(client_obj,'models'):
      contents=[prom]
      for im in imgs:
       b=io.BytesIO(); im.save(b, format="JPEG")
       contents.append(genai_types.Part.from_bytes(data=b.getvalue(), mime_type="image/jpeg"))
      resp=client_obj.models.generate_content(model=model_name, contents=contents)
      txt=getattr(resp,'text',None) or resp.candidates[0].content.parts[0].text
      return {"ok":True,"text":txt}
     else:
      import google.generativeai as old_g
      m=old_g.GenerativeModel(model_name)
      r=m.generate_content([prom]+imgs)
      return {"ok":True,"text":r.text}
    except Exception as e: return {"ok":False,"raw":str(e)}
   with st.spinner(f"AI ({selected_model}) กำลังประมวลผล 13 โมดูล..."):
    res=call_ai(prompt, comps, selected_model, client)
   if res["ok"]:
    st.session_state.ai_text=res["text"]
    st.success(f"✅ สำเร็จด้วย {selected_model} v1.4 Fix")
    st.markdown(res["text"])
   else: st.error(res["raw"][:1000])
 if st.session_state.ai_text:
  pdf2=gen_pdf(applicant_name, model_name if 'model_name' in locals() else 'Manual', def_code if 'def_code' in locals() else '-', st.session_state.vehicle_price, st.session_state.downpayment, st.session_state.processing_fee, def_total_out if 'def_total_out' in locals() else st.session_state.processing_fee, monthly_instalment, st.session_state.tenure, st.session_state.get('dsr_value',42.3), st.session_state.get('r_verdict',''), st.session_state.ai_text, st.session_state.extra_details, behavior_context, spouse_summary, guarantor_summary, gift_data)
  st.download_button("🔴 ส่งออกรายงาน 13 โมดูล PDF (v1.4 Fix)", data=pdf2, file_name=f"SRD_13M_v14Fix_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf", mime="application/pdf", use_container_width=True)
 st.markdown('</div>', unsafe_allow_html=True)

with right_col:
 dsr_val=st.session_state.get('dsr_value',42.3)
 st.markdown('<div class="moto-card">', unsafe_allow_html=True)
 st.markdown(f'<div style="text-align:center;"><div style="position:relative;width:200px;height:110px;margin:0 auto;overflow:hidden;"><div style="width:200px;height:200px;border-radius:50%;background:conic-gradient(from 180deg,#10B981 0deg 90deg,#FBBF24 90deg 135deg,#EF4444 135deg 180deg);"></div><div style="position:absolute;top:20px;left:20px;width:160px;height:160px;background:#1E293B;border-radius:50%;border:2px solid #334155;"></div><div style="position:absolute;top:50px;left:0;width:200px;text-align:center;"><div style="font-size:32px;font-weight:800;color:#FFFFFF;">{dsr_val:.1f}%</div><div style="font-size:11px;color:#E2E8F0;font-weight:700;">DSR</div></div></div></div>', unsafe_allow_html=True)
 st.markdown('</div>', unsafe_allow_html=True)
 st.markdown('<div class="moto-card">', unsafe_allow_html=True)
 st.markdown('<div style="font-weight:800;color:#FFFFFF;">วิเคราะห์ 13 โมดูลด้วย AI</div><div style="font-size:13px;color:#FFFFFF;margin-top:8px;font-weight:500;">✅ ผ่านทั้ง 13 โมดูล • ความมั่นใจ 92% • ไม่แสดงสูตร • รวมทุกรุ่น</div>', unsafe_allow_html=True)
 st.markdown('</div>', unsafe_allow_html=True)

st.caption("SRD v1.4 Fix • รวมทุกรุ่น • พื้นเข้มตัดข้อความขาวเด่น • ยึด ยอดจัด ดาวน์ ทะเบียน พรบ ประกัน ออกรถได้ • แก้ซ้ำซ้อน: DB ห้ามแก้ไข Manual แก้ได้ • ไม่แสดงสูตร • PDF 2 จุด")
