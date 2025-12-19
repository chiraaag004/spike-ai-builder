# Assumptions & Limitations

## 1. Google Analytics 4 (GA4)
* **Data Latency:** The GA4 Standard API (`runReport`) has a processing latency of 24-48 hours. Real-time data is not instantly available via this API.
    * *Mitigation:* For the demo, we use a "Mock Mode" or historical data to demonstrate functionality without waiting for processing.
* **Metric Compatibility:** We assume standard metrics (`activeUsers`, `screenPageViews`) are available. Custom metrics defined in the UI but not the API will cause errors.
    * *Mitigation:* The Agent includes "Smart Retry" logic to fallback to standard metrics if a query fails.

## 2. SEO Data (Screaming Frog / Sheets)
* **Static Export:** The system relies on a pre-exported CSV/Google Sheet. It does not crawl the website in real-time.
* **Column Naming:** We assume standard Screaming Frog column headers (e.g., "Address", "Title 1", "Status Code").
    * *Mitigation:* The `SEOAgent` uses fuzzy matching to detect URL columns even if headers vary slightly.
* **File Size:** The system loads the spreadsheet into memory.
    * *Mitigation:* We enforce a 500-row limit for the Hackathon demo to ensure performance on standard VMs. Production would require database chunking.

## 3. Data Fusion (Tier 3)
* **URL Matching:** We assume the GA4 `pagePath` (e.g., `/blog`) corresponds to the SEO `Address` (e.g., `https://site.com/blog`).
    * *Mitigation:* A robust normalization engine strips protocols (`https://`), domains, and trailing slashes to maximize match rates.