import streamlit as st
from PIL import Image
import google.generativeai as genai

st.set_page_config(page_title="E-commerce SEO Generator", layout="wide")

st.title("🛍️ E-commerce Saree & Shirt SEO Generator")
st.write("Upload a garment image to generate high-converting, platform-specific SEO content for Amazon, Flipkart, and Meesho.")

# Automatically fetch API key from Streamlit Secrets
if "GEMINI_API_KEY" in st.secrets:
    gemini_api_key = st.secrets["GEMINI_API_KEY"]
else:
    gemini_api_key = st.text_input("Enter your Gemini API Key", type="password")

uploaded_file = st.file_uploader("Upload Garment Image (Saree/Shirt)", type=["jpg", "jpeg", "png"])
user_caption = st.text_input("Additional Notes (e.g., Kanjivaram silk, pure cotton, festive wear):", "")

if uploaded_file is not None and gemini_api_key:
    genai.configure(api_key=gemini_api_key)
    
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Garment", width=300)
    
    if st.button("🚀 Generate Platform-Specific SEO"):
        with st.spinner("Analyzing image and generating listings..."):
            try:
                prompt = f"""
                You are an Elite Senior E-commerce Cataloging Expert and Conversion Copywriter for Indian Marketplaces (Amazon, Flipkart, Meesho). 

                Analyze the garment image and user notes: "{user_caption}".

                Generate strict, high-converting, platform-specific content using top-ranking search keywords. Do NOT use generic text. Provide the output in the following strictly separated sections:

                1. 📊 PRICING & MARGIN STRATEGY:
                - Suggested MRP & Selling Price (Amazon/Flipkart): 
                - Suggested Selling Price (Meesho): 

                2. 🅰️ AMAZON LISTING DATA:
                - Title: [Optimized for A9 algorithm with high-intent buyer keywords]
                - Bullet Points (5 Points): [Benefit-driven, highly searchable features]
                - Description: [Detailed paragraph incorporating key features]
                - Backend Search Keywords: [Comma-separated high-volume search terms]

                3. 🔵 FLIPKART LISTING DATA:
                - Catalog Title: [Crisp, attribute-heavy title optimized for filters]
                - Product Highlights: [Short key specs]
                - Description: [Flipkart style catalog description]
                - Search Tags / Keywords: [Top 10-15 discovery tags specific to Flipkart]
                - Recommended Attributes: [Fabric, Fit, Collar, Ornamentation, Surface]

                4. 🟣 MEESHO LISTING DATA:
                - Reseller Product Name: [Catchy, value-focused product name]
                - Description & Key Selling Points: [Reseller and margin-focused bullet points]
                - Search Keywords / Tags: [Top trending tags for Meesho app search]
                """
                
                model = genai.GenerativeModel('gemini-2.5-flash')
                response = model.generate_content([prompt, image])
                
                st.success("Listing Generated Successfully!")
                st.markdown(response.text)
                
            except Exception as e:
                st.error(f"An error occurred: {e}")
elif not gemini_api_key and uploaded_file:
    st.warning("Please configure your Gemini API key in Streamlit Secrets or enter it above.")
