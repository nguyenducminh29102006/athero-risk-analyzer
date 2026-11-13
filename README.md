# 🫀 Cardio-Risk Analyzer
**Web-Based Clinical Intake, Rule-Based Priority Queue & Population Reference Prototype (N = 68,610)**

## 1. Project Motivation & Two-Module Scope
Developed independently following clinical observations in outpatient cardiology, **Cardio-Risk Analyzer** explores how lightweight information systems can organize initial patient intake records systematically while providing descriptive, multi-factor population context within a single interface—leaving clinical decisions entirely in physicians' hands.

### Functional Modules
* **Module 1 — Structured Patient Intake & Rule-Based Priority Queue (Python, Streamlit, SQLite):**
  * **Physiological Input Validation:** Enforces anthropometric and hemodynamic bounds (`Systolic BP 70–250 mmHg`, `Diastolic BP 40–150 mmHg`, `SBP > DBP`) prior to database insertion.
  * **Automated Hemodynamic & Queue Sorting:** Computes **BMI**, **Pulse Pressure (PP)**, and **Mean Arterial Pressure (MAP)**, storing validated records in a local SQLite database (`patient_intake`) and ordering cases into a preliminary rule-based priority queue (`🔴 Elevated Risk` vs. `🟢 Low/Normal Risk`).
* **Module 2 — Population-Level Analytical Reference Dashboard (Python, Pandas, Tableau Public):**
  * **Data Cleaning Pipeline:** Prepared **68,610** publicly available cardiovascular records (ages 29–64; baseline cohort prevalence: **49.5%**) using Python and Pandas by removing non-physiological blood pressure outliers.
  * **Multi-Factor Reference Visuals:** Embeds an interactive Tableau Public dashboard examining elevated-risk overlap in the borderline blood pressure zone (`120–139 / 80–89 mmHg`) and subgroup prevalence across **Glucose × Physical Activity** (`46.6%` to `63.4%`).

---

## 2. Technical Stack & Data Ethics
* **Application & Persistence Layer:** Python 3, Streamlit, SQLite3 (`patient_intake` schema)
* **Data Preparation & BI Layer:** Pandas, Tableau Public (`N = 68,610` anonymized Kaggle records)
* **Clinical Data Privacy:** Population analytics rely exclusively on de-identified public data; all pre-populated patient names and identifiers (`BN-2601` to `BN-2606`) in the SQLite queue are 100% synthetic demonstration records.

---

## 3. Current Prototype Limitations & Architectural Roadmap
1. **Relational Longitudinal Records:** The current single flat SQLite table (`patient_intake`) cannot link multiple visits by the same patient over time; future iterations require a normalized relational schema (`Patients`, `Clinical_Encounters`, `Vitals_Logs`).
2. **Automated Data Synchronization:** The local SQLite intake queue and the embedded Tableau dashboard currently operate independently without automated ETL pipelines incorporating new records into the historical reference dataset.
3. **Validated Individualized Modeling:** Current analytics remain descriptive at the subgroup level (`46.6%–63.4%`) alongside predefined triage rules rather than clinically validated, individualized predictive models.
