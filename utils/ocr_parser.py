"""
OCR Parser Module for Lab Report Extraction
============================================
Handles PDF and image processing, text extraction, and parameter parsing
from clinical laboratory reports.
"""

import re
import io
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass

# Try to import optional dependencies
try:
    import pytesseract
    from PIL import Image
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False

try:
    import pdf2image
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False


@dataclass
class ExtractedParameter:
    """Data class for extracted lab parameters."""
    name: str
    value: float
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    status: Optional[str] = None


# Parameter name mappings (OCR variations -> Standard keys)
PARAMETER_ALIASES = {
    # CBC
    "haemoglobin": "Hemoglobin",
    "hemoglobin": "Hemoglobin",
    "hb": "Hemoglobin",
    "hgb": "Hemoglobin",
    "rbc": "RBC",
    "red blood cell": "RBC",
    "red blood cells": "RBC",
    "erythrocytes": "RBC",
    "wbc": "WBC",
    "white blood cell": "WBC",
    "white blood cells": "WBC",
    "leukocytes": "WBC",
    "platelet": "Platelets",
    "platelets": "Platelets",
    "plt": "Platelets",
    "hematocrit": "Hematocrit",
    "hct": "Hematocrit",
    "packed cell volume": "Hematocrit",
    "pcv": "Hematocrit",
    "mcv": "MCV",
    "mean corpuscular volume": "MCV",
    "mch": "MCH",
    "mean corpuscular hemoglobin": "MCH",
    "mchc": "MCHC",
    "mean corpuscular hemoglobin concentration": "MCHC",
    "rdw": "RDW_CV",
    "rdw-cv": "RDW_CV",
    "rdw-sd": "RDW_SD",
    "mpv": "MPV",
    "mean platelet volume": "MPV",
    "pdw": "PDW",
    "pct": "PCT",
    "neutrophils": "Neutrophils",
    "neutrophil": "Neutrophils",
    "lymphocytes": "Lymphocytes",
    "lymphocyte": "Lymphocytes",
    "monocytes": "Monocytes",
    "monocyte": "Monocytes",
    "eosinophils": "Eosinophils",
    "eosinophil": "Eosinophils",
    "basophils": "Basophils",
    "basophil": "Basophils",
    "esr": "ESR",
    "erythrocyte sedimentation rate": "ESR",
    "reticulocytes": "Reticulocytes",
    "retic": "Reticulocytes",
    
    # LFT
    "alt": "ALT",
    "alanine aminotransferase": "ALT",
    "sgpt": "ALT",
    "ast": "AST",
    "aspartate aminotransferase": "AST",
    "sgot": "AST",
    "alp": "ALP",
    "alkaline phosphatase": "ALP",
    "ggt": "GGT",
    "gamma gt": "GGT",
    "gamma-glutamyl transferase": "GGT",
    "bilirubin total": "Total_Bilirubin",
    "total bilirubin": "Total_Bilirubin",
    "bilirubin direct": "Direct_Bilirubin",
    "direct bilirubin": "Direct_Bilirubin",
    "conjugated bilirubin": "Direct_Bilirubin",
    "bilirubin indirect": "Indirect_Bilirubin",
    "indirect bilirubin": "Indirect_Bilirubin",
    "unconjugated bilirubin": "Indirect_Bilirubin",
    "albumin": "Albumin",
    "alb": "Albumin",
    "total protein": "Total_Protein",
    "tp": "Total_Protein",
    "globulin": "Globulin",
    "a/g ratio": "AG_Ratio",
    "ag ratio": "AG_Ratio",
    "albumin/globulin ratio": "AG_Ratio",
    "pt": "PT",
    "prothrombin time": "PT",
    "inr": "INR",
    "international normalized ratio": "INR",
    "aptt": "APTT",
    "activated partial thromboplastin time": "APTT",
    "ptt": "APTT",
    "ldh": "LDH",
    "lactate dehydrogenase": "LDH",
    
    # KFT/Renal
    "creatinine": "Serum_Creatinine",
    "serum creatinine": "Serum_Creatinine",
    "s. creatinine": "Serum_Creatinine",
    "blood urea nitrogen": "BUN",
    "bun": "BUN",
    "urea": "Serum_Urea",
    "blood urea": "Serum_Urea",
    "serum urea": "Serum_Urea",
    "uric acid": "Serum_Uric_Acid",
    "serum uric acid": "Serum_Uric_Acid",
    "s. uric acid": "Serum_Uric_Acid",
    "egfr": "eGFR",
    "estimated gfr": "eGFR",
    "cystatin c": "Cystatin_C",
    "sodium": "Serum_Sodium",
    "serum sodium": "Serum_Sodium",
    "na+": "Serum_Sodium",
    "potassium": "Serum_Potassium",
    "serum potassium": "Serum_Potassium",
    "k+": "Serum_Potassium",
    "chloride": "Serum_Chloride",
    "serum chloride": "Serum_Chloride",
    "cl-": "Serum_Chloride",
    "bicarbonate": "Serum_Bicarbonate",
    "hco3": "Serum_Bicarbonate",
    "calcium": "Serum_Calcium",
    "serum calcium": "Serum_Calcium",
    "ionized calcium": "Ionised_Calcium",
    "ionised calcium": "Ionised_Calcium",
    "phosphorus": "Serum_Phosphorus",
    "serum phosphorus": "Serum_Phosphorus",
    "phosphate": "Serum_Phosphorus",
    "magnesium": "Serum_Magnesium",
    "serum magnesium": "Serum_Magnesium",
    "mg": "Serum_Magnesium",
    "acr": "ACR",
    "albumin/creatinine ratio": "ACR",
    "uacr": "ACR",
    "microalbumin": "Urine_Microalbumin",
    "urine microalbumin": "Urine_Microalbumin",
    
    # Lipid Profile
    "total cholesterol": "Total_Cholesterol",
    "cholesterol total": "Total_Cholesterol",
    "tc": "Total_Cholesterol",
    "hdl": "HDL_Cholesterol",
    "hdl cholesterol": "HDL_Cholesterol",
    "hdl-c": "HDL_Cholesterol",
    "ldl": "LDL_Cholesterol",
    "ldl cholesterol": "LDL_Cholesterol",
    "ldl-c": "LDL_Cholesterol",
    "vldl": "VLDL_Cholesterol",
    "vldl cholesterol": "VLDL_Cholesterol",
    "triglycerides": "Triglycerides",
    "tg": "Triglycerides",
    "non-hdl": "Non_HDL_Cholesterol",
    "non hdl cholesterol": "Non_HDL_Cholesterol",
    "tc/hdl ratio": "TC_HDL_Ratio",
    "ldl/hdl ratio": "LDL_HDL_Ratio",
    "lipoprotein(a)": "Lipoprotein_a",
    "lp(a)": "Lipoprotein_a",
    "apoa1": "ApoA1",
    "apob": "ApoB",
    "apolipoprotein a1": "ApoA1",
    "apolipoprotein b": "ApoB",
    
    # Diabetes
    "fasting glucose": "Fasting_Blood_Glucose",
    "fasting blood glucose": "Fasting_Blood_Glucose",
    "fbs": "Fasting_Blood_Glucose",
    "fbg": "Fasting_Blood_Glucose",
    "postprandial glucose": "Postprandial_Glucose",
    "ppbs": "Postprandial_Glucose",
    "2h pp": "Postprandial_Glucose",
    "random glucose": "Random_Blood_Glucose",
    "random blood glucose": "Random_Blood_Glucose",
    "rbs": "Random_Blood_Glucose",
    "hba1c": "HbA1c",
    "glycated hemoglobin": "HbA1c",
    "glycosylated hemoglobin": "HbA1c",
    "a1c": "HbA1c",
    "eag": "eAG",
    "estimated average glucose": "eAG",
    "fasting insulin": "Fasting_Insulin",
    "insulin": "Fasting_Insulin",
    "homa-ir": "HOMA_IR",
    "c-peptide": "C_Peptide",
    
    # Thyroid
    "tsh": "TSH",
    "thyroid stimulating hormone": "TSH",
    "ft3": "Free_T3",
    "free t3": "Free_T3",
    "free triiodothyronine": "Free_T3",
    "t3": "Total_T3",
    "total t3": "Total_T3",
    "triiodothyronine": "Total_T3",
    "ft4": "Free_T4",
    "free t4": "Free_T4",
    "free thyroxine": "Free_T4",
    "t4": "Total_T4",
    "total t4": "Total_T4",
    "thyroxine": "Total_T4",
    "anti-tpo": "Anti_TPO",
    "tpo antibody": "Anti_TPO",
    "thyroid peroxidase antibody": "Anti_TPO",
    "anti-thyroglobulin": "Anti_Thyroglobulin",
    "tg antibody": "Anti_Thyroglobulin",
    "trab": "TSH_Receptor_Ab",
    "tsh receptor antibody": "TSH_Receptor_Ab",
    "thyroglobulin": "Thyroglobulin",
    "calcitonin": "Calcitonin",
    
    # Vitamins
    "vitamin d": "Vitamin_D_25OH",
    "vitamin d3": "Vitamin_D3",
    "25-oh vitamin d": "Vitamin_D_25OH",
    "25 hydroxy vitamin d": "Vitamin_D_25OH",
    "vitamin d total": "Vitamin_D_25OH",
    "pth": "PTH",
    "parathyroid hormone": "PTH",
    "vitamin b12": "Vitamin_B12",
    "b12": "Vitamin_B12",
    "cyanocobalamin": "Vitamin_B12",
    "folate": "Serum_Folate",
    "serum folate": "Serum_Folate",
    "rbc folate": "RBC_Folate",
    "homocysteine": "Homocysteine",
    
    # Rheumatology
    "rf": "RA_Factor",
    "rheumatoid factor": "RA_Factor",
    "anti-ccp": "Anti_CCP",
    "anti cyclic citrullinated peptide": "Anti_CCP",
    "crp": "CRP",
    "c-reactive protein": "CRP",
    "hscrp": "hs_CRP",
    "hs-crp": "hs_CRP",
    "high sensitivity crp": "hs_CRP",
    "anti-dsdna": "Anti_dsDNA",
    "anti double stranded dna": "Anti_dsDNA",
    "c3": "C3_Complement",
    "complement c3": "C3_Complement",
    "c4": "C4_Complement",
    "complement c4": "C4_Complement",
    "aso": "ASO_Titre",
    "aso titre": "ASO_Titre",
    "anti-streptolysin o": "ASO_Titre",
    
    # Iron Studies
    "ferritin": "Ferritin",
    "serum iron": "Serum_Iron",
    "iron": "Serum_Iron",
    "tibc": "TIBC",
    "total iron binding capacity": "TIBC",
    "transferrin saturation": "Transferrin_Saturation",
    "tsat": "Transferrin_Saturation",
    
    # Oncology Markers
    "psa": "PSA_Total",
    "psa total": "PSA_Total",
    "free psa": "PSA_Free",
    "psa free": "PSA_Free",
    "cea": "CEA",
    "carcinoembryonic antigen": "CEA",
    "ca 125": "CA_125",
    "ca125": "CA_125",
    "cancer antigen 125": "CA_125",
    "ca 19-9": "CA_19_9",
    "ca19-9": "CA_19_9",
    "cancer antigen 19-9": "CA_19_9",
    "ca 15-3": "CA_15_3",
    "ca15-3": "CA_15_3",
    "ca 72-4": "CA_72_4",
    "ca72-4": "CA_72_4",
    "afp": "AFP",
    "alpha fetoprotein": "AFP",
    "alpha-fetoprotein": "AFP",
    "beta-hcg": "Beta_HCG",
    "β-hcg": "Beta_HCG",
    "nse": "NSE",
    "neuron specific enolase": "NSE",
    "cyfra 21-1": "CYFRA_21_1",
    "scc": "SCC_Antigen",
    "squamous cell carcinoma antigen": "SCC_Antigen",
    "chromogranin a": "Chromogranin_A",
    "he4": "HE4",
    
    # Urine
    "urine ph": "Urine_pH",
    "ph": "Urine_pH",
    "specific gravity": "Urine_Specific_Gravity",
    "urine specific gravity": "Urine_Specific_Gravity",
    "pus cells": "Urine_Pus_Cells",
    "wbc in urine": "Urine_Pus_Cells",
    "urine wbc": "Urine_Pus_Cells",
    "rbc in urine": "Urine_RBC",
    "urine rbc": "Urine_RBC",
    "urine red blood cells": "Urine_RBC",
}


def preprocess_text(text: str) -> str:
    """
    Preprocess extracted text for better parameter parsing.
    
    Args:
        text: Raw OCR text
        
    Returns:
        Cleaned and normalized text
    """
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove common OCR artifacts
    text = re.sub(r'[_]{2,}', '', text)
    text = re.sub(r'\|+', ' ', text)
    
    # Normalize units (common OCR errors)
    replacements = {
        'g/dL': ['g/dl', 'g/dI', 'gm/dL', 'gms/dL', 'g/dL'],
        'mg/dL': ['mg/dl', 'mg/dI', 'mgs/dL', 'mgm/dL'],
        'U/L': ['u/l', 'units/L', 'units/l', 'IU/L'],
        'mmol/L': ['mmol/l', 'mmol/ L', 'mmol / L'],
        'pg': ['p g', 'p.g'],
        'fL': ['f l', 'f.l', 'fl'],
        '10^9/L': ['10^9 /L', '10 9/L', 'x10^9/L', '*10^9/L', '10⁹/L'],
        '10^12/L': ['10^12 /L', '10 12/L', 'x10^12/L', '*10^12/L', '10¹²/L'],
        'mIU/L': ['miu/l', 'mIU/l', 'mIU/ L'],
        'pmol/L': ['pmol/l', 'p mol/L'],
        'ng/mL': ['ng/ml', 'ng/ mL', 'ng /mL'],
        'μg/mL': ['ug/ml', 'mcg/mL', 'µg/mL'],
        'ng/dL': ['ng/dl', 'ng/ dL'],
    }
    
    for standard, variants in replacements.items():
        for variant in variants:
            text = text.replace(variant, standard)
    
    # Normalize numbers (handle common OCR errors like O->0, l->1)
    # But be careful not to alter valid text
    text = re.sub(r'(?<!\w)[Oo](?=\d)', '0', text)  # O followed by digit -> 0
    text = re.sub(r'(?<=\d)[Oo](?!\w)', '0', text)  # digit followed by O -> 0
    text = re.sub(r'(?<!\w)[lI](?=\d)', '1', text)   # l/I followed by digit -> 1
    
    return text.strip()


def extract_patient_info(text: str) -> Dict[str, str]:
    """
    Extract patient demographic information from lab report text.
    
    Args:
        text: Preprocessed lab report text
        
    Returns:
        Dictionary with patient info fields
    """
    info = {}
    
    # Name patterns
    name_patterns = [
        r'(?:Patient\s*Name|Name|PName)[\s:]*([A-Za-z\s\.]+)(?=\n|Age|Sex|$)',
        r'(?:Mr\.?|Mrs\.?|Ms\.?|Dr\.?)\s*([A-Za-z\s\.]+)(?=\n|Age|Sex|$)',
    ]
    
    for pattern in name_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            if len(name) > 2 and not any(x in name.lower() for x in ['report', 'date', 'lab']):
                info['name'] = name
                break
    
    # Age patterns
    age_patterns = [
        r'(?:Age|A\s*ge)[\s:]*(\d+)[\s]*(?:years?|yrs?|Y)?',
        r'(\d+)[\s]*(?:years?|yrs?|Y)[\s]*(?:old)?',
        r'(?:Age|A\s*ge)[\s:]*(\d+)[\s]*\/',
    ]
    
    for pattern in age_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            info['age'] = match.group(1)
            break
    
    # Sex/Gender patterns
    sex_patterns = [
        r'(?:Sex|Gender)[\s:]*([MF])(?=\s|$)',
        r'(?:Sex|Gender)[\s:]*(Male|Female|M|F)(?=\s|$)',
        r'\b(Male|Female|M|F)\b(?=\s|,|\.|Age|$)',
    ]
    
    for pattern in sex_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            sex = match.group(1).upper()
            info['sex'] = 'male' if sex in ['M', 'MALE'] else 'female' if sex in ['F', 'FEMALE'] else sex.lower()
            break
    
    # Report ID/Accession
    id_patterns = [
        r'(?:Report\s*ID|Accession|Lab\s*ID|Ref\s*No)[\s:]*([A-Z0-9\-]+)',
        r'(?:Bill\s*No|Invoice)[\s:]*([A-Z0-9\-]+)',
    ]
    
    for pattern in id_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            info['report_id'] = match.group(1).strip()
            break
    
    # Date patterns
    date_patterns = [
        r'(?:Report\s*Date|Date\s*Collected|Sample\s*Date)[\s:]*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
        r'(?:Date)[\s:]*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
        r'(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})(?=\s|$)',
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            info['report_date'] = match.group(1)
            break
    
    return info


def extract_value_unit(text: str) -> Tuple[Optional[float], Optional[str]]:
    """
    Extract numeric value and unit from text.
    
    Args:
        text: String containing value and possibly unit
        
    Returns:
        Tuple of (value, unit) where value is float or None
    """
    # Pattern for numeric values (including decimals, ranges, and inequalities)
    # Handle formats: 12.5, <0.5, >100, 5-10, 5.2 (H), 5.2*, etc.
    value_pattern = r'([<>≤≥]?)\s*(\d+\.?\d*)\s*(?:-\s*(\d+\.?\d*))?\s*([\*HLhl\↑\↓])?'
    
    # Unit pattern (common lab units)
    unit_pattern = r'(g/dL|mg/dL|U/L|mmol/L|μmol/L|pmol/L|nmol/L|mIU/L|IU/L|pg|fL|%|10\^9/L|10\^12/L|ng/mL|μg/mL|ng/dL|mm/hr|mL/min|ratio|units|mg/g|mEq/L|mmol/L|copies/mL)'
    
    # Try to find value
    val_match = re.search(value_pattern, text)
    if not val_match:
        return None, None
    
    inequality = val_match.group(1)
    main_val = val_match.group(2)
    range_val = val_match.group(3)
    flag = val_match.group(4)
    
    # Use the main value
    try:
        value = float(main_val)
    except ValueError:
        return None, None
    
    # Look for unit in the text (after the value)
    remaining_text = text[val_match.end():]
    unit_match = re.search(unit_pattern, remaining_text, re.IGNORECASE)
    unit = unit_match.group(1) if unit_match else None
    
    # If inequality present, adjust value interpretation
    if inequality == '<' or inequality == '≤':
        # Value is below detectable limit, use half of reported
        value = value / 2
    elif inequality == '>' or inequality == '≥':
        # Value is above limit, use the value as-is but flag
        pass
    
    return value, unit


def parse_parameters(text: str) -> Dict[str, Union[Dict, float]]:
    """
    Parse lab parameters from preprocessed text.
    
    Args:
        text: Preprocessed lab report text
        
    Returns:
        Dictionary mapping parameter keys to values or value dictionaries
    """
    parameters = {}
    lines = text.split('\n')
    
    # Pattern to match parameter lines
    # Format: Parameter Name ... Value Unit [Reference] [Flag]
    param_line_pattern = re.compile(
        r'^([A-Za-z\s\(\)\-\+/]+?)[\s\.\_]*'  # Parameter name
        r'(\d+\.?\d*)\s*'  # Value
        r'(g/dL|mg/dL|U/L|mmol/L|μmol/L|pmol/L|nmol/L|mIU/L|IU/L|pg|fL|%|10\^9/L|10\^12/L|ng/mL|μg/mL|ng/dL|mm/hr|mL/min|mg/g|mEq/L|copies/mL|units|ratio)?\s*'  # Unit (optional)
        r'(?:[\(\[]?\s*([\d\.]+\s*-\s*[\d\.]+)\s*[\)\]]?)?\s*'  # Reference range (optional)
        r'([HLhl\↑\↓\*])?$',  # Flag (optional)
        re.IGNORECASE
    )
    
    # Alternative pattern for tabular data
    table_pattern = re.compile(
        r'([A-Za-z\s\(\)\-\+/]+?)[\s\|]+'  # Parameter name
        r'(\d+\.?\d*)\s*'  # Value
        r'(g/dL|mg/dL|U/L|mmol/L|μmol/L|pmol/L|nmol/L|mIU/L|IU/L|pg|fL|%|10\^9/L|10\^12/L|ng/mL|μg/mL|ng/dL|mm/hr|mL/min|mg/g|mEq/L|copies/mL|units|ratio)?\s*[\|]+'
        r'(?:([\d\.]+\s*-\s*[\d\.]+))?',  # Reference range
        re.IGNORECASE
    )
    
    for line in lines:
        line = line.strip()
        if not line or len(line) < 3:
            continue
        
        # Try to match parameter line
        match = param_line_pattern.match(line)
        if not match:
            match = table_pattern.search(line)
        
        if match:
            raw_name = match.group(1).strip()
            value_str = match.group(2)
            unit = match.group(3)
            ref_range = match.group(4) if len(match.groups()) > 3 else None
            
            # Clean parameter name
            clean_name = re.sub(r'[\s\.]+', ' ', raw_name).strip().lower()
            
            # Check if this is a known parameter
            standard_key = None
            for alias, key in PARAMETER_ALIASES.items():
                if alias in clean_name or clean_name in alias:
                    standard_key = key
                    break
            
            if not standard_key:
                # Try fuzzy matching or skip
                continue
            
            # Parse value
            try:
                value = float(value_str)
            except ValueError:
                continue
            
            # Store parameter
            parameters[standard_key] = {
                'value': value,
                'unit': unit,
                'reference_range': ref_range,
                'original_name': raw_name
            }
    
    # Also try to find parameters in a more flexible way
    # Look for known parameter names followed by numbers
    for alias, key in PARAMETER_ALIASES.items():
        # Pattern: parameter name followed by number (possibly with unit)
        pattern = re.compile(
            rf'{re.escape(alias)}[\s\:\.\=]+(\d+\.?\d*)\s*(g/dL|mg/dL|U/L|mmol/L|μmol/L|pmol/L|nmol/L|mIU/L|IU/L|pg|fL|%|10\^9/L|10\^12/L|ng/mL|μg/mL|ng/dL|mm/hr|mL/min|mg/g|mEq/L|copies/mL|units|ratio)?',
            re.IGNORECASE
        )
        
        for match in pattern.finditer(text):
            if key not in parameters:  # Don't overwrite if already found
                try:
                    value = float(match.group(1))
                    unit = match.group(2)
                    parameters[key] = {
                        'value': value,
                        'unit': unit,
                        'original_name': alias
                    }
                except ValueError:
                    continue
    
    return parameters


def process_pdf_with_pymupdf(file_bytes: bytes) -> str:
    """
    Extract text from PDF using PyMuPDF (fitz).
    
    Args:
        file_bytes: PDF file bytes
        
    Returns:
        Extracted text
    """
    if not PYMUPDF_AVAILABLE:
        raise ImportError("PyMuPDF not installed. Install with: pip install PyMuPDF")
    
    text_parts = []
    
    with fitz.open(stream=file_bytes, filetype="pdf") as doc:
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text()
            text_parts.append(text)
    
    return "\n".join(text_parts)


def process_pdf_with_ocr(file_bytes: bytes) -> str:
    """
    Convert PDF to images and OCR them.
    
    Args:
        file_bytes: PDF file bytes
        
    Returns:
        Extracted text from OCR
    """
    if not PDF2IMAGE_AVAILABLE:
        raise ImportError("pdf2image not installed. Install with: pip install pdf2image")
    if not PYTESSERACT_AVAILABLE:
        raise ImportError("pytesseract not installed. Install with: pip install pytesseract")
    
    # Convert PDF to images
    images = pdf2image.convert_from_bytes(file_bytes, dpi=300)
    
    text_parts = []
    for img in images:
        # Preprocess image for better OCR
        if CV2_AVAILABLE:
            img_array = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
            # Denoise and threshold
            denoised = cv2.fastNlMeansDenoising(gray)
            _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            img = Image.fromarray(binary)
        
        # OCR
        text = pytesseract.image_to_string(img, config='--psm 6')
        text_parts.append(text)
    
    return "\n".join(text_parts)


def process_image(file_bytes: bytes) -> str:
    """
    Process image file with OCR.
    
    Args:
        file_bytes: Image file bytes
        
    Returns:
        Extracted text
    """
    if not PYTESSERACT_AVAILABLE:
        raise ImportError("pytesseract not installed. Install with: pip install pytesseract")
    
    # Load image
    img = Image.open(io.BytesIO(file_bytes))
    
    # Preprocess
    if CV2_AVAILABLE:
        img_array = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
        denoised = cv2.fastNlMeansDenoising(gray)
        _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        img = Image.fromarray(binary)
    
    # OCR with multiple PSM modes for better accuracy
    configs = ['--psm 6', '--psm 3', '--psm 4']
    texts = []
    
    for config in configs:
        text = pytesseract.image_to_string(img, config=config)
        texts.append(text)
    
    # Return the longest text (usually most complete)
    return max(texts, key=len)


def process_uploaded_file(uploaded_file) -> Tuple[str, Dict, Dict, Dict, Dict]:
    """
    Main entry point for processing uploaded lab reports.
    
    Args:
        uploaded_file: Streamlit uploaded file object or file-like object
        
    Returns:
        Tuple of (raw_text, parameters, grouped_parameters, panel_summary, patient_info)
    """
    # Read file bytes
    if hasattr(uploaded_file, 'getvalue'):
        file_bytes = uploaded_file.getvalue()
    else:
        file_bytes = uploaded_file.read()
    
    # Determine file type
    filename = getattr(uploaded_file, 'name', '').lower()
    
    # Extract raw text
    if filename.endswith('.pdf'):
        # Try PyMuPDF first, fall back to OCR
        try:
            raw_text = process_pdf_with_pymupdf(file_bytes)
            # If little text extracted, try OCR
            if len(raw_text.strip()) < 100:
                raw_text = process_pdf_with_ocr(file_bytes)
        except Exception:
            raw_text = process_pdf_with_ocr(file_bytes)
    else:
        # Image file
        raw_text = process_image(file_bytes)
    
    # Preprocess text
    clean_text = preprocess_text(raw_text)
    
    # Extract patient info
    patient_info = extract_patient_info(clean_text)
    
    # Parse parameters
    parameters = parse_parameters(clean_text)
    
    # Group parameters by panel
    grouped = group_parameters_by_panel(parameters)
    
    # Generate panel summary
    panel_summary = generate_panel_summary(grouped)
    
    return raw_text, parameters, grouped, panel_summary, patient_info


def group_parameters_by_panel(parameters: Dict) -> Dict[str, List[str]]:
    """
    Group extracted parameters by their clinical panel.
    
    Args:
        parameters: Dictionary of extracted parameters
        
    Returns:
        Dictionary mapping panel names to lists of parameter keys
    """
    from utils.analysis_engine import PANEL_PARAMETER_MAP
    
    grouped = {}
    for panel, panel_params in PANEL_PARAMETER_MAP.items():
        found = [p for p in panel_params if p in parameters]
        if found:
            grouped[panel] = found
    
    return grouped


def generate_panel_summary(grouped: Dict[str, List[str]]) -> Dict[str, Dict]:
    """
    Generate summary statistics for each panel.
    
    Args:
        grouped: Grouped parameters by panel
        
    Returns:
        Summary dictionary for each panel
    """
    summary = {}
    for panel, params in grouped.items():
        summary[panel] = {
            'parameters_found': len(params),
            'parameter_names': params,
            'completeness': len(params)  # Could be compared to expected count
        }
    return summary
