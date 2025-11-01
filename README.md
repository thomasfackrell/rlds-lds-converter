# RLDS / LDS Scripture Comparison Tool

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://rlds-lds-converter.streamlit.app/)

A Streamlit web app for comparing scripture references, chapters, and entire books between the RLDS (Restorationist) and LDS (Latter-day Saint) canons.

## ✨ Core Features

* **Verse Converter:** Convert a single scripture reference (e.g., `1 Nephi 3:7` or `Genesis 1:1`) from one canon to the other.
* **Chapter Explorer:** A full, side-by-side scripture reader. Navigate by Corpus &rarr; Volume &rarr; Book &rarr; Chapter to read the full text and see its exact cross-referenced counterpart.
* **Full Book Comparator:** Load an entire book (e.g., *Book of Alma*) and scroll through a complete, verse-by-verse comparison to easily visualize chapter and verse differences.
* **Useful Links:** A curated list of links to external resources for scripture study and historical research, primarily for RLDS / Restoration-focused materials.

## 🗃️ Data Source

This app runs entirely on a self-contained SQLite database (`scriptures.db`). This file contains all scripture texts for both the LDS and RLDS corpora, as well as the crucial `cross_reference` table that links them verse by verse.

All database logic is handled by standard `sqlite3` queries within the `app.py` file.

## 🚀 How to Run Locally

To run this app on your local machine:

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/thomasfackrell/rlds-lds-converter.git
    cd rlds-lds-converter
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    # On macOS/Linux
    python3 -m venv .venv
    source .venv/bin/activate

    # On Windows
    python -m venv .venv
    .\.venv\Scripts\activate
    ```

3.  **Install the requirements:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the app:**
    ```bash
    streamlit run app.py
    ```
    Your browser should automatically open to the app.

## 📁 Project Structure
```
rlds-lds-converter/
├── app.py           # The main Streamlit application
├── requirements.txt # Python dependencies (just streamlit)
├── scripture.db     # The complete SQLite database
└── README.md
```