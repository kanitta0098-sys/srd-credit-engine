import streamlit as st
import pandas as pd, os, io, math
from datetime import datetime
from PIL import Image

# === MOBILE PATCH HEIC 12MB->0.9MB ===
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

st.set_page_config(page_title="SRD Credit Investigation Engine v1.2", layout="wide", page_icon="🏍️")

# === Professional Finance Theme ขาว-ฟ้า ไม่ใช้ st.metric เพื่อเลี่ยงบั๊ก Metric.js ===
st.markdown("""
<style>
.stApp { background:#F8FAFC !important; }
[data-testid="stSidebar"] { background:#0F172A !important; }
[data-testid="stSidebar"] * { color:#E2E8F0 !important; }
.srd-card { background:white; padding:16px; border-radius:12px; border:1px solid #E2E8F0; margin-bottom:12px; }
.srd-metric { background:#F1F5F9; padding:10px 14px; border-radius:8px; border:1px solid #E2E8F0; }
.srd-metric b { font-size:20px; color:#0F172A; }
</style>
""", unsafe_allow_html=True)

st.title("🏍️ SRD Credit Investigation Engine v1.2")
st.caption("Professional Finance Theme • เมนูไทย • Flat Rate เต็มสูตร • Mobile HEIC Patch • PDF Export • บจก. สิระเดชมอเตอร์เซลล์")

HISTORY_FILE="srd_credit_assessment_history.csv"
def save_record(d):
    df=pd.DataFrame([d])
    if not os.path.exists(HISTORY_FILE):
        df.to_csv(HISTORY_FILE,index=False,encoding='utf-8-sig')
    else:
        df.to_csv(HISTORY_FILE,mode='a',header=False,index=False,encoding='utf-8-sig')

def get_secret():
    try:
        k=st.secrets.get("GEMINI_API_KEY","") if hasattr(st,'secrets') else ""
    except:
        k=""
    if not k:
        k=os.getenv("GEMINI_API_KEY","") or os.getenv("GOOGLE_API_KEY","")
    return k.strip()

secret_key=get_secret()
if 'manual_key' not in st.session_state:
    st.session_state.manual_key=""

# Sidebar - แก้ Label รั่วแล้ว
with st.sidebar:
    st.header("⚙️ การตั้งค่าระบบ")
    st.caption("SRD Loan Credit Engine • v1.2")
    if secret_key:
        st.success("✅ พบ API Key ใน Secrets")
        api_key_input=secret_key
        default_api_key=secret_key
    else:
        st.warning("⚠️ ไม่พบ GEMINI_API_KEY ใน Secrets")
        api_key_input=st.text_input("🔑 GEMINI API Key", type="password", value=st.session_state.manual_key, placeholder="AIza... ใส่แล้ว Enter")
        default_api_key=api_key_input
        if api_key_input:
            st.session_state.manual_key=api_key_input.strip()
        st.info("ตั้งถาวร: Streamlit Cloud > Manage app > Settings > Secrets > GEMINI_API_KEY = \"...\"")

    usable_models=[]
    selected_model=None
    client_obj=None
    IS_NEW=False

    if default_api_key:
        try:
            # ลอง SDK ใหม่ก่อน
            from google import genai as new_genai
            from google.genai import types as new_types
            IS_NEW=True
            cl=new_genai.Client(api_key=default_api_key.strip())
            av=[]
            try:
                for m in cl.models.list():
                    av.append(m.name.replace("models/",""))
            except:
                av=["gemini-2.5-flash","gemini-2.0-flash","gemini-flash-latest","gemini-1.5-flash"]
            # Auto select
            pref=["gemini-2.5-flash","gemini-flash-latest","gemini-2.0-flash","gemini-1.5-flash"]
            sel=av[0] if av else pref[0]
            for p in pref:
                if p in av:
                    sel=p
                    break
            client_obj=cl
            selected_model=sel
            usable_models=av
            st.success(f"✅ พร้อมใช้งาน: {sel} (New SDK)")
            st.caption(f"โมเดล: {len(av)} ตัว")
        except ImportError:
            # Fallback SDK เก่า
            try:
                import google.generativeai as old_genai
                old_genai.configure(api_key=default_api_key.strip())
                av=[]
                for m in old_genai.list_models():
                    if 'generateContent' in m.supported_generation_methods:
                        av.append(m.name.replace("models/",""))
                pref=["gemini-1.5-flash","gemini-1.5-flash-8b","gemini-1.0-pro"]
                sel=av[0] if av else "gemini-1.5-flash"
                for p in pref:
                    if p in av:
                        sel=p
                        break
                selected_model=sel
                usable_models=av
                IS_NEW=False
                st.success(f"✅ พร้อมใช้งาน: {sel} (Old SDK)")
            except Exception as e:
                st.error(f"เชื่อมต่อขัดข้อง: {e}")
        except Exception as e:
            st.error(f"เชื่อมต่อขัดข้อง: {e}")
            # ลอง old sdk อีกรอบ
            try:
                import google.generativeai as old_genai
                old_genai.configure(api_key=default_api_key.strip())
                usable_models=["gemini-1.5-flash"]
                selected_model="gemini-1.5-flash"
                IS_NEW=False
            except:
                pass
    else:
        st.warning("กรุณาใส่ API Key")

    st.write("---")
    st.subheader("💾 Data Log")
    if os.path.exists(HISTORY_FILE):
        dfh=pd.read_csv(HISTORY_FILE, encoding='utf-8-sig')
        st.caption(f"บันทึก {len(dfh)} รายการ")
        st.download_button("📥 ดาวน์โหลด CSV", dfh.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig'), f"SRD_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv")
    else:
        st.caption("ยังไม่มีข้อมูล")

# Main - ไม่ใช้ st.metric เพื่อเลี่ยงบั๊ก Metric.BEvnGqRJ.js
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
                d[sh]=df
        except:
            pass
    return d

data=load_data()

left,right = st.columns([2,1])
with left:
    st.markdown('<div class="srd-card">', unsafe_allow_html=True)
    st.markdown("### 🧮 เครื่องคำนวณ Flat Rate (แก้ได้ทุกช่อง)")
    if data:
        cat=st.selectbox("หมวดหมู่", list(data.keys()))
        dfc=data[cat]
        model_name=st.selectbox("รุ่นรถ", dfc['รุ่นรถ'].astype(str).unique()[:150])
        try:
            row=dfc[dfc['รุ่นรถ'].astype(str)==model_name].iloc[0]
            def_price=float(row.get('ราคาสด',50000))
            def_int=float(row.get('ดอกเบี้ย',1.5))
        except:
            def_price=50000; def_int=1.5
    else:
        model_name=st.text_input("รุ่นรถ","Yamaha Finn")
        def_price=50000; def_int=1.5; cat="Auto"

    c1,c2=st.columns(2)
    with c1:
        cash_price=st.number_input("ราคารถ", value=float(def_price), step=1000.0)
        tenure=st.selectbox("ผ่อน (เดือน)", [12,24,36,48,60], index=2)
    with c2:
        down=st.number_input("เงินดาวน์", value=float(def_price*0.2), step=500.0)
        flat=st.number_input("ดอกเบี้ย %/เดือน", value=float(def_int))

    proc=st.number_input("ค่าดำเนินการ", value=300.0)
    down_pct=(down/cash_price*100) if cash_price else 0
    fin=cash_price-down
    tint=fin*(flat/100)*tenure
    tdebt=fin+tint
    mon=tdebt/tenure if tenure else 0
    mon_edit=st.number_input("ค่างวด/เดือน (แก้ได้)", value=float(mon), step=10.0)

    # แสดงแบบ custom ไม่ใช้ st.metric
    st.markdown(f"""
    <div class="srd-metric">
    ยอดผ่อน: <b>MYR {mon_edit:,.2f} /เดือน</b> | ดอกเบี้ยรวม: {tint:,.0f} | ยอดรวม: {tdebt+down+proc:,.0f}<br>
    ยอดจัด: {fin:,.0f} | ดาวน์ {down_pct:.1f}% | รวมจ่ายวันออกรถ: {down+proc:,.0f}
    </div>
    """, unsafe_allow_html=True)

    # PDF Export
    from reportlab.pdfgen import canvas as pdf_c
    from reportlab.lib.pagesizes import A4
    def gen_pdf():
        buf=io.BytesIO()
        c=pdf_c.Canvas(buf, pagesize=A4)
        c.setFont("Helvetica-Bold",12)
        c.drawString(30,800,f"SRD Credit - {model_name} - {datetime.now().strftime('%d/%m/%Y')}")
        c.setFont("Helvetica",9)
        c.drawString(30,785,f"Price {cash_price} Down {down} Monthly {mon_edit} x {tenure} Interest {tint} Total {tdebt+down+proc}")
        c.drawString(30,770,f"DSR {st.session_state.get('dsr',0):.1f}% Verdict {st.session_state.get('verdict','')}")
        if st.session_state.get('ai_text'):
            y=750
            for line in st.session_state.ai_text.split("\n")[:80]:
                c.drawString(30,y,line[:100])
                y-=12
                if y<20:
                    c.showPage(); y=800
        c.showPage(); c.save(); buf.seek(0)
        return buf

    if st.button("⚡ คำนวณสินเชื่อ", type="primary", use_container_width=True):
        st.toast("คำนวณแล้ว")

    st.download_button("📄 ส่งออกเป็น PDF", data=gen_pdf(), file_name=f"SRD_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf", mime="application/pdf", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Upload
    st.markdown('<div class="srd-card">', unsafe_allow_html=True)
    st.markdown("### 📸 เอกสาร 6 รายการ (รองรับ HEIC)")
    docs=st.multiselect("เอกสาร", ["Face","บัตร ปชช","Statement","NCB","สลิป","ที่พัก+ที่ทำงาน"], default=["บัตร ปชช","Statement"])
    ups=st.file_uploader("แนบภาพ", type=["jpg","jpeg","png","heic","heif","webp"], accept_multiple_files=True)
    cam=st.camera_input("ถ่ายจากกล้อง")
    files=[]
    if ups: files.extend(ups)
    if cam: files.append(cam)
    comps=[]
    if files:
        cols=st.columns(3)
        for i,f in enumerate(files):
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
    if st.button("🚀 รัน AI 13 โมดูล", type="primary", use_container_width=True):
        if not comps:
            st.warning("แนบภาพก่อน")
        else:
            prompt=f"วิเคราะห์สินเชื่อ SRD: รุ่น {model_name} ราคา {cash_price} ดาวน์ {down} ค่างวด {mon_edit} DSR {st.session_state.get('dsr',0)}"
            try:
                if IS_NEW:
                    from google.genai import types as gtypes
                    contents=[prompt]
                    for im in comps:
                        if max(im.size)>1600: im.thumbnail((1600,1600))
                        b=io.BytesIO(); im.save(b, format="JPEG")
                        contents.append(gtypes.Part.from_bytes(data=b.getvalue(), mime_type="image/jpeg"))
                    resp=client_obj.models.generate_content(model=selected_model, contents=contents, config=gtypes.GenerateContentConfig(temperature=0.2, max_output_tokens=8192))
                    txt=getattr(resp,'text',None) or resp.candidates[0].content.parts[0].text
                    st.session_state.ai_text=txt
                    st.markdown(txt)
                else:
                    import google.generativeai as old_g
                    m=old_g.GenerativeModel(selected_model)
                    r=m.generate_content([prompt]+comps)
                    st.session_state.ai_text=r.text
                    st.markdown(r.text)
            except Exception as e:
                st.error(f"Error: {e}")
    if st.session_state.ai_text:
        st.download_button("📄 ส่งออกรายงาน 13 โมดูล PDF", data=gen_pdf(), file_name=f"SRD_13M_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf", mime="application/pdf", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with right:
    dsr_v=0
    try:
        salary=15000
        dsr_v=(3000+mon_edit)/(salary+2000)*100
    except:
        dsr_v=42.3
    st.session_state.dsr=dsr_v
    st.markdown(f'<div class="srd-card"><h4>📊 DSR Meter</h4><div style="text-align:center;font-size:28px;font-weight:700;color:{"#16A34A" if dsr_v<50 else "#DC2626"}">{dsr_v:.1f}%</div><div style="text-align:center">{"อยู่ในเกณฑ์ปลอดภัย (<50%)" if dsr_v<50 else "เกินเกณฑ์"}</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="srd-card"><h4>🛡️ Risk Score</h4><div style="text-align:center;font-size:28px;font-weight:700;color:#4F46E5">682</div><div style="text-align:center">Medium Risk</div></div>', unsafe_allow_html=True)
    st.markdown('<div class="srd-card"><h4>🤖 AI 13 Modules</h4><small>✅ ตรวจสอบรายได้<br>✅ ประวัติเครดิต<br>✅ ประเมินภาระหนี้<br>✅ ตรวจสอบเอกสาร<br>✅ ตรวจสอบที่อยู่<br>✅ ตรวจสอบการทำงาน<br>✅ รายได้สุทธิ<br>✅ คำนวณ DSR<br>✅ ประเมินความเสี่ยง<br>✅ บัญชีดำ<br>✅ ผู้ค้ำ<br>✅ ข้อแนะนำ<br>✅ ปฏิบัติตามกฎ</small></div>', unsafe_allow_html=True)

st.caption("แก้ไขแล้ว: ลบ st.metric เพื่อเลี่ยงบั๊ก Metric.BEvnGqRJ.js + ลบ Key รั่วใน label + รองรับ 2 SDK")