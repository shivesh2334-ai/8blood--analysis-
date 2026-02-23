"""
LabIQ Utilities Package
=======================
OCR parsing and clinical analysis engines for laboratory report processing.
"""

from utils.ocr_parser import (
    process_uploaded_file,
    parse_parameters,
    extract_patient_info,
    preprocess_text,
    PARAMETER_ALIASES,
)

from utils.analysis_engine import (
    REFERENCE_RANGES,
    PANEL_PARAMETER_MAP,
    PANEL_LABELS,
    PANEL_ICONS,
    analyze_panel,
    analyze_all,
    get_overall_severity,
    SEV_NORMAL,
    SEV_MILD,
    SEV_MODERATE,
    SEV_SEVERE,
    SEV_CRITICAL,
    STATUS_NORMAL,
    STATUS_LOW,
    STATUS_HIGH,
    STATUS_CRITICALLY_LOW,
    STATUS_CRITICALLY_HIGH,
    get_reference_range,
    calculate_severity,
)

__all__ = [
    # OCR
    'process_uploaded_file',
    'parse_parameters',
    'extract_patient_info',
    'preprocess_text',
    'PARAMETER_ALIASES',
    
    # Analysis
    'REFERENCE_RANGES',
    'PANEL_PARAMETER_MAP',
    'PANEL_LABELS',
    'PANEL_ICONS',
    'analyze_panel',
    'analyze_all',
    'get_overall_severity',
    'get_reference_range',
    'calculate_severity',
    
    # Constants
    'SEV_NORMAL',
    'SEV_MILD',
    'SEV_MODERATE',
    'SEV_SEVERE',
    'SEV_CRITICAL',
    'STATUS_NORMAL',
    'STATUS_LOW',
    'STATUS_HIGH',
    'STATUS_CRITICALLY_LOW',
    'STATUS_CRITICALLY_HIGH',
]
