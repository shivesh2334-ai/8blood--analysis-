"""
Clinical Laboratory Analysis Engine
==================================
Core analysis logic for interpreting lab results against reference ranges,
calculating severity, generating interpretations, and providing recommendations.
"""

import math
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

# Severity constants
SEV_NORMAL = 0
SEV_MILD = 1
SEV_MODERATE = 2
SEV_SEVERE = 3
SEV_CRITICAL = 4

STATUS_NORMAL = "Normal"
STATUS_LOW = "Low"
STATUS_HIGH = "High"
STATUS_CRITICALLY_LOW = "Critically Low"
STATUS_CRITICALLY_HIGH = "Critically High"
STATUS_BORDERLINE = "Borderline"


# Reference ranges with units and clinical context
# Format: (min, max, unit, description, critical_low, critical_high)
REFERENCE_RANGES = {
    # CBC Parameters
    "RBC": {
        "male": (4.5, 5.5, "10^12/L", "Red Blood Cell Count", 3.0, 6.5),
        "female": (4.0, 5.0, "10^12/L", "Red Blood Cell Count", 3.0, 6.5),
        "description": "Oxygen-carrying cells",
    },
    "Hemoglobin": {
        "male": (13.5, 17.5, "g/dL", "Hemoglobin", 7.0, 20.0),
        "female": (12.0, 16.0, "g/dL", "Hemoglobin", 7.0, 20.0),
        "description": "Oxygen-carrying protein",
    },
    "Hematocrit": {
        "male": (38.0, 50.0, "%", "Hematocrit", 25.0, 60.0),
        "female": (35.0, 45.0, "%", "Hematocrit", 25.0, 60.0),
        "description": "Blood volume occupied by RBCs",
    },
    "MCV": {
        "default": (80.0, 100.0, "fL", "Mean Corpuscular Volume", 60.0, 120.0),
        "description": "Average RBC size",
    },
    "MCH": {
        "default": (27.0, 33.0, "pg", "Mean Corpuscular Hemoglobin", 20.0, 40.0),
        "description": "Average hemoglobin per RBC",
    },
    "MCHC": {
        "default": (32.0, 36.0, "g/dL", "Mean Corpuscular Hemoglobin Concentration", 28.0, 40.0),
        "description": "Hemoglobin concentration in RBCs",
    },
    "RDW_CV": {
        "default": (11.5, 14.5, "%", "Red Cell Distribution Width (CV)", 10.0, 20.0),
        "description": "RBC size variation",
    },
    "RDW_SD": {
        "default": (35.0, 56.0, "fL", "Red Cell Distribution Width (SD)", 30.0, 80.0),
        "description": "RBC size variation (SD)",
    },
    "WBC": {
        "default": (4.0, 11.0, "10^9/L", "White Blood Cell Count", 2.0, 30.0),
        "description": "Immune system cells",
    },
    "Neutrophils": {
        "default": (40.0, 75.0, "%", "Neutrophils", 10.0, 90.0),
        "absolute": (2.0, 7.5, "10^9/L", "Absolute Neutrophil Count", 0.5, 15.0),
        "description": "Primary bacterial defense",
    },
    "Lymphocytes": {
        "default": (20.0, 40.0, "%", "Lymphocytes", 5.0, 60.0),
        "absolute": (1.0, 4.5, "10^9/L", "Absolute Lymphocyte Count", 0.5, 10.0),
        "description": "Viral defense and immunity",
    },
    "Monocytes": {
        "default": (2.0, 10.0, "%", "Monocytes", 0.0, 20.0),
        "absolute": (0.2, 0.8, "10^9/L", "Absolute Monocyte Count", 0.0, 2.0),
        "description": "Phagocytic cells",
    },
    "Eosinophils": {
        "default": (1.0, 6.0, "%", "Eosinophils", 0.0, 15.0),
        "absolute": (0.0, 0.6, "10^9/L", "Absolute Eosinophil Count", 0.0, 1.5),
        "description": "Allergic/parasitic response",
    },
    "Basophils": {
        "default": (0.0, 2.0, "%", "Basophils", 0.0, 5.0),
        "absolute": (0.0, 0.2, "10^9/L", "Absolute Basophil Count", 0.0, 0.5),
        "description": "Inflammatory response",
    },
    "Bands": {
        "default": (0.0, 5.0, "%", "Band Neutrophils", 0.0, 15.0),
        "description": "Immature neutrophils",
    },
    "Platelets": {
        "default": (150.0, 450.0, "10^9/L", "Platelet Count", 50.0, 1000.0),
        "description": "Clotting cells",
    },
    "MPV": {
        "default": (7.5, 12.5, "fL", "Mean Platelet Volume", 5.0, 15.0),
        "description": "Average platelet size",
    },
    "PDW": {
        "default": (9.0, 17.0, "%", "Platelet Distribution Width", 5.0, 25.0),
        "description": "Platelet size variation",
    },
    "PCT": {
        "default": (0.15, 0.35, "%", "Plateletcrit", 0.05, 0.50),
        "description": "Blood volume occupied by platelets",
    },
    "ESR": {
        "male": (0.0, 15.0, "mm/hr", "Erythrocyte Sedimentation Rate", 0.0, 100.0),
        "female": (0.0, 20.0, "mm/hr", "Erythrocyte Sedimentation Rate", 0.0, 100.0),
        "description": "Inflammation marker",
    },
    "Reticulocytes": {
        "default": (0.5, 2.5, "%", "Reticulocytes", 0.0, 5.0),
        "description": "Immature RBCs",
    },
    "ANC": {
        "default": (2.0, 7.5, "10^9/L", "Absolute Neutrophil Count", 0.5, 15.0),
        "description": "Calculated absolute neutrophils",
    },
    "ALC": {
        "default": (1.0, 4.5, "10^9/L", "Absolute Lymphocyte Count", 0.5, 10.0),
        "description": "Calculated absolute lymphocytes",
    },
    
    # LFT Parameters
    "ALT": {
        "default": (7.0, 56.0, "U/L", "Alanine Aminotransferase", 5.0, 500.0),
        "description": "Liver enzyme (hepatocellular)",
    },
    "AST": {
        "default": (10.0, 40.0, "U/L", "Aspartate Aminotransferase", 5.0, 500.0),
        "description": "Liver enzyme (hepatocellular)",
    },
    "ALP": {
        "default": (44.0, 147.0, "U/L", "Alkaline Phosphatase", 20.0, 500.0),
        "description": "Biliary enzyme",
    },
    "GGT": {
        "male": (10.0, 71.0, "U/L", "Gamma-Glutamyl Transferase", 5.0, 500.0),
        "female": (6.0, 42.0, "U/L", "Gamma-Glutamyl Transferase", 5.0, 500.0),
        "description": "Biliary/liver enzyme",
    },
    "LDH": {
        "default": (140.0, 280.0, "U/L", "Lactate Dehydrogenase", 100.0, 1000.0),
        "description": "Cellular metabolism enzyme",
    },
    "Total_Bilirubin": {
        "default": (0.1, 1.2, "mg/dL", "Total Bilirubin", 0.0, 5.0),
        "description": "Bile pigment (total)",
    },
    "Direct_Bilirubin": {
        "default": (0.0, 0.3, "mg/dL", "Direct Bilirubin", 0.0, 2.0),
        "description": "Conjugated bilirubin",
    },
    "Indirect_Bilirubin": {
        "default": (0.2, 0.9, "mg/dL", "Indirect Bilirubin", 0.0, 3.0),
        "description": "Unconjugated bilirubin",
    },
    "Total_Protein": {
        "default": (6.0, 8.3, "g/dL", "Total Protein", 4.0, 10.0),
        "description": "Total blood proteins",
    },
    "Albumin": {
        "default": (3.4, 5.4, "g/dL", "Albumin", 2.0, 6.0),
        "description": "Major blood protein",
    },
    "Globulin": {
        "default": (2.0, 3.5, "g/dL", "Globulin", 1.0, 5.0),
        "description": "Non-albumin proteins",
    },
    "AG_Ratio": {
        "default": (1.0, 2.2, "ratio", "Albumin/Globulin Ratio", 0.5, 3.0),
        "description": "Albumin to globulin ratio",
    },
    "PT": {
        "default": (11.0, 13.5, "seconds", "Prothrombin Time", 10.0, 20.0),
        "description": "Coagulation time",
    },
    "INR": {
        "default": (0.8, 1.2, "ratio", "International Normalized Ratio", 0.5, 5.0),
        "description": "Standardized PT ratio",
    },
    "APTT": {
        "default": (25.0, 35.0, "seconds", "Activated Partial Thromboplastin Time", 20.0, 60.0),
        "description": "Intrinsic coagulation pathway",
    },
    "Serum_Ammonia": {
        "default": (15.0, 45.0, "μmol/L", "Serum Ammonia", 10.0, 100.0),
        "description": "Protein metabolism byproduct",
    },
    
    # KFT/Renal Parameters
    "Serum_Creatinine": {
        "male": (0.7, 1.3, "mg/dL", "Serum Creatinine", 0.3, 5.0),
        "female": (0.6, 1.1, "mg/dL", "Serum Creatinine", 0.3, 5.0),
        "description": "Kidney function marker",
    },
    "BUN": {
        "default": (7.0, 20.0, "mg/dL", "Blood Urea Nitrogen", 5.0, 100.0),
        "description": "Nitrogenous waste",
    },
    "Serum_Urea": {
        "default": (15.0, 45.0, "mg/dL", "Serum Urea", 10.0, 200.0),
        "description": "Urea in blood",
    },
    "Serum_Uric_Acid": {
        "male": (3.5, 7.2, "mg/dL", "Serum Uric Acid", 2.0, 15.0),
        "female": (2.6, 6.0, "mg/dL", "Serum Uric Acid", 2.0, 15.0),
        "description": "Purine metabolism end product",
    },
    "eGFR": {
        "default": (90.0, 120.0, "mL/min/1.73m²", "Estimated Glomerular Filtration Rate", 15.0, 150.0),
        "description": "Kidney filtration rate",
    },
    "Serum_Sodium": {
        "default": (135.0, 145.0, "mEq/L", "Serum Sodium", 120.0, 160.0),
        "description": "Electrolyte balance",
    },
    "Serum_Potassium": {
        "default": (3.5, 5.0, "mEq/L", "Serum Potassium", 2.5, 6.5),
        "description": "Electrolyte balance",
    },
    "Serum_Chloride": {
        "default": (98.0, 106.0, "mEq/L", "Serum Chloride", 80.0, 120.0),
        "description": "Electrolyte balance",
    },
    "Serum_Bicarbonate": {
        "default": (22.0, 29.0, "mEq/L", "Serum Bicarbonate", 10.0, 40.0),
        "description": "Acid-base balance",
    },
    "Serum_Calcium": {
        "default": (8.5, 10.5, "mg/dL", "Serum Calcium", 6.0, 14.0),
        "description": "Bone/nerve/muscle function",
    },
    "Ionised_Calcium": {
        "default": (4.5, 5.6, "mg/dL", "Ionized Calcium", 3.0, 7.0),
        "description": "Biologically active calcium",
    },
    "Serum_Phosphorus": {
        "default": (2.5, 4.5, "mg/dL", "Serum Phosphorus", 1.0, 8.0),
        "description": "Bone/mineral metabolism",
    },
    "Serum_Magnesium": {
        "default": (1.7, 2.2, "mg/dL", "Serum Magnesium", 1.0, 4.0),
        "description": "Enzyme cofactor",
    },
    "ACR": {
        "default": (0.0, 30.0, "mg/g", "Albumin-to-Creatinine Ratio", 0.0, 300.0),
        "description": "Early kidney damage marker",
    },
    "Urine_Microalbumin": {
        "default": (0.0, 30.0, "mg/L", "Urine Microalbumin", 0.0, 300.0),
        "description": "Early proteinuria",
    },
    "Cystatin_C": {
        "default": (0.5, 1.0, "mg/L", "Cystatin C", 0.3, 2.0),
        "description": "Kidney function marker",
    },
    
    # Lipid Profile
    "Total_Cholesterol": {
        "default": (0.0, 200.0, "mg/dL", "Total Cholesterol", 0.0, 400.0),
        "description": "Cardiovascular risk marker",
        "optimal": 200.0,
    },
    "HDL_Cholesterol": {
        "male": (40.0, 60.0, "mg/dL", "HDL Cholesterol", 20.0, 100.0),
        "female": (50.0, 60.0, "mg/dL", "HDL Cholesterol", 20.0, 100.0),
        "description": "Good cholesterol",
        "optimal": 60.0,
    },
    "LDL_Cholesterol": {
        "default": (0.0, 100.0, "mg/dL", "LDL Cholesterol", 0.0, 300.0),
        "description": "Bad cholesterol",
        "optimal": 100.0,
    },
    "VLDL_Cholesterol": {
        "default": (5.0, 40.0, "mg/dL", "VLDL Cholesterol", 0.0, 100.0),
        "description": "Triglyceride-rich lipoprotein",
    },
    "Triglycerides": {
        "default": (0.0, 150.0, "mg/dL", "Triglycerides", 0.0, 1000.0),
        "description": "Blood fats",
        "optimal": 150.0,
    },
    "Non_HDL_Cholesterol": {
        "default": (0.0, 130.0, "mg/dL", "Non-HDL Cholesterol", 0.0, 300.0),
        "description": "Atherogenic cholesterol",
    },
    "TC_HDL_Ratio": {
        "default": (0.0, 4.0, "ratio", "Total Cholesterol/HDL Ratio", 0.0, 10.0),
        "description": "Cardiovascular risk ratio",
        "optimal": 3.5,
    },
    "LDL_HDL_Ratio": {
        "default": (0.0, 2.0, "ratio", "LDL/HDL Ratio", 0.0, 5.0),
        "description": "Atherogenic ratio",
    },
    "Lipoprotein_a": {
        "default": (0.0, 30.0, "mg/dL", "Lipoprotein(a)", 0.0, 100.0),
        "description": "Genetic cardiovascular risk",
    },
    "ApoA1": {
        "default": (100.0, 180.0, "mg/dL", "Apolipoprotein A-I", 50.0, 250.0),
        "description": "HDL structural protein",
    },
    "ApoB": {
        "default": (60.0, 130.0, "mg/dL", "Apolipoprotein B", 30.0, 200.0),
        "description": "LDL structural protein",
    },
    
    # Diabetes
    "Fasting_Blood_Glucose": {
        "default": (70.0, 100.0, "mg/dL", "Fasting Blood Glucose", 50.0, 400.0),
        "description": "Blood sugar (fasting)",
    },
    "Postprandial_Glucose": {
        "default": (70.0, 140.0, "mg/dL", "Postprandial Glucose", 50.0, 400.0),
        "description": "Blood sugar (2h after meal)",
    },
    "Random_Blood_Glucose": {
        "default": (70.0, 140.0, "mg/dL", "Random Blood Glucose", 50.0, 400.0),
        "description": "Blood sugar (random)",
    },
    "HbA1c": {
        "default": (4.0, 5.6, "%", "HbA1c", 3.0, 15.0),
        "description": "3-month glucose average",
    },
    "eAG": {
        "default": (70.0, 126.0, "mg/dL", "Estimated Average Glucose", 50.0, 400.0),
        "description": "Estimated average glucose",
    },
    "Fasting_Insulin": {
        "default": (2.0, 25.0, "μU/mL", "Fasting Insulin", 1.0, 50.0),
        "description": "Insulin level (fasting)",
    },
    "HOMA_IR": {
        "default": (0.0, 2.5, "ratio", "HOMA-IR", 0.0, 10.0),
        "description": "Insulin resistance index",
    },
    "C_Peptide": {
        "default": (0.8, 3.1, "ng/mL", "C-Peptide", 0.3, 5.0),
        "description": "Endogenous insulin production",
    },
    
    # Thyroid
    "TSH": {
        "default": (0.4, 4.0, "mIU/L", "TSH", 0.01, 20.0),
        "description": "Thyroid stimulating hormone",
    },
    "Free_T3": {
        "default": (2.3, 4.2, "pg/mL", "Free T3", 1.0, 10.0),
        "description": "Active thyroid hormone (T3)",
    },
    "Total_T3": {
        "default": (80.0, 200.0, "ng/dL", "Total T3", 50.0, 400.0),
        "description": "Total T3 (bound+free)",
    },
    "Free_T4": {
        "default": (0.8, 1.8, "ng/dL", "Free T4", 0.3, 5.0),
        "description": "Active thyroid hormone (T4)",
    },
    "Total_T4": {
        "default": (5.0, 12.0, "μg/dL", "Total T4", 2.0, 20.0),
        "description": "Total T4 (bound+free)",
    },
    "Anti_TPO": {
        "default": (0.0, 34.0, "IU/mL", "Anti-TPO Antibodies", 0.0, 1000.0),
        "description": "Thyroid peroxidase antibodies",
    },
    "Anti_Thyroglobulin": {
        "default": (0.0, 40.0, "IU/mL", "Anti-Thyroglobulin Antibodies", 0.0, 1000.0),
        "description": "Thyroglobulin antibodies",
    },
    "TSH_Receptor_Ab": {
        "default": (0.0, 1.0, "IU/L", "TSH Receptor Antibodies", 0.0, 10.0),
        "description": "Graves' disease marker",
    },
    "Thyroglobulin": {
        "default": (1.5, 38.5, "ng/mL", "Thyroglobulin", 0.0, 100.0),
        "description": "Thyroid cancer marker",
    },
    "Calcitonin": {
        "default": (0.0, 8.4, "pg/mL", "Calcitonin", 0.0, 100.0),
        "description": "Medullary thyroid cancer marker",
    },
    
    # Vitamins
    "Vitamin_D_25OH": {
        "default": (30.0, 100.0, "ng/mL", "Vitamin D (25-OH)", 10.0, 150.0),
        "description": "Vitamin D status",
    },
    "Vitamin_D3": {
        "default": (20.0, 80.0, "ng/mL", "Vitamin D3", 10.0, 150.0),
        "description": "Cholecalciferol level",
    },
    "PTH": {
        "default": (10.0, 65.0, "pg/mL", "Parathyroid Hormone", 5.0, 200.0),
        "description": "Calcium regulation hormone",
    },
    "Vitamin_B12": {
        "default": (200.0, 900.0, "pg/mL", "Vitamin B12", 100.0, 2000.0),
        "description": "Cobalamin level",
    },
    "Serum_Folate": {
        "default": (3.0, 20.0, "ng/mL", "Serum Folate", 1.0, 50.0),
        "description": "Folic acid level",
    },
    "RBC_Folate": {
        "default": (140.0, 628.0, "ng/mL", "RBC Folate", 50.0, 1000.0),
        "description": "Red cell folate",
    },
    "Homocysteine": {
        "default": (4.0, 15.0, "μmol/L", "Homocysteine", 2.0, 50.0),
        "description": "Amino acid (cardiovascular risk)",
    },
    
    # Rheumatology
    "RA_Factor": {
        "default": (0.0, 14.0, "IU/mL", "Rheumatoid Factor", 0.0, 200.0),
        "description": "Rheumatoid arthritis marker",
    },
    "Anti_CCP": {
        "default": (0.0, 20.0, "U/mL", "Anti-CCP Antibodies", 0.0, 200.0),
        "description": "Specific RA marker",
    },
    "CRP": {
        "default": (0.0, 10.0, "mg/L", "C-Reactive Protein", 0.0, 200.0),
        "description": "Acute inflammation marker",
    },
    "hs_CRP": {
        "default": (0.0, 3.0, "mg/L", "hs-CRP", 0.0, 10.0),
        "description": "Cardiovascular risk marker",
    },
    "Anti_dsDNA": {
        "default": (0.0, 100.0, "IU/mL", "Anti-dsDNA Antibodies", 0.0, 1000.0),
        "description": "SLE specific marker",
    },
    "C3_Complement": {
        "default": (90.0, 180.0, "mg/dL", "Complement C3", 50.0, 300.0),
        "description": "Immune system component",
    },
    "C4_Complement": {
        "default": (10.0, 40.0, "mg/dL", "Complement C4", 5.0, 100.0),
        "description": "Immune system component",
    },
    "ASO_Titre": {
        "default": (0.0, 200.0, "IU/mL", "ASO Titre", 0.0, 1000.0),
        "description": "Streptococcal infection marker",
    },
    
    # Iron Studies
    "Ferritin": {
        "male": (30.0, 400.0, "ng/mL", "Ferritin", 10.0, 1000.0),
        "female": (15.0, 150.0, "ng/mL", "Ferritin", 10.0, 1000.0),
        "description": "Iron stores",
    },
    "Serum_Iron": {
        "male": (65.0, 176.0, "μg/dL", "Serum Iron", 30.0, 300.0),
        "female": (50.0, 170.0, "μg/dL", "Serum Iron", 30.0, 300.0),
        "description": "Circulating iron",
    },
    "TIBC": {
        "default": (250.0, 400.0, "μg/dL", "Total Iron Binding Capacity", 200.0, 500.0),
        "description": "Iron transport capacity",
    },
    "Transferrin_Saturation": {
        "default": (20.0, 50.0, "%", "Transferrin Saturation", 10.0, 80.0),
        "description": "Iron availability",
    },
    
    # Oncology Markers
    "PSA_Total": {
        "default": (0.0, 4.0, "ng/mL", "Total PSA", 0.0, 50.0),
        "description": "Prostate cancer marker",
    },
    "PSA_Free": {
        "default": (0.0, 2.5, "ng/mL", "Free PSA", 0.0, 10.0),
        "description": "Unbound PSA",
    },
    "CEA": {
        "default": (0.0, 3.0, "ng/mL", "CEA", 0.0, 50.0),
        "description": "Colorectal cancer marker",
    },
    "CA_125": {
        "default": (0.0, 35.0, "U/mL", "CA-125", 0.0, 500.0),
        "description": "Ovarian cancer marker",
    },
    "CA_19_9": {
        "default": (0.0, 37.0, "U/mL", "CA 19-9", 0.0, 500.0),
        "description": "Pancreatic cancer marker",
    },
    "CA_15_3": {
        "default": (0.0, 30.0, "U/mL", "CA 15-3", 0.0, 300.0),
        "description": "Breast cancer marker",
    },
    "CA_72_4": {
        "default": (0.0, 6.9, "U/mL", "CA 72-4", 0.0, 100.0),
        "description": "Gastric cancer marker",
    },
    "AFP": {
        "default": (0.0, 10.0, "ng/mL", "Alpha-Fetoprotein", 0.0, 500.0),
        "description": "Liver cancer marker",
    },
    "Beta_HCG": {
        "default": (0.0, 5.0, "mIU/mL", "Beta-HCG", 0.0, 10000.0),
        "description": "Pregnancy/cancer marker",
    },
    "NSE": {
        "default": (0.0, 12.5, "ng/mL", "NSE", 0.0, 100.0),
        "description": "Neuroendocrine marker",
    },
    "CYFRA_21_1": {
        "default": (0.0, 3.3, "ng/mL", "CYFRA 21-1", 0.0, 50.0),
        "description": "Lung cancer marker",
    },
    "SCC_Antigen": {
        "default": (0.0, 1.5, "ng/mL", "SCC Antigen", 0.0, 20.0),
        "description": "Squamous cell carcinoma marker",
    },
    "Chromogranin_A": {
        "default": (0.0, 93.0, "ng/mL", "Chromogranin A", 0.0, 500.0),
        "description": "Neuroendocrine tumor marker",
    },
    "HE4": {
        "default": (0.0, 70.0, "pmol/L", "HE4", 0.0, 500.0),
        "description": "Ovarian cancer marker",
    },
    
    # Urine Analysis
    "Urine_pH": {
        "default": (5.0, 8.0, "pH", "Urine pH", 4.0, 9.0),
        "description": "Urine acidity",
    },
    "Urine_Specific_Gravity": {
        "default": (1.005, 1.030, "ratio", "Specific Gravity", 1.000, 1.040),
        "description": "Urine concentration",
    },
    "Urine_Pus_Cells": {
        "default": (0.0, 5.0, "/HPF", "Pus Cells", 0.0, 50.0),
        "description": "White cells in urine",
    },
    "Urine_RBC": {
        "default": (0.0, 3.0, "/HPF", "Red Blood Cells", 0.0, 50.0),
        "description": "Red cells in urine",
    },
}


# Panel parameter mappings
PANEL_PARAMETER_MAP = {
    "CBC": [
        "RBC", "Hemoglobin", "Hematocrit", "MCV", "MCH", "MCHC", 
        "RDW_CV", "RDW_SD", "WBC", "Neutrophils", "Lymphocytes", 
        "Monocytes", "Eosinophils", "Basophils", "Bands", "Platelets", 
        "MPV", "PDW", "PCT", "ESR", "Reticulocytes", "ANC", "ALC"
    ],
    "LFT": [
        "ALT", "AST", "ALP", "GGT", "LDH", "Total_Bilirubin", 
        "Direct_Bilirubin", "Indirect_Bilirubin", "Total_Protein", 
        "Albumin", "Globulin", "AG_Ratio", "PT", "INR", "APTT", "Serum_Ammonia"
    ],
    "KFT": [
        "Serum_Creatinine", "BUN", "Serum_Urea", "Serum_Uric_Acid", 
        "eGFR", "Serum_Sodium", "Serum_Potassium", "Serum_Chloride", 
        "Serum_Bicarbonate", "Serum_Calcium", "Ionised_Calcium", 
        "Serum_Phosphorus", "Serum_Magnesium", "ACR", "Urine_Microalbumin", "Cystatin_C"
    ],
    "LIPID": [
        "Total_Cholesterol", "HDL_Cholesterol", "LDL_Cholesterol", 
        "VLDL_Cholesterol", "Triglycerides", "Non_HDL_Cholesterol", 
        "TC_HDL_Ratio", "LDL_HDL_Ratio", "Lipoprotein_a", "ApoA1", "ApoB"
    ],
    "DIABETES": [
        "Fasting_Blood_Glucose", "Postprandial_Glucose", "Random_Blood_Glucose", 
        "HbA1c", "eAG", "Fasting_Insulin", "HOMA_IR", "C_Peptide"
    ],
    "TFT": [
        "TSH", "Free_T3", "Total_T3", "Free_T4", "Total_T4", 
        "Anti_TPO", "Anti_Thyroglobulin", "TSH_Receptor_Ab", "Thyroglobulin", "Calcitonin"
    ],
    "VITD": [
        "Vitamin_D_25OH", "Vitamin_D3", "PTH"
    ],
    "VITB12": [
        "Vitamin_B12", "Serum_Folate", "RBC_Folate", "Homocysteine"
    ],
    "URINE": [
        "Urine_pH", "Urine_Specific_Gravity", "Urine_Pus_Cells", "Urine_RBC"
    ],
    "RHEUMATOID": [
        "RA_Factor", "Anti_CCP", "CRP", "hs_CRP", "Anti_dsDNA", 
        "C3_Complement", "C4_Complement", "ASO_Titre"
    ],
    "ONCOLOGY": [
        "PSA_Total", "PSA_Free", "CEA", "CA_125", "CA_19_9", 
        "CA_15_3", "CA_72_4", "AFP", "Beta_HCG", "NSE", 
        "CYFRA_21_1", "SCC_Antigen", "Chromogranin_A", "HE4"
    ],
    "IRON": [
        "Ferritin", "Serum_Iron", "TIBC", "Transferrin_Saturation"
    ],
}

PANEL_LABELS = {
    "CBC": "Complete Blood Count",
    "LFT": "Liver Function Test",
    "KFT": "Kidney Function Test",
    "LIPID": "Lipid Profile",
    "DIABETES": "Diabetes Panel",
    "TFT": "Thyroid Function Test",
    "VITD": "Vitamin D Panel",
    "VITB12": "Vitamin B12/Folate Panel",
    "URINE": "Urine Analysis",
    "RHEUMATOID": "Rheumatology Panel",
    "ONCOLOGY": "Oncology Markers",
    "IRON": "Iron Studies",
}

PANEL_ICONS = {
    "CBC": "🩸",
    "LFT": "🫁",
    "KFT": "🫘",
    "LIPID": "🫀",
    "DIABETES": "🍯",
    "TFT": "🦋",
    "VITD": "☀️",
    "VITB12": "🔋",
    "URINE": "🧪",
    "RHEUMATOID": "🦴",
    "ONCOLOGY": "🔬",
    "IRON": "⚙️",
}


def get_reference_range(param_key: str, sex: str = "male", age: int = 35) -> Optional[Tuple]:
    """
    Get reference range for a parameter considering sex and age.
    
    Args:
        param_key: Standard parameter key
        sex: 'male' or 'female'
        age: Patient age in years
        
    Returns:
        Tuple of (min, max, unit, description, critical_low, critical_high) or None
    """
    ref = REFERENCE_RANGES.get(param_key)
    if not ref:
        return None
    
    # Check for sex-specific ranges
    if sex.lower() in ref:
        return ref[sex.lower()]
    elif "default" in ref:
        return ref["default"]
    else:
        # Try to find any available range
        for key in ["male", "female", "default"]:
            if key in ref:
                return ref[key]
    
    return None


def calculate_severity(value: float, ref_min: float, ref_max: float, 
                      critical_low: float, critical_high: float) -> Tuple[int, str, str]:
    """
    Calculate severity level and status for a lab value.
    
    Returns:
        Tuple of (severity_code, status, flag)
    """
    # Check critical values first
    if value < critical_low:
        return SEV_CRITICAL, STATUS_CRITICALLY_LOW, "↓↓"
    if value > critical_high:
        return SEV_CRITICAL, STATUS_CRITICALLY_HIGH, "↑↑"
    
    # Check normal range
    if ref_min <= value <= ref_max:
        return SEV_NORMAL, STATUS_NORMAL, "✓"
    
    # Calculate deviation percentage
    if value < ref_min:
        deviation = (ref_min - value) / ref_min if ref_min != 0 else 0
        if deviation <= 0.1:
            return SEV_MILD, STATUS_LOW, "↓"
        elif deviation <= 0.25:
            return SEV_MODERATE, STATUS_LOW, "↓"
        else:
            return SEV_SEVERE, STATUS_LOW, "↓↓"
    else:  # value > ref_max
        deviation = (value - ref_max) / ref_max if ref_max != 0 else 0
        if deviation <= 0.1:
            return SEV_MILD, STATUS_HIGH, "↑"
        elif deviation <= 0.25:
            return SEV_MODERATE, STATUS_HIGH, "↑"
        else:
            return SEV_SEVERE, STATUS_HIGH, "↑↑"


def generate_interpretation(param_key: str, value: float, status: str, 
                           ref_data: Dict) -> str:
    """
    Generate clinical interpretation for a parameter.
    """
    interpretations = {
        # CBC
        "Hemoglobin": {
            STATUS_LOW: "Indicates anemia. Consider iron, B12, folate deficiency or chronic disease.",
            STATUS_HIGH: "Possible polycythemia, dehydration, or lung disease.",
            STATUS_CRITICALLY_LOW: "Severe anemia - immediate evaluation required.",
            STATUS_CRITICALLY_HIGH: "Polycythemia - evaluate for myeloproliferative disorder.",
        },
        "WBC": {
            STATUS_LOW: "Leukopenia - increased infection risk. Consider viral infection, drugs, or bone marrow disorder.",
            STATUS_HIGH: "Leukocytosis - suggests infection, inflammation, or stress response.",
            STATUS_CRITICALLY_LOW: "Critical leukopenia - high infection risk.",
            STATUS_CRITICALLY_HIGH: "Critical leukocytosis - possible leukemia or severe infection.",
        },
        "Platelets": {
            STATUS_LOW: "Thrombocytopenia - bleeding risk. Monitor for petechiae/bruising.",
            STATUS_HIGH: "Thrombocytosis - reactive or myeloproliferative.",
            STATUS_CRITICALLY_LOW: "Critical thrombocytopenia - spontaneous bleeding risk.",
            STATUS_CRITICALLY_HIGH: "Critical thrombocytosis - thrombosis risk.",
        },
        # LFT
        "ALT": {
            STATUS_HIGH: "Hepatocellular injury. Consider hepatitis, fatty liver, or drug toxicity.",
            STATUS_CRITICALLY_HIGH: "Severe hepatocellular damage - urgent evaluation.",
        },
        "AST": {
            STATUS_HIGH: "Hepatocellular injury. AST>ALT suggests alcoholic liver disease or cirrhosis.",
            STATUS_CRITICALLY_HIGH: "Severe hepatocellular damage.",
        },
        "ALP": {
            STATUS_HIGH: "Cholestasis or biliary obstruction. Check GGT to confirm hepatic origin.",
        },
        "Total_Bilirubin": {
            STATUS_HIGH: "Jaundice. Evaluate for hemolysis, hepatocellular, or obstructive causes.",
            STATUS_CRITICALLY_HIGH: "Severe hyperbilirubinemia - risk of kernicterus.",
        },
        # KFT
        "Serum_Creatinine": {
            STATUS_HIGH: "Reduced kidney function. Calculate eGFR for staging.",
            STATUS_CRITICALLY_HIGH: "Severe renal impairment - possible acute kidney injury.",
        },
        "eGFR": {
            STATUS_LOW: "Decreased kidney function. Stage CKD and evaluate cause.",
            STATUS_CRITICALLY_LOW: "Kidney failure - urgent nephrology referral.",
        },
        "Serum_Potassium": {
            STATUS_LOW: "Hypokalemia - risk of arrhythmias. Check for diuretic use or GI losses.",
            STATUS_HIGH: "Hyperkalemia - cardiac toxicity risk. Urgent correction needed.",
            STATUS_CRITICALLY_LOW: "Critical hypokalemia - immediate replacement.",
            STATUS_CRITICALLY_HIGH: "Critical hyperkalemia - emergency treatment required.",
        },
        # Lipid
        "LDL_Cholesterol": {
            STATUS_HIGH: "Increased cardiovascular risk. Consider statin therapy.",
        },
        "HDL_Cholesterol": {
            STATUS_LOW: "Low protective cholesterol. Increased cardiovascular risk.",
        },
        "Triglycerides": {
            STATUS_HIGH: "Elevated triglycerides. Risk of pancreatitis if >500.",
            STATUS_CRITICALLY_HIGH: "Severe hypertriglyceridemia - pancreatitis risk.",
        },
        # Diabetes
        "HbA1c": {
            STATUS_HIGH: "Poor glycemic control. Target <7% for most diabetics.",
            STATUS_CRITICALLY_HIGH: "Very poor control - complication risk high.",
        },
        "Fasting_Blood_Glucose": {
            STATUS_HIGH: "Impaired fasting glucose or diabetes.",
            STATUS_CRITICALLY_HIGH: "Severe hyperglycemia - DKA risk.",
        },
        # Thyroid
        "TSH": {
            STATUS_LOW: "Hyperthyroidism or suppressed TSH. Check free T4/T3.",
            STATUS_HIGH: "Hypothyroidism. Check free T4 and antibodies.",
            STATUS_CRITICALLY_HIGH: "Severe hypothyroidism - myxedema risk.",
        },
        "Free_T4": {
            STATUS_LOW: "Hypothyroidism if TSH high, or non-thyroidal illness.",
            STATUS_HIGH: "Hyperthyroidism if TSH low.",
        },
        # Vitamins
        "Vitamin_D_25OH": {
            STATUS_LOW: "Vitamin D deficiency. Consider supplementation.",
            STATUS_CRITICALLY_LOW: "Severe deficiency - osteomalacia risk.",
        },
        "Vitamin_B12": {
            STATUS_LOW: "B12 deficiency - risk of megaloblastic anemia and neuropathy.",
            STATUS_CRITICALLY_LOW: "Severe deficiency - neurological complications.",
        },
    }
    
    if param_key in interpretations and status in interpretations[param_key]:
        return interpretations[param_key][status]
    
    # Generic interpretations
    if "Critical" in status:
        return f"Critical value - immediate clinical attention required."
    elif status == STATUS_HIGH:
        return f"Elevated {ref_data.get('description', param_key)}."
    elif status == STATUS_LOW:
        return f"Low {ref_data.get('description', param_key)}."
    
    return ""


def calculate_derived_values(param_key: str, value: float, all_values: Dict) -> Dict[str, Dict]:
    """
    Calculate derived values based on other parameters.
    """
    derived = {}
    
    if param_key == "Serum_Creatinine":
        # Calculate eGFR using CKD-EPI formula if not present
        if "eGFR" not in all_values and "Serum_Creatinine" in all_values:
            creatinine = all_values["Serum_Creatinine"]
            # Simplified CKD-EPI (would need age, sex, race for accurate calculation)
            derived["eGFR_estimated"] = {
                "value": 175 * (creatinine ** -1.154) * (65 ** -0.203),  # Placeholder age
                "unit": "mL/min/1.73m²",
                "description": "Estimated GFR (CKD-EPI)",
                "reference": ">90",
                "interpretation": "Estimated - use calculated eGFR if available"
            }
    
    elif param_key == "Fasting_Blood_Glucose" and "Fasting_Insulin" in all_values:
        # Calculate HOMA-IR
        glucose = value
        insulin = all_values["Fasting_Insulin"]
        homa_ir = (glucose * insulin) / 405
        derived["HOMA_IR_calculated"] = {
            "value": homa_ir,
            "unit": "ratio",
            "description": "HOMA-IR (calculated)",
            "reference": "<2.5",
            "interpretation": "Insulin resistance index"
        }
    
    elif param_key == "Total_Cholesterol" and "HDL_Cholesterol" in all_values:
        # Calculate Non-HDL
        non_hdl = value - all_values["HDL_Cholesterol"]
        derived["Non_HDL_calculated"] = {
            "value": non_hdl,
            "unit": "mg/dL",
            "description": "Non-HDL Cholesterol (calculated)",
            "reference": "<130",
            "interpretation": "Atherogenic cholesterol fraction"
        }
        
        # Calculate TC/HDL ratio
        ratio = value / all_values["HDL_Cholesterol"] if all_values["HDL_Cholesterol"] > 0 else 0
        derived["TC_HDL_Ratio_calculated"] = {
            "value": ratio,
            "unit": "ratio",
            "description": "TC/HDL Ratio (calculated)",
            "reference": "<4.0",
            "interpretation": "Cardiovascular risk ratio"
        }
    
    return derived


def generate_recommendations(panel_key: str, results: Dict, abnormal: List[str], critical: List[str]) -> List[str]:
    """
    Generate clinical recommendations based on panel results.
    """
    recommendations = []
    
    # Critical values first
    for crit in critical:
        r = results[crit]
        recommendations.append(f"🚨 URGENT: {r['description']} is critically {r['status'].lower()}. Immediate clinical correlation required.")
    
    # Panel-specific recommendations
    if panel_key == "CBC":
        if "Hemoglobin" in abnormal:
            hgb = results["Hemoglobin"]
            if STATUS_LOW in hgb["status"]:
                recommendations.append("⚠️ Evaluate for iron deficiency (ferritin, TIBC), B12/folate deficiency, or chronic disease.")
        if "WBC" in abnormal:
            recommendations.append("⚠️ Correlate with clinical symptoms of infection/inflammation.")
        if "Platelets" in abnormal:
            recommendations.append("⚠️ Review peripheral smear. Consider hematology referral if persistent.")
    
    elif panel_key == "LFT":
        if any(p in abnormal for p in ["ALT", "AST"]):
            recommendations.append("⚠️ Evaluate for viral hepatitis, NAFLD, alcohol use, or drug-induced injury.")
        if "ALP" in abnormal or "GGT" in abnormal:
            recommendations.append("⚠️ If cholestatic pattern, consider abdominal ultrasound.")
        if "Total_Bilirubin" in abnormal:
            recommendations.append("⚠️ Fractionate bilirubin and check for hemolysis if indirect elevated.")
    
    elif panel_key == "KFT":
        if "Serum_Creatinine" in abnormal or "eGFR" in abnormal:
            recommendations.append("⚠️ Stage CKD if eGFR <60 for >3 months. Evaluate for AKI causes if acute rise.")
        if "Serum_Potassium" in abnormal:
            recommendations.append("⚠️ Check ECG for potassium abnormalities. Review medications (ACEi, ARB, diuretics).")
    
    elif panel_key == "LIPID":
        if "LDL_Cholesterol" in abnormal or "Non_HDL_Cholesterol" in abnormal:
            recommendations.append("⚠️ Calculate 10-year ASCVD risk. Consider statin therapy if elevated risk.")
        if "Triglycerides" in abnormal:
            tg = results.get("Triglycerides", {})
            if tg.get("value", 0) > 500:
                recommendations.append("🚨 Triglycerides >500 - pancreatitis risk. Initiate fibrate therapy.")
    
    elif panel_key == "DIABETES":
        if "HbA1c" in abnormal:
            recommendations.append("⚠️ Optimize glycemic control. Target HbA1c <7% for most patients.")
        if "HOMA_IR" in abnormal or (results.get("Fasting_Insulin", {}).get("value", 0) > 15):
            recommendations.append("⚠️ Insulin resistance present - consider metformin and lifestyle intervention.")
    
    elif panel_key == "TFT":
        if "TSH" in abnormal:
            recommendations.append("⚠️ Check free T4/T3 to determine thyroid status. Consider thyroid antibodies.")
        if any(p in abnormal for p in ["Anti_TPO", "Anti_Thyroglobulin"]):
            recommendations.append("⚠️ Autoimmune thyroiditis likely. Monitor TSH annually.")
    
    elif panel_key == "VITD":
        if "Vitamin_D_25OH" in abnormal:
            recommendations.append("⚠️ Vitamin D supplementation recommended. Recheck in 3 months.")
    
    elif panel_key == "VITB12":
        if "Vitamin_B12" in abnormal:
            recommendations.append("⚠️ B12 supplementation (oral or IM). Check intrinsic factor if deficient.")
        if "Homocysteine" in abnormal and results["Homocysteine"].get("value", 0) > 15:
            recommendations.append("⚠️ Elevated homocysteine - cardiovascular risk. Ensure adequate B12/folate/B6.")
    
    elif panel_key == "RHEUMATOID":
        if "Anti_CCP" in abnormal or "RA_Factor" in abnormal:
            recommendations.append("⚠️ Early rheumatoid arthritis - consider DMARD therapy referral.")
        if "Anti_dsDNA" in abnormal:
            recommendations.append("⚠️ SLE marker positive - refer to rheumatology.")
    
    elif panel_key == "ONCOLOGY":
        recommendations.append("⚠️ Tumor markers must be correlated with imaging and clinical context.")
        if any(p in abnormal for p in ["PSA_Total", "CEA", "CA_125"]):
            recommendations.append("⚠️ Elevated tumor marker - consider appropriate imaging workup.")
    
    if not recommendations:
        recommendations.append("✓ No urgent recommendations. Routine follow-up as clinically indicated.")
    
    return recommendations


def analyze_parameter(param_key: str, value: float, sex: str = "male", 
                     age: int = 35, all_values: Dict = None) -> Optional[Dict]:
    """
    Analyze a single lab parameter against reference ranges.
    
    Returns:
        Dictionary with analysis results or None if parameter not recognized
    """
    ref = get_reference_range(param_key, sex, age)
    if not ref:
        return None
    
    ref_min, ref_max, unit, description, crit_low, crit_high = ref
    ref_data = REFERENCE_RANGES.get(param_key, {})
    
    # Calculate severity
    severity, status, flag = calculate_severity(value, ref_min, ref_max, crit_low, crit_high)
    
    # Generate interpretation
    interpretation = generate_interpretation(param_key, value, status, ref_data)
    
    # Calculate derived values
    derived = calculate_derived_values(param_key, value, all_values or {})
    
    return {
        "key": param_key,
        "value": value,
        "unit": unit,
        "description": description,
        "reference_min": ref_min,
        "reference_max": ref_max,
        "critical_low": crit_low,
        "critical_high": crit_high,
        "status": status,
        "severity": severity,
        "flag": flag,
        "interpretation": interpretation,
        "derived": derived,
    }


def analyze_panel(panel_key: str, values: Dict, sex: str = "male", 
                 age: int = 35) -> Dict:
    """
    Analyze all parameters in a clinical panel.
    
    Args:
        panel_key: Panel identifier (e.g., 'CBC', 'LFT')
        values: Dictionary of parameter values
        sex: Patient sex
        age: Patient age
        
    Returns:
        Panel analysis results
    """
    panel_params = PANEL_PARAMETER_MAP.get(panel_key, [])
    results = {}
    abnormal = []
    critical = []
    max_severity = SEV_NORMAL
    
    # Analyze each parameter in the panel
    for param_key in panel_params:
        if param_key not in values:
            continue
        
        value = values[param_key]
        if not isinstance(value, (int, float)) or math.isnan(value):
            continue
        
        analysis = analyze_parameter(param_key, float(value), sex, age, values)
        if analysis:
            results[param_key] = analysis
            
            if analysis["severity"] > SEV_NORMAL:
                abnormal.append(param_key)
                if analysis["severity"] >= SEV_CRITICAL:
                    critical.append(param_key)
            
            max_severity = max(max_severity, analysis["severity"])
    
    # Generate summary
    total = len(results)
    summary = f"{total - len(abnormal)}/{total} parameters normal"
    if critical:
        summary += f", {len(critical)} critical"
    elif abnormal:
        summary += f", {len(abnormal)} abnormal"
    
    # Generate recommendations
    recommendations = generate_recommendations(panel_key, results, abnormal, critical)
    
    # Collect derived values
    all_derived = {}
    for r in results.values():
        all_derived.update(r.get("derived", {}))
    
    return {
        "panel": panel_key,
        "panel_name": PANEL_LABELS.get(panel_key, panel_key),
        "results": results,
        "abnormal": abnormal,
        "critical": critical,
        "overall_severity": max_severity,
        "summary": summary,
        "recommendations": recommendations,
        "derived": all_derived,
    }


def analyze_all(values: Dict, sex: str = "male", age: int = 35, 
               active_panels: List[str] = None) -> Dict[str, Dict]:
    """
    Analyze all active panels.
    
    Args:
        values: Dictionary of all lab values
        sex: Patient sex
        age: Patient age
        active_panels: List of panel keys to analyze (default: all)
        
    Returns:
        Dictionary mapping panel keys to analysis results
    """
    if active_panels is None:
        active_panels = list(PANEL_PARAMETER_MAP.keys())
    
    results = {}
    for panel_key in active_panels:
        panel_result = analyze_panel(panel_key, values, sex, age)
        if panel_result["results"]:  # Only include if parameters found
            results[panel_key] = panel_result
    
    return results


def get_overall_severity(all_results: Dict[str, Dict]) -> int:
    """
    Calculate overall severity across all panels.
    
    Returns:
        Maximum severity level found
    """
    max_sev = SEV_NORMAL
    for panel_result in all_results.values():
        max_sev = max(max_sev, panel_result.get("overall_severity", SEV_NORMAL))
    return max_sev
