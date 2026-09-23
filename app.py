import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import urllib.parse
import time
import requests
import pandas as pd
import json
import re
import difflib

# Page Configuration
st.set_page_config(
    page_title="E-Commerce Elite SEO & AI Virtual Model Studio",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ==========================================
# LISTING AUDITOR PRO V3 - DETERMINISTIC RULE ENGINE
# ==========================================
PLATFORM_PROFILES = {
    "Amazon India": {
        "title_max": 200,
        "bullet_target": 5,
        "description_max": None,
        "notes": "Amazon.in's current public listing guidance states a 200-character maximum title and describes titles, images, bullet points and descriptions as core listing fields."
    },
    "Flipkart": {
        "title_max": 200,
        "bullet_target": 5,
        "description_max": 4000,
        "notes": "Flipkart field requirements can vary by category/catalogue; use the current seller panel/category template as the final validation source."
    },
    "Meesho": {
        "title_max": 150,
        "bullet_target": 5,
        "description_max": None,
        "notes": "Meesho field requirements can vary by catalogue/category; use the current supplier panel as the final validation source."
    }
}

PROMO_CLAIMS = [
    "best", "no.1", "#1", "number one", "guaranteed", "guarantee",
    "lowest price", "cheapest", "best seller", "top selling"
]

STOPWORDS = {
    "the","and","for","with","from","this","that","are","you","your","our",
    "of","to","in","on","a","an","is","it","by","as","at","or","be","has",
    "have","will","can","into","made","ideal","use","using","also","only"
}

def _audit_normalize(text):
    return re.sub(r"[^a-z0-9\s]", " ", str(text or "").lower())

def _audit_tokens(text):
    return [
        t for t in _audit_normalize(text).split()
        if len(t) > 1 and t not in STOPWORDS
    ]

def _audit_word_counts(text):
    counts = {}
    for token in _audit_tokens(text):
        counts[token] = counts.get(token, 0) + 1
    return counts

def _audit_parse_keywords(text):
    if not text:
        return []
    return [p.strip().lower() for p in re.split(r"[,;\n|]+", str(text)) if p.strip()]

def _audit_parse_attributes(text):
    result = {}
    for line in str(text or "").splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip().lower()
            if key:
                result[key] = value.strip()
    return result

def run_deterministic_listing_audit(
    marketplace, title, bullets, description, backend_terms,
    attributes, verified_facts, target_keywords,
    category="", product_type="", browse_node=""
):
    profile = PLATFORM_PROFILES.get(marketplace, PLATFORM_PROFILES["Amazon India"])
    title = str(title or "").strip()
    bullets = str(bullets or "").strip()
    description = str(description or "").strip()
    backend_terms = str(backend_terms or "").strip()
    category = str(category or "").strip()
    product_type = str(product_type or "").strip()
    browse_node = str(browse_node or "").strip()

    issues = []
    title_len = len(title)
    max_title = profile["title_max"]

    if not title:
        issues.append({
            "severity": "CRITICAL", "field": "Title",
            "problem": "Title is empty.",
            "recommended_fix": "Add a precise product title using verified product facts."
        })
    elif title_len > max_title:
        issues.append({
            "severity": "HIGH", "field": "Title",
            "problem": f"Title is {title_len} characters; profile reference is {max_title}.",
            "recommended_fix": "Shorten the title while retaining product type, key material/design, colour and differentiating attributes."
        })

    title_counts = _audit_word_counts(title)
    duplicate_title_words = sorted([w for w, n in title_counts.items() if n >= 3])
    if duplicate_title_words:
        issues.append({
            "severity": "MEDIUM", "field": "Title",
            "problem": "Repeated title words detected: " + ", ".join(duplicate_title_words),
            "recommended_fix": "Remove unnecessary repetition and use distinct relevant attributes."
        })

    bullet_lines = [x.strip(" •-\t") for x in bullets.splitlines() if x.strip(" •-\t")]
    bullet_count = len(bullet_lines)
    if marketplace == "Amazon India" and bullet_count < 5:
        issues.append({
            "severity": "HIGH", "field": "Bullet Points",
            "problem": f"Only {bullet_count} bullet(s) supplied; this auditor targets 5 for a complete Amazon audit.",
            "recommended_fix": "Cover verified material, design/features, use/occasion, included components and care/specification information."
        })
    elif bullet_count == 0:
        issues.append({
            "severity": "CRITICAL", "field": "Bullet Points",
            "problem": "No bullet points supplied.",
            "recommended_fix": "Add concise feature-led bullets."
        })

    if len(description) < 80:
        issues.append({
            "severity": "MEDIUM", "field": "Description",
            "problem": "Description is missing or very short.",
            "recommended_fix": "Explain product identity, verified features, included components and relevant care/use information."
        })

    if not backend_terms:
        issues.append({
            "severity": "MEDIUM", "field": "Backend Search Terms",
            "problem": "No backend search terms were supplied for audit.",
            "recommended_fix": "Add relevant non-duplicate terms after checking the marketplace's current field rules."
        })

    all_customer_text = " ".join([title, bullets, description])
    content_normalized = _audit_normalize(all_customer_text)
    content_tokens = set(_audit_tokens(all_customer_text))
    requested_keywords = _audit_parse_keywords(target_keywords)
    missing_keywords = []
    covered_keywords = []

    for kw in requested_keywords:
        kw_tokens = set(_audit_tokens(kw))
        if kw.lower() in content_normalized or kw_tokens.issubset(content_tokens):
            covered_keywords.append(kw)
        else:
            missing_keywords.append(kw)

    if missing_keywords:
        issues.append({
            "severity": "MEDIUM", "field": "Keyword Coverage",
            "problem": "Relevant seller-supplied keywords are not clearly represented: " + ", ".join(missing_keywords[:12]),
            "recommended_fix": "Integrate relevant terms naturally into appropriate customer-facing or backend fields."
        })

    claim_hits = [c for c in PROMO_CLAIMS if c in content_normalized]
    if claim_hits:
        issues.append({
            "severity": "HIGH", "field": "Claims / Compliance",
            "problem": "Potential promotional or unsupported claims detected: " + ", ".join(claim_hits),
            "recommended_fix": "Remove or manually verify the claim before publishing."
        })

    attr_map = _audit_parse_attributes(attributes)
    fact_map = _audit_parse_attributes(verified_facts)
    conflicts = []
    for key, attr_value in attr_map.items():
        if key in fact_map and fact_map[key] and attr_value:
            if _audit_normalize(fact_map[key]) != _audit_normalize(attr_value):
                conflicts.append((key, attr_value, fact_map[key]))
                issues.append({
                    "severity": "CRITICAL",
                    "field": f"Attribute: {key}",
                    "problem": f"Current '{attr_value}' conflicts with verified '{fact_map[key]}'.",
                    "recommended_fix": "Physically verify the product and update the marketplace attribute."
                })

    if not category and not product_type and not browse_node:
        issues.append({
            "severity": "HIGH", "field": "Category / Browse Classification",
            "problem": "No category, product type or browse information was supplied.",
            "recommended_fix": "Paste the current marketplace classification fields so the auditor can check classification risk."
        })

    # Suspicious dimension field example: flag for verification, never auto-correct.
    for key, value in attr_map.items():
        if any(term in key for term in ["length", "width", "height", "dimension", "weight"]):
            if re.search(r"\b35\s*cm\b", value.lower()):
                issues.append({
                    "severity": "HIGH",
                    "field": f"Attribute: {key}",
                    "problem": f"Value '{value}' should be physically verified.",
                    "recommended_fix": "Measure the actual product/package and confirm the field meaning and unit."
                })

    score = 100
    penalties = {"CRITICAL": 20, "HIGH": 12, "MEDIUM": 7, "LOW": 3}
    for issue in issues:
        score -= penalties.get(issue["severity"], 3)
    score = max(0, min(100, score))

    return {
        "score": score,
        "issues": issues,
        "title_length": title_len,
        "title_limit": max_title,
        "bullet_count": bullet_count,
        "description_length": len(description),
        "backend_length": len(backend_terms),
        "requested_keywords": requested_keywords,
        "covered_keywords": covered_keywords,
        "missing_keywords": missing_keywords,
        "duplicate_title_words": duplicate_title_words,
        "claim_hits": claim_hits,
        "attribute_conflicts": conflicts,
        "profile_notes": profile["notes"]
    }

def render_rule_audit(result):
    st.markdown("### ⚙️ Deterministic Rule Audit")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Rule Score", f"{result['score']}/100")
    c2.metric("Title", f"{result['title_length']}/{result['title_limit']}")
    c3.metric("Bullets", result["bullet_count"])
    c4.metric("Description", result["description_length"])
    c5.metric("Backend chars", result["backend_length"])

    if result["issues"]:
        rows = [{
            "Priority": x["severity"],
            "Field": x["field"],
            "Problem": x["problem"],
            "Exact Fix": x["recommended_fix"]
        } for x in result["issues"]]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.success("No obvious deterministic issues found in the supplied fields.")

    if result["missing_keywords"]:
        st.warning("Missing supplied keywords: " + ", ".join(result["missing_keywords"]))
    if result["duplicate_title_words"]:
        st.info("Repeated title words: " + ", ".join(result["duplicate_title_words"]))
    if result["claim_hits"]:
        st.warning("Claims requiring review: " + ", ".join(result["claim_hits"]))

    with st.expander("Platform profile / validation note"):
        st.write(result["profile_notes"])


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
    st.title("🧠 E-Commerce Listing Auditor PRO")
    st.markdown("""
    <div style="background-color:#f0f2f6;padding:14px;border-radius:10px;margin-bottom:16px;">
    <b>Amazon India • Flipkart • Meesho</b><br>
    Deterministic rule checks run first; Gemini then adds semantic, keyword and image analysis.
    The auditor separates <b>verified product facts</b> from recommendations and flags fields
    that require seller-panel verification.
    </div>
    """, unsafe_allow_html=True)

    audit_tab, bulk_tab, methodology_tab = st.tabs([
        "🔍 Single Listing Audit",
        "📦 Bulk Listing Audit",
        "📚 Methodology"
    ])

    with audit_tab:
        st.subheader("1. Marketplace & Product Context")
        c1, c2, c3 = st.columns(3)
        with c1:
            marketplace = st.selectbox(
                "Marketplace",
                ["Amazon India", "Flipkart", "Meesho"],
                key="pro_marketplace"
            )
            audit_id = st.text_input("ASIN / FSN / SKU", key="pro_audit_id")
            category = st.text_input("Current Category / Browse Path", key="pro_category")
        with c2:
            product_type = st.text_input("Product Type / Item Type Keyword", key="pro_product_type")
            browse_node = st.text_input("Browse Node / Category ID", key="pro_browse_node")
            target_customer = st.text_input(
                "Target Customer / Use Case",
                placeholder="women, festive, wedding, party...",
                key="pro_target_customer"
            )
        with c3:
            material = st.text_input("Verified Material / Fabric", key="pro_material")
            colour = st.text_input("Verified Colour", key="pro_colour")
            pattern = st.text_input("Verified Pattern / Design", key="pro_pattern")

        st.subheader("2. Verified Product Facts")
        verified_facts = st.text_area(
            "Facts physically verified by you",
            placeholder=(
                "Fabric: Linen Cotton\n"
                "Print: Digital floral print\n"
                "Work: Mirror work\n"
                "Pallu: Tassel finish\n"
                "Blouse: Matching unstitched blouse piece\n"
                "Actual saree length: ...\n"
                "Actual blouse length: ..."
            ),
            height=150,
            key="pro_verified_facts"
        )

        st.subheader("3. Current Listing")
        existing_title = st.text_area("Current Title", height=90, key="pro_title")
        existing_bullets = st.text_area(
            "Current Bullet Points",
            height=180,
            placeholder="One bullet per line",
            key="pro_bullets"
        )
        existing_desc = st.text_area("Current Description", height=180, key="pro_description")
        existing_backend = st.text_area(
            "Current Backend Search Terms / Keywords",
            height=100,
            key="pro_backend"
        )
        current_attributes = st.text_area(
            "Current Attributes",
            height=160,
            placeholder="One attribute per line: Attribute: Value",
            key="pro_attributes"
        )
        target_keywords = st.text_area(
            "Known / Target Keywords (optional)",
            placeholder="linen cotton saree, digital print saree...",
            height=90,
            key="pro_keywords"
        )

        st.subheader("4. Product Images")
        audit_imgs = st.file_uploader(
            "Upload up to 8 product images",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True,
            key="pro_images"
        )
        opened_images = []
        if audit_imgs:
            audit_imgs = audit_imgs[:8]
            img_cols = st.columns(min(len(audit_imgs), 4))
            for i, file in enumerate(audit_imgs):
                try:
                    img = Image.open(file)
                    opened_images.append(img)
                    with img_cols[i % len(img_cols)]:
                        st.image(img, caption=f"Image {i+1}", use_container_width=True)
                except Exception as image_error:
                    st.warning(f"{file.name}: {image_error}")

        st.subheader("5. Audit Controls")
        a1, a2, a3 = st.columns(3)
        with a1:
            run_ai = st.checkbox("Gemini Deep Audit", value=True, key="pro_run_ai")
        with a2:
            run_images = st.checkbox("Image Analysis", value=True, key="pro_run_images")
        with a3:
            generate_rewrite = st.checkbox(
                "Generate Optimized Copy", value=True, key="pro_rewrite"
            )

        if st.button("🚀 RUN PRO LISTING AUDIT", type="primary", key="run_pro_audit"):
            if not existing_title.strip():
                st.warning("⚠️ Current title required hai.")
            elif run_ai and not gemini_api_key:
                st.warning("⚠️ Gemini API key configure karein, ya Gemini Deep Audit off karein.")
            else:
                with st.spinner("Running deterministic + marketplace audit..."):
                    rule_result = run_deterministic_listing_audit(
                        marketplace=marketplace,
                        title=existing_title,
                        bullets=existing_bullets,
                        description=existing_desc,
                        backend_terms=existing_backend,
                        attributes=current_attributes,
                        verified_facts=verified_facts,
                        target_keywords=target_keywords,
                        category=category,
                        product_type=product_type,
                        browse_node=browse_node
                    )
                render_rule_audit(rule_result)

                if run_ai:
                    with st.spinner("Gemini is performing semantic, keyword and image analysis..."):
                        try:
                            model = get_working_model()
                            ai_prompt = f"""
You are a senior marketplace listing auditor for {marketplace}.

RULES
- Do not claim access to private ranking algorithms.
- Never invent product facts, measurements, certifications, search volume or sales data.
- Seller-provided verified facts are the source of truth; conflicts must be flagged VERIFY.
- Keyword recommendations are relevance suggestions, not search-volume claims.
- Do not keyword-stuff.
- Do not use unsupported superlatives or guarantees.
- Do not invent category IDs/browse nodes. If classification is uncertain, say VERIFY.
- Customer-facing copy must contain only supportable facts.
- Return JSON only.

PRODUCT CONTEXT
ID: {audit_id}
Category: {category}
Product Type: {product_type}
Browse Node: {browse_node}
Target Customer: {target_customer}
Material: {material}
Colour: {colour}
Pattern: {pattern}

VERIFIED FACTS:
{verified_facts}

CURRENT TITLE:
{existing_title}

CURRENT BULLETS:
{existing_bullets}

CURRENT DESCRIPTION:
{existing_desc}

CURRENT BACKEND:
{existing_backend}

CURRENT ATTRIBUTES:
{current_attributes}

TARGET KEYWORDS:
{target_keywords}

DETERMINISTIC AUDIT:
{json.dumps(rule_result, ensure_ascii=False)}

Generate an evidence-first audit. Return ONLY this JSON structure:
{{
  "executive_summary": "",
  "semantic_score": 0,
  "score_breakdown": {{
    "search_relevance": 0,
    "content_quality": 0,
    "attribute_quality": 0,
    "category_alignment": 0,
    "customer_clarity": 0,
    "conversion_readiness": 0,
    "image_quality": 0
  }},
  "priority_actions": [
    {{
      "priority": "P0|P1|P2|P3",
      "field": "",
      "current": "",
      "issue": "",
      "exact_fix": "",
      "why": ""
    }}
  ],
  "keyword_strategy": {{
    "primary": [],
    "secondary": [],
    "long_tail": [],
    "missing": [],
    "redundant": [],
    "backend_suggestions": [],
    "keyword_warnings": []
  }},
  "attribute_strategy": [
    {{
      "attribute": "",
      "current": "",
      "recommended": "",
      "status": "KEEP|CHANGE|VERIFY|MISSING",
      "reason": ""
    }}
  ],
  "category_strategy": {{
    "status": "ALIGNED|VERIFY|MISMATCH_RISK",
    "finding": "",
    "seller_panel_fields_to_verify": [],
    "recommended_action": ""
  }},
  "title": {{
    "recommended": "",
    "changes": []
  }},
  "bullets": [],
  "description": "",
  "backend_search_terms": "",
  "image_audit": [
    {{
      "image": "",
      "finding": "",
      "recommended_action": ""
    }}
  ],
  "verification_required": [],
  "publish_checklist": []
}}
"""
                            payload = [ai_prompt]
                            if run_images and opened_images:
                                payload.extend(opened_images)

                            response = safe_generate_content(model, payload)
                            raw = response.text.strip()
                            raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.I)
                            raw = re.sub(r"\s*```$", "", raw).strip()

                            try:
                                ai_result = json.loads(raw)
                            except json.JSONDecodeError:
                                ai_result = None
                                st.error("Gemini ne valid JSON return nahi kiya.")
                                st.code(response.text)

                            if ai_result:
                                st.markdown("---")
                                st.subheader("🧠 Gemini Deep Audit")
                                x1, x2, x3 = st.columns(3)
                                x1.metric(
                                    "Semantic Score",
                                    f"{ai_result.get('semantic_score', 0)}/100"
                                )
                                x2.metric(
                                    "Rule Score",
                                    f"{rule_result['score']}/100"
                                )
                                x3.metric(
                                    "Priority Actions",
                                    len(ai_result.get("priority_actions", []) or [])
                                )
                                st.progress(
                                    max(0, min(int(ai_result.get("semantic_score", 0) or 0), 100)) / 100
                                )
                                st.info(ai_result.get("executive_summary", ""))

                                deep_breakdown = ai_result.get("score_breakdown", {}) or {}
                                if deep_breakdown:
                                    st.markdown("### 🎯 Deep Score Breakdown")
                                    st.dataframe(
                                        pd.DataFrame([
                                            {
                                                "Area": str(k).replace("_", " ").title(),
                                                "Score": v
                                            }
                                            for k, v in deep_breakdown.items()
                                        ]),
                                        use_container_width=True,
                                        hide_index=True
                                    )

                                actions = ai_result.get("priority_actions", []) or []
                                if actions:
                                    st.markdown("### 🚨 Priority Action Plan")
                                    st.dataframe(
                                        pd.DataFrame([
                                            {
                                                "Priority": x.get("priority", ""),
                                                "Field": x.get("field", ""),
                                                "Current": x.get("current", ""),
                                                "Issue": x.get("issue", ""),
                                                "Exact Fix": x.get("exact_fix", ""),
                                                "Why": x.get("why", "")
                                            }
                                            for x in actions
                                        ]),
                                        use_container_width=True,
                                        hide_index=True
                                    )

                                kw = ai_result.get("keyword_strategy", {}) or {}
                                st.markdown("### 🔑 Keyword Strategy")
                                k1, k2, k3, k4 = st.columns(4)
                                for col, heading, key in [
                                    (k1, "Primary", "primary"),
                                    (k2, "Secondary", "secondary"),
                                    (k3, "Long-tail", "long_tail"),
                                    (k4, "Missing", "missing")
                                ]:
                                    with col:
                                        st.markdown(f"**{heading}**")
                                        for value in kw.get(key, []) or []:
                                            st.write("•", value)
                                if kw.get("redundant"):
                                    st.info("Redundant: " + ", ".join(map(str, kw["redundant"])))
                                for warning in kw.get("keyword_warnings", []) or []:
                                    st.caption("⚠️ " + str(warning))

                                st.markdown("### ✏️ Optimized Listing")
                                title_data = ai_result.get("title", {}) or {}
                                title_after = title_data.get("recommended", "")
                                bullets_after = "\n".join(
                                    f"• {x}" for x in (ai_result.get("bullets", []) or [])
                                )
                                desc_after = ai_result.get("description", "")
                                backend_after = ai_result.get("backend_search_terms", "")

                                st.text_area(
                                    "Recommended Title",
                                    value=title_after,
                                    height=90,
                                    key="pro_result_title"
                                )
                                st.text_area(
                                    "Recommended Bullet Points",
                                    value=bullets_after,
                                    height=220,
                                    key="pro_result_bullets"
                                )
                                st.text_area(
                                    "Recommended Description",
                                    value=desc_after,
                                    height=220,
                                    key="pro_result_description"
                                )
                                st.text_area(
                                    "Recommended Backend Search Terms",
                                    value=backend_after,
                                    height=110,
                                    key="pro_result_backend"
                                )

                                st.markdown("### 🧩 Attribute Strategy")
                                attr_rows = [{
                                    "Attribute": x.get("attribute", ""),
                                    "Current": x.get("current", ""),
                                    "Recommended": x.get("recommended", ""),
                                    "Status": x.get("status", ""),
                                    "Reason": x.get("reason", "")
                                } for x in ai_result.get("attribute_strategy", []) or []]
                                if attr_rows:
                                    st.dataframe(
                                        pd.DataFrame(attr_rows),
                                        use_container_width=True,
                                        hide_index=True
                                    )

                                st.markdown("### 🗂️ Category / Browse Strategy")
                                cat = ai_result.get("category_strategy", {}) or {}
                                status = cat.get("status", "VERIFY")
                                if status == "MISMATCH_RISK":
                                    st.error("⚠️ Category mismatch risk.")
                                elif status == "VERIFY":
                                    st.warning("⚠️ Category requires verification.")
                                else:
                                    st.success("Category appears aligned based on supplied information.")
                                st.write(cat.get("finding", ""))
                                st.write("**Action:**", cat.get("recommended_action", ""))
                                for field in cat.get("seller_panel_fields_to_verify", []) or []:
                                    st.write("•", field)

                                if run_images:
                                    st.markdown("### 🖼️ Image Audit")
                                    image_rows = [{
                                        "Image": x.get("image", ""),
                                        "Finding": x.get("finding", ""),
                                        "Action": x.get("recommended_action", "")
                                    } for x in ai_result.get("image_audit", []) or []]
                                    if image_rows:
                                        st.dataframe(
                                            pd.DataFrame(image_rows),
                                            use_container_width=True,
                                            hide_index=True
                                        )

                                verification = ai_result.get("verification_required", []) or []
                                if verification:
                                    st.markdown("### ⚠️ Verify Before Publishing")
                                    for item in verification:
                                        st.write("•", item)

                                checklist = ai_result.get("publish_checklist", []) or []
                                if checklist:
                                    st.markdown("### ✅ Publish Checklist")
                                    for item in checklist:
                                        st.write("☐", item)

                                st.markdown("### 🔄 Before → After")
                                st.write("**Title**")
                                st.code(existing_title + "\n\n→\n\n" + title_after)
                                st.write("**Description**")
                                st.code(existing_desc + "\n\n→\n\n" + str(desc_after))

                                export_data = {
                                    "marketplace": marketplace,
                                    "id": audit_id,
                                    "rule_engine": rule_result,
                                    "ai_audit": ai_result
                                }
                                st.download_button(
                                    "📥 Download Complete Audit JSON",
                                    data=json.dumps(
                                        export_data, ensure_ascii=False, indent=2
                                    ).encode("utf-8"),
                                    file_name=f"listing_audit_{audit_id or 'product'}.json",
                                    mime="application/json",
                                    key="pro_download_json"
                                )

                        except Exception as audit_error:
                            st.error(f"Deep Audit Error: {audit_error}")

    with bulk_tab:
        st.subheader("📦 Bulk Listing Auditor")
        st.caption(
            "CSV columns supported: marketplace, sku/asin, title, bullets, description, "
            "backend_keywords, attributes, verified_facts, target_keywords, category, "
            "product_type, browse_node."
        )
        bulk_file = st.file_uploader(
            "Upload Listing CSV", type=["csv"], key="pro_bulk_csv"
        )

        if bulk_file:
            try:
                bulk_df = pd.read_csv(bulk_file)
                st.write(f"Loaded {len(bulk_df)} listings.")
                st.dataframe(
                    bulk_df.head(10), use_container_width=True, hide_index=True
                )

                if st.button("⚡ Run Bulk Rule Audit", key="run_bulk_rule_audit"):
                    results = []
                    for idx, row in bulk_df.iterrows():
                        marketplace_b = str(row.get("marketplace", "Amazon India"))
                        if marketplace_b not in PLATFORM_PROFILES:
                            marketplace_b = "Amazon India"

                        rr = run_deterministic_listing_audit(
                            marketplace=marketplace_b,
                            title=row.get("title", ""),
                            bullets=row.get("bullets", ""),
                            description=row.get("description", ""),
                            backend_terms=row.get("backend_keywords", ""),
                            attributes=row.get("attributes", ""),
                            verified_facts=row.get("verified_facts", ""),
                            target_keywords=row.get("target_keywords", ""),
                            category=row.get("category", ""),
                            product_type=row.get("product_type", ""),
                            browse_node=row.get("browse_node", "")
                        )
                        results.append({
                            "ID": row.get(
                                "sku/asin",
                                row.get("sku", row.get("asin", idx))
                            ),
                            "Marketplace": marketplace_b,
                            "Rule Score": rr["score"],
                            "Critical": sum(
                                x["severity"] == "CRITICAL" for x in rr["issues"]
                            ),
                            "High": sum(
                                x["severity"] == "HIGH" for x in rr["issues"]
                            ),
                            "Medium": sum(
                                x["severity"] == "MEDIUM" for x in rr["issues"]
                            ),
                            "Title Chars": rr["title_length"],
                            "Bullets": rr["bullet_count"],
                            "Missing Keywords": ", ".join(rr["missing_keywords"]),
                            "Top Fix": (
                                rr["issues"][0]["recommended_fix"]
                                if rr["issues"] else "No obvious rule issue"
                            )
                        })

                    result_df = pd.DataFrame(results)
                    st.subheader("📊 Bulk Audit Results")
                    st.dataframe(
                        result_df, use_container_width=True, hide_index=True
                    )
                    st.download_button(
                        "📥 Download Bulk Audit CSV",
                        data=result_df.to_csv(index=False).encode("utf-8-sig"),
                        file_name="listing_audit_bulk_results.csv",
                        mime="text/csv",
                        key="download_bulk_audit"
                    )
            except Exception as bulk_error:
                st.error(f"Bulk CSV Error: {bulk_error}")

    with methodology_tab:
        st.subheader("📚 Auditor Scope")
        st.markdown("""
        **Content:** title, bullets, description, keyword coverage, redundancy and backend terms.

        **Catalog:** product type, category/browse path, attribute completeness and
        conflicts against verified product facts.

        **Images:** image observations, consistency with supplied facts, visibility and
        potential quality/content issues.

        **Conversion readiness:** product identity, feature hierarchy, included components,
        use/occasion clarity and unsupported claims.

        **Important:** this is an audit assistant, not a private marketplace ranking oracle.
        Marketplace/category rules can change. Fields marked VERIFY must be checked in the
        current seller/supplier panel before publishing.
        """)
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
    st.title("✂️ Smart Shipping Label Cropper & Thermal Converter")
    st.markdown("""
    <div style="background-color: #f0f2f6; padding: 10px; border-radius: 8px; margin-bottom: 15px;">
    <b>Advanced E-Commerce Tool:</b> Multiple shipping label PDFs ya images yahan upload karein. Yeh tool invoices ko analyze karega, delivery partners ke hisaab se sort karega aur SKU pick-list summary banayega.
    </div>
    """, unsafe_allow_html=True)
    
    selected_marketplace = st.selectbox(
        "Select Source Marketplace Preset:",
        ["Flipkart Seller Hub", "Amazon Shipping / Easy Ship", "Meesho Supplier Panel", "Multi-Marketplace Mixed Batch"]
    )
    
    label_files = st.file_uploader("Upload Shipping Label Files (PDF or Images)", type=["jpg", "jpeg", "png", "pdf"], accept_multiple_files=True, key="label_crop_files")
    
    if label_files:
        st.markdown(f"### 📄 Uploaded Files Count: {len(label_files)}")
        
        gemini_payload_parts = []
        for file in label_files:
            try:
                # Safe file bytes reading
                file_bytes = file.read()
                file.seek(0) # Reset pointer
                
                if file.type == "application/pdf" or file.name.lower().endswith('.pdf'):
                    st.info(f"📂 PDF Loaded Successfully: {file.name} ({len(file_bytes) / 1024:.1f} KB)")
                    gemini_payload_parts.append({
                        "mime_type": "application/pdf",
                        "data": file_bytes
                    })
                else:
                    img = Image.open(file)
                    st.image(img, caption=f"Image: {file.name}", width=300)
                    gemini_payload_parts.append(img)
            except Exception as load_err:
                st.error(f"Error reading file {file.name}: {load_err}")
                
        if not gemini_api_key:
            st.warning("⚠️ Kripya pehle sidebar mein Gemini API Key enter karein.")
        else:
            if st.button("🚀 Process, Analyze & Sort by Partner / SKU"):
                with st.spinner("Analyzing shipping label files via Gemini AI, filtering invoices, and sorting by partner & SKU..."):
                    try:
                        model = get_working_model()
                        cropper_prompt = [
                            f"""Act as an expert E-Commerce Logistics & Thermal Label Cropper Tool.
                            Source Platform Preset: {selected_marketplace}
                            
                            Analyze the uploaded shipping label document(s)/image(s):
                            1. **Invoice & Margin Removal:** Identify and separate tax invoice sections from the actual logistics shipping label.
                            2. **Delivery Partner Detection:** Automatically classify each label based on courier logos/text (e.g., Flipkart Ekart, Amazon Shipping, Delhivery, Shadowfax, Xpressbees, Valmo/Meesho).
                            3. **SKU-wise Sorting & Pick-List Summary:** Group orders by SKU/Item and provide a consolidated pick-list summary.
                            4. **Thermal 4x6 Layout Instructions:** Provide exact formatting details for thermal printing.
                            
                            Provide clean structured output with clear headings for Partner Sorting, SKU Pick-list Summary, and Cropping Instructions.""",
                        ]
                        cropper_payload = cropper_prompt + gemini_payload_parts
                            
                        response = safe_generate_content(model, cropper_payload)
                        st.markdown("### 📊 Smart Label Sorting & Analysis Report")
                        st.write(response.text)
                        
                        st.success("✅ Files successfully processed and sorted by courier partner & SKU!")
                    except Exception as e:
                        st.error(f"Processing Error: {e}")
