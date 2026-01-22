import streamlit as st
import google.generativeai as genai
import PyPDF2
import re
import json
from datetime import datetime
from typing import Dict, List, Tuple


api_key = st.secrets["GOOGLE_API_KEY"]
genai.configure(api_key=api_key)


COUNTRY_RULES = {
    "Chile": {
        "tax_id_pattern": r'\b\d{1,2}\.\d{3}\.\d{3}-[\dkK]\b',
        "tax_id_name": "RUT",
        "required_fields": ["RUT", "Incoterm", "HS Code"],
        "currency": "CLP"
    },
    "Brazil": {
        "tax_id_pattern": r'\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b',
        "tax_id_name": "CNPJ",
        "required_fields": ["CNPJ", "NCM", "Incoterm"],
        "currency": "BRL"
    },
    "Argentina": {
        "tax_id_pattern": r'\b\d{2}-\d{8}-\d\b',
        "tax_id_name": "CUIT",
        "required_fields": ["CUIT", "Incoterm", "NCM"],
        "currency": "ARS"
    },
    "Spain": {
        "tax_id_pattern": r'\b[A-Z]\d{7}[A-Z0-9]\b|\b\d{8}[A-Z]\b',
        "tax_id_name": "NIF/CIF",
        "required_fields": ["NIF", "Incoterm", "HS Code"],
        "currency": "EUR"
    },
    "Portugal": {
        "tax_id_pattern": r'\b\d{9}\b',
        "tax_id_name": "NIF",
        "required_fields": ["NIF", "Incoterm", "HS Code"],
        "currency": "EUR"
    }
}

# Valid Incoterms (2020)
VALID_INCOTERMS = [
    "EXW", "FCA", "CPT", "CIP", "DAP", "DPU", "DDP",
    "FAS", "FOB", "CFR", "CIF"
]

# --- RULES-BASED VALIDATION ---
def check_tax_id(text: str, country: str) -> Tuple[bool, str]:
    """Check if tax ID exists and matches country pattern."""
    pattern = COUNTRY_RULES[country]["tax_id_pattern"]
    tax_id_name = COUNTRY_RULES[country]["tax_id_name"]
    
    matches = re.findall(pattern, text)
    if matches:
        return True, f"✅ {tax_id_name} found: {matches[0]}"
    else:
        return False, f"❌ CRITICAL: Missing {tax_id_name} (format: {pattern})"

def check_incoterm(text: str) -> Tuple[bool, str, str]:
    """Check if Incoterm exists and is valid."""
    text_upper = text.upper()
    found_terms = [term for term in VALID_INCOTERMS if term in text_upper]
    
    if found_terms:
        return True, f"✅ Incoterm found: {found_terms[0]}", found_terms[0]
    else:
        return False, "❌ CRITICAL: Missing Incoterm", None

def check_hs_codes(text: str) -> Tuple[bool, str]:
    """Check for HS/NCM codes (basic pattern matching)."""
    # HS codes are 6+ digits, often formatted like 1234.56.78
    hs_pattern = r'\b\d{4}[\.\s]?\d{2}[\.\s]?\d{0,4}\b'
    matches = re.findall(hs_pattern, text)
    
    if matches:
        return True, f"✅ HS/NCM codes found: {len(matches)} items"
    else:
        return False, "⚠️ WARNING: No HS/NCM codes detected"

def rules_based_validation(text: str, country: str) -> Dict:
    """Run all rules-based checks."""
    results = {
        "critical_errors": [],
        "warnings": [],
        "passed_checks": []
    }
    
    # Check Tax ID
    passed, message = check_tax_id(text, country)
    if passed:
        results["passed_checks"].append(message)
    else:
        results["critical_errors"].append(message)
    
    # Check Incoterm
    passed, message, term = check_incoterm(text)
    if passed:
        results["passed_checks"].append(message)
    else:
        results["critical_errors"].append(message)
    
    # Check HS Codes
    passed, message = check_hs_codes(text)
    if passed:
        results["passed_checks"].append(message)
    else:
        results["warnings"].append(message)
    
    return results

# --- AI-POWERED DEEP AUDIT ---
def ai_deep_audit(text: str, country: str, rules_results: Dict) -> str:
    """Use AI for contextual analysis and ambiguity detection."""
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""You are an expert Customs Compliance Auditor specializing in {country} import/export regulations.

RULES-BASED FINDINGS:
Critical Errors: {rules_results['critical_errors']}
Warnings: {rules_results['warnings']}

YOUR TASK: Perform a deep contextual audit of this invoice. Focus on:

1. **Product Description Quality**
   - Are descriptions specific enough for customs classification?
   - Check for vague terms like "parts", "equipment", "goods", "accessories"
   - Flag descriptions under 10 words or missing material/use details

2. **Quantity & Value Consistency**
   - Do quantities match across line items?
   - Are unit prices reasonable?
   - Any missing totals or calculation errors?

3. **Country-Specific Red Flags for {country}**
   - Missing required certifications or licenses
   - Restricted/prohibited goods indicators
   - Currency mismatch with expected {COUNTRY_RULES[country]['currency']}

4. **Additional Missing Information**
   - Buyer/Seller complete addresses
   - Invoice date and number
   - Payment terms
   - Country of origin per item

OUTPUT FORMAT (use this exact structure):
### AI Audit Results

**High Priority Issues:**
- [List critical issues found, or write "None detected"]

**Medium Priority Warnings:**
- [List concerning items that need review]

**Low Priority Notes:**
- [Minor improvements or observations]

**Confidence Score:** X/10
[Explain your confidence level in this audit]

---
INVOICE TEXT:
{text[:8000]}
"""  # Limit text to avoid token limits
    
    response = model.generate_content(prompt)
    return response.text

# --- STREAMLIT UI ---
st.set_page_config(page_title="LATAM Trade Auditor", page_icon="📦", layout="wide")

st.title("📦 LATAM Supply Chain Watchdog")
st.markdown("**Professional Import/Export Document Auditor** | Powered by AI + Rules-Based Validation")

# Sidebar Configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    country = st.selectbox(
        "Select Origin/Destination Country",
        options=list(COUNTRY_RULES.keys()),
        help="Choose the country whose regulations to audit against"
    )
    
    st.markdown("---")
    st.markdown("### 🔍 What We Check")
    st.markdown(f"""
    **Rules-Based:**
    - {COUNTRY_RULES[country]['tax_id_name']} format validation
    - Valid Incoterms (2020)
    - HS/NCM code presence
    
    **AI-Powered:**
    - Description quality
    - Value consistency
    - Country-specific compliance
    """)
    
    st.markdown("---")
    st.info("💡 **Tip:** This tool assists audits but doesn't replace professional customs review.")

# Main Content
uploaded_file = st.file_uploader(
    "📄 Upload Commercial Invoice (PDF)", 
    type="pdf",
    help="Upload the invoice PDF you want to audit"
)

if uploaded_file is not None:
    # Extract PDF text
    try:
        reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        
        # Display extraction info
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Pages Extracted", len(reader.pages))
        with col2:
            st.metric("Characters Read", f"{len(text):,}")
        with col3:
            st.metric("Selected Country", country)
        
        # Show preview
        with st.expander("📄 View Extracted Text Preview"):
            st.text(text[:1000] + "..." if len(text) > 1000 else text)
        
    except Exception as e:
        st.error(f"❌ PDF Extraction Error: {e}")
        st.stop()
    
    # Audit Button
    if st.button("🔍 Run Full Audit", type="primary", use_container_width=True):
        with st.spinner("Running validation checks..."):
            
            # Stage 1: Rules-Based Validation
            st.markdown("### 📋 Stage 1: Rules-Based Validation")
            rules_results = rules_based_validation(text, country)
            
            # Display rules results
            if rules_results["critical_errors"]:
                st.error("**Critical Errors Found:**")
                for error in rules_results["critical_errors"]:
                    st.markdown(f"- {error}")
            
            if rules_results["warnings"]:
                st.warning("**Warnings:**")
                for warning in rules_results["warnings"]:
                    st.markdown(f"- {warning}")
            
            if rules_results["passed_checks"]:
                st.success("**Passed Checks:**")
                for check in rules_results["passed_checks"]:
                    st.markdown(f"- {check}")
            
            st.markdown("---")
            
            # Stage 2: AI Deep Audit
            st.markdown("### 🤖 Stage 2: AI Deep Audit")
            try:
                with st.spinner("AI analyzing document context..."):
                    ai_report = ai_deep_audit(text, country, rules_results)
                    st.markdown(ai_report)
            except Exception as e:
                st.error(f"❌ AI Audit Error: {e}")
            
            # Summary Score
            st.markdown("---")
            critical_count = len(rules_results["critical_errors"])
            warning_count = len(rules_results["warnings"])
            
            if critical_count == 0 and warning_count == 0:
                st.success("### ✅ AUDIT PASSED - Document appears compliant")
            elif critical_count > 0:
                st.error(f"### ❌ AUDIT FAILED - {critical_count} critical error(s) detected")
            else:
                st.warning(f"### ⚠️ REVIEW NEEDED - {warning_count} warning(s) detected")
            
            # Export Report
            st.markdown("---")
            report_text = f"""
LATAM SUPPLY CHAIN WATCHDOG - AUDIT REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Country: {country}
Document: {uploaded_file.name}

=== RULES-BASED VALIDATION ===
Critical Errors: {len(rules_results['critical_errors'])}
{chr(10).join(rules_results['critical_errors'])}

Warnings: {len(rules_results['warnings'])}
{chr(10).join(rules_results['warnings'])}

Passed Checks: {len(rules_results['passed_checks'])}
{chr(10).join(rules_results['passed_checks'])}

=== AI DEEP AUDIT ===
{ai_report}
"""
            
            st.download_button(
                label="📥 Download Audit Report",
                data=report_text,
                file_name=f"audit_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain"
            )

else:
    # Show example when no file uploaded
    st.info("👆 Upload a commercial invoice PDF to begin the audit process")
    
    with st.expander("📚 What makes a good invoice?"):
        st.markdown("""
        **Essential Elements:**
        1. ✅ Valid Tax ID (RUT/CNPJ/NIF/CUIT)
        2. ✅ Clear Incoterm (FOB, CIF, etc.)
        3. ✅ HS/NCM codes for all items
        4. ✅ Detailed product descriptions (>10 words, include material/use)
        5. ✅ Complete buyer & seller information
        6. ✅ Invoice date and unique number
        7. ✅ Quantities, unit prices, and totals
        8. ✅ Currency clearly stated
        9. ✅ Country of origin per product
        10. ✅ Payment terms
        """)
