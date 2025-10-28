import streamlit as st
import pandas as pd
import pytesseract
from PIL import Image
import pdfplumber
import io

st.title("🔍 HSN Code Identifier Tool")

# Upload HSN Master
hsn_file = st.file_uploader("Upload HSN Master (Excel or PDF)", type=["xlsx", "xls", "pdf"])
if hsn_file:
    if hsn_file.name.endswith(".pdf"):
        with pdfplumber.open(hsn_file) as pdf:
            text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
        hsn_data = pd.DataFrame([line.split("\t") for line in text.split("\n") if line.strip()])
        hsn_data.columns = ["HSN Code", "Product Description"]
    else:
        hsn_data = pd.read_excel(hsn_file)
    st.success("HSN Master Loaded ✅")
    st.dataframe(hsn_data)

# Upload Brochure
brochure_file = st.file_uploader("Upload Product Brochure (Image or PDF)", type=["png", "jpg", "jpeg", "pdf"])
if brochure_file:
    if brochure_file.name.endswith(".pdf"):
        with pdfplumber.open(brochure_file) as pdf:
            brochure_text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
    else:
        image = Image.open(brochure_file)
        brochure_text = pytesseract.image_to_string(image)

    st.text_area("Extracted Brochure Text", brochure_text, height=300)

    # Match HSN
    results = []
    for line in brochure_text.split("\n"):
        if line.strip():
            best_match = hsn_data[hsn_data["Product Description"].str.contains(line, case=False, na=False)]
            if not best_match.empty:
                results.append({
                    "Lot Number": "N/A",  # You can extract this with regex if needed
                    "Product Name": line[:30],
                    "Product Description": line,
                    "HSN Code": best_match.iloc[0]["HSN Code"]
                })

    if results:
        result_df = pd.DataFrame(results)
        st.subheader("📋 Matched HSN Codes")
        st.dataframe(result_df)

---

### 🔹 Step 4: Run the App
In your terminal, run:
```bash
streamlit run app.py
