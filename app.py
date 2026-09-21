import streamlit as st
from PIL import Image
import google.generativeai as genai
import pandas as pd
import io
import requests

st.set_page_config(page_title="E-commerce Elite SEO & Automation Suite", layout="wide")

# Sidebar Configuration & Mode Selection
st.sidebar.title("🛠️ E-Commerce Suite Navigation")
app_mode = st.sidebar.radio("Select Tool Mode:", [
    "Single Listing & SEO Generator", 
    "Bulk CSV Catalog Generator", 
    "Profit Margin & Commission Calculator",
    "Listing Audit & Optimization Tool",
    "AI Virtual Model Studio"
])

if "GEMINI_API_KEY" in st.secrets:
    gemini_api_key = st.secrets["GEMINI_API_KEY"]
else:
    gemini_api_key = st.sidebar.text_input("Enter your Gemini API Key", type="password")

if not gemini_api_key:
    st.warning("⚠️ Please configure your Gemini API key in Streamlit Secrets or enter it in the sidebar.")

# Function to get working model dynamically
def get_working_model(is_image=False):
    genai.configure(api_key=gemini_api_key)
    model_candidates = ['gemini-2.5-flash', 'gemini-2.5-pro', 'gemini-pro']
    for m_name in model_candidates:
        try:
            m = genai.GenerativeModel(m_name)
            return m
        except Exception:
            continue
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            if is_image and ('vision' in m.name or '2.5' in m.name):
                return genai.GenerativeModel(m.name)
            elif not is_image:
                return genai.GenerativeModel(m.name)
    return genai.GenerativeModel('gemini-2.5-flash')

# Function to generate image using Hugging Face Official Client
def generate_hf_image(prompt_text, hf_token):
    try:
        client = InferenceClient("stabilityai/stable-diffusion-xl-base-1.0", token=hf_token)
        image = client.text_to_image(prompt_text)
        return image
    except Exception as e:
        st.error(f"Hugging Face API Error: {e}")
        return None

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
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Garment", width=300)
        
        if st.button("🚀 Generate Elite SEO & Growth Strategy"):
            with st.spinner("Analyzing image, locking fabric patterns, and generating algorithm-optimized listings..."):
                try:
                    prompt = f"""
                    You are an Elite E-commerce SEO Director, A9 Algorithm Specialist, and Marketplace Growth Hacker for Top Indian Sellers. 
                    Analyze the garment image and user notes: "{user_caption}". Sourcing cost is ₹{sourcing_cost}.
                    
                    Your primary objective is **SEARCH VISIBILITY, ALGORITHM RANKING, AND HIGH-CONVERSION DISCOVERY**. 
                    Lock the exact fabric color, design, pattern, and style shown in the image. Do NOT write generic text. 

                    Provide the output in the following strictly separated sections with complete details:
                    1. 📊 PRICING & TREND MARGIN STRATEGY
                    2. 🅰️ AMAZON A9 ALGORITHM SEO LISTING (Title, 5 Bullet Points, Description, Backend Keywords)
                    3. 🔵 FLIPKART DISCOVERY OPTIMIZED LISTING (Catalog Title, Highlights, Description, Search Tags, Attributes)
                    4. 🟣 MEESHO TRENDING SEARCH & RESELLER LISTING (Reseller Title, Description & WhatsApp Hook, Tags)
                    5. 📄 AMAZON A+ CONTENT (EBC) LAYOUT SUGGESTION
                    """
                    
                    model = get_working_model(is_image=True)
                    response = model.generate_content([prompt, image])
                    st.success("Elite Listing Generated Successfully!")
                    st.markdown(response.text)
                    
                except Exception as e:
                    st.error(f"An error occurred: {e}")

# ==========================================
# MODE 2: BULK CSV CATALOG GENERATOR
# ==========================================
elif app_mode == "Bulk CSV Catalog Generator":
    st.title("📦 Bulk Catalog SEO Generator & CSV Export")
    st.write("Generate comprehensive SEO titles, all bullet points, and descriptions for multiple products, then download them as a CSV file.")

    product_names_input = st.text_area("Enter Product Names/Types (one per line):", 
                                      "Blue Floral Rayon Shirt\nMaroon Kanjivaram Silk Saree")
    
    if st.button("🚀 Generate Bulk SEO & Prepare CSV") and gemini_api_key:
        with st.spinner("Generating complete listings and preparing CSV download..."):
            try:
                prompt = f"""
                Act as an E-commerce Bulk Cataloging Expert. For each product listed below, generate structured SEO data in a clean format covering Amazon, Flipkart, and Meesho.
                Products:
                {product_names_input}
                """
                model = get_working_model(is_image=False)
                response = model.generate_content(prompt)
                
                st.markdown(response.text)
                
                csv_buffer = io.StringIO()
                csv_buffer.write(response.text)
                csv_data = csv_buffer.getvalue().encode('utf-8')
                
                st.download_button(
                    label="📥 Download Bulk Listings CSV / Text File",
                    data=csv_data,
                    file_name="ecommerce_bulk_seo_listings.csv",
                    mime="text/csv"
                )
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

# ==========================================
# MODE 4: LISTING AUDIT & OPTIMIZATION TOOL
# ==========================================
elif app_mode == "Listing Audit & Optimization Tool":
    st.title("🔍 Existing Listing Audit & SEO Optimizer")
    st.write("Upload a screenshot of your live listing or paste its text below to find mistakes, missing keywords, and get an upgraded high-ranking version.")

    target_platform = st.selectbox("Select Target Marketplace for Audit:", ["Amazon India (A9)", "Flipkart", "Meesho"])
    
    audit_col1, audit_col2 = st.columns([1, 1])
    with audit_col1:
        audit_image = st.file_uploader("Upload Listing Screenshot (Optional):", type=["jpg", "jpeg", "png"], key="audit_img")
    with audit_col2:
        existing_listing_text = st.text_area("Or Paste existing product listing text here:", 
                                            "Men's Casual Shirt\nNice cotton shirt for men. Comfortable wear.\nColor: Blue")

    if st.button("🔎 Audit & Upgrade Listing") and gemini_api_key:
        with st.spinner("Analyzing listing mistakes, keyword gaps, and generating optimized version..."):
            try:
                prompt = f"""
                Act as an Elite E-commerce Algorithm Auditor and Senior SEO Copywriter for {target_platform}.
                Analyze the provided existing product listing (from text and/or attached image):
                Existing Text: "{existing_listing_text}"
                
                Provide a thorough audit report in structured sections: 
                1. ❌ MISTAKES & WEAKNESSES FOUND
                2. 🔑 MISSING HIGH-VOLUME KEYWORDS
                3. ✨ FULLY OPTIMIZED & UPGRADED LISTING (Title, 5 Bullet Points, Description, Backend Keywords)
                """
                model = get_working_model(is_image=True if audit_image is not None else False)
                if audit_image is not None:
                    img = Image.open(audit_image)
                    response = model.generate_content([prompt, img])
                else:
                    response = model.generate_content(prompt)
                st.success("Listing Audit & Optimization Complete!")
                st.markdown(response.text)
            except Exception as e:
                st.error(f"An error occurred during listing audit: {e}")

# ==========================================
# MODE 5: AI VIRTUAL MODEL STUDIO (PERMANENT FINAL FIX)
# ==========================================
elif app_mode == "AI Virtual Model Studio":
    st.title("👗 AI Virtual Model & Background Studio")
    st.write("Upload 1-3 photos of your garment. Analyze once, then select any background from the dropdown to instantly view and download your catalog image.")
    
    garment_files = st.file_uploader("Upload Garment Photos (Max 3 angles)", type=["jpg", "jpeg", "png"], accept_multiple_files=True, key="permanent_vton_uploader")
    
    if garment_files and gemini_api_key:
        if len(garment_files) > 3:
            st.warning("⚠️ Please upload a maximum of 3 photos.")
            garment_files = garment_files[:3]
            
        st.markdown("### 📸 Uploaded Garment Preview:")
        cols = st.columns(len(garment_files))
        opened_images = []
        for i, file in enumerate(garment_files):
            img = Image.open(file)
            opened_images.append(img)
            with cols[i]:
                st.image(img, caption=f"Angle {i+1}", use_container_width=True)
                
        # Initialize session state for analysis description
        if "vton_core_desc" not in st.session_state:
            st.session_state.vton_core_desc = None
            
        if st.button("✨ Step 1: Analyze Garment with AI"):
            with st.spinner("Analyzing garment fabric, color, and patterns..."):
                try:
                    model = get_working_model(is_image=True)
                    analysis_prompt = [
                        "Analyze these multiple photos of the same garment. Describe the exact fabric color, print design, borders, motifs, and details comprehensively. Create a detailed description for a professional female model wearing this exact garment.",
                        *opened_images
                    ]
                    response = model.generate_content(analysis_prompt)
                    st.session_state.vton_core_desc = response.text.title().strip()
                    st.success("✅ Analysis Complete! Now select your background below.")
                except Exception as analysis_err:
                    st.error(f"Analysis Error: {analysis_err}")
                    
        # If description is ready, show background selector
        if st.session_state.vton_core_desc:
            st.markdown("---")
            st.subheader("🎯 Step 2: Choose Background & Render")
            
            environments = {
                "1. E-Commerce White Background Studio": "Professional e-commerce catalog studio photography, 100% pure white background, bright even softbox lighting, sharp focus on garment, high resolution",
                "2. Lush Green Garden Outdoor": "Outdoor natural lifestyle setting, lush green botanical garden background, soft natural sunlight, cinematic depth of field, high resolution",
                "3. Modern Luxury Home Interior": "Modern luxury indoor home living room interior background, elegant warm ambient lighting, elegant interior decor, high resolution",
                "4. Traditional Heritage Courtyard": "Traditional Indian heritage courtyard background, ethnic architecture, warm terracotta tones, royal heritage aesthetics, high resolution",
                "5. Golden Hour Sunset Outdoor": "Outdoor sunset golden hour setting, warm glowing sunlight flare, urban chic aesthetic background, high resolution",
                "6. Modern Fashion Street Runway": "Modern urban city street fashion runway background, stylish architectural backdrop, dynamic street style lighting, high resolution",
                "7. Luxury Boutique Interior": "High-end luxury fashion boutique interior background, sophisticated designer racks, elegant warm lighting and premium atmosphere, high resolution"
            }
            
            selected_bg = st.selectbox("Select Catalog Background:", list(environments.keys()), key="vton_bg_dropdown")
            
            if st.button("🚀 Generate Selected Catalog Image", key="vton_generate_btn"):
                with st.spinner(f"Generating catalog for {selected_bg}..."):
                    import urllib.parse
                    import time
                    
                    bg_style = environments[selected_bg]
                    final_prompt = f"A hyper-realistic professional fashion model wearing {st.session_state.vton_core_desc}. Background setting: {bg_style}, commercial fashion photography."
                    
                    encoded_prompt = urllib.parse.quote(final_prompt)
                    timestamp_seed = int(time.time())
                    
                    # Using direct secure URL encoding with auto-refresh seed
                    target_url = f"https://pollinations.ai/p/{encoded_prompt}?width=768&height=1024&nologo=true&seed={timestamp_seed}"
                    
                    st.success(f"🎉 Catalog generated successfully for {selected_bg}!")
                    
                    # Streamlit ka native image renderer use karein
                    st.image(target_url, caption=selected_bg, use_container_width=True)
                    
                    # Display using native markdown iframe/image container to prevent any python decoding bugs
                    st.markdown(
                        f"""
                        <div style="display: flex; justify-content: center; align-items: center; margin-top: 10px; margin-bottom: 15px;">
                            <img src="{target_url}" width="100%" style="border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);" alt="Generated Catalog">
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
                    
                    st.info("💡 **Tip:** Aap generated image par right-click karke **'Save image as...'** select karke apni image turant download kar sakte hain!")
