
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
        img.thumbnail((max_side, max_side), Image.LANCZOS)
    for q in [75,65,55,40]:
        b=io.BytesIO(); img.save(b, format="JPEG", quality=q, optimize=True)
        if b.tell()<=max_bytes: b.seek(0); return Image.open(b)
    b.seek(0); return Image.open(b)
st.set_page_config(page_title="SRD Credit Engine v1.7.1", layout="wide", page_icon="🛵")
st.markdown('''
<style>
@import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;600;700;800&display=swap');
html, body, [class*="css"] { font-family:'Sarabun', sans-serif !important; }
.stApp { background:#0F172A !important; } header { visibility:hidden; }
[data-testid="stSidebar"] { background:#020617 !important; border-right:1px solid #1E293B !important; }
[data-testid="stSidebar"] * { color:#94A3B8 !important; }
input, textarea, div[data-baseweb="select"] > div { background:#0F172A !important; color:#FFFFFF !important; border:2px solid #475569 !important; border-radius:12px !important; font-weight:700 !important; }
label { color:#F8FAFC !important; font-weight:700 !important; font-size:13px !important; }
.moto-card { background:#1E293B !important; border:2px solid #334155 !important; border-radius:16px; padding:18px; margin-bottom:14px; max-width:1320px; margin:0 auto; }
.yellow-summary { background:#FBBF24 !important; border-radius:12px; padding:14px 16px; color:#000 !important; font-weight:800; margin:10px 0; border:2px solid #F59E0B; }
.green-box { background:#065F46 !important; border:2px solid #10B981 !important; border-radius:12px; padding:12px; text-align:center; }
.yellow-box { background:#92400E !important; border:2px solid #FBBF24 !important; border-radius:12px; padding:12px; text-align:center; }
.white-box { background:#F1F5F9 !important; border:2px solid #94A3B8 !important; border-radius:12px; padding:12px; text-align:center; color:#000 !important; }
.editable-hint { background:#1E3A8A !important; border:1px dashed #60A5FA; border-radius:8px; padding:8px 12px; margin:6px 0; font-size:12px; color:#BFDBFE !important; }
.block-container { max-width:1320px !important; }
</style>
''', unsafe_allow_html=True)
HISTORY_FILE="srd_credit_assessment_history.csv"
def save_record(rec):
    df=pd.DataFrame([rec])
    if not os.path.exists(HISTORY_FILE): df.to_csv(HISTORY_FILE, index=False, encoding='utf-8-sig')
    else: df.to_csv(HISTORY_FILE, mode='a', header=False, index=False, encoding='utf-8-sig')
with st.sidebar:
    st.markdown('<div style="display:flex;gap:12px;padding:12px;align-items:center;"><div style="width:52px;height:52px;background:linear-gradient(135deg,#0EA5E9,#06B6D4);border-radius:14px;display:flex;align-items:center;justify-content:center;font-size:28px;">🐒</div><div><div style="color:#FFF;font-weight:800;">SRD Credit Engine</div><div style="color:#38BDF8;font-size:11px;">v1.7.1 Editable Monthly</div></div></div>', unsafe_allow_html=True)
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
st.markdown('<div style="background:#1E293B;border:2px solid #334155;border-radius:16px;padding:18px;max-width:1320px;margin:0 auto 12px auto;"><div style="font-size:24px;font-weight:800;color:#FFF;">🛡️ SRD Credit Engine v1.7.1</div><div style="font-size:13px;font-weight:700;color:#38BDF8;margin-top:4px;">Monthly แก้ได้หลังคำนวณเพื่อปัดขึ้น/ลง • แก้ได้ทุกช่อง • มีสูตรฝัง</div></div>', unsafe_allow_html=True)
st.markdown('<div class="moto-card">', unsafe_allow_html=True)
st.markdown('### 🛵 Mode 1: เครื่องคำนวณค่างวดเดี่ยว | แก้ไขได้ทุกช่อง')
c_left,c_right=st.columns([1.2,0.8])
with c_left:
    model_name=st.text_input("ชื่อรุ่นรถ / Model (แก้ได้)", value="HONDA GIORNO+ CBS", key="model_v171")
    cc1,cc2=st.columns(2)
    with cc1:
        cash_price=st.number_input("ราคาสดตัวรถ / Cash Price (แก้ได้)", value=85500.0, step=100.0, key="cash_v171")
        fee_in_loan=st.number_input("บวกค่า พรบ./ทะเบียน/ประกันรวมในยอดจัด (แก้ได้)", value=0.0, step=100.0, key="fee_in_v171")
        net_price=cash_price+fee_in_loan
        st.markdown(f'<div class="editable-hint">💡 Net Price = {cash_price:,.0f} + {fee_in_loan:,.0f} = <b>{net_price:,.0f}</b></div>', unsafe_allow_html=True)
        down_payment=st.number_input("เงินดาวน์ / Down Payment (แก้ได้)", value=8900.0, step=100.0, key="down_v171")
        financing=net_price-down_payment
        st.markdown(f'<div class="editable-hint">💡 Financing = {net_price:,.0f} - {down_payment:,.0f} = <b>{financing:,.0f}</b></div>', unsafe_allow_html=True)
    with cc2:
        flat_rate=st.number_input("อัตราดอกเบี้ยต่อเดือน / Flat Rate %/เดือน (แก้ได้)", value=1.70, step=0.05, format="%.2f", key="flat_v171")
        term_months=st.selectbox("ระยะเวลาผ่อน / Term เดือน (แก้ได้)", [12,24,36,48,60], index=3, key="term_v171")
        total_interest_calc=financing*(flat_rate/100)*term_months
        total_debt_calc=financing+total_interest_calc
        monthly_calc=total_debt_calc/term_months if term_months else 0
        st.markdown(f'<div class="editable-hint">🧮 สูตร: ดอกเบี้ยรวม = {financing:,.0f} x {flat_rate}% x {term_months} = {total_interest_calc:,.0f}<br>ยอดหนี้รวม = {financing:,.0f} + {total_interest_calc:,.0f} = {total_debt_calc:,.0f}<br>ค่างวดคำนวณ = {total_debt_calc:,.0f} / {term_months} = <b>{monthly_calc:,.2f}</b></div>', unsafe_allow_html=True)
        total_debt_editable=st.number_input("ยอดหนี้รวมทั้งหมด / Total Debt (แก้ได้หลังคำนวณ)", value=float(total_debt_calc), step=100.0, key="debt_edit_v171")
        monthly_editable=st.number_input("⭐ ค่างวดต่อเดือน / Monthly Payment แก้ได้เพื่อปัดขึ้น/ลง", value=float(round(monthly_calc)), step=1.0, key="monthly_edit_v171", help=f"สูตรได้ {monthly_calc:,.2f} - แก้เป็น 2900, 2898, 2850 ได้เลย")
        diff=monthly_editable-monthly_calc
        if abs(diff)>0.01:
            total_debt_from_monthly=monthly_editable*term_months
            st.markdown(f'<div style="background:#065F46;border:1px solid #10B981;border-radius:8px;padding:8px;color:#D1FAE5;font-size:12px;">✅ คุณปัดค่างวดจาก {monthly_calc:,.2f} → <b>{monthly_editable:,.0f}</b> (ต่าง {diff:+,.2f})<br>ยอดหนี้ใหม่ = {monthly_editable:,.0f} x {term_months} = <b>{total_debt_from_monthly:,.0f}</b></div>', unsafe_allow_html=True)
            total_debt_final=total_debt_from_monthly; monthly_final=monthly_editable
        else:
            total_debt_final=total_debt_editable; monthly_final=monthly_editable
with c_right:
    reg_fee=st.number_input("ค่า พรบ / ทะเบียน/ประกันภัย (แก้ได้)", value=2500.0, step=100.0, key="reg_v171")
    total_now=reg_fee+down_payment
    st.markdown(f'<div class="yellow-summary"><div style="display:flex;justify-content:space-between;"><span>ค่า พรบ</span><span>{reg_fee:,.0f}</span></div><div style="display:flex;justify-content:space-between;"><span>เงินดาวน์</span><span>{down_payment:,.0f}</span></div><div style="display:flex;justify-content:space-between;margin-top:6px;border-top:1px solid #000;padding-top:6px;"><span>ออกรถได้</span><span style="color:#DC2626;font-size:20px;">{total_now:,.0f}</span></div></div>', unsafe_allow_html=True)
    b1,b2=st.columns(2)
    with b1:
        if st.button("🔄 คำนวณใหม่ตามสูตร", use_container_width=True, key="recalc_v171"): st.rerun()
    with b2:
        if st.button("💾 บันทึกยอดที่ปัดแล้ว", type="primary", use_container_width=True, key="save_calc_v171"):
            save_record({"Timestamp":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"Model":model_name,"Cash":cash_price,"Down":down_payment,"Financing":financing,"Monthly_Calc":monthly_calc,"Monthly_Final":monthly_final,"Term":term_months,"TotalDebt_Calc":total_debt_calc,"TotalDebt_Final":total_debt_final,"TotalNow":total_now})
            st.success(f"บันทึกแล้ว: ค่างวดปัดเป็น {monthly_final:,.0f}")
st.markdown('</div>', unsafe_allow_html=True)
