import streamlit as st
import google.generativeai as genai
import PyPDF2
import re
import json
from datetime import datetime
from typing import Dict, List, Tuple

# --- CONFIGURATION ---
api_key = st.secrets["GOOGLE_API_KEY"]
genai.configure(api_key=api_key)

# --- VALIDATION RULES BY COUNTRY ---
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
    },
    "United States of America": {
        "tax_id_pattern": r'\b\d{2}-\d{7}\b',
        "tax_id_name": "EIN",
        "required_fields": ["EIN" , "Incoterm", "HTS Code"],
        "currency: "USD"
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

# --- LANGUAGE TRANSLATIONS ---
TRANSLATIONS = {
    "English": {
        "title": "📦 LATAM Supply Chain Watchdog",
        "subtitle": "**Professional Import/Export Document Auditor** | Powered by AI + Rules-Based Validation",
        "config_header": "⚙️ Configuration",
        "language_label": "Language / Idioma / Língua",
        "country_label": "Select Origin/Destination Country",
        "country_help": "Choose the country whose regulations to audit against",
        "what_we_check": "🔍 What We Check",
        "rules_based": "Rules-Based:",
        "ai_powered": "AI-Powered:",
        "description_quality": "Description quality",
        "value_consistency": "Value consistency",
        "country_compliance": "Country-specific compliance",
        "tip": "💡 **Tip:** This tool assists audits but doesn't replace professional customs review.",
        "upload_label": "📄 Upload Commercial Invoice (PDF)",
        "upload_help": "Upload the invoice PDF you want to audit",
        "pages_extracted": "Pages Extracted",
        "characters_read": "Characters Read",
        "selected_country": "Selected Country",
        "view_preview": "📄 View Extracted Text Preview",
        "extraction_error": "❌ PDF Extraction Error:",
        "run_audit": "🔍 Run Full Audit",
        "stage1": "### 📋 Stage 1: Rules-Based Validation",
        "critical_errors": "**Critical Errors Found:**",
        "warnings": "**Warnings:**",
        "passed_checks": "**Passed Checks:**",
        "stage2": "### 🤖 Stage 2: AI Deep Audit",
        "ai_analyzing": "AI analyzing document context...",
        "ai_error": "❌ AI Audit Error:",
        "audit_passed": "### ✅ AUDIT PASSED - Document appears compliant",
        "audit_failed": "### ❌ AUDIT FAILED - {count} critical error(s) detected",
        "review_needed": "### ⚠️ REVIEW NEEDED - {count} warning(s) detected",
        "download_report": "📥 Download Audit Report",
        "upload_prompt": "👆 Upload a commercial invoice PDF to begin the audit process",
        "good_invoice": "📚 What makes a good invoice?",
        "essential_elements": "**Essential Elements:**",
        "validating": "Running validation checks..."
    },
    "Español": {
        "title": "📦 Guardián de la Cadena de Suministro LATAM",
        "subtitle": "**Auditor Profesional de Documentos de Importación/Exportación** | Impulsado por IA + Validación Basada en Reglas",
        "config_header": "⚙️ Configuración",
        "language_label": "Language / Idioma / Língua",
        "country_label": "Seleccionar País de Origen/Destino",
        "country_help": "Elija el país cuyas regulaciones desea auditar",
        "what_we_check": "🔍 Qué Verificamos",
        "rules_based": "Basado en Reglas:",
        "ai_powered": "Impulsado por IA:",
        "description_quality": "Calidad de descripción",
        "value_consistency": "Consistencia de valores",
        "country_compliance": "Cumplimiento específico del país",
        "tip": "💡 **Consejo:** Esta herramienta asiste en auditorías pero no reemplaza la revisión aduanera profesional.",
        "upload_label": "📄 Cargar Factura Comercial (PDF)",
        "upload_help": "Cargue el PDF de la factura que desea auditar",
        "pages_extracted": "Páginas Extraídas",
        "characters_read": "Caracteres Leídos",
        "selected_country": "País Seleccionado",
        "view_preview": "📄 Ver Vista Previa del Texto Extraído",
        "extraction_error": "❌ Error de Extracción de PDF:",
        "run_audit": "🔍 Ejecutar Auditoría Completa",
        "stage1": "### 📋 Etapa 1: Validación Basada en Reglas",
        "critical_errors": "**Errores Críticos Encontrados:**",
        "warnings": "**Advertencias:**",
        "passed_checks": "**Verificaciones Aprobadas:**",
        "stage2": "### 🤖 Etapa 2: Auditoría Profunda con IA",
        "ai_analyzing": "IA analizando contexto del documento...",
        "ai_error": "❌ Error de Auditoría IA:",
        "audit_passed": "### ✅ AUDITORÍA APROBADA - El documento parece conforme",
        "audit_failed": "### ❌ AUDITORÍA FALLIDA - {count} error(es) crítico(s) detectado(s)",
        "review_needed": "### ⚠️ REVISIÓN NECESARIA - {count} advertencia(s) detectada(s)",
        "download_report": "📥 Descargar Reporte de Auditoría",
        "upload_prompt": "👆 Cargue un PDF de factura comercial para comenzar el proceso de auditoría",
        "good_invoice": "📚 ¿Qué hace una buena factura?",
        "essential_elements": "**Elementos Esenciales:**",
        "validating": "Ejecutando verificaciones de validación..."
    },
    "Português": {
        "title": "📦 Guardião da Cadeia de Suprimentos LATAM",
        "subtitle": "**Auditor Profissional de Documentos de Importação/Exportação** | Alimentado por IA + Validação Baseada em Regras",
        "config_header": "⚙️ Configuração",
        "language_label": "Language / Idioma / Língua",
        "country_label": "Selecionar País de Origem/Destino",
        "country_help": "Escolha o país cujas regulamentações deseja auditar",
        "what_we_check": "🔍 O Que Verificamos",
        "rules_based": "Baseado em Regras:",
        "ai_powered": "Alimentado por IA:",
        "description_quality": "Qualidade da descrição",
        "value_consistency": "Consistência de valores",
        "country_compliance": "Conformidade específica do país",
        "tip": "💡 **Dica:** Esta ferramenta auxilia auditorias, mas não substitui a revisão aduaneira profissional.",
        "upload_label": "📄 Carregar Fatura Comercial (PDF)",
        "upload_help": "Carregue o PDF da fatura que deseja auditar",
        "pages_extracted": "Páginas Extraídas",
        "characters_read": "Caracteres Lidos",
        "selected_country": "País Selecionado",
        "view_preview": "📄 Ver Prévia do Texto Extraído",
        "extraction_error": "❌ Erro de Extração de PDF:",
        "run_audit": "🔍 Executar Auditoria Completa",
        "stage1": "### 📋 Etapa 1: Validação Baseada em Regras",
        "critical_errors": "**Erros Críticos Encontrados:**",
        "warnings": "**Avisos:**",
        "passed_checks": "**Verificações Aprovadas:**",
        "stage2": "### 🤖 Etapa 2: Auditoria Profunda com IA",
        "ai_analyzing": "IA analisando contexto do documento...",
        "ai_error": "❌ Erro de Auditoria IA:",
        "audit_passed": "### ✅ AUDITORIA APROVADA - O documento parece conforme",
        "audit_failed": "### ❌ AUDITORIA REPROVADA - {count} erro(s) crítico(s) detectado(s)",
        "review_needed": "### ⚠️ REVISÃO NECESSÁRIA - {count} aviso(s) detectado(s)",
        "download_report": "📥 Baixar Relatório de Auditoria",
        "upload_prompt": "👆 Carregue um PDF de fatura comercial para iniciar o processo de auditoria",
        "good_invoice": "📚 O que faz uma boa fatura?",
        "essential_elements": "**Elementos Essenciais:**",
        "validating": "Executando verificações de validação..."
    }
}

# --- STREAMLIT UI ---
st.set_page_config(page_title="LATAM Trade Auditor", page_icon="📦", layout="wide")

# Sidebar Configuration
with st.sidebar:
    st.header("🌍 Language / Idioma")
    language = st.selectbox(
        "Select Language",
        options=list(TRANSLATIONS.keys()),
        index=0,
        label_visibility="collapsed"
    )

# Get translations for selected language
t = TRANSLATIONS[language]

st.title(t["title"])
st.markdown(t["subtitle"])

# Continue Sidebar Configuration
with st.sidebar:
    st.markdown("---")
    st.header(t["config_header"])
    country = st.selectbox(
        t["country_label"],
        options=list(COUNTRY_RULES.keys()),
        help=t["country_help"]
    )
    
    st.markdown("---")
    st.markdown(f"### {t['what_we_check']}")
    st.markdown(f"""
    **{t['rules_based']}**
    - {COUNTRY_RULES[country]['tax_id_name']} format validation
    - Valid Incoterms (2020)
    - HS/NCM code presence
    
    **{t['ai_powered']}**
    - {t['description_quality']}
    - {t['value_consistency']}
    - {t['country_compliance']}
    """)
    
    st.markdown("---")
    st.info(t["tip"])

# Main Content
uploaded_file = st.file_uploader(
    t["upload_label"], 
    type="pdf",
    help=t["upload_help"]
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
            st.metric(t["pages_extracted"], len(reader.pages))
        with col2:
            st.metric(t["characters_read"], f"{len(text):,}")
        with col3:
            st.metric(t["selected_country"], country)
        
        # Show preview
        with st.expander(t["view_preview"]):
            st.text(text[:1000] + "..." if len(text) > 1000 else text)
        
    except Exception as e:
        st.error(f"{t['extraction_error']} {e}")
        st.stop()
    
    # Audit Button
    if st.button(t["run_audit"], type="primary", use_container_width=True):
        with st.spinner(t["validating"]):
            
            # Stage 1: Rules-Based Validation
            st.markdown(t["stage1"])
            rules_results = rules_based_validation(text, country)
            
            # Display rules results
            if rules_results["critical_errors"]:
                st.error(t["critical_errors"])
                for error in rules_results["critical_errors"]:
                    st.markdown(f"- {error}")
            
            if rules_results["warnings"]:
                st.warning(t["warnings"])
                for warning in rules_results["warnings"]:
                    st.markdown(f"- {warning}")
            
            if rules_results["passed_checks"]:
                st.success(t["passed_checks"])
                for check in rules_results["passed_checks"]:
                    st.markdown(f"- {check}")
            
            st.markdown("---")
            
            # Stage 2: AI Deep Audit
            st.markdown(t["stage2"])
            try:
                with st.spinner(t["ai_analyzing"]):
                    ai_report = ai_deep_audit(text, country, rules_results)
                    st.markdown(ai_report)
            except Exception as e:
                st.error(f"{t['ai_error']} {e}")
            
            # Summary Score
            st.markdown("---")
            critical_count = len(rules_results["critical_errors"])
            warning_count = len(rules_results["warnings"])
            
            if critical_count == 0 and warning_count == 0:
                st.success(t["audit_passed"])
            elif critical_count > 0:
                st.error(t["audit_failed"].format(count=critical_count))
            else:
                st.warning(t["review_needed"].format(count=warning_count))
            
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
                label=t["download_report"],
                data=report_text,
                file_name=f"audit_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain"
            )

else:
    # Show example when no file uploaded
    st.info(t["upload_prompt"])
    
    with st.expander(t["good_invoice"]):
        st.markdown(f"""
        {t["essential_elements"]}
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
