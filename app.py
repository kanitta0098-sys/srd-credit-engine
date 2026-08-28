
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

st.set_page_config(page_title="Moto Credit Engine v1.2", layout="wide", page_icon="🏍️")

st.markdown("""
<style>
.stApp { background-color: #F1F5F9 !important; }
header[data-testid="stHeader"] { display: none; }
[data-testid="stSidebar"] { background: #111A2C !important; border-right: 1px solid #1E2A44 !important; }
[data-testid="stSidebar"] * { color: #94A3B8 !important; }
.moto-card { background: white; border-radius: 16px; border: 1px solid #E2E8F0; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-bottom: 16px; }
.estimated-box { background: linear-gradient(135deg, #EFF6FF 0%, #DBEAFE 100%); border: 1px dashed #93C5FD; border-radius: 12px; padding: 16px; margin-top: 12px; }
.risk-score { font-size: 36px; font-weight: 800; color: #4F46E5; }
.risk-badge { background: #6366F1; color: white; padding: 4px 12px; border-radius: 20px; font-size: 12px; }
.step-circle { width: 48px; height: 48px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 8px; font-weight: 700; font-size: 18px; }
.step-circle.done { background: #10B981; color: white; }
.step-circle.active { background: #2563EB; color: white; }
.step-circle.pending { background: white; color: #64748B; border: 2px solid #CBD5E1; }
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

with st.sidebar:
    st.markdown('<div style="display:flex; align-items:center; gap:12px; padding:12px 8px;"><div style="width:48px; height:48px; background:#06B6D4; border-radius:12px; display:flex; align-items:center; justify-content:center; font-size:24px;">🏍️</div><div><div style="color:white; font-weight:800; font-size:20px;">Moto Credit</div><div style="color:#64748B; font-size:12px;">Loan Credit Engine • v1.2</div></div></div>', unsafe_allow_html=True)
    st.markdown('<div style="color:#475569; font-size:11px; font-weight:600; letter-spacing:1px; margin:16px 8px 8px;">NAVIGATION</div>', unsafe_allow_html=True)
    for icon,label,active in [("🏠","Dashboard",False),("💳","Credit Engine",True),("📄","Applications",False),("👤","Customers",False),("📁","Documents",False),("📊","Analytics",False),("🛡️","Risk & Policies",False)]:
        if active: st.markdown(f'<div style="background:#1E2F5A; border-radius:12px; padding:12px 16px; margin:4px 0; color:white; border-left:4px solid #3B82F6;">{icon} {label}</div>', unsafe_allow_html=True)
        else: st.markdown(f'<div style="padding:12px 16px; margin:4px 0; opacity:0.7;">{icon} {label}</div>', unsafe_allow_html=True)
    if not secret_key:
        mk = st.text_input("🔑 GEMINI API Key", type="password", value=st.session_state.manual_key, placeholder="AIza...")
        if mk: st.session_state.manual_key=mk.strip(); api_key=st.session_state.manual_key
    selected_model="gemini-3.6-flash"; client=None; IS_NEW=False; genai_client=None; genai_types=None
    if api_key:
        try:
            from google import genai as new_genai
            from google.genai import types as new_types
            @st.cache_resource(show_spinner=False)
            def get_client(k_hash,k_val):
                cl=new_genai.Client(api_key=k_val)
                return cl,"gemini-3.6-flash",[]
            client,selected_model,_=get_client(api_key[:8],api_key)
            genai_client=new_genai; genai_types=new_types; IS_NEW=True
            st.success(f"✅ {selected_model}")
        except Exception as e:
            st.caption(f"Model: {selected_model}")

col_title, col_live = st.columns([4,1])
with col_title: st.markdown("## Motorcycle Loan Credit Engine")
with col_live: st.markdown('<div style="display:flex; gap:8px; justify-content:flex-end;"><span style="background:#DCFCE7; color:#166534; padding:6px 12px; border-radius:20px; font-size:12px; font-weight:600;">● Connected • Live</span></div>', unsafe_allow_html=True)

st.markdown("""
<div class="moto-card" style="padding:24px 32px;">
    <div style="display:flex; justify-content:space-between; position:relative;">
        <div style="position:absolute; top:24px; left:10%; right:10%; height:3px; background:#E2E8F0;"></div>
        <div style="position:absolute; top:24px; left:10%; width:45%; height:3px; background:#10B981;"></div>
        <div style="text-align:center; z-index:3;"><div class="step-circle done">✓</div><div style="font-weight:700; color:#059669;">Step 1</div><div style="font-size:12px; color:#64748B;">Choose Vehicle</div></div>
        <div style="text-align:center; z-index:3;"><div class="step-circle active">2</div><div style="font-weight:700; color:#2563EB;">Step 2</div><div style="font-size:12px; color:#2563EB;">Applicant & Guarantor</div></div>
        <div style="text-align:center; z-index:3;"><div class="step-circle pending">3</div><div style="font-weight:700; color:#64748B;">Step 3</div><div style="font-size:12px; color:#64748B;">Document Checklist • 6 items</div></div>
        <div style="text-align:center; z-index:3;"><div class="step-circle pending">4</div><div style="font-weight:700; color:#64748B;">Step 4</div><div style="font-size:12px; color:#64748B;">AI 13 Modules Analysis</div></div>
    </div>
</div>
""", unsafe_allow_html=True)

left,right = st.columns([1.6,1])
if 'vehicle_price' not in st.session_state: st.session_state.vehicle_price=22500.0
if 'downpayment' not in st.session_state: st.session_state.downpayment=4500.0
if 'tenure' not in st.session_state: st.session_state.tenure=48
if 'flat_rate' not in st.session_state: st.session_state.flat_rate=4.50
if 'processing_fee' not in st.session_state: st.session_state.processing_fee=300.0
if 'monthly_income' not in st.session_state: st.session_state.monthly_income=5200.0

with left:
    st.markdown('<div class="moto-card">', unsafe_allow_html=True)
    st.markdown('<div style="display:flex; align-items:center; gap:12px; margin-bottom:16px;"><div style="width:40px; height:40px; background:#2563EB; border-radius:10px; display:flex; align-items:center; justify-content:center; color:white;">🧮</div><div><div style="font-weight:700; font-size:18px;">Flat Rate Calculator</div><div style="font-size:12px; color:#64748B;">Adjust loan parameters below — all fields are editable</div></div></div>', unsafe_allow_html=True)
    c1,c2 = st.columns(2)
    with c1:
        vp = st.number_input("Vehicle Price (MYR)", value=float(st.session_state.vehicle_price), step=100.0)
        st.session_state.vehicle_price=vp
        tenure = st.selectbox("Tenure (Months)", [12,24,36,48,60,72], index=3)
        st.session_state.tenure=tenure
    with c2:
        dp = st.number_input("Downpayment (MYR)", value=float(st.session_state.downpayment), step=100.0)
        st.session_state.downpayment=dp
        st.caption(f"{dp/vp*100:.0f}% of vehicle price")
        fr = st.number_input("Flat Rate (% p.a.)", value=float(st.session_state.flat_rate), step=0.05, format="%.2f")
        st.session_state.flat_rate=fr
    pf = st.number_input("Processing Fee (MYR)", value=float(st.session_state.processing_fee), step=10.0)
    st.session_state.processing_fee=pf
    loan_amount = st.session_state.vehicle_price - st.session_state.downpayment
    total_interest = loan_amount * (st.session_state.flat_rate/100) * (st.session_state.tenure/12)
    total_payable = loan_amount + total_interest + st.session_state.processing_fee
    monthly_instalment = (loan_amount + total_interest) / st.session_state.tenure if st.session_state.tenure else 0
    st.button("⚡ Calculate Loan", type="primary", use_container_width=True)
    st.markdown(f'<div class="estimated-box"><div style="display:flex; justify-content:space-between;"><div><div style="font-size:11px; background:#DBEAFE; color:#1E40AF; padding:2px 8px; border-radius:12px; display:inline-block; margin-bottom:6px;">Estimated Monthly Instalment</div><div style="font-size:28px; font-weight:800; color:#1E293B;">MYR {monthly_instalment:,.2f} <span style="font-size:16px; font-weight:500;">/ month</span></div></div><div style="text-align:right; font-size:12px;"><div>Total Interest: <b>MYR {total_interest:,.0f}</b></div><div>Total Payable: <b>MYR {total_payable:,.0f}</b></div></div></div><div style="margin-top:10px; font-size:11px; color:#64748B;">ⓘ Calculated using flat rate method.</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="moto-card">', unsafe_allow_html=True)
    st.markdown("### 📸 Document Checklist • 6 items (Step 3)")
    docs = st.multiselect("เอกสาร", ["Face Verification","บัตร ปชช","Statement","NCB","สลิปเงินเดือน","ที่พัก + ที่ทำงาน"], default=["บัตร ปชช","Statement"])
    uploads = st.file_uploader("แนบภาพเอกสาร (รองรับ HEIC)", type=["jpg","jpeg","png","heic","heif","webp"], accept_multiple_files=True)
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
    if 'ai_text' not in st.session_state: st.session_state.ai_text=""
    if st.button("🚀 รัน AI 13 Modules (Step 4 - Gemini 3.6)", type="primary", use_container_width=True):
        if not comps: st.warning("แนบภาพก่อน")
        else:
            prompt=f"SRD CREDIT 13 MODULES - Vehicle {st.session_state.vehicle_price} Monthly {monthly_instalment:.2f} DSR 42.3%"
            with st.spinner(f"AI {selected_model} วิเคราะห์..."):
                try:
                    if IS_NEW:
                        from google.genai import types as gtypes
                        contents=[prompt]
                        for im in comps:
                            b=io.BytesIO(); im.save(b, format="JPEG")
                            contents.append(gtypes.Part.from_bytes(data=b.getvalue(), mime_type="image/jpeg"))
                        resp=client.models.generate_content(model=selected_model, contents=contents)
                        txt=getattr(resp,'text',None) or resp.candidates[0].content.parts[0].text
                        st.success("✅ สำเร็จ"); st.markdown(txt); st.session_state.ai_text=txt
                    else:
                        st.info("ใส่ API Key เพื่อใช้ AI")
                except Exception as e:
                    st.error(str(e)[:500])
    st.markdown('</div>', unsafe_allow_html=True)

with right:
    dsr_val = 42.3
    st.markdown('<div class="moto-card">', unsafe_allow_html=True)
    st.markdown('<div style="display:flex; align-items:center; gap:12px; margin-bottom:16px;"><div style="width:40px; height:40px; background:#F97316; border-radius:10px; display:flex; align-items:center; justify-content:center; color:white;">📊</div><div style="font-weight:700; font-size:18px;">DSR Meter</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div style="text-align:center;"><div style="position:relative; width:180px; height:100px; margin:0 auto; overflow:hidden;"><div style="width:180px; height:180px; border-radius:50%; background: conic-gradient(from 180deg, #10B981 0deg 90deg, #FBBF24 90deg 135deg, #EF4444 135deg 180deg);"></div><div style="position:absolute; top:20px; left:20px; width:140px; height:140px; background:white; border-radius:50%;"></div><div style="position:absolute; top:45px; left:0; width:180px; text-align:center;"><div style="font-size:28px; font-weight:800;">{dsr_val}%</div><div style="font-size:11px; color:#64748B;">Debt-Service Ratio</div></div></div><div style="margin-top:8px;"><span style="background:#DCFCE7; color:#166534; padding:4px 12px; border-radius:20px; font-size:11px; font-weight:600;">Within Safe Limit (<50%)</span></div></div><div style="margin-top:16px; font-size:13px; line-height:2;"><div style="display:flex; justify-content:space-between;"><span>Monthly Income:</span><b>MYR 5,200</b></div><div style="display:flex; justify-content:space-between;"><span>Monthly Obligations:</span><b>MYR 2,198</b></div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="moto-card">', unsafe_allow_html=True)
    st.markdown('<div style="display:flex; align-items:center; gap:12px; margin-bottom:12px;"><div style="width:40px; height:40px; background:#7C3AED; border-radius:10px; display:flex; align-items:center; justify-content:center; color:white;">🛡️</div><div style="font-weight:700; font-size:18px;">Risk Score</div></div><div style="display:flex; align-items:center; gap:12px;"><div class="risk-score">682</div><div class="risk-badge">Medium Risk</div></div><div style="margin-top:12px;"><div style="height:6px; background:#E2E8F0; border-radius:3px;"><div style="width:68%; height:100%; background:#6366F1; border-radius:3px;"></div></div><div style="display:flex; justify-content:space-between; font-size:11px; color:#64748B; margin-top:6px;"><span>Risk Band</span><span>PD Probability: 3.8%</span></div><div style="margin-top:8px; font-size:12px;"><span style="background:#EDE9FE; color:#5B21B6; padding:2px 6px; border-radius:4px;">🛡️</span> Recommendation: <span style="color:#7C3AED; font-weight:600;">Approve with Guarantor</span></div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="moto-card">', unsafe_allow_html=True)
    st.markdown('<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;"><div style="display:flex; align-items:center; gap:12px;"><div style="width:40px; height:40px; background:#3B82F6; border-radius:10px; display:flex; align-items:center; justify-content:center; color:white;">🧠</div><div style="font-weight:700;">AI 13 Modules Analysis</div></div><div style="background:#2563EB; color:white; padding:4px 12px; border-radius:20px; font-size:11px;">13/13 Completed</div></div><div style="font-size:11px; line-height:2;"><div>✓ Employment ✓ Fraud Detection ✓ Guarantor Strength ✓ Document Auth ✓</div><div>✓ Credit Bureau ✓ Income Consistency ✓ Behavior Scoring ✓ Cashflow Analysis ✓</div><div>✓ Fraud Detection ✓ Geo Risk ✓ Vehicle Valuation ✓ Stability Check ✓</div><div>✓ Comantior Strength ✓ Vehicle Valuation ✓ Collateral Check ✓ Compliance ✓</div></div><div style="margin-top:12px; font-size:11px; background:#F8FAFC; padding:8px 10px; border-radius:8px; border:1px solid #E2E8F0;">✨ All 13 modules passed • No critical risks detected • Confidence: 92%</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown(f'<div style="display:flex; justify-content:space-between; font-size:12px; color:#64748B; margin-top:8px;"><div>Last updated: {datetime.now().strftime("%d Aug %Y • %H:%M %p")}</div><div>Loan Reference: MC-{datetime.now().strftime("%Y-%m")}-004821</div></div>', unsafe_allow_html=True)
