import os
import re
import sqlite3

import streamlit as st

# --- Database Setup ---

DB_FILE = "scriptures.db"

@st.cache_resource
def get_connection(db_path):
    """Establishes and caches a connection to the SQLite database."""
    try:
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row # Access columns by name
        return conn
    except sqlite3.Error as e:
        st.error(f"Error connecting to database '{db_path}': {e}")
        return None

@st.cache_data
def get_corpus_ids(_conn):
    """Fetches and caches the corpus IDs for 'LDS' and 'RLDS'."""
    conn = get_connection(DB_FILE)
    if conn is None: return None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, short_name FROM corpus WHERE short_name IN ('LDS', 'RLDS')")
        rows = cursor.fetchall()
        ids = {row['short_name']: row['id'] for row in rows}
        if 'LDS' not in ids or 'RLDS' not in ids:
            st.error("Database 'corpus' table must contain 'LDS' and 'RLDS' entries.")
            return None
        return ids
    except sqlite3.Error as e:
        st.error(f"Error fetching corpus IDs: {e}")
        return None

# --- Data Functions for Tab 2 (Full Book Comparator) ---

@st.cache_data
def get_books_for_corpus(_conn, corpus_id):
    """Fetches all book titles for a given corpus."""
    conn = get_connection(DB_FILE)
    if conn is None: return []
    query = """
    SELECT b.title
    FROM book b
    JOIN volume v ON b.volume_id = v.id
    WHERE v.corpus_id = ?
    ORDER BY b.id;
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query, (corpus_id,))
        rows = cursor.fetchall()
        return [row['title'] for row in rows]
    except sqlite3.Error as e:
        st.error(f"Error fetching books: {e}")
        return []

@st.cache_data
def get_full_book_comparison(_conn, source_corpus_id, book_title):
    """Fetches the side-by-side data for an entire book."""
    conn = get_connection(DB_FILE)
    if conn is None: return []
    query = """
    SELECT
        c_source.chapter_number AS source_chapter,
        v_source.verse_number AS source_verse,
        v_source.text AS source_text,
        b_target.title AS target_book,
        c_target.chapter_number AS target_chapter,
        v_target.verse_number AS target_verse,
        v_target.text AS target_text
    FROM verse AS v_source
    JOIN chapter AS c_source ON v_source.chapter_id = c_source.id
    JOIN book AS b_source ON c_source.book_id = b_source.id
    JOIN volume AS vol_source ON b_source.volume_id = vol_source.id
    LEFT JOIN cross_reference AS cr ON v_source.id = cr.verse_id
    LEFT JOIN verse AS v_target ON cr.cross_ref_verse_id = v_target.id
    LEFT JOIN chapter AS c_target ON v_target.chapter_id = c_target.id
    LEFT JOIN book AS b_target ON c_target.book_id = b_target.id
    WHERE vol_source.corpus_id = ?
      AND b_source.title = ?
    ORDER BY v_source.id;
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query, (source_corpus_id, book_title))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        st.error(f"Database error getting comparison: {e}")
        return []

# --- Data Functions for Tab 3 (Chapter Explorer) ---

@st.cache_data
def get_volumes_for_corpus(_conn, corpus_id):
    """Fetches all volumes for a given corpus."""
    conn = get_connection(DB_FILE)
    if conn is None: return []
    query = "SELECT id, title FROM volume WHERE corpus_id = ? ORDER BY id"
    try:
        cursor = conn.cursor()
        cursor.execute(query, (corpus_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        st.error(f"Error fetching volumes: {e}")
        return []

@st.cache_data
def get_books_for_volume(_conn, volume_id):
    """Fetches all books for a given volume."""
    conn = get_connection(DB_FILE)
    if conn is None: return []
    query = "SELECT id, title FROM book WHERE volume_id = ? ORDER BY id"
    try:
        cursor = conn.cursor()
        cursor.execute(query, (volume_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        st.error(f"Error fetching books: {e}")
        return []

@st.cache_data
def get_chapters_for_book(_conn, book_id):
    """Fetches all chapters for a given book."""
    conn = get_connection(DB_FILE)
    if conn is None: return []
    query = "SELECT id, chapter_number FROM chapter WHERE book_id = ? ORDER BY chapter_number"
    try:
        cursor = conn.cursor()
        cursor.execute(query, (book_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        st.error(f"Error fetching chapters: {e}")
        return []

@st.cache_data
def get_chapter_comparison_data(_conn, source_chapter_id):
    """
    Fetches the side-by-side comparison data for a single chapter.
    """
    conn = get_connection(DB_FILE)
    if conn is None: return []
    query = """
    SELECT
        v_source.verse_number AS source_verse,
        v_source.text AS source_text,
        b_target.title AS target_book,
        c_target.chapter_number AS target_chapter,
        v_target.verse_number AS target_verse,
        v_target.text AS target_text
    FROM verse AS v_source
    LEFT JOIN cross_reference AS cr ON v_source.id = cr.verse_id
    LEFT JOIN verse AS v_target ON cr.cross_ref_verse_id = v_target.id
    LEFT JOIN chapter AS c_target ON v_target.chapter_id = c_target.id
    LEFT JOIN book AS b_target ON c_target.book_id = b_target.id
    WHERE v_source.chapter_id = ?
    ORDER BY v_source.id;
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query, (source_chapter_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        st.error(f"Database error getting chapter comparison: {e}")
        return []


# --- Data Functions for Tab 1 (Verse Converter) ---

def parse_reference(ref_string):
    """Parses a scripture reference string into (book, chapter, verse)."""
    match = re.match(r'^(.*?)\s*(\d+):(\d+.*)$', ref_string.strip())
    if match:
        book, chapter, verse = match.groups()
        return book.strip(), chapter.strip(), verse.strip()
    return None

def find_source_verse_id(conn, book, chapter, verse, corpus_id):
    """Finds the verse_id from the source corpus."""
    query = """
    SELECT v.id
    FROM verse v
    JOIN chapter c ON v.chapter_id = c.id
    JOIN book b ON c.book_id = b.id
    JOIN volume vol ON b.volume_id = vol.id
    WHERE (b.title = ? OR b.short_title = ?)
      AND c.chapter_number = ?
      AND v.verse_number = ?
      AND vol.corpus_id = ?
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query, (book, book, chapter, verse, corpus_id))
        result = cursor.fetchone()
        return result['id'] if result else None
    except sqlite3.Error: return None

def find_target_verse_id(conn, source_verse_id):
    """Finds the corresponding target verse_id."""
    query = "SELECT cross_ref_verse_id FROM cross_reference WHERE verse_id = ?"
    try:
        cursor = conn.cursor()
        cursor.execute(query, (source_verse_id,))
        result = cursor.fetchone()
        return result['cross_ref_verse_id'] if result else None
    except sqlite3.Error: return None

def get_reference_from_id(conn, target_verse_id, target_corpus_id):
    """Reconstructs the scripture reference string from a target verse_id."""
    query = """
    SELECT b.title, c.chapter_number, v.verse_number
    FROM verse v
    JOIN chapter c ON v.chapter_id = c.id
    JOIN book b ON c.book_id = b.id
    JOIN volume vol ON b.volume_id = vol.id
    WHERE v.id = ? AND vol.corpus_id = ?
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query, (target_verse_id, target_corpus_id))
        result = cursor.fetchone()
        if result:
            return f"{result['title']} {result['chapter_number']}:{result['verse_number']}"
        return None
    except sqlite3.Error: return None

# --- Main Streamlit App UI ---

st.set_page_config(page_title="Scripture Tool", layout="wide")
st.title("✝️ LDS / RLDS Scripture Comparison Tool")

# --- Global Setup (DB Connection and Corpus IDs) ---
if not os.path.exists(DB_FILE):
    st.error(f"Database file '{DB_FILE}' not found! Please add it to the app's root directory.")
    st.stop()
conn = get_connection(DB_FILE)
if conn is None: st.stop()
corpus_ids = get_corpus_ids(conn)
if corpus_ids is None: st.stop()

# --- Tabbed Interface ---
tab1, tab2, tab3, tab4 = st.tabs(["Verse Converter", "Full Book Comparator", "Chapter Explorer", "Useful Links"])

# --- TAB 1: Verse Converter ---
with tab1:
    st.header("Single Verse Converter")
    st.write("Convert a single scripture reference between LDS and RLDS (Community of Christ) canons.")
    
    with st.form(key="converter_form"):
        ref_input = st.text_input("Enter scripture reference", placeholder="e.g., 1 Nephi 3:7 or Genesis 1:1")
        source_corpus_name = st.radio("Select the source:", ('LDS', 'RLDS'), horizontal=True)
        submit_button = st.form_submit_button(label="Convert")

    if submit_button and ref_input:
        with st.spinner("Looking up reference..."):
            parsed_ref = parse_reference(ref_input)
            if not parsed_ref:
                st.error("Invalid format. Please use 'Book Chapter:Verse' (e.g., Genesis 1:1).")
            else:
                book, chapter, verse = parsed_ref
                target_corpus_name = 'RLDS' if source_corpus_name == 'LDS' else 'LDS'
                source_corpus_id = corpus_ids[source_corpus_name]
                target_corpus_id = corpus_ids[target_corpus_name]

                source_id = find_source_verse_id(conn, book, chapter, verse, source_corpus_id)
                if not source_id:
                    st.warning(f"Could not find **{ref_input}** in the **{source_corpus_name}** canon.")
                else:
                    target_id = find_target_verse_id(conn, source_id)
                    if not target_id:
                        st.info(f"**{ref_input}** was found, but no cross-reference exists.")
                    else:
                        target_ref = get_reference_from_id(conn, target_id, target_corpus_id)
                        if not target_ref:
                            st.error("Found a cross-reference, but could not reconstruct the target reference.")
                        else:
                            st.success(f"**{source_corpus_name}**: {ref_input}")
                            st.success(f"**{target_corpus_name}**: {target_ref}")
    elif submit_button:
        st.warning("Please enter a scripture reference.")

# --- TAB 2: Full Book Comparator ---
with tab2:
    st.header("Full Book Comparator")
    st.write("See a side-by-side comparison of an entire book.")

    col1, col2 = st.columns(2)
    with col1:
        source_corpus_select_book = st.selectbox("Select Source Corpus", ('LDS', 'RLDS'), key="book_source_corpus")
    source_corpus_id_book = corpus_ids[source_corpus_select_book]
    target_corpus_name_book = 'RLDS' if source_corpus_select_book == 'LDS' else 'LDS'
    
    books_list = get_books_for_corpus(conn, source_corpus_id_book)
    with col2:
        if not books_list:
            st.warning(f"No books found for {source_corpus_select_book} corpus.")
            selected_book = None
        else:
            selected_book = st.selectbox("Select Book", books_list, key="book_book")

    if selected_book and st.button("Load Book Comparison", key="load_book"):
        with st.spinner(f"Loading {selected_book}..."):
            comparison_data = get_full_book_comparison(conn, source_corpus_id_book, selected_book)
            if not comparison_data:
                st.info(f"No data found for {selected_book}.")
            else:
                st.divider()
                read_col1, read_col2 = st.columns(2)
                with read_col1: st.subheader(f"{source_corpus_select_book}: {selected_book}")
                with read_col2: st.subheader(f"{target_corpus_name_book} (Cross-References)")
                
                last_source_chapter = None
                last_target_ref = None
                
                for row in comparison_data:
                    with read_col1:
                        if row['source_chapter'] != last_source_chapter:
                            st.markdown(f"### Chapter {row['source_chapter']}")
                            last_source_chapter = row['source_chapter']
                        st.markdown(f"**{row['source_verse']}** {row['source_text']}", unsafe_allow_html=True)
                    
                    with read_col2:
                        if row['target_book']:
                            current_target_ref = f"{row['target_book']} {row['target_chapter']}"
                            if current_target_ref != last_target_ref:
                                if last_target_ref is not None:
                                    st.markdown("---")
                                st.markdown(f"### {current_target_ref}")
                                last_target_ref = current_target_ref
                            
                            st.markdown(f"**{row['target_verse']}** {row['target_text']}", unsafe_allow_html=True)
                        else:
                            st.markdown(f"**{row['source_verse']}** - *No cross-reference*")

# --- TAB 3: Chapter Explorer ---
with tab3:
    st.header("Chapter Explorer & Side-by-Side Reader")
    st.write("Navigate by corpus, volume, book, and chapter to read the text side-by-side with its counterpart.")

    # --- Navigation Dropdowns ---
    nav_cols = st.columns(4)
    with nav_cols[0]:
        corpus_select_nav = st.selectbox("Corpus", ('LDS', 'RLDS'), key="nav_corpus")
        corpus_id_nav = corpus_ids[corpus_select_nav]
        target_corpus_name_nav = 'RLDS' if corpus_select_nav == 'LDS' else 'LDS'

    with nav_cols[1]:
        volumes_list = get_volumes_for_corpus(conn, corpus_id_nav)
        if not volumes_list:
            st.warning("No volumes found for this corpus.")
            selected_volume_id = None
        else:
            volume_dict = {vol['title']: vol['id'] for vol in volumes_list}
            selected_volume_title = st.selectbox("Volume", volume_dict.keys(), key="nav_vol")
            selected_volume_id = volume_dict.get(selected_volume_title)

    with nav_cols[2]:
        if not selected_volume_id:
            st.selectbox("Book", [], key="nav_book", disabled=True)
            selected_book_id = None
            selected_book_title = None
        else:
            books_list_nav = get_books_for_volume(conn, selected_volume_id)
            if not books_list_nav:
                st.warning("No books found for this volume.")
                selected_book_id = None
                selected_book_title = None
            else:
                book_dict_nav = {book['title']: book['id'] for book in books_list_nav}
                selected_book_title = st.selectbox("Book", book_dict_nav.keys(), key="nav_book")
                selected_book_id = book_dict_nav.get(selected_book_title)

    with nav_cols[3]:
        if not selected_book_id:
            st.selectbox("Chapter", [], key="nav_chap", disabled=True)
            selected_chapter_id = None
            selected_chapter_num = None
        else:
            chapters_list = get_chapters_for_book(conn, selected_book_id)
            if not chapters_list:
                st.warning("No chapters found for this book.")
                selected_chapter_id = None
                selected_chapter_num = None
            else:
                chapter_dict = {f"{ch['chapter_number']}": ch['id'] for ch in chapters_list}
                selected_chapter_num = st.selectbox("Chapter", chapter_dict.keys(), key="nav_chap")
                selected_chapter_id = chapter_dict.get(selected_chapter_num)

    st.divider()

    # --- Display Chapter Text ---
    if selected_chapter_id and selected_book_title and selected_chapter_num:
        chapter_data = get_chapter_comparison_data(conn, selected_chapter_id)
        
        read_col_nav_1, read_col_nav_2 = st.columns(2)
        
        with read_col_nav_1:
            st.subheader(f"{corpus_select_nav}: {selected_book_title} {selected_chapter_num}")
            for row in chapter_data:
                st.markdown(f"**{row['source_verse']}** {row['source_text']}", unsafe_allow_html=True)

        with read_col_nav_2:
            st.subheader(f"{target_corpus_name_nav} (Cross-References)")
            last_target_ref_nav = None
            for row in chapter_data:
                if row['target_book']:
                    current_target_ref_nav = f"{row['target_book']} {row['target_chapter']}"
                    if current_target_ref_nav != last_target_ref_nav:
                        if last_target_ref_nav is not None:
                            st.markdown("---")
                        st.markdown(f"### {current_target_ref_nav}")
                        last_target_ref_nav = current_target_ref_nav
                    st.markdown(f"**{row['target_verse']}** {row['target_text']}", unsafe_allow_html=True)
                else:
                    st.markdown(f"**{row['source_verse']}** - *No cross-reference*")

# --- TAB 4: Useful Links ---
with tab4:
    st.header("Useful Links")

    st.subheader("Scripture Study Tools")
    st.markdown("""
    * [**Joseph Smith's Inspired Version (JST) Inline Viewer**](https://scripturetoolbox.com/html/ic/index.html)  
        An inline difference viewer for the KJV Bible and Joseph Smith's Inspired Version, letting you see the edits.
    * [**ZionBound (RLDS Study App)**](https://study.zionbound.com/)  
        An RLDS scripture search and study web app.
    """)

    st.subheader("Historical Documents & Resources")
    st.markdown("""
    * [**Latter Day Truth**](https://latterdaytruth.org/)  
        An archive of many scanned RLDS church history documents and periodicals.
    * [**CenterPlace**](https://www.centerplace.org/)  
        A large library of resources. The search bar at the top is very useful for finding materials.
    """)

    st.subheader("Literature & Scriptures")
    st.markdown("""
    * [**Restoration Bookstore**](https://restorationbookstore.org/)  
        A marketplace for traditional RLDS literature and scriptures.
    * [**Restoration Scriptures Blog**](https://restorationscriptures.blogspot.com/)  
        Where you can purchase a 3-in-1 fully bound traditional RLDS scripture set.
    """)

    st.subheader("Community & Media")
    st.markdown("""
    * [**South Crysler Restoration Branch**](https://www.southcrysler.org/)  
        A local restoration branch that livestreams services. Check out the "for-lds-friends" and "sermons" pages.
    * [**Across the Restoration (YouTube)**](https://www.youtube.com/@AcrosstheRestoration1830)  
        An up-and-coming channel for learning more about RLDS and Restoration Branches.
    """)