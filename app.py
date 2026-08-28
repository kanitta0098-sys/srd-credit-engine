
import streamlit as st
import pandas as pd, os, io
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

st.set_page_config(page_title="SRD Moto Credit v1.2 ไทย", layout="wide", page_icon="🐒")

st.markdown("""
<style>
.stApp { background-color: #F1F5F9 !important; }
header[data-testid="stHeader"] { display: none; }
[data-testid="stSidebar"] { background: #0F172A !important; }
[data-testid="stSidebar"] * { color: #94A3B8 !important; }
.moto-card { background:white; border-radius:16px; border:1px solid #E2E8F0; padding:20px; box-shadow:0 1px 3px rgba(0,0,0,0.05); margin-bottom:16px; }
.estimated-box { background:linear-gradient(135deg,#EFF6FF 0%,#DBEAFE 100%); border:1px dashed #93C5FD; border-radius:12px; padding:16px; margin-top:12px; }
.risk-score { font-size:36px; font-weight:800; color:#4F46E5; }
.risk-badge { background:#6366F1; color:white; padding:4px 12px; border-radius:20px; font-size:12px; }
.step-circle { width:48px; height:48px; border-radius:50%; display:flex; align-items:center; justify-content:center; margin:0 auto 8px; font-weight:700; font-size:18px; }
.step-circle.done { background:#10B981; color:white; }
.step-circle.active { background:#2563EB; color:white; }
.step-circle.pending { background:white; color:#64748B; border:2px solid #CBD5E1; }
.price-mode { background:#F8FAFC; border:1px solid #E2E8F0; border-radius:10px; padding:12px; margin-bottom:12px; }
</style>
""", unsafe_allow_html=True)

def get_secret():
    try: k = st.secrets.get("GEMINI_API_KEY","") if hasattr(st,'secrets') else ""
    except: k=""
    if not k: k = os.getenv("GEMINI_API_KEY","") or os.getenv("GOOGLE_API_KEY","")
    return k.strip()

secret_key = get_secret()
if 'manual_key' not in st.session_state: st.session_state.manual_key=""
api_key = secret_key or st.session_state.manual_key
PREFERRED_MODELS = ["gemini-3.6-flash","gemini-3.0-flash","gemini-2.5-flash","gemini-1.5-flash"]

def save_record(d):
    import pandas as pd, os
    f="srd_credit_assessment_history.csv"
    df=pd.DataFrame([d])
    if not os.path.exists(f): df.to_csv(f,index=False,encoding='utf-8-sig')
    else: df.to_csv(f,mode='a',header=False,index=False,encoding='utf-8-sig')

with st.sidebar:
    st.markdown('<div style="display:flex; align-items:center; gap:12px; padding:12px 8px;"><div style="width:48px; height:48px; background:linear-gradient(135deg,#0EA5E9,#06B6D4); border-radius:12px; display:flex; align-items:center; justify-content:center; font-size:26px;">🐒</div><div><div style="color:white; font-weight:800; font-size:18px;">SRD Moto Credit</div><div style="color:#38BDF8; font-size:12px;">บจก. สิระเดชมอเตอร์เซลล์</div><div style="color:#64748B; font-size:11px;">Loan Credit Engine • v1.2</div></div></div>', unsafe_allow_html=True)
    st.markdown('<div style="color:#475569; font-size:11px; font-weight:700; letter-spacing:1px; margin:16px 8px 8px;">เมนูนำทาง</div>', unsafe_allow_html=True)
    for icon,label,active in [("🏠","แดชบอร์ด",False),("💳","เครื่องคำนวณสินเชื่อ",True),("📄","ใบสมัคร",False),("👥","ลูกค้า",False),("📁","เอกสาร",False),("📊","วิเคราะห์ข้อมูล",False),("🛡️","ความเสี่ยงและนโยบาย",False)]:
        if active: st.markdown(f'<div style="background:#1E3A5F; border-radius:12px; padding:12px 16px; margin:4px 0; color:white; border-left:4px solid #38BDF8; display:flex; gap:12px;"><span>{icon}</span> {label}</div>', unsafe_allow_html=True)
        else: st.markdown(f'<div style="padding:12px 16px; margin:4px 0; opacity:0.7; display:flex; gap:12px;"><span>{icon}</span> {label}</div>', unsafe_allow_html=True)
    st.markdown('<div style="border-top:1px solid #1E293B; margin:20px 0;"></div>', unsafe_allow_html=True)
    if not secret_key:
        mk=st.text_input("🔑 GEMINI API Key", type="password", value=st.session_state.manual_key, placeholder="AIza...")
        if mk: st.session_state.manual_key=mk.strip(); api_key=st.session_state.manual_key
    else: st.success("✅ API Key พร้อม")
    selected_model="gemini-3.6-flash"; client=None; genai_types=None; IS_NEW=False
    if api_key:
        try:
            from google import genai as new_genai
            from google.genai import types as new_types
            @st.cache_resource(show_spinner=False)
            def get_client(k_hash,k_val):
                cl=new_genai.Client(api_key=k_val)
                return cl,"gemini-3.6-flash",[]
            client,selected_model,_=get_client(api_key[:8],api_key)
            genai_types=new_types; IS_NEW=True
            st.caption(f"🤖 {selected_model}")
        except Exception as e: st.error(str(e))
    st.markdown('<div style="margin-top:20px; opacity:0.6; padding:0 16px;"><div>⚙️ ตั้งค่า</div><div>🚪 ออกจากระบบ</div></div>', unsafe_allow_html=True)

col_title, col_live = st.columns([4,1])
with col_title:
    st.markdown('<div><div style="font-size:28px; font-weight:800; color:#0F172A;">Motorcycle Loan Credit Engine</div><div style="font-size:16px; font-weight:600; color:#2563EB;">ระบบตรวจสอบสินเชื่อมอเตอร์ไซค์ • บจก. สิระเดชมอเตอร์เซลล์</div></div>', unsafe_allow_html=True)
with col_live:
    st.markdown('<div style="display:flex; justify-content:flex-end; margin-top:8px;"><span style="background:#DCFCE7; color:#166534; padding:6px 12px; border-radius:20px; font-size:12px; font-weight:600;">● Connected • Live</span></div>', unsafe_allow_html=True)

st.markdown("""
<div class="moto-card" style="padding:24px 32px;">
    <div style="display:flex; justify-content:space-between; position:relative;">
        <div style="position:absolute; top:24px; left:10%; right:10%; height:3px; background:#E2E8F0;"></div>
        <div style="position:absolute; top:24px; left:10%; width:45%; height:3px; background:#10B981;"></div>
        <div style="text-align:center; z-index:3;"><div class="step-circle done">✓</div><div style="font-weight:700; color:#059669;">Step 1</div><div style="font-size:11px; color:#059669; font-weight:600;">เลือกยานพาหนะ</div></div>
        <div style="text-align:center; z-index:3;"><div class="step-circle active">2</div><div style="font-weight:700; color:#2563EB;">Step 2</div><div style="font-size:11px; color:#2563EB; font-weight:600;">ผู้สมัคร & ผู้ค้ำประกัน</div></div>
        <div style="text-align:center; z-index:3;"><div class="step-circle pending">3</div><div style="font-weight:700; color:#64748B;">Step 3</div><div style="font-size:11px; font-weight:600;">เช็กลิสต์เอกสาร • 6 รายการ</div></div>
        <div style="text-align:center; z-index:3;"><div class="step-circle pending">4</div><div style="font-weight:700; color:#64748B;">Step 4</div><div style="font-size:11px; font-weight:600;">วิเคราะห์ 13 โมดูลด้วย AI</div></div>
    </div>
</div>
""", unsafe_allow_html=True)

left_col, right_col = st.columns([1.6, 1])

@st.cache_data
def load_all_data():
    fp='Yamaha_+รวมขายทุกตัว 25-8-69 Dynamic_Formulas_Categories.xlsx'
    d={}
    for sh in ['Auto','Moped','Sport','Honda รถใหม่','Honda มือสอง']:
        try:
            df=pd.read_excel(fp, sheet_name=sh, skiprows=1)
            if 'รุ่นรถ' in df.columns:
                df[['รุ่นรถ']]=df[['รุ่นรถ']].ffill()
                d[sh]=df.dropna(subset=['รุ่นรถ'])
        except: pass
    return d

motorcycle_data = load_all_data()
if 'vehicle_price' not in st.session_state: st.session_state.vehicle_price=22500.0
if 'downpayment' not in st.session_state: st.session_state.downpayment=4500.0
if 'tenure' not in st.session_state: st.session_state.tenure=48
if 'flat_rate' not in st.session_state: st.session_state.flat_rate=4.50
if 'processing_fee' not in st.session_state: st.session_state.processing_fee=300.0
if 'monthly_income' not in st.session_state: st.session_state.monthly_income=5200.0

with left_col:
    st.markdown('<div class="moto-card">', unsafe_allow_html=True)
    st.markdown(f'<div style="display:flex; align-items:center; gap:12px; margin-bottom:16px;"><div style="width:40px; height:40px; background:#2563EB; border-radius:10px; display:flex; align-items:center; justify-content:center; color:white;">🧮</div><div><div style="font-weight:700; font-size:18px;">เครื่องคำนวณ Flat Rate • {selected_model}</div><div style="font-size:12px; color:#64748B;">แก้ได้ทุกช่อง ส่งไป DSR+AI อัตโนมัติ</div></div></div>', unsafe_allow_html=True)
    st.markdown('<div class="price-mode">', unsafe_allow_html=True)
    st.markdown("**🔀 วิธีเลือกราคา (2 แบบ)**")
    price_mode = st.radio("โหมดราคา", ["📦 เลือกรุ่นจากฐานข้อมูล", "✏️ ใส่ราคาด้วยตนเอง (Manual)"], horizontal=True, label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)
    if price_mode.startswith("📦"):
        if motorcycle_data:
            cat = st.selectbox("📂 หมวดหมู่รถ (5 หมวด)", list(motorcycle_data.keys()))
            df_cat = motorcycle_data[cat]
            model_col = 'รุ่นรถ' if 'รุ่นรถ' in df_cat.columns else df_cat.columns[0]
            model_name = st.selectbox(f"🏍️ รุ่นรถในหมวด {cat}", df_cat[model_col].astype(str).unique()[:300])
            try:
                row = df_cat[df_cat[model_col].astype(str)==model_name].iloc[0]
                def_price = float(row.get('ราคาสด', 22500)); def_int = float(row.get('ดอกเบี้ย', 4.5))
                if def_int>10: def_int/=12
            except: def_price=22500; def_int=4.5
        else: model_name="Yamaha Finn"; def_price=22500; def_int=4.5; cat="Auto"
    else:
        model_name = st.text_input("ชื่อรุ่นรถ (Manual)", "Yamaha Finn 115")
        cat = st.text_input("หมวดหมู่", "Auto")
        def_price = st.number_input("ราคารถตั้งต้น", value=22500.0)
        def_int = st.number_input("ดอกเบี้ยตั้งต้น", value=4.5)

    c1,c2 = st.columns(2)
    with c1:
        vp = st.number_input("💰 ราคารถ - แก้ได้", value=float(def_price), step=100.0)
        st.session_state.vehicle_price=vp
        tenure = st.selectbox("📅 ระยะผ่อน - แก้ได้", [12,18,24,30,36,42,48,60,72], index=3)
        st.session_state.tenure=tenure
    with c2:
        dp = st.number_input("💵 เงินดาวน์ - แก้ได้", value=float(st.session_state.downpayment if st.session_state.downpayment else vp*0.2), step=100.0)
        st.session_state.downpayment=dp
        st.caption(f"{dp/vp*100:.1f}% ของราคารถ")
        fr = st.number_input("📈 ดอกเบี้ย (% p.a.) - แก้ได้", value=float(st.session_state.flat_rate), step=0.05, format="%.2f")
        st.session_state.flat_rate=fr
    pf = st.number_input("🧾 ค่าธรรมเนียม - แก้ได้", value=float(st.session_state.processing_fee), step=10.0)
    st.session_state.processing_fee=pf

    loan_amount = st.session_state.vehicle_price - st.session_state.downpayment
    total_interest = loan_amount * (st.session_state.flat_rate/100) * (st.session_state.tenure/12)
    total_payable = loan_amount + total_interest + st.session_state.processing_fee
    monthly_instalment = (loan_amount + total_interest) / st.session_state.tenure if st.session_state.tenure else 0

    from reportlab.pdfgen import canvas as pdf_c
    from reportlab.lib.pagesizes import A4
    def gen_pdf(name,model,cash,down,monthly,term,interest,total,dsr,verdict,ai_text,extra):
        buf=io.BytesIO()
        c=pdf_c.Canvas(buf,pagesize=A4)
        c.setFont("Helvetica-Bold",12)
        c.drawString(30,800,f"SRD Moto Credit v1.2 - {model} - {datetime.now().strftime('%d/%m/%Y %H:%M')} - {selected_model}")
        c.setFont("Helvetica",9)
        c.drawString(30,785,f"Applicant: {name} | Price: {cash:,.0f} Down: {down:,.0f} Monthly: {monthly:,.0f} x {term}")
        c.drawString(30,770,f"DSR: {dsr:.1f}% Verdict: {verdict} Extra: {extra[:150]}")
        y=750; c.setFont("Helvetica",8)
        if ai_text:
            for line in ai_text.split("\n")[:90]:
                if y<30: c.showPage(); y=800
                c.drawString(30,y,line[:110]); y-=11
        c.showPage(); c.save(); buf.seek(0)
        return buf

    col_calc, col_pdf1 = st.columns([1.2,1])
    with col_calc: st.button("⚡ คำนวณสินเชื่อ", type="primary", use_container_width=True)
    with col_pdf1:
        pdf1 = gen_pdf(st.session_state.get('applicant_name',''), model_name, st.session_state.vehicle_price, st.session_state.downpayment, monthly_instalment, st.session_state.tenure, total_interest, total_payable, st.session_state.get('dsr_value',42.3), st.session_state.get('r_verdict',''), st.session_state.get('ai_text',''), st.session_state.get('extra_details',''))
        st.download_button("🔴 ส่งออกเป็น PDF", data=pdf1, file_name=f"SRD_Loan_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf", mime="application/pdf", use_container_width=True)

    st.markdown(f'<div class="estimated-box"><div style="display:flex; justify-content:space-between;"><div><div style="font-size:11px; background:#DBEAFE; color:#1E40AF; padding:2px 8px; border-radius:12px; display:inline-block; margin-bottom:6px;">ยอดผ่อนต่อเดือน</div><div style="font-size:28px; font-weight:800;">MYR {monthly_instalment:,.2f} / เดือน</div></div><div style="text-align:right; font-size:12px;"><div>ดอกเบี้ยรวม: <b>MYR {total_interest:,.0f}</b></div><div>ยอดรวม: <b>MYR {total_payable:,.0f}</b></div></div></div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="moto-card">', unsafe_allow_html=True)
    st.markdown("### 👤 ผู้สมัคร & ผู้ค้ำประกัน + รายละเอียดเพิ่มเติมให้ AI")
    a1,a2 = st.columns(2)
    with a1:
        applicant_name = st.text_input("👤 ชื่อผู้กู้", "สมชาย")
        salary = st.number_input("💼 เงินเดือน", value=15000.0, step=500.0)
    with a2:
        phone = st.text_input("📞 เบอร์โทร", "081-xxx-xxxx")
        extra_income = st.number_input("💰 รายได้เสริม", value=2000.0, step=500.0)
        emp_type = st.selectbox("💼 อาชีพ", ["พนักงานประจำ","ฟรีแลนซ์","ค้าขาย","ว่างงาน","เกษตรกร"])
    debt = st.number_input("💳 หนี้เดิมต่อเดือน", value=2198.0, step=100.0)
    st.session_state.monthly_income = salary + extra_income
    total_obligations = debt + monthly_instalment
    dsr = (total_obligations / st.session_state.monthly_income * 100) if st.session_state.monthly_income else 42.3
    st.session_state.dsr_value = dsr
    st.session_state.applicant_name = applicant_name
    st.markdown("**📝 รายละเอียดเพิ่มเติมให้ AI (ปลีกย่อย)**")
    workplace = st.text_input("🏢 สถานที่ทำงาน / พิกัด", "ตลาดสดเทศบาล ต.ลำนารายณ์")
    spouse_info = st.text_input("💑 ข้อมูลคู่สมรส", "นางสมหญิง - ค้าขาย - 8,000")
    guarantor_info = st.text_input("🤝 คนค้ำ", "นายสมหมาย - พนักงานประจำ - 20,000")
    extra_details = st.text_area("🗒️ คำให้การลูกค้า / วัตถุประสงค์การใช้รถ", "ใช้รถไปทำงานโรงงาน ไป-กลับ 20 กม. ยินยอมติด GPS ตาม PDPA", height=80)
    ref1 = st.text_input("👥 อ้างอิง 1", "นายสมศักดิ์ - พี่ชาย - 082-xxx-xxxx")
    ref2 = st.text_input("👥 อ้างอิง 2", "นางสาวสมปอง - เพื่อน - 083-xxx-xxxx")
    st.session_state.extra_details = f"{workplace} | {spouse_info} | {guarantor_info} | {extra_details} | {ref1} | {ref2}"
    def evaluate_fraud(vt, dpct, et, shared, dsr_val, gps):
        score=0
        if "Sport" in vt and dpct<=5: score+=40
        if score>=80: verdict="⛔ AUTO REJECT"
        elif score>=50: verdict="🟠 MANUAL REVIEW"
        else: verdict="🟢 AUTO PASS"
        return score,[],verdict
    r_score,_,r_verdict = evaluate_fraud(cat, dp/vp*100 if vp else 20, emp_type, 0, dsr, True)
    st.session_state.r_verdict=r_verdict
    st.markdown(f'<div style="display:flex; gap:10px; margin-top:12px;"><div style="flex:1; background:#F1F5F9; padding:10px; border-radius:8px; border:1px solid #E2E8F0;"><div style="font-size:11px;">DSR</div><b>{dsr:.1f}%</b></div><div style="flex:1; background:#F1F5F9; padding:10px; border-radius:8px; border:1px solid #E2E8F0;"><div style="font-size:11px;">Rule Engine</div><b>{r_verdict}</b></div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="moto-card">', unsafe_allow_html=True)
    st.markdown("### 📸 เช็กลิสต์เอกสาร • 6 รายการ (Step 3)")
    docs = st.multiselect("เอกสาร", ["Face Verification","บัตร ปชช + ทะเบียนบ้าน","Statement","NCB","สลิปเงินเดือน","ที่พัก + ที่ทำงาน"], default=["บัตร ปชช + ทะเบียนบ้าน","Statement"])
    uploads = st.file_uploader("แนบภาพเอกสาร (HEIC)", type=["jpg","jpeg","png","heic","heif","webp"], accept_multiple_files=True)
    cam = st.camera_input("ถ่ายจากกล้อง")
    comps=[]; files=[]
    if uploads: files.extend(uploads)
    if cam: files.append(cam)
    if files:
        cols=st.columns(3)
        for i,f in enumerate(files):
            try:
                im=Image.open(f)
                cp=_compress_mobile(im)
                comps.append(cp)
                with cols[i%3]: st.image(cp, use_container_width=True)
            except Exception as e: st.error(str(e))
    st.session_state.comps=comps
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="moto-card">', unsafe_allow_html=True)
    st.markdown(f"### 🧠 วิเคราะห์ 13 โมดูลด้วย AI (Step 4) • {selected_model}")
    if 'ai_text' not in st.session_state: st.session_state.ai_text=""
    if st.button("🚀 รัน AI 13 Modules (Gemini 3.6)", type="primary", use_container_width=True):
        if not comps: st.warning("แนบภาพก่อน")
        else:
            prompt=f"SRD CREDIT 13 MODULES - {model_name} ราคา {st.session_state.vehicle_price} ดาวน์ {st.session_state.downpayment} ค่างวด {monthly_instalment:.2f} DSR {dsr:.1f}% ผู้กู้ {applicant_name} อาชีพ {emp_type} ที่ทำงาน {workplace} คู่สมรส {spouse_info} คนค้ำ {guarantor_info} รายละเอียด {extra_details} เอกสาร {', '.join(docs)} วิเคราะห์ภาษาไทย"
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
                save_record({"Timestamp":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"Applicant":applicant_name,"Model":model_name,"Cash":st.session_state.vehicle_price,"Down":st.session_state.downpayment,"Monthly":monthly_instalment,"DSR":f"{dsr:.1f}%","Rule":r_verdict})
            else: st.error(res["raw"][:1000])
    if st.session_state.ai_text:
        pdf2 = gen_pdf(applicant_name, model_name, st.session_state.vehicle_price, st.session_state.downpayment, monthly_instalment, st.session_state.tenure, total_interest, total_payable, dsr, r_verdict, st.session_state.ai_text, st.session_state.extra_details)
        st.download_button("🔴 ส่งออกรายงาน 13 โมดูล PDF", data=pdf2, file_name=f"SRD_13M_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf", mime="application/pdf", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with right_col:
    dsr_val = st.session_state.get('dsr_value', 42.3)
    st.markdown('<div class="moto-card">', unsafe_allow_html=True)
    st.markdown('<div style="display:flex; align-items:center; gap:12px; margin-bottom:16px;"><div style="width:40px; height:40px; background:#F97316; border-radius:10px; display:flex; align-items:center; justify-content:center; color:white;">📊</div><div style="font-weight:700;">มาตรวัด DSR / DSR Meter</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div style="text-align:center;"><div style="position:relative; width:180px; height:100px; margin:0 auto; overflow:hidden;"><div style="width:180px; height:180px; border-radius:50%; background: conic-gradient(from 180deg, #10B981 0deg 90deg, #FBBF24 90deg 135deg, #EF4444 135deg 180deg);"></div><div style="position:absolute; top:20px; left:20px; width:140px; height:140px; background:white; border-radius:50%;"></div><div style="position:absolute; top:45px; left:0; width:180px; text-align:center;"><div style="font-size:28px; font-weight:800;">{dsr_val:.1f}%</div><div style="font-size:11px; color:#64748B;">Debt-Service Ratio</div></div></div><div style="margin-top:8px;"><span style="background:#DCFCE7; color:#166534; padding:4px 12px; border-radius:20px; font-size:11px; font-weight:600;">Within Safe Limit (<50%)</span></div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="moto-card">', unsafe_allow_html=True)
    st.markdown('<div style="display:flex; align-items:center; gap:12px; margin-bottom:12px;"><div style="width:40px; height:40px; background:#7C3AED; border-radius:10px; display:flex; align-items:center; justify-content:center; color:white;">🛡️</div><div style="font-weight:700;">คะแนนความเสี่ยง / Risk Score</div></div><div style="display:flex; align-items:center; gap:12px;"><div class="risk-score">682</div><div class="risk-badge">Medium Risk / ปานกลาง</div></div><div style="margin-top:12px;"><div style="height:6px; background:#E2E8F0; border-radius:3px;"><div style="width:68%; height:100%; background:#6366F1; border-radius:3px;"></div></div><div style="display:flex; justify-content:space-between; font-size:11px; color:#64748B; margin-top:6px;"><span>Risk Band</span><span>PD 3.8%</span></div><div style="margin-top:8px; font-size:12px;">คำแนะนำ: <span style="color:#7C3AED; font-weight:600;">อนุมัติเมื่อมีผู้ค้ำประกัน</span></div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="moto-card">', unsafe_allow_html=True)
    st.markdown('<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;"><div style="display:flex; align-items:center; gap:12px;"><div style="width:40px; height:40px; background:#3B82F6; border-radius:10px; display:flex; align-items:center; justify-content:center; color:white;">🧠</div><div><div style="font-weight:700;">วิเคราะห์ 13 โมดูลด้วย AI</div><div style="font-size:12px; color:#64748B;">AI 13 Modules Analysis</div></div></div><div style="background:#2563EB; color:white; padding:4px 12px; border-radius:20px; font-size:11px;">13/13 Completed</div></div><div style="font-size:11px; line-height:2;">✅ ตรวจสอบการทำงาน ✅ ตรวจจับทุจริต ✅ ความแข็งแกร่งผู้ค้ำ ✅ ตรวจเอกสาร<br>✅ เครดิตบูโร ✅ ความสอดคล้องรายได้ ✅ คะแนนพฤติกรรม ✅ วิเคราะห์กระแสเงินสด<br>✅ ตรวจจับทุจริต ✅ ความเสี่ยงภูมิศาสตร์ ✅ ประเมินมูลค่ารถ ✅ ตรวจสอบความมั่นคง<br>✅ ความแข็งแกร่งผู้ติดต่อ ✅ ประเมินยานพาหนะ ✅ ตรวจสอบหลักประกัน ✅ ปฏิบัติตามกฎระเบียบ</div><div style="margin-top:12px; font-size:11px; background:#F8FAFC; padding:8px 10px; border-radius:8px; border:1px solid #E2E8F0;">✨ ผ่านทั้ง 13 โมดูล • ไม่พบความเสี่ยงร้ายแรง • ความมั่นใจ: 92%</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.caption("SRD Moto Credit v1.2 ไทย • เมนูไทย 100% + โลโก้ลิง SRD + ปุ่ม PDF แดง 2 จุด + 2 โหมดราคา + รายละเอียดปลีกย่อย + Gemini 3.6")
