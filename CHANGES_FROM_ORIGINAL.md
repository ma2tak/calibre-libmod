# オリジナルのcalibreからの変更箇所

このドキュメントは、[オリジナルのcalibre](https://github.com/kovidgoyal/calibre) から
本リポジトリ（calibre-libmod）に加えた変更をまとめたものです。

calibreのバージョンアップ時に同じ変更を再適用するための参考として使用してください。

---

## 変更の概要

| # | ファイル | 変更内容 |
|---|---------|---------|
| 1 | `src/calibre/db/backend.py` | ライブラリフォルダ構造をタイトル名ベースに変更 |
| 2 | `src/calibre/db/backend.py` | ファイル名をタイトル名のみに変更 |
| 3 | `src/calibre/db/backend.py` | `cover_abspath()` のパス構築をリファクタリング |
| 4 | `src/calibre/db/backend.py` | Windows上でのファイル置換リトライ待機時間を短縮 |
| 5 | `src/calibre/__init__.py` | `sanitize_file_name()` に全角変換処理を追加 |
| 6 | `src/calibre/ebooks/metadata/book/base.py` | タイトル設定時に全角変換処理を追加 |

---

## 変更詳細

### 1. `src/calibre/db/backend.py` — `construct_path_name()` の変更

**目的:** 書籍のフォルダ名をオリジナルの「著者名/タイトル (ID)」形式から、タイトルのみの形式に変更する。ASCII変換を行わず、書籍の元のタイトルをそのまま使用する。

**変更前（オリジナル）:**

```python
def construct_path_name(self, book_id, title, author):
    '''
    Construct the directory name for this book based on its metadata.
    '''
    book_id = BOOK_ID_PATH_TEMPLATE.format(book_id)
    l = self.PATH_LIMIT - (len(book_id) // 2) - 2
    author = ascii_filename(author)[:l]
    title  = ascii_filename(title.lstrip())[:l].rstrip()
    if not title:
        title = 'Unknown'[:l]
    try:
        while author[-1] in (' ', '.'):
            author = author[:-1]
    except IndexError:
        author = ''
    if not author:
        author = ascii_filename(_('Unknown'))
    if author.upper() in WINDOWS_RESERVED_NAMES:
        author += 'w'
    return f'{author}/{title}{book_id}'
```

**変更後（本リポジトリ）:**

```python
def construct_path_name(self, book_id, title, author):
    '''
    Construct the directory name for this book based on its metadata.
    Uses the original title without modification.
    '''
    base_name = title.strip()
    if not base_name:
        base_name = 'Unknown'

    # Handle name collisions by appending _number
    path = base_name
    counter = 1
    while os.path.exists(os.path.join(self.library_path, path)):
        path = f"{base_name}_{counter}"
        counter += 1

    if path.upper() in WINDOWS_RESERVED_NAMES:
        path += 'w'
    return path
```

**主な変更点:**
- 著者名のサブディレクトリを廃止し、タイトルのみのフラットなフォルダ構造に変更
- `ascii_filename()` によるASCII変換を廃止し、元のタイトル文字列をそのまま使用
- `BOOK_ID_PATH_TEMPLATE` によるIDサフィックスを廃止
- 同名フォルダが存在する場合は `_1`, `_2` のようなサフィックスを付与して衝突を回避

---

### 2. `src/calibre/db/backend.py` — `construct_file_name()` の変更

**目的:** 書籍ファイルの名前を「タイトル - 著者名」形式からタイトルのみに変更する。ASCII変換を行わず、書籍の元のタイトルをそのまま使用する。

**変更前（オリジナル）:**

```python
def construct_file_name(self, book_id, title, author, extlen):
    '''
    Construct the file name for this book based on its metadata.
    '''
    extlen = max(extlen, 14)  # 14 accounts for ORIGINAL_EPUB
    l = (self.PATH_LIMIT - (extlen // 2) - 2) if iswindows else ((self.PATH_LIMIT - extlen - 2) // 2)
    if l < 5:
        raise ValueError(f'Extension length too long: {extlen}')
    author = ascii_filename(author)[:l]
    title  = ascii_filename(title.lstrip())[:l].rstrip()
    if not title:
        title = 'Unknown'[:l]
    name   = title + ' - ' + author
    while name.endswith('.'):
        name = name[:-1]
    if not name:
        name = ascii_filename(_('Unknown'))
    return name
```

**変更後（本リポジトリ）:**

```python
def construct_file_name(self, book_id, title, author, extlen):
    '''
    Construct the file name for this book based on its metadata.
    '''
    name = title.strip()
    if not name:
        name = 'Unknown'
    return name
```

**主な変更点:**
- ファイル名から著者名部分（`- 著者名`）を廃止
- `ascii_filename()` によるASCII変換を廃止し、元のタイトル文字列をそのまま使用
- パス長制限チェックを廃止

---

### 3. `src/calibre/db/backend.py` — `cover_abspath()` のリファクタリング

**目的:** カバー画像のパス構築を `os.path.abspath()` を使用してシンプルに記述する。

**変更前（オリジナル）:**

```python
def cover_abspath(self, book_id, path):
    path = os.path.join(self.library_path, path)
    fmt_path = os.path.join(path, COVER_FILE_NAME)
    if os.path.exists(fmt_path):
        return fmt_path
```

**変更後（本リポジトリ）:**

```python
def cover_abspath(self, book_id, path):
    path = os.path.abspath(os.path.join(self.library_path, path, COVER_FILE_NAME))
    if os.path.exists(path):
        return path
```

---

### 4. `src/calibre/db/backend.py` — `add_format()` の待機時間変更

**目的:** Windowsでファイル置換に失敗した際のリトライ待機時間を 1秒 から 0.2秒 に短縮する。

**変更箇所（`add_format()` 内）:**

```python
# 変更前
time.sleep(1)

# 変更後
time.sleep(0.2)
```

---

### 5. `src/calibre/__init__.py` — `sanitize_file_name()` への全角変換追加

**目的:** ファイル名のサニタイズ時に、ファイルシステムで使用できない特殊文字を全角文字に置換する（削除や `_` への置換の代わりに）。日本語タイトルに含まれる記号をファイル名に保持するためのもの。

**変更内容:**

新しい関数 `change_to_zenkaku()` を追加し、`sanitize_file_name()` の冒頭で呼び出す：

```python
def change_to_zenkaku(name):
    replacements = {
        ':': '：',
        '/': '／',
        '\\': '＼',
        '+': '＋',
        '*': '＊',
        '?': '？',
        '<': '＜',
        '>': '＞',
        '|': '｜',
        '"': '"',
    }

    for old_char, new_char in replacements.items():
        name = name.replace(old_char, new_char)

    return name


def sanitize_file_name(name, substitute='_'):
    # ...（既存コード）
    name = change_to_zenkaku(name)   # ← この行を追加
    chars = (substitute if c in _filename_sanitize_unicode else c for c in name)
    # ...（以下既存コード）
```

**変換テーブル:**

| 半角文字 | 全角文字 | 説明 |
|---------|---------|------|
| `:` | `：` | コロン |
| `/` | `／` | スラッシュ |
| `\` | `＼` | バックスラッシュ |
| `+` | `＋` | プラス |
| `*` | `＊` | アスタリスク |
| `?` | `？` | クエスチョンマーク |
| `<` | `＜` | 小なり |
| `>` | `＞` | 大なり |
| `\|` (pipe) | `｜` | パイプ |
| `"` | `"` | 二重引用符 |

---

### 6. `src/calibre/ebooks/metadata/book/base.py` — タイトル設定時の全角変換

**目的:** 書籍のタイトルを設定する際に、ファイルシステムで使用できない文字を全角文字に変換する。

**変更内容:**

`Metadata` クラスに `change_to_zenkaku()` メソッドを追加し、`__setattr__()` でタイトル設定時に呼び出す：

```python
def change_to_zenkaku(self, name):
    replacements = {
        ':': '：',
        '/': '／',
        '\\': '＼',
        '+': '＋',
        '*': '＊',
        '?': '？',
        '<': '＜',
        '>': '＞',
        '|': '｜',
        '"': '"',
    }

    for old_char, new_char in replacements.items():
        name = name.replace(old_char, new_char)
    return name


def __setattr__(self, field, val, extra=None):
    _data = object.__getattribute__(self, '_data')
    if field in SIMPLE_SET:
        if val is None:
            val = copy.copy(NULL_VALUES.get(field, None))
        # タイトルの場合、コロンを全角に変換
        if field == 'title' and isinstance(val, string_or_bytes):
            val = self.change_to_zenkaku(val)   # ← この行を変更（元は val.replace(':', '：')）
        _data[field] = val
```

---

### インポートの変更

**目的:** 変更1・2により不要になった `ascii_filename` 等の関数をインポートから削除する。

**ファイル:** `src/calibre/db/backend.py`

**変更前:**

```python
from calibre.utils.filenames import (
    ascii_filename,
    atomic_rename,
    copyfile_using_links,
    copytree_using_links,
    get_long_path_name,
    hardlink_file,
    is_case_sensitive,
    is_fat_filesystem,
    make_long_path_useable,
    remove_dir_if_empty,
    samefile,
)
```

**変更後:**

```python
from calibre.utils.filenames import (
    get_long_path_name,
    is_case_sensitive,
    is_fat_filesystem,
    make_long_path_useable,
    remove_dir_if_empty,
    samefile,
)
```

---

## calibreアップデート時の手順

1. 上記の変更が含まれるファイルを特定する：
   - `src/calibre/db/backend.py`
   - `src/calibre/__init__.py`
   - `src/calibre/ebooks/metadata/book/base.py`

2. アップストリームのcalibreと本リポジトリのdiffを確認する：
   ```
   git diff upstream/master HEAD -- src/calibre/db/backend.py
   git diff upstream/master HEAD -- src/calibre/__init__.py
   git diff upstream/master HEAD -- src/calibre/ebooks/metadata/book/base.py
   ```

3. 各ファイルにマージコンフリクトが発生した場合は、上記の「変更詳細」を参照して
   本リポジトリの変更を優先して適用する。

4. アップストリームの変更で関連する関数のシグネチャや内部実装が変わっている場合は、
   このドキュメントの変更内容を参考に、同等の機能を実現するよう適宜調整する。
