import streamlit as st
import pandas as pd
import pdfplumber
import re
import io
from rapidfuzz import fuzz

st.set_page_config(page_title="HSN Code Identifier", layout="wide")
st.title("🔍 HSN Code Identifier Tool")

# Cache HSN master loading
@st.cache_data
def load_hsn(file):
    if file.name.endswith(".pdf"):
        with pdfplumber.open(file) as pdf:
            text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
        hsn_lines = [line.split("\t") for line in text.split("\n") if line.strip()]
        return pd.DataFrame(hsn_lines, columns=["HSN Code", "Product Description"])
    else:
        return pd.read_excel(file)

# Cache brochure loading
@st.cache_data
def load_brochure(file):
    if file.name.endswith(".pdf"):
        with pdfplumber.open(file) as pdf:
            text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
        return text.split("\n")
    else:
        df = pd.read_excel(file)
        return df.astype(str).apply(lambda row: ' '.join(row), axis=1).tolist()

# Upload HSN Master File
hsn_file = st.file_uploader("Upload HSN Master (Excel or PDF)", type=["xlsx", "xls", "pdf"])
hsn_data = None
if hsn_file:
    with st.spinner("Reading HSN Master..."):
        try:
            hsn_data = load_hsn(hsn_file)
            st.success("✅ HSN Master Loaded")
            st.dataframe(hsn_data)
        except Exception as e:
            st.error(f"Error reading HSN master file: {e}")

# Upload Brochure File (Excel or PDF)
brochure_file = st.file_uploader("Upload Product Brochure (Excel or PDF)", type=["xlsx", "xls", "pdf"])
if brochure_file:
    with st.spinner("Reading Brochure..."):
        try:
            lines = load_brochure(brochure_file)
            st.text_area("📄 Extracted Brochure Text", "\n".join(lines), height=300)

            # Match HSN Codes with Enhanced Fuzzy Matching
            results = []
            if hsn_data is not None:
                for line in lines:
                    clean_line = re.sub(r"\s+", " ", line.strip().lower())
                    if clean_line:
                        lot_match = re.search(r"Lot\s*No[:\-]?\s*(\w+)", line, re.IGNORECASE)
                        lot_number = lot_match.group(1) if lot_match else "N/A"

                        best_score = 0
                        best_match = None
                        for _, row in hsn_data.iterrows():
                            hsn_desc = str(row["Product Description"]).lower()
                            score = fuzz.token_set_ratio(clean_line, hsn_desc)
                            if score > best_score:
                                best_score = score
                                best_match = row

                        if best_match is not None:
                            results.append({
                                "Lot Number": lot_number,
                                "Product Name": line[:30],
                                "Product Description": line,
                                "HSN Code": best_match["HSN Code"],
                                "Match Score": best_score
                            })

                if results:
                    result_df = pd.DataFrame(results)
                    st.subheader("📋 Matched HSN Codes")
                    st.dataframe(result_df)

                    # Export to Excel
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        result_df.to_excel(writer, index=False, sheet_name='HSN Matches')
                    st.download_button(
                        label="📥 Download Results as Excel",
                        data=output.getvalue(),
                        file_name="hsn_matches.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                else:
                    st.warning("No matches found.")
            else:
                st.warning("Please upload a valid HSN master file first.")
        except Exception as e:
            st.error(f"Error processing brochure file: {e}")
