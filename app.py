
import os, io, pandas as pd, streamlit as st
from datetime import datetime
from PIL import Image
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except: pass

def _compress_mobile(img, max_side=1280, max_bytes=1200000):
    img=img.convert("RGB")
    if max(img.size)>max_side:
        img.thumbnail((max_side,max_side), Image.LANCZOS)
    for q in [75,65,55,40]:
        b=io.BytesIO(); img.save(b, format="JPEG", quality=q, optimize=True)
        if b.tell()<=max_bytes: b.seek(0); return Image.open(b)
    b.seek(0); return Image.open(b)

st.set_page_config(page_title="SRD Credit Engine v1.7.2 Full Complete", layout="wide", page_icon="🛵")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;600;700;800&display=swap');
html, body, [class*="css"] { font-family:'Sarabun', sans-serif !important; }
.stApp { background:#0F172A !important; }
header { visibility:hidden; }
[data-testid="stSidebar"] { background:#020617 !important; border-right:1px solid #1E293B !important; }
.moto-card { background:#1E293B !important; border:2px solid #334155 !important; border-radius:16px; padding:18px; margin-bottom:14px; max-width:1320px; margin:0 auto; }
.yellow-summary { background:#FBBF24 !important; border-radius:12px; padding:14px 16px; color:#000 !important; font-weight:800; margin:10px 0; border:2px solid #F59E0B; }
.green-box { background:#065F46 !important; border:2px solid #10B981 !important; border-radius:12px; padding:12px; text-align:center; }
.yellow-box { background:#92400E !important; border:2px solid #FBBF24 !important; border-radius:12px; padding:12px; text-align:center; }
.white-box { background:#F1F5F9 !important; border:2px solid #94A3B8 !important; border-radius:12px; padding:12px; text-align:center; color:#000 !important; }
.tag-red { background:#DC2626 !important; color:white !important; border-radius:8px; padding:4px 10px; font-weight:700; font-size:12px; display:inline-block; margin:2px; }
.dsr-gauge { background:radial-gradient(circle at 50% 60%, #1E40AF 0%, #0F172A 70%); border:2px solid #3B82F6; border-radius:50%; width:160px; height:160px; display:flex; flex-direction:column; align-items:center; justify-content:center; margin:auto; }
.block-container { max-width:1320px !important; }
</style>
""", unsafe_allow_html=True)

HISTORY_FILE="srd_credit_assessment_history.csv"
def save_record(rec):
    df=pd.DataFrame([rec])
    if not os.path.exists(HISTORY_FILE): df.to_csv(HISTORY_FILE, index=False, encoding='utf-8-sig')
    else: df.to_csv(HISTORY_FILE, mode='a', header=False, index=False, encoding='utf-8-sig')

with st.sidebar:
    st.markdown('<div style="color:#FFF;font-weight:800;">SRD Credit Engine v1.7.2 Full</div><div style="color:#38BDF8;font-size:11px;">ข้อมูลครบภาพที่ 2 + Step3+4</div>')
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
                pref=['gemini-2.5-flash','gemini-flash-latest','gemini-2.0-flash','gemini-1.5-flash']; idx=0
                for p in pref:
                    if p in usable: idx=usable.index(p); break
                selected_model=st.selectbox("🤖 โมเดล AI", usable, index=idx)
                st.success(f"✅ พร้อม: {selected_model}")
        except Exception as e: st.error(f"เชื่อมต่อขัดข้อง: {e}")
    st.write("---")
    if os.path.exists(HISTORY_FILE):
        dfh=pd.read_csv(HISTORY_FILE, encoding='utf-8-sig')
        st.caption(f"บันทึกแล้ว {len(dfh)} รายการ")
        st.download_button("📥 ดาวน์โหลด CSV", dfh.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig'), file_name=f"SRD_Credit_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv")

st.markdown('<div style="background:#1E293B;border:2px solid #334155;border-radius:16px;padding:18px;max-width:1320px;margin:0 auto 12px auto;"><div style="font-size:24px;font-weight:800;color:#FFF;">🛡️ SRD Credit Engine v1.7.2 Full Complete</div><div style="font-size:13px;font-weight:700;color:#38BDF8;margin-top:4px;">Mode 1 HONDA GIORNO+ CBS 85,500 • DSR 42% • Risk 72/100 • AI 13 • ข้อมูลครบภาพที่ 2 • Step3+Step4</div></div>', unsafe_allow_html=True)

# Mode1
st.markdown('<div class="moto-card">', unsafe_allow_html=True)
st.markdown('### 🛵 Mode 1: เครื่องคำนวณค่างวดเดี่ยว | HONDA GIORNO+ CBS | แก้ได้ทุกช่อง | Monthly ปัดได้')
c_left,c_right=st.columns([1.2,0.8])
with c_left:
    model_name=st.text_input("ชื่อรุ่นรถ / Model", value="HONDA GIORNO+ CBS", key="model_v172")
    cc1,cc2=st.columns(2)
    with cc1:
        cash_price=st.number_input("ราคาสดตัวรถ / Cash Price", value=85500.0, step=100.0, key="cash_v172")
        fee_in_loan=st.number_input("บวกค่า พรบ./ทะเบียน/ประกันรวมในยอดจัด", value=0.0, step=100.0, key="fee_in_v172")
        net_price=cash_price+fee_in_loan
        down_payment=st.number_input("เงินดาวน์ / Down Payment", value=8900.0, step=100.0, key="down_v172")
        financing=net_price-down_payment
    with cc2:
        flat_rate=st.number_input("Flat Rate %/เดือน", value=1.70, step=0.05, format="%.2f", key="flat_v172")
        term_months=st.selectbox("Term เดือน", [12,24,36,48,60], index=3, key="term_v172")
        total_interest_calc=financing*(flat_rate/100)*term_months
        total_debt_calc=financing+total_interest_calc
        monthly_calc=total_debt_calc/term_months if term_months else 0
        monthly_editable=st.number_input("⭐ Monthly Payment แก้ได้เพื่อปัดขึ้น/ลง", value=float(round(monthly_calc)), step=1.0, key="monthly_edit_v172")
        total_debt_editable=st.number_input("Total Debt", value=float(total_debt_calc), step=100.0, key="debt_edit_v172")
        monthly_final=monthly_editable; total_debt_final=monthly_editable*term_months if abs(monthly_editable-monthly_calc)>0.01 else total_debt_editable
with c_right:
    reg_fee=st.number_input("ค่า พรบ / ทะเบียน/ประกันภัย", value=2500.0, step=100.0, key="reg_v172")
    total_now=reg_fee+down_payment
    st.markdown(f'<div class="yellow-summary"><div style="display:flex;justify-content:space-between;"><span>ค่า พรบ</span><span>{reg_fee:,.0f}</span></div><div style="display:flex;justify-content:space-between;"><span>เงินดาวน์</span><span>{down_payment:,.0f}</span></div><div style="display:flex;justify-content:space-between;margin-top:6px;border-top:1px solid #000;padding-top:6px;"><span>ออกรถได้</span><span style="color:#DC2626;font-size:20px;">{total_now:,.0f}</span></div></div>', unsafe_allow_html=True)
    if st.button("💾 บันทึก Save", type="primary", use_container_width=True, key="save_calc_v172"):
        save_record({"Timestamp":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"Model":model_name,"Cash":cash_price,"Down":down_payment,"Financing":financing,"Monthly_Final":monthly_final,"Term":term_months,"TotalDebt":total_debt_final,"TotalNow":total_now})
        st.success(f"บันทึกแล้ว: {model_name} {monthly_final:,.0f}")
st.markdown('</div>', unsafe_allow_html=True)

# Dashboard
st.markdown('<div class="moto-card">', unsafe_allow_html=True)
st.markdown('#### 📊 Flat Calculator • DSR Meter 42% • Risk Score 72/100 • AI 13 ระบบ')
colA,colB,colC=st.columns(3)
with colA:
    st.markdown('<div class="dsr-gauge"><div style="font-size:36px;font-weight:800;color:#60A5FA;">42%</div><div style="font-size:14px;font-weight:700;color:#93C5FD;">DSR: 42%</div></div>', unsafe_allow_html=True)
    st.caption("รายได้ 37,500 ภาระ 15,694 ปานกลาง ปลอดภัย")
with colB:
    st.markdown('<div style="font-size:42px;font-weight:800;color:#60A5FA;">72 / 100</div><div style="background:#1E293B;border-radius:8px;height:8px;"><div style="width:72%;height:8px;background:#3B82F6;border-radius:8px;"></div></div><div style="font-size:13px;color:#6EE7B7;">72% ความเสี่ยงต่ำ</div>', unsafe_allow_html=True)
with colC:
    for m in ["1 ตรวจสอบเอกสารอัตโนมัติ","2 ตรวจเครดิตบูโร AI","3 วิเคราะห์พฤติกรรมการชำระหนี้","4 คาดการณ์ความเสี่ยงผิดนัด","5 ตรวจจับการปลอมเอกสาร","6 ประเมินความสามารถชำระหนี้","7 วิเคราะห์ความน่าเชื่อถือรายได้","8 Alternative Credit","9 จำแนกกลุ่มลูกค้าใหม่","10 เตือนความเสี่ยงล่วงหน้า","11 แนะนำผลิตภัณฑ์เหมาะสม","12 วิเคราะห์แนวโน้ม","13 สรุปข้อเสนออัจฉริยะ"]:
        st.markdown(f'<div style="font-size:12px;color:#E2E8F0;">🔹 {m}</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# Full Applicant
st.markdown('<div class="moto-card">', unsafe_allow_html=True)
st.markdown('### 👤 ข้อมูลคนเช่าซื้อ / ผู้สมัครหลัก (Applicant) • ข้อมูลครบแบบภาพที่ 2')
a1,a2=st.columns(2)
with a1:
    applicant_first=st.text_input("ชื่อ", value="สมชาย", key="app_first_v172")
    applicant_last=st.text_input("นามสกุล", value="นามสกุล", key="app_last_v172")
    applicant_job=st.text_input("อาชีพ เจ้าของกิจการ/พนักงานประจำ", value="เจ้าของกิจการ/พนักงานประจำ", key="app_job_v172")
    supervisor_name=st.text_input("หัวหน้างาน นายสมศักดิ์ พี่ชาย", value="นายสมศักดิ์ พี่ชาย", key="sup_name_v172")
    applicant_age=st.number_input("อายุ 25", min_value=18, max_value=80, value=25, key="app_age_v172")
    residence=st.selectbox("ที่พัก บ้านตนเอง", ["บ้านตนเอง/ปลอดภาระ","บ้านตนเอง/ติดผ่อน","บ้านเช่า/หอพัก","บ้านญาติ"], key="res_v172")
    salary=st.number_input("เงินเดือน 15,000", value=15000, step=500, key="salary_v172")
    existing_debt=st.number_input("หนี้เดิม 2198", value=2198, step=100, key="exist_debt_v172")
with a2:
    applicant_phone=st.text_input("เบอร์โทร 081-xxx-xxxx", value="081-xxx-xxxx", key="app_phone_v172")
    extra_income=st.number_input("รายได้เสริม 2,000", value=2000, step=500, key="extra_v172")
    living_cost=st.number_input("ค่าใช้ชีวิต 5000", value=5000, step=500, key="living_v172")
total_income=salary+extra_income
total_burden=existing_debt+living_cost+monthly_final
dsr_calc=(total_burden/total_income*100) if total_income else 0
cg,cy,cw=st.columns(3)
with cg: st.markdown(f'<div class="green-box"><div style="font-size:12px;color:#A7F3D0;">รายได้รวม</div><div style="font-size:26px;font-weight:800;color:#6EE7B7;">{total_income:,.0f}</div></div>', unsafe_allow_html=True)
with cy: st.markdown(f'<div class="yellow-box"><div style="font-size:12px;color:#FDE68A;">ภาระรวม</div><div style="font-size:26px;font-weight:800;color:#FBBF24;">{total_burden:,.0f}</div></div>', unsafe_allow_html=True)
with cw: st.markdown(f'<div class="white-box"><div style="font-size:12px;">DSR</div><div style="font-size:26px;font-weight:800;">{dsr_calc:.1f}%</div></div>', unsafe_allow_html=True)
st.markdown('#### 💞 บุคคลอ้างอิง 2 คน')
r1c,r2c=st.columns(2)
with r1c:
    ref1_name=st.text_input("อ้างอิง 1: ชื่อ-นามสกุล นายสมศักดิ์ พี่ชาย", value="นายสมศักดิ์ พี่ชาย", key="ref1_name_v172")
    ref1_phone=st.text_input("อ้างอิง 1: เบอร์โทร 086-xxx-xxxx", value="086-xxx-xxxx", key="ref1_phone_v172")
    ref1_rel=st.selectbox("อ้างอิง 1: ความสัมพันธ์ พี่ชาย", ["พี่ชาย","น้องชาย","เพื่อน","หัวหน้างาน","บิดา/มารดา"], key="ref1_rel_v172")
with r2c:
    ref2_name=st.text_input("อ้างอิง 2: ชื่อ-นามสกุล นางสาวสมปอง เพื่อน", value="นางสาวสมปอง เพื่อน", key="ref2_name_v172")
    ref2_phone=st.text_input("อ้างอิง 2: เบอร์โทร 082-xxx-xxxx", value="082-xxx-xxxx", key="ref2_phone_v172")
    ref2_rel=st.selectbox("อ้างอิง 2: ความสัมพันธ์ เพื่อน", ["เพื่อน","พี่ชาย","หัวหน้างาน","ญาติ"], key="ref2_rel_v172")
st.markdown('#### 💍 ข้อมูลคู่สมรส • นางสมหญิง จดทะเบียน สมรส 5 ปี มีบุตร 1 คน รายได้ 8,000 อาชีพ ค้าขาย')
has_spouse=st.checkbox("💍 มีคู่สมรส", value=True, key="has_spouse_v172")
spouse_summary="โสด"
if has_spouse:
    s1,s2=st.columns(2)
    with s1:
        spouse_name=st.text_input("ชื่อคู่สมรส นางสมหญิง", value="นางสมหญิง", key="sp_name_v172")
        spouse_status=st.selectbox("สถานะภาพสมรส จดทะเบียน", ["จดทะเบียนสมรส","โสด","อยู่กินกันฉันสามีภริยา (ไม่จดทะเบียน)","หย่าร้าง"], key="sp_status_v172")
        spouse_years=st.number_input("จำนวนปีที่สมรส 5 ปี", value=5, min_value=0, key="sp_years_v172")
    with s2:
        has_child=st.selectbox("มีบุตร/ไม่มีบุตร", ["มีบุตร","ไม่มีบุตร"], key="has_child_v172")
        child_count=st.number_input("จำนวนบุตร 1 คน", value=1, min_value=0, key="child_cnt_v172")
        spouse_income=st.number_input("รายได้คู่สมรส 8,000", value=8000, step=500, key="sp_inc_v172")
        spouse_job=st.text_input("อาชีพคู่สมรส ค้าขาย", value="ค้าขาย", key="sp_job_v172")
    spouse_summary=f"{spouse_name} | {spouse_status} สมรส {spouse_years} ปี | {has_child} {child_count} คน | รายได้ {spouse_income:,.0f} อาชีพ {spouse_job}"
st.markdown('#### 🛡️ ผู้ค้ำประกัน มีติ๊ก มี/ไม่มี • นายสมหมาย พนักงานประจำ ความสัมพันธ์ พ่อแม่ รายได้ 20,000 รู้จักน้อยกว่า 1 ปี เหตุผล เป็นพ่อแม่อยู่บ้านเดียวกัน')
has_guarantor=st.checkbox("✅ มีผู้ค้ำประกัน (ติ๊กถ้ามี)", value=True, key="has_guar_v172")
g_text="ไม่มีคนค้ำ"
if has_guarantor:
    g1,g2=st.columns(2)
    with g1:
        g_name=st.text_input("ชื่อผู้ค้ำ นายสมหมาย", value="นายสมหมาย", key="g_name_v172")
        g_job=st.text_input("อาชีพผู้ค้ำ พนักงานประจำ", value="พนักงานประจำ", key="g_job_v172")
        g_rel=st.selectbox("ความสัมพันธ์ผู้ค้ำ พ่อแม่", ["พ่อแม่","พี่ชาย","น้องชาย","เพื่อน","หัวหน้างาน"], key="g_rel_v172")
    with g2:
        g_phone=st.text_input("เบอร์ผู้ค้ำ", value="082-xxx-xxxx", key="g_phone_v172")
        g_income=st.number_input("รายได้ผู้ค้ำ 20,000", value=20000, step=1000, key="g_inc_v172")
        g_known=st.selectbox("รู้จักกัน น้อยกว่า 1 ปี", ["น้อยกว่า 1 ปี","1-3 ปี","มากกว่า 3 ปี"], key="g_known_v172")
    g_reason=st.text_area("ทำไมถึงค้ำให้: เป็นพ่อแม่อยู่บ้านเดียวกัน", value="เป็นพ่อแม่อยู่บ้านเดียวกัน", key="g_reason_v172")
    g_text=f"{g_name} อาชีพ {g_job} {g_rel} รายได้ {g_income:,.0f} รู้จัก {g_known} เหตุผล {g_reason}"
st.markdown('</div>', unsafe_allow_html=True)

# Step3 + Step4
st.markdown('<div class="moto-card">', unsafe_allow_html=True)
st.markdown('### 📸 เช็กลิสต์เอกสาร 6 รายการ (Step 3) แบบในรูป v1.3 Full')
d1=st.checkbox("1. 📸 ภาพถ่ายยืนยันตัวตนหน้าร้าน (Selfie คู่บัตร ปชช. ตัวจริง)", value=True, key="doc1_v172")
d2=st.checkbox("2. 📑 บัตรประชาชน + สำเนาทะเบียนบ้าน", value=True, key="doc2_v172")
d3=st.checkbox("3. 🏦 Statement ย้อนหลัง", value=True, key="doc3_v172")
d4=st.checkbox("4. 📊 NCB Report", value=False, key="doc4_v172")
d5=st.checkbox("5. 💵 สลิปเงินเดือน / หนังสือรับรองรายได้", value=True, key="doc5_v172")
d6=st.checkbox("6. 📍 รูปถ่ายที่พัก + หมุด Google Maps / รูปสต็อกแผงค้า", value=True, key="doc6_v172")
attached=[]; 
for name,chk in [("Selfie คู่บัตร",d1),("บัตร+ทะเบียนบ้าน",d2),("Statement",d3),("NCB",d4),("สลิป",d5),("พิกัด/แผงค้า",d6)]:
    if chk: attached.append(name)
if attached: st.markdown("".join([f'<span class="tag-red">{a} x</span>' for a in attached]), unsafe_allow_html=True)
st.markdown("**แนบภาพเอกสาร (รองรับ HEIC)**")
uploaded_files=st.file_uploader("Upload เอกสาร", type=["png","jpg","jpeg","heic","heif","webp"], accept_multiple_files=True, key="upload_v172", label_visibility="collapsed")
st.caption("200MB per file • JPG, PNG, HEIC, HEIF, WEBP")
st.markdown("**📷 ถ่ายจากกล้องมือถือ**")
st.caption("This app would like to use your camera Learn how to allow access")
camera_photo=st.camera_input("Take Photo", key="camera_v172", label_visibility="collapsed")
workplace_note=st.text_input("📌 พิกัด Google Maps", placeholder="https://maps.app.goo.gl/...", key="workplace_v172")
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="moto-card">', unsafe_allow_html=True)
st.markdown('### 🧠 วิเคราะห์ 13 โมดูลด้วย AI (Step 4) • gemini-3.6-flash')
if uploaded_files or camera_photo or st.checkbox("✅ ทดสอบโดยไม่ต้องอัปโหลด", key="test_no_upload_v172"):
    if st.button("🚀 รัน SRD Credit Investigation Engine 13 Modules เต็มระบบ v1.3", type="primary", use_container_width=True, key="run_ai_v172"):
        if not api_key_input or not selected_model:
            st.error("กรุณากรอก API Key ก่อน")
        else:
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key_input.strip())
                imgs=[]
                if uploaded_files:
                    for f in uploaded_files: imgs.append(_compress_mobile(Image.open(f)))
                if camera_photo: imgs.append(_compress_mobile(Image.open(camera_photo)))
                prompt=f"SRD v1.7.2 Model:{model_name} Cash:{cash_price:.0f} Down:{down_payment:.0f} Monthly:{monthly_final:.0f} Applicant:{applicant_first} {applicant_last} Job:{applicant_job} Supervisor:{supervisor_name} Phone:{applicant_phone} Income:{total_income:.0f} DSR:{dsr_calc:.1f}% Ref1:{ref1_name} {ref1_phone} {ref1_rel} Ref2:{ref2_name} {ref2_phone} {ref2_rel} Spouse:{spouse_summary} Guarantor:{g_text} Docs:{','.join(attached)}"
                with st.spinner(f"AI ({selected_model}) วิเคราะห์..."):
                    model_ai=genai.GenerativeModel(selected_model)
                    if imgs: response=model_ai.generate_content([prompt]+imgs)
                    else: response=model_ai.generate_content(prompt)
                    save_record({"Timestamp":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"Model":model_name,"Applicant":f"{applicant_first} {applicant_last}","Phone":applicant_phone,"Job":applicant_job,"Supervisor":supervisor_name,"Income":total_income,"DSR":f"{dsr_calc:.1f}%"})
                    st.success("💾 บันทึกและวิเคราะห์เสร็จสิ้น")
                    st.markdown(response.text)
            except Exception as e: st.error(f"Error: {e}")
else:
    st.info("กรุณาอัปโหลดภาพเอกสารหรือถ่ายภาพจากกล้องมือถือก่อนรัน AI")
st.markdown('</div>', unsafe_allow_html=True)
