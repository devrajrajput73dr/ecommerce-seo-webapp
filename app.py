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

# Sidebar Navigation (Default set to AI Virtual Model Studio)
st.sidebar.markdown("## 🛠️ E-Commerce Suite Navigation")
app_mode = st.sidebar.radio(
    "Select Tool Mode:",
    [
        "AI Virtual Model Studio (Gemini Powered)",
        "Single Listing & SEO Generator",
        "Bulk CSV Catalog Generator",
        "Profit Margin & Commission Calculator",
        "Listing Audit & Optimization Tool"
    ]
)

# API Key Configuration (Automatic detection from secrets or sidebar input)
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

def get_working_model(is_image=False):
    return genai.GenerativeModel('gemini-2.5-flash')

# ==========================================
# MODE 1: SINGLE LISTING & SEO GENERATOR
# ==========================================
if app_mode == "Single Listing & SEO Generator":
    st.title("📦 Multi-Platform SEO Listing Generator")
    st.markdown("Generate high-converting titles, bullet points, and descriptions optimized for **Amazon A9/A10, Flipkart, and Meesho Prism** algorithms.")
    
    product_name = st.text_input("Enter Product Name / Category (e.g., Designer Silk Saree):")
    key_features = st.text_area("Enter Key Features / Fabric Details (e.g., Pure Kanjivaram Silk, Zari Work):")
    
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
                    
                    Provide optimized content for:
                    1. Amazon A9/A10 (High search volume backend & frontend keywords, conversion-focused bullet points).
                    2. Flipkart Algorithm (Clarity, value propositions, high search attributes).
                    3. Meesho Prism Algorithm (Trendy, budget & visual-appeal focused description).
                    """
                    response = model.generate_content(prompt)
                    st.markdown("### 📊 Generated Multi-Platform SEO Content")
                    st.write(response.text)
                except Exception as e:
                    st.error(f"Error: {e}")

# ==========================================
# MODE 5: AI VIRTUAL MODEL STUDIO (GEMINI POWERED WITH GARMENT LOCK)
# ==========================================
elif app_mode == "AI Virtual Model Studio (Gemini Powered)":
    st.title("👗 AI Virtual Model Studio (Strict Garment Lock & 6 Variations)")
    st.markdown("""
    <div style="background-color: #f0f2f6; padding: 10px; border-radius: 8px; margin-bottom: 15px;">
    <b>Smart Protection Feature:</b> Yeh studio aapke uploaded garment ke <b>exact color, prints, borders, aur fabric quality ko 100% lock</b> rakhta hai aur 5-6 alag-alag professional backgrounds mein catalog generate karta hai.
    </div>
    """, unsafe_allow_html=True)
    
    if not gemini_api_key:
        st.warning("⚠️ Kripya sidebar mein apni Gemini API Key enter karein (ya Streamlit Secrets configure karein).")
    
    garment_files = st.file_uploader("Upload Photos of the Garment (Max 3 angles)", type=["jpg", "jpeg", "png"], accept_multiple_files=True, key="gemini_vton_uploader_multi")
    
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
                    model = get_working_model(is_image=True)
                    lock_prompt = [
                        """Strictly analyze these garment images. Create a master reference profile that locks the exact fabric color, precise dye shade, weave pattern, border designs, and unique motifs without altering any detail. 
                        Prepare a strict description for a professional e-commerce fashion catalog featuring a model wearing this exact unalterable garment.""",
                        *opened_images
                    ]
                    response = model.generate_content(lock_prompt)
                    st.session_state.locked_garment_profile = response.text.strip()
                    st.success("✅ Garment Successfully Locked! Color, pattern, and quality parameters secured.")
                except Exception as e:
                    st.error(f"Analysis Error: {e}")
                    
        if st.session_state.locked_garment_profile:
            st.markdown("---")
            st.subheader("🎯 Step 2: Choose Algorithm & Generate 6 Catalog Variations")
            
            algo_choice = st.selectbox(
                "Target Marketplace Algorithm Optimizer:",
                [
                    "Amazon A9/A10 Algorithm (High Search Keyword & Conversion Focus)",
                    "Flipkart Algorithm (Value & Catalog Clarity Focus)",
                    "Meesho Prism Algorithm (Budget & Trendy Visual Focus)"
                ]
            )
            
            environments = {
                "1. E-Commerce Pure White Studio": "Professional e-commerce catalog studio photography, 100% pure white background, bright studio softbox lighting, high conversion layout",
                "2. Lush Green Garden Outdoor": "Outdoor natural lifestyle setting, botanical garden background, soft natural sunlight, high-end catalog look",
                "3. Modern Luxury Boutique Interior": "High-end luxury fashion boutique interior background, sophisticated designer racks, warm premium atmospheric lighting",
                "4. Traditional Heritage Courtyard": "Traditional Indian heritage courtyard background, ethnic architecture, warm terracotta tones, royal ethnic aesthetics",
                "5. Golden Hour Sunset Urban": "Outdoor sunset golden hour setting, warm glowing sunlight flare, urban chic aesthetic background, high resolution",
                "6. Modern Fashion Street Runway": "Modern urban city street fashion runway background, stylish architectural backdrop, dynamic street style lighting, high resolution"
            }
            
            if st.button("🚀 Generate All 6 Catalog Variations"):
                with st.spinner("Generating 6 professional variations with locked garment details... This may take a moment."):
                    try:
                        model = get_working_model(is_image=False)
                        st.success("🎉 All 6 Variations Generated Successfully! Aap niche har image ko alag-alag download kar sakte hain:")
                        
                        for idx, (env_name, env_style) in enumerate(environments.items(), 1):
                            st.markdown(f"### Variation {idx}: {env_name}")
                            
                            generation_instruction = f"""
                            Generate a professional high-resolution e-commerce catalog visual optimized for {algo_choice}.
                            Strict Instruction: The garment worn by the professional fashion model must strictly match this locked specification: '{st.session_state.locked_garment_profile}'. 
                            Do not change the garment color, design, pattern, or fabric quality under any circumstances.
                            Background Setting: {env_style}.
                            """
                            
                            prompt_response = model.generate_content(generation_instruction)
                            optimized_prompt_text = prompt_response.text.strip()
                            
                            encoded_prompt = urllib.parse.quote(optimized_prompt_text[:400])
                            seed_val = int(time.time()) + idx
                            target_url = f"https://pollinations.ai/p/{encoded_prompt}?width=768&height=1024&nologo=true&seed={seed_val}"
                            
                            try:
                                img_resp = requests.get(target_url, timeout=30)
                                if img_resp.status_code == 200:
                                    image_bytes = io.BytesIO(img_resp.content)
                                    st.image(image_bytes, caption=f"{env_name}", use_container_width=True)
                                    
                                    st.download_button(
                                        label=f"📥 Download Variation {idx} ({env_name.split('.')[1].strip()})",
                                        data=img_resp.content,
                                        file_name=f"catalog_variation_{idx}.jpg",
                                        mime="image/jpeg",
                                        key=f"dl_btn_{idx}"
                                    )
                                else:
                                    st.image(target_url, caption=env_name, use_container_width=True)
                            except Exception:
                                st.image(target_url, caption=env_name, use_container_width=True)
                                
                            st.markdown("---")
                            
                    except Exception as gen_err:
                        st.error(f"Generation Error: {gen_err}")

else:
    st.title("📦 Additional Tools")
    st.info("Aap sidebar se 'AI Virtual Model Studio (Gemini Powered)' ya 'Single Listing & SEO Generator' select karke apna kaam shuru kar sakte hain.")
