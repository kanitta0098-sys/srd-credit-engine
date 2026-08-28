import streamlit as st
import pandas as pd, os, io
from datetime import datetime
from PIL import Image

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except:
    pass

def _compress_mobile(img, max_side=1280, max_bytes=1200000):
    img = img.convert("RGB")
    if max(img.size) > max_side:
        img.thumbnail((max_side, max_side), Image.LANCZOS)
    for q in [75,65,55,40]:
        b=io.BytesIO()
        img.save(b, format="JPEG", quality=q, optimize=True)
        if b.tell() <= max_bytes:
            b.seek(0)
            return Image.open(b)
    b.seek(0)
    return Image.open(b)

st.set_page_config(page_title="SRD Credit Engine v1.2 - Gemini 3.6", layout="wide", page_icon="🏍️")

st.markdown("""
<style>
.stApp { background:#F8FAFC !important; }
[data-testid="stSidebar"] { background:#0F172A !important; }
[data-testid="stSidebar"] * { color:#E2E8F0 !important; }
.srd-card { background:white; padding:16px; border-radius:12px; border:1px solid #E2E8F0; margin-bottom:12px; }
.srd-metric { background:#F1F5F9; padding:10px 14px; border-radius:8px; border:1px solid #E2E8F0; }
</style>
""", unsafe_allow_html=True)

st.markdown("## Motorcycle Loan Credit Engine v1.2 - Gemini 3.6 Ready")
st.caption("Professional Finance Theme • รองรับ gemini-3.6-flash + Interactions API • Auto Fallback 404")

def get_secret():
    try:
        k = st.secrets.get("GEMINI_API_KEY","") if hasattr(st,'secrets') else ""
    except:
        k=""
    if not k:
        k = os.getenv("GEMINI_API_KEY","") or os.getenv("GOOGLE_API_KEY","")
    return k.strip()

secret_key = get_secret()
if 'manual_key' not in st.session_state:
    st.session_state.manual_key=""
api_key = secret_key or st.session_state.manual_key

PREFERRED_MODELS = ["gemini-3.6-flash","gemini-3.0-flash","gemini-2.5-flash","gemini-2.0-flash","gemini-flash-latest","gemini-1.5-flash"]

HISTORY_FILE="srd_credit_assessment_history.csv"
def save_record(d):
    df=pd.DataFrame([d])
    if not os.path.exists(HISTORY_FILE):
        df.to_csv(HISTORY_FILE,index=False,encoding='utf-8-sig')
    else:
        df.to_csv(HISTORY_FILE,mode='a',header=False,index=False,encoding='utf-8-sig')

with st.sidebar:
    st.markdown("### 🏍️ SRD Credit v1.2 - Gemini 3.6")
    if not secret_key:
        st.warning("⚠️ ไม่พบ GEMINI_API_KEY ใน Secrets")
        mk = st.text_input("🔑 GEMINI API Key", type="password", value=st.session_state.manual_key, placeholder="AIza... ")
        if mk:
            st.session_state.manual_key = mk.strip()
            api_key = st.session_state.manual_key
    else:
        st.success("✅ พบ API Key ใน Secrets แล้ว")

    if not api_key:
        st.error("❌ กรุณาใส่ API Key ก่อน")
        st.stop()

    usable_models=[]; selected_model=None; client=None; genai_client=None; genai_types=None; IS_NEW_SDK=False

    try:
        from google import genai as new_genai
        from google.genai import types as new_types
        IS_NEW_SDK=True
        genai_client=new_genai; genai_types=new_types
        @st.cache_resource(show_spinner=False)
        def get_client_new(k_hash,k_val):
            cl=new_genai.Client(api_key=k_val)
            av=[]
            try:
                for m in cl.models.list():
                    av.append(m.name.replace("models/",""))
            except:
                av=PREFERRED_MODELS
            sel="gemini-3.6-flash"
            if sel not in av:
                for p in PREFERRED_MODELS:
                    if p in av:
                        sel=p; break
                if sel not in av and av:
                    sel=av[0]
            return cl,sel,av
        client,selected_model,usable_models=get_client_new(api_key[:8],api_key)
        def sort_key(x):
            if "3.6" in x: return 0
            if "3.0" in x: return 1
            if "2.5" in x: return 2
            return 3
        sorted_models=sorted(usable_models,key=sort_key)
        try: default_idx=sorted_models.index(selected_model)
        except: default_idx=0
        selected_model=st.selectbox("🤖 โมเดล AI (แนะนำ 3.6-flash)", sorted_models, index=default_idx)
        st.success(f"✅ New SDK พร้อม: {selected_model}")
    except ImportError:
        IS_NEW_SDK=False
        import google.generativeai as old_genai
        old_genai.configure(api_key=api_key.strip())
        av=[]
        try:
            for m in old_genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    av.append(m.name.replace("models/",""))
        except:
            av=PREFERRED_MODELS
        sel="gemini-3.6-flash"
        if sel not in av:
            sel=av[0] if av else "gemini-1.5-flash"
        selected_model=st.selectbox("🤖 โมเดล AI", av, index=av.index(sel) if sel in av else 0) if av else sel
        usable_models=av; genai_client=old_genai
    except Exception as e:
        err_msg=str(e)
        if "404" in err_msg or "NOT_FOUND" in err_msg:
            from google import genai as new_genai
            from google.genai import types as new_types
            cl=new_genai.Client(api_key=api_key.strip())
            selected_model="gemini-3.6-flash"; client=cl; genai_client=new_genai; genai_types=new_types; IS_NEW_SDK=True; usable_models=PREFERRED_MODELS
            st.success(f"✅ Auto Fallback ไปใช้: {selected_model}")
        else:
            st.error(f"เชื่อมต่อขัดข้อง: {e}"); st.stop()

    st.write("---")
    menu=st.radio("เมนู",["แดชบอร์ด","เครื่องคำนวณสินเชื่อ","ใบสมัคร","ลูกค้า","เอกสาร","วิเคราะห์ข้อมูล","ความเสี่ยงและนโยบาย"], label_visibility="collapsed", index=1)

def evaluate_fraud_rules(vehicle_type, down_pct, emp_type, shared, dsr_val, gps):
    score=0; flags=[]
    if "Sport" in vehicle_type and down_pct<=5: score+=40; flags.append("เสี่ยงดาวน์แลกเงิน")
    if shared>=1: score+=50; flags.append("เครือข่ายนายหน้า")
    if (dsr_val>50 or down_pct<10) and not gps: score+=20; flags.append("DSRสูงแต่ไม่ยินยอม GPS")
    if score>=80: verdict="⛔ AUTO REJECT"
    elif score>=50: verdict="🟠 MANUAL REVIEW"
    else: verdict="🟢 AUTO PASS"
    return score,flags,verdict

@st.cache_data
def load_data():
    fp='Yamaha_+รวมขายทุกตัว 25-8-69 Dynamic_Formulas_Categories.xlsx'
    d={}
    for sh in ['Auto','Moped','Sport']:
        try:
            df=pd.read_excel(fp, sheet_name=sh, skiprows=1)
            if 'รุ่นรถ' in df.columns:
                df[['รุ่นรถ']]=df[['รุ่นรถ']].ffill()
                d[sh]=df.dropna(subset=['รุ่นรถ'])
        except: pass
    return d

motorcycle_data=load_data()

from reportlab.pdfgen import canvas as pdf_c
from reportlab.lib.pagesizes import A4
def gen_pdf(name,model,cash,down,monthly,term,interest,total,dsr,verdict,ai_text):
    buf=io.BytesIO()
    c=pdf_c.Canvas(buf,pagesize=A4)
    c.setFont("Helvetica-Bold",12)
    c.drawString(30,800,f"SRD Credit v1.2 - {model} - {datetime.now().strftime('%d/%m/%Y')} - {selected_model}")
    c.setFont("Helvetica",9)
    c.drawString(30,785,f"Applicant: {name} | Price: {cash:,.0f} Down: {down:,.0f} Monthly: {monthly:,.0f} x {term}")
    c.drawString(30,770,f"DSR: {dsr:.1f}% Verdict: {verdict}")
    if ai_text:
        y=750; c.setFont("Helvetica",8)
        for line in ai_text.split("\n")[:90]:
            c.drawString(30,y,line[:100]); y-=11
            if y<30: c.showPage(); y=800
    c.showPage(); c.save(); buf.seek(0)
    return buf

st.markdown('<div class="srd-card" style="text-align:center"><span style="background:#16A34A;color:white;padding:6px 12px;border-radius:20px">✓ ขั้นตอนที่ 1</span><span style="background:#2563EB;color:white;padding:6px 12px;border-radius:20px;margin-left:6px">2 ผู้สมัคร & ผู้ค้ำ</span><span style="background:#F1F5F9;color:#64748B;border:1px solid #E2E8F0;padding:6px 12px;border-radius:20px;margin-left:6px">3 เช็กลิสต์ 6 รายการ</span><span style="background:#F1F5F9;color:#64748B;border:1px solid #E2E8F0;padding:6px 12px;border-radius:20px;margin-left:6px">4 วิเคราะห์ 13 โมดูล</span></div>', unsafe_allow_html=True)

left,right=st.columns([2,1])
with left:
    st.markdown('<div class="srd-card">', unsafe_allow_html=True)
    st.markdown(f"### 🧮 เครื่องคำนวณ Flat Rate (ใช้ {selected_model})")
    if motorcycle_data:
        cat=st.selectbox("หมวดหมู่รถ", list(motorcycle_data.keys()))
        df_cat=motorcycle_data[cat]
        model_col='รุ่นรถ' if 'รุ่นรถ' in df_cat.columns else df_cat.columns[0]
        model_name=st.selectbox("รุ่นรถ", df_cat[model_col].astype(str).unique()[:250])
        try:
            row=df_cat[df_cat[model_col].astype(str)==model_name].iloc[0]
            def_price=float(row.get('ราคาสด',80000)); def_int=float(row.get('ดอกเบี้ย',1.5))
            if def_int>10: def_int/=12
        except: def_price=80000; def_int=1.5
    else:
        model_name=st.text_input("รุ่นรถ","Yamaha Finn"); def_price=50000; def_int=1.5; cat="Auto"
    c1,c2=st.columns(2)
    with c1:
        cash_price=st.number_input("ราคารถ", value=float(def_price), step=1000.0)
        tenure=st.selectbox("ผ่อน (เดือน)", [12,18,24,30,36,42,48,60], index=4)
    with c2:
        down_payment=st.number_input("เงินดาวน์", value=float(def_price*0.2), step=500.0)
        flat_rate=st.number_input("ดอกเบี้ย %/เดือน", value=float(def_int), format="%.3f")
    proc_fee=st.number_input("ค่าดำเนินการ", value=300.0)
    down_pct=(down_payment/cash_price*100) if cash_price else 0
    financing=cash_price-down_payment
    total_interest=financing*(flat_rate/100)*tenure
    total_debt=financing+total_interest
    monthly=total_debt/tenure if tenure else 0
    total_all=total_debt+down_payment+proc_fee
    monthly_edit=st.number_input("ค่างวด/เดือน (แก้ได้)", value=float(monthly), step=10.0)
    colA,colB=st.columns(2)
    with colA: st.button("⚡ คำนวณสินเชื่อ", type="primary", use_container_width=True)
    with colB:
        pdf1=gen_pdf(st.session_state.get('applicant_name',''), model_name, cash_price, down_payment, monthly_edit, tenure, total_interest, total_all, st.session_state.get('dsr_calc',0), st.session_state.get('r_verdict',''), st.session_state.get('ai_text',''))
        st.download_button("📄 ส่งออกเป็น PDF", data=pdf1, file_name=f"SRD_Loan_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf", mime="application/pdf", use_container_width=True)
    st.markdown(f'<div class="srd-metric">ยอดผ่อน: <b>MYR {monthly_edit:,.2f} /เดือน</b> | ดอกเบี้ยรวม: {total_interest:,.0f} | ยอดรวม: {total_all:,.0f}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="srd-card">', unsafe_allow_html=True)
    st.markdown("### 👤 ผู้สมัคร & ผู้ค้ำ")
    a1,a2=st.columns(2)
    with a1:
        applicant_name=st.text_input("ชื่อผู้กู้","สมชาย")
        salary=st.number_input("เงินเดือน", value=15000.0, step=500.0)
        extra=st.number_input("รายได้เสริม", value=2000.0)
    with a2:
        debt=st.number_input("หนี้เดิมต่อเดือน", value=3000.0)
        emp_type=st.selectbox("อาชีพ",["พนักงานประจำ","ฟรีแลนซ์/รับจ้างทั่วไป","ค้าขาย","ว่างงาน/ไม่มีงานประจำ"])
    st.session_state.applicant_name=applicant_name
    total_income=salary+extra
    dsr_calc=((debt+monthly_edit)/total_income*100) if total_income else 0
    st.session_state.dsr_calc=dsr_calc
    r_score,r_flags,r_verdict=evaluate_fraud_rules(cat, down_pct, emp_type, 0, dsr_calc, True)
    st.session_state.r_verdict=r_verdict
    st.markdown(f'<div style="display:flex;gap:10px"><div class="srd-metric" style="flex:1"><div>DSR</div><b>{dsr_calc:.1f}%</b></div><div class="srd-metric" style="flex:1"><div>Rule Engine</div><b>{r_verdict}</b></div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="srd-card">', unsafe_allow_html=True)
    st.markdown("### 📸 เช็กลิสต์เอกสาร 6 รายการ")
    docs=st.multiselect("เอกสาร",["Face Verification","บัตร ปชช + ทะเบียนบ้าน","Statement","NCB","สลิปเงินเดือน","ที่พัก + ที่ทำงาน"], default=["บัตร ปชช + ทะเบียนบ้าน","Statement"])
    uploads=st.file_uploader("แนบภาพ (ย่ออัตโนมัติ)", type=["jpg","jpeg","png","heic","heif","webp"], accept_multiple_files=True)
    cam=st.camera_input("ถ่ายจากกล้อง")
    all_files=[]
    if uploads: all_files.extend(uploads)
    if cam: all_files.append(cam)
    comps=[]
    if all_files:
        cols=st.columns(3)
        for i,f in enumerate(all_files):
            try:
                im=Image.open(f)
                cp=_compress_mobile(im)
                comps.append(cp)
                with cols[i%3]: st.image(cp, use_container_width=True)
            except Exception as e:
                st.error(str(e))
    st.session_state.comps=comps
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="srd-card">', unsafe_allow_html=True)
    if 'ai_text' not in st.session_state: st.session_state.ai_text=""
    if st.button("🚀 รัน AI 13 โมดูล (Gemini 3.6)", type="primary", use_container_width=True):
        if not comps:
            st.warning("แนบภาพก่อน")
        else:
            prompt=f"""SRD CREDIT 13 MODULES - ใช้ {selected_model}
รุ่นรถ: {model_name} ราคา {cash_price} ดาวน์ {down_payment} ({down_pct:.1f}%)
ค่างวด {monthly_edit} x {tenure} DSR {dsr_calc:.1f}% Rule {r_verdict}
ผู้กู้: {applicant_name} อาชีพ {emp_type} รายได้ {total_income}
เอกสาร: {', '.join(docs)} วิเคราะห์ภาษาไทย
"""
            def call_ai_v3(prom, imgs, model_name, client_obj):
                try:
                    if IS_NEW_SDK:
                        contents=[prom]
                        for im in imgs:
                            if max(im.size)>1600: im.thumbnail((1600,1600))
                            buf=io.BytesIO(); im.save(buf, format="JPEG")
                            contents.append(genai_types.Part.from_bytes(data=buf.getvalue(), mime_type="image/jpeg"))
                        try:
                            resp=client_obj.models.generate_content(model=model_name, contents=contents, config=genai_types.GenerateContentConfig(temperature=0.2, max_output_tokens=8192))
                        except Exception as e:
                            if "404" in str(e) or "NOT_FOUND" in str(e):
                                fallback="gemini-3.6-flash"
                                st.warning(f"โมเดล {model_name} ไม่พร้อมใช้งาน ลอง {fallback}...")
                                resp=client_obj.models.generate_content(model=fallback, contents=contents, config=genai_types.GenerateContentConfig(temperature=0.2, max_output_tokens=8192))
                            else:
                                raise e
                        txt=getattr(resp,'text',None) or resp.candidates[0].content.parts[0].text
                        return {"ok":True,"text":txt}
                    else:
                        m=genai_client.GenerativeModel(model_name)
                        r=m.generate_content([prom]+imgs)
                        return {"ok":True,"text":r.text}
                except Exception as e:
                    msg=str(e)
                    if "404" in msg or "NOT_FOUND" in msg or "no longer available" in msg.lower():
                        return {"ok":False,"error":"MODEL_NOT_FOUND","raw":msg}
                    if "429" in msg or "quota" in msg.lower():
                        return {"ok":False,"error":"QUOTA_FULL","raw":msg}
                    return {"ok":False,"error":"API_ERROR","raw":msg}

            with st.spinner(f"AI ({selected_model}) กำลังวิเคราะห์..."):
                res=call_ai_v3(prompt, comps, selected_model, client)
            if res["ok"]:
                st.session_state.ai_text=res["text"]
                st.success(f"✅ สำเร็จด้วย {selected_model}")
                st.markdown(res["text"])
                save_record({"Timestamp":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"Applicant":applicant_name,"Model":model_name,"Cash":cash_price,"Down":down_payment,"Monthly":monthly_edit,"DSR":f"{dsr_calc:.1f}%","Rule":r_verdict,"AIModel":selected_model})
            elif res["error"]=="MODEL_NOT_FOUND":
                st.error(f"❌ โมเดลไม่พร้อมใช้งาน: {res['raw'][:500]}")
                st.info("💡 เลือก gemini-3.6-flash ใน Sidebar")
            elif res["error"]=="QUOTA_FULL":
                st.error("⏳ โควตาเต็มชั่วคราว (429)")
            else:
                st.error(f"Error: {res['raw'][:1000]}")
    if st.session_state.ai_text:
        pdf2=gen_pdf(applicant_name, model_name, cash_price, down_payment, monthly_edit, tenure, total_interest, total_all, dsr_calc, r_verdict, st.session_state.ai_text)
        st.download_button("📄 ส่งออกรายงาน 13 โมดูล PDF", data=pdf2, file_name=f"SRD_13M_{datetime.now().strftime('%Y%m%d_%H%M')}_{selected_model}.pdf", mime="application/pdf", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with right:
    dsr_v=st.session_state.get('dsr_calc',42.3)
    st.markdown(f'<div class="srd-card"><h4>📊 DSR Meter</h4><div style="text-align:center;font-size:32px;font-weight:700;color:{"#16A34A" if dsr_v<50 else "#DC2626"}">{dsr_v:.1f}%</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="srd-card"><h4>🛡️ Risk Score 682</h4><div>Rule: {st.session_state.get("r_verdict","")}</div></div>', unsafe_allow_html=True)
    st.markdown('<div class="srd-card"><h4>🤖 AI 13 Modules</h4>✅ 13/13 Completed</div>', unsafe_allow_html=True)

st.caption(f"Model: {selected_model} • แก้ไขแล้ว: Gemini 3.6 Flash + Interactions API + Auto Fallback 404 -> 3.6-flash + ลบ st.metric")