"""CMP 305 Data Structures and Algorithms. Owner: Ahmed Abdelmonem.

Reference: M. A. Weiss, Data Structures and Algorithm Analysis in C++, 4th ed., Pearson 2014,
ISBN-13 978-0-13-284737-7, first printing (June 2013). Scope per the Fall 2024 syllabus: chapters 1-7,
printed pages 1-350 = PDF pages 20-369. Page offset checked on chapter starts ch1 p1 (PDF 20),
ch4 p121 (PDF 140), ch7 p291 (PDF 310).
The reference was verified before indexing (errata, VR4-VR10, code verification); every finding is in
data/cmp305/known_issues.json.
"""
from courses.base import CourseModule


class CMP305(CourseModule):
    course_id = "cmp305"
    book_title = "Weiss, Data Structures and Algorithm Analysis in C++, 4th ed."
    keywords = ["time complexity", "big-o", "binary search tree", "avl tree",
                "splay tree", "b-tree", "hash table", "separate chaining",
                "linear probing", "priority queue", "binary heap",
                "linked list", "insertion sort", "quicksort", "heapsort"]
    trusted_domains = ["algs4.cs.princeton.edu", "en.cppreference.com"]
    page_range = (20, 369)           # printed pp. 1-350, chapters 1-7
    page_offset = 19                 # printed page = PDF page - 19
    claim_types = ["prose", "code"]
    # Weiss's math fonts (MTEX/MTSYN) put symbols in control characters. Θ and Ω per the guide; the rest
    # were found by scanning every in-scope page: U+0002/U+0003 summation, U+000C Δ (decreaseKey(p, Δ)),
    # U+000E integral (p202), U+0015/U+0016 ceiling (p327). Bracket glyphs U+0004/5/8/F/10 map to brackets.
    glyph_map = {"\x07": "Θ", "\x06": "Ω", "\x02": "Σ", "\x03": "Σ", "\x0c": "Δ", "\x0e": "∫",
                 "\x15": "⌈", "\x16": "⌉", "\x04": "[", "\x05": "]", "\x08": "(", "\x0f": "(", "\x10": ")"}
    book_sha256 = "d3510f9b88bb8ea0178d980772657c5a485a0ae319816ede9ef620c65b643f76"
    MIN_SCORE = 0.60                 # replaced after the eval run
