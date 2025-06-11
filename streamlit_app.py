import streamlit as st
from PIL import Image
import base64
import requests
from io import BytesIO
from fpdf import FPDF
import re
import tempfile
import os

# 🔐 Gemini API
GEMINI_API_KEY = "AIzaSyCVDQqukptLYzFObQFieAaUS8uR0nmksJI"  # Replace with your API key
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

# Convert image to base64
def image_to_base64(image):
    buffered = BytesIO()
    image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode()

# Gemini API call
def get_gemini_prediction(base64_image):
    headers = {"Content-Type": "application/json"}
    prompt = """
You are an expert plant pathologist. An image of a leaf is uploaded.
Identify the plant disease based on the image and suggest **3 short cures or solutions**.

Return the output in this format:

Disease: <disease name>
Cure:
1. <First cure>
2. <Second cure>
3. <Third cure>
"""
    request_body = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": base64_image
                        }
                    }
                ]
            }
        ]
    }
    try:
        response = requests.post(GEMINI_API_URL, headers=headers, json=request_body)
        result = response.json()
        return result["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        return f"❌ Error: Could not get a prediction. {str(e)}"

# Extract Disease and Cure
def extract_disease_and_cure(text):
    disease_match = re.search(r'Disease:\s*(.+)', text, re.IGNORECASE)
    cure_matches = re.findall(r'\d+\.\s*(.+)', text)

    disease = disease_match.group(1).strip() if disease_match else "Not found"
    cure = "\n".join([f"{i+1}. {c.strip()}" for i, c in enumerate(cure_matches)]) if cure_matches else "Not found"
    return disease, cure

# Generate PDF and return as BytesIO
def generate_pdf(disease, cure, image):
    try:
        pdf = FPDF()
        pdf.add_page()

        # Title
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "AgroPulse AI - Plant Diagnosis Report", ln=True)

        # Save image to temporary path
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            image.save(tmp.name)
            image_path = tmp.name

        # Insert image
        pdf.ln(5)
        pdf.image(image_path, w=100)

        # Disease (bold red)
        pdf.ln(10)
        pdf.set_font("Arial", "B", 12)
        pdf.set_text_color(220, 50, 50)
        pdf.cell(0, 10, f"Disease: {disease}", ln=True)

        # Cure (italic black)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", "I", 12)
        pdf.multi_cell(0, 10, f"Cure:\n{cure}")

        # Clean up temp file
        os.remove(image_path)

        # Return PDF
        pdf_output = pdf.output(dest="S")
        if isinstance(pdf_output, str):
            pdf_output = pdf_output.encode("latin-1")
        return BytesIO(pdf_output)

    except Exception as e:
        st.error(f"❌ PDF generation failed: {e}")
        return None

# Streamlit UI
st.set_page_config(page_title="AgroPulse AI - Gemini Powered", page_icon="🌿")
st.title("🌿 AgroPulse AI - Plant Disease Detector (Gemini API)")
st.markdown("Upload a leaf image to get the **plant disease** and its **suggested cures** using Gemini AI.")

# Upload Image
uploaded_file = st.file_uploader("📷 Choose a plant leaf image...", type=["jpg", "jpeg", "png"])

# Toggle to preview image
show_image = st.toggle("👁️ Show Uploaded Image", value=False)

if uploaded_file:
    image = Image.open(uploaded_file)
    if show_image:
        st.image(image, caption="🖼️ Uploaded Image", use_column_width=True)

    with st.spinner("🔍 Analyzing with Gemini..."):
        base64_img = image_to_base64(image)
        result_text = get_gemini_prediction(base64_img)

    st.subheader("🧪 Diagnosis Result")
    disease, cure = extract_disease_and_cure(result_text)

    st.markdown(f"""
    <div style="border: 1px solid #ccc; border-radius: 6px; padding: 10px;">
        <b>🌿 Plant Disease:</b> {disease}  
        <br><br>
        <b>💊 Suggested Cure:</b><br>
        {"<br>".join(cure.splitlines())}
    </div>
    """, unsafe_allow_html=True)


    pdf_data = generate_pdf(disease, cure, image)
    if pdf_data:
        st.download_button(
            label="📄 Download Diagnosis Report (PDF)",
            data=pdf_data,
            file_name="plant_diagnosis_report.pdf",
            mime="application/pdf"
        )
