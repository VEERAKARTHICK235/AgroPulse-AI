import streamlit as st
from PIL import Image
import base64
import requests
from io import BytesIO
from fpdf import FPDF
import re

# === Gemini API Configuration ===
GEMINI_API_KEY = "AIzaSyCVDQqukptLYzFObQFieAaUS8uR0nmksJI"  # Replace with your actual key
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

# === Helper: Convert image to base64 ===
def image_to_base64(image):
    buffered = BytesIO()
    image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode()

# === Gemini API Call ===
def get_gemini_predictions(base64_image):
    headers = {"Content-Type": "application/json"}
    prompt = """
You are a professional plant disease expert. An image of a leaf is uploaded.
Provide a list of the top 3 possible plant diseases and their respective cures.

Return strictly in this format:

Disease 1: <name>
Cure 1: <solution>

Disease 2: <name>
Cure 2: <solution>

Disease 3: <name>
Cure 3: <solution>
    """
    body = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": "image/jpeg", "data": base64_image}}
            ]
        }]
    }
    try:
        response = requests.post(GEMINI_API_URL, headers=headers, json=body)
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        return f"❌ Error: Could not get prediction. {e}"

# === Helper: Parse multiple diseases and cures ===
def extract_multiple_disease_cure(text):
    pattern = r"Disease\s*(\d+):\s*(.*?)\s*Cure\s*\1:\s*(.*?)(?=(\nDisease|\Z))"
    matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
    results = [{"Disease": m[1].strip(), "Cure": m[2].strip()} for m in matches]
    return results

# === Generate PDF with table ===
def generate_pdf(results):
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "AgroPulse AI - Plant Diagnosis Report", ln=True)

        pdf.set_font("Arial", "B", 12)
        pdf.cell(90, 10, "Disease", 1)
        pdf.cell(90, 10, "Cure", 1)
        pdf.ln()

        pdf.set_font("Arial", "", 11)
        for item in results:
            pdf.multi_cell(90, 10, item["Disease"], border=1, align='L', max_line_height=pdf.font_size)
            x = pdf.get_x()
            y = pdf.get_y() - 10
            pdf.set_xy(x + 90, y)
            pdf.multi_cell(90, 10, item["Cure"], border=1, align='L', max_line_height=pdf.font_size)
            pdf.ln()

        output = BytesIO()
        pdf.output(output)
        output.seek(0)
        return output
    except Exception as e:
        st.error(f"❌ PDF generation failed: {e}")
        return None

# === Streamlit UI ===
st.set_page_config(page_title="AgroPulse AI", page_icon="🌿")
st.title("🌿 AgroPulse AI - Multi-Disease Plant Diagnosis (Gemini)")
st.markdown("Upload a leaf image to get the **top 3 plant diseases** and their **suggested cures** using Gemini AI.")

uploaded_file = st.file_uploader("📷 Upload a leaf image", type=["jpg", "jpeg", "png"])
show_img = st.toggle("👁️ Show Image", value=False)

if uploaded_file:
    image = Image.open(uploaded_file)
    if show_img:
        st.image(image, caption="Uploaded Leaf", use_column_width=True)

    with st.spinner("🔍 Analyzing with Gemini..."):
        base64_img = image_to_base64(image)
        raw_result = get_gemini_predictions(base64_img)

    st.subheader("🧪 Prediction Results")
    results = extract_multiple_disease_cure(raw_result)

    if results:
        st.table({ "Disease": [r["Disease"] for r in results], "Cure": [r["Cure"] for r in results] })

        pdf_file = generate_pdf(results)
        if pdf_file:
            st.download_button(
                label="📄 Download Diagnosis Report (PDF)",
                data=pdf_file,
                file_name="plant_diagnosis_report.pdf",
                mime="application/pdf"
            )
    else:
        st.warning("⚠️ Could not extract structured results. Try again with a different image.")
