import streamlit as st
import os
import io
import math
import re
import json
import uuid
import pandas as pd
from datetime import datetime
from pathlib import Path
from PIL import Image

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except Exception:
    pass


# ============================================================
# SRD CREDIT ENGINE V3
# Refined architecture:
# - Deal / Customer / Evidence / Risk / Decision
# - Separate affordability, fraud, data-quality and decision logic
# - Explainable results
# - Human review / override
# - CSV audit history (upgradeable to DB later)
# ============================================================

APP_VERSION = "3.0.0-refined"
HISTORY_FILE = "srd_credit_assessment_history.csv"

st.set_page_config(
    page_title=f"SRD Credit Engine {APP_VERSION}",
    page_icon="🏍️",
    layout="wide",
)

# -----------------------------
# UI
# -----------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Sarabun', sans-serif !important;
}
.stApp {
    background: #0F172A;
    color: #E2E8F0;
}
.block-container {
    max-width: 1500px !important;
    padding-top: 1rem !important;
}
.srd-card {
    background: #1E293B;
    border: 1px solid #334155;
    border-radius: 14px;
    padding: 16px;
    margin-bottom: 12px;
}
.srd-title {
    font-size: 28px;
    font-weight: 800;
}
.srd-subtitle {
    color: #94A3B8;
    font-size: 13px;
}
.status {
    border-radius: 10px;
    padding: 12px 16px;
    font-weight: 800;
    font-size: 20px;
    text-align: center;
}
.status-green {
    background: #064E3B;
    color: #A7F3D0;
    border: 1px solid #10B981;
}
.status-yellow {
    background: #78350F;
    color: #FDE68A;
    border: 1px solid #F59E0B;
}
.status-red {
    background: #7F1D1D;
    color: #FECACA;
    border: 1px solid #EF4444;
}
.status-blue {
    background: #1E3A8A;
    color: #BFDBFE;
    border: 1px solid #3B82F6;
}
.small-note {
    color: #94A3B8;
    font-size: 12px;
}
.reason {
    background: #0F172A;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 9px 12px;
    margin: 5px 0;
}
</style>
""", unsafe_allow_html=True)


# ============================================================
# Utilities
# ============================================================

def compress_mobile(img, max_side=1280, max_bytes=1_200_000):
    """Compress uploaded/camera images before sending to AI."""
    img = img.convert("RGB")
    if max(img.size) > max_side:
        img.thumbnail((max_side, max_side), Image.LANCZOS)

    last = None
    for quality in [75, 65, 55, 40]:
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        last = buf
        if buf.tell() <= max_bytes:
            buf.seek(0)
            return Image.open(buf)
    last.seek(0)
    return Image.open(last)


def clamp(value, low=0.0, high=100.0):
    return max(low, min(high, float(value)))


def safe_float(value, default=0.0):
    try:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def pct(value):
    return f"{value:.1f}%"


# ============================================================
# Motorcycle master data
# ============================================================

@st.cache_data(show_spinner=False)
def load_master_models(file_bytes=None, file_name=""):
    """Load motorcycle pricing once. Returns dataframe + lookup + diagnostics."""
    debug = []
    sources = []

    if file_bytes:
        sources.append(("uploaded", io.BytesIO(file_bytes)))

    candidates = [
        "Motorcycle-Price-All-Models.xlsx",
        "./Motorcycle-Price-All-Models.xlsx",
        "motorcycle_price_all_models.xlsx",
        "/mnt/data/Motorcycle-Price-All-Models.xlsx",
        "/mnt/data/motorcycle_price_all_models.xlsx",
        "data/Motorcycle-Price-All-Models.xlsx",
    ]
    for path in candidates:
        if os.path.exists(path):
            sources.append((path, path))

    for source_name, source in sources:
        try:
            xls = pd.ExcelFile(source)

            for sheet in xls.sheet_names:
                for header in [1, 0, 2]:
                    try:
                        df = pd.read_excel(xls, sheet_name=sheet, header=header)

                        if "รุ่นรถ" not in df.columns:
                            continue

                        df["รุ่นรถ"] = df["รุ่นรถ"].ffill()
                        if "รหัสรถ" in df.columns:
                            df["รหัสรถ"] = df["รหัสรถ"].ffill()
                        if "ราคาจัด" in df.columns:
                            df["ราคาจัด"] = df["ราคาจัด"].ffill()

                        interest_cols = [c for c in df.columns if "ดอกเบี้ย" in str(c)]
                        if not interest_cols:
                            continue

                        interest_col = interest_cols[0]
                        df[interest_col] = df[interest_col].ffill()

                        if "รหัสรถ" in df.columns:
                            df = df[pd.notna(df["รหัสรถ"])].copy()

                        df = df[
                            ~df["รุ่นรถ"].astype(str).str.contains(
                                "รุ่นรถ|ตารางโปรโมชัน", na=False
                            )
                        ].copy()

                        df["รุ่นรถ"] = df["รุ่นรถ"].astype(str).str.strip()
                        df = df[~df["รุ่นรถ"].isin(["nan", "NaN", ""])].copy()
                        df = df.drop_duplicates(subset=["รุ่นรถ"], keep="first")

                        if len(df) < 5:
                            continue

                        rename_map = {
                            "ราคาจัด": "ยอดจัด",
                            interest_col: "ดอกเบี้ยต่อเดือน",
                            "ดาวน์": "ราคาดาวน์",
                            "ค่าจด/พรบ.": "ทะเบียน พรบ ประกัน",
                            "รวมออกรถ": "ค่าใช้จ่ายออกรถ",
                            "เงินดาวน์": "ราคาดาวน์",
                        }
                        df = df.rename(columns=rename_map)

                        for col in [
                            "ยอดจัด",
                            "ดอกเบี้ยต่อเดือน",
                            "ราคาดาวน์",
                            "ทะเบียน พรบ ประกัน",
                        ]:
                            if col not in df.columns:
                                df[col] = 0

                        debug.append(
                            f"โหลดสำเร็จ: {source_name} / {sheet} / {len(df)} รุ่น"
                        )
                        return df, debug

                    except Exception as exc:
                        # Keep trying other header/sheet combinations.
                        continue

        except Exception as exc:
            debug.append(f"โหลด {source_name} ไม่สำเร็จ: {exc}")

    fallback = pd.DataFrame({
        "รุ่นรถ": [
            "ฟาซซิโอ้ SMK",
            "Aerox 155 2026",
            "Wave 125 กุญแจธรรมดา /2026",
            "GIORNO+ CBS",
        ],
        "รหัสรถ": ["BKF700", "BWR100", "AFS125CSBT TH", "ACF125CBT"],
        "ยอดจัด": [49500, 85900, 63500, 85500],
        "ดอกเบี้ยต่อเดือน": [0.015, 0.011, 0.017, 0.017],
        "ราคาดาวน์": [0, 0, 6900, 6900],
        "ทะเบียน พรบ ประกัน": [1000, 1000, 2000, 2000],
    })
    debug.append("ใช้ข้อมูลสำรอง 4 รุ่น เพราะไม่พบ Master Excel")
    return fallback, debug


# ============================================================
# Deal calculations
# ============================================================

def calculate_deal(cash_price, extra_fee, down_payment, flat_rate, term, round_type):
    net_price = cash_price + extra_fee
    financing = max(0.0, net_price - down_payment)

    total_interest = financing * (flat_rate / 100.0) * term
    total_debt = financing + total_interest
    monthly_raw = total_debt / term if term > 0 else 0.0

    if round_type == "ปัดขึ้น":
        monthly = math.ceil(monthly_raw)
    elif round_type == "ปัดลง":
        monthly = math.floor(monthly_raw)
    elif round_type == "ปัดขึ้น 10 บ.":
        monthly = math.ceil(monthly_raw / 10) * 10
    elif round_type == "ปัดลง 10 บ.":
        monthly = math.floor(monthly_raw / 10) * 10
    elif round_type == "ปัดขึ้น 100 บ.":
        monthly = math.ceil(monthly_raw / 100) * 100
    elif round_type == "ปัดลง 100 บ.":
        monthly = math.floor(monthly_raw / 100) * 100
    else:
        monthly = monthly_raw

    down_pct = (down_payment / net_price * 100) if net_price > 0 else 0.0

    return {
        "net_price": net_price,
        "financing": financing,
        "total_interest": total_interest,
        "total_debt": total_debt,
        "monthly_raw": monthly_raw,
        "monthly": monthly,
        "down_pct": down_pct,
    }


# ============================================================
# Affordability engine
# IMPORTANT: This is a decision-support model, not a regulatory
# credit score. Thresholds should be calibrated to SRD's actual
# portfolio performance and policy.
# ============================================================

def calculate_affordability(income, existing_debt, living_cost, new_payment):
    income = max(0.0, income)
    existing_debt = max(0.0, existing_debt)
    living_cost = max(0.0, living_cost)
    new_payment = max(0.0, new_payment)

    debt_service = existing_debt + new_payment
    dsr = (debt_service / income * 100) if income > 0 else 999.0

    disposable = income - existing_debt - new_payment - living_cost
    disposable_ratio = (disposable / income * 100) if income > 0 else -100.0

    # Transparent baseline scoring.
    # Lower DSR and positive disposable income are better.
    if income <= 0:
        score = 0
    else:
        dsr_component = clamp(100 - (dsr / 70 * 100))
        disposable_component = clamp((disposable_ratio + 20) / 50 * 100)
        score = round((dsr_component * 0.60) + (disposable_component * 0.40))

    if dsr <= 40 and disposable > 0:
        band = "GREEN"
    elif dsr <= 55 and disposable >= 0:
        band = "YELLOW"
    elif dsr <= 70:
        band = "ORANGE"
    else:
        band = "RED"

    return {
        "income": income,
        "existing_debt": existing_debt,
        "living_cost": living_cost,
        "new_payment": new_payment,
        "debt_service": debt_service,
        "dsr": dsr,
        "disposable": disposable,
        "disposable_ratio": disposable_ratio,
        "score": clamp(score),
        "band": band,
    }


# ============================================================
# Data quality engine
# ============================================================

def evaluate_data_quality(
    name,
    age,
    phone,
    job,
    residence,
    income,
    documents,
    workplace,
):
    checks = []
    score = 100

    def check(label, ok, penalty):
        nonlocal score
        checks.append((label, bool(ok)))
        if not ok:
            score -= penalty

    check("ชื่อผู้กู้", bool(name.strip()), 10)
    check("อายุ", age >= 18, 10)
    check("เบอร์โทร", len(re.sub(r"\D", "", phone)) >= 9, 10)
    check("อาชีพ", bool(job.strip()), 10)
    check("ที่พัก", residence not in ("", "[ว่าง]"), 10)
    check("รายได้", income > 0, 20)
    check("เอกสารอย่างน้อย 1 รายการ", len(documents) > 0, 15)
    check("สถานที่ทำงาน/พิกัด", bool(workplace.strip()), 15)

    score = clamp(score)

    if score >= 85:
        band = "GREEN"
    elif score >= 65:
        band = "YELLOW"
    elif score >= 45:
        band = "ORANGE"
    else:
        band = "RED"

    missing = [label for label, ok in checks if not ok]

    return {
        "score": score,
        "band": band,
        "missing": missing,
        "checks": checks,
    }


# ============================================================
# Fraud / anomaly engine
# Rule-based first; evidence must be shown.
# Do not treat a single proxy signal as proof of fraud.
# ============================================================

HIGH_RISK_VEHICLES = {
    "Yamaha - Sport", "Honda - รถใหม่", "SPORT",
    "YAMAHA", "R15", "WR155R", "Aerox", "XMAX",
    "NMAX", "Wave", "GIORNO", "BigBike"
}

UNSTABLE_EMPLOYMENT = {
    "ฟรีแลนซ์/รับจ้างทั่วไป",
    "ว่างงาน/ไม่มีงานประจำ",
}

def evaluate_fraud_rules(
    vehicle_type,
    down_pct,
    employment_type,
    shared_contracts,
    dsr,
    gps_consent,
    document_count,
    income,
    workplace,
):
    score = 0
    flags = []

    def add(points, severity, code, message, evidence):
        nonlocal score
        score += points
        flags.append({
            "severity": severity,
            "code": code,
            "message": message,
            "evidence": evidence,
            "points": points,
        })

    # These are indicators, not conclusions.
    if (
        vehicle_type in HIGH_RISK_VEHICLES
        and down_pct <= 5
        and employment_type in UNSTABLE_EMPLOYMENT
    ):
        add(
            25, "HIGH", "R_MATCH_RISK_01",
            "รูปแบบดีลมีความเสี่ยงสูงกว่าปกติ",
            "รถกลุ่มที่กำหนด + ดาวน์ <=5% + อาชีพไม่มั่นคง",
        )

    if shared_contracts >= 1:
        add(
            min(30, 10 * shared_contracts),
            "HIGH" if shared_contracts >= 2 else "MEDIUM",
            "R_LINKAGE_02",
            "พบจำนวนสัญญาที่เชื่อมโยงซึ่งควรตรวจสอบเพิ่มเติม",
            f"สัญญาที่เชื่อมโยงใน 90 วัน = {shared_contracts}",
        )

    if dsr > 70 and not gps_consent:
        add(
            20, "HIGH", "R_HIGH_DSR_NO_TRACKING",
            "ภาระหนี้สูงและไม่มีการยินยอมติดตามตำแหน่ง",
            f"DSR = {dsr:.1f}%",
        )
    elif down_pct < 5 and not gps_consent:
        add(
            10, "MEDIUM", "R_LOW_DOWN_NO_GPS",
            "ดาวน์ต่ำและไม่มีการยินยอมติดตามตำแหน่ง",
            f"ดาวน์ = {down_pct:.1f}%",
        )

    if income <= 0:
        add(
            25, "HIGH", "R_NO_INCOME",
            "ยังไม่พบรายได้ที่ใช้ประเมิน",
            "รายได้ = 0",
        )

    if document_count == 0:
        add(
            15, "MEDIUM", "R_NO_DOCUMENT",
            "ยังไม่มีเอกสารประกอบ",
            "จำนวนเอกสาร = 0",
        )

    if not workplace.strip():
        add(
            10, "MEDIUM", "R_NO_WORKPLACE",
            "ยังไม่มีข้อมูลสถานที่ทำงาน/พิกัด",
            "ช่องข้อมูลว่าง",
        )

    # Cap score so it remains a comparable 0-100 indicator.
    score = int(clamp(score))

    # Critical flags should not automatically become an irreversible
    # rejection. They trigger policy-defined review/halt.
    critical = any(f["severity"] == "CRITICAL" for f in flags)

    if critical:
        verdict = "HOLD / POLICY REVIEW"
    elif score >= 60:
        verdict = "MANUAL REVIEW"
    elif score >= 30:
        verdict = "ENHANCED REVIEW"
    else:
        verdict = "LOW FRAUD SIGNAL"

    return score, flags, verdict


# ============================================================
# Decision engine
# ============================================================

def decision_engine(affordability, fraud, data_quality):
    reasons = []
    actions = []

    # Hard safety/data gates.
    if data_quality["score"] < 45:
        reasons.append("ข้อมูลสำคัญยังไม่เพียงพอ")
        actions.extend(data_quality["missing"][:4])

    if affordability["income"] <= 0:
        reasons.append("ยังไม่พบรายได้ที่ใช้คำนวณความสามารถชำระ")
        actions.append("ตรวจสอบรายได้")

    if affordability["dsr"] > 70:
        reasons.append(f"DSR สูง {affordability['dsr']:.1f}%")
        actions.append("ทบทวนโครงสร้างดีล/ภาระหนี้")

    if affordability["disposable"] < 0:
        reasons.append("กระแสเงินสดหลังหักภาระและค่าใช้ชีวิตติดลบ")
        actions.append("ตรวจสอบค่าใช้ชีวิตและภาระหนี้")

    high_flags = [f for f in fraud["flags"] if f["severity"] == "HIGH"]
    if high_flags:
        reasons.append(f"พบ Fraud/Anomaly Signal ระดับสูง {len(high_flags)} รายการ")
        actions.append("ตรวจสอบหลักฐานของ Red Flag")

    if fraud["score"] >= 60:
        decision = "MANUAL REVIEW"
        band = "ORANGE"
    elif affordability["dsr"] > 70 or affordability["disposable"] < 0:
        decision = "MANUAL REVIEW"
        band = "ORANGE"
    elif data_quality["score"] < 65:
        decision = "MANUAL REVIEW"
        band = "YELLOW"
    elif fraud["score"] >= 30 or affordability["band"] in ("YELLOW", "ORANGE"):
        decision = "MANUAL REVIEW"
        band = "YELLOW"
    else:
        decision = "PRELIMINARY PASS"
        band = "GREEN"

    if not reasons:
        reasons.append("ไม่พบเหตุผลหลักที่บังคับให้เข้าสู่ Manual Review")

    # De-duplicate actions while preserving order.
    actions = list(dict.fromkeys(actions))

    return {
        "decision": decision,
        "band": band,
        "reasons": reasons[:5],
        "actions": actions[:6],
    }


# ============================================================
# History / audit
# ============================================================

def save_record(record):
    df = pd.DataFrame([record])
    path = Path(HISTORY_FILE)

    try:
        if not path.exists():
            df.to_csv(path, index=False, encoding="utf-8-sig")
        else:
            df.to_csv(
                path,
                mode="a",
                header=False,
                index=False,
                encoding="utf-8-sig",
            )
        return True, ""
    except Exception as exc:
        return False, str(exc)


# ============================================================
# Session defaults
# ============================================================

defaults = {
    "case_id": str(uuid.uuid4())[:8].upper(),
    "api_key": "",
    "model_sel": "gemini-2.0-flash",
    "decision_saved": False,
}
for key, value in defaults.items():
    st.session_state.setdefault(key, value)


# ============================================================
# Sidebar
# ============================================================

with st.sidebar:
    st.markdown("## 🏍️ SRD Credit Engine")
    st.caption(f"Version {APP_VERSION}")

    api_key = st.text_input(
        "Gemini API Key",
        value=st.session_state["api_key"],
        type="password",
    )
    st.session_state["api_key"] = api_key

    uploaded_excel = st.file_uploader(
        "Motorcycle-Price-All-Models.xlsx",
        type=["xlsx", "xls"],
    )

    file_bytes = uploaded_excel.getvalue() if uploaded_excel else None
    df_master, debug_list = load_master_models(
        file_bytes=file_bytes,
        file_name=uploaded_excel.name if uploaded_excel else "",
    )

    st.caption(f"รุ่นรถใน Master: {len(df_master)} รุ่น")

    if st.button("🔄 เริ่ม Case ใหม่", use_container_width=True):
        st.session_state.clear()
        st.rerun()

    st.divider()
    st.markdown("### Decision Policy")
    st.caption(
        "ระบบนี้เป็น Decision Support เท่านั้น "
        "ควรใช้ร่วมกับนโยบายบริษัทและการตรวจสอบโดยเจ้าหน้าที่"
    )


# ============================================================
# Header
# ============================================================

st.markdown("""
<div class="srd-card">
    <div class="srd-title">🏍️ SRD Credit Engine V3</div>
    <div class="srd-subtitle">
        Risk Decision Intelligence — Credit + Affordability + Fraud Signal
        + Data Confidence + Explainable Decision
    </div>
</div>
""", unsafe_allow_html=True)

tabs = st.tabs([
    "① DEAL",
    "② CUSTOMER",
    "③ EVIDENCE",
    "④ RISK",
    "⑤ DECISION",
])


# ============================================================
# TAB 1 — DEAL
# ============================================================

with tabs[0]:
    st.markdown("### ① Deal & Payment Structure")

    model_list = ["[ว่าง] เลือกรุ่นรถ"] + df_master["รุ่นรถ"].astype(str).tolist()
    brand_model = st.selectbox("ชื่อรุ่นรถ / Model", model_list)

    selected = None
    if brand_model != "[ว่าง] เลือกรุ่นรถ":
        selected = df_master[df_master["รุ่นรถ"].astype(str) == brand_model].iloc[0]

    default_cash = safe_float(selected["ยอดจัด"]) if selected is not None else 49500.0
    default_reg = safe_float(selected["ทะเบียน พรบ ประกัน"]) if selected is not None else 0.0
    default_down = safe_float(selected["ราคาดาวน์"]) if selected is not None else 8900.0
    default_flat = (
        safe_float(selected["ดอกเบี้ยต่อเดือน"]) * 100
        if selected is not None else 1.5
    )
    code_auto = str(selected["รหัสรถ"]) if selected is not None else ""

    c1, c2 = st.columns(2)

    with c1:
        cash_price = st.number_input(
            "ราคาสดตัวรถ",
            min_value=0.0,
            value=float(default_cash),
            step=100.0,
        )
        extra_fee = st.number_input(
            "ค่าดำเนินการ / ชุดแต่ง / อื่น ๆ",
            min_value=0.0,
            value=float(default_reg),
            step=100.0,
        )
        down_payment = st.number_input(
            "เงินดาวน์",
            min_value=0.0,
            value=float(default_down),
            step=100.0,
        )

    with c2:
        flat_rate = st.number_input(
            "Flat Rate ต่อเดือน (%)",
            min_value=0.0,
            value=float(default_flat),
            step=0.05,
            format="%.3f",
        )

        term_options = [12, 18, 24, 30, 36, 48, 55, 62]
        term_choice = st.selectbox("จำนวนงวด", term_options, index=4)

        custom_term = st.checkbox("กำหนดจำนวนงวดเอง 6–84")
        if custom_term:
            term = st.number_input(
                "Term",
                min_value=6,
                max_value=84,
                value=36,
                step=1,
            )
        else:
            term = term_choice

        round_type = st.selectbox(
            "วิธีปัดค่างวด",
            [
                "ไม่ปัดเศษ",
                "ปัดขึ้น",
                "ปัดลง",
                "ปัดขึ้น 10 บ.",
                "ปัดลง 10 บ.",
                "ปัดขึ้น 100 บ.",
                "ปัดลง 100 บ.",
            ],
        )

    deal = calculate_deal(
        cash_price,
        extra_fee,
        down_payment,
        flat_rate,
        term,
        round_type,
    )

    st.markdown("---")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Net Price", f"{deal['net_price']:,.0f}")
    m2.metric("ยอดจัด", f"{deal['financing']:,.0f}")
    m3.metric("ค่างวด", f"{deal['monthly']:,.0f}")
    m4.metric("ดาวน์", f"{deal['down_pct']:.1f}%")

    st.info(
        f"รหัสรถ: {code_auto or '-'} | "
        f"ดอกเบี้ยรวม {deal['total_interest']:,.0f} บาท | "
        f"ยอดหนี้รวม {deal['total_debt']:,.0f} บาท"
    )


# ============================================================
# TAB 2 — CUSTOMER
# ============================================================

with tabs[1]:
    st.markdown("### ② Customer & Affordability")

    c1, c2, c3 = st.columns([0.4, 0.4, 0.2])
    with c1:
        first_name = st.text_input("ชื่อ")
    with c2:
        last_name = st.text_input("สกุล")
    with c3:
        age = st.number_input("อายุ", min_value=0, max_value=100, value=0)

    c1, c2, c3 = st.columns(3)
    with c1:
        job = st.text_input("อาชีพ")
    with c2:
        phone = st.text_input("เบอร์โทร")
    with c3:
        employment_type = st.selectbox(
            "ประเภทอาชีพ",
            [
                "พนักงานประจำ",
                "เจ้าของกิจการ",
                "ฟรีแลนซ์/รับจ้างทั่วไป",
                "ว่างงาน/ไม่มีงานประจำ",
            ],
        )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        residence = st.selectbox(
            "ที่พัก",
            [
                "[ว่าง]",
                "บ้านตนเอง/ปลอดภาระ",
                "บ้านตนเอง/ติดผ่อน",
                "บ้านเช่า/หอพัก",
                "บ้านญาติ",
            ],
        )
    with c2:
        salary = st.number_input("เงินเดือน", min_value=0.0, value=0.0, step=500.0)
    with c3:
        extra_income = st.number_input("รายได้เสริม", min_value=0.0, value=0.0, step=500.0)
    with c4:
        existing_debt = st.number_input("หนี้เดิม/เดือน", min_value=0.0, value=0.0, step=100.0)

    living_cost = st.number_input("ค่าใช้ชีวิต/เดือน", min_value=0.0, value=0.0, step=500.0)

    total_income = salary + extra_income

    affordability = calculate_affordability(
        total_income,
        existing_debt,
        living_cost,
        deal["monthly"],
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("รายได้รวม", f"{total_income:,.0f}")
    c2.metric("หนี้ + ค่างวด", f"{affordability['debt_service']:,.0f}")
    c3.metric("DSR", pct(affordability["dsr"]))
    c4.metric("เงินเหลือหลังค่าใช้ชีวิต", f"{affordability['disposable']:,.0f}")

    if affordability["band"] == "GREEN":
        st.success("🟢 Affordability: ดี")
    elif affordability["band"] == "YELLOW":
        st.warning("🟡 Affordability: ต้องพิจารณา")
    elif affordability["band"] == "ORANGE":
        st.warning("🟠 Affordability: ความเสี่ยงสูงขึ้น")
    else:
        st.error("🔴 Affordability: ต้องตรวจสอบอย่างละเอียด")

    st.caption(
        f"Disposable Ratio = {affordability['disposable_ratio']:.1f}% | "
        f"Affordability Score = {affordability['score']:.0f}/100"
    )


# ============================================================
# TAB 3 — EVIDENCE
# ============================================================

with tabs[2]:
    st.markdown("### ③ Evidence & Data Quality")

    c1, c2 = st.columns(2)

    with c1:
        st.markdown("**เอกสาร**")
        doc1 = st.checkbox("สำเนาบัตรประชาชน")
        doc2 = st.checkbox("ทะเบียนบ้าน")
        doc3 = st.checkbox("สลิปเงินเดือน 3 เดือน")
        doc4 = st.checkbox("สเตทเมนท์ 6 เดือน")
        doc5 = st.checkbox("ใบจดทะเบียนการค้า")
        doc6 = st.checkbox("รูปที่พัก / หมุด Google Maps")

    with c2:
        st.markdown("**ข้อมูลตรวจสอบ**")
        workplace = st.text_input("สถานที่ทำงาน / Google Maps")
        story = st.text_area("บริบทหน้าร้าน / หมายเหตุ")
        gps_consent = st.checkbox(
            "ยินยอมให้ติดตามตำแหน่งตามนโยบายบริษัท",
            value=True,
        )
        shared_contracts = st.number_input(
            "จำนวนสัญญาที่เชื่อมโยงใน 90 วัน",
            min_value=0,
            value=0,
        )

    documents = [
        x for x, ok in [
            ("บัตรประชาชน", doc1),
            ("ทะเบียนบ้าน", doc2),
            ("สลิปเงินเดือน 3 เดือน", doc3),
            ("สเตทเมนท์ 6 เดือน", doc4),
            ("ใบจดทะเบียนการค้า", doc5),
            ("รูปที่พัก / หมุด Google Maps", doc6),
        ] if ok
    ]

    uploaded = st.file_uploader(
        "Upload เอกสาร / รูปภาพ",
        type=["png", "jpg", "jpeg", "heic", "heif", "webp"],
        accept_multiple_files=True,
    )
    camera = st.camera_input("📷 ถ่ายภาพ")

    bad_extensions = (".dng", ".raw", ".arw", ".cr2", ".cr3", ".nef", ".orf", ".rw2", ".raf")
    if uploaded:
        bad = [f.name for f in uploaded if f.name.lower().endswith(bad_extensions)]
        if bad:
            st.error(f"ไม่รองรับไฟล์ RAW/DNG: {', '.join(bad)}")

    data_quality = evaluate_data_quality(
        name=f"{first_name} {last_name}".strip(),
        age=age,
        phone=phone,
        job=job,
        residence=residence,
        income=total_income,
        documents=documents,
        workplace=workplace,
    )

    c1, c2 = st.columns([1, 2])
    with c1:
        st.metric("Data Confidence", f"{data_quality['score']:.0f}/100")
    with c2:
        if data_quality["missing"]:
            st.warning("ข้อมูลที่ยังขาด: " + ", ".join(data_quality["missing"]))
        else:
            st.success("ข้อมูลพื้นฐานครบตาม checklist")


# ============================================================
# TAB 4 — RISK
# ============================================================

with tabs[3]:
    st.markdown("### ④ Risk Intelligence")

    vehicle_types = [
        "Auto", "Yamaha - Sport", "YAMAHA", "Honda - รถใหม่",
        "Moped", "Sport", "BigBike", "Electric", "Wave", "GIORNO",
    ]
    vehicle_type = st.selectbox("ประเภทรถสำหรับ Risk Rule", vehicle_types)

    fraud_score, fraud_flags, fraud_verdict = evaluate_fraud_rules(
        vehicle_type=vehicle_type,
        down_pct=deal["down_pct"],
        employment_type=employment_type,
        shared_contracts=shared_contracts,
        dsr=affordability["dsr"],
        gps_consent=gps_consent,
        document_count=len(documents),
        income=total_income,
        workplace=workplace,
    )

    risk_c1, risk_c2, risk_c3, risk_c4 = st.columns(4)
    risk_c1.metric("Credit/Affordability", f"{affordability['score']:.0f}/100")
    risk_c2.metric("Fraud Signal", f"{fraud_score}/100")
    risk_c3.metric("Data Confidence", f"{data_quality['score']:.0f}/100")
    risk_c4.metric("DSR", pct(affordability["dsr"]))

    st.markdown("#### 🚨 Red Flags / Evidence")

    if fraud_flags:
        for flag in fraud_flags:
            severity = flag["severity"]
            icon = {"HIGH": "🔴", "MEDIUM": "🟠", "CRITICAL": "⛔"}.get(severity, "🟡")
            st.markdown(
                f"""
                <div class="reason">
                    <b>{icon} {severity} — {flag['code']}</b><br>
                    {flag['message']}<br>
                    <span class="small-note">Evidence: {flag['evidence']} | +{flag['points']} points</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.success("🟢 ยังไม่พบ Fraud/Anomaly Signal จาก Rule ที่กำหนด")

    st.info(f"Fraud Engine: {fraud_verdict}")

    # What-if simulator
    st.markdown("---")
    st.markdown("#### 🧪 What-if Simulator")

    whatif_down = st.number_input("ทดลองเงินดาวน์", min_value=0.0, value=float(deal["down_payment"] if "down_payment" in deal else down_payment), step=100.0,
        step=100.0,
        key="whatif_down",
    )

    whatif = calculate_deal(
        cash_price,
        extra_fee,
        whatif_down,
        flat_rate,
        term,
        round_type,
    )
    whatif_affordability = calculate_affordability(
        total_income,
        existing_debt,
        living_cost,
        whatif["monthly"],
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("ค่างวดใหม่", f"{whatif['monthly']:,.0f}")
    c2.metric("DSR ใหม่", pct(whatif_affordability["dsr"]))
    c3.metric("เงินเหลือใหม่", f"{whatif_affordability['disposable']:,.0f}")

    st.caption(
        "What-if เป็นการจำลองโครงสร้างดีลเท่านั้น ไม่ใช่การรับประกันผลอนุมัติ"
    )


# ============================================================
# TAB 5 — DECISION
# ============================================================

with tabs[4]:
    st.markdown("### ⑤ Decision Center")

    fraud_pack = {
        "score": fraud_score,
        "flags": fraud_flags,
        "verdict": fraud_verdict,
    }

    final_decision = decision_engine(
        affordability=affordability,
        fraud=fraud_pack,
        data_quality=data_quality,
    )

    status_class = {
        "GREEN": "status-green",
        "YELLOW": "status-yellow",
        "ORANGE": "status-yellow",
        "RED": "status-red",
    }.get(final_decision["band"], "status-blue")

    st.markdown(
        f"""
        <div class="status {status_class}">
            {final_decision['decision']}
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("#### เหตุผลหลัก")
    for i, reason in enumerate(final_decision["reasons"], 1):
        st.markdown(f"**{i}.** {reason}")

    st.markdown("#### สิ่งที่ควรตรวจ / ทำต่อ")
    if final_decision["actions"]:
        for action in final_decision["actions"]:
            st.checkbox(action, key=f"action_{hash(action)}")
    else:
        st.success("ไม่พบ Action ที่ต้องทำเพิ่มจาก Engine ปัจจุบัน")

    st.markdown("---")
    st.markdown("#### 👤 Human Decision / Override")

    human_decision = st.radio(
        "ผลการพิจารณาของเจ้าหน้าที่",
        [
            "ใช้คำแนะนำระบบ",
            "อนุมัติ",
            "Manual Review",
            "ไม่อนุมัติ",
        ],
        horizontal=True,
    )

    override_reason = st.text_area(
        "เหตุผลของเจ้าหน้าที่ / Override",
        placeholder="ระบุเหตุผลและหลักฐานประกอบ หากเปลี่ยนจากคำแนะนำของระบบ",
    )

    # AI is optional analyst, not the decision maker.
    st.markdown("---")
    st.markdown("#### 🤖 AI Analyst (Optional)")

    run_ai = st.button(
        "วิเคราะห์สรุปด้วย Gemini",
        type="primary",
        use_container_width=True,
    )

    if run_ai:
        if not api_key:
            st.error("กรุณากรอก Gemini API Key ที่ Sidebar")
        else:
            try:
                import google.generativeai as genai

                genai.configure(api_key=api_key.strip())
                model_name = st.session_state.get("model_sel", "gemini-2.0-flash")

                prompt = f"""
คุณเป็น AI Analyst ของระบบ SRD Credit Engine
หน้าที่คือสรุปข้อมูลและชี้จุดที่ควรตรวจสอบ
ห้ามตัดสินอนุมัติสินเชื่อแทนเจ้าหน้าที่ และห้ามสร้างข้อมูลที่ไม่มีหลักฐาน

ข้อมูล:
- รถ: {brand_model}
- ยอดจัด: {deal['financing']:,.0f}
- ค่างวด: {deal['monthly']:,.0f}
- รายได้รวม: {total_income:,.0f}
- หนี้เดิม: {existing_debt:,.0f}
- ค่าใช้ชีวิต: {living_cost:,.0f}
- DSR: {affordability['dsr']:.1f}%
- Disposable: {affordability['disposable']:,.0f}
- Affordability Score: {affordability['score']:.0f}
- Fraud Signal: {fraud_score}
- Data Confidence: {data_quality['score']:.0f}
- System Decision: {final_decision['decision']}
- Reasons: {json.dumps(final_decision['reasons'], ensure_ascii=False)}
- Actions: {json.dumps(final_decision['actions'], ensure_ascii=False)}

กรุณาตอบ 4 หัวข้อ:
1) สรุปภาพรวม
2) จุดแข็ง
3) จุดเสี่ยง/ข้อมูลที่ยังไม่พอ
4) สิ่งที่เจ้าหน้าที่ควรตรวจต่อ
"""

                model_names = [
                    model_name,
                    "gemini-2.0-flash",
                    "gemini-2.0-flash-lite",
                ]

                response = None
                used_model = None
                last_error = None

                for candidate in dict.fromkeys(model_names):
                    try:
                        model = genai.GenerativeModel(candidate)
                        response = model.generate_content(prompt)
                        used_model = candidate
                        break
                    except Exception as exc:
                        last_error = exc

                if response is None:
                    raise last_error or RuntimeError("AI model unavailable")

                st.success(f"AI Analyst ใช้ {used_model}")
                st.markdown(response.text)

            except Exception as exc:
                st.error(f"AI Analyst Error: {exc}")

    st.markdown("---")

    # Save final audit record.
    if st.button("💾 บันทึก Case / Audit Trail", use_container_width=True):
        selected_human = (
            final_decision["decision"]
            if human_decision == "ใช้คำแนะนำระบบ"
            else human_decision
        )

        record = {
            "CaseID": st.session_state["case_id"],
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "AppVersion": APP_VERSION,
            "Model": brand_model,
            "Code": code_auto,
            "Cash": cash_price,
            "Net": deal["net_price"],
            "Down": down_payment,
            "DownPct": deal["down_pct"],
            "Financing": deal["financing"],
            "FlatRate": flat_rate,
            "Term": term,
            "MonthlyRaw": deal["monthly_raw"],
            "MonthlyFinal": deal["monthly"],
            "TotalInterest": deal["total_interest"],
            "TotalDebt": deal["total_debt"],
            "Income": total_income,
            "ExistingDebt": existing_debt,
            "LivingCost": living_cost,
            "DSR": affordability["dsr"],
            "Disposable": affordability["disposable"],
            "AffordabilityScore": affordability["score"],
            "FraudScore": fraud_score,
            "FraudVerdict": fraud_verdict,
            "DataConfidence": data_quality["score"],
            "SystemDecision": final_decision["decision"],
            "HumanDecision": selected_human,
            "OverrideReason": override_reason,
            "Reasons": " | ".join(final_decision["reasons"]),
            "Actions": " | ".join(final_decision["actions"]),
            "Documents": " | ".join(documents),
        }

        ok, error = save_record(record)

        if ok:
            st.success(
                f"บันทึก Case {st.session_state['case_id']} สำเร็จ — "
                f"System: {final_decision['decision']} / Human: {selected_human}"
            )
        else:
            st.error(f"บันทึก Audit Trail ไม่สำเร็จ: {error}")


# ============================================================
# Footer
# ============================================================

st.caption(
    f"SRD Credit Engine {APP_VERSION} | "
    "Decision-support only | ตรวจสอบผลกับนโยบายบริษัทก่อนใช้งานจริง"
)
