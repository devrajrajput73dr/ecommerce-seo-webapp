
import io
import copy
import json
import math
import os
import re
import time
from pathlib import Path

import pandas as pd
import streamlit as st
from PIL import Image, ImageOps, ImageDraw

try:
    import google.generativeai as genai
except Exception:
    genai = None

try:
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import RectangleObject
except Exception:
    PdfReader = PdfWriter = RectangleObject = None

st.set_page_config(
    page_title="Pure Vastra Seller Intelligence Suite V4",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# MARKETPLACE PROFILES
# ============================================================
MARKETPLACE = {
    "Amazon India": {
        "title_max": 75,
        "highlight_max": 125,
        "note": "Current Amazon India guidance: most non-media categories use <=75 characters for Item Name; Item Highlights provide up to 125 additional characters.",
    },
    "Flipkart": {
        "title_max": 200,
        "highlight_max": 0,
        "note": "Use the current Seller Hub/category template as the final authority because field requirements can vary.",
    },
    "Meesho": {
        "title_max": 150,
        "highlight_max": 0,
        "note": "Use the current Supplier Panel/category template as the final authority because catalog requirements can vary.",
    },
}

DEFAULT_FEES = {
    "Amazon India": {"referral_pct": 15.0, "closing": 0.0},
    "Flipkart": {"referral_pct": 12.0, "closing": 0.0},
    "Meesho": {"referral_pct": 8.0, "closing": 0.0},
}

UNSUPPORTED_CLAIMS = [
    "best", "no.1", "number 1", "guaranteed", "100% guaranteed",
    "cheapest", "lowest price", "best seller", "perfect",
    "premium quality", "luxury", "skin friendly", "money back",
]

# ============================================================
# COMMON HELPERS
# ============================================================
def s(v):
    if v is None:
        return ""
    try:
        if pd.isna(v):
            return ""
    except Exception:
        pass
    return str(v).strip()

def norm(v):
    return re.sub(r"\s+", " ", s(v)).strip()

def tokens(v):
    return re.findall(r"[a-z0-9]+", s(v).lower())

def bullets(v):
    raw = s(v)
    if not raw:
        return []
    parts = re.split(r"\n+|(?:^|\n)\s*[-•*]\s+", raw)
    return [norm(re.sub(r"^[\-\•\*\d\.\)\s]+", "", x)) for x in parts if norm(x)]

def repeated_words(v, minimum=3):
    c = {}
    for x in tokens(v):
        c[x] = c.get(x, 0) + 1
    return {k: n for k, n in c.items() if n >= minimum and len(k) > 2}

def parse_lines(v):
    out = {}
    for line in s(v).splitlines():
        if ":" in line:
            k, val = line.split(":", 1)
            out[norm(k).lower()] = norm(val)
    return out

def safe_json(text):
    text = s(text)
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S | re.I)
    text = m.group(1) if m else text
    a, b = text.find("{"), text.rfind("}")
    if a >= 0 and b > a:
        try:
            return json.loads(text[a:b+1])
        except Exception:
            pass
    return None

def api_key():
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass
    return st.session_state.get("gemini_key")

def model():
    key = api_key()
    if not key or genai is None:
        return None
    genai.configure(api_key=key)
    return genai.GenerativeModel("gemini-2.5-flash")

def ai_generate(contents, retries=3):
    m = model()
    if not m:
        raise RuntimeError("Gemini API key configure karein.")
    last = None
    for i in range(retries):
        try:
            return m.generate_content(contents)
        except Exception as e:
            last = e
            if ("429" in str(e) or "quota" in str(e).lower()) and i < retries - 1:
                time.sleep(5 * (i + 1))
            else:
                raise
    raise last

def image_list(files):
    result = []
    for f in files or []:
        try:
            f.seek(0)
            result.append(Image.open(f).convert("RGB"))
            f.seek(0)
        except Exception:
            pass
    return result

# ============================================================
# DETERMINISTIC AUDIT
# ============================================================
def audit_listing(marketplace, title, highlights="", bullets_text="", description="",
                  backend="", attributes="", facts="", target_keywords="",
                  category="", product_type="", browse_node=""):
    p = MARKETPLACE[marketplace]
    score = 100
    critical, warnings, passed = [], [], []

    title = norm(title)
    highlights = norm(highlights)
    b = bullets(bullets_text)
    desc = norm(description)
    combined = " ".join([title, highlights, bullets_text, desc, backend]).lower()

    if not title:
        critical.append(("P0", "Title missing", "Add a factual title."))
        score -= 25
    elif len(title) > p["title_max"]:
        critical.append(("P0", "Title over limit", f"{len(title)} chars; target <= {p['title_max']}."))
        score -= 20
    else:
        passed.append(f"Title length OK: {len(title)}/{p['title_max']}")

    rep = repeated_words(title)
    if rep:
        warnings.append(("P1", "Repeated title terms", ", ".join(rep.keys())))
        score -= min(10, len(rep) * 2)

    if marketplace == "Amazon India":
        if highlights and len(highlights) <= 125:
            passed.append(f"Item Highlights OK: {len(highlights)}/125")
        elif highlights:
            warnings.append(("P1", "Item Highlights over limit", f"{len(highlights)} chars; target <=125."))
            score -= 8
        else:
            warnings.append(("P1", "Item Highlights missing", "Add verified material/use-case information where appropriate."))
            score -= 4

    if len(b) >= 5:
        passed.append(f"{len(b)} bullet lines detected")
    elif b:
        warnings.append(("P1", "Few bullet lines", f"Only {len(b)} detected."))
        score -= 7
    else:
        critical.append(("P0", "Bullets/highlights missing", "Add factual product benefits and specifications."))
        score -= 15

    if len(desc) >= 80:
        passed.append("Description has useful content")
    elif desc:
        warnings.append(("P2", "Description short", "Expand with verified product facts."))
        score -= 4
    else:
        critical.append(("P1", "Description missing", "Add a factual description."))
        score -= 8

    if marketplace == "Amazon India" and not norm(backend):
        warnings.append(("P2", "Backend/search terms missing", "Add relevant non-duplicative terms if the field is available."))
        score -= 4

    kws = [norm(x) for x in re.split(r"[,;\n]+", s(target_keywords)) if norm(x)]
    missing = [k for k in kws if k.lower() not in combined]
    if missing:
        warnings.append(("P1", "Target keyword gaps", ", ".join(missing[:15])))
        score -= min(12, len(missing) * 2)

    hits = sorted(set(x for x in UNSUPPORTED_CLAIMS if x in combined))
    if hits:
        warnings.append(("P1", "Potential unsupported/promotional claims", ", ".join(hits)))
        score -= min(12, len(hits) * 2)

    fact_map = parse_lines(facts)
    attr_map = parse_lines(attributes)
    conflicts = []
    for k, v in attr_map.items():
        if k in fact_map and v and fact_map[k] and v.lower() != fact_map[k].lower():
            conflicts.append(f"{k}: attribute='{v}' vs verified='{fact_map[k]}'")
    if conflicts:
        critical.append(("P0", "Attribute conflicts", " | ".join(conflicts[:8])))
        score -= min(20, 5 * len(conflicts))

    if not category:
        warnings.append(("P2", "Category not supplied", "Verify category in the current marketplace panel."))
        score -= 2
    if not product_type:
        warnings.append(("P2", "Product type missing", "Verify the exact catalog/product type."))
        score -= 2
    if marketplace == "Amazon India" and not browse_node:
        warnings.append(("P2", "Browse node not supplied", "Verify current browse placement; never invent IDs."))
        score -= 2

    if re.search(r"\bitem length\s*[:=-]?\s*35\s*cm\b", (attributes + " " + facts).lower()):
        warnings.append(("P1", "Dimension needs manual verification", "Verify 35 cm is the actual product measurement, not package data."))
        score -= 5

    score = max(0, min(100, int(score)))
    status = "READY" if score >= 90 and not critical else ("REVIEW" if score >= 70 else "FIX BEFORE PUBLISH")
    return {
        "score": score, "status": status, "critical": critical,
        "warnings": warnings, "passed": passed, "missing_keywords": missing
    }

# ============================================================
# MULTI-LISTING VARIANT ENGINE
# ============================================================
def make_variant_prompt(marketplace, base_name, facts, category, product_type,
                        target_keywords, count, strategies, current_content=""):
    p = MARKETPLACE[marketplace]
    strategy_text = "\n".join(f"{i+1}. {x}" for i, x in enumerate(strategies))
    return f"""
Create {count} DIFFERENT DRAFT LISTING VARIANTS for the SAME physical product on {marketplace}.

This is a content-variation generator, NOT permission to create duplicate marketplace catalogs.
Keep the physical product identity locked.

LOCKED FACTS — DO NOT CHANGE:
{facts}

Base product name:
{base_name}

Category:
{category}

Product type:
{product_type}

Target keywords:
{target_keywords}

Variation strategies:
{strategy_text}

Rules:
- Never invent material, color, measurements, certifications, warranty, quality grade or features.
- Never change locked facts between variants.
- Do not use keyword stuffing.
- Do not use unsupported superlatives.
- Do not claim access to private ranking algorithms.
- Avoid near-duplicate wording.
- Every variant must be genuinely different in wording/angle while remaining factually identical.
- For Amazon India: Item Name <= {p['title_max']} characters and Item Highlights <= {p['highlight_max']} characters.
- Use the most important product facts in the title; distribute additional verified details into Item Highlights where available.
- Return JSON only.

JSON:
{{
 "variants":[
   {{
    "variant_no":1,
    "angle":"...",
    "title":"...",
    "item_highlights":"...",
    "bullets":["...","...","...","...","..."],
    "description":"...",
    "backend_keywords":"...",
    "keyword_focus":["..."],
    "locked_facts_check":"PASS"
   }}
 ]
}}
"""

def local_similarity(a, b):
    A, B = set(tokens(a)), set(tokens(b))
    if not A or not B:
        return 0.0
    return round(100 * len(A & B) / len(A | B), 1)

def variant_quality(variants, marketplace):
    rows = []
    seen = []
    for v in variants:
        title = s(v.get("title"))
        sim = max([local_similarity(title, x) for x in seen], default=0)
        audit = audit_listing(
            marketplace, title, v.get("item_highlights",""),
            "\n".join(v.get("bullets",[]) if isinstance(v.get("bullets"), list) else bullets(v.get("bullets",""))),
            v.get("description",""), v.get("backend_keywords","")
        )
        rows.append({
            "Variant": v.get("variant_no"),
            "Angle": s(v.get("angle")),
            "Title": title,
            "Title chars": len(title),
            "Similarity vs prior title %": sim,
            "Audit score": audit["score"],
            "Status": audit["status"],
        })
        seen.append(title)
    return pd.DataFrame(rows)

# ============================================================
# BUSINESS REPORT HEALTH ENGINE
# ============================================================
def business_health(df):
    """Normalize Amazon Business Report exports without creating duplicate columns.

    Amazon exports can contain slightly different headers, and renaming several
    source columns to the same canonical name creates duplicate pandas columns.
    This function instead selects one source column per metric and builds a clean
    output dataframe.
    """
    if df is None or df.empty:
        return pd.DataFrame()

    src = df.copy()
    columns = list(src.columns)

    def find_col(kind):
        for c in columns:
            lc = s(c).lower().strip()
            if kind == "asin" and (lc == "asin" or "asin" in lc):
                return c
            if kind == "sku" and (lc == "sku" or lc.endswith("sku")):
                return c
            if kind == "title" and "title" in lc:
                return c
            if kind == "sessions" and "session" in lc and "percentage" not in lc and "unit session" not in lc:
                return c
            if kind == "orders" and ("units ordered" in lc or lc == "units ordered"):
                return c
            if kind == "conversion" and ("unit session percentage" in lc or "unit session %" in lc):
                return c
            if kind == "sales" and ("ordered product sales" in lc or lc == "sales" or "product sales" in lc):
                return c
        return None

    out = pd.DataFrame(index=src.index)
    mapping = {
        "ASIN": find_col("asin"),
        "SKU": find_col("sku"),
        "Title": find_col("title"),
        "Sessions": find_col("sessions"),
        "Orders": find_col("orders"),
        "Conversion": find_col("conversion"),
        "Sales": find_col("sales"),
    }

    for target, source in mapping.items():
        if source is not None:
            # Always extract a Series by position/name from the original frame.
            value = src.loc[:, source]
            if isinstance(value, pd.DataFrame):
                value = value.iloc[:, 0]
            out[target] = value

    for c in ["Sessions", "Orders", "Sales"]:
        if c in out.columns:
            out[c] = pd.to_numeric(
                out[c].astype(str).str.replace(",", "", regex=False).str.replace("₹", "", regex=False).str.strip(),
                errors="coerce",
            ).fillna(0.0)

    if "Orders" not in out.columns:
        out["Orders"] = 0.0
    if "Sessions" not in out.columns:
        out["Sessions"] = 0.0
    if "Sales" not in out.columns:
        out["Sales"] = 0.0

    if "Conversion" in out.columns:
        out["Conversion"] = pd.to_numeric(
            out["Conversion"].astype(str).str.replace("%", "", regex=False).str.replace(",", "", regex=False).str.strip(),
            errors="coerce",
        )
    else:
        out["Conversion"] = pd.NA

    # Amazon may export conversion as a percentage. Fill missing values from orders/sessions.
    calculated = (out["Orders"] / out["Sessions"].replace(0, pd.NA) * 100)
    out["Conversion"] = out["Conversion"].fillna(calculated).fillna(0.0)

    out["Diagnosis"] = out.apply(
        lambda r: "NO/LOW TRAFFIC DATA" if r["Sessions"] < 20 and r["Orders"] == 0
        else ("TRAFFIC OK → CHECK CONVERSION" if r["Sessions"] >= 50 and r["Orders"] == 0
              else ("CONVERSION REVIEW" if r["Orders"] > 0 and r["Conversion"] < 1.0
                    else "NORMAL / MONITOR")),
        axis=1,
    )

    preferred = ["ASIN", "SKU", "Title", "Sessions", "Orders", "Conversion", "Sales", "Diagnosis"]
    return out[[c for c in preferred if c in out.columns]]

# ============================================================
# UI
# ============================================================
st.sidebar.title("🛍️ Pure Vastra Seller Suite V4")
st.sidebar.caption("New Listing • Multi-Listing • Bulk • Audit • Profit • Labels • Health")

st.sidebar.markdown("### Gemini AI")
key_input = st.sidebar.text_input("Gemini API Key", type="password", key="gemini_key_input")
if key_input:
    st.session_state.gemini_key = key_input
st.sidebar.caption("AI is optional for deterministic audits and calculators.")

mode = st.sidebar.radio(
    "Select Module",
    [
        "🆕 New Single Listing",
        "🔁 Multi-Listing Generator",
        "📦 Bulk Listing Builder",
        "🔍 Listing Auditor",
        "📊 Listing Health Center",
        "💰 Profit & Margin Calculator",
        "🧮 Price / Break-even Simulator",
        "🧾 PDF Label Cropper",
        "👗 AI Virtual Model Studio",
        "⚙️ Methodology & Templates",
    ],
)

# ============================================================
# NEW SINGLE LISTING
# ============================================================

# ============================================================
# MARKETPLACE BULK TEMPLATE HELPERS
# ============================================================
# Streamlit Cloud can run the script in an environment where __file__ is not
# available (for example, when the app is executed from a managed runner).
# Resolve assets without ever referencing an undefined __file__.
_TEMPLATE_SEARCH_DIRS = [
    os.path.join(os.getcwd(), "templates"),
    os.path.join(os.getcwd(), "template_assets"),
]

def _template_bytes(filename):
    for base_dir in _TEMPLATE_SEARCH_DIRS:
        p = os.path.join(base_dir, filename)
        if os.path.isfile(p):
            with open(p, "rb") as fh:
                return fh.read()
    return None

if mode == "🆕 New Single Listing":
    st.title("🆕 New Single Listing Builder")
    st.info("Verified-facts-first workflow. AI can rewrite content, but it cannot invent product specifications.")

    marketplace = st.selectbox("Marketplace", list(MARKETPLACE))
    c1, c2 = st.columns(2)
    with c1:
        product_name = st.text_input("Product / Base Name")
        category = st.text_input("Category / Browse Path")
        product_type = st.text_input("Product Type / Item Type Keyword")
        target_customer = st.text_input("Target Customer / Use Case")
    with c2:
        target_keywords = st.text_area("Target Keywords (comma separated)")
        facts = st.text_area("VERIFIED PRODUCT FACTS (one per line)", height=180,
                              placeholder="Fabric: Linen Cotton\nColour: Baby Pink\nPattern: Digital Floral Print\nWork: Mirror Work\nIncluded Components: Blouse Piece")
    imgs = st.file_uploader("Product Images (up to 6)", type=["jpg","jpeg","png"], accept_multiple_files=True, key="new_imgs")

    if imgs:
        imgs = imgs[:6]
        cols = st.columns(min(6, len(imgs)))
        for i, im in enumerate(imgs):
            with cols[i]:
                st.image(im, caption=f"Image {i+1}", use_container_width=True)

    if st.button("🚀 Generate New Listing", type="primary"):
        if not product_name or not facts:
            st.warning("Product name aur verified facts required hain.")
        else:
            with st.spinner("Generating marketplace-ready draft..."):
                data, err = None, None
                try:
                    data, err = generate = None, None
                    prompt = f"""
Create one new factual listing for {marketplace}. Return JSON only.
Product: {product_name}
Category: {category}
Product type: {product_type}
Target customer/use: {target_customer}
Verified facts:
{facts}
Target keywords: {target_keywords}
Rules: never invent facts, never claim ranking guarantees, avoid keyword stuffing and unsupported superlatives.
For Amazon India Item Name <=75 chars and Item Highlights <=125 chars.
JSON keys: title,item_highlights,bullets,description,backend_keywords,attribute_suggestions,verification_required,publish_checklist.
"""
                    payload = [prompt] + image_list(imgs)
                    resp = ai_generate(payload)
                    data = safe_json(resp.text)
                    if not data:
                        st.error("AI response JSON format mein nahi aaya. Raw response:")
                        st.write(resp.text)
                    else:
                        st.success("Draft generated. Publish se pehle verification required fields check karein.")
                        st.subheader("Title")
                        st.code(s(data.get("title")))
                        if marketplace == "Amazon India":
                            st.subheader("Item Highlights")
                            st.code(s(data.get("item_highlights")))
                        st.subheader("Bullets")
                        for x in data.get("bullets", []):
                            st.write("•", x)
                        st.subheader("Description")
                        st.write(s(data.get("description")))
                        st.subheader("Backend/Search Keywords")
                        st.code(s(data.get("backend_keywords")))
                        st.subheader("Verification Required")
                        st.write(data.get("verification_required", []))
                        st.subheader("Publish Checklist")
                        st.write(data.get("publish_checklist", []))
                        st.download_button("📥 Download JSON", json.dumps(data, ensure_ascii=False, indent=2), "new_listing.json", "application/json")
                except Exception as e:
                    st.error(f"Generation error: {e}")

# ============================================================
# MULTI-LISTING GENERATOR
# ============================================================
elif mode == "🔁 Multi-Listing Generator":
    st.title("🔁 Multi-Listing / Visibility Variant Generator")
    st.info("🎯 Goal: ek hi physical saree ke liye multiple SEO/content angles banana, taaki existing Amazon listing ki search visibility improve karne ke liye relevant keywords aur content options milen. Yeh duplicate ASIN generator nahi hai.")

    tab_content, tab_visibility = st.tabs(["📝 Content Variants", "📈 Visibility Planner"])

    with tab_content:
        marketplace = st.selectbox("Marketplace", list(MARKETPLACE), key="multi_market")
        base = st.text_input("Base Product Name", key="multi_base",
                             placeholder="Example: Pure Vastra Linen Cotton Saree")
        category = st.text_input("Category", value="Sarees", key="multi_category")
        product_type = st.text_input("Product Type", value="Saree", key="multi_product_type")

        st.markdown("### 🔒 Product Fact Lock")
        st.caption("Yahan sirf physically verified facts likhein. AI in facts ko variants ke beech change nahi karega.")
        facts = st.text_area("Verified Product Facts", height=180, key="multi_facts",
                             placeholder="Fabric: Linen Cotton\nColour: Baby Pink\nPattern: Digital Floral Print\nWork: Mirror Work\nPallu: Tassel\nIncluded Components: Blouse Piece")

        current_title = st.text_input("Current Listing Title (optional)", key="multi_current_title")
        current_content = st.text_area("Current Highlights / Bullets / Description (optional)", height=130,
                                        key="multi_current_content")
        kws = st.text_area("Target / Known Keywords (optional)", key="multi_kws",
                           placeholder="linen cotton saree, baby pink saree, digital floral saree, mirror work saree")

        c1, c2 = st.columns(2)
        with c1:
            count = st.slider("Number of content variants", 2, 10, 5, key="multi_count")
        with c2:
            st.caption("Amazon India: variants are drafts/angles for the same ASIN. Do not create duplicate ASINs just because wording differs.")

        strategies_all = [
            "Fabric + comfort focus",
            "Digital print + design focus",
            "Mirror work / embellishment focus",
            "Occasion focus",
            "Pallu + tassel detail focus",
            "Blouse-piece / set completeness focus",
            "Colour + styling focus",
            "Festive / wedding search intent",
            "Minimal keyword-first focus",
            "Long-tail search-intent focus",
        ]
        strategies = st.multiselect("Visibility / content angles", strategies_all,
                                    default=strategies_all[:min(5, count)], key="multi_strategies")

        audit_images = st.file_uploader("📸 Product Images for Fact Verification (optional, max 6)",
                                        type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True,
                                        key="multi_listing_images")
        opened_multi_images = []
        if audit_images:
            audit_images = audit_images[:6]
            cols = st.columns(min(6, len(audit_images)))
            for i, f in enumerate(audit_images):
                try:
                    img = Image.open(f).convert("RGB")
                    opened_multi_images.append(img)
                    with cols[i]:
                        st.image(img, caption=f"Image {i+1}", use_container_width=True)
                except Exception:
                    st.warning(f"Could not read image {i+1}.")

        if st.button("🚀 Generate Visibility Variants", type="primary", key="generate_multi_variants"):
            if not base or not facts:
                st.warning("Base Product Name aur Verified Product Facts required hain.")
            elif not api_key() or genai is None:
                st.warning("⚠️ Kripya sidebar me Gemini API Key configure karein aur google-generativeai package available rakhein.")
            else:
                try:
                    image_note = ""
                    if opened_multi_images:
                        image_note = "\nProduct images are attached. Use them only to verify visible design/colour/print/work/pallu details. Do not infer exact fabric composition or measurements from images."
                    prompt = make_variant_prompt(
                        marketplace, base, facts, category, product_type, kws or "Not supplied",
                        count, strategies or strategies_all[:5], current_content=current_title + "\n" + current_content
                    ) + f"\nCURRENT TITLE (reference only): {current_title}\nCURRENT CONTENT (reference only): {current_content}\n{image_note}\n"
                    payload = [prompt] + opened_multi_images
                    resp = ai_generate(payload)
                    data = safe_json(resp.text)
                    if not data or not isinstance(data.get("variants"), list):
                        st.error("AI JSON parse failed.")
                        st.write(resp.text)
                    else:
                        variants = data["variants"][:count]
                        qdf = variant_quality(variants, marketplace)
                        st.subheader("Variant Quality Dashboard")
                        st.dataframe(qdf, use_container_width=True)

                        titles = [norm(v.get("title")).lower() for v in variants]
                        dupes = {t for t in titles if titles.count(t) > 1 and t}
                        if dupes:
                            st.error("Duplicate titles detected: " + ", ".join(dupes))
                        else:
                            st.success("No exact duplicate titles detected.")

                        st.subheader("Generated Content Variants")
                        for v in variants:
                            with st.expander(f"Variant {v.get('variant_no')} — {v.get('angle','')}"):
                                st.markdown("**Title / Item Name**")
                                st.code(s(v.get("title")))
                                if marketplace == "Amazon India":
                                    st.markdown("**Item Highlights**")
                                    st.code(s(v.get("item_highlights")))
                                st.markdown("**Bullets**")
                                for x in v.get("bullets", []):
                                    st.write("•", x)
                                st.markdown("**Description**")
                                st.write(s(v.get("description")))
                                st.markdown("**Backend Keywords**")
                                st.code(s(v.get("backend_keywords")))
                                st.markdown("**Keyword Focus**")
                                st.write(", ".join(v.get("keyword_focus", [])))
                                st.caption("🔒 Locked-facts check: " + s(v.get("locked_facts_check")))

                        export_rows = []
                        for v in variants:
                            export_rows.append({
                                "marketplace": marketplace,
                                "base_product": base,
                                "variant_no": v.get("variant_no"),
                                "visibility_angle": v.get("angle"),
                                "title": v.get("title"),
                                "item_highlights": v.get("item_highlights"),
                                "bullets": " | ".join(v.get("bullets", [])),
                                "description": v.get("description"),
                                "backend_keywords": v.get("backend_keywords"),
                                "keyword_focus": ", ".join(v.get("keyword_focus", [])),
                                "locked_facts_check": v.get("locked_facts_check"),
                            })
                        out = pd.DataFrame(export_rows)
                        st.download_button("📥 Download Visibility Variants CSV",
                                           out.to_csv(index=False).encode("utf-8-sig"),
                                           "purevastra_visibility_variants.csv", "text/csv",
                                           key="download_multi_variants")
                except Exception as e:
                    st.error(f"Variant generation error: {e}")

    with tab_visibility:
        st.subheader("📈 Visibility Planner")
        st.markdown("Ek hi saree ke liye kaunse searchable/content angles cover ho rahe hain aur kaunse missing hain, yeh plan karein.")
        planner_facts = st.text_area("Verified Product Facts", height=150, key="planner_facts",
                                     placeholder="Fabric, colour, digital print, work, pallu, blouse, occasion...")
        planner_keywords = st.text_area("Existing / Known Keywords", height=100, key="planner_keywords",
                                        placeholder="Paste keywords already used in your listing")
        planner_angles = st.multiselect("Angles to check", strategies_all, default=strategies_all[:5], key="planner_angles")

        if st.button("🔎 Build Visibility Plan", key="build_visibility_plan"):
            if not planner_facts:
                st.warning("Verified Product Facts enter karein.")
            else:
                keyword_tokens = set(tokens(planner_keywords))
                rows = []
                angle_terms = {
                    "Fabric + comfort focus": ["fabric", "linen", "cotton", "lightweight", "breathable"],
                    "Digital print + design focus": ["digital", "print", "floral", "design", "pattern"],
                    "Mirror work / embellishment focus": ["mirror", "work", "embellishment"],
                    "Occasion focus": ["party", "wedding", "festive", "occasion"],
                    "Pallu + tassel detail focus": ["pallu", "tassel", "border"],
                    "Blouse-piece / set completeness focus": ["blouse", "piece", "matching", "set"],
                    "Colour + styling focus": ["colour", "pink", "styling", "style"],
                    "Festive / wedding search intent": ["festive", "wedding", "party"],
                    "Minimal keyword-first focus": ["saree"],
                    "Long-tail search-intent focus": ["saree", "women", "designer", "printed"],
                }
                for angle in planner_angles:
                    terms = angle_terms.get(angle, [])
                    covered = [t for t in terms if t in keyword_tokens]
                    missing = [t for t in terms if t not in keyword_tokens]
                    rows.append({"Visibility Angle": angle, "Covered Terms": ", ".join(covered) or "—",
                                 "Potential Missing Terms": ", ".join(missing) or "None", 
                                 "Status": "Covered" if not missing else "Review"})
                st.dataframe(pd.DataFrame(rows), use_container_width=True)
                st.caption("Note: keyword presence is not a ranking guarantee. Use only terms that accurately describe the product and are allowed by the marketplace/category.")

# ============================================================
# BULK LISTING BUILDER
# ============================================================
elif mode == "📦 Bulk Listing Builder":
    st.title("📦 Bulk Listing Builder & Bulk Audit")
    st.markdown("CSV-based production workflow. Existing content can be audited; blank rows can be prepared for AI generation.")

    template = pd.DataFrame([{
        "marketplace": "Amazon India",
        "sku_asin": "PV-001",
        "base_product": "Linen Cotton Saree",
        "title": "",
        "item_highlights": "",
        "bullets": "",
        "description": "",
        "backend_keywords": "",
        "attributes": "Fabric: Linen Cotton\nColour: Baby Pink",
        "verified_facts": "Fabric: Linen Cotton\nColour: Baby Pink\nPattern: Digital Floral Print",
        "target_keywords": "linen cotton saree, baby pink saree",
        "category": "Sarees",
        "product_type": "Saree",
        "browse_node": "",
        "variant_count": 1,
        "variation_strategies": "Fabric focus|Design focus|Occasion focus",
    }])
    st.download_button("📥 Download Master CSV Template", template.to_csv(index=False).encode("utf-8-sig"),
                       "pure_vastra_bulk_listing_template.csv", "text/csv")

    st.divider()
    st.subheader("🏪 Marketplace Bulk Listing Templates")
    st.caption("Amazon/Meesho templates are based on the exact files you supplied. Flipkart's current bulk template is vertical-specific and generated inside Seller Hub.")

    tc1, tc2, tc3 = st.columns(3)
    with tc1:
        st.markdown("**Amazon India — Saree**")
        b = _template_bytes("Amazon_SAREE_Official_Template_2026_0923.xlsm")
        if b:
            st.download_button("⬇️ Official Amazon XLSM", b,
                               "Amazon_SAREE_Official_Template_2026_0923.xlsm",
                               "application/vnd.ms-excel.sheet.macroEnabled.12", key="tpl_amz_xlsm")
        b = _template_bytes("Amazon_SAREE_upload_format.csv")
        if b:
            st.download_button("⬇️ Amazon Upload-Format CSV", b,
                               "Amazon_SAREE_upload_format.csv", "text/csv", key="tpl_amz_csv")
        st.caption("CSV uses the exact internal upload-field columns from your Amazon Saree template.")

    with tc2:
        st.markdown("**Meesho — Sarees**")
        b = _template_bytes("Meesho_Sarees_Official_Template.xlsx")
        if b:
            st.download_button("⬇️ Official Meesho XLSX", b,
                               "Meesho_Sarees_Official_Template.xlsx",
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="tpl_meesho_xlsx")
        b = _template_bytes("Meesho_Sarees_upload_format.csv")
        if b:
            st.download_button("⬇️ Meesho Upload-Format CSV", b,
                               "Meesho_Sarees_upload_format.csv", "text/csv", key="tpl_meesho_csv")
        st.caption("CSV uses the exact 52 field columns from your 'Sarees-Fill this' sheet.")

    with tc3:
        st.markdown("**Flipkart — Saree**")
        b = _template_bytes("Flipkart_Saree_Starter_Format.csv")
        if b:
            st.download_button("⬇️ Flipkart Starter CSV", b,
                               "Flipkart_Saree_Starter_Format.csv", "text/csv", key="tpl_flip_csv")
        st.warning("Not an official Flipkart upload template.")
        st.caption("Flipkart generates the official template after you select the exact vertical/brand in Seller Hub.")

    st.divider()
    f = st.file_uploader("Upload Bulk CSV", type=["csv"], key="bulk_csv")
    if f:
        df = pd.read_csv(f)
        st.success(f"{len(df)} rows loaded.")
        st.dataframe(df.head(20), use_container_width=True)

        if st.button("🔍 Run Bulk Audit"):
            result = []
            for i, r in df.iterrows():
                mp = s(r.get("marketplace")) or "Amazon India"
                if mp not in MARKETPLACE:
                    mp = "Amazon India"
                a = audit_listing(mp, r.get("title",""), r.get("item_highlights",""),
                                  r.get("bullets",""), r.get("description",""),
                                  r.get("backend_keywords",""), r.get("attributes",""),
                                  r.get("verified_facts",""), r.get("target_keywords",""),
                                  r.get("category",""), r.get("product_type",""), r.get("browse_node",""))
                result.append({
                    "row": i+1, "marketplace": mp, "sku_asin": s(r.get("sku_asin")),
                    "base_product": s(r.get("base_product")), "audit_score": a["score"],
                    "status": a["status"],
                    "critical_issues": " | ".join(x[1] for x in a["critical"]),
                    "warnings": " | ".join(x[1] for x in a["warnings"]),
                })
            out = pd.DataFrame(result)
            st.dataframe(out, use_container_width=True)
            st.download_button("📥 Download Bulk Audit CSV", out.to_csv(index=False).encode("utf-8-sig"),
                               "bulk_audit.csv", "text/csv")

# ============================================================
# LISTING AUDITOR
# ============================================================
elif mode == "🔍 Listing Auditor":
    st.title("🔍 Deep Listing Auditor")
    marketplace = st.selectbox("Marketplace", list(MARKETPLACE), key="audit_market")
    c1,c2 = st.columns(2)
    with c1:
        title = st.text_input("Current Title")
        highlights = st.text_area("Item Highlights / Key Highlights")
        bullets_text = st.text_area("Bullets", height=140)
        description = st.text_area("Description", height=180)
    with c2:
        backend = st.text_area("Backend/Search Keywords")
        attributes = st.text_area("Current Attributes (key: value)", height=120)
        facts = st.text_area("Verified Facts (key: value)", height=120)
        kws = st.text_area("Target Keywords (comma separated)")
        category = st.text_input("Category / Browse Path")
        product_type = st.text_input("Product Type")
        browse = st.text_input("Browse Node / Catalog Node")

    st.divider()
    st.subheader("🖼️ Listing Image Verification")
    st.caption("Upload the actual listing images to verify visible product presentation. Visual checks do not treat AI guesses as verified fabric, measurements or composition facts.")
    listing_images = st.file_uploader(
        "Upload listing images (up to 6)",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        key="audit_listing_images"
    )
    if listing_images:
        listing_images = listing_images[:6]
        imgs = image_list(listing_images)
        if imgs:
            st.write(f"**{len(imgs)} image(s) loaded.**")
            icols = st.columns(min(6, len(imgs)))
            for idx, im in enumerate(imgs):
                with icols[idx % len(icols)]:
                    st.image(im, caption=f"Image {idx+1}", use_container_width=True)
            visual_checks = []
            for idx, im in enumerate(imgs, 1):
                w, h = im.size
                visual_checks.append({
                    "image": idx,
                    "width": w,
                    "height": h,
                    "aspect_ratio": round(w / h, 3) if h else 0,
                    "resolution": "PASS" if min(w, h) >= 500 else "WARNING — low resolution",
                    "format": im.format or "unknown"
                })
            st.dataframe(pd.DataFrame(visual_checks), use_container_width=True)

            if st.button("🤖 Verify Images with AI", key="audit_ai_images"):
                try:
                    prompt = f"""
You are verifying e-commerce listing images for {marketplace}.
Compare the uploaded images with these seller-provided facts and listing content.
Do not invent facts and do not claim fabric composition, measurements, exact color, GSM,
or other non-visible specifications from an image. Mark each point as:
VISIBLE / NOT VISIBLE / UNCERTAIN / CONFLICT.
Check: product consistency across images, visible garment/saree design, colour appearance,
print/work/pallu/blouse visibility, image quality, background clarity, text/logo/watermark,
and whether the images appear to show the same product.
Seller verified facts: {facts}
Current attributes: {attributes}
Title: {title}
Return concise JSON with keys: overall, checks (list), conflicts (list), verification_required (list).
"""
                    parts = [prompt] + imgs
                    resp = ai_generate(parts)
                    result = safe_json(getattr(resp, "text", "") or "")
                    if result:
                        st.json(result)
                    else:
                        st.write(getattr(resp, "text", "No structured result returned."))
                except Exception as e:
                    st.error(f"AI image verification error: {e}")

    if st.button("🔍 Audit Listing", type="primary"):
        a = audit_listing(marketplace, title, highlights, bullets_text, description, backend,
                          attributes, facts, kws, category, product_type, browse)
        c1,c2,c3 = st.columns(3)
        c1.metric("Audit Score", a["score"])
        c2.metric("Status", a["status"])
        c3.metric("Missing Keywords", len(a["missing_keywords"]))
        st.subheader("Critical Issues")
        for x in a["critical"]:
            st.error(f"{x[0]} — {x[1]}: {x[2]}")
        st.subheader("Warnings")
        for x in a["warnings"]:
            st.warning(f"{x[0]} — {x[1]}: {x[2]}")
        st.subheader("Passed Checks")
        for x in a["passed"]:
            st.success(x)

# ============================================================
# LISTING HEALTH CENTER
# ============================================================
elif mode == "📊 Listing Health Center":
    st.title("📊 Listing Health Center")
    st.caption("Business Report CSV se traffic vs conversion diagnosis. It does not replace marketplace analytics.")

    f = st.file_uploader("Upload Amazon Business Report CSV", type=["csv"], key="health_csv")
    if f:
        df = pd.read_csv(f)
        h = business_health(df)
        st.dataframe(h, use_container_width=True)
        if "Diagnosis" in h:
            st.subheader("Diagnosis Summary")
            st.write(h["Diagnosis"].value_counts())
        st.download_button("📥 Download Health Report", h.to_csv(index=False).encode("utf-8-sig"),
                           "listing_health_report.csv", "text/csv")

# ============================================================
# PROFIT CALCULATOR
# ============================================================
elif mode == "💰 Profit & Margin Calculator":
    st.title("💰 Profit & Margin Calculator")
    st.caption("Marketplace fees are editable assumptions. Verify your current Seller/Supplier fee schedule before making pricing decisions.")

    marketplace = st.selectbox("Marketplace", list(DEFAULT_FEES))
    c1,c2,c3 = st.columns(3)
    with c1:
        selling = st.number_input("Selling Price (₹)", 0.0, 100000.0, 899.0)
        product_cost = st.number_input("Product Cost (₹)", 0.0, 100000.0, 350.0)
        packaging = st.number_input("Packaging (₹)", 0.0, 10000.0, 15.0)
    with c2:
        shipping = st.number_input("Shipping/Fulfilment (₹)", 0.0, 10000.0, 70.0)
        ads = st.number_input("Ads per Order (₹)", 0.0, 10000.0, 30.0)
        return_cost = st.number_input("Expected Return/NCX Cost per Order (₹)", 0.0, 10000.0, 25.0)
    with c3:
        referral_pct = st.number_input("Referral Fee %", 0.0, 100.0, DEFAULT_FEES[marketplace]["referral_pct"])
        closing = st.number_input("Closing / Fixed Fee (₹)", 0.0, 10000.0, DEFAULT_FEES[marketplace]["closing"])
        gst_rate = st.number_input("GST on Marketplace Fees %", 0.0, 100.0, 18.0)

    if st.button("Calculate", type="primary"):
        referral = selling * referral_pct / 100
        fee_gst = (referral + closing) * gst_rate / 100
        total_cost = product_cost + packaging + shipping + ads + return_cost + referral + closing + fee_gst
        profit = selling - total_cost
        margin = profit / selling * 100 if selling else 0
        break_even = total_cost / max(1 - referral_pct/100, 0.01) if selling else 0

        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Net Profit", f"₹{profit:,.2f}")
        c2.metric("Net Margin", f"{margin:.2f}%")
        c3.metric("Marketplace Fee + GST", f"₹{referral+closing+fee_gst:,.2f}")
        c4.metric("Total Cost", f"₹{total_cost:,.2f}")

        if profit > 0:
            st.success("Positive contribution margin under these assumptions.")
        else:
            st.error("Negative contribution margin under these assumptions.")

# ============================================================
# PRICE SIMULATOR
# ============================================================
elif mode == "🧮 Price / Break-even Simulator":
    st.title("🧮 Price & Break-even Simulator")
    marketplace = st.selectbox("Marketplace", list(DEFAULT_FEES), key="sim_market")
    base_cost = st.number_input("Fixed non-marketplace cost per order (₹)", 0.0, 100000.0, 500.0)
    fee_pct = st.number_input("Marketplace fee %", 0.0, 100.0, DEFAULT_FEES[marketplace]["referral_pct"])
    fee_fixed = st.number_input("Fixed marketplace fee (₹)", 0.0, 10000.0, 0.0)
    gst_fee = st.number_input("GST on marketplace fees %", 0.0, 100.0, 18.0)
    ad_pct = st.number_input("Ad cost % of selling price", 0.0, 100.0, 3.0)
    low = st.number_input("Start price", 1.0, 100000.0, 599.0)
    high = st.number_input("End price", 1.0, 100000.0, 1499.0)
    step = st.number_input("Step", 1.0, 10000.0, 50.0)

    if st.button("Build Price Table", type="primary"):
        rows = []
        p = low
        while p <= high + 1e-9:
            fee = p * fee_pct/100 + fee_fixed
            fee_tax = fee * gst_fee/100
            ads = p * ad_pct/100
            profit = p - base_cost - fee - fee_tax - ads
            rows.append({"Selling Price": round(p,2), "Marketplace Fee": round(fee,2),
                         "Fee GST": round(fee_tax,2), "Ads": round(ads,2),
                         "Net Profit": round(profit,2),
                         "Margin %": round(profit/p*100,2)})
            p += step
        out = pd.DataFrame(rows)
        st.dataframe(out, use_container_width=True)
        st.download_button("📥 Download Price Scenarios", out.to_csv(index=False).encode("utf-8-sig"),
                           "price_scenarios.csv", "text/csv")

# ============================================================
# PDF LABEL CROPPER
# ============================================================
elif mode == "🧾 PDF Label Cropper":
    st.title("🧾 PDF Label Cropper & Sorter")
    st.caption("Marketplace-specific shipping-label templates for Amazon, Flipkart/E-Kart and Meesho/Valmo. Invoice pages/areas are excluded where the marketplace format allows it.")

    if PdfReader is None:
        st.warning("Install pypdf from requirements.txt to enable PDF processing.")
    else:
        pdf = st.file_uploader("Upload Flipkart / Meesho PDF", type=["pdf"], key="label_pdf")
        if pdf:
            data = pdf.read()
            reader = PdfReader(io.BytesIO(data))
            page_texts = [(p.extract_text() or "").lower() for p in reader.pages]
            st.success(f"{len(reader.pages)} page(s) loaded.")

            # These templates were measured from the user's supplied 595 x 842 point PDFs.
            # Coordinates are expressed as percentages of the page, with Y measured from
            # the bottom-left PDF origin.
            templates = {
                # Calibrated from the supplied Flipkart and Meesho/Valmo samples.
                # Y is measured from the PDF bottom-left origin.
                "Meesho / Valmo — exact label": (0.0, 58.5, 100.0, 98.8),
                "Flipkart / E-Kart — exact label": (31.0, 54.0, 69.0, 97.5),
            }

            c1, c2, c3 = st.columns(3)
            with c1:
                mode_crop = st.selectbox(
                    "Label template",
                    [
                        "Auto Detect (Amazon / Flipkart / Meesho)",
                        "Amazon — exact shipping label (keep label page)",
                        "Meesho / Valmo — exact label",
                        "Flipkart / E-Kart — exact label",
                        "Custom crop",
                        "Keep pages",
                        "2-up split",
                        "4-up split",
                    ],
                    help="Auto Detect reads the PDF text page-by-page. Amazon shipping-label pages are kept as-is because the supplied Amazon label already occupies the full page; invoice pages are skipped when detected."
                )
            with c2:
                order = st.selectbox("Page order", ["Original", "Reverse"])
            with c3:
                margin = st.number_input(
                    "Safety margin %",
                    min_value=0.0, max_value=5.0, value=0.0, step=0.1,
                    help="Adds a small border around the marketplace label. Use 0.0 for the tightest crop."
                )

            st.subheader("🚚 Delivery Partner Filter")
            partner_filter = st.selectbox(
                "Keep only labels for",
                [
                    "All Partners",
                    "Amazon / Amazon Shipping",
                    "Flipkart / E-Kart",
                    "Meesho / Valmo",
                    "Delhivery",
                    "Blue Dart",
                    "Xpressbees",
                    "DTDC",
                    "Ecom Express",
                    "Shadowfax",
                    "Custom keyword",
                ],
                key="label_partner_filter",
                help="Filters pages by delivery-partner/carrier text. Existing marketplace presets, Auto Detect, Keep pages, 2-up and 4-up remain available."
            )
            custom_partner_keyword = ""
            if partner_filter == "Custom keyword":
                custom_partner_keyword = st.text_input(
                    "Delivery partner keyword",
                    placeholder="e.g. amazon shipping, shadowfax, ecom express",
                    key="custom_partner_keyword"
                ).strip().lower()

            c4, c5 = st.columns(2)
            with c4:
                start = st.number_input("Start page", 1, len(reader.pages), 1)
            with c5:
                end = st.number_input("End page", int(start), len(reader.pages), len(reader.pages))
            pages = list(range(int(start)-1, int(end)))
            if order == "Reverse":
                pages.reverse()

            st.write("Selected pages:", [x + 1 for x in pages])

            if mode_crop == "Custom crop":
                st.info("Coordinates are percentages. X is left→right. Y is bottom→top, matching PDF coordinates.")
                cc1, cc2, cc3, cc4 = st.columns(4)
                with cc1:
                    x1_pct = st.number_input("Left X %", 0.0, 100.0, 30.0, 0.5)
                with cc2:
                    y1_pct = st.number_input("Bottom Y %", 0.0, 100.0, 53.0, 0.5)
                with cc3:
                    x2_pct = st.number_input("Right X %", 0.0, 100.0, 70.0, 0.5)
                with cc4:
                    y2_pct = st.number_input("Top Y %", 0.0, 100.0, 98.5, 0.5)
            elif mode_crop in templates:
                x1_pct, y1_pct, x2_pct, y2_pct = templates[mode_crop]
                st.info(
                    f"Preset: X {x1_pct:.1f}–{x2_pct:.1f}% | "
                    f"Y {y1_pct:.1f}–{y2_pct:.1f}%. "
                    f"This is calibrated to the supplied {mode_crop.split('—')[0].strip()} sample."
                )
            else:
                x1_pct = y1_pct = x2_pct = y2_pct = None

            if mode_crop == "Auto Detect (Amazon / Flipkart / Meesho)":
                st.info("Auto Detect: Amazon shipping-label pages are kept as full label pages; Flipkart/E-Kart uses the centered template; Meesho/Valmo uses the wide upper-page template. Detected invoice-only pages are skipped.")
            elif mode_crop == "Amazon — exact shipping label (keep label page)":
                st.info("Amazon sample: the shipping label is the complete first page. The second page is the Tax Invoice, so this preset keeps only the Amazon label page.")

            if st.button("✂️ Create Label PDF", type="primary"):
                writer = PdfWriter()
                detections = []

                def partner_matches(txt, selected, custom_kw=""):
                    txt = (txt or "").lower()
                    if selected == "All Partners":
                        return True
                    if selected == "Custom keyword":
                        return bool(custom_kw) and custom_kw in txt
                    terms = {
                        "Amazon / Amazon Shipping": ["amazon", "amazon shipping", "amazon transportation services", "ats"],
                        "Flipkart / E-Kart": ["flipkart", "e-kart", "ekart logistics", "ekart"],
                        "Meesho / Valmo": ["meesho", "valmo"],
                        "Delhivery": ["delhivery"],
                        "Blue Dart": ["blue dart", "bluedart"],
                        "Xpressbees": ["xpressbees", "xpress bees"],
                        "DTDC": ["dtdc"],
                        "Ecom Express": ["ecom express", "ecomexpress"],
                        "Shadowfax": ["shadowfax"],
                    }
                    return any(t in txt for t in terms.get(selected, []))

                for pi in pages:
                    page = reader.pages[pi]
                    detected = None
                    skip_page = False
                    page_txt = page_texts[pi]
                    if mode_crop == "Auto Detect (Amazon / Flipkart / Meesho)":
                        txt = page_txt
                        # Amazon shipping-label page: strong combination found in the supplied sample.
                        amazon_label = (
                            ("ship to:" in txt or "ship to" in txt)
                            and ("awb" in txt or "box 1 of 1" in txt)
                            and ("customer self declaration" in txt or "sold on: www.amazon.in" in txt)
                        )
                        amazon_invoice = "tax invoice/bill of supply/cash memo" in txt or ("tax invoice" in txt and "invoice value" in txt)
                        # The supplied Amazon shipping-label page is image-based and has almost no
                        # extractable text. If the following page is clearly the Amazon tax invoice,
                        # treat the current image-only page as the shipping label.
                        next_is_amazon_invoice = (
                            pi + 1 < len(page_texts)
                            and ("tax invoice/bill of supply/cash memo" in page_texts[pi + 1]
                                 or ("tax invoice" in page_texts[pi + 1] and "invoice value" in page_texts[pi + 1]))
                        )
                        if amazon_label and not amazon_invoice:
                            detected = "Amazon — exact shipping label (keep label page)"
                        elif amazon_invoice and not amazon_label:
                            detected = "SKIP — Amazon invoice"
                        elif not txt.strip() and next_is_amazon_invoice:
                            detected = "Amazon — exact shipping label (keep label page)"
                        elif "flipkart" in txt or "e-kart logistics" in txt or "ekart logistics" in txt:
                            detected = "Flipkart / E-Kart — exact label"
                        elif "valmo" in txt or "meesho" in txt:
                            detected = "Meesho / Valmo — exact label"

                    effective = detected if detected else mode_crop

                    # Apply delivery-partner filtering after marketplace detection so image-based
                    # Amazon label pages can still match via the detected preset/next-page invoice logic.
                    partner_probe = page_txt
                    if effective == "Amazon — exact shipping label (keep label page)":
                        partner_probe += " amazon amazon shipping ats"
                    elif effective == "Flipkart / E-Kart — exact label":
                        partner_probe += " flipkart e-kart logistics"
                    elif effective == "Meesho / Valmo — exact label":
                        partner_probe += " meesho valmo"
                    if not partner_matches(partner_probe, partner_filter, custom_partner_keyword):
                        detections.append((pi + 1, f"SKIP — partner filter: {partner_filter}"))
                        continue

                    # Amazon exact-label preset: keep shipping-label pages and skip detected tax-invoice pages.
                    if mode_crop == "Amazon — exact shipping label (keep label page)" and not detected:
                        txt_for_preset = (page.extract_text() or "").lower()
                        if "tax invoice/bill of supply/cash memo" in txt_for_preset or ("tax invoice" in txt_for_preset and "invoice value" in txt_for_preset):
                            effective = "SKIP — Amazon invoice"
                        else:
                            effective = "Amazon — exact shipping label (keep label page)"
                    detections.append((pi + 1, effective))

                    if effective.startswith("SKIP"):
                        skip_page = True
                    if skip_page:
                        continue
                    if effective == "Keep pages" or (mode_crop == "Auto Detect (Amazon / Flipkart / Meesho)" and not detected):
                        writer.add_page(page)
                        continue

                    mb = page.mediabox
                    w = float(mb.width)
                    h = float(mb.height)

                    def add_crop(x1, y1, x2, y2):
                        x1 = max(0.0, min(w, float(x1)))
                        x2 = max(0.0, min(w, float(x2)))
                        y1 = max(0.0, min(h, float(y1)))
                        y2 = max(0.0, min(h, float(y2)))
                        if x2 <= x1 or y2 <= y1:
                            raise ValueError("Invalid crop rectangle. Check crop settings.")

                        clone = copy.deepcopy(page)
                        # Add a small safety margin while staying inside the page.
                        mx = (x2 - x1) * float(margin) / 100.0
                        my = (y2 - y1) * float(margin) / 100.0
                        x1 = max(0.0, x1 - mx)
                        y1 = max(0.0, y1 - my)
                        x2 = min(w, x2 + mx)
                        y2 = min(h, y2 + my)
                        box = RectangleObject([x1, y1, x2, y2])
                        clone.cropbox = box
                        clone.mediabox = box
                        writer.add_page(clone)

                    if effective == "Amazon — exact shipping label (keep label page)":
                        # The supplied Amazon shipping label is already a full-page label.
                        # Do not crop it: trimming would remove the AWB, QR codes, route boxes,
                        # declaration and barcode. Simply copy the label page.
                        writer.add_page(copy.deepcopy(page))
                    elif effective in templates:
                        a, b, c, d = templates[effective]
                        add_crop(w*a/100.0, h*b/100.0, w*c/100.0, h*d/100.0)
                    elif effective == "Custom crop":
                        add_crop(w*x1_pct/100.0, h*y1_pct/100.0, w*x2_pct/100.0, h*y2_pct/100.0)
                    elif effective == "2-up split":
                        add_crop(0, 0, w/2, h)
                        add_crop(w/2, 0, w, h)
                    elif effective == "4-up split":
                        for row in range(2):
                            for col in range(2):
                                add_crop(col*w/2, row*h/2, (col+1)*w/2, (row+1)*h/2)
                    else:
                        writer.add_page(page)

                out = io.BytesIO()
                writer.write(out)
                out.seek(0)

                if detections:
                    st.write("Detected/selected template:", detections)

                st.success(f"Label PDF ready — {len(writer.pages)} page(s).")
                st.download_button(
                    "📥 Download Label PDF",
                    out.getvalue(),
                    "pure_vastra_shipping_labels.pdf",
                    "application/pdf"
                )

# ============================================================
# AI VIRTUAL MODEL STUDIO
# ============================================================
elif mode == "👗 AI Virtual Model Studio":
    st.title("👗 AI Virtual Model Studio")
    st.caption("Upload garment photos → preview → analyze/lock product facts. This V4 module analyzes references; it does not silently generate a new model image.")

    files = st.file_uploader(
        "Upload garment reference images",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        key="vton",
        help="Use clear front/back/detail photos. Up to 3 images are analyzed."
    )

    if not files:
        st.info("👆 Pehle kam se kam 1 garment image upload kijiye.")
    else:
        imgs = image_list(files[:3])
        if not imgs:
            st.error("Uploaded image read nahi ho payi. JPG/PNG/WEBP file try karein.")
        else:
            cols = st.columns(len(imgs))
            for i, im in enumerate(imgs):
                with cols[i]:
                    st.image(im, caption=f"Reference {i+1}", use_container_width=True)

            st.write(f"**{len(imgs)} image(s) ready.**")
            c1, c2 = st.columns(2)
            with c1:
                analyze_clicked = st.button("🔍 Analyze Garment", type="primary", use_container_width=True)
            with c2:
                clear_clicked = st.button("🗑️ Clear Analysis", use_container_width=True)

            if clear_clicked:
                st.session_state.pop("locked_garment_profile", None)
                st.session_state.pop("garment_analysis_result", None)
                st.rerun()

            if analyze_clicked:
                # Always give visible feedback. AI is optional; without a key we still
                # expose image metadata instead of appearing to do nothing.
                key = api_key()
                if key and genai is not None:
                    try:
                        with st.spinner("Gemini garment analysis chal raha hai..."):
                            resp = ai_generate([
                                """Analyze these uploaded garment references for e-commerce use.
Return JSON only with: apparent_colour, apparent_pattern, visible_work, visible_border,
visible_pallu_details, visible_blouse_piece, visual_notes, verification_required.
Only report visually supportable observations. Do not claim exact fabric composition,
measurements, GSM, certification, quality grade, or other non-visible specifications.
If something is uncertain, put it in verification_required.""",
                                *imgs
                            ])
                        data = safe_json(getattr(resp, "text", ""))
                        if data is None:
                            data = {"raw_ai_response": getattr(resp, "text", ""), "verification_required": ["Review AI response before publishing."]}
                        st.session_state["garment_analysis_result"] = data
                        st.session_state["locked_garment_profile"] = data
                        st.success("✅ Garment analysis complete. Review the facts before using them in a listing.")
                    except Exception as e:
                        st.error(f"Gemini analysis failed: {e}")
                        st.info("API key/quota/network issue ho sakta hai. Neeche image metadata fallback available hai.")
                        data = {
                            "images_analyzed": len(imgs),
                            "image_dimensions": [f"{im.width} × {im.height}px" for im in imgs],
                            "verification_required": ["AI analysis unavailable; manually verify colour, fabric, pattern, work, pallu and included components."],
                        }
                        st.session_state["garment_analysis_result"] = data
                else:
                    data = {
                        "images_analyzed": len(imgs),
                        "image_dimensions": [f"{im.width} × {im.height}px" for im in imgs],
                        "ai_status": "Gemini API key not configured",
                        "verification_required": [
                            "Add Gemini API Key in the left sidebar for AI analysis.",
                            "Do not treat image appearance as proof of exact fabric composition or measurements.",
                        ],
                    }
                    st.session_state["garment_analysis_result"] = data
                    st.warning("Gemini API key configured nahi hai. Image upload/action working hai, lekin AI analysis ke liye sidebar me API key deni hogi.")

            result = st.session_state.get("garment_analysis_result")
            if result:
                st.subheader("Analysis / Verification")
                st.json(result)
                st.caption("🔒 Lock karne se pehle AI-suggested facts ko manually verify karein. Exact fabric/composition/measurements ko image se infer na karein.")

# ============================================================
# METHODOLOGY
# ============================================================
else:
    st.title("⚙️ Methodology & Templates")
    st.markdown("""
### Core principles

**1. Verified facts first**
AI must not invent material, dimensions, certifications, quality claims, warranty or product features.

**2. Multi-listing**
The Multi-Listing Generator changes wording/angle while keeping the same physical product facts locked. It does not certify that separate duplicate marketplace catalogs are allowed.

**3. Similarity control**
Generated titles are compared using token-set similarity. Exact duplicates are flagged.

**4. Marketplace rules**
Marketplace profiles are configurable. Always verify the current Seller/Supplier panel and category template before publishing.

**5. Performance diagnosis**
Business Report analysis separates low-traffic situations from situations where traffic exists but conversion needs review.

### Suggested bulk CSV columns

`marketplace, sku_asin, base_product, title, item_highlights, bullets, description, backend_keywords, attributes, verified_facts, target_keywords, category, product_type, browse_node, variant_count, variation_strategies`

### Recommended workflow

Product facts → New Listing → Multi-Listing variants → Audit → Business Report Health → Profit check → Publish.
""")
    st.subheader("Amazon India current note")
    st.info(MARKETPLACE["Amazon India"]["note"])
