# เมนูด้านข้าง (Sidebar) - ฉบับรองรับ Gemini API Key จาก Google Cloud
with st.sidebar:
    st.header("⚙️ การตั้งค่าระบบ")
    api_key_input = st.text_input(
    "Gemini API Key", 
    type="password", 
    placeholder="วางรหัส API Key ที่นี่",
    help="รหัส API Key จาก Google Cloud"
)

    if api_key_input:
        try:
            genai.configure(api_key=api_key_input.strip())
            # กำหนดโมเดลมาตรฐานที่พร้อมใช้งานโดยตรง ไม่ต้องดึง list_models
            model_options = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-1.5-pro']
            selected_model = st.selectbox("🤖 เลือกโมเดล AI", model_options, index=0)
            st.success(f"✅ เชื่อมต่อสำเร็จ: `{selected_model}`")
        except Exception as e:
            st.error(f"⚠️ เชื่อมต่อขัดข้อง: {e}")
    else:
        st.warning("⚠️ กรุณากรอก Gemini API Key ในช่องด้านบน")

    # ดาวน์โหลดประวัติการประเมิน
    st.write("---")
    st.subheader("💾 ฐานข้อมูลการประเมิน (Data Log)")
    if os.path.exists(HISTORY_FILE):
        df_hist = pd.read_csv(HISTORY_FILE, encoding='utf-8-sig')
        st.caption(f"บันทึกแล้วทั้งหมด: {len(df_hist)} รายการ")
        csv_data = df_hist.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button(
            label="📥 ดาวน์โหลดประวัติ (CSV)",
            data=csv_data,
            file_name=f"SRD_Credit_Data_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.caption("ยังไม่มีข้อมูลบันทึกในระบบ")