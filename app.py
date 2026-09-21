import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import urllib.parse
import time
import requests

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
        "Profit Margin & Commission Calculator"
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

# ==========================================
# MODE 1: SINGLE LISTING & SEO GENERATOR
# ==========================================
if app_mode == "Single Listing & SEO Generator":
    st.title("📦 Multi-Platform SEO Listing Generator")
    product_name = st.text_input("Enter Product Name / Category (e.g., Designer Silk Saree):")
    key_features = st.text_area("Enter Key Features / Fabric Details:")
    
    if st.button("Generate Optimized Listings") and product_name:
        if not gemini_api_key:
            st.warning("⚠️ Kripya pehle Gemini API Key configure karein.")
        else:
            with st.spinner("Generating SEO optimized content..."):
                try:
                    model = get_working_model()
                    prompt = f"""
                    Act as an E-commerce SEO Expert for Amazon (A9/A10), Flipkart, and Meesho algorithms.
                    Product: {product_name}
                    Details: {key_features}
                    Provide optimized content for Amazon, Flipkart, and Meesho.
                    """
                    response = model.generate_content(prompt)
                    st.markdown("### 📊 Generated Multi-Platform SEO Content")
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
    Apni mojuda (existing) product listing yahan paste karein. Yeh tool Amazon A9/A10, Flipkart, aur Meesho algorithms ke mutabiq aapki listing ka audit karega aur kamiyaan sudhar kar ek high-converting version dega.
    </div>
    """, unsafe_allow_html=True)
    
    existing_title = st.text_input("Enter Existing Product Title:")
    existing_bullets = st.text_area("Enter Existing Bullet Points / Features:")
    existing_desc = st.text_area("Enter Existing Product Description:")
    
    if st.button("🔍 Audit & Optimize Listing") and existing_title:
        if not gemini_api_key:
            st.warning("⚠️ Kripya pehle Gemini API Key configure karein.")
        else:
            with st.spinner("Auditing listing against marketplace algorithms..."):
                try:
                    model = get_working_model()
                    audit_prompt = f"""
                    Act as a Senior E-Commerce Marketplace Auditor & SEO Expert for Amazon, Flipkart, and Meesho.
                    Analyze the following existing listing:
                    - Title: {existing_title}
                    - Bullet Points: {existing_bullets}
                    - Description: {existing_desc}
                    
                    Please provide:
                    1. **Audit Score & Weaknesses:** What is missing in terms of high-search keywords and algorithm ranking factors?
                    2. **Marketplace-wise Recommendations:** Specific improvements for Amazon A9/A10, Flipkart, and Meesho.
                    3. **Optimized Rewrite:** Fully rewritten, high-converting SEO optimized Title, Bullet Points, and Description.
                    """
                    response = model.generate_content(audit_prompt)
                    st.markdown("### 📈 Audit Report & Optimized Content")
                    st.write(response.text)
                except Exception as e:
                    st.error(f"Audit Error: {e}")

# ==========================================
# MODE 5: AI VIRTUAL MODEL STUDIO (ONE BY ONE GENERATION)
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
                    response = model.generate_content(lock_prompt)
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
                        
                        prompt_response = model.generate_content(generation_instruction)
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

else:
    st.title("📦 Other Tools")
    st.info("Aap sidebar se 'AI Virtual Model Studio' ya 'Listing Audit Tool' select karke apna kaam shuru kar sakte hain.")
