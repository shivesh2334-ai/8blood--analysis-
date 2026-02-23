# LabIQ — Comprehensive Lab Investigation Analysis Platform

AI-Powered Multi-Panel Clinical Laboratory Analysis Platform supporting:
- **CBC** (Complete Blood Count)
- **LFT** (Liver Function Test)
- **KFT** (Kidney Function Test)
- **Lipid Profile**
- **Diabetes Panel** (HbA1c, Glucose, Insulin)
- **TFT** (Thyroid Function Test)
- **Vitamin D & B12 Panels**
- **Urine Analysis**
- **Rheumatology Panel**
- **Oncology Markers**

## Features

- **OCR Extraction**: Extract lab values from PDF and image reports
- **Manual Entry**: Input values directly with smart validation
- **Clinical Analysis**: Automated interpretation against reference ranges
- **AI Review**: Claude-powered clinical review and recommendations
- **Report Generation**: Downloadable HTML and JSON reports

## Installation

```bash
# Clone repository
git clone <repo-url>
cd labiq

# Install dependencies
pip install -r requirements.txt

# Install Tesseract OCR (system dependency)
# macOS: brew install tesseract
# Ubuntu: sudo apt-get install tesseract-ocr
# Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki

# Run application
streamlit run app.py
