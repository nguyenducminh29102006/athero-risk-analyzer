# 🫀 Athero-Risk Analyzer (Cardio Risk Analyzer)
**Two-Tier Clinical Intake, Hemodynamic Risk-Prioritization & Population BI Reference System**

## 1. System Overview & Architectural Motivation
**Athero-Risk Analyzer** bridges the gap between static epidemiological visualization and frontline outpatient clinical workflows. Built upon a validated reference cohort of **N = 68,610 cardiovascular patient records** (aged 29–64), the system integrates a macro-level Business Intelligence reference layer with a lightweight web-based clinical intake and triage engine.

### Two-Tier Architecture
* **Tier 1 — Population Reference & Epidemiological BI Layer (Python Pandas + Tableau Public):**
  * Rigorous physiological data cleaning pipeline filtering out non-biological blood pressure entry errors outside **Systolic BP 70–250 mmHg** and **Diastolic BP 40–150 mmHg**, establishing a baseline cohort risk probability of **49.5%**.
  * **Hemodynamic Scatter Analysis (SBP vs. DBP):** Identifies a dense high-risk overlap cluster within the **borderline blood pressure zone (120–139 / 80–89 mmHg)**.
  * **Metabolic × Lifestyle Risk Matrix (Glucose × Physical Activity):** Quantifies subgroup cardiovascular risk probability escalating from **46.6%** (*Normal Glucose + Physically Active*) to **63.4%** (*Well Above Normal Glucose + Physically Inactive*).

* **Tier 2 — Clinical Intake, Validation & Live Triage Web Layer (Python Streamlit + SQLite):**
  * **Physiological Input Validation Gate:** Enforces real-time anthropometric and hemodynamic constraints (`SBP > DBP`, `SBP ∈ [70, 250] mmHg`, `DBP ∈ [40, 150] mmHg`) prior to database persistence.
  * **Automated Hemodynamic & Triage Engine:** Computes **BMI**, **Pulse Pressure (PP)**, and **Mean Arterial Pressure (MAP)** instantaneously. Assigns **`🔴 Elevated Risk (Priority Triage)`** to patients exhibiting overt hypertension (`BP >= 140/90 mmHg`) OR borderline blood pressure (`120–139 / 80–89 mmHg`) compounded by **2 or more metabolic/lifestyle risk factors**.
  * **Local SQLite Consultation Queue (`patient_intake`):** Persists validated clinical records and dynamically prioritizes high-risk cases to the top of the consultation queue alongside embedded Tableau Public visual cross-referencing.

---

## 2. Technical Stack
* **Frontend & Application Framework:** Python, Streamlit (`st.components.v1` interactive iframe integration)
* **Data Processing & Validation:** Pandas, Rule-based Physiological Validation Engine
* **Database Layer:** SQLite3 (`patient_intake` schema with automated Vietnamese clinical seed records)
* **Business Intelligence Layer:** Tableau Public (Interactive Cohort Dashboard, N = 68,610)

---

## 3. Future Engineering Roadmap
While the current prototype utilizes a single flat SQLite table (`patient_intake`) and deterministic rule-based triage thresholds, future architectural iterations aim to:
1. **Normalized Relational Schema Design:** Refactor the flat storage structure into a multi-table relational database (`Patients`, `Clinical_Encounters`, `Hemodynamic_Logs`, `Lab_Metabolics`) to eliminate data redundancy and support longitudinal patient tracking across multiple hospital visits.
2. **Probabilistic Machine Learning Integration:** Replace static rule-based cutoffs in the borderline blood pressure zone with calibrated multivariate classification models (e.g., Regularized Logistic Regression / Gradient Boosted Trees) trained on the 68,610-patient cohort to output individualized continuous risk probabilities.
