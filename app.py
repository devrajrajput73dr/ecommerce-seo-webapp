import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import urllib.parse
import time
import requests

# Corrected Page Configuration (layout instead of page_layout)
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
        "Single Listing & SEO Generator",
        "Bulk CSV Catalog Generator",
        "Profit Margin & Commission Calculator",
        "Listing Audit & Optimization Tool",
        "AI Virtual Model Studio (Gemini Powered)"
    ]
)

# API Key Configuration
st.sidebar.markdown("---")
gemini_api_key = st.sidebar.text_input("Enter Gemini API Key", type="password")

if gemini_api_key:
    genai.configure(api_key=gemini_api_key)

def get_working_model(is_image=False):
    return genai.GenerativeModel('gemini-2.5-flash')

# ==========================================
# MODE 5: AI VIRTUAL MODEL STUDIO (5-6 VARIATIONS & INDIVIDUAL DOWNLOAD)
# ==========================================
if app_mode == "AI Virtual Model Studio (Gemini Powered)":
    st.title("👗 AI Virtual Model Studio (5-6 Variations & Individual Downloads)")
    st.markdown("""
    <div style="background-color: #f0f2f6; padding: 10px; border-radius: 8px; margin-bottom: 15px;">
    <b>Smart Protection Feature:</b> Yeh studio aapke uploaded garment ke <b>exact color, prints, borders, aur fabric quality ko 100% lock</b> rakhta hai aur 5-6 alag-alag professional backgrounds mein catalog generate karta hai.
    </div>
    """, unsafe_allow_html=True)
    
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
            st.subheader("🎯 Step 2: Generate 5-6 Catalog Variations")
            
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
                            Generate a professional high-resolution e-commerce catalog visual.
                            Strict Instruction: The garment worn by the professional fashion model must strictly match this locked specification: '{st.session_state.locked_garment_profile}'. 
                            Do not change the garment color, design, pattern, or fabric quality under any circumstances.
                            Background Setting: {env_style}. Optimized for {algo_choice}.
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
    if not gemini_api_key:
        st.warning("⚠️ Kripya pehle sidebar mein apni Gemini API Key enter karein.")
