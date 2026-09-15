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
                You are an Elite E-commerce SEO Director, A9 Algorithm Specialist, and Marketplace Growth Hacker for Top Indian Sellers. 

                Analyze the garment image and user notes: "{user_caption}".

                Your primary objective is **SEARCH VISIBILITY, ALGORITHM RANKING, AND TRENDING DISCOVERY**. 
                Do NOT write generic descriptions. Every single section must be packed with high-volume buyer search terms, high-intent keywords, and SEO structures that force Amazon, Flipkart, and Meesho search engines to push this product to the top.

                Provide the output in the following strictly separated sections:

                1. 📊 PRICING & TREND MARGIN STRATEGY:
                - Suggested MRP & Competitive Selling Price (Amazon/Flipkart): 
                - Suggested High-Velocity Selling Price (Meesho): 

                2. 🅰️ AMAZON A9 ALGORITHM SEO LISTING:
                - High-Velocity Search Title: [Front-load core primary keywords within the first 50 characters, followed by material, pattern, and use-case for high CTR]
                - High-Converting Bullet Points (5 SEO-Optimized Points): [Incorporate primary and LSI keywords naturally while highlighting buyer benefits, sizing confidence, and fabric reliability]
                - Search-Indexed Description: [A rich narrative paragraph embedded with hidden semantic keywords and long-tail search terms that match buyer search queries]
                - Backend Search Keywords (Hidden Indexing Term List): [Comma-separated exact-match and variation high-volume search phrases without repeating words, max 250 bytes optimized]

                3. 🔵 FLIPKART DISCOVERY OPTIMIZED LISTING:
                - Catalog Discovery Title: [Crisp, attribute-heavy title structured exactly for Flipkart's filter and search indexing rules]
                - SEO Product Highlights: [Keyword-rich punchy specs]
                - Catalog Description: [Flipkart style descriptive text optimized for category search]
                - High-Traffic Search Tags / Keywords: [Top 15 trending discovery tags specifically searched on Flipkart app]
                - Search Filters Attributes: [Fabric, Fit, Collar, Sleeves, Pattern, Occasion]

                4. 🟣 MEESHO TRENDING SEARCH & RESELLER LISTING:
                - Viral Reseller Product Name: [Catchy, high-search-intent product name designed to rank on top of Meesho's app search bar]
                - SEO Description & Margin Selling Points: [Reseller-focused bullet points with trending keywords]
                - High-Volume Meesho Search Tags: [Top trending tags currently dominating Meesho app search queries]
                """
                
                model = genai.GenerativeModel('gemini-2.5-flash')
                response = model.generate_content([prompt, image])
                
                st.success("Listing Generated Successfully!")
                st.markdown(response.text)
                
            except Exception as e:
                st.error(f"An error occurred: {e}")
elif not gemini_api_key and uploaded_file:
    st.warning("Please configure your Gemini API key in Streamlit Secrets or enter it above.")
