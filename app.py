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

st.set_page_config(page_title="SRD Credit Engine v1.7.3 Blank", layout="wide", page_icon="🛵")

st.title("SRD Credit Engine v1.7.3 Blank Form - ฟอร์มว่าง")
st.caption("Mode 1 ยี่ห้อ/รุ่น / ราคาเงินสด / ดาวน์ / ยอดจัด / Flat % / Term / Monthly / Total Debt editable แก้ได้เพื่อปัดขึ้น/ลง + Total Debt แก้ได้ / ค่าทะเบียน/ประกันรถหาย/อื่นๆ กล่องเหลืองออกรถรวม ดึงจากเงินดาวน์")

# Mode 1 blank
st.subheader("Mode 1: ยี่ห้อ/รุ่น / ราคาเงินสด / ดาวน์ / ยอดจัด / Flat % / Term / Monthly / Total Debt")
c1,c2,c3,c4=st.columns(4)
with c1:
    brand_model=st.text_input("ยี่ห้อ/รุ่น", value="", placeholder="[ว่าง]")
    cash_price=st.number_input("ราคาเงินสด", value=0.0, step=100.0)
    down_payment=st.number_input("ดาวน์", value=0.0, step=100.0)
with c2:
    financing=st.number_input("ยอดจัด", value=0.0, step=100.0)
    flat_rate=st.number_input("Flat %", value=0.0, step=0.05, format="%.2f")
    term=st.selectbox("Term", [12,24,36,48,60], index=3)
with c3:
    monthly=st.number_input("Monthly ⭐ แก้ได้เพื่อปัดขึ้น/ลง", value=0.0, step=1.0)
    total_debt=st.number_input("Total Debt ✏️ แก้ได้", value=0.0, step=100.0)
with c4:
    reg_fee=st.number_input("ค่าทะเบียน/ประกันรถหาย/อื่นๆ", value=0.0, step=100.0)
    total_now=reg_fee+down_payment
    st.markdown(f"**Initial Payment Summary ดึงจากเงินดาวน์ + ค่าทะเบียน = ออกรถรวม: {down_payment:,.0f} + {reg_fee:,.0f} = {total_now:,.0f}**")

st.subheader("ข้อมูลคนเช่าซื้อ: ชื่อ-สกุล + อายุ อาชีพ + หัวหน้างาน + เบอร์ + ที่พัก + เงินเดือน + รายได้เสริม + รายได้รวม / ภาระรวม / DSR %")
a1,a2=st.columns(2)
with a1:
    f_name=st.text_input("ชื่อ", value="", placeholder="[ว่าง]")
    l_name=st.text_input("สกุล", value="", placeholder="[ว่าง]")
    age=st.number_input("อายุ", value=0)
    job=st.text_input("อาชีพ", value="", placeholder="[ว่าง]")
    sup=st.text_input("หัวหน้างาน", value="", placeholder="[ว่าง]")
    phone=st.text_input("เบอร์", value="", placeholder="[ว่าง]")
with a2:
    salary=st.number_input("เงินเดือน", value=0, step=500)
    extra=st.number_input("รายได้เสริม", value=0, step=500)
    debt=st.number_input("หนี้เดิม", value=0)
    living=st.number_input("ค่าใช้ชีวิต", value=0)
    total_inc=salary+extra
    total_bur=debt+living+monthly
    dsr=total_bur/total_inc*100 if total_inc>0 else 0
    st.metric("รายได้รวม", f"{total_inc:,.0f}")
    st.metric("ภาระรวม", f"{total_bur:,.0f}")
    st.metric("DSR %", f"{dsr:.1f}%")

st.subheader("บุคคลอ้างอิง 2 คน: อ้างอิง 1 +ความสัมพันธ์ / อ้างอิง 2 + ความสัมพันธ์")
r1,r2=st.columns(2)
with r1:
    ref1_name=st.text_input("อ้างอิง 1 ชื่อ-สกุล", value="", placeholder="[ว่าง]")
    ref1_rel=st.text_input("อ้างอิง 1 ความสัมพันธ์", value="", placeholder="[ว่าง]")
with r2:
    ref2_name=st.text_input("อ้างอิง 2 ชื่อ-สกุล", value="", placeholder="[ว่าง]")
    ref2_rel=st.text_input("อ้างอิง 2 ความสัมพันธ์", value="", placeholder="[ว่าง]")

st.subheader("คู่สมรส: ชื่อ-สกุล อายุ (ช่องติ๊ก ✅ไม่จด ✅จดทะเบียน) สมรส ปี มีบุตร คน รายได้ อาชีพ")
has_spouse=st.checkbox("มีคู่สมรส")
if has_spouse:
    c1,c2=st.columns(2)
    with c1:
        sp_name=st.text_input("คู่สมรส ชื่อ-สกุล", value="", placeholder="[ว่าง]")
        sp_age=st.number_input("คู่สมรส อายุ", value=0)
        sp_reg=st.radio("จดทะเบียน", ["✅ไม่จด","✅จดทะเบียน"], horizontal=True)
        sp_year=st.number_input("สมรส ปี", value=0)
    with c2:
        sp_child=st.number_input("มีบุตร คน", value=0)
        sp_inc=st.number_input("คู่สมรส รายได้", value=0)
        sp_job=st.text_input("คู่สมรส อาชีพ", value="", placeholder="[ว่าง]")

st.subheader("ผู้ค้ำประกัน ช่องติ๊ก ✅")
has_guar=st.checkbox("✅ มีผู้ค้ำประกัน")
if has_guar:
    g_name=st.text_input("ผู้ค้ำ ชื่อ-สกุล", value="", placeholder="[ว่าง]")
    g_phone=st.text_input("ผู้ค้ำ เบอร์", value="", placeholder="[ว่าง]")
    g_job=st.text_input("ผู้ค้ำ อาชีพ", value="", placeholder="[ว่าง]")
    g_inc=st.number_input("ผู้ค้ำ รายได้", value=0)
    g_rel=st.text_input("ผู้ค้ำ ความสัมพันธ์", value="", placeholder="[ว่าง]")

st.subheader("Step 3: เช็กลิสต์เอกสาร 6 รายการ แท็กแดง บัตร ปชช + ทะเบียนบ้าน x Statement x + Upload 200MB JPG PNG HEIC HEIF WEBP + This app would like to use your camera Take Photo")
d1=st.checkbox("1. สำเนาบัตรประชาชน")
d2=st.checkbox("2. ทะเบียนบ้าน")
d3=st.checkbox("3. สลิปเงินเดือน 3 เดือน")
d4=st.checkbox("4. สเตทเม้นท์ 6 เดือน")
d5=st.checkbox("5. ใบจดทะเบียนการค้า")
d6=st.checkbox("6. รูปถ่ายที่พัก")
uploaded=st.file_uploader("Upload", type=["png","jpg","jpeg","heic","heif","webp"], accept_multiple_files=True)
st.caption("200MB per file • JPG, PNG, HEIC, HEIF, WEBP")
st.caption("This app would like to use your camera Learn how to allow access")
cam=st.camera_input("Take Photo")

st.subheader("Step 4: วิเคราะห์ 13 โมดูลด้วย AI gemini-3.6-flash ปุ่มน้ำเงิน 🚀 รัน SRD Credit Investigation Engine 13 Modules เต็มระบบ v1.3 DSR Meter Risk Score AI 13 Modules")
if st.button("🚀 รัน SRD Credit Investigation Engine 13 Modules เต็มระบบ v1.3", type="primary", use_container_width=True):
    st.success("พร้อมรัน - ต้องใส่ API Key")
