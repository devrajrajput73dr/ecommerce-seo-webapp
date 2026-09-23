# PureVastra Seller Intelligence Suite V4.10.1

## Dynamic Marketplace Template Engine

This build extends the visibility-variant workflow to **Amazon India, Flipkart and Meesho together**.

### Workflow
1. Select marketplace: Amazon India / Flipkart / Meesho.
2. Select the product vertical/category.
3. Upload the **actual latest template downloaded from that marketplace for that vertical** (`.xlsx`, `.xlsm` or `.csv`).
4. Upload product images and enter verified product facts.
5. Generate visibility/content variants.
6. The app maps product facts, generated listing content and seller-provided operational data into the uploaded template's detected columns.
7. Any fields that cannot be confidently auto-filled are shown in a fixed **Remaining Manual Fields** table.
8. Required fields exposed by the uploaded template are validated before download.
9. Download the final **Prefilled CSV** with the uploaded template's detected column order preserved.

### Important
- No category-specific upload format is hard-coded as the only format. The uploaded template is the source of truth for each vertical.
- System-use/error fields are intentionally left untouched.
- AI must not invent product facts. Unknown values remain manual.
- For Flipkart, upload the current official vertical template from Seller Hub rather than relying on the included starter CSV.
- For Amazon, upload the current official vertical template from Seller Central for the exact product type.
- Marketplace acceptance can still depend on the marketplace's current validation rules; the app validates what can be inferred from the uploaded template and blocks unresolved required fields.
