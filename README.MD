# Pure Vastra Seller Intelligence Suite V4

## Modules
- New Single Listing Builder
- Multi-Listing / Content Variant Generator
- Bulk Listing Builder & Bulk Audit
- Deep Listing Auditor
- Listing Health Center (Business Report CSV)
- Profit & Margin Calculator
- Price / Break-even Simulator
- PDF Label Cropper & Sorter
- AI Virtual Model Studio
- Methodology & Templates

## Run
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Multi-listing behavior
The Multi-Listing Generator creates multiple content drafts for the SAME physical product. It locks seller-provided verified facts and varies wording/angle. It does NOT certify that separate duplicate catalogs are allowed by a marketplace.

## Amazon note
The app is configured for Amazon India's current 75-character Item Name / 125-character Item Highlights guidance for most non-media categories, based on Amazon Seller Central's July 2026 announcement. Always verify the current category-specific Seller Central template before upload.

## Important
Marketplace fees are editable assumptions and must be verified against the seller's current fee schedule.
