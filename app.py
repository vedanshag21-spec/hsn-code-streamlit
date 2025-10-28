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
        df = pd.DataFrame(hsn_lines)
    else:
        df = pd.read_excel(file)

    # Rename first two columns to standard names
    if df.shape[1] >= 2:
        df = df.iloc[:, :2]
        df.columns = ["HSN Code", "Product Description"]
    else:
        raise ValueError("HSN master must have at least two columns.")

    return df

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

            # Match HSN Codes with Top 3 Suggestions
            results = []
            if hsn_data is not None:
                for line in lines:
                    clean_line = re.sub(r"\s+", " ", line.strip().lower())
                    if clean_line:
                        lot_match = re.search(r"Lot\s*No[:\-]?\s*(\w+)", line, re.IGNORECASE)
                        lot_number = lot_match.group(1) if lot_match else "N/A"

                        # Score all HSN descriptions
                        scored_matches = []
                        for _, row in hsn_data.iterrows():
                            hsn_desc = str(row.get("Product Description", "")).lower()
                            score = fuzz.token_set_ratio(clean_line, hsn_desc)
                            scored_matches.append((score, row["HSN Code"], row["Product Description"]))

                        # Sort and pick top 3
                        top_matches = sorted(scored_matches, reverse=True)[:3]
                        for match in top_matches:
                            results.append({
                                "Lot Number": lot_number,
                                "Product Name": line[:30],
                                "Product Description": line,
                                "HSN Code": match[1],
                                "Suggested Description": match[2]
                            })

                if results:
                    result_df = pd.DataFrame(results)
                    st.subheader("📋 Top HSN Code Suggestions")
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
