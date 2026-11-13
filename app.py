import sqlite3
from datetime import datetime
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# ==============================================================================
# 1. PAGE CONFIGURATION & CLINICAL UI STYLING
# ==============================================================================
st.set_page_config(
    page_title="Cardio-Risk Analyzer | Clinical Intake & Reference Prototype",
    page_icon="🫀",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        .main-header {
            background: linear-gradient(90deg, #0f172a 0%, #1e3a8a 100%);
            color: white;
            padding: 1.4rem 1.8rem;
            border-radius: 10px;
            margin-bottom: 1.2rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        .main-header h1 {
            margin: 0;
            font-size: 1.75rem;
            font-weight: 700;
            color: #ffffff;
        }
        .main-header p {
            margin: 0.35rem 0 0 0;
            font-size: 0.95rem;
            color: #cbd5e1;
        }
        .kpi-card {
            background-color: #ffffff;
            border: 1px solid #e2e8f0;
            border-left: 5px solid #1e3a8a;
            border-radius: 8px;
            padding: 1rem 1.2rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        .kpi-card.alert {
            border-left-color: #dc2626;
            background-color: #fef2f2;
        }
        .kpi-card.reference {
            border-left-color: #0284c7;
            background-color: #f0f9ff;
        }
        .kpi-title {
            font-size: 0.8rem;
            font-weight: 600;
            text-transform: uppercase;
            color: #64748b;
            margin-bottom: 0.25rem;
        }
        .kpi-value {
            font-size: 1.65rem;
            font-weight: 700;
            color: #0f172a;
        }
        .kpi-sub {
            font-size: 0.78rem;
            color: #475569;
            margin-top: 0.2rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==============================================================================
# 2. CONSTANTS & REFERENCE PARAMETERS (SYNCED 100% WITH TABLEAU N = 68,610)
# ==============================================================================
DB_PATH = "cardio_risk_clinical.db"

TABLEAU_BASE_URL = (
    "https://public.tableau.com/views/"
    "CardioRiskAnalyzer-NguyenDucMinh-VYGO2026/Dashboard1"
)
TABLEAU_EMBED_URL = (
    f"{TABLEAU_BASE_URL}?:embed=y&:showVizHome=no&:toolbar=top&:language=en-US"
)

SBP_MIN, SBP_MAX = 70, 250
DBP_MIN, DBP_MAX = 40, 150
HEIGHT_MIN, HEIGHT_MAX = 120.0, 220.0
WEIGHT_MIN, WEIGHT_MAX = 30.0, 200.0
AGE_MIN, AGE_MAX = 18, 100

# Exact Subgroup Prevalence Values from Tableau Heatmap (Glucose Level x Physical Activity)
SUBGROUP_PROB_MATRIX = {
    ("Normal", "Yes"): 46.6,
    ("Normal", "No"): 51.5,
    ("Above Normal", "Yes"): 58.1,
    ("Above Normal", "No"): 61.7,
    ("Well above normal", "Yes"): 61.4,
    ("Well above normal", "No"): 63.4,
}


# ==============================================================================
# 3. CLINICAL VALIDATION & RULE-BASED TRIAGE ENGINE
# ==============================================================================
def validate_clinical_inputs(
    patient_name: str,
    age: int,
    height_cm: float,
    weight_kg: float,
    sbp: int,
    dbp: int,
) -> list[str]:
    """Validate physiological bounds before computation and database insertion."""
    errors = []

    if not patient_name or len(patient_name.strip()) < 2:
        errors.append("Patient ID / Full Name must contain at least 2 characters.")

    if not (AGE_MIN <= age <= AGE_MAX):
        errors.append(
            f"Age ({age} yrs) is outside valid adult clinical range ({AGE_MIN}–{AGE_MAX} yrs)."
        )

    if not (SBP_MIN <= sbp <= SBP_MAX):
        errors.append(
            f"Physiological Outlier: Systolic BP ({sbp} mmHg) is outside valid bounds ({SBP_MIN}–{SBP_MAX} mmHg)."
        )

    if not (DBP_MIN <= dbp <= DBP_MAX):
        errors.append(
            f"Physiological Outlier: Diastolic BP ({dbp} mmHg) is outside valid bounds ({DBP_MIN}–{DBP_MAX} mmHg)."
        )

    if sbp <= dbp:
        errors.append(
            f"Hemodynamic Error: Systolic BP ({sbp} mmHg) must be strictly greater than Diastolic BP ({dbp} mmHg). Pulse Pressure cannot be zero or negative."
        )

    if not (HEIGHT_MIN <= height_cm <= HEIGHT_MAX):
        errors.append(
            f"Anthropometric Error: Height ({height_cm} cm) must be between {HEIGHT_MIN:.0f} and {HEIGHT_MAX:.0f} cm."
        )

    if not (WEIGHT_MIN <= weight_kg <= WEIGHT_MAX):
        errors.append(
            f"Anthropometric Error: Weight ({weight_kg} kg) must be between {WEIGHT_MIN:.0f} and {WEIGHT_MAX:.0f} kg."
        )

    return errors


def evaluate_patient_profile(
    height_cm: float,
    weight_kg: float,
    sbp: int,
    dbp: int,
    cholesterol: str,
    glucose: str,
    smoke: str,
    active: str,
) -> dict:
    """Compute BMI, Pulse Pressure (PP), Mean Arterial Pressure (MAP), and Rule-Based Triage Label."""
    bmi = round(weight_kg / ((height_cm / 100.0) ** 2), 1)
    pp = int(sbp - dbp)
    map_val = round(dbp + (pp / 3.0), 1)

    risk_factors = []
    if cholesterol != "Normal":
        risk_factors.append(f"Cholesterol ({cholesterol})")
    if glucose != "Normal":
        risk_factors.append(f"Glucose ({glucose})")
    if smoke == "Yes":
        risk_factors.append("Active Smoker")
    if active == "No":
        risk_factors.append("Physical Inactivity")

    risk_factor_count = len(risk_factors)

    is_overt_hypertension = (sbp >= 140) or (dbp >= 90)
    is_borderline_bp = (120 <= sbp <= 139) or (80 <= dbp <= 89)

    if is_overt_hypertension:
        triage_status = "🔴 Elevated Risk (Priority Triage)"
        priority_rank = 1
        triage_reason = f"Overt Hypertension (BP {sbp}/{dbp} >= 140/90 mmHg)"
    elif is_borderline_bp and risk_factor_count >= 2:
        triage_status = "🔴 Elevated Risk (Priority Triage)"
        priority_rank = 1
        triage_reason = (
            f"Borderline BP ({sbp}/{dbp} mmHg) + {risk_factor_count} Metabolic/Lifestyle Risk Factors"
        )
    else:
        triage_status = "🟢 Low/Normal Risk (Standard Queue)"
        priority_rank = 2
        if is_borderline_bp:
            triage_reason = (
                f"Borderline BP ({sbp}/{dbp} mmHg) with <2 Risk Factors ({risk_factor_count} present)"
            )
        else:
            triage_reason = f"Normotensive Range ({sbp}/{dbp} mmHg)"

    subgroup_prob = SUBGROUP_PROB_MATRIX.get((glucose, active), 49.5)

    return {
        "bmi": bmi,
        "pp": pp,
        "map_val": map_val,
        "risk_factor_count": risk_factor_count,
        "triage_status": triage_status,
        "priority_rank": priority_rank,
        "triage_reason": triage_reason,
        "subgroup_prob": subgroup_prob,
    }


# ==============================================================================
# 4. LOCAL SQLITE DATABASE ENGINE (FLAT TABLE `patient_intake` + SEED DATA)
# ==============================================================================
def init_and_seed_db():
    """Initialize flat SQLite table `patient_intake` and populate synthetic Vietnamese seed records."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS patient_intake (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_code TEXT NOT NULL,
            patient_name TEXT NOT NULL,
            age INTEGER NOT NULL,
            gender TEXT NOT NULL,
            height_cm REAL NOT NULL,
            weight_kg REAL NOT NULL,
            bmi REAL NOT NULL,
            systolic_bp INTEGER NOT NULL,
            diastolic_bp INTEGER NOT NULL,
            pulse_pressure INTEGER NOT NULL,
            map_mmhg REAL NOT NULL,
            cholesterol TEXT NOT NULL,
            glucose TEXT NOT NULL,
            smoke TEXT NOT NULL,
            physical_activity TEXT NOT NULL,
            risk_factor_count INTEGER NOT NULL,
            subgroup_ref_prob REAL NOT NULL,
            triage_status TEXT NOT NULL,
            triage_reason TEXT NOT NULL,
            priority_rank INTEGER NOT NULL,
            intake_timestamp TEXT NOT NULL
        )
        """
    )

    cursor.execute("SELECT COUNT(*) FROM patient_intake")
    count = cursor.fetchone()[0]

    if count == 0:
        seed_patients = [
            ("BN-2601", "Nguyễn Văn Hùng", 58, "Male", 168.0, 76.0, 162, 98, "Well above normal", "Above Normal", "Yes", "No", "2026-11-09 08:05"),
            ("BN-2602", "Trần Thị Mai Phương", 52, "Female", 156.0, 64.0, 134, 86, "Above Normal", "Well above normal", "No", "No", "2026-11-09 08:12"),
            ("BN-2603", "Lê Hoàng Nam", 46, "Male", 172.0, 78.0, 128, 84, "Above Normal", "Normal", "Yes", "No", "2026-11-09 08:19"),
            ("BN-2604", "Phạm Thu Hà", 37, "Female", 160.0, 53.0, 114, 72, "Normal", "Normal", "No", "Yes", "2026-11-09 08:25"),
            ("BN-2605", "Vũ Minh Tuấn", 41, "Male", 170.0, 68.0, 126, 82, "Normal", "Normal", "No", "Yes", "2026-11-09 08:31"),
            ("BN-2606", "Hoàng Bích Ngọc", 61, "Female", 155.0, 58.0, 148, 92, "Above Normal", "Well above normal", "No", "Yes", "2026-11-09 08:38"),
        ]

        for p_code, p_name, age, gender, h, w, sbp, dbp, chol, gluc, smoke, act, ts in seed_patients:
            res = evaluate_patient_profile(h, w, sbp, dbp, chol, gluc, smoke, act)
            cursor.execute(
                """
                INSERT INTO patient_intake (
                    patient_code, patient_name, age, gender, height_cm, weight_kg, bmi,
                    systolic_bp, diastolic_bp, pulse_pressure, map_mmhg,
                    cholesterol, glucose, smoke, physical_activity,
                    risk_factor_count, subgroup_ref_prob, triage_status, triage_reason,
                    priority_rank, intake_timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    p_code, p_name, age, gender, h, w, res["bmi"],
                    sbp, dbp, res["pp"], res["map_val"],
                    chol, gluc, smoke, act,
                    res["risk_factor_count"], res["subgroup_prob"],
                    res["triage_status"], res["triage_reason"],
                    res["priority_rank"], ts,
                ),
            )
        conn.commit()
    conn.close()


def insert_patient_record(
    patient_code: str,
    patient_name: str,
    age: int,
    gender: str,
    height_cm: float,
    weight_kg: float,
    sbp: int,
    dbp: int,
    cholesterol: str,
    glucose: str,
    smoke: str,
    active: str,
    eval_result: dict,
):
    """Save validated patient record into `patient_intake` table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    cursor.execute(
        """
        INSERT INTO patient_intake (
            patient_code, patient_name, age, gender, height_cm, weight_kg, bmi,
            systolic_bp, diastolic_bp, pulse_pressure, map_mmhg,
            cholesterol, glucose, smoke, physical_activity,
            risk_factor_count, subgroup_ref_prob, triage_status, triage_reason,
            priority_rank, intake_timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            patient_code.strip(),
            patient_name.strip(),
            age,
            gender,
            height_cm,
            weight_kg,
            eval_result["bmi"],
            sbp,
            dbp,
            eval_result["pp"],
            eval_result["map_val"],
            cholesterol,
            glucose,
            smoke,
            active,
            eval_result["risk_factor_count"],
            eval_result["subgroup_prob"],
            eval_result["triage_status"],
            eval_result["triage_reason"],
            eval_result["priority_rank"],
            now_str,
        ),
    )
    conn.commit()
    conn.close()


def fetch_live_queue() -> pd.DataFrame:
    """Retrieve patient queue ordered by Triage Priority Rank, Systolic BP, and Intake ID."""
    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT
            patient_code AS "Patient ID",
            patient_name AS "Full Name",
            age AS "Age",
            gender AS "Gender",
            triage_status AS "Triage Classification",
            systolic_bp || '/' || diastolic_bp || ' mmHg' AS "BP (SBP/DBP)",
            pulse_pressure || ' mmHg' AS "PP",
            map_mmhg || ' mmHg' AS "MAP",
            bmi AS "BMI",
            cholesterol AS "Cholesterol",
            glucose AS "Glucose",
            smoke AS "Smoker",
            physical_activity AS "Active",
            subgroup_ref_prob || '%' AS "Cohort Subgroup Risk",
            triage_reason AS "Clinical Triage Rationale",
            intake_timestamp AS "Intake Time",
            priority_rank,
            systolic_bp,
            map_mmhg
        FROM patient_intake
        ORDER BY priority_rank ASC, systolic_bp DESC, id DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


def reset_seed_database():
    """Reset SQLite database back to default 6 synthetic Vietnamese patient records."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DROP TABLE IF EXISTS patient_intake")
    conn.close()
    init_and_seed_db()


init_and_seed_db()


# ==============================================================================
# 5. SIDEBAR: VALIDATED CLINICAL INPUT FORM
# ==============================================================================
with st.sidebar:
    st.markdown("## 🩺 Clinical Intake Form")
    st.caption(
        "Enter outpatient vitals & metabolic indicators. Physiological bounds are strictly enforced prior to database commit."
    )

    with st.form("clinical_intake_form", clear_on_submit=False):
        st.markdown("**1. Patient Demographics**")
        col_id, col_age = st.columns([1.2, 1])
        with col_id:
            patient_code = st.text_input("Patient ID", value="BN-2607")
        with col_age:
            age = st.number_input("Age (yrs)", min_value=1, max_value=120, value=54, step=1)

        patient_name = st.text_input("Patient Full Name", value="Đỗ Quang Minh")
        gender = st.selectbox("Biological Sex", options=["Male", "Female"])

        col_h, col_w = st.columns(2)
        with col_h:
            height_cm = st.number_input(
                "Height (cm)", min_value=50.0, max_value=250.0, value=166.0, step=1.0
            )
        with col_w:
            weight_kg = st.number_input(
                "Weight (kg)", min_value=10.0, max_value=300.0, value=72.0, step=0.5
            )

        st.markdown("---")
        st.markdown("**2. Hemodynamic Measurements**")
        st.caption("Valid Physiological Bounds: SBP 70–250 mmHg | DBP 40–150 mmHg | SBP > DBP")
        col_sbp, col_dbp = st.columns(2)
        with col_sbp:
            sbp = st.number_input(
                "Systolic BP (mmHg)", min_value=10, max_value=350, value=132, step=1
            )
        with col_dbp:
            dbp = st.number_input(
                "Diastolic BP (mmHg)", min_value=10, max_value=250, value=86, step=1
            )

        st.markdown("---")
        st.markdown("**3. Metabolic & Lifestyle Profile**")
        cholesterol = st.selectbox(
            "Cholesterol Level",
            options=["Normal", "Above Normal", "Well above normal"],
            index=1,
        )
        glucose = st.selectbox(
            "Glucose Level",
            options=["Normal", "Above Normal", "Well above normal"],
            index=2,
        )
        col_smk, col_act = st.columns(2)
        with col_smk:
            smoke = st.selectbox("Smoking Status", options=["No", "Yes"], index=0)
        with col_act:
            active = st.selectbox("Physical Activity", options=["No", "Yes"], index=0)

        submitted = st.form_submit_button(
            "➕ Validate & Commit to Triage Queue", use_container_width=True, type="primary"
        )

    if submitted:
        validation_errors = validate_clinical_inputs(
            patient_name=patient_name,
            age=age,
            height_cm=height_cm,
            weight_kg=weight_kg,
            sbp=sbp,
            dbp=dbp,
        )

        if validation_errors:
            st.error("🚨 **Clinical Validation Blocked Submission:**")
            for err in validation_errors:
                st.markdown(f"- {err}")
        else:
            eval_res = evaluate_patient_profile(
                height_cm=height_cm,
                weight_kg=weight_kg,
                sbp=sbp,
                dbp=dbp,
                cholesterol=cholesterol,
                glucose=glucose,
                smoke=smoke,
                active=active,
            )
            insert_patient_record(
                patient_code=patient_code,
                patient_name=patient_name,
                age=age,
                gender=gender,
                height_cm=height_cm,
                weight_kg=weight_kg,
                sbp=sbp,
                dbp=dbp,
                cholesterol=cholesterol,
                glucose=glucose,
                smoke=smoke,
                active=active,
                eval_result=eval_res,
            )
            st.success(f"✅ Recorded **{patient_code} - {patient_name}** into SQLite Queue!")
            st.info(
                f"**Triage Output:** {eval_res['triage_status']}\n\n"
                f"• **Hemodynamics:** BMI `{eval_res['bmi']}` | PP `{eval_res['pp']} mmHg` | MAP `{eval_res['map_val']} mmHg`\n\n"
                f"• **Subgroup Ref. Risk:** `{eval_res['subgroup_prob']}%` *(Glucose: {glucose} × Active: {active})*\n\n"
                f"• **Rationale:** {eval_res['triage_reason']}"
            )

    with st.expander("🛠️ Database & Demo Controls"):
        st.caption(
            "To test physiological validation errors, try entering Systolic BP = 265 mmHg or Systolic (80) <= Diastolic (90) above."
        )
        if st.button("🔄 Reset Queue to Default Seed Data", use_container_width=True):
            reset_seed_database()
            st.rerun()


# ==============================================================================
# 6. MAIN FRAME TOP: HEADER, KPI SUMMARY & SQLITE LIVE TRIAGE QUEUE
# ==============================================================================
st.markdown(
    """
    <div class="main-header">
        <h1>🫀 Cardio-Risk Analyzer</h1>
        <p>Web-Based Clinical Intake, Rule-Based Priority Queue & Population Reference Prototype (Cohort N = 68,610 | Ages 29–64)</p>
    </div>
    """,
    unsafe_allow_html=True,
)

queue_df = fetch_live_queue()
total_patients = len(queue_df)
priority_count = int((queue_df["priority_rank"] == 1).sum()) if total_patients > 0 else 0
priority_pct = round((priority_count / total_patients) * 100, 1) if total_patients > 0 else 0.0
avg_map = round(queue_df["map_mmhg"].mean(), 1) if total_patients > 0 else 0.0

kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-title">Live Consultation Queue</div>
            <div class="kpi-value">{total_patients} Patients</div>
            <div class="kpi-sub">Active local SQLite (`patient_intake`)</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with kpi2:
    st.markdown(
        f"""
        <div class="kpi-card alert">
            <div class="kpi-title">🔴 Priority Triage (Elevated Risk)</div>
            <div class="kpi-value">{priority_count} Cases ({priority_pct}%)</div>
            <div class="kpi-sub">Rule-based priority queue sorting</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with kpi3:
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-title">Mean Queue MAP</div>
            <div class="kpi-value">{avg_map} mmHg</div>
            <div class="kpi-sub">MAP = DBP + 1/3 Pulse Pressure</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with kpi4:
    st.markdown(
        """
        <div class="kpi-card reference">
            <div class="kpi-title">Reference Cohort Baseline Risk</div>
            <div class="kpi-value">49.5%</div>
            <div class="kpi-sub">N = 68,610 cleaned records (Subgroups: 46.6%–63.4%)</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("### 📋 Live Clinical Consultation & Triage Queue (SQLite Engine)")
st.caption(
    "Preliminary rule-based priority queue: patients meeting **🔴 Elevated Risk** criteria—via overt hypertension (SBP ≥ 140 or DBP ≥ 90 mmHg) or borderline blood pressure (120–139 / 80–89 mmHg) accompanied by ≥ 2 metabolic/lifestyle risk factors—are sorted to the top for physician review."
)

display_cols = [
    "Patient ID",
    "Full Name",
    "Age",
    "Gender",
    "Triage Classification",
    "BP (SBP/DBP)",
    "PP",
    "MAP",
    "BMI",
    "Cholesterol",
    "Glucose",
    "Smoker",
    "Active",
    "Cohort Subgroup Risk",
    "Clinical Triage Rationale",
    "Intake Time",
]

st.dataframe(
    queue_df[display_cols],
    use_container_width=True,
    hide_index=True,
    height=280,
)

with st.expander("📐 View Hemodynamic Formulas, Triage Rules & Cohort Subgroup Matrix"):
    col_rule1, col_rule2 = st.columns([1.3, 1])
    with col_rule1:
        st.markdown(
            """
            **1. Automated Hemodynamic Indices:**
            * **Body Mass Index (BMI):** $\\text{Weight (kg)} / [\\text{Height (m)}]^2$
            * **Pulse Pressure (PP):** $\\text{Systolic BP} - \\text{Diastolic BP}$ *(normal reference ~40 mmHg)*
            * **Mean Arterial Pressure (MAP):** $\\text{Diastolic BP} + \\frac{1}{3}(\\text{Systolic BP} - \\text{Diastolic BP})$

            **2. Rule-Based Triage Decision Logic:**
            * **🔴 Elevated Risk (Priority Triage):** Triggered if $\\text{SBP} \\ge 140\\text{ mmHg}$ or $\\text{DBP} \\ge 90\\text{ mmHg}$, **OR** within the borderline zone ($120\\text{--}139 / 80\\text{--}89\\text{ mmHg}$) when accompanied by $\\ge 2$ metabolic/lifestyle risk factors (*Cholesterol > Normal, Glucose > Normal, Smoking = Yes, Physical Activity = No*).
            * **🟢 Low/Normal Risk (Standard Queue):** Normotensive patients or borderline BP patients with fewer than 2 accompanying metabolic/lifestyle risk factors.
            """
        )
    with col_rule2:
        st.markdown("**3. Tableau Reference Probability Matrix (Glucose × Physical Activity):**")
        matrix_df = pd.DataFrame(
            {
                "Glucose Level": ["Normal", "Above Normal", "Well above normal"],
                "Active (Yes)": ["46.6% (Lowest)", "58.1%", "61.4%"],
                "Inactive (No)": ["51.5%", "61.7%", "63.4% (Highest)"],
            }
        )
        st.table(matrix_df)

st.markdown("---")

# ==============================================================================
# 7. MAIN FRAME BOTTOM: EMBEDDED TABLEAU PUBLIC ENGINE
# ==============================================================================
col_tb_title, col_tb_link = st.columns([3, 1])
with col_tb_title:
    st.markdown("### 📊 Population Reference Layer: Interactive Analytical Dashboard (N = 68,610)")
    st.caption(
        "Descriptive population reference dashboard operating alongside the local intake queue. Examine multi-factor patterns in the borderline blood pressure zone (120–139 / 80–89 mmHg) and Glucose × Physical Activity subgroups (46.6% to 63.4%)."
    )
with col_tb_link:
    st.link_button(
        "🔗 Open Fullscreen on Tableau Public",
        url=f"{TABLEAU_BASE_URL}?:language=en-US",
        use_container_width=True,
    )

tableau_html = f"""
<div style="width: 100%; border: 1px solid #cbd5e1; border-radius: 10px; overflow: hidden; background: #ffffff; box-shadow: 0 2px 6px rgba(0,0,0,0.06);">
    <iframe
        src="{TABLEAU_EMBED_URL}"
        width="100%"
        height="880"
        frameborder="0"
        allowfullscreen="true"
        style="display: block;">
    </iframe>
</div>
"""
components.html(tableau_html, height=900, scrolling=True)
