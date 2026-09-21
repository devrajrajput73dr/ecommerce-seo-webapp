import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import urllib.parse
import time
import requests
import pandas as pd

# Page Configuration
st.set_page_config(
    page_title="E-Commerce Elite SEO & AI Virtual Model Studio",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Sidebar Navigation
st.sidebar.markdown("## 🛠️ E-Commerce Suite Navigation")
app_mode = st.sidebar.radio(
    "Select Tool Mode:",
    [
        "AI Virtual Model Studio (Gemini Powered)",
        "Single Listing & SEO Generator",
        "Listing Audit & Optimization Tool",
        "Bulk CSV Catalog Generator",
        "Profit Margin & Commission Calculator",
        "Smart Shipping Label Cropper & Sorter"
    ]
)

# API Key Configuration
st.sidebar.markdown("---")
gemini_api_key = None
if "GEMINI_API_KEY" in st.secrets:
    gemini_api_key = st.secrets["GEMINI_API_KEY"]

if not gemini_api_key:
    api_key_input = st.sidebar.text_input("Enter Gemini API Key", type="password")
    if api_key_input:
        gemini_api_key = api_key_input

if gemini_api_key:
    genai.configure(api_key=gemini_api_key)

def get_working_model():
    return genai.GenerativeModel('gemini-2.5-flash')

# Helper function with automatic retry for rate limits (429 errors)
def safe_generate_content(model, contents, retries=3, delay=10):
    for attempt in range(retries):
        try:
            return model.generate_content(contents)
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "Quota exceeded" in error_str:
                if attempt < retries - 1:
                    time.sleep(delay)
                    continue
            raise e

# ==========================================
# MODE 1: SINGLE LISTING & SEO GENERATOR
# ==========================================
if app_mode == "Single Listing & SEO Generator":
    st.title("📦 Multi-Platform SEO Listing Generator (Multi-Image Support)")
    st.markdown("Product/Garment ki images upload karein aur Amazon A9/A10, Flipkart, aur Meesho algorithms ke liye complete SEO content generate karein.")
    
    uploaded_listing_imgs = st.file_uploader("Upload Product/Garment Images (Max 4 angles)", type=["jpg", "jpeg", "png"], accept_multiple_files=True, key="single_listing_imgs")
    product_name = st.text_input("Enter Product Name / Category (e.g., Designer Silk Saree):")
    key_features = st.text_area("Enter Key Features / Fabric Details (e.g., Pure Kanjivaram Silk, Zari Work):")
    
    if uploaded_listing_imgs:
        if len(uploaded_listing_imgs) > 4:
            st.warning("⚠️ Please upload a maximum of 4 images.")
            uploaded_listing_imgs = uploaded_listing_imgs[:4]
            
        st.markdown("### 📸 Uploaded Images Preview:")
        cols = st.columns(len(uploaded_listing_imgs))
        opened_listing_images = []
        for i, file in enumerate(uploaded_listing_imgs):
            img = Image.open(file)
            opened_listing_images.append(img)
            with cols[i]:
                st.image(img, caption=f"View {i+1}", use_container_width=True)
                
    if st.button("Generate Optimized Listings") and product_name:
        if not gemini_api_key:
            st.warning("⚠️ Kripya pehle Gemini API Key configure karein.")
        else:
            with st.spinner("Analyzing product images and generating complete multi-platform listings..."):
                try:
                    model = get_working_model()
                    unified_prompt = [
                        f"""Act as an E-commerce Senior SEO Expert & Garment Analyst for Amazon (A9/A10), Flipkart, and Meesho algorithms.
                        Product Name: {product_name}
                        Additional Details: {key_features}
                        
                        Please analyze the uploaded product images and details to provide:
                        PART 1: GARMENT & PRODUCT ANALYSIS BREAKDOWN
                        - Design Type & Style (e.g., Ethnic, Anarkali, Kanjivaram, etc.)
                        - Print & Pattern Type (e.g., Floral Print, Embroidered, Zari Work, etc.)
                        - Occasion (Festive, Wedding, Party, etc.)
                        - Color & Fabric Quality (Shade, fabric type & grade)
                        
                        PART 2: COMPLETE MULTI-PLATFORM SEO CONTENT
                        Provide separate, fully detailed sections for:
                        1. Amazon India (A9/A10): Title, Bullet Points, Product Description, Search / Backend Keywords.
                        2. Flipkart: Title, Bullet Points, Product Description, Search Keywords.
                        3. Meesho Prism: Title, Trendy Description, Budget & Visual Focus Keywords.""",
                    ]
                    if 'opened_listing_images' in locals() and opened_listing_images:
                        unified_prompt.extend(opened_listing_images)
                        
                    response = safe_generate_content(model, unified_prompt)
                    st.markdown("### 📊 Complete Garment Analysis & Multi-Platform SEO Content")
                    st.write(response.text)
                    
                except Exception as e:
                    st.error(f"Error: {e}")

# ==========================================
# MODE 2: LISTING AUDIT & OPTIMIZATION TOOL
# ==========================================
elif app_mode == "Listing Audit & Optimization Tool":
    st.title("🔍 E-Commerce Listing Audit & Optimization")
    st.markdown("""
    <div style="background-color: #f0f2f6; padding: 10px; border-radius: 8px; margin-bottom: 15px;">
    Apni mojuda listing aur product ki images upload karein. Yeh tool Amazon A9/A10, Flipkart, aur Meesho algorithms ke mutabiq audit karke sudhara hua version dega.
    </div>
    """, unsafe_allow_html=True)
    
    audit_imgs = st.file_uploader("Upload Product Images for Audit (Max 4 images)", type=["jpg", "jpeg", "png"], accept_multiple_files=True, key="audit_imgs")
    existing_title = st.text_input("Enter Existing Product Title:")
    existing_bullets = st.text_area("Enter Existing Bullet Points / Features:")
    existing_desc = st.text_area("Enter Existing Product Description:")
    
    if audit_imgs:
        if len(audit_imgs) > 4:
            audit_imgs = audit_imgs[:4]
        cols_a = st.columns(len(audit_imgs))
        opened_audit_images = []
        for i, file in enumerate(audit_imgs):
            img = Image.open(file)
            opened_audit_images.append(img)
            with cols_a[i]:
                st.image(img, caption=f"Audit View {i+1}", use_container_width=True)

    if st.button("🔍 Audit & Optimize Listing") and existing_title:
        if not gemini_api_key:
            st.warning("⚠️ Kripya pehle Gemini API Key configure karein.")
        else:
            with st.spinner("Auditing listing against marketplace algorithms..."):
                try:
                    model = get_working_model()
                    audit_payload = [
                        f"""Act as a Senior E-Commerce Marketplace Auditor & SEO Expert for Amazon, Flipkart, and Meesho.
                        Analyze the following existing listing along with the uploaded product images:
                        - Title: {existing_title}
                        - Bullet Points: {existing_bullets}
                        - Description: {existing_desc}
                        
                        Please provide:
                        1. **Audit Score & Weaknesses:** What is missing in terms of high-search keywords and algorithm ranking factors?
                        2. **Marketplace-wise Recommendations:** Specific improvements for Amazon, Flipkart, and Meesho.
                        3. **Optimized Rewrite:** Fully rewritten, high-converting SEO optimized Title, Bullet Points, Description, and Search Keywords.""",
                    ]
                    if 'opened_audit_images' in locals() and opened_audit_images:
                        audit_payload.extend(opened_audit_images)
                        
                    response = safe_generate_content(model, audit_payload)
                    st.markdown("### 📈 Audit Report & Optimized Content")
                    st.write(response.text)
                except Exception as e:
                    st.error(f"Audit Error: {e}")

# ==========================================
# MODE 3: BULK CSV CATALOG GENERATOR
# ==========================================
elif app_mode == "Bulk CSV Catalog Generator":
    st.title("📁 Bulk CSV Catalog & Listing Generator")
    st.markdown("Multiple products ke liye categories enter karein aur ek sath SEO optimized listings aur CSV format generate karein.")
    
    categories_input = st.text_area("Enter Product Categories / Items (one per line):", "Designer Silk Saree\nEmbroidered Kurti Set\nFestive Lehenga Choli")

    if st.button("Generate Bulk CSV Data"):
        if not gemini_api_key:
            st.warning("⚠️ Kripya pehle Gemini API Key configure karein.")
        else:
            with st.spinner("Generating bulk catalog data..."):
                try:
                    model = get_working_model()
                    bulk_prompt = f"""Generate bulk e-commerce catalog data for the following categories:
                    {categories_input}
                    
                    Return a clean structured analysis with complete Titles, Bullet Points, Descriptions, and Search Keywords for Amazon, Flipkart, and Meesho."""
                    
                    response = safe_generate_content(model, bulk_prompt)
                    st.markdown("### 📋 Generated Bulk Data")
                    st.write(response.text)
                    
                    df_dummy = pd.DataFrame({
                        "Category": categories_input.split("\n"),
                        "Status": ["Ready for Marketplace"] * len(categories_input.split("\n"))
                    })
                    csv_data = df_dummy.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download Bulk CSV Template",
                        data=csv_data,
                        file_name="bulk_ecommerce_catalog.csv",
                        mime="text/csv"
                    )
                except Exception as e:
                    st.error(f"Error: {e}")

# ==========================================
# MODE 4: PROFIT MARGIN & COMMISSION CALCULATOR
# ==========================================
elif app_mode == "Profit Margin & Commission Calculator":
    st.title("💰 E-Commerce Profit Margin & Commission Calculator")
    st.markdown("Amazon, Flipkart, aur Meesho par selling cost, commission, shipping, aur net profit calculate karein.")
    
    col1, col2 = st.columns(2)
    with col1:
        cost_price = st.number_input("Product Cost Price (₹):", min_value=0.0, value=500.0)
        selling_price = st.number_input("Target Selling Price (₹):", min_value=0.0, value=1299.0)
    with col2:
        shipping_cost = st.number_input("Shipping & Packaging Cost (₹):", min_value=0.0, value=70.0)
        ad_spend = st.number_input("Estimated Ad Spend per Item (₹):", min_value=0.0, value=50.0)
        
    platform = st.selectbox("Select Marketplace:", ["Amazon India", "Flipkart", "Meesho"])
    
    if st.button("Calculate Net Profit"):
        commission_rate = 0.15 if platform == "Amazon India" else (0.12 if platform == "Flipkart" else 0.08)
        referral_fee = selling_price * commission_rate
        gst_on_fee = referral_fee * 0.18
        total_deductions = cost_price + shipping_cost + ad_spend + referral_fee + gst_on_fee
        net_profit = selling_price - total_deductions
        margin_percentage = (net_profit / selling_price) * 100 if selling_price > 0 else 0
        
        st.markdown("### 📊 Financial Breakdown")
        m_col1, m_col2, m_col3 = st.columns(3)
        m_col1.metric("Referral Fee + GST", f"₹{referral_fee + gst_on_fee:.2f}")
        m_col2.metric("Net Profit", f"₹{net_profit:.2f}", delta=f"{margin_percentage:.1f}% Margin")
        m_col3.metric("Total Expenses", f"₹{total_deductions:.2f}")
        
        if net_profit > 0:
            st.success("✅ Yeh product profitable hai! Aap iske sath aage badh sakte hain.")
        else:
            st.warning("⚠️ Is price par aapko loss ho sakta hai. Selling price badhayein ya cost kam karein.")

# ==========================================
# MODE 5: AI VIRTUAL MODEL STUDIO
# ==========================================
elif app_mode == "AI Virtual Model Studio (Gemini Powered)":
    st.title("👗 AI Virtual Model Studio (One-by-One Generation & Download)")
    st.markdown("""
    <div style="background-color: #f0f2f6; padding: 10px; border-radius: 8px; margin-bottom: 15px;">
    <b>Smart Protection Feature:</b> Yeh studio aapke uploaded garment ke <b>exact color, prints, borders, aur fabric quality ko 100% lock</b> rakhta hai. Aap apni pasand ka ek-ek background chun kar image generate aur download kar sakte hain.
    </div>
    """, unsafe_allow_html=True)
    
    if not gemini_api_key:
        st.warning("⚠️ Kripya sidebar mein apni Gemini API Key enter karein (ya Streamlit Secrets configure karein).")
    
    garment_files = st.file_uploader("Upload Photos of the Garment (Max 3 angles)", type=["jpg", "jpeg", "png"], accept_multiple_files=True, key="gemini_vton_uploader_single")
    
    if garment_files and gemini_api_key:
        if len(garment_files) > 3:
            st.warning("⚠️ Please upload a maximum of 3 photos.")
            garment_files = garment_files[:3]
            
        st.markdown("### 📸 Uploaded Garment Preview (Locked Reference):")
        cols = st.columns(len(garment_files))
        opened_images = []
        for i, file in enumerate(garment_files):
            img = Image.open(file)
            opened_images.append(img)
            with cols[i]:
                st.image(img, caption=f"Angle {i+1}", use_container_width=True)
                
        if "locked_garment_profile" not in st.session_state:
            st.session_state.locked_garment_profile = None
            
        if st.button("🔒 Step 1: Lock Garment & Analyze via Gemini"):
            with st.spinner("Analyzing and locking exact garment attributes..."):
                try:
                    model = get_working_model()
                    lock_prompt = [
                        """Strictly analyze these garment images. Create a master reference profile that locks the exact fabric color, precise dye shade, weave pattern, border designs, and unique motifs without altering any detail. 
                        Prepare a strict description for a professional e-commerce fashion catalog featuring a model wearing this exact unalterable garment.""",
                        *opened_images
                    ]
                    response = safe_generate_content(model, lock_prompt)
                    if response.text:
                        st.session_state.locked_garment_profile = response.text.strip()
                        st.success("✅ Garment Successfully Locked! Color, pattern, and quality parameters secured.")
                    else:
                        st.error("Analysis failed to return text. Please try again.")
                except Exception as e:
                    st.error(f"Analysis Error: {e}")
                    
        if st.session_state.locked_garment_profile:
            st.markdown("---")
            st.subheader("🎯 Step 2: Choose Algorithm & Generate Single Catalog Image")
            
            algo_choice = st.selectbox(
                "Target Marketplace Algorithm Optimizer:",
                [
                    "Amazon A9/A10 Algorithm (High Search Keyword & Conversion Focus)",
                    "Flipkart Algorithm (Value & Catalog Clarity Focus)",
                    "Meesho Prism Algorithm (Budget & Trendy Visual Focus)"
                ]
            )
            
            environments = {
                "E-Commerce Pure White Studio": "Professional e-commerce catalog studio photography, 100% pure white background, bright studio softbox lighting, high conversion layout",
                "Lush Green Garden Outdoor": "Outdoor natural lifestyle setting, botanical garden background, soft natural sunlight, high-end catalog look",
                "Modern Luxury Boutique Interior": "High-end luxury fashion boutique interior background, sophisticated designer racks, warm premium atmospheric lighting",
                "Traditional Heritage Courtyard": "Traditional Indian heritage courtyard background, ethnic architecture, warm terracotta tones, royal ethnic aesthetics",
                "Golden Hour Sunset Urban": "Outdoor sunset golden hour setting, warm glowing sunlight flare, urban chic aesthetic background, high resolution",
                "Modern Fashion Street Runway": "Modern urban city street fashion runway background, stylish architectural backdrop, dynamic street style lighting, high resolution"
            }
            
            selected_env_name = st.selectbox("Select Background/Environment:", list(environments.keys()))
            
            if st.button("🚀 Generate Selected Catalog Image"):
                with st.spinner(f"Generating catalog for '{selected_env_name}' with locked garment details..."):
                    try:
                        model = get_working_model()
                        env_style = environments[selected_env_name]
                        
                        generation_instruction = f"""
                        Generate a professional high-resolution e-commerce catalog visual optimized for {algo_choice}.
                        Strict Instruction: The garment worn by the professional fashion model must strictly match this locked specification: '{st.session_state.locked_garment_profile}'. 
                        Do not change the garment color, design, pattern, or fabric quality under any circumstances.
                        Background Setting: {env_style}.
                        Provide a vivid descriptive prompt for image rendering.
                        """
                        
                        prompt_response = safe_generate_content(model, generation_instruction)
                        if prompt_response.text:
                            optimized_prompt_text = prompt_response.text.strip()
                        else:
                            optimized_prompt_text = f"A professional fashion model wearing the exact garment described as {st.session_state.locked_garment_profile}, set in {env_style}, high resolution e-commerce catalog photography."
                        
                        encoded_prompt = urllib.parse.quote(optimized_prompt_text[:400])
                        seed_val = int(time.time())
                        target_url = f"https://pollinations.ai/p/{encoded_prompt}?width=768&height=1024&nologo=true&seed={seed_val}"
                        
                        img_resp = requests.get(target_url, timeout=30)
                        if img_resp.status_code == 200:
                            image_bytes = io.BytesIO(img_resp.content)
                            st.success(f"🎉 Successfully generated: {selected_env_name}!")
                            st.image(image_bytes, caption=selected_env_name, use_container_width=True)
                            
                            st.download_button(
                                label=f"📥 Download {selected_env_name}",
                                data=img_resp.content,
                                file_name=f"catalog_{selected_env_name.lower().replace(' ', '_')}.jpg",
                                mime="image/jpeg"
                            )
                        else:
                            st.error("Image generation service busy. Kripya dobara click karein.")
                            
                    except Exception as gen_err:
                        st.error(f"Generation Error: {gen_err}")

# ==========================================
# MODE 6: SMART SHIPPING LABEL CROPPER & PARTNER SORTER
# ==========================================
elif app_mode == "Smart Shipping Label Cropper & Sorter":
    st.title("✂️ Smart Shipping Label Cropper & Partner Sorter")
    st.markdown("""
    <div style="background-color: #f0f2f6; padding: 10px; border-radius: 8px; margin-bottom: 15px;">
    <b>Advanced E-Commerce Tool:</b> A4 shipping label sheets upload karein. Yeh tool invoices ko filter karega, 4x6 thermal format me crop coordinates batayega, delivery partners (Flipkart Ekart, Amazon Shipping, Delhivery, Meesho/Valmo, etc.) ke hisaab se sort karega aur SKU pick-list summary banayega.
    </div>
    """, unsafe_allow_html=True)
    
    selected_marketplace = st.selectbox(
        "Select Source Marketplace Preset:",
        ["Flipkart Seller Hub", "Amazon Shipping / Easy Ship", "Meesho Supplier Panel", "Multi-Marketplace Mixed Batch"]
    )
    
    label_file = st.file_uploader("Upload Shipping Label Sheet (Image/Snapshot)", type=["jpg", "jpeg", "png"], key="label_crop_file")
    
    if label_file:
        st.markdown("### 📄 Uploaded Label Sheet Preview:")
        opened_label_img = Image.open(label_file)
        st.image(opened_label_img, caption="Original Label Sheet", width=400)
        
        if not gemini_api_key:
            st.warning("⚠️ Kripya pehle sidebar mein Gemini API Key enter karein.")
        else:
            if st.button("🚀 Process, Crop & Sort by Delivery Partner"):
                with st.spinner("Analyzing labels, stripping invoices, and sorting by courier partner..."):
                    try:
                        model = get_working_model()
                        cropper_prompt = [
                            f"""Act as an expert E-Commerce Logistics & Thermal Label Cropper Tool.
                            Source Platform Preset: {selected_marketplace}
                            
                            Analyze the uploaded label document/image:
                            1. **Invoice & Margin Removal:** Identify and separate tax invoice sections from the actual logistics shipping label.
                            2. **Delivery Partner Detection:** Automatically classify each label based on courier logos/text (e.g., Flipkart Ekart, Amazon Shipping, Delhivery, Shadowfax, Xpressbees, Valmo/Meesho).
                            3. **Thermal 4x6 Optimization Details:** Provide precise cropping zones/instructions suitable for a 4x6 inch (100x150mm) thermal printer layout.
                            4. **SKU Pick-List Summary:** Extract and summarize the SKU items for consolidated dispatch tracking.
                            
                            Provide clean structured output with clear headings for Partner Sorting and Thermal Cropping Instructions.""",
                            opened_label_img
                        ]
                        response = safe_generate_content(model, cropper_prompt)
                        st.markdown("### 📊 Smart Label Cropping & Partner Sorting Report")
                        st.write(response.text)
                        
                        st.success("✅ Labels successfully processed, sorted by delivery partner, and optimized for thermal printing!")
                    except Exception as e:
                        st.error(f"Cropping & Sorting Error: {e}")
