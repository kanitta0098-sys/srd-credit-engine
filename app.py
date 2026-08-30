
import streamlit as st
import os, io, pandas as pd
from datetime import datetime
from PIL import Image
try:
    import pillow_heif; pillow_heif.register_heif_opener()
except: pass
def _compress_mobile(img, max_side=1280, max_bytes=1200000):
    img=img.convert("RGB")
    if max(img.size)>max_side: img.thumbnail((max_side,max_side), Image.LANCZOS)
    for q in [75,65,55,40]:
        b=io.BytesIO(); img.save(b, format="JPEG", quality=q, optimize=True)
        if b.tell()<=max_bytes: b.seek(0); return Image.open(b)
    b.seek(0); return Image.open(b)

st.set_page_config(page_title="SRD Credit Engine", layout="wide", page_icon="🏍️")

# 1
st.title("🏍️ SRD Credit Engine")
st.caption("ฟอร์มว่าง • คำนวณ Flat Rate อัตโนมัติ • AI 13 โมดูล")

HISTORY_FILE="srd_credit_assessment_history.csv"
def save_record(rec):
    df=pd.DataFrame([rec])
    if not os.path.exists(HISTORY_FILE): df.to_csv(HISTORY_FILE, index=False, encoding='utf-8-sig')
    else: df.to_csv(HISTORY_FILE, mode='a', header=False, index=False, encoding='utf-8-sig')

with st.sidebar:
    st.header("⚙️ การตั้งค่า")
    api_key_input=st.text_input("GEMINI API Key", value=st.secrets.get("GEMINI_API_KEY","") if hasattr(st,'secrets') else "", type="password")
    selected_model=None; usable=[]
    if api_key_input:
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key_input.strip())
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    usable.append(m.name.replace("models/",""))
            if usable:
                selected_model=st.selectbox("🤖 โมเดล AI", usable, index=0)
        except Exception as e: st.error(str(e))
    if st.button("🔄 รีเซ็ตฟอร์มว่างทั้งหมด", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# 2
st.subheader("🏍️ ข้อมูลรถและคำนวณค่างวด Flat Rate")
st.caption("กรอกข้อมูลแล้วระบบจะคำนวณค่างวดแบบ Flat Rate ให้อัตโนมัติ • Monthly / Total Debt แก้ได้เพื่อปัดขึ้น/ลง")
c1,c2,c3,c4=st.columns(4)
with c1:
    brand_model=st.text_input("ยี่ห้อ/รุ่น", value="", placeholder="[ว่าง]")
    cash_price=st.number_input("ราคาเงินสด", value=0.0, step=100.0)
    down_payment=st.number_input("ดาวน์", value=0.0, step=100.0)
with c2:
    financing_input=st.number_input("ยอดจัด (ถ้าว่าง = ราคาเงินสด - ดาวน์)", value=0.0, step=100.0)
    flat_rate=st.number_input("Flat % ต่อเดือน", value=0.0, step=0.05, format="%.2f")
    term=st.selectbox("Term เดือน", [12,24,36,48,60], index=3)
with c3:
    monthly_editable=st.number_input("Monthly ⭐ แก้ได้เพื่อปัดขึ้น/ลง", value=0.0, step=1.0)
    total_debt_editable=st.number_input("Total Debt ✏️ แก้ได้", value=0.0, step=100.0)
with c4:
    reg_fee=st.number_input("ค่าทะเบียน/ประกันรถหาย/อื่นๆ", value=0.0, step=100.0)
    total_now=reg_fee+down_payment

financing=financing_input if financing_input>0 else (cash_price-down_payment if cash_price>0 else 0)
if financing>0 and flat_rate>0:
    interest_total=financing*(flat_rate/100)*term
    total_debt_calc=financing+interest_total
    monthly_calc=total_debt_calc/term if term else 0
else:
    interest_total=0; total_debt_calc=total_debt_editable; monthly_calc=monthly_editable

monthly_final=monthly_editable if monthly_editable>0 else monthly_calc
total_debt_final=total_debt_editable if total_debt_editable>0 else total_debt_calc
if monthly_editable>0 and total_debt_editable==0 and term>0:
    total_debt_final=monthly_editable*term

st.info(f"💡 คำนวณ Flat Rate: ยอดจัด {financing:,.0f} × {flat_rate:.2f}% × {term} = ดอกเบี้ยรวม {interest_total:,.0f} | ยอดหนี้รวม {total_debt_final:,.0f} | ค่างวด {monthly_final:,.2f}")
st.warning(f"Initial Payment Summary ดึงจากเงินดาวน์ + ค่าทะเบียน = ออกรถรวม: {down_payment:,.0f} + {reg_fee:,.0f} = {total_now:,.0f}")

# 3
st.subheader("🏍️ ข้อมูลผู้เช่าซื้อ")
a1,a2=st.columns(2)
with a1:
    f_name=st.text_input("ชื่อ", value="", placeholder="[ว่าง]")
    l_name=st.text_input("สกุล", value="", placeholder="[ว่าง]")
    age=st.number_input("อายุ", min_value=0, max_value=80, value=0)
    job=st.text_input("อาชีพ", value="", placeholder="[ว่าง]")
    sup=st.text_input("หัวหน้างาน", value="", placeholder="[ว่าง]")
    phone=st.text_input("เบอร์โทร", value="", placeholder="[ว่าง]")
with a2:
    residence=st.selectbox("ที่พัก", ["[ว่าง]","บ้านตนเอง/ปลอดภาระ","บ้านตนเอง/ติดผ่อน","บ้านเช่า/หอพัก","บ้านญาติ"])
    salary=st.number_input("เงินเดือน", value=0, step=500)
    extra=st.number_input("รายได้เสริม", value=0, step=500)
    debt=st.number_input("หนี้เดิมต่อเดือน", value=0)
    living=st.number_input("ค่าใช้ชีวิต", value=0)

total_inc=salary+extra
total_bur=debt+living+monthly_final
dsr=(total_bur/total_inc*100) if total_inc>0 else 0
c1,c2,c3=st.columns(3)
with c1: st.metric("รายได้รวม", f"{total_inc:,.0f}")
with c2: st.metric("ภาระรวม", f"{total_bur:,.0f}")
with c3: st.metric("DSR %", f"{dsr:.1f}%")

# 4
st.subheader("🏍️ บุคคลอ้างอิง")
r1,r2=st.columns(2)
with r1:
    ref1_name=st.text_input("อ้างอิง 1: ชื่อ-สกุล", value="", placeholder="[ว่าง]")
    ref1_phone=st.text_input("อ้างอิง 1: เบอร์โทร", value="", placeholder="[ว่าง]")
    ref1_rel=st.text_input("อ้างอิง 1: ความสัมพันธ์", value="", placeholder="[ว่าง]")
with r2:
    ref2_name=st.text_input("อ้างอิง 2: ชื่อ-สกุล", value="", placeholder="[ว่าง]")
    ref2_phone=st.text_input("อ้างอิง 2: เบอร์โทร", value="", placeholder="[ว่าง]")
    ref2_rel=st.text_input("อ้างอิง 2: ความสัมพันธ์", value="", placeholder="[ว่าง]")

# 5
st.subheader("🏍️ คู่สมรส")
spouse_choice=st.radio("สถานะคู่สมรส", ["1 ไม่มีคู่สมรส","2 มีคู่สมรส"], horizontal=True)
spouse_summary="ไม่มีคู่สมรส"
if spouse_choice=="2 มีคู่สมรส":
    sp1,sp2,sp3=st.columns(3)
    with sp1:
        sp_name=st.text_input("1. ชื่อ-สกุล คู่สมรส", value="", placeholder="[ว่าง]")
        sp_age=st.number_input("2. อายุคู่สมรส", min_value=0, max_value=80, value=0)
    with sp2:
        sp_year=st.number_input("3. จำนวนปีที่สมรส", min_value=0, value=0)
        sp_child=st.number_input("4. มีบุตรกี่คน", min_value=0, value=0)
    with sp3:
        sp_income=st.number_input("5. รายได้คู่สมรส", value=0, step=500)
        sp_job=st.text_input("6. อาชีพคู่สมรส", value="", placeholder="[ว่าง]")
    spouse_summary=f"{sp_name} อายุ {sp_age} สมรส {sp_year} ปี บุตร {sp_child} คน รายได้ {sp_income:,.0f} อาชีพ {sp_job}"
    st.success(f"สรุป: {spouse_summary}")

# 6
st.subheader("🏍️ ผู้ค้ำประกัน")
guar_choice=st.radio("สถานะผู้ค้ำประกัน", ["1 ไม่มีผู้ค้ำประกัน","2 มีผู้ค้ำประกัน"], horizontal=True)
g_text="ไม่มีผู้ค้ำประกัน"
if guar_choice=="2 มีผู้ค้ำประกัน":
    g1,g2,g3=st.columns(3)
    with g1:
        g_name=st.text_input("1. ชื่อ-สกุล ผู้ค้ำ", value="", placeholder="[ว่าง]")
        g_age=st.number_input("2. อายุ ผู้ค้ำ", min_value=0, max_value=80, value=0)
    with g2:
        g_job=st.text_input("3. อาชีพผู้ค้ำประกัน", value="", placeholder="[ว่าง]")
        g_income=st.number_input("4. รายได้ผู้ค้ำประกัน", value=0, step=1000)
    with g3:
        g_phone=st.text_input("5. เบอร์โทร ผู้ค้ำ", value="", placeholder="[ว่าง]")
    g_text=f"{g_name} อายุ {g_age} อาชีพ {g_job} รายได้ {g_income:,.0f} เบอร์ {g_phone}"
    st.success(f"สรุป: {g_text}")

# 7
st.subheader("🏍️ เช็คลิสต์เอกสาร 6 รายการ")
d1=st.checkbox("1. สำเนาบัตรประชาชน")
d2=st.checkbox("2. ทะเบียนบ้าน")
d3=st.checkbox("3. สลิปเงินเดือน 3 เดือน")
d4=st.checkbox("4. สเตทเม้นท์ 6 เดือน")
d5=st.checkbox("5. ใบจดทะเบียนการค้า")
d6=st.checkbox("6. รูปถ่ายที่พัก / หมุด Google Maps")
attached=[]
for name,chk in [("บัตร ปชช",d1),("ทะเบียนบ้าน",d2),("สลิป 3 เดือน",d3),("สเตทเม้นท์ 6 เดือน",d4),("ใบจดทะเบียนการค้า",d5),("รูปที่พัก",d6)]:
    if chk: attached.append(name)
if attached:
    st.markdown(" ".join([f"`{a} x`" for a in attached]))
uploaded=st.file_uploader("Upload เอกสาร", type=["png","jpg","jpeg","heic","heif","webp"], accept_multiple_files=True)
st.caption("200MB per file • JPG, PNG, HEIC, HEIF, WEBP")
st.caption("This app would like to use your camera Learn how to allow access")
cam=st.camera_input("Take Photo")
workplace=st.text_input("📌 พิกัด Google Maps", value="", placeholder="[ว่าง]")

# 8
st.subheader("🏍️ วิเคราะห์ 13 โมดูลด้วย Ai")
colA,colB=st.columns(2)
with colA:
    st.metric("DSR Meter - ตรวจสอบรายได้ รายจ่าย คนซื้อ คู่สมรส คนค้ำประกัน", f"{dsr:.1f}%")
with colB:
    risk=int(min(100, dsr*1.2)) if dsr>0 else 0
    st.metric("Risk Score - ตรวจตามช่องที่สอดคล้อง % ตรวจตามข้อมูลที่ใส่", f"{risk}/100")

if uploaded or cam or st.checkbox("✅ ทดสอบโดยไม่ต้องอัปโหลด"):
    if st.button("🚀 รัน SRD Credit Investigation Engine 13 Modules เต็มระบบ v1.3", type="primary", use_container_width=True):
        if not api_key_input or not selected_model:
            st.error("กรุณากรอก API Key ในแถบด้านซ้าย")
        else:
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key_input.strip())
                imgs=[]
                if uploaded:
                    for f in uploaded: imgs.append(_compress_mobile(Image.open(f)))
                if cam: imgs.append(_compress_mobile(Image.open(cam)))
                prompt=f"SRD Credit Engine - รถ: {brand_model} ราคา {cash_price} ดาวน์ {down_payment} ยอดจัด {financing} Flat {flat_rate}% Term {term} Monthly {monthly_final} TotalDebt {total_debt_final} ผู้เช่าซื้อ: {f_name} {l_name} อายุ {age} อาชีพ {job} หัวหน้างาน {sup} เบอร์ {phone} ที่พัก {residence} รายได้รวม {total_inc} ภาระรวม {total_bur} DSR {dsr:.1f}% อ้างอิง: {ref1_name} {ref1_rel} / {ref2_name} {ref2_rel} คู่สมรส: {spouse_summary} ผู้ค้ำ: {g_text} เอกสาร: {', '.join(attached)}"
                with st.spinner(f"AI ({selected_model}) วิเคราะห์ 13 โมดูล..."):
                    model_ai=genai.GenerativeModel(selected_model)
                    if imgs: resp=model_ai.generate_content([prompt]+imgs)
                    else: resp=model_ai.generate_content(prompt)
                    save_record({"Timestamp":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"BrandModel":brand_model,"Monthly":monthly_final,"Applicant":f"{f_name} {l_name}","DSR":f"{dsr:.1f}%","Spouse":spouse_summary,"Guarantor":g_text})
                    st.success("บันทึกและวิเคราะห์เสร็จสิ้น")
                    st.markdown(resp.text)
            except Exception as e:
                st.error(f"Error: {e}")
else:
    st.info("อัปโหลดภาพเอกสารหรือถ่ายภาพก่อนรัน AI")
