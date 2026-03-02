#!/usr/bin/env python


__license__   = 'GPL v3'
__copyright__ = '2024, calibre-libmod contributors'
__docformat__ = 'restructuredtext en'

'''
Tests for calibre-libmod modifications.

These tests verify the specific changes made to calibre's original code.
Modified files:
  - src/calibre/__init__.py           (change_to_zenkaku, sanitize_file_name)
  - src/calibre/db/backend.py         (construct_path_name, construct_file_name, cover_abspath)
  - src/calibre/ebooks/metadata/book/base.py  (Metadata.change_to_zenkaku, Metadata.__setattr__)
'''

import os
import unittest

from calibre.db.tests.base import BaseTest


class ChangeToZenkakuTest(unittest.TestCase):
    '''Tests for change_to_zenkaku() added to src/calibre/__init__.py'''

    def _func(self):
        from calibre import change_to_zenkaku
        return change_to_zenkaku

    def test_colon(self):
        self.assertEqual(self._func()('a:b'), 'a：b')

    def test_slash(self):
        self.assertEqual(self._func()('a/b'), 'a／b')

    def test_backslash(self):
        self.assertEqual(self._func()('a\\b'), 'a＼b')

    def test_plus(self):
        self.assertEqual(self._func()('a+b'), 'a＋b')

    def test_asterisk(self):
        self.assertEqual(self._func()('a*b'), 'a＊b')

    def test_question_mark(self):
        self.assertEqual(self._func()('a?b'), 'a？b')

    def test_less_than(self):
        self.assertEqual(self._func()('a<b'), 'a＜b')

    def test_greater_than(self):
        self.assertEqual(self._func()('a>b'), 'a＞b')

    def test_pipe(self):
        self.assertEqual(self._func()('a|b'), 'a｜b')

    def test_double_quote(self):
        # double quote is replaced with LEFT DOUBLE QUOTATION MARK (U+201C)
        self.assertEqual(self._func()('a"b'), 'a\u201cb')

    def test_multiple_chars(self):
        result = self._func()('title: chapter/1')
        self.assertEqual(result, 'title： chapter／1')

    def test_no_special_chars_unchanged(self):
        self.assertEqual(self._func()('normal title'), 'normal title')

    def test_japanese_with_colon(self):
        result = self._func()('タイトル:サブタイトル')
        self.assertEqual(result, 'タイトル：サブタイトル')

    def test_all_replacements(self):
        replacements = [
            (':', '：'),
            ('/', '／'),
            ('\\', '＼'),
            ('+', '＋'),
            ('*', '＊'),
            ('?', '？'),
            ('<', '＜'),
            ('>', '＞'),
            ('|', '｜'),
            ('"', '\u201c'),
        ]
        for half, full in replacements:
            result = self._func()(f'a{half}b')
            self.assertEqual(result, f'a{full}b', f'Failed conversion for {half!r}')


class SanitizeFileNameZenkakuTest(unittest.TestCase):
    '''Tests that sanitize_file_name() in src/calibre/__init__.py calls change_to_zenkaku()'''

    def _func(self):
        from calibre import sanitize_file_name
        return sanitize_file_name

    def test_colon_becomes_zenkaku_not_underscore(self):
        result = self._func()('title:subtitle')
        self.assertIn('：', result)
        self.assertNotIn(':', result)

    def test_slash_becomes_zenkaku(self):
        result = self._func()('a/b')
        self.assertIn('／', result)
        self.assertNotIn('/', result)

    def test_question_mark_becomes_zenkaku(self):
        result = self._func()('what?')
        self.assertIn('？', result)
        self.assertNotIn('?', result)


class ConstructPathNameTest(BaseTest):
    '''Tests for construct_path_name() modified in src/calibre/db/backend.py'''

    def test_returns_title_only_no_author_subfolder(self):
        'construct_path_name returns title only, not author/title structure'
        cache = self.init_cache()
        path = cache.backend.construct_path_name(1, 'My Title', 'Some Author')
        self.assertNotIn('/', path)
        self.assertNotIn('Author', path)
        self.assertEqual(path, 'My Title')

    def test_strips_whitespace_from_title(self):
        'construct_path_name strips leading/trailing whitespace from title'
        cache = self.init_cache()
        path = cache.backend.construct_path_name(1, '  My Title  ', 'Author')
        self.assertEqual(path, 'My Title')

    def test_empty_title_becomes_unknown(self):
        'construct_path_name uses "Unknown" for empty title'
        cache = self.init_cache()
        path = cache.backend.construct_path_name(1, '', 'Author')
        self.assertEqual(path, 'Unknown')

    def test_whitespace_only_title_becomes_unknown(self):
        'construct_path_name uses "Unknown" for whitespace-only title'
        cache = self.init_cache()
        path = cache.backend.construct_path_name(1, '   ', 'Author')
        self.assertEqual(path, 'Unknown')

    def test_japanese_title_preserved_without_ascii_conversion(self):
        'construct_path_name preserves Japanese characters without ASCII conversion'
        cache = self.init_cache()
        path = cache.backend.construct_path_name(1, '日本語タイトル', '著者名')
        self.assertEqual(path, '日本語タイトル')

    def test_no_book_id_appended(self):
        'construct_path_name does not append book ID to the path'
        cache = self.init_cache()
        path = cache.backend.construct_path_name(99, 'My Title', 'Author')
        self.assertNotIn('99', path)
        self.assertNotIn('(', path)

    def test_windows_reserved_name_gets_w_suffix(self):
        'construct_path_name appends "w" to Windows reserved names'
        cache = self.init_cache()
        path = cache.backend.construct_path_name(1, 'CON', 'Author')
        self.assertNotEqual(path.upper(), 'CON')
        self.assertTrue(path.upper().startswith('CON'))

    def test_collision_handled_with_numeric_suffix(self):
        'construct_path_name appends _1 when title folder already exists'
        cache = self.init_cache()
        library_path = cache.backend.library_path
        existing_dir = os.path.join(library_path, 'My Title')
        os.makedirs(existing_dir, exist_ok=True)
        try:
            path = cache.backend.construct_path_name(1, 'My Title', 'Author')
            self.assertEqual(path, 'My Title_1')
        finally:
            os.rmdir(existing_dir)

    def test_multiple_collisions_increment_suffix(self):
        'construct_path_name increments suffix when multiple folders exist'
        cache = self.init_cache()
        library_path = cache.backend.library_path
        dir1 = os.path.join(library_path, 'My Title')
        dir2 = os.path.join(library_path, 'My Title_1')
        os.makedirs(dir1, exist_ok=True)
        os.makedirs(dir2, exist_ok=True)
        try:
            path = cache.backend.construct_path_name(1, 'My Title', 'Author')
            self.assertEqual(path, 'My Title_2')
        finally:
            os.rmdir(dir2)
            os.rmdir(dir1)


class ConstructFileNameTest(BaseTest):
    '''Tests for construct_file_name() modified in src/calibre/db/backend.py'''

    def test_returns_title_only_no_author(self):
        'construct_file_name returns title only, not "title - author"'
        cache = self.init_cache()
        name = cache.backend.construct_file_name(1, 'My Title', 'Some Author', 4)
        self.assertEqual(name, 'My Title')
        self.assertNotIn('Author', name)
        self.assertNotIn(' - ', name)

    def test_strips_whitespace_from_title(self):
        'construct_file_name strips leading/trailing whitespace from title'
        cache = self.init_cache()
        name = cache.backend.construct_file_name(1, '  My Title  ', 'Author', 4)
        self.assertEqual(name, 'My Title')

    def test_empty_title_becomes_unknown(self):
        'construct_file_name uses "Unknown" for empty title'
        cache = self.init_cache()
        name = cache.backend.construct_file_name(1, '', 'Author', 4)
        self.assertEqual(name, 'Unknown')

    def test_whitespace_only_title_becomes_unknown(self):
        'construct_file_name uses "Unknown" for whitespace-only title'
        cache = self.init_cache()
        name = cache.backend.construct_file_name(1, '   ', 'Author', 4)
        self.assertEqual(name, 'Unknown')

    def test_japanese_title_preserved_without_ascii_conversion(self):
        'construct_file_name preserves Japanese characters without ASCII conversion'
        cache = self.init_cache()
        name = cache.backend.construct_file_name(1, '日本語タイトル', '著者名', 4)
        self.assertEqual(name, '日本語タイトル')

    def test_extlen_does_not_affect_result(self):
        'construct_file_name result is not truncated based on extlen'
        cache = self.init_cache()
        long_title = 'A' * 200
        name = cache.backend.construct_file_name(1, long_title, 'Author', 4)
        self.assertEqual(name, long_title)


class CoverAbspathTest(BaseTest):
    '''Tests for cover_abspath() modified in src/calibre/db/backend.py'''

    def test_returns_path_when_cover_exists(self):
        'cover_abspath returns an absolute path when cover file exists'
        cache = self.init_cache()
        # Books 1 and 2 have covers set in create_db()
        book_path = cache.field_for('path', 1)
        result = cache.backend.cover_abspath(1, book_path)
        self.assertIsNotNone(result)
        self.assertTrue(os.path.exists(result))

    def test_returns_none_when_no_cover(self):
        'cover_abspath returns None when no cover file exists'
        cache = self.init_cache()
        # Book 3 has no cover set in create_db()
        book_path = cache.field_for('path', 3)
        result = cache.backend.cover_abspath(3, book_path)
        self.assertIsNone(result)

    def test_path_is_absolute(self):
        'cover_abspath result is an absolute path (uses os.path.abspath)'
        cache = self.init_cache()
        book_path = cache.field_for('path', 1)
        result = cache.backend.cover_abspath(1, book_path)
        if result is not None:
            self.assertEqual(result, os.path.abspath(result))


class MetadataChangeToZenkakuTest(unittest.TestCase):
    '''Tests for Metadata.change_to_zenkaku() added to src/calibre/ebooks/metadata/book/base.py'''

    def _make_metadata(self, title='test'):
        from calibre.ebooks.metadata.book.base import Metadata
        return Metadata(title)

    def test_change_to_zenkaku_method_all_chars(self):
        'Metadata.change_to_zenkaku() converts all expected special characters'
        mi = self._make_metadata()
        replacements = [
            (':', '：'),
            ('/', '／'),
            ('\\', '＼'),
            ('+', '＋'),
            ('*', '＊'),
            ('?', '？'),
            ('<', '＜'),
            ('>', '＞'),
            ('|', '｜'),
            ('"', '\u201c'),
        ]
        for half, full in replacements:
            result = mi.change_to_zenkaku(f'a{half}b')
            self.assertEqual(result, f'a{full}b', f'Failed conversion for {half!r}')

    def test_title_colon_converted_on_set(self):
        'Setting title with colon converts it to zenkaku colon'
        mi = self._make_metadata('title:subtitle')
        self.assertIn('：', mi.title)
        self.assertNotIn(':', mi.title)

    def test_title_slash_converted_on_set(self):
        'Setting title with slash converts it to zenkaku slash'
        mi = self._make_metadata('title/subtitle')
        self.assertIn('／', mi.title)
        self.assertNotIn('/', mi.title)

    def test_title_multiple_special_chars_all_converted(self):
        'Setting title converts all special characters to zenkaku'
        mi = self._make_metadata('a:b/c?d')
        self.assertIn('：', mi.title)
        self.assertIn('／', mi.title)
        self.assertIn('？', mi.title)

    def test_title_without_special_chars_unchanged(self):
        'Setting normal title leaves it unchanged'
        mi = self._make_metadata('Normal Title')
        self.assertEqual(mi.title, 'Normal Title')

    def test_japanese_title_preserved(self):
        'Japanese characters in title are preserved'
        mi = self._make_metadata('日本語タイトル')
        self.assertEqual(mi.title, '日本語タイトル')

    def test_reassigning_title_applies_zenkaku_conversion(self):
        'Re-assigning title also applies zenkaku conversion'
        mi = self._make_metadata('initial')
        mi.title = 'updated:title'
        self.assertIn('：', mi.title)
        self.assertNotIn(':', mi.title)
