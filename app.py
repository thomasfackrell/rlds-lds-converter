import os
import re
import sqlite3

import streamlit as st

from utils import (
    find_chapter_start_end_ids,
    find_source_verse_id,
    format_ref_range,
    get_full_book_name,
    get_reference_components,
)

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
        v_target.text AS target_text,
        v_target.id AS target_verse_id
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
        v_target.text AS target_text,
        v_target.id AS target_verse_id
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
    """Parses 'Book C:V' format."""
    match = re.match(r'^(.*?)\s*(\d+):(\d+.*)$', ref_string.strip())
    if match:
        book, chapter, verse = match.groups()
        book = get_full_book_name(book)
        return book.strip(), chapter.strip(), verse.strip()
    return None

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


# --- Helper Functions for Quick Jump (Tab 3) ---

def parse_chapter_reference(ref_string):
    """Parses 'Book C' format (e.g., 'Genesis 1', '1 Nephi 3')."""
    match = re.match(r'^(.*?)\s*(\d+)$', ref_string.strip())
    if match:
        book, chapter = match.groups()
        book = get_full_book_name(book)
        return book.strip(), chapter.strip()
    return None

def get_nav_state_from_ref(conn, book, chapter, corpus_id):
    """
    Given a book, chapter, and corpus, finds the correct
    Volume Title, Book Title, and Chapter Number for the dropdowns.
    """
    query = """
    SELECT
        vol.title AS volume_title,
        b.title AS book_title,
        c.chapter_number
    FROM chapter c
    JOIN book b ON c.book_id = b.id
    JOIN volume vol ON b.volume_id = vol.id
    WHERE (UPPER(b.title) = UPPER(?) OR UPPER(b.short_title) = UPPER(?))
      AND c.chapter_number = ?
      AND vol.corpus_id = ?
    """
    try:
        cursor = conn.cursor()
        # Pass book twice, once for title, once for short_title
        cursor.execute(query, (book, book, chapter, corpus_id))
        result = cursor.fetchone()
        return result # Returns a dict-like Row
    except sqlite3.Error:
        return None

def jump_to_chapter():
    """
    Callback function for the Quick Jump button.
    Parses input and sets session_state for the dropdowns.
    """
    corpus_name = st.session_state.jump_corpus
    corpus_id = corpus_ids[corpus_name]
    ref_string = st.session_state.jump_input
    
    parsed = parse_chapter_reference(ref_string)
    if not parsed:
        st.toast(f"Invalid format. Use 'Book Chapter' (e.g., Genesis 1)", icon="❌")
        return
    
    book, chapter = parsed
    nav_state = get_nav_state_from_ref(conn, book, chapter, corpus_id)
    
    if not nav_state:
        st.toast(f"Could not find {book} {chapter} in {corpus_name} corpus.", icon="❌")
        return

    # Set the session state keys for the selectboxes
    st.session_state.nav_corpus = corpus_name
    st.session_state.nav_vol = nav_state['volume_title']
    st.session_state.nav_book = nav_state['book_title']
    st.session_state.nav_chap = str(nav_state['chapter_number'])
    
    # Clear the text input
    st.session_state.jump_input = ""


def swap_corpora():
    """Swaps the source and target corpora in session state."""
    # Simple swap
    old_source = st.session_state.source
    st.session_state.source = st.session_state.target
    st.session_state.target = old_source

@st.cache_data
def get_chapter_verses(_conn, chapter_id):
    """Fetches all verses (as dicts) for a single chapter_id."""
    conn = get_connection(DB_FILE)
    if conn is None: return []
    query = "SELECT verse_number, text FROM verse WHERE chapter_id = ? ORDER BY id"
    try:
        cursor = conn.cursor()
        cursor.execute(query, (chapter_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error:
        return []

@st.cache_data
def get_contiguous_verses(_conn, start_verse_id, end_verse_id):
    """
    Fetches all verse rows (as dicts) between two verse IDs, inclusive,
    joining to get chapter/book info for display headers.
    """
    conn = get_connection(DB_FILE)
    if conn is None: return []
    
    # Ensure start and end are in the correct order
    if start_verse_id > end_verse_id:
        start_verse_id, end_verse_id = end_verse_id, start_verse_id
    
    query = """
    SELECT
        v.verse_number, v.text,
        c.chapter_number,
        b.title AS book_title
    FROM verse v
    JOIN chapter c ON v.chapter_id = c.id
    JOIN book b ON c.book_id = b.id
    WHERE v.id >= ? AND v.id <= ?
    ORDER BY v.id;
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query, (start_verse_id, end_verse_id))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        st.error(f"Database error getting contiguous verses: {e}")
        return []

def get_verse_text_from_id(conn, verse_id):
    """Fetches the text of a single verse by its ID."""
    query = "SELECT text FROM verse WHERE id = ?"
    try:
        cursor = conn.cursor()
        cursor.execute(query, (verse_id,))
        result = cursor.fetchone()
        return result['text'] if result else None
    except sqlite3.Error:
        return None

@st.cache_data
def get_chapter_boundaries(_conn, chapter_id):
    """Finds the first and last verse.id for a given chapter_id."""
    conn = get_connection(DB_FILE)
    if conn is None: return None, None
    query = "SELECT MIN(id) AS first_id, MAX(id) AS last_id FROM verse WHERE chapter_id = ?"
    try:
        cursor = conn.cursor()
        cursor.execute(query, (chapter_id,))
        result = cursor.fetchone()
        if result and result['first_id'] and result['last_id']:
            return result['first_id'], result['last_id']
        return None, None
    except sqlite3.Error:
        return None, None

# --- Main Streamlit App UI ---

# 1. Initialize the session state variable
if 'show_alert' not in st.session_state:
    st.session_state.show_alert = True

# 2. Callback function to update the state
def dismiss_alert():
    st.session_state.show_alert = False

# 3. Check the state. If True, display the alert.
if st.session_state.show_alert:
    # Use columns to place the button neatly
    col1, col2 = st.columns([0.85, 0.15]) 
    with col1:
        st.info("🔄 **For the best experience on mobile,** please rotate your device to landscape mode.", icon="ℹ️")
    with col2:
        # Pass the callback to the button's on_click
        st.button("Dismiss", on_click=dismiss_alert, key="dismiss_alert_btn", use_container_width=True)

# --- END OF ALERT ---
# --- END OF ROTATION ALERT ---

# ... rest of your app code ...
st.set_page_config(page_title="RLDS/LDS Converter", page_icon="📖", layout="centered")
st.title("📖 RLDS / LDS Scripture Converter")
st.write("Convert scripture references between LDS and RLDS (Restorationist) canons.")

# --- Initialize session state for the converter ---
if 'source' not in st.session_state:
    st.session_state.source = 'RLDS'
if 'target' not in st.session_state:
    st.session_state.target = 'LDS'

# --- Global Setup (DB Connection and Corpus IDs) ---
if not os.path.exists(DB_FILE):
    st.error(f"Database file '{DB_FILE}' not found! Please add it to the app's root directory.")
    st.stop()
conn = get_connection(DB_FILE)
if conn is None: st.stop()
corpus_ids = get_corpus_ids(conn)
if corpus_ids is None: st.stop()

# --- Tabbed Interface (REMOVED TAB 4) ---
tab1, tab2, tab3 = st.tabs(["Converter", "Chapter Explorer", "More Resources"])

# --- TAB 1: Verse Converter ---
with tab1:
    st.header("Chapter/Verse Converter")
    st.write("Convert a single verse (e.g., 1 Nephi 1:1) or a full chapter (e.g., Gen 1).")
    
    # --- "Google Translate" UI (OUTSIDE THE FORM) ---
    col1, col2, col3 = st.columns([0.4, 0.2, 0.4], gap="small", vertical_alignment="center")
    
    with col1:
        st.markdown(f"<h3 style='text-align: right; font-weight: 400;'>From: {st.session_state.source}</h3>", unsafe_allow_html=True)
    with col2:
        st.button("⇆", on_click=swap_corpora, use_container_width=True, help="Swap corpora")
    with col3:
        st.markdown(f"<h3 style='text-align: left; font-weight: 400;'>To: {st.session_state.target}</h3>", unsafe_allow_html=True)
    
    # --- THE FORM ---
    with st.form(key="converter_form"):
        ref_input = st.text_input("Enter reference", placeholder="e.g., 1 Nephi 3:7 or Gen 1", label_visibility="collapsed")
        submit_button = st.form_submit_button(label="Convert", use_container_width=True)

    # --- NEW LOGIC ---
    if submit_button and ref_input:
        with st.spinner("Looking up reference..."):
            source_corpus_name = st.session_state.source
            target_corpus_name = st.session_state.target
            source_corpus_id = corpus_ids[source_corpus_name]
            target_corpus_id = corpus_ids[target_corpus_name]
            
            # --- BRANCH: Is it a verse or a chapter? ---
            if ":" in ref_input:
                # --- 1. HANDLE VERSE CONVERSION ---
                parsed_ref = parse_reference(ref_input)
                if not parsed_ref:
                    st.error("Invalid format. Please use 'Book Chapter:Verse' (e.g., Genesis 1:1).")
                else:
                    book, chapter, verse = parsed_ref
                    ref_input = f"{book} {chapter}:{verse}"
                    source_id, source_text = find_source_verse_id(conn, book, chapter, verse, source_corpus_id)
                    
                    if not source_id:
                        st.warning(f"Could not find **{book} {chapter}:{verse}** in the **{source_corpus_name}** canon.")
                    else:
                        target_id = find_target_verse_id(conn, source_id)
                        
                        if not target_id:
                            st.info(f"**{ref_input}** was found, but no cross-reference exists.")
                            st.divider()
                            # Show text in columns (Source only)
                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.subheader(f"{source_corpus_name}: {ref_input}")
                                st.markdown(f"**{verse}** {source_text.replace('\\n', '<br>')}", unsafe_allow_html=True)
                            with col_b:
                                st.subheader(f"{target_corpus_name}: (No Cross-Reference)")
                        else:
                            target_ref = get_reference_from_id(conn, target_id, target_corpus_id)
                            target_text = get_verse_text_from_id(conn, target_id)
                            
                            if not target_ref or target_text is None:
                                st.error("Found a cross-reference, but could not reconstruct the target reference or text.")
                            else:
                                st.divider()
                                
                                # Show text in columns
                                col_a, col_b = st.columns(2)
                                with col_a:
                                    st.subheader(f"{source_corpus_name}: {ref_input}")
                                    st.markdown(f"**{verse}** {source_text.replace('\\n', '<br>')}", unsafe_allow_html=True) # <-- FIX
                                with col_b:
                                    st.subheader(f"{target_corpus_name}: {target_ref}")
                                    target_verse_num = target_ref.split(":")[-1]
                                    st.markdown(f"**{target_verse_num}** {target_text.replace('\\n', '<br>')}", unsafe_allow_html=True)
            
            else:
                # --- 2. HANDLE CHAPTER CONVERSION ---
                parsed_ref = parse_chapter_reference(ref_input)
                if not parsed_ref:
                    st.error("Invalid format. Use 'Book Chapter' (e.g., Genesis 1). No colon was found.")
                else:
                    book, chapter = parsed_ref
                    ref_input = f"{book} {chapter}"
                    
                    source_chapter_id, source_first_verse_id, source_last_verse_id = find_chapter_start_end_ids(conn, book, chapter, source_corpus_id)

                    
                    if not source_chapter_id:
                        st.warning(f"Could not find **{book} {chapter}** in the **{source_corpus_name}** canon.")
                    else:
                        # --- SOURCE WAS FOUND ---
                        # Get source verses immediately
                        source_verses = get_chapter_verses(conn, source_chapter_id)
                        
                        # Now, check for target
                        target_first_verse_id = find_target_verse_id(conn, source_first_verse_id)
                        target_last_verse_id = find_target_verse_id(conn, source_last_verse_id)
                        
                        col_a, col_b = st.columns(2)

                        # Display Source Column (Always)
                        with col_a:
                            st.subheader(f"{source_corpus_name}: {book} {chapter}")
                            for verse in source_verses:
                                st.markdown(f"**{verse['verse_number']}** {verse['text'].replace('\\n', '<br>')}", unsafe_allow_html=True)

                        # Display Target Column (Conditional)
                        with col_b:
                            if not target_first_verse_id or not target_last_verse_id:
                                st.subheader(f"{target_corpus_name}: (No Cross-Reference)")
                            else:
                                start_comps = get_reference_components(conn, target_first_verse_id, target_corpus_id)
                                end_comps = get_reference_components(conn, target_last_verse_id, target_corpus_id)
                                
                                if not start_comps or not end_comps:
                                    st.error("Found cross-references, but could not reconstruct the target references.")
                                else:
                                    target_ref_range = format_ref_range(start_comps, end_comps)
                                    
                                    
                                    st.subheader(f"{target_corpus_name}: {target_ref_range}")
                                    target_verses = get_contiguous_verses(conn, target_first_verse_id, target_last_verse_id)
                                    
                                    last_target_book_chap = None
                                    for verse in target_verses:
                                        current_target_book_chap = f"{verse['book_title']} {verse['chapter_number']}"
                                        if current_target_book_chap != last_target_book_chap:
                                            st.markdown(f"### {current_target_book_chap}")
                                            last_target_book_chap = current_target_book_chap
                                        
                                        st.markdown(f"**{verse['verse_number']}** {verse['text'].replace('\\n', '<br>')}", unsafe_allow_html=True)
                        
                        # We need a divider *after* the success messages and *before* the columns
                        st.divider()
                      

    elif submit_button:
        st.warning("Please enter a scripture reference.")


# --- TAB 2: Chapter Explorer ---
with tab2:
    st.header("Chapter Explorer & Side-by-Side Reader")
    st.write("Navigate by corpus, volume, book, and chapter.")#, or use the 'Quick Jump' to go directly to a chapter.")

    st.subheader("Browse")
    nav_cols = st.columns(4)
    with nav_cols[0]:
        corpus_select_nav = st.selectbox("Corpus", ('LDS', 'RLDS'), key="nav_corpus")
        corpus_id_nav = corpus_ids[corpus_select_nav]
        target_corpus_name_nav = 'RLDS' if corpus_select_nav == 'LDS' else 'LDS'
        # Get target_corpus_id, we'll need it for the helpers
        target_corpus_id_nav = corpus_ids[target_corpus_name_nav]


    with nav_cols[1]:
        volumes_list = get_volumes_for_corpus(conn, corpus_id_nav)
        if not volumes_list:
            st.warning("No volumes found.")
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
                st.warning("No books found.")
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
                st.warning("No chapters found.")
                selected_chapter_id = None
                selected_chapter_num = None
            else:
                chapter_dict = {f"{ch['chapter_number']}": ch['id'] for ch in chapters_list}
                selected_chapter_num = st.selectbox("Chapter", chapter_dict.keys(), key="nav_chap")
                selected_chapter_id = chapter_dict.get(selected_chapter_num)

    st.divider()

    # --- Display Chapter Text (NEW LOGIC) ---
    if selected_chapter_id and selected_book_title and selected_chapter_num:
        
        read_col_nav_1, read_col_nav_2 = st.columns(2)
        
        # 1. Get and display source chapter text (Left Column)
        with read_col_nav_1:
            st.subheader(f"{corpus_select_nav}: {selected_book_title} {selected_chapter_num}")
            source_verses = get_chapter_verses(conn, selected_chapter_id)
            if not source_verses:
                st.warning("No text found for this chapter.")
            else:
                for verse in source_verses:
                    st.markdown(f"**{verse['verse_number']}** {verse['text'].replace('\\n', '<br>')}", unsafe_allow_html=True)

        # 2. Get and display target contiguous block (Right Column)
        with read_col_nav_2:
            # Find boundaries of the source chapter
            source_first_verse_id, source_last_verse_id = get_chapter_boundaries(conn, selected_chapter_id)
            
            if not source_first_verse_id:
                st.subheader(f"{target_corpus_name_nav} (Cross-References)")
                st.info("Source chapter is empty or not found.")
            else:
                # Find target IDs for the first and last verse
                target_first_verse_id = find_target_verse_id(conn, source_first_verse_id)
                target_last_verse_id = find_target_verse_id(conn, source_last_verse_id)
                
                if not target_first_verse_id or not target_last_verse_id:
                    st.subheader(f"{target_corpus_name_nav} (Cross-References)")
                    st.info("A complete cross-reference (start and end) was not found for this chapter.")
                else:
                    # We have a valid range. Get components to build the header.
                    start_comps = get_reference_components(conn, target_first_verse_id, target_corpus_id_nav)
                    end_comps = get_reference_components(conn, target_last_verse_id, target_corpus_id_nav)
                    
                    if not start_comps or not end_comps:
                        st.subheader(f"{target_corpus_name_nav} (Cross-References)")
                        st.error("Found cross-references, but could not reconstruct the target references.")
                    else:
                        # Format the range and set the subheader
                        target_ref_range = format_ref_range(start_comps, end_comps)
                        st.subheader(f"{target_corpus_name_nav}: {target_ref_range}")
                        
                        # Get the contiguous block of verses
                        target_verses = get_contiguous_verses(conn, target_first_verse_id, target_last_verse_id)
                        
                        last_target_book_chap = None
                        for verse in target_verses:
                            current_target_book_chap = f"{verse['book_title']} {verse['chapter_number']}"
                            if current_target_book_chap != last_target_book_chap:
                                st.markdown(f"### {current_target_book_chap}")
                                last_target_book_chap = current_target_book_chap
                            
                            st.markdown(f"**{verse['verse_number']}** {verse['text'].replace('\\n', '<br>')}", unsafe_allow_html=True)

with tab3:
    st.header("More Study Resources")

    # Use st.html() to bypass the Markdown parser
    
    st.subheader("Scripture Study Tools")
    st.html("""
    <ul>
      <li><a href="https://scripturetoolbox.com/html/ic/index.html" target="_blank" rel="noopener noreferrer">
          <strong>Joseph Smith's Inspired Version (IV/JST) Inline Viewer</strong>
          </a><br>
          An inline difference viewer for the KJV Bible and Joseph Smith's Inspired Version, letting you see the edits.
      </li>
      <li><a href="https://study.zionbound.com/" target="_blank" rel="noopener noreferrer">
          <strong>ZionBound (RLDS Study App)</strong>
          </a><br>
          An RLDS scripture search and study web app.
      </li>
    </ul>
    """)

    st.subheader("Historical Documents & Resources")
    st.html("""
    <ul>
      <li><a href="https://latterdaytruth.org/" target="_blank" rel="noopener noreferrer">
          <strong>Latter Day Truth</strong>
          </a><br>
          An archive of many scanned RLDS church history documents and periodicals.
      </li>
      <li><a href="https://www.centerplace.org/" target="_blank" rel="noopener noreferrer">
          <strong>CenterPlace.org</strong>
          </a><br>
          A large library of resources. The search bar at the top is very useful for finding materials.
      </li>
    </ul>
    """)

    st.subheader("Literature & Scriptures")
    st.html("""
    <ul>
      <li><a href="https://restorationbookstore.org/" target="_blank" rel="noopener noreferrer">
          <strong>Restoration Bookstore</strong>
          </a><br>
          A marketplace for traditional RLDS literature and scriptures.
      </li>
      <li><a href="https://restorationscriptures.blogspot.com/" target="_blank" "rel="noopener noreferrer">
          <strong>Restoration Scriptures Blog</strong>
          </a><br>
          Where you can purchase a 3-in-1 fully bound traditional RLDS scripture set.
      </li>
    </ul>
    """)

    st.subheader("Community & Media")
    st.html("""
    <ul>
      <li><a href="https://www.southcrysler.org/" target="_blank" rel="noopener noreferrer">
          <strong>South Crysler Restoration Branch</strong>
          </a><br>
          A local restoration branch that livestreams services. Check out the "For LDS Friends" and "Sermons" pages.
      </li>
      <li><a href="https://www.youtube.com/@AcrosstheRestoration1830" target="_blank" rel="noopener noreferrer">
          <strong>Across the Restoration (YouTube)</strong>
          </a><br>
          An up-and-coming channel for learning more about RLDS and Restoration Branches.
      </li>
    </ul>
    """)