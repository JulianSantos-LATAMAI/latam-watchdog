import streamlit as st
import google.generativeai as genai
import PyPDF2
import io

# --- SECURITY: Get key from Streamlit Secrets ---
# We do not hardcode the key here anymore!
api_key = st.secrets["GOOGLE_API_KEY"]
genai.configure(api_key=api_key)

def audit_invoice(text):
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"""
    You are a strict Customs Auditor. Analyze this invoice text.
    Check for: 
    1. Missing Tax IDs (RUT/CNPJ/NIF)
    2. Missing Incoterms
    3. Vague Descriptions

    INVOICE TEXT:
    {text}
    """
    response = model.generate_content(prompt)
    return response.text

st.title("📦 Latam Supply Chain Watchdog")

uploaded_file = st.file_uploader("Upload Invoice (PDF)", type="pdf")

if uploaded_file is not None:
    reader = PyPDF2.PdfReader(uploaded_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()

    st.info(f"Read {len(text)} characters.")

    if st.button("Audit Document"):
        with st.spinner("Auditing..."):
            try:
                report = audit_invoice(text)
                st.markdown(report)
            except Exception as e:
                st.error(f"Error: {e}")
