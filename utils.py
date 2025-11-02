import sqlite3


def get_full_book_name(abbreviation: str) -> str | None:
    """
    Converts an LDS scripture book abbreviation to its full, formal name.

    This function is case-insensitive and handles common variations
    for all books in the Standard Works (Old Testament, New Testament,
    Book of Mormon, Doctrine and Covenants, and Pearl of Great Price).

    Args:
        abbreviation: The scripture book abbreviation (e.g., "Gen", "ne", "D&C").

    Returns:
        The full book name (e.g., "Genesis", "1 Nephi") or None if
        the abbreviation is not found.
    """
    
    # We process the input to be consistent: lowercase and no periods or spaces.
    # This allows one dictionary key to match many variations.
    # e.g., "1 Ne.", "1 ne", "1ne", "1 Ne" all become "1ne"
    # We make an exception for "D&C" and "JS-H" style abbreviations.
    
    if abbreviation.upper() in ["D&C", "D. AND C."]:
        processed_key = "d&c"
    elif "JS-M" in abbreviation.upper():
        processed_key = "js-m"
    elif "JS-H" in abbreviation.upper():
        processed_key = "js-h"
    elif "W OF M" in abbreviation.upper():
        processed_key = "w of m"
    elif "A OF F" in abbreviation.upper():
        processed_key = "a of f"
    else:
        # Standard processing for most books
        processed_key = abbreviation.lower().replace('.', '').replace(' ', '')
        # Standardize numbers (e.g., "1st" -> "1", "first" -> "1")
        processed_key = processed_key.replace('1st', '1').replace('first', '1')
        processed_key = processed_key.replace('2nd', '2').replace('second', '2')
        processed_key = processed_key.replace('3rd', '3').replace('third', '3')
        processed_key = processed_key.replace('4th', '4').replace('fourth', '4')

    # Master dictionary mapping processed keys to full names
    scripture_map = {
        # --- Book of Mormon ---
        '1ne': '1 Nephi',
        '1nephi': '1 Nephi',
        'nephi1': '1 Nephi',
        '2ne': '2 Nephi',
        '2nephi': '2 Nephi',
        'nephi2': '2 Nephi',
        '3ne': '3 Nephi',
        '3nephi': '3 Nephi',
        'nephi3': '3 Nephi',
        '4ne': '4 Nephi',
        '4nephi': '4 Nephi',
        'nephi4': '4 Nephi',
        'jac': 'Jacob',
        'jacob': 'Jacob',
        'enos': 'Enos',
        'jar': 'Jarom',
        'jarom': 'Jarom',
        'omni': 'Omni',
        'wofm': 'Words of Mormon',
        'wordsofmormon': 'Words of Mormon',
        'w of m': 'Words of Mormon',
        'mos': 'Mosiah',
        'mosiah': 'Mosiah',
        'alma': 'Alma',
        'hel': 'Helaman',
        'helaman': 'Helaman',
        'morm': 'Mormon',
        'mormon': 'Mormon',
        'eth': 'Ether',
        'ether': 'Ether',
        'moro': 'Moroni',
        'mor': 'Moroni',
        'mni': 'Moroni',
        'moroni': 'Moroni',
        'ne': '1 Nephi',  # Ambiguous "ne" defaults to "1 Nephi" as requested
        
        # --- Doctrine and Covenants ---
        'd&c': 'Doctrine and Covenants',
        'dc': 'Doctrine and Covenants',
        'od': 'Official Declaration',
        'od1': 'Official Declaration 1',
        'od2': 'Official Declaration 2',
        'lof': 'Lecture',
        'lecturesonfaith': 'Lecture',
        'lecture': 'Lecture',
        'lec': 'Lecture',
        'section': 'Doctrine and Covenants',

        # --- Pearl of Great Price ---
        'moses': 'Moses',
        'abr': 'Abraham',
        'abraham': 'Abraham',
        'js-m': 'Joseph Smith--Matthew',
        'jsm': 'Joseph Smith--Matthew',
        'js-h': 'Joseph Smith--History',
        'jsh': 'Joseph Smith--History',
        'josephsmithhistory': 'Joseph Smith--History',
        'js-hist': 'Joseph Smith--History',
        'josephsmithhist': 'Joseph Smith--History',
        'aoff': 'Articles of Faith',
        'a of f': 'Articles of Faith',
        'articlesoffaith': 'Articles of Faith',

        # --- Old Testament ---
        'gen': 'Genesis',
        'gn': 'Genesis',
        'ex': 'Exodus',
        'exod': 'Exodus',
        'lev': 'Leviticus',
        'lv': 'Leviticus',
        'num': 'Numbers',
        'nm': 'Numbers',
        'deut': 'Deuteronomy',
        'dt': 'Deuteronomy',
        'josh': 'Joshua',
        'judg': 'Judges',
        'jg': 'Judges',
        'ruth': 'Ruth',
        '1sam': '1 Samuel',
        '1sm': '1 Samuel',
        '2sam': '2 Samuel',
        '2sm': '2 Samuel',
        '1kgs': '1 Kings',
        '1ki': '1 Kings',
        '2kgs': '2 Kings',
        '2ki': '2 Kings',
        '1chr': '1 Chronicles',
        '1ch': '1 Chronicles',
        '2chr': '2 Chronicles',
        '2ch': '2 Chronicles',
        'ezra': 'Ezra',
        'neh': 'Nehemiah',
        'est': 'Esther',
        'esth': 'Esther',
        'job': 'Job',
        'ps': 'Psalms',
        'psa': 'Psalms',
        'pslm': 'Psalms',
        'psalms': 'Psalms',
        'prov': 'Proverbs',
        'pr': 'Proverbs',
        'eccl': 'Ecclesiastes',
        'ecc': 'Ecclesiastes',
        'song': 'Song of Solomon',
        'songofsol': 'Song of Solomon',
        'sos': 'Song of Solomon',
        'isa': 'Isaiah',
        'is': 'Isaiah',
        'jer': 'Jeremiah',
        'jr': 'Jeremiah',
        'lam': 'Lamentations',
        'ezek': 'Ezekiel',
        'ez': 'Ezekiel',
        'dan': 'Daniel',
        'dn': 'Daniel',
        'hos': 'Hosea',
        'joel': 'Joel',
        'amos': 'Amos',
        'obad': 'Obadiah',
        'ob': 'Obadiah',
        'jonah': 'Jonah',
        'jon': 'Jonah',
        'mic': 'Micah',
        'nah': 'Nahum',
        'hab': 'Habakkuk',
        'zeph': 'Zephaniah',
        'hag': 'Haggai',
        'zech': 'Zechariah',
        'mal': 'Malachi',

        # --- New Testament ---
        'matt': 'Matthew',
        'mt': 'Matthew',
        'mark': 'Mark',
        'mk': 'Mark',
        'luke': 'Luke',
        'lk': 'Luke',
        'john': 'John',
        'jn': 'John',
        'acts': 'Acts',
        'rom': 'Romans',
        '1cor': '1 Corinthians',
        '1co': '1 Corinthians',
        '2cor': '2 Corinthians',
        '2co': '2 Corinthians',
        'gal': 'Galatians',
        'eph': 'Ephesians',
        'phil': 'Philippians',
        'php': 'Philippians',
        'col': 'Colossians',
        '1thes': '1 Thessalonians',
        '1th': '1 Thessalonians',
        '2thes': '2 Thessalonians',
        '2th': '2 Thessalonians',
        '1tim': '1 Timothy',
        '1tm': '1 Timothy',
        '2tim': '2 Timothy',
        '2tm': '2 Timothy',
        'titus': 'Titus',
        'philem': 'Philemon',
        'phm': 'Philemon',
        'heb': 'Hebrews',
        'jas': 'James',
        '1pet': '1 Peter',
        '1pt': '1 Peter',
        '2pet': '2 Peter',
        '2pt': '2 Peter',
        '1john': '1 John',
        '1jn': '1 John',
        '2john': '2 John',
        '2jn': '2 John',
        '3john': '3 John',
        '3jn': '3 John',
        'jude': 'Jude',
        'rev': 'Revelation',
    }

    return scripture_map.get(processed_key, abbreviation)

def find_source_verse_id(conn, book, chapter, verse, corpus_id):
    """Finds the verse_id and text from the source corpus."""
    query = """
    SELECT v.id, v.text
    FROM verse v
    JOIN chapter c ON v.chapter_id = c.id
    JOIN book b ON c.book_id = b.id
    JOIN volume vol ON b.volume_id = vol.id
    WHERE (UPPER(b.title) = UPPER(?) OR UPPER(b.short_title) = UPPER(?))
      AND c.chapter_number = ?
      AND v.verse_number = ?
      AND vol.corpus_id = ?
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query, (book, book, chapter, verse, corpus_id))
        result = cursor.fetchone()
        # Return both the ID and the text
        return (result['id'], result['text']) if result else (None, None)
    except sqlite3.Error: 
        return None, None
    
def find_chapter_start_end_ids(conn, book, chapter, corpus_id):
    """
    Finds the chapter_id, first verse.id, and last verse.id
    for a given book and chapter.
    """
    query = """
    SELECT 
        c.id as chapter_id,
        MIN(v.id) AS first_id, 
        MAX(v.id) AS last_id
    FROM verse v
    JOIN chapter c ON v.chapter_id = c.id
    JOIN book b ON c.book_id = b.id
    JOIN volume vol ON b.volume_id = vol.id
    WHERE (UPPER(b.title) = UPPER(?) OR UPPER(b.short_title) = UPPER(?))
      AND c.chapter_number = ?
      AND vol.corpus_id = ?
    GROUP BY c.id
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query, (book, book, chapter, corpus_id))
        result = cursor.fetchone()
        if result and result['first_id'] and result['last_id']:
            # Return the chapter_id, first_id, and last_id
            return result['chapter_id'], result['first_id'], result['last_id']
        return None, None, None
    except sqlite3.Error:
        return None, None, None

def get_reference_components(conn, target_verse_id, target_corpus_id):
    """
    Reconstructs the scripture reference components (book, chapter, verse)
    from a target verse_id. Returns a dictionary.
    """
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
            return {
                'book': result['title'],
                'chapter': result['chapter_number'],
                'verse': result['verse_number']
            }
        return None
    except sqlite3.Error:
        return None

def format_ref_range(start_ref_comp, end_ref_comp):
    """
    Intelligently combines two reference components into a display string.
    Handles same-chapter, different-chapter, and different-book ranges.
    """
    if not start_ref_comp or not end_ref_comp:
        return None
    
    start_book = start_ref_comp['book']
    start_chap = start_ref_comp['chapter']
    start_verse = start_ref_comp['verse']
    
    end_book = end_ref_comp['book']
    end_chap = end_ref_comp['chapter']
    end_verse = end_ref_comp['verse']

    # Case 1: The entire chapter maps to a single verse
    if start_book == end_book and start_chap == end_chap and start_verse == end_verse:
        return f"{start_book} {start_chap}:{start_verse}"
    
    # Case 2: Range is within the same book and chapter
    if start_book == end_book and start_chap == end_chap:
        return f"{start_book} {start_chap}:{start_verse}–{end_verse}" # en-dash
    
    # Case 3: Range spans chapters within the same book
    if start_book == end_book:
        return f"{start_book} {start_chap}:{start_verse}–{end_chap}:{end_verse}"
    
    # Case 4: Range spans different books
    return f"{start_book} {start_chap}:{start_verse}–{end_book} {end_chap}:{end_verse}"