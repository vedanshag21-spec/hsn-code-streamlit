import streamlit as st
import pandas as pd
import pdfplumber
import re
import io

st.set_page_config(page_title="HSN Code Identifier", layout="wide")
st.title("🔍 HSN Code Identifier Tool")

# Upload HSN Master File
hsn_file = st.file_uploader("Upload HSN Master (Excel or PDF)", type=["xlsx", "xls", "pdf"])
if hsn_file:
    try:
        if hsn_file.name.endswith(".pdf"):
            with pdfplumber.open(hsn_file) as pdf:
                text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
            hsn_lines = [line.split("\t") for line in text.split("\n") if line.strip()]
            hsn_data = pd.DataFrame(hsn_lines, columns=["HSN Code", "Product Description"])
        else:
            hsn_data = pd.read_excel(hsn_file)
        st.success("✅ HSN Master Loaded")
        st.dataframe(hsn_data)
    except Exception as e:
        st.error(f"Error reading HSN master file: {e}")

# Upload Brochure File (PDF only)
brochure_file = st.file_uploader("Upload Product Brochure (PDF only)", type=["pdf"])
if brochure_file:
    try:
        with pdfplumber.open(brochure_file) as pdf:
            brochure_text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())

        st.text_area("📄 Extracted Brochure Text", brochure_text, height=300)

        # Match HSN Codes with Lot Number Extraction
        results = []
        for line in brochure_text.split("\n"):
            if line.strip():
                # Extract lot number if present
                lot_match = re.search(r"Lot\s*No[:\-]?\s*(\w+)", line, re.IGNORECASE)
                lot_number = lot_match.group(1) if lot_match else "N/A"

                match = hsn_data[hsn_data["Product Description"].str.contains(line, case=False, na=False)]
                if not match.empty:
                    results.append({
                        "Lot Number": lot_number,
                        "Product Name": line[:30],
                        "Product Description": line,
                        "HSN Code": match.iloc[0]["HSN Code"]
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
            st.warning("No matches found in HSN master.")
    except Exception as e:
        st.error(f"Error processing brochure: {e}")
