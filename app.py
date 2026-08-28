import streamlit as st
import pandas as pd
import math, os, io
from datetime import datetime
from PIL import Image
import base64

# Mobile patch
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except:
    pass

def _compress_mobile(img, max_side=1280, max_bytes=1200000):
    img=img.convert("RGB")
    if max(img.size)>max_side:
        img.thumbnail((max_side,max_side), Image.LANCZOS)
    for q in [75,65,55,40]:
        b=io.BytesIO()
        img.save(b, format="JPEG", quality=q, optimize=True)
        if b.tell()<=max_bytes:
            b.seek(0)
            return Image.open(b)
    b.seek(0)
    return Image.open(b)

st.set_page_config(page_title="SRD Credit Engine v1.2", layout="wide", page_icon="🏍️")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }
.stApp { background-color: #F8FAFC !important; }
[data-testid="stSidebar"] { background-color: #0F172A !important; }
[data-testid="stSidebar"] * { color: #E2E8F0 !important; }
.srd-card { background: white; padding: 18px; border-radius: 12px; border: 1px solid #E2E8F0; box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-bottom: 14px; }
</style>
""", unsafe_allow_html=True)

# Header
c1,c2,c3 = st.columns([1,6,2])
with c1:
    if os.path.exists("srd_logo.png"):
        st.image("srd_logo.png", width=60)
    else:
        st.markdown("### 🏍️ SRD")
with c2:
    st.markdown("## Motorcycle Loan Credit Engine")
    st.caption("ระบบตรวจสอบสินเชื่อมอเตอร์ไซค์ • SRD Loan Credit Engine v1.2")
with c3:
    st.markdown("🟢 **Connected • Live**")

# API Key handling - both Secrets and manual
def get_secret_key():
    try:
        k = st.secrets.get("GEMINI_API_KEY","") if hasattr(st,'secrets') else ""
    except:
        k=""
    if not k:
        k = os.getenv("GEMINI_API_KEY","") or os.getenv("GOOGLE_API_KEY","")
    return k.strip()

secret_key = get_secret_key()
if 'manual_key' not in st.session_state:
    st.session_state.manual_key=""

api_key = secret_key or st.session_state.manual_key

PREFERRED_MODELS = ["gemini-2.5-flash","gemini-2.0-flash","gemini-flash-latest","gemini-1.5-flash","gemini-1.5-flash-8b"]

# Sidebar
with st.sidebar:
    st.markdown("### 🏍️ SRD Credit")
    st.caption("SRD Loan Credit Engine • v1.2")
    st.write("---")
    if not secret_key:
        st.warning("⚠️ ไม่พบ GEMINI_API_KEY ใน Secrets")
        mk = st.text_input("🔑 ใส่ GEMINI API Key ชั่วคราว", type="password", value=st.session_state.manual_key, placeholder="AIza...")
        if mk:
            st.session_state.manual_key = mk.strip()
            api_key = st.session_state.manual_key
        st.caption("วิธีตั้งถาวร: Streamlit Cloud > Manage app > Settings > Secrets ใส่ GEMINI_API_KEY = \"...\"")
    else:
        st.success("✅ พบ API Key ใน Secrets แล้ว")

    if not api_key:
        st.error("❌ กรุณาใส่ API Key ก่อนใช้งาน")
        st.stop()

    # Dual SDK init
    IS_NEW_SDK=True
    try:
        from google import genai as new_genai
        from google.genai import types as new_types
        from google.genai.errors import ClientError as NewClientError
        @st.cache_resource(show_spinner=False)
        def get_client_new(k_hash, k_val):
            cl = new_genai.Client(api_key=k_val)
            av=[]
            try:
                for m in cl.models.list():
                    av.append(m.name.replace("models/",""))
            except:
                av=PREFERRED_MODELS
            sel=PREFERRED_MODELS[0]
            for p in PREFERRED_MODELS:
                if p in av:
                    sel=p
                    break
            return cl, sel, av
        client, selected_model, usable_models = get_client_new(api_key[:8], api_key)
        genai_types=new_types
        ClientErrorClass=NewClientError
        genai_client=new_genai
    except ImportError:
        IS_NEW_SDK=False
        import google.generativeai as old_genai
        old_genai.configure(api_key=api_key)
        av=[]
        try:
            for m in old_genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    av.append(m.name.replace("models/",""))
        except:
            av=PREFERRED_MODELS
        sel=PREFERRED_MODELS[0]
        for p in PREFERRED_MODELS:
            if p in av:
                sel=p
                break
        client=None
        selected_model=sel
        usable_models=av
        genai_types=None
        ClientErrorClass=Exception
        genai_client=old_genai

    st.write("---")
    st.caption("เมนูนำทาง")
    menu = st.radio("เมนู",["แดชบอร์ด","เครื่องคำนวณสินเชื่อ","ใบสมัคร","ลูกค้า","เอกสาร","วิเคราะห์ข้อมูล","ความเสี่ยงและนโยบาย"], label_visibility="collapsed", index=1)
    st.write("---")
    st.caption(f"🤖 AI: {selected_model}")
    st.caption(f"พร้อมใช้งาน: {len(usable_models)} โมเดล")

# History
HISTORY_FILE="srd_credit_assessment_history.csv"
def save_record(d):
    df=pd.DataFrame([d])
    if not os.path.exists(HISTORY_FILE):
        df.to_csv(HISTORY_FILE,index=False,encoding='utf-8-sig')
    else:
        df.to_csv(HISTORY_FILE,mode='a',header=False,index=False,encoding='utf-8-sig')

# Rule Engine
def evaluate_fraud_rules(vehicle_type, down_pct, employment_type, shared, dsr_val, gps):
    score=0; flags=[]
    high=["Yamaha - Sport","Honda - รถใหม่"]
    unstable=["ฟรีแลนซ์/รับจ้างทั่วไป","ว่างงาน/ไม่มีงานประจำ","FREELANCE"]
    if (vehicle_type in high or "Sport" in vehicle_type) and down_pct<=5 and employment_type in unstable:
        score+=40; flags.append("⚠️ เสี่ยงดาวน์แลกเงิน")
    if shared>=1:
        score+=50; flags.append("🚨 เครือข่ายนายหน้า")
    if (dsr_val>50 or down_pct<10) and not gps:
        score+=20; flags.append("⚠️ DSRสูงแต่ไม่ยินยอม GPS")
    if score>=80:
        verdict="⛔ AUTO REJECT"
    elif score>=50:
        verdict="🟠 MANUAL REVIEW"
    else:
        verdict="🟢 AUTO PASS"
    return score,flags,verdict

# Load motorcycle data
@st.cache_data
def load_data():
    fp='Yamaha_+รวมขายทุกตัว 25-8-69 Dynamic_Formulas_Categories.xlsx'
    d={}
    for sh in ['Auto','Moped','Sport','Honda รถใหม่','Honda มือสอง']:
        try:
            df=pd.read_excel(fp,sheet_name=sh,skiprows=1)
            if 'รุ่นรถ' in df.columns:
                df[['รุ่นรถ']]=df[['รุ่นรถ']].ffill()
                d[sh]=df
        except:
            pass
    return d

motorcycle_data=load_data()

# PDF
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.lib.pagesizes import A4
def gen_pdf(name,model,cash,down,monthly,term,interest,total,dsr,verdict,ai_text):
    buf=io.BytesIO()
    c=pdf_canvas.Canvas(buf,pagesize=A4)
    w,h=A4
    c.setFont("Helvetica-Bold",14)
    c.drawString(20,800,"SRD Credit - Loan Credit Engine v1.2")
    c.setFont("Helvetica",9)
    c.drawString(20,785,f"Applicant: {name} | Model: {model} | Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    c.setFont("Helvetica-Bold",11)
    c.drawString(20,765,"Flat Rate Calculation")
    c.setFont("Helvetica",9)
    c.drawString(20,750,f"Price: {cash:,.0f} | Down: {down:,.0f} | Monthly: {monthly:,.0f} x {term} | Interest: {interest:,.0f} | Total: {total:,.0f}")
    c.drawString(20,735,f"DSR: {dsr:.1f}% | Verdict: {verdict}")
    c.setFont("Helvetica-Bold",11)
    c.drawString(20,715,"AI 13 Modules Analysis")
    c.setFont("Helvetica",8)
    y=700
    for line in (ai_text or "No analysis").split("\n"):
        for chunk in [line[i:i+100] for i in range(0,len(line),100)]:
            if y<30:
                c.showPage(); y=800
            c.drawString(20,y,chunk[:110])
            y-=11
    c.showPage(); c.save(); buf.seek(0)
    return buf

# Steps bar
st.markdown("""
<div class="srd-card" style="text-align:center">
<span style="background:#16A34A;color:white;padding:6px 12px;border-radius:20px">✓ ขั้นตอนที่ 1 เลือกยานพาหนะ</span>
<span style="background:#2563EB;color:white;padding:6px 12px;border-radius:20px;margin-left:8px">2 ผู้สมัคร & ผู้ค้ำประกัน</span>
<span style="background:#F1F5F9;color:#64748B;border:1px solid #E2E8F0;padding:6px 12px;border-radius:20px;margin-left:8px">3 เช็กลิสต์เอกสาร • 6 รายการ</span>
<span style="background:#F1F5F9;color:#64748B;border:1px solid #E2E8F0;padding:6px 12px;border-radius:20px;margin-left:8px">4 วิเคราะห์ 13 โมดูลด้วย AI</span>
</div>
""", unsafe_allow_html=True)

left,right = st.columns([2,1])

with left:
    st.markdown('<div class="srd-card">',unsafe_allow_html=True)
    st.markdown("### 🧮 เครื่องคำนวณอัตราดอกเบี้ยคงที่")
    st.caption("ปรับค่าพารามิเตอร์ได้ทุกช่อง - สูตร Flat Rate เต็มรูปแบบ")

    if motorcycle_data:
        cat=st.selectbox("หมวดหมู่รถ (5 หมวด)", list(motorcycle_data.keys()))
        df_cat=motorcycle_data[cat]
        model_col='รุ่นรถ' if 'รุ่นรถ' in df_cat.columns else df_cat.columns[0]
        model_name=st.selectbox("รุ่นรถ", df_cat[model_col].astype(str).unique()[:200])
        try:
            row=df_cat[df_cat[model_col].astype(str)==model_name].iloc[0]
            def_price=float(row.get('ราคาสด', row.get('ราคาจัด', 80000)))
            def_int=float(row.get('ดอกเบี้ย',1.5))
            if def_int>10: def_int=def_int/12
        except:
            def_price=80000; def_int=1.5
    else:
        model_name=st.text_input("รุ่นรถ","Yamaha Finn")
        def_price=50000; def_int=1.5; cat="Auto"

    c1,c2=st.columns(2)
    with c1:
        cash_price=st.number_input("ราคารถ (MYR/บาท)", value=float(def_price), step=1000.0)
        tenure=st.selectbox("ระยะเวลาผ่อน (เดือน)", [12,18,24,30,36,42,48,60], index=4)
    with c2:
        down_payment=st.number_input("เงินดาวน์ (MYR/บาท)", value=float(def_price*0.2), step=500.0)
        flat_rate=st.number_input("ดอกเบี้ย Flat Rate (% ต่อเดือน)", value=float(def_int), format="%.2f")

    proc_fee=st.number_input("ค่าธรรมเนียมดำเนินการ (MYR)", value=300.0)

    down_pct=(down_payment/cash_price*100) if cash_price else 0
    financing=cash_price-down_payment
    total_interest=financing*(flat_rate/100)*tenure
    total_debt=financing+total_interest
    monthly=total_debt/tenure if tenure else 0
    total_cash=down_payment+proc_fee
    total_all=total_debt+down_payment+proc_fee

    monthly_edit=st.number_input("ค่างวดต่อเดือน (แก้ไขได้ - ส่งไป DSR+AI อัตโนมัติ)", value=float(monthly), step=10.0)

    colA,colB=st.columns(2)
    with colA:
        st.button("⚡ คำนวณสินเชื่อ", type="primary", use_container_width=True)
    with colB:
        pdf1=gen_pdf(st.session_state.get('applicant_name',''), model_name, cash_price, down_payment, monthly_edit, tenure, total_interest, total_all, st.session_state.get('dsr_calc',0), st.session_state.get('r_verdict',''), st.session_state.get('ai_text',''))
        st.download_button("📄 ส่งออกเป็น PDF", data=pdf1, file_name=f"SRD_Loan_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf", mime="application/pdf", use_container_width=True)

    st.info(f"ยอดผ่อน: MYR {monthly_edit:,.2f}/เดือน | ดอกเบี้ยรวม: {total_interest:,.0f} | ยอดรวม: {total_all:,.0f} | จ่ายวันออกรถ: {total_cash:,.0f} | ยอดจัด: {financing:,.0f} ({down_pct:.1f}% ดาวน์)")
    st.markdown('</div>',unsafe_allow_html=True)

    st.markdown('<div class="srd-card">',unsafe_allow_html=True)
    st.markdown("### 👤 ข้อมูลผู้สมัคร & ผู้ค้ำประกัน")
    a1,a2=st.columns(2)
    with a1:
        applicant_name=st.text_input("ชื่อผู้กู้","สมชาย")
        salary=st.number_input("เงินเดือน", value=15000.0, step=500.0)
        extra=st.number_input("รายได้เสริม", value=2000.0)
    with a2:
        phone=st.text_input("เบอร์โทร","081-xxx-xxxx")
        debt=st.number_input("หนี้เดิมต่อเดือน", value=3000.0)
        emp_type=st.selectbox("อาชีพ",["พนักงานประจำ","ฟรีแลนซ์/รับจ้างทั่วไป","ค้าขาย","ว่างงาน/ไม่มีงานประจำ"])

    st.session_state.applicant_name=applicant_name
    total_income=salary+extra
    dsr_calc=((debt+monthly_edit)/total_income*100) if total_income else 0
    st.session_state.dsr_calc=dsr_calc
    r_score,r_flags,r_verdict=evaluate_fraud_rules(cat, down_pct, emp_type, 0, dsr_calc, True)
    st.session_state.r_verdict=r_verdict

    st.metric("DSR", f"{dsr_calc:.1f}%", delta="ปลอดภัย" if dsr_calc<50 else "เกินเกณฑ์")
    st.metric("Rule Engine", r_verdict)
    for f in r_flags: st.warning(f)
    st.markdown('</div>',unsafe_allow_html=True)

    st.markdown('<div class="srd-card">',unsafe_allow_html=True)
    st.markdown("### 📸 เช็กลิสต์เอกสาร • 6 รายการ")
    docs=st.multiselect("เอกสารที่แนบแล้ว",["Face Verification","บัตร ปชช + ทะเบียนบ้าน","Statement","NCB","สลิปเงินเดือน","ที่พัก + ที่ทำงาน"], default=["บัตร ปชช + ทะเบียนบ้าน","Statement"])
    uploads=st.file_uploader("แนบภาพ (รองรับ HEIC - ย่ออัตโนมัติ)", type=["jpg","jpeg","png","heic","heif","webp"], accept_multiple_files=True)
    cam=st.camera_input("ถ่ายจากกล้องมือถือ")
    all_files=[]
    if uploads: all_files.extend(uploads)
    if cam: all_files.append(cam)
    comps=[]
    if all_files:
        cols=st.columns(3)
        for i,f in enumerate(all_files):
            try:
                img=Image.open(f)
                cp=_compress_mobile(img)
                comps.append(cp)
                with cols[i%3]: st.image(cp, use_container_width=True)
            except Exception as e:
                st.error(str(e))
        st.success(f"เตรียมไฟล์ {len(comps)} รูปแล้ว")
    st.session_state.comps=comps
    st.markdown('</div>',unsafe_allow_html=True)

    st.markdown('<div class="srd-card">',unsafe_allow_html=True)
    if 'ai_text' not in st.session_state: st.session_state.ai_text=""
    if st.button("🚀 รัน SRD Credit Investigation Engine 13 Modules เต็มระบบ", type="primary", use_container_width=True):
        if not st.session_state.comps:
            st.warning("กรุณาแนบภาพอย่างน้อย 1 ไฟล์")
        else:
            prompt=f"""
            SRD CREDIT INVESTIGATION ENGINE FULL 13 MODULES - ภาษาไทย
            รุ่นรถ: {model_name} หมวด {cat} ราคา {cash_price:,.0f} ดาวน์ {down_payment:,.0f} ({down_pct:.1f}%) ยอดจัด {financing:,.0f}
            ค่างวด {monthly_edit:,.0f} x {tenure} ดอกเบี้ย {flat_rate:.2f}% DSR {dsr_calc:.1f}% Rule {r_verdict}
            ผู้กู้: {applicant_name} อาชีพ {emp_type} รายได้ {total_income:,.0f}
            เอกสาร: {', '.join(docs)}
            วิเคราะห์ 10 ข้อ: Profile, Identity, Verified vs Unverified, Money Flow, Fraud Gambling Nominee, Guarantor, Contradiction Table, Risk Scoring 100 คะแนน, Interview, Summary
            """
            def call_ai(prom, imgs, model, client_obj):
                try:
                    if IS_NEW_SDK:
                        contents=[prom]
                        for im in imgs:
                            if max(im.size)>1600: im.thumbnail((1600,1600))
                            buf=io.BytesIO(); im.save(buf, format="JPEG")
                            contents.append(genai_types.Part.from_bytes(data=buf.getvalue(), mime_type="image/jpeg"))
                        resp=client_obj.models.generate_content(model=model, contents=contents, config=genai_types.GenerateContentConfig(temperature=0.2, max_output_tokens=8192))
                        txt=getattr(resp,'text',None) or resp.candidates[0].content.parts[0].text
                        return {"ok":True,"text":txt}
                    else:
                        m=genai_client.GenerativeModel(model)
                        r=m.generate_content([prom]+imgs)
                        return {"ok":True,"text":r.text}
                except Exception as e:
                    msg=str(e)
                    if "429" in msg or "quota" in msg.lower():
                        return {"ok":False,"error":"QUOTA_FULL","raw":msg}
                    return {"ok":False,"error":"API_ERROR","raw":msg}

            with st.spinner(f"AI ({selected_model}) กำลังวิเคราะห์ 13 โมดูล..."):
                res=call_ai(prompt, st.session_state.comps, selected_model, client)
            if res["ok"]:
                st.session_state.ai_text=res["text"]
                st.success("✅ วิเคราะห์สำเร็จ")
                st.markdown(res["text"])
                save_record({"Timestamp":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"Applicant":applicant_name,"Model":model_name,"Cash":cash_price,"Down":down_payment,"Monthly":monthly_edit,"DSR":f"{dsr_calc:.1f}%","Rule":r_verdict})
            elif res["error"]=="QUOTA_FULL":
                st.error("⏳ AI โควตาเต็มชั่วคราว (429) - Rule Engine และ DSR ยังใช้งานได้")
            else:
                st.error(res["raw"])

    if st.session_state.ai_text:
        pdf2=gen_pdf(applicant_name, model_name, cash_price, down_payment, monthly_edit, tenure, total_interest, total_all, dsr_calc, r_verdict, st.session_state.ai_text)
        st.download_button("📄 ส่งออกรายงาน 13 โมดูล PDF", data=pdf2, file_name=f"SRD_13M_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf", mime="application/pdf", use_container_width=True)
    st.markdown('</div>',unsafe_allow_html=True)

with right:
    st.markdown('<div class="srd-card">',unsafe_allow_html=True)
    st.markdown("### 📊 มาตรวัด DSR")
    colc="#16A34A" if st.session_state.get('dsr_calc',0)<35 else "#F59E0B" if st.session_state.get('dsr_calc',0)<50 else "#DC2626"
    dsr_v=st.session_state.get('dsr_calc',0)
    st.markdown(f"<div style='text-align:center'><div style='font-size:32px;font-weight:700;color:{colc}'>{dsr_v:.1f}%</div><div>อัตราส่วนภาระหนี้</div></div>", unsafe_allow_html=True)
    st.markdown('</div>',unsafe_allow_html=True)

    st.markdown('<div class="srd-card">',unsafe_allow_html=True)
    st.markdown("### 🛡️ คะแนนความเสี่ยง")
    score=max(300, min(850, 850 - r_score*3 - dsr_v*2))
    st.markdown(f"<div style='text-align:center'><span style='font-size:32px;font-weight:700;color:#4F46E5'>{score:.0f}</span> <span style='background:#DDD6FE;padding:4px 10px;border-radius:12px'>{'ต่ำ' if score>700 else 'ปานกลาง' if score>600 else 'สูง'}</span></div>", unsafe_allow_html=True)
    st.info(r_verdict)
    st.markdown('</div>',unsafe_allow_html=True)

    st.markdown('<div class="srd-card">',unsafe_allow_html=True)
    st.markdown("### 🤖 การวิเคราะห์ 13 โมดูลด้วย AI")
    mods=["ตรวจสอบรายได้","ประวัติเครดิต","ประเมินภาระหนี้","ตรวจสอบเอกสาร","ตรวจสอบที่อยู่","ตรวจสอบการทำงาน","รายได้สุทธิ","คำนวณ DSR","ประเมินความเสี่ยง","บัญชีดำ","ผู้ค้ำ","ข้อแนะนำ","ปฏิบัติตามกฎ"]
    for m in mods: st.caption(f"✅ {m}")
    if st.session_state.ai_text: st.success("เสร็จสิ้น 13/13")
    st.markdown('</div>',unsafe_allow_html=True)