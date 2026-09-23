# Pure Vastra Seller Intelligence Suite V4.1

## Modules
1. 🆕 New Single Listing
2. 🔁 Multi-Listing Generator
3. 📦 Bulk Listing Builder
4. 🔍 Listing Auditor
5. 📊 Listing Health Center
6. 💰 Profit & Margin Calculator
7. 🧮 Price / Break-even Simulator
8. 🧾 PDF Label Cropper
9. 👗 AI Virtual Model Studio
10. ⚙️ Methodology & Templates

## V4.1 stability fixes
- PDF Label Cropper: fixed pypdf CropBox handling using safe page copies and RectangleObject; 2-up and 4-up splitting tested.
- Listing Health Center: robust Amazon Business Report column normalization; avoids duplicate-column pandas errors and correctly reads Unit Session Percentage, Sessions, Units Ordered and Ordered Product Sales.
- AI Virtual Model Studio: upload/preview/action now always gives visible feedback. Gemini analysis works when an API key is configured; without a key the app shows a clear fallback instead of a silent no-op. AI observations remain verification-required and do not prove exact fabric composition or measurements.

## Run
```bash
pip install -r requirements.txt
streamlit run app.py
```

Gemini is optional. Configure the API key in the sidebar or as `GEMINI_API_KEY` in Streamlit secrets for AI analysis.

Marketplace fees are editable assumptions and must be verified against the current marketplace fee schedule before pricing decisions.


## V4.3 PDF Label Cropper Calibration
The PDF Label Cropper now includes marketplace-specific templates calibrated against the supplied Pure Vastra sample PDFs:
- Meesho / Valmo — exact label: wide upper-page label; invoice excluded.
- Flipkart / E-Kart — exact label: centered upper-page label; invoice excluded.
- Auto Detect (Flipkart / Meesho): detects Flipkart/E-Kart or Meesho/Valmo from page text and applies the matching template.
- Custom crop remains available using PDF bottom-left coordinates.
- Safety margin defaults to 0% for tight marketplace-label cropping.
