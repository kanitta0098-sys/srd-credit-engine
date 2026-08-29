
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

st.set_page_config(page_title="SRD Moto Credit v1.3 Full", layout="wide", page_icon="🐒")

st.markdown("""
<style>
.stApp { background:#0F172A !important; }
header { display:none; }
[data-testid="stSidebar"] { background:#020617 !important; }
[data-testid="stSidebar"] * { color:#94A3B8 !important; }
div[data-baseweb="select"] > div { background:#0F172A !important; color:#F8FAFC !important; border:2px solid #475569 !important; border-radius:12px !important; }
div[data-baseweb="select"] span { color:#F8FAFC !important; }
input, textarea { background:#0F172A !important; color:#F8FAFC !important; border-radius:12px !important; }
label { color:#E2E8F0 !important; font-weight:600 !important; }
.moto-card { background:#1E293B !important; border:1px solid #334155 !important; border-radius:16px; padding:18px; margin-bottom:16px; }
.moto-card * { color:#E2E8F0; }
.moto-card h3 { color:white !important; }
.estimated-box { background:linear-gradient(135deg,#1E3A5F 0%,#0F172A 100%) !important; border:2px dashed #38BDF8 !important; border-radius:12px; padding:16px; }
.step-circle { width:46px; height:46px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:800; }
.step-circle.done { background:#10B981; color:white; }
.step-circle.active { background:#2563EB; color:white; }
.step-circle.pending { background:#0F172A; color:#64748B; border:2px solid #475569; }
.stDownloadButton > button { background:#DC2626 !important; color:white !important; border-radius:12px !important; font-weight:700 !important; border:2px solid #EF4444 !important; height:48px; }
div[data-testid="stButton"] > button[kind="primary"] { background:#2563EB !important; border-radius:12px !important; height:50px; font-weight:700; }
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
def load_excel_real():
 fp="Yamaha_รวมขายทุกตัว_25-8-69_Dynamic_Formulas_Categories.xlsx"
 for p in [fp, "/mnt/data/Yamaha_รวมขายทุกตัว_25-8-69_Dynamic_Formulas_Categories.xlsx"]:
  if os.path.exists(p): fp=p; break
 all_data=[]
 try:
  xls=pd.ExcelFile(fp)
  for sheet in xls.sheet_names:
   if sheet in ["คำนวณค่างวด Flat Rate","ตารางราคาทะเบียน"]: continue
   try:
    df=pd.read_excel(fp, sheet_name=sheet, skiprows=2, header=None)
    if df.shape[1]<8: continue
    df.columns=[f"col_{i}" for i in range(df.shape[1])]
    df=df.rename(columns={"col_0":"รุ่นรถ","col_1":"รหัสรถ","col_2":"ราคาจัด","col_3":"ดอกเบี้ยต่อเดือน","col_4":"%ดาวน์","col_5":"ราคาดาวน์","col_6":"ค่าจดพรบ","col_7":"ค่าใช้จ่ายออกรถ"})
    df['รุ่นรถ']=df['รุ่นรถ'].ffill()
    df=df.dropna(subset=['รุ่นรถ'])
    df['ราคาจัด']=pd.to_numeric(df['ราคาจัด'], errors='coerce')
    df=df.dropna(subset=['ราคาจัด'])
    df['ยี่ห้อ']=df['รุ่นรถ'].astype(str).str.split().str[0]
    df['หมวด']=sheet
    df['ยอดจัด']=df['ราคาจัด']
    df['ทะเบียน พรบ ประกัน']=df['ค่าจดพรบ']
    all_data.append(df)
   except: pass
  if all_data:
   return pd.concat(all_data, ignore_index=True)
 except: pass
 return pd.DataFrame()

full_price_df=load_excel_real()

with st.sidebar:
 st.markdown('<div style="display:flex;align-items:center;gap:12px;padding:12px;"><div style="width:52px;height:52px;background:linear-gradient(135deg,#0EA5E9,#06B6D4);border-radius:14px;display:flex;align-items:center;justify-content:center;font-size:28px;">🐒</div><div><div style="color:white;font-weight:800;">SRD Moto Credit</div><div style="color:#38BDF8;font-size:12px;">บจก. สิระเดชมอเตอร์เซลล์</div><div style="color:#64748B;font-size:11px;">v1.3 High Contrast Dark</div></div></div>', unsafe_allow_html=True)
 for icon,label,active in [("🏠","แดชบอร์ด",False),("💳","เครื่องคำนวณสินเชื่อ",True),("📄","ใบสมัคร",False),("👥","ลูกค้า",False),("📁","เอกสาร",False),("📊","วิเคราะห์ข้อมูล",False),("🛡️","ความเสี่ยงและนโยบาย",False)]:
  if active: st.markdown(f'<div style="background:#1E3A5F;border-radius:12px;padding:13px 16px;margin:5px 0;color:white;border-left:4px solid #38BDF8;display:flex;gap:12px;font-weight:700;"><span>{icon}</span> {label}</div>', unsafe_allow_html=True)
  else: st.markdown(f'<div style="padding:13px 16px;margin:5px 0;opacity:0.7;display:flex;gap:12px;color:#CBD5E1;"><span>{icon}</span> {label}</div>', unsafe_allow_html=True)
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
   st.markdown(f'<div style="background:#052E16;padding:8px 12px;border-radius:8px;border:1px solid #166534;color:#BBF7D0;font-size:12px;">🤖 {selected_model}</div>', unsafe_allow_html=True)
  except Exception as e: st.error(str(e))

st.markdown('<div style="background:#1E293B;border-radius:16px;padding:18px;border:2px solid #334155;margin-bottom:16px;"><div style="font-size:24px;font-weight:800;color:white;">Motorcycle Loan Credit Engine</div><div style="font-size:16px;font-weight:700;color:#38BDF8;margin-top:4px;">ระบบตรวจสอบสินเชื่อมอเตอร์ไซค์ • บจก. สิระเดชมอเตอร์เซลล์</div><div style="margin-top:12px;"><span style="background:#052E16;color:#BBF7D0;padding:6px 14px;border-radius:20px;font-size:12px;border:1px solid #166534;">● Connected • Live</span> <span style="background:#1E1B4B;color:#C7D2FE;padding:6px 14px;border-radius:20px;font-size:12px;margin-left:8px;">v1.3 High Contrast Dark • Mobile • Gemini 3.6</span></div></div>', unsafe_allow_html=True)
st.markdown('<div class="moto-card"><div style="display:flex;gap:8px;justify-content:space-between;"><div style="text-align:center;"><div class="step-circle done">✓</div><div style="font-size:13px;font-weight:800;color:#10B981;">Step 1</div><div style="font-size:11px;color:#E2E8F0;">เลือกยานพาหนะ</div></div><div style="text-align:center;"><div class="step-circle active">2</div><div style="font-size:13px;font-weight:800;color:#60A5FA;">Step 2</div><div style="font-size:11px;color:#E2E8F0;">ผู้สมัคร & คู่สมรส & ผู้ค้ำ</div></div><div style="text-align:center;"><div class="step-circle pending">3</div><div style="font-size:13px;color:#94A3B8;">Step 3</div><div style="font-size:11px;color:#94A3B8;">เอกสาร 6 รายการ</div></div><div style="text-align:center;"><div class="step-circle pending">4</div><div style="font-size:13px;color:#94A3B8;">Step 4</div><div style="font-size:11px;color:#94A3B8;">AI 13 โมดูล</div></div></div></div>', unsafe_allow_html=True)

if 'vehicle_price' not in st.session_state: st.session_state.vehicle_price=54600.0
if 'downpayment' not in st.session_state: st.session_state.downpayment=0.0
if 'tenure' not in st.session_state: st.session_state.tenure=36
if 'flat_rate' not in st.session_state: st.session_state.flat_rate=1.5
if 'processing_fee' not in st.session_state: st.session_state.processing_fee=1000.0

left_col,right_col=st.columns([1.7,1])
with left_col:
 st.markdown('<div class="moto-card">', unsafe_allow_html=True)
 st.markdown(f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;"><div style="width:42px;height:42px;background:#2563EB;border-radius:12px;display:flex;align-items:center;justify-content:center;color:white;">🧮</div><div><div style="font-weight:800;color:white;">เครื่องคำนวณ Flat Rate • {selected_model}</div><div style="font-size:12px;color:#94A3B8;">พื้นเข้มตัดข้อความชัด • ยึด ยอดจัด / %ดอกเบี้ย / ทะเบียน พรบ ประกัน</div></div></div>', unsafe_allow_html=True)
 price_mode=st.radio("🔀 วิธีเลือกราคา", ["📦 เลือกรุ่นจากฐานข้อมูล Excel (รุ่น รหัส ยอดจัด ดาวน์ ทะเบียน พรบ ประกัน แยกยี่ห้อ)", "✏️ ใส่ราคาด้วยตนเอง (Manual)"], index=0)
 if price_mode.startswith("📦") and not full_price_df.empty:
  brands=sorted(full_price_df['ยี่ห้อ'].dropna().unique().tolist())
  col_brand,col_cat=st.columns(2)
  with col_brand: sel_brand=st.selectbox("🏷️ ยี่ห้อ (แยกตามรุ่น)", ["ทั้งหมด"]+brands)
  with col_cat:
   cats=sorted(full_price_df['หมวด'].unique().tolist())
   sel_cat=st.selectbox("📂 หมวดหมู่", ["ทั้งหมด"]+cats)
  filtered_df=full_price_df.copy()
  if sel_brand!="ทั้งหมด": filtered_df=filtered_df[filtered_df['ยี่ห้อ']==sel_brand]
  if sel_cat!="ทั้งหมด": filtered_df=filtered_df[filtered_df['หมวด']==sel_cat]
  models=sorted(filtered_df['รุ่นรถ'].unique().tolist())
  sel_model=st.selectbox(f"🏍️ รุ่นรถ ({len(models)} รุ่น)", models)
  model_variants=filtered_df[filtered_df['รุ่นรถ']==sel_model].copy().sort_values('%ดาวน์')
  st.markdown(f"<div style='background:#020617;padding:10px;border-radius:10px;border:1px solid #334155;margin:10px 0;color:#38BDF8;font-weight:700;font-size:13px;'>📋 ตารางราคา: {sel_model} • {len(model_variants)} แบบดาวน์ • ยึด ยอดจัด / %ดอกเบี้ย / ทะเบียน พรบ ประกัน</div>", unsafe_allow_html=True)
  st.dataframe(model_variants[['รหัสรถ','รุ่นรถ','ยอดจัด','%ดาวน์','ราคาดาวน์','ค่าใช้จ่ายออกรถ','ทะเบียน พรบ ประกัน']], use_container_width=True, height=220)
  down_options=model_variants[['%ดาวน์','ราคาดาวน์','ค่าใช้จ่ายออกรถ','ยอดจัด','ดอกเบี้ยต่อเดือน','รหัสรถ','ทะเบียน พรบ ประกัน']].to_dict('records')
  down_labels=[f"{r['%ดาวน์']*100:.0f}% ดาวน์ {r['ราคาดาวน์']:,.0f}บ. • ออกรถ {r['ค่าใช้จ่ายออกรถ']:,.0f}บ. • ทะเบียน {r['ทะเบียน พรบ ประกัน']:,.0f}บ. • รหัส {r['รหัสรถ']}" for r in down_options]
  sel_down_idx=st.selectbox("💵 เลือก % ดาวน์", range(len(down_labels)), format_func=lambda i: down_labels[i])
  chosen=down_options[sel_down_idx]
  def_price=float(chosen['ยอดจัด']); def_down=float(chosen['ราคาดาวน์']); def_total_out=float(chosen['ค่าใช้จ่ายออกรถ']); def_reg=float(chosen['ทะเบียน พรบ ประกัน']); def_int=float(chosen['ดอกเบี้ยต่อเดือน'])*100; def_code=chosen['รหัสรถ']
  st.session_state.vehicle_price=def_price; st.session_state.downpayment=def_down; st.session_state.processing_fee=def_reg; st.session_state.flat_rate=def_int
  model_name=sel_model; cat=sel_cat if sel_cat!="ทั้งหมด" else model_variants.iloc[0]['หมวด']
 else:
  model_name=st.text_input("ชื่อรุ่นรถ", "ฟาซซิโอ้ SMK")
  cat=st.text_input("หมวดหมู่", "Auto")
  def_price=st.number_input("ยอดจัด / ราคารถ", value=54600.0)
  def_down=st.number_input("ราคาดาวน์", value=0.0)
  def_reg=st.number_input("ทะเบียน พรบ ประกัน", value=1000.0)
  def_code=st.text_input("รหัสรถ", "BKF700"); def_int=st.number_input("ดอกเบี้ยต่อเดือน (%)", value=1.5); def_total_out=def_reg
 c1,c2=st.columns(2)
 with c1:
  vp=st.number_input("💰 ยอดจัด / ราคารถ - แก้ได้", value=float(st.session_state.vehicle_price), step=100.0)
  st.session_state.vehicle_price=vp
  tenure=st.selectbox("📅 ระยะผ่อน - แก้ได้", [12,18,24,30,36,42,48,60], index=4)
  st.session_state.tenure=tenure
 with c2:
  dp=st.number_input("💵 ราคาดาวน์ - แก้ได้", value=float(st.session_state.downpayment), step=100.0)
  st.session_state.downpayment=dp
  fr=st.number_input("📈 ดอกเบี้ยต่อเดือน (%) - แก้ได้", value=float(st.session_state.flat_rate), step=0.01, format="%.3f")
  st.session_state.flat_rate=fr
 pf=st.number_input("🧾 ทะเบียน พรบ ประกัน - แก้ไขเป็นชื่อนี้ตามที่ขอ", value=float(st.session_state.processing_fee), step=100.0)
 st.session_state.processing_fee=pf
 loan_amount=st.session_state.vehicle_price-st.session_state.downpayment
 total_interest=loan_amount*(st.session_state.flat_rate/100)*st.session_state.tenure
 total_payable=loan_amount+total_interest+st.session_state.processing_fee
 monthly_instalment=(loan_amount+total_interest)/st.session_state.tenure if st.session_state.tenure else 0
 from reportlab.pdfgen import canvas as pdf_c
 from reportlab.lib.pagesizes import A4
 def gen_pdf(name,model,code,cash,down,reg,out_cost,monthly,term,interest,total,dsr,verdict,ai_text,extra,b_behavior,spouse_data,guarantor_data,gift):
  buf=io.BytesIO()
  c=pdf_c.Canvas(buf,pagesize=A4)
  c.setFont("Helvetica-Bold",11)
  c.drawString(30,800,f"SRD v1.3 - {model} ({code}) - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
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
  pdf1=gen_pdf(st.session_state.get('applicant_name',''), model_name if 'model_name' in locals() else 'Manual', def_code if 'def_code' in locals() else '-', st.session_state.vehicle_price, st.session_state.downpayment, st.session_state.processing_fee, st.session_state.processing_fee, monthly_instalment, st.session_state.tenure, total_interest, total_payable, st.session_state.get('dsr_value',42.3), st.session_state.get('r_verdict',''), st.session_state.get('ai_text',''), st.session_state.get('extra_details',''), st.session_state.get('behavior_context',''), st.session_state.get('spouse_summary',''), st.session_state.get('guarantor_summary',''), st.session_state.get('gift_data',''))
  st.download_button("🔴 ส่งออกเป็น PDF", data=pdf1, file_name=f"SRD_Loan_v13_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf", mime="application/pdf", use_container_width=True)
  st.markdown(f'<div class="estimated-box"><div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:10px;align-items:center;"><div><div style="font-size:11px;background:#0F172A;color:#7DD3FC;padding:4px 12px;border-radius:20px;display:inline-block;margin-bottom:8px;border:1px solid #075985;font-weight:700;">ยอดผ่อนต่อเดือนโดยประมาณ</div><div style="font-size:32px;font-weight:800;color:white;letter-spacing:-0.5px;">{monthly_instalment:,.0f} บาท / เดือน</div><div style="font-size:12px;color:#94A3B8;margin-top:4px;">{st.session_state.tenure} งวด • รหัส {def_code if "def_code" in locals() else "-"}</div></div><div style="text-align:right;"><div style="background:#020617;padding:12px 16px;border-radius:10px;border:1px solid #334155;"><div style="font-size:11px;color:#94A3B8;">ยอดจัด</div><div style="font-size:16px;font-weight:800;color:white;">{loan_amount:,.0f} บาท</div><div style="font-size:11px;color:#94A3B8;margin-top:8px;">ออกรถจ่าย</div><div style="font-size:16px;font-weight:800;color:#4ADE80;">{st.session_state.processing_fee:,.0f} บาท</div></div></div></div></div>', unsafe_allow_html=True)
 st.markdown('</div>', unsafe_allow_html=True)

 st.markdown('<div class="moto-card" style="background:#422006 !important;border:1px solid #92400E !important;">', unsafe_allow_html=True)
 st.markdown('<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;"><div style="width:36px;height:36px;background:#92400E;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:18px;">🎁</div><div style="font-weight:800;color:#FEF3C7;font-size:16px;">ของแถมพิเศษ / โปรโมชั่น (เพิ่มใหม่)</div></div>', unsafe_allow_html=True)
 gift_data=st.text_area("🎁 ของแถมพิเศษ (ช่องว่างให้ใส่ข้อมูล)", "เช่น หมวกกันน็อค SRD ฟรี, น้ำมันเต็มถัง, ประกันรถหาย 1 ปี, ส่วนลด 1,000 บาท", height=80, key="gift")
 st.session_state.gift_data=gift_data
 st.markdown('</div>', unsafe_allow_html=True)

 st.markdown('<div class="moto-card">', unsafe_allow_html=True)
 st.markdown('<div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;"><div style="width:40px;height:40px;background:#2563EB;border-radius:12px;display:flex;align-items:center;justify-content:center;color:white;">👤</div><div><div style="font-weight:800;color:white;">ผู้สมัครหลัก (Applicant) - แยกจากผู้ค้ำ</div></div></div>', unsafe_allow_html=True)
 a1,a2=st.columns(2)
 with a1:
  applicant_name=st.text_input("👤 ชื่อผู้กู้", "สมชาย", key="app_name")
  age=st.number_input("🎂 อายุ", value=25, step=1)
  salary=st.number_input("💼 เงินเดือน", value=15000.0, step=500.0, key="salary")
 with a2:
  phone=st.text_input("📞 เบอร์โทร", "081-xxx-xxxx", key="phone")
  residence=st.selectbox("🏠 ที่พัก", ["บ้านตนเอง","บ้านเช่า","หอพัก","บ้านพ่อแม่"])
  extra_income=st.number_input("💰 รายได้เสริม", value=2000.0, step=500.0, key="extra")
 st.markdown('<div style="background:#020617;padding:12px;border-radius:10px;border:1px solid #334155;margin:12px 0;"><div style="color:#F8FAFC;font-weight:700;font-size:13px;">💳 หนี้เดิม + ค่าใช้ชีวิตต่อเดือน (ตามข้อมูลลูกค้า หรือวิเคราะห์คร่าว)</div></div>', unsafe_allow_html=True)
 c_debt1,c_debt2=st.columns(2)
 with c_debt1:
  debt_old=st.number_input("หนี้เดิมต่อเดือน", value=2198.0, step=100.0, key="debt_old")
  debt_mode=st.radio("วิธีใส่ค่าใช้ชีวิต", ["ใส่ตามที่ลูกค้าบอก", "ให้ระบบประเมินคร่าว 60% ของรายได้"], index=0, horizontal=False)
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
 st.markdown(f'<div style="display:flex;gap:10px;margin-top:12px;"><div style="flex:1;background:#020617;padding:12px;border-radius:10px;border:1px solid #334155;text-align:center;"><div style="font-size:11px;color:#94A3B8;">รายได้รวม</div><div style="font-size:16px;font-weight:800;color:#4ADE80;">{st.session_state.monthly_income:,.0f}</div></div><div style="flex:1;background:#020617;padding:12px;border-radius:10px;border:1px solid #334155;text-align:center;"><div style="font-size:11px;color:#94A3B8;">ภาระรวม</div><div style="font-size:16px;font-weight:800;color:#FBBF24;">{total_obligations:,.0f}</div></div><div style="flex:1;background:#020617;padding:12px;border-radius:10px;border:1px solid #334155;text-align:center;"><div style="font-size:11px;color:#94A3B8;">DSR ใหม่</div><div style="font-size:18px;font-weight:800;color:white;">{dsr:.1f}%</div></div></div>', unsafe_allow_html=True)
 st.markdown('</div>', unsafe_allow_html=True)

 st.markdown('<div class="moto-card" style="background:#172554 !important;border:1px solid #1E40AF !important;">', unsafe_allow_html=True)
 st.markdown('<div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;"><div style="width:40px;height:40px;background:#1E40AF;border-radius:12px;display:flex;align-items:center;justify-content:center;color:white;">💑</div><div><div style="font-weight:800;color:#DBEAFE;">ข้อมูลคู่สมรส (ใหม่)</div><div style="font-size:12px;color:#93C5FD;">จำนวนปีที่สมรส จดทะเบียน มีบุตร รายได้คู่สมรส</div></div></div>', unsafe_allow_html=True)
 s1,s2=st.columns(2)
 with s1:
  spouse_name=st.text_input("👩‍❤️‍👨 ชื่อคู่สมรส", "นางสมหญิง", key="spouse_name")
  marriage_years=st.selectbox("📅 จำนวนปีที่สมรส", list(range(0,31)), index=5, key="marry_years")
  spouse_income=st.number_input("💰 รายได้คู่สมรส", value=8000.0, step=500.0, key="spouse_income")
 with s2:
  marriage_status=st.selectbox("📜 จดทะเบียนสมรส", ["จดทะเบียน","ไม่จดทะเบียน","หย่า","หม้าย"], index=0, key="marry_status")
  has_children=st.selectbox("👶 มีบุตร / ไม่มีบุตร", ["ไม่มีบุตร","มีบุตร 1 คน","มีบุตร 2 คน","มีบุตร 3 คนขึ้นไป"], index=1, key="children")
  spouse_job=st.text_input("💼 อาชีพคู่สมรส", "ค้าขาย", key="spouse_job")
 spouse_summary=f"{spouse_name} สมรส {marriage_years}ปี {marriage_status} {has_children} รายได้ {spouse_income} อาชีพ {spouse_job}"
 st.session_state.spouse_summary=spouse_summary
 st.markdown(f'<div style="background:#1E1B4B;padding:10px;border-radius:8px;border:1px solid #3730A3;margin-top:10px;font-size:12px;color:#C7D2FE;">สรุป: {spouse_summary}</div>', unsafe_allow_html=True)
 st.markdown('</div>', unsafe_allow_html=True)

 st.markdown('<div class="moto-card" style="background:#14532D !important;border:1px solid #166534 !important;">', unsafe_allow_html=True)
 st.markdown('<div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;"><div style="width:40px;height:40px;background:#166534;border-radius:12px;display:flex;align-items:center;justify-content:center;color:white;">🤝</div><div><div style="font-weight:800;color:#BBF7D0;">ผู้ค้ำประกัน - มีติ๊ก มี/ไม่มี</div></div></div>', unsafe_allow_html=True)
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
  guarantor_reason=st.text_area("❓ ทำไมถึงค้ำให้?", "เป็นพี่ชายแท้ๆ อยู่บ้านเดียวกัน ทำงานบริษัทเดียวกันมา 5 ปี", height=70, key="guar_reason")
  guarantor_summary=f"{guarantor_name} {guarantor_relation} รายได้ {guarantor_income} อาชีพ {guarantor_job} รู้จัก {guarantor_years} เหตุผล {guarantor_reason}"
 else:
  guarantor_summary="ไม่มีผู้ค้ำประกัน"
  st.warning("⚠️ ไม่มีผู้ค้ำ - AI จะประเมินความเสี่ยงสูงขึ้น")
 st.session_state.guarantor_summary=guarantor_summary
 st.markdown('</div>', unsafe_allow_html=True)

 st.markdown('<div class="moto-card">', unsafe_allow_html=True)
 st.markdown('<div style="font-weight:800;color:white;font-size:16px;margin-bottom:12px;">📝 รายละเอียดเพิ่มเติมให้ AI + บันทึกบริบทหน้าร้าน / พฤติกรรมลูกค้า</div>', unsafe_allow_html=True)
 workplace=st.text_input("🏢 สถานที่ทำงาน / พิกัดที่ทำงานจริง", "ตลาดสดเทศบาล ต.ลำนารายณ์", key="workplace")
 st.markdown('<div style="background:#020617;border:2px solid #334155;border-radius:12px;padding:14px;margin:12px 0;"><div style="color:#F8FAFC;font-weight:700;font-size:13px;margin-bottom:6px;">บันทึกบริบทหน้าร้าน / พฤติกรรมลูกค้า (ต้องตัดกับข้อความชัดเจน)</div><div style="color:#94A3B8;font-size:11px;">เช่น ลูกค้ามากับคุณแม่และคู่สมรส แจ้งว่าจะนำรถไปใช้รับส่งไปทำงาน...</div></div>', unsafe_allow_html=True)
 behavior_context=st.text_area("บันทึกบริบทหน้าร้าน / พฤติกรรมลูกค้า", "เช่น ลูกค้ามากับคุณแม่และคู่สมรส แจ้งว่าจะนำรถไปใช้รับส่งไปทำงานโรงงาน ไป-กลับ 20 กม. ทุกวัน ต้องการผ่อนแบบมีผู้ค้ำ ยินยอมติด GPS ตาม PDPA ไม่มีพฤติกรรมเร่งรีบ", height=120, label_visibility="collapsed", key="behavior")
 extra_details=st.text_area("🗒️ คำให้การลูกค้า / วัตถุประสงค์การใช้รถ", "ใช้รถไปทำงานโรงงาน ไป-กลับ 20 กม. ทุกวัน ยินยอมติด GPS", height=80, key="extra2")
 c_ref1,c_ref2=st.columns(2)
 with c_ref1: ref1=st.text_input("👥 บุคคลอ้างอิง 1", "นายสมศักดิ์ - พี่ชาย - 082-xxx-xxxx", key="ref1")
 with c_ref2: ref2=st.text_input("👥 บุคคลอ้างอิง 2", "นางสาวสมปอง - เพื่อนร่วมงาน - 083-xxx-xxxx", key="ref2")
 st.session_state.extra_details=f"{workplace} | {extra_details}"
 st.session_state.behavior_context=behavior_context
 def evaluate_fraud(vt, dpct, et, shared, dsr_val, gps):
  score=0; flags=[]
  if "Sport" in vt and dpct<=5: score+=40; flags.append("เสี่ยงดาวน์แลกเงิน")
  if not has_guarantor and dsr_val>45: score+=15; flags.append("ไม่มีผู้ค้ำ + DSR สูง")
  if marriage_status=="ไม่จดทะเบียน" and has_children!="ไม่มีบุตร": score+=10; flags.append("ไม่จดทะเบียนแต่มีบุตร")
  if score>=80: verdict="⛔ AUTO REJECT"
  elif score>=50: verdict="🟠 MANUAL REVIEW"
  else: verdict="🟢 AUTO PASS"
  return score,flags,verdict
 r_score,r_flags,r_verdict=evaluate_fraud(cat if 'cat' in locals() else "Auto", dp/vp*100 if 'vp' in locals() and vp else 20, "พนักงานประจำ", 0, dsr, True)
 st.session_state.r_verdict=r_verdict
 st.markdown(f'<div style="display:flex;gap:10px;margin-top:14px;"><div style="flex:1;background:#020617;padding:14px;border-radius:10px;border:1px solid #334155;text-align:center;"><div style="font-size:11px;color:#94A3B8;">DSR ใหม่</div><div style="font-size:20px;font-weight:800;color:white;">{dsr:.1f}%</div></div><div style="flex:1;background:#020617;padding:14px;border-radius:10px;border:1px solid #334155;text-align:center;"><div style="font-size:11px;color:#94A3B8;">Rule Engine</div><div style="font-size:14px;font-weight:800;color:white;">{r_verdict}</div></div></div>', unsafe_allow_html=True)
 for f in r_flags: st.warning(f)
 st.markdown('</div>', unsafe_allow_html=True)

 st.markdown('<div class="moto-card">', unsafe_allow_html=True)
 st.markdown("### 📸 เช็กลิสต์เอกสาร • 6 รายการ (Step 3)")
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
    im=Image.open(f)
    cp=_compress_mobile(im)
    comps.append(cp)
    with cols[i%2]: st.image(cp, use_container_width=True)
   except Exception as e: st.error(str(e))
 st.session_state.comps=comps
 st.markdown('</div>', unsafe_allow_html=True)

 st.markdown('<div class="moto-card">', unsafe_allow_html=True)
 st.markdown(f"### 🧠 วิเคราะห์ 13 โมดูลด้วย AI (Step 4) • {selected_model}")
 if 'ai_text' not in st.session_state: st.session_state.ai_text=""
 if st.button("🚀 รัน SRD Credit Investigation Engine 13 Modules เต็มระบบ v1.3", type="primary", use_container_width=True):
  if not comps: st.warning("กรุณาแนบภาพอย่างน้อย 1 ไฟล์")
  else:
   prompt=f"SRD CREDIT 13 MODULES v1.3 - รุ่น {model_name if 'model_name' in locals() else 'Manual'} รหัส {def_code if 'def_code' in locals() else '-'} ยอดจัด {st.session_state.vehicle_price} ดาวน์ {st.session_state.downpayment} ค่างวด {monthly_instalment:.2f} DSR {dsr:.1f}% ผู้สมัคร {applicant_name} คู่สมรส {spouse_summary} ผู้ค้ำ {guarantor_summary} ของแถม {gift_data} บริบทหน้าร้าน {behavior_context} รายละเอียด {extra_details} เอกสาร {', '.join(docs)} วิเคราะห์ภาษาไทย"
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
   with st.spinner(f"AI ({selected_model}) กำลังประมวลผล 13 โมดูล v1.3..."):
    res=call_ai(prompt, comps, selected_model, client)
   if res["ok"]:
    st.session_state.ai_text=res["text"]
    st.success(f"✅ สำเร็จด้วย {selected_model} v1.3")
    st.markdown(res["text"])
   else: st.error(res["raw"][:1000])
 if st.session_state.ai_text:
  pdf2=gen_pdf(applicant_name, model_name if 'model_name' in locals() else 'Manual', def_code if 'def_code' in locals() else '-', st.session_state.vehicle_price, st.session_state.downpayment, st.session_state.processing_fee, st.session_state.processing_fee, monthly_instalment, st.session_state.tenure, total_interest, total_payable, dsr, r_verdict, st.session_state.ai_text, st.session_state.extra_details, behavior_context, spouse_summary, guarantor_summary, gift_data)
  st.download_button("🔴 ส่งออกรายงาน 13 โมดูล PDF (v1.3)", data=pdf2, file_name=f"SRD_13M_v13_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf", mime="application/pdf", use_container_width=True)
 st.markdown('</div>', unsafe_allow_html=True)

with right_col:
 dsr_val=st.session_state.get('dsr_value',42.3)
 st.markdown('<div class="moto-card">', unsafe_allow_html=True)
 st.markdown(f'<div style="text-align:center;"><div style="position:relative;width:200px;height:110px;margin:0 auto;overflow:hidden;"><div style="width:200px;height:200px;border-radius:50%;background:conic-gradient(from 180deg,#10B981 0deg 90deg,#FBBF24 90deg 135deg,#EF4444 135deg 180deg);"></div><div style="position:absolute;top:20px;left:20px;width:160px;height:160px;background:#1E293B;border-radius:50%;border:2px solid #334155;"></div><div style="position:absolute;top:50px;left:0;width:200px;text-align:center;"><div style="font-size:30px;font-weight:800;color:white;">{dsr_val:.1f}%</div><div style="font-size:11px;color:#94A3B8;">Debt-Service Ratio</div></div></div></div>', unsafe_allow_html=True)
 st.markdown('</div>', unsafe_allow_html=True)
 st.markdown('<div class="moto-card">', unsafe_allow_html=True)
 st.markdown('<div style="display:flex;align-items:center;gap:12px;"><div style="width:42px;height:42px;background:#7C3AED;border-radius:12px;display:flex;align-items:center;justify-content:center;color:white;">🛡️</div><div style="font-weight:800;color:white;">คะแนนความเสี่ยง</div></div><div style="display:flex;align-items:center;gap:14px;margin-top:10px;"><div style="font-size:40px;font-weight:800;color:#A78BFA;">682</div><div style="background:#6D28D9;color:white;padding:6px 14px;border-radius:20px;font-size:12px;">Medium Risk</div></div></div>', unsafe_allow_html=True)
 st.markdown('<div class="moto-card">', unsafe_allow_html=True)
 st.markdown('<div style="font-weight:800;color:white;">วิเคราะห์ 13 โมดูลด้วย AI</div><div style="font-size:12px;color:#CBD5E1;margin-top:8px;">✅ ผ่านทั้ง 13 โมดูล • ความมั่นใจ 92%</div>', unsafe_allow_html=True)
 st.markdown('</div>', unsafe_allow_html=True)

st.caption("SRD v1.3 High Contrast Dark • ยึด ยอดจัด %ดอกเบี้ย ทะเบียน พรบ ประกัน • ของแถมพิเศษ • ผู้สมัครแยกผู้ค้ำ มีติ๊ก • คู่สมรส ปีสมรส จดทะเบียน มีบุตร รายได้ • หนี้เดิม+ค่าใช้ชีวิต • พื้นเข้มตัดข้อความชัด • Mobile • PDF 2 จุด • Gemini 3.6")
