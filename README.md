# Honor of Kings Hero Meta Database 🎮

A modern, high-performance web dashboard for tracking **Honor of Kings (HoK)** hero statistics, tiers, and English names. This tool is designed to bridge the gap for global players by providing easy search capabilities using English names alongside official Chinese metrics.

![HOK Dashboard](https://img.shields.io/badge/Status-Active-brightgreen)
![Tech](https://img.shields.io/badge/Tech-Python%20|%20Playwright%20|%20Vanilla%20JS-blue)

## ✨ Key Features

*   **🔍 Easy Search**: Search for heroes using English names or Chinese names. No more guessing who is who!
*   **📊 Live Meta Metrics**: Real-time data on Win Rates, Pick Rates, and Ban Rates.
*   **🏆 Automated Tier List**: Heroes are automatically categorized into Tiers (S, A, B, C, D) based on official popularity data.
*   **📱 Mobile First**: A fully responsive design that transforms into a sleek card layout on mobile devices.
*   **🔗 Shareable Filters**: Filters (search, role, lane, sort) are saved in the URL, allowing you to share specific views with others.
*   **⚡ High Performance**: Asynchronous scraping using Playwright for fast data updates.

## 🛠️ Data Sources & Credits

This project aggregates data from these primary sources:

1.  **[Liquipedia Honor of Kings](https://liquipedia.net/honorofkings/)**: Used to fetch the official English hero names and epithets. Huge thanks to the Liquipedia community for their documentation!
2.  **[Camp HOK (King's Camp)](https://camp.honorofkings.com/h5/app/index.html)**: The official Tencent source for real-time hero data, metrics, and profile details.

## 🚀 Getting Started

### 1. Update the Data (Scraping)
The dashboard relies on `heroes.json`. To refresh the data:
1.  Ensure you have Python installed.
2.  Install dependencies: `pip install playwright`
3.  Install browsers: `playwright install chromium`
4.  Run the unified scraper:
    ```bash
    python scraper_unified.py
    ```

### 2. View the Dashboard
Since the dashboard uses `fetch()` to load the JSON data, it must be served via a local web server (it won't work by just opening the file in a browser due to CORS).

Run this in the project directory:
```bash
python -m http.server 8000
```
Then visit: `http://localhost:8000`

## 📂 Project Structure

*   `scraper_unified.py`: The core engine that scrapes both Liquipedia and Camp HOK concurrently.
*   `index.html`: The main dashboard frontend (HTML/CSS/JS).
*   `heroes.json`: The generated database of hero info.
*   `metadata.json`: Stores the "Last Updated" timestamp.
*   `heroes.csv`: Spreadsheet-friendly export of the hero data.

---
*Created for Honor of Kings players who want a faster, English-friendly way to check the meta.*
