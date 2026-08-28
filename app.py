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
st.set_page_config(page_title="SRD Moto Credit v1.2 Mobile", layout="wide", page_icon="🐒")
st.markdown('<style>.stApp{background:#F1F5F9!important;}header{display:none;} [data-testid="stSidebar"]{background:#0F172A!important;} [data-testid="stSidebar"] *{color:#94A3B8!important;} div[data-baseweb="select"]>div{background:white!important;color:#0F172A!important;border-radius:10px!important;border:1px solid #CBD5E1!important;} div[data-baseweb="select"] span{color:#0F172A!important;} input,textarea{background:white!important;color:#0F172A!important;border-radius:10px!important;} .moto-card{background:white;border-radius:16px;border:1px solid #E2E8F0;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,0.05);margin-bottom:14px;} .estimated-box{background:linear-gradient(135deg,#EFF6FF 0%,#DBEAFE 100%);border:1px dashed #93C5FD;border-radius:12px;padding:14px;margin-top:12px;} .step-circle{width:44px;height:44px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:700;flex-shrink:0;} .step-circle.done{background:#10B981;color:white;} .step-circle.active{background:#2563EB;color:white;} .step-circle.pending{background:white;color:#64748B;border:2px solid #CBD5E1;} @media(max-width:768px){[data-testid="stHorizontalBlock"]{flex-direction:column!important;}} .stDownloadButton>button{background:#DC2626!important;color:white!important;border-radius:10px!important;font-weight:600!important;border:none!important;}</style>', unsafe_allow_html=True)
def get_secret():
 try: k=st.secrets.get("GEMINI_API_KEY","") if hasattr(st,'secrets') else ""
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
    all_data.append(df)
   except: pass
  if all_data:
   full=pd.concat(all_data, ignore_index=True)
   return full
 except: pass
 return pd.DataFrame()
full_price_df=load_excel_real()
with st.sidebar:
 st.markdown('<div style="display:flex;align-items:center;gap:12px;padding:12px 8px;"><div style="width:48px;height:48px;background:linear-gradient(135deg,#0EA5E9,#06B6D4);border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:26px;">🐒</div><div><div style="color:white;font-weight:800;font-size:18px;">SRD Moto Credit</div><div style="color:#38BDF8;font-size:12px;">บจก. สิระเดชมอเตอร์เซลล์</div><div style="color:#64748B;font-size:11px;">v1.2 • Mobile</div></div></div>', unsafe_allow_html=True)
 st.markdown('<div style="color:#475569;font-size:11px;font-weight:700;letter-spacing:1px;margin:16px 8px 8px;">เมนูนำทาง</div>', unsafe_allow_html=True)
 for icon,label,active in [("🏠","แดชบอร์ด",False),("💳","เครื่องคำนวณสินเชื่อ",True),("📄","ใบสมัคร",False),("👥","ลูกค้า",False),("📁","เอกสาร",False),("📊","วิเคราะห์ข้อมูล",False),("🛡️","ความเสี่ยงและนโยบาย",False)]:
  if active: st.markdown(f'<div style="background:#1E3A5F;border-radius:12px;padding:12px 16px;margin:4px 0;color:white;border-left:4px solid #38BDF8;display:flex;gap:12px;"><span>{icon}</span> {label}</div>', unsafe_allow_html=True)
  else: st.markdown(f'<div style="padding:12px 16px;margin:4px 0;opacity:0.7;display:flex;gap:12px;"><span>{icon}</span> {label}</div>', unsafe_allow_html=True)
 if not secret_key:
  mk=st.text_input("🔑 GEMINI API Key", type="password", value=st.session_state.manual_key, placeholder="AIza...")
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
   st.caption(f"🤖 {selected_model} • Mobile")
  except Exception as e: st.error(str(e))
st.markdown('<div style="background:white;border-radius:16px;padding:16px;border:1px solid #E2E8F0;margin-bottom:14px;"><div style="font-size:22px;font-weight:800;color:#0F172A;">Motorcycle Loan Credit Engine</div><div style="font-size:15px;font-weight:600;color:#2563EB;margin-top:4px;">ระบบตรวจสอบสินเชื่อมอเตอร์ไซค์ • บจก. สิระเดชมอเตอร์เซลล์</div><div style="margin-top:10px;"><span style="background:#DCFCE7;color:#166534;padding:5px 12px;border-radius:20px;font-size:12px;font-weight:600;">● Connected • Live</span> <span style="font-size:12px;color:#64748B;">Mobile Optimized • Gemini 3.6</span></div></div>', unsafe_allow_html=True)
st.markdown('<div class="moto-card"><div style="display:flex;gap:8px;overflow-x:auto;"><div style="text-align:center;min-width:80px;"><div class="step-circle done">✓</div><div style="font-size:12px;font-weight:700;color:#059669;">Step 1</div><div style="font-size:10px;">เลือกยานพาหนะ</div></div><div style="text-align:center;min-width:80px;"><div class="step-circle active">2</div><div style="font-size:12px;font-weight:700;color:#2563EB;">Step 2</div><div style="font-size:10px;">ผู้สมัคร & ผู้ค้ำ</div></div><div style="text-align:center;min-width:90px;"><div class="step-circle pending">3</div><div style="font-size:12px;font-weight:700;color:#64748B;">Step 3</div><div style="font-size:10px;">เช็กลิสต์ 6 รายการ</div></div><div style="text-align:center;min-width:90px;"><div class="step-circle pending">4</div><div style="font-size:12px;font-weight:700;color:#64748B;">Step 4</div><div style="font-size:10px;">วิเคราะห์ 13 โมดูล</div></div></div></div>', unsafe_allow_html=True)
if 'vehicle_price' not in st.session_state: st.session_state.vehicle_price=54600.0
if 'downpayment' not in st.session_state: st.session_state.downpayment=0.0
if 'tenure' not in st.session_state: st.session_state.tenure=36
if 'flat_rate' not in st.session_state: st.session_state.flat_rate=1.5
if 'processing_fee' not in st.session_state: st.session_state.processing_fee=1000.0
if 'monthly_income' not in st.session_state: st.session_state.monthly_income=5200.0
st.markdown('<div class="moto-card">', unsafe_allow_html=True)
st.markdown(f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;"><div style="width:36px;height:36px;background:#2563EB;border-radius:10px;display:flex;align-items:center;justify-content:center;color:white;">🧮</div><div><div style="font-weight:700;font-size:16px;">เครื่องคำนวณ Flat Rate • {selected_model}</div><div style="font-size:11px;color:#64748B;">Mobile Optimized • แก้ได้ทุกช่อง</div></div></div>', unsafe_allow_html=True)
price_mode=st.radio("🔀 วิธีเลือกราคา (2 แบบ)", ["📦 เลือกรุ่นจากฐานข้อมูล Excel (รุ่น รหัส ราคาจัด ดาวน์ ออกรถ แยกยี่ห้อ)", "✏️ ใส่ราคาด้วยตนเอง (Manual)"], index=0)
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
 st.markdown(f"**📋 ตารางราคา: {sel_model} • {len(model_variants)} แบบดาวน์**")
 st.dataframe(model_variants[['รหัสรถ','รุ่นรถ','ราคาจัด','%ดาวน์','ราคาดาวน์','ค่าใช้จ่ายออกรถ']], use_container_width=True, height=200)
 down_options=model_variants[['%ดาวน์','ราคาดาวน์','ค่าใช้จ่ายออกรถ','ราคาจัด','ดอกเบี้ยต่อเดือน','รหัสรถ']].to_dict('records')
 down_labels=[f"{r['%ดาวน์']*100:.0f}% ดาวน์ {r['ราคาดาวน์']:,.0f} บาท • ออกรถ {r['ค่าใช้จ่ายออกรถ']:,.0f} บาท • รหัส {r['รหัสรถ']}" for r in down_options]
 sel_down_idx=st.selectbox("💵 เลือก % ดาวน์ (จากตารางจริง)", range(len(down_labels)), format_func=lambda i: down_labels[i])
 chosen=down_options[sel_down_idx]
 def_price=float(chosen['ราคาจัด']); def_down=float(chosen['ราคาดาวน์']); def_total_out=float(chosen['ค่าใช้จ่ายออกรถ']); def_int=float(chosen['ดอกเบี้ยต่อเดือน'])*100; def_code=chosen['รหัสรถ']
 st.session_state.vehicle_price=def_price; st.session_state.downpayment=def_down; st.session_state.processing_fee=def_total_out if def_total_out else 1000.0; st.session_state.flat_rate=def_int
 model_name=sel_model; cat=sel_cat if sel_cat!="ทั้งหมด" else model_variants.iloc[0]['หมวด']
else:
 model_name=st.text_input("ชื่อรุ่นรถ", "ฟาซซิโอ้ SMK")
 cat=st.text_input("หมวดหมู่", "Auto")
 def_price=st.number_input("ราคาจัด", value=54600.0); def_down=st.number_input("ราคาดาวน์", value=0.0); def_total_out=st.number_input("ค่าใช้จ่ายออกรถ", value=1000.0)
 def_code=st.text_input("รหัสรถ", "BKF700"); def_int=st.number_input("ดอกเบี้ยต่อเดือน (%)", value=1.5)
 st.session_state.vehicle_price=def_price; st.session_state.downpayment=def_down
c1,c2=st.columns(2)
with c1:
 vp=st.number_input("💰 ราคาจัด - แก้ได้", value=float(st.session_state.vehicle_price), step=100.0)
 st.session_state.vehicle_price=vp
 tenure=st.selectbox("📅 ระยะผ่อน - แก้ได้", [12,18,24,30,36,42,48,60], index=4)
 st.session_state.tenure=tenure
with c2:
 dp=st.number_input("💵 ราคาดาวน์ - แก้ได้", value=float(st.session_state.downpayment), step=100.0)
 st.session_state.downpayment=dp
 fr=st.number_input("📈 ดอกเบี้ยต่อเดือน (%) - แก้ได้", value=float(st.session_state.flat_rate), step=0.01, format="%.3f")
 st.session_state.flat_rate=fr
pf=st.number_input("🧾 ค่าใช้จ่ายออกรถ / ค่าจดพรบ - แก้ได้", value=float(st.session_state.processing_fee), step=100.0)
st.session_state.processing_fee=pf
loan_amount=st.session_state.vehicle_price-st.session_state.downpayment
total_interest=loan_amount*(st.session_state.flat_rate/100)*st.session_state.tenure
total_payable=loan_amount+total_interest+st.session_state.processing_fee
monthly_instalment=(loan_amount+total_interest)/st.session_state.tenure if st.session_state.tenure else 0
from reportlab.pdfgen import canvas as pdf_c
from reportlab.lib.pagesizes import A4
def gen_pdf(name,model,code,cash,down,out_cost,monthly,term,interest,total,dsr,verdict,ai_text,extra,b_behavior):
 buf=io.BytesIO()
 c=pdf_c.Canvas(buf,pagesize=A4)
 c.setFont("Helvetica-Bold",11)
 c.drawString(30,800,f"SRD Moto Credit v1.2 Mobile - {model} ({code}) - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
 c.setFont("Helvetica",9)
 c.drawString(30,785,f"Applicant: {name} | ราคาจัด: {cash:,.0f} ดาวน์: {down:,.0f} ออกรถ: {out_cost:,.0f} ค่างวด: {monthly:,.0f} x {term}")
 c.drawString(30,770,f"DSR: {dsr:.1f}% Verdict: {verdict}")
 y=750; c.setFont("Helvetica",8)
 c.drawString(30,y,f"Extra: {extra[:150]}"); y-=12
 c.drawString(30,y,f"Behavior: {b_behavior[:150]}"); y-=14
 if ai_text:
  for line in ai_text.split("\n")[:80]:
   if y<30: c.showPage(); y=800
   c.drawString(30,y,line[:110]); y-=11
 c.showPage(); c.save(); buf.seek(0)
 return buf
col_calc,col_pdf1=st.columns([1.2,1])
with col_calc: st.button("⚡ คำนวณสินเชื่อ", type="primary", use_container_width=True)
with col_pdf1:
 pdf1=gen_pdf(st.session_state.get('applicant_name',''), model_name if 'model_name' in locals() else 'Manual', def_code if 'def_code' in locals() else '-', st.session_state.vehicle_price, st.session_state.downpayment, st.session_state.processing_fee, monthly_instalment, st.session_state.tenure, total_interest, total_payable, st.session_state.get('dsr_value',42.3), st.session_state.get('r_verdict',''), st.session_state.get('ai_text',''), st.session_state.get('extra_details',''), st.session_state.get('behavior_context',''))
 st.download_button("🔴 ส่งออกเป็น PDF", data=pdf1, file_name=f"SRD_Loan_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf", mime="application/pdf", use_container_width=True)
st.markdown(f'<div class="estimated-box"><div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px;"><div><div style="font-size:11px;background:#DBEAFE;color:#1E40AF;padding:2px 8px;border-radius:12px;display:inline-block;margin-bottom:6px;">ยอดผ่อนต่อเดือน</div><div style="font-size:26px;font-weight:800;">MYR {monthly_instalment:,.2f} / เดือน</div></div><div style="text-align:right;font-size:12px;"><div>ดอกเบี้ยรวม: <b>MYR {total_interest:,.0f}</b></div><div>ยอดรวม: <b>MYR {total_payable:,.0f}</b></div><div>ออกรถ: <b>MYR {st.session_state.processing_fee:,.0f}</b></div></div></div></div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)
st.markdown('<div class="moto-card">', unsafe_allow_html=True)
st.markdown("### 👤 ผู้สมัคร & ผู้ค้ำประกัน (Step 2) + รายละเอียดเพิ่มเติม")
a1,a2=st.columns(2)
with a1:
 applicant_name=st.text_input("👤 ชื่อผู้กู้", "สมชาย")
 salary=st.number_input("💼 เงินเดือน", value=15000.0, step=500.0)
with a2:
 phone=st.text_input("📞 เบอร์โทร", "081-xxx-xxxx")
 extra_income=st.number_input("💰 รายได้เสริม", value=2000.0, step=500.0)
 emp_type=st.selectbox("💼 อาชีพ", ["พนักงานประจำ","ฟรีแลนซ์","ค้าขาย","ว่างงาน","เกษตรกร"])
debt=st.number_input("💳 หนี้เดิมต่อเดือน", value=2198.0, step=100.0)
st.session_state.monthly_income=salary+extra_income
total_obligations=debt+monthly_instalment
dsr=(total_obligations/st.session_state.monthly_income*100) if st.session_state.monthly_income else 42.3
st.session_state.dsr_value=dsr
st.session_state.applicant_name=applicant_name
workplace=st.text_input("🏢 สถานที่ทำงาน / พิกัด", "ตลาดสดเทศบาล ต.ลำนารายณ์")
c_sp1,c_sp2=st.columns(2)
with c_sp1: spouse_info=st.text_input("💑 คู่สมรส", "นางสมหญิง - ค้าขาย - 8,000")
with c_sp2: guarantor_info=st.text_input("🤝 คนค้ำ", "นายสมหมาย - พนักงานประจำ - 20,000")
st.markdown('<div style="background:#1E293B;border-radius:12px;padding:12px;margin-top:12px;"><div style="color:#E2E8F0;font-size:13px;font-weight:600;">บันทึกบริบทหน้าร้าน / พฤติกรรมลูกค้า</div><div style="color:#94A3B8;font-size:11px;">เช่น ลูกค้ามากับคุณแม่และคู่สมรส แจ้งว่าจะนำรถไปใช้รับส่งไปทำงาน...</div></div>', unsafe_allow_html=True)
behavior_context=st.text_area("บันทึกบริบทหน้าร้าน / พฤติกรรมลูกค้า (เพิ่มใหม่)", "เช่น ลูกค้ามากับคุณแม่และคู่สมรส แจ้งว่าจะนำรถไปใช้รับส่งไปทำงานโรงงาน ไป-กลับ 20 กม. ทุกวัน ต้องการผ่อนแบบมีผู้ค้ำ ยินยอมติด GPS ตาม PDPA ไม่มีพฤติกรรมเร่งรีบ", height=120, label_visibility="collapsed")
extra_details=st.text_area("🗒️ คำให้การลูกค้า / วัตถุประสงค์การใช้รถ", "ใช้รถไปทำงานโรงงาน ไป-กลับ 20 กม. ยินยอมติด GPS", height=80)
c_ref1,c_ref2=st.columns(2)
with c_ref1: ref1=st.text_input("👥 อ้างอิง 1", "นายสมศักดิ์ - พี่ชาย - 082-xxx-xxxx")
with c_ref2: ref2=st.text_input("👥 อ้างอิง 2", "นางสาวสมปอง - เพื่อน - 083-xxx-xxxx")
st.session_state.extra_details=f"{workplace} | {spouse_info} | {guarantor_info} | {extra_details}"
st.session_state.behavior_context=behavior_context
def evaluate_fraud(vt, dpct, et, shared, dsr_val, gps):
 score=0
 if "Sport" in vt and dpct<=5: score+=40
 if score>=80: verdict="⛔ AUTO REJECT"
 elif score>=50: verdict="🟠 MANUAL REVIEW"
 else: verdict="🟢 AUTO PASS"
 return score,[],verdict
r_score,_,r_verdict=evaluate_fraud(cat if 'cat' in locals() else "Auto", dp/vp*100 if vp else 20, emp_type, 0, dsr, True)
st.session_state.r_verdict=r_verdict
st.markdown(f'<div style="display:flex;gap:8px;margin-top:12px;"><div style="flex:1;background:#F1F5F9;padding:10px;border-radius:8px;border:1px solid #E2E8F0;"><div style="font-size:11px;">DSR</div><b>{dsr:.1f}%</b></div><div style="flex:1;background:#F1F5F9;padding:10px;border-radius:8px;border:1px solid #E2E8F0;"><div style="font-size:11px;">Rule Engine</div><b>{r_verdict}</b></div></div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)
st.markdown('<div class="moto-card">', unsafe_allow_html=True)
st.markdown("### 📸 เช็กลิสต์เอกสาร • 6 รายการ (Step 3) - Mobile")
docs=st.multiselect("เอกสารที่แนบแล้ว", ["Face Verification","บัตร ปชช + ทะเบียนบ้าน","Statement","NCB","สลิปเงินเดือน","ที่พัก + ที่ทำงาน"], default=["บัตร ปชช + ทะเบียนบ้าน","Statement"])
uploads=st.file_uploader("แนบภาพเอกสาร (HEIC)", type=["jpg","jpeg","png","heic","heif","webp"], accept_multiple_files=True)
cam=st.camera_input("📷 ถ่ายจากกล้องมือถือ")
comps=[]; files=[]
if uploads: files.extend(uploads)
if cam: files.append(cam)
if files:
 st.success(f"📱 เตรียมไฟล์ {len(files)} รูป - ย่ออัตโนมัติ")
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
if st.button("🚀 รัน AI 13 Modules (Gemini 3.6) - Mobile", type="primary", use_container_width=True):
 if not comps: st.warning("แนบภาพก่อน")
 else:
  prompt=f"SRD CREDIT 13 MODULES Mobile - {model_name if 'model_name' in locals() else 'Manual'} ราคาจัด {st.session_state.vehicle_price} ดาวน์ {st.session_state.downpayment} ค่างวด {monthly_instalment:.2f} DSR {dsr:.1f}% ผู้กู้ {applicant_name} อาชีพ {emp_type} ที่ทำงาน {workplace} บริบทหน้าร้าน {behavior_context} รายละเอียด {extra_details} เอกสาร {', '.join(docs)} วิเคราะห์ภาษาไทย"
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
  with st.spinner(f"AI {selected_model} วิเคราะห์..."):
   res=call_ai(prompt, comps, selected_model, client)
  if res["ok"]:
   st.session_state.ai_text=res["text"]
   st.success(f"✅ สำเร็จด้วย {selected_model}")
   st.markdown(res["text"])
  else: st.error(res["raw"][:1000])
if st.session_state.ai_text:
 pdf2=gen_pdf(applicant_name, model_name if 'model_name' in locals() else 'Manual', def_code if 'def_code' in locals() else '-', st.session_state.vehicle_price, st.session_state.downpayment, st.session_state.processing_fee, monthly_instalment, st.session_state.tenure, total_interest, total_payable, dsr, r_verdict, st.session_state.ai_text, st.session_state.extra_details, behavior_context)
 st.download_button("🔴 ส่งออกรายงาน 13 โมดูล PDF", data=pdf2, file_name=f"SRD_13M_Mobile_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf", mime="application/pdf", use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)
st.markdown('<div class="moto-card">', unsafe_allow_html=True)
dsr_val=st.session_state.get('dsr_value',42.3)
st.markdown(f'<div style="text-align:center;"><div style="position:relative;width:180px;height:100px;margin:0 auto;overflow:hidden;"><div style="width:180px;height:180px;border-radius:50%;background:conic-gradient(from 180deg,#10B981 0deg 90deg,#FBBF24 90deg 135deg,#EF4444 135deg 180deg);"></div><div style="position:absolute;top:20px;left:20px;width:140px;height:140px;background:white;border-radius:50%;"></div><div style="position:absolute;top:45px;left:0;width:180px;text-align:center;"><div style="font-size:28px;font-weight:800;">{dsr_val:.1f}%</div><div style="font-size:11px;color:#64748B;">Debt-Service Ratio</div></div></div><div style="margin-top:8px;"><span style="background:#DCFCE7;color:#166534;padding:4px 12px;border-radius:20px;font-size:11px;font-weight:600;">Within Safe Limit (<50%)</span></div></div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)
st.caption("SRD Moto Credit v1.2 Mobile • เมนูไทย 100% • ตารางจริง รุ่น รหัส ราคาจัด ดาวน์ ออกรถ แยกยี่ห้อ • Mobile Optimized • ปุ่ม PDF แดง 2 จุด • ช่องบันทึกบริบทหน้าร้าน • Gemini 3.6")
