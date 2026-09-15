import streamlit as st
from PIL import Image
import google.generativeai as genai
import pandas as pd

st.set_page_config(page_title="E-commerce Elite SEO & Automation Suite", layout="wide")

# Sidebar Configuration & Mode Selection
st.sidebar.title("🛠️ E-Commerce Suite Navigation")
app_mode = st.sidebar.radio("Select Tool Mode:", ["Single Listing & SEO Generator", "Bulk CSV Catalog Generator", "Profit Margin & Commission Calculator"])

# Automatically fetch API key from Streamlit Secrets or User Input
if "GEMINI_API_KEY" in st.secrets:
    gemini_api_key = st.secrets["GEMINI_API_KEY"]
else:
    gemini_api_key = st.sidebar.text_input("Enter your Gemini API Key", type="password")

if not gemini_api_key:
    st.warning("⚠️ Please configure your Gemini API key in Streamlit Secrets or enter it in the sidebar.")

# ==========================================
# MODE 1: SINGLE LISTING & SEO GENERATOR
# ==========================================
if app_mode == "Single Listing & SEO Generator":
    st.title("🛍️ Advanced E-commerce Saree & Shirt SEO Generator")
    st.write("Upload a garment image to generate high-converting, search-optimized platform listings for Amazon, Flipkart, and Meesho.")

    col1, col2 = st.columns([1, 1])
    with col1:
        uploaded_file = st.file_uploader("Upload Garment Image (Saree/Shirt)", type=["jpg", "jpeg", "png"])
    with col2:
        user_caption = st.text_input("Additional Notes (e.g., Kanjivaram silk, pure cotton, festive wear, color details):", "")
        sourcing_cost = st.number_input("Enter Product Sourcing/Manufacturing Cost (₹) for Profit estimation:", min_value=0.0, value=300.0, step=50.0)

    if uploaded_file is not None and gemini_api_key:
        genai.configure(api_key=gemini_api_key)
        image = Image.open(uploaded_file)
        
        st.image(image, caption="Uploaded Garment", width=300)
        
        if st.button("🚀 Generate Elite SEO & Growth Strategy"):
            with st.spinner("Analyzing image, locking fabric patterns, and generating algorithm-optimized listings..."):
                try:
                    prompt = f"""
                    You are an Elite E-commerce SEO Director, A9 Algorithm Specialist, and Marketplace Growth Hacker for Top Indian Sellers. 
                    Analyze the garment image and user notes: "{user_caption}". Sourcing cost is ₹{sourcing_cost}.
                    Provide the output in the following strictly separated sections:
                    1. 📊 PRICING & TREND MARGIN STRATEGY
                    2. 🅰️ AMAZON A9 ALGORITHM SEO LISTING (Title, 5 Bullet Points, Description, Backend Keywords)
                    3. 🔵 FLIPKART DISCOVERY OPTIMIZED LISTING (Catalog Title, Highlights, Description, Search Tags, Attributes)
                    4. 🟣 MEESHO TRENDING SEARCH & RESELLER LISTING (Reseller Title, Description & WhatsApp Hook, Tags)
                    5. 📄 AMAZON A+ CONTENT (EBC) LAYOUT SUGGESTION
                    """
                    
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    response = model.generate_content([prompt, image])
                    
                    st.success("Elite Listing Generated Successfully!")
                    st.markdown(response.text)
                    
                except Exception as e:
                    st.error(f"An error occurred: {e}")

# ==========================================
# MODE 2: BULK CSV CATALOG GENERATOR
# ==========================================
elif app_mode == "Bulk CSV Catalog Generator":
    st.title("📦 Bulk Catalog SEO Generator")
    st.write("Generate comprehensive SEO titles, all 5 bullet points, full descriptions, and keywords for multiple products.")

    product_names_input = st.text_area("Enter Product Names/Types (one per line):", 
                                      "Blue Floral Rayon Shirt\nMaroon Kanjivaram Silk Saree")
    
    if st.button("🚀 Generate Detailed Bulk SEO") and gemini_api_key:
        with st.spinner("Generating complete listings with all bullet points and descriptions..."):
            try:
                genai.configure(api_key=gemini_api_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                prompt = f"""
                Act as an E-commerce Bulk Cataloging Expert. For each product listed below, generate complete and detailed SEO data including Amazon Title, 5 Bullet Points, Detailed Description, Flipkart Title, and Search Keywords.
                Products:
                {product_names_input}
                """
                response = model.generate_content(prompt)
                st.markdown(response.text)
            except Exception as e:
                st.error(f"An error occurred in Bulk Generator: {e}")

# ==========================================
# MODE 3: PROFIT MARGIN & COMMISSION CALCULATOR
# ==========================================
elif app_mode == "Profit Margin & Commission Calculator":
    st.title("💰 Marketplace Profit & Commission Calculator")
    st.write("Calculate your net earnings, marketplace referral fees, closing fees, GST, and shipping charges across Amazon, Flipkart, and Meesho.")

    col1, col2 = st.columns(2)
    with col1:
        sp = st.number_input("Expected Selling Price (₹):", min_value=100.0, value=799.0, step=50.0)
        cost = st.number_input("Product Sourcing / Manufacturing Cost (₹):", min_value=0.0, value=300.0, step=50.0)
    with col2:
        shipping_cost = st.number_input("Estimated Shipping Cost (₹):", min_value=0.0, value=60.0, step=10.0)
        gst_percent = st.selectbox("GST Rate on Apparel (%):", [5, 12, 18], index=0)

    if st.button("📊 Calculate Net Profit"):
        commission_amazon = sp * 0.18
        commission_flipkart = sp * 0.17
        commission_meesho = sp * 0.05
        
        net_amazon = sp - (cost + commission_amazon + shipping_cost + (sp * gst_percent / 100))
        net_flipkart = sp - (cost + commission_flipkart + shipping_cost + (sp * gst_percent / 100))
        net_meesho = sp - (cost + commission_meesho + shipping_cost + (sp * gst_percent / 100))

        st.markdown("### 📈 Profitability Summary:")
        res_df = pd.DataFrame({
            "Platform": ["Amazon India", "Flipkart", "Meesho"],
            "Estimated Selling Price": [f"₹{sp}", f"₹{sp}", f"₹{sp}"],
            "Est. Commission & Fees": [f"₹{commission_amazon:.2f}", f"₹{commission_flipkart:.2f}", f"₹{commission_meesho:.2f}"],
            "Net Profit (₹)": [f"₹{net_amazon:.2f}", f"₹{net_flipkart:.2f}", f"₹{net_meesho:.2f}"],
            "ROI (%)": [f"{(net_amazon/cost)*100:.1f}%", f"{(net_flipkart/cost)*100:.1f}%", f"{(net_meesho/cost)*100:.1f}%"]
        })
        st.table(res_df)
