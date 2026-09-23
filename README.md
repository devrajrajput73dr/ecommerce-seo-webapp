# PureVastra Seller Intelligence Suite V4.4

V4.4 fixes the PDF Label Cropper for Amazon in addition to the calibrated Flipkart/E-Kart and Meesho/Valmo templates.

## PDF Label Cropper
- Auto Detect: Amazon / Flipkart / Meesho
- Amazon exact shipping label: keeps the full Amazon label page and skips detected Tax Invoice pages
- Flipkart/E-Kart exact label: calibrated to supplied sample
- Meesho/Valmo exact label: calibrated to supplied sample
- Custom crop, keep pages, 2-up, 4-up
- Amazon image-only shipping pages are detected using the following-page invoice pattern when text extraction is unavailable

The supplied Amazon sample is 2 pages: page 1 is the shipping label and page 2 is the Tax Invoice. V4.4 outputs only the shipping-label page for this format.


## Marketplace Bulk Templates
Amazon and Meesho include the exact user-supplied Saree templates plus CSV exports of their exact upload-field columns. Flipkart is vertical-specific in Seller Hub; the included Flipkart Saree CSV is explicitly a starter/mapping format, not an official upload template.
