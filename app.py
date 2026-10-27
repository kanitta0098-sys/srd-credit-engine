from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="SRD คำนวณเรตรถจักรยานยนต์", page_icon="🏍️", layout="wide")

html_path = Path(__file__).resolve().with_name("calculator.html")
if not html_path.is_file():
    st.error("ไม่พบ calculator.html กรุณาอัปโหลดไฟล์นี้ไว้ในโฟลเดอร์เดียวกับ app.py")
    st.stop()

html = html_path.read_text(encoding="utf-8")
st.caption("SRD • เครื่องคำนวณเรตรถจักรยานยนต์")
st.download_button(
    "ดาวน์โหลดเครื่องคำนวณเพื่อเปิดและพิมพ์โดยตรง",
    data=html,
    file_name="SRD_Motorcycle_Rate.html",
    mime="text/html",
)
st.caption("หากพิมพ์ผ่านหน้านี้ไม่ได้ ให้ดาวน์โหลดไฟล์ HTML เปิดด้วย Chrome หรือ Edge แล้วกรอกข้อมูลและกดพิมพ์ ข้อมูลจากหน้านี้จะไม่ย้ายไปในไฟล์ดาวน์โหลดโดยอัตโนมัติ")
components.html(html, height=1200, scrolling=True)
