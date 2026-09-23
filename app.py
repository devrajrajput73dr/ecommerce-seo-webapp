
import io
import json
import math
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
except Exception:
    PdfReader = PdfWriter = None

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
    rename = {}
    for c in df.columns:
        lc = c.lower().strip()
        if "asin" in lc:
            rename[c] = "ASIN"
        elif "sku" == lc or lc.endswith("sku"):
            rename[c] = "SKU"
        elif "sessions" in lc:
            rename[c] = "Sessions"
        elif "units ordered" in lc:
            rename[c] = "Orders"
        elif "unit session" in lc:
            rename[c] = "Conversion"
        elif "ordered product sales" in lc or lc == "sales":
            rename[c] = "Sales"
        elif "title" in lc:
            rename[c] = "Title"
    x = df.rename(columns=rename).copy()
    for c in ["Sessions","Orders","Sales"]:
        if c in x:
            x[c] = pd.to_numeric(x[c], errors="coerce").fillna(0)
    if "Conversion" not in x and {"Sessions","Orders"} <= set(x.columns):
        x["Conversion"] = (x["Orders"] / x["Sessions"].replace(0, pd.NA) * 100).fillna(0)
    if "Orders" in x and "Sessions" in x:
        x["Diagnosis"] = x.apply(
            lambda r: "NO/LOW TRAFFIC DATA" if r["Sessions"] < 20 and r["Orders"] == 0
            else ("TRAFFIC OK → CHECK CONVERSION" if r["Sessions"] >= 50 and r["Orders"] == 0
                  else ("CONVERSION REVIEW" if r["Orders"] > 0 and r["Conversion"] < 1.0
                        else "NORMAL / MONITOR")),
            axis=1,
        )
    return x

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
    st.title("🔁 Multi-Listing / Content Variant Generator")
    st.warning("This creates content variants for the SAME physical product. It does not certify that separate duplicate marketplace catalogs are permitted.")

    marketplace = st.selectbox("Marketplace", list(MARKETPLACE), key="multi_market")
    base = st.text_input("Base Product Name", value="Pure Vastra Linen Cotton Saree")
    category = st.text_input("Category", value="Sarees")
    product_type = st.text_input("Product Type", value="Saree")
    facts = st.text_area("🔒 LOCKED VERIFIED FACTS", height=180,
                         value="Fabric: Linen Cotton\nColour: Baby Pink\nPattern: Digital Floral Print\nWork: Mirror Work\nPallu: Tassel\nIncluded Components: Blouse Piece")
    kws = st.text_area("Target Keywords", value="linen cotton saree, baby pink saree, digital floral saree, mirror work saree")
    count = st.slider("Number of variants", 2, 20, 5)

    strategies_all = [
        "Fabric + comfort focus",
        "Print + design focus",
        "Mirror work / embellishment focus",
        "Occasion focus",
        "Pallu + tassel detail focus",
        "Blouse-piece / set completeness focus",
        "Colour + styling focus",
        "Gift / festive use focus",
        "Minimal concise keyword-first focus",
        "Long-tail search-intent focus",
    ]
    strategies = st.multiselect("Variation strategies", strategies_all, default=strategies_all[:min(5,count)])
    if len(strategies) < count:
        st.caption("Strategies repeat only after the selected strategy pool is exhausted; facts remain locked.")

    if st.button("🚀 Generate Multiple Listing Variants", type="primary"):
        try:
            prompt = make_variant_prompt(marketplace, base, facts, category, product_type, kws, count, strategies)
            resp = ai_generate([prompt])
            data = safe_json(resp.text)
            if not data or not isinstance(data.get("variants"), list):
                st.error("AI JSON parse failed.")
                st.write(resp.text)
            else:
                variants = data["variants"][:count]
                qdf = variant_quality(variants, marketplace)
                st.subheader("Variant Quality Dashboard")
                st.dataframe(qdf, use_container_width=True)

                # Exact duplicate title detection
                titles = [norm(v.get("title")).lower() for v in variants]
                dupes = {t for t in titles if titles.count(t) > 1 and t}
                if dupes:
                    st.error("Duplicate titles detected: " + ", ".join(dupes))
                else:
                    st.success("No exact duplicate titles detected.")

                st.subheader("Generated Variants")
                for v in variants:
                    with st.expander(f"Variant {v.get('variant_no')} — {v.get('angle','')}"):
                        st.markdown("**Title**")
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

                export_rows = []
                for v in variants:
                    export_rows.append({
                        "marketplace": marketplace,
                        "base_product": base,
                        "variant_no": v.get("variant_no"),
                        "angle": v.get("angle"),
                        "title": v.get("title"),
                        "item_highlights": v.get("item_highlights"),
                        "bullets": " | ".join(v.get("bullets", [])),
                        "description": v.get("description"),
                        "backend_keywords": v.get("backend_keywords"),
                        "keyword_focus": ", ".join(v.get("keyword_focus", [])),
                        "locked_facts_check": v.get("locked_facts_check"),
                    })
                out = pd.DataFrame(export_rows)
                st.download_button("📥 Download Multi-Listing CSV", out.to_csv(index=False).encode("utf-8-sig"),
                                   "multi_listing_variants.csv", "text/csv")
        except Exception as e:
            st.error(f"Variant generation error: {e}")

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
    st.caption("Local PDF processing. No AI is required for basic page splitting/reordering.")

    if PdfReader is None:
        st.warning("Install pypdf from requirements.txt to enable PDF processing.")
    else:
        pdf = st.file_uploader("Upload PDF", type=["pdf"], key="label_pdf")
        if pdf:
            data = pdf.read()
            reader = PdfReader(io.BytesIO(data))
            st.success(f"{len(reader.pages)} pages loaded.")

            c1,c2,c3 = st.columns(3)
            with c1:
                mode_crop = st.selectbox("Page mode", ["Keep pages", "2-up split", "4-up split"])
            with c2:
                order = st.selectbox("Order", ["Original", "Reverse"])
            with c3:
                start = st.number_input("Start page", 1, len(reader.pages), 1)

            end = st.number_input("End page", int(start), len(reader.pages), len(reader.pages))
            pages = list(range(int(start)-1, int(end)))
            if order == "Reverse":
                pages.reverse()

            st.write("Selected pages:", [x+1 for x in pages])

            if st.button("✂️ Create Output PDF", type="primary"):
                # Keep-pages is lossless and reliable. For split modes, create quarter/half
                # pages using pypdf transformations when page media boxes are available.
                writer = PdfWriter()
                for pi in pages:
                    page = reader.pages[pi]
                    if mode_crop == "Keep pages":
                        writer.add_page(page)
                    else:
                        mb = page.mediabox
                        w = float(mb.width)
                        h = float(mb.height)
                        if mode_crop == "2-up split":
                            for side in range(2):
                                new = reader.pages[pi]
                                clone = new
                                # CropBox clipping; original page object is not mutated permanently.
                                clone = type(page)(page)
                                if side == 0:
                                    clone.cropbox.lower_left = (0, 0)
                                    clone.cropbox.upper_right = (w/2, h)
                                else:
                                    clone.cropbox.lower_left = (w/2, 0)
                                    clone.cropbox.upper_right = (w, h)
                                writer.add_page(clone)
                        else:
                            for row in range(2):
                                for col in range(2):
                                    clone = type(page)(page)
                                    clone.cropbox.lower_left = (col*w/2, row*h/2)
                                    clone.cropbox.upper_right = ((col+1)*w/2, (row+1)*h/2)
                                    writer.add_page(clone)

                out = io.BytesIO()
                writer.write(out)
                out.seek(0)
                st.success("Output PDF ready.")
                st.download_button("📥 Download Cropped PDF", out.getvalue(),
                                   "pure_vastra_labels_cropped.pdf", "application/pdf")

# ============================================================
# AI VIRTUAL MODEL STUDIO
# ============================================================
elif mode == "👗 AI Virtual Model Studio":
    st.title("👗 AI Virtual Model Studio")
    st.info("Garment-reference analysis is supported. Actual image rendering depends on the configured image-generation service.")
    files = st.file_uploader("Upload garment reference images", type=["jpg","jpeg","png"], accept_multiple_files=True, key="vton")
    if files:
        imgs = image_list(files[:3])
        cols = st.columns(len(imgs))
        for i, im in enumerate(imgs):
            with cols[i]:
                st.image(im, caption=f"Reference {i+1}", use_container_width=True)
        if st.button("🔒 Analyze & Lock Garment Facts"):
            try:
                resp = ai_generate([
                    """Analyze the uploaded garment references for e-commerce use.
Return JSON with only visually supportable observations: apparent colour, pattern, fabric if visually stated by seller, border/work details, pallu details, included components only if explicitly provided, and verification_required.
Do not claim exact fabric composition from appearance alone.""",
                    *imgs
                ])
                data = safe_json(resp.text)
                if data:
                    st.json(data)
                    st.session_state["locked_garment_profile"] = data
                else:
                    st.write(resp.text)
            except Exception as e:
                st.error(str(e))

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
