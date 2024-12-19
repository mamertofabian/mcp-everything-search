# Search Syntax Guide

## Windows Search (Everything SDK)

The following advanced search features are only available on Windows when using the Everything SDK:

### Basic Operators

- `space`: AND operator
- `|`: OR operator
- `!`: NOT operator
- `< >`: Grouping
- `" "`: Search for an exact phrase

### Wildcards

- `*`: Matches zero or more characters
- `?`: Matches exactly one character

Note: Wildcards match the whole filename by default. Disable Match whole filename to match wildcards anywhere.

### Functions

#### Size and Count

- `size:<size>[kb|mb|gb]`: Search by file size
- `count:<max>`: Limit number of results
- `childcount:<count>`: Folders with specific number of children
- `childfilecount:<count>`: Folders with specific number of files
- `childfoldercount:<count>`: Folders with specific number of subfolders
- `len:<length>`: Match filename length

#### Dates

- `datemodified:<date>, dm:<date>`: Modified date
- `dateaccessed:<date>, da:<date>`: Access date
- `datecreated:<date>, dc:<date>`: Creation date
- `daterun:<date>, dr:<date>`: Last run date
- `recentchange:<date>, rc:<date>`: Recently changed date

Date formats: YYYY[-MM[-DD[Thh[:mm[:ss[.sss]]]]]] or today, yesterday, lastweek, etc.

#### File Attributes and Types

- `attrib:<attributes>, attributes:<attributes>`: Search by file attributes (A:Archive, H:Hidden, S:System, etc.)
- `type:<type>`: Search by file type
- `ext:<list>`: Search by semicolon-separated extensions

#### Path and Name

- `path:<path>`: Search in specific path
- `parent:<path>, infolder:<path>, nosubfolders:<path>`: Search in path excluding subfolders
- `startwith:<text>`: Files starting with text
- `endwith:<text>`: Files ending with text
- `child:<filename>`: Folders containing specific child
- `depth:<count>, parents:<count>`: Files at specific folder depth
- `root`: Files with no parent folder
- `shell:<name>`: Search in known shell folders

#### Duplicates and Lists

- `dupe, namepartdupe, attribdupe, dadupe, dcdupe, dmdupe, sizedupe`: Find duplicates
- `filelist:<list>`: Search pipe-separated (|) file list
- `filelistfilename:<filename>`: Search files from list file
- `frn:<frnlist>`: Search by File Reference Numbers
- `fsi:<index>`: Search by file system index
- `empty`: Find empty folders

### Function Syntax

- `function:value`: Equal to value
- `function:<=value`: Less than or equal
- `function:<value`: Less than
- `function:=value`: Equal to
- `function:>value`: Greater than
- `function:>=value`: Greater than or equal
- `function:start..end`: Range of values
- `function:start-end`: Range of values

### Modifiers

- `case:, nocase:`: Enable/disable case sensitivity
- `file:, folder:`: Match only files or folders
- `path:, nopath:`: Match full path or filename only
- `regex:, noregex:`: Enable/disable regex
- `wfn:, nowfn:`: Match whole filename or anywhere
- `wholeword:, ww:`: Match whole words only
- `wildcards:, nowildcards:`: Enable/disable wildcards

### Examples

1. Find Python files modified today:
   `ext:py datemodified:today`

2. Find large video files:
   `ext:mp4|mkv|avi size:>1gb`

3. Find files in specific folder:
   `path:C:\Projects *.js`

## macOS Search (mdfind)

macOS uses Spotlight's metadata search capabilities through the `mdfind` command. The following features are supported:

### Command Options

- `-live`: Provides live updates to search results as files change
- `-count`: Show only the number of matches
- `-onlyin directory`: Limit search to specific directory
- `-literal`: Treat query as literal text without interpretation
- `-interpret`: Interpret query as if typed in Spotlight menu

### Basic Search

- Simple text search looks for matches in any metadata attribute
- Wildcards (`*`) are supported in search strings
- Multiple words are treated as AND conditions
- Whitespace is significant in queries
- Use parentheses () to group expressions

### Search Operators

- `|` (OR): Match either word, e.g., `"image|photo"`
- `-` (NOT): Exclude matches, e.g., `-screenshot`
- `=`, `==` (equal)
- `!=` (not equal)
- `<`, `>` (less/greater than)
- `<=`, `>=` (less/greater than or equal)

### Value Comparison Modifiers

Use brackets with these modifiers:

- `[c]`: Case-insensitive comparison
- `[d]`: Diacritical marks insensitive
- Can be combined, e.g., `[cd]` for both

### Content Types (kind:)

- `application`, `app`: Applications
- `audio`, `music`: Audio/Music files
- `bookmark`: Bookmarks
- `contact`: Contacts
- `email`, `mail message`: Email messages
- `event`: Calendar events
- `folder`: Folders
- `font`: Fonts
- `image`: Images
- `movie`: Movies
- `pdf`: PDF documents
- `preferences`: System preferences
- `presentation`: Presentations
- `todo`: Calendar to-dos

### Date Filters (date:)

Time-based search using these keywords:

- `today`, `yesterday`, `tomorrow`
- `this week`, `next week`
- `this month`, `next month`
- `this year`, `next year`

Or use time functions:

- `$time.today()`
- `$time.yesterday()`
- `$time.this_week()`
- `$time.this_month()`
- `$time.this_year()`
- `$time.tomorrow()`
- `$time.next_week()`
- `$time.next_month()`
- `$time.next_year()`

### Common Metadata Attributes

Search specific metadata using these attributes:

- `kMDItemAuthors`: Document authors
- `kMDItemContentType`: File type
- `kMDItemContentTypeTree`: File type hierarchy
- `kMDItemCreator`: Creating application
- `kMDItemDescription`: File description
- `kMDItemDisplayName`: Display name
- `kMDItemFSContentChangeDate`: File modification date
- `kMDItemFSCreationDate`: File creation date
- `kMDItemFSName`: Filename
- `kMDItemKeywords`: Keywords/tags
- `kMDItemLastUsedDate`: Last used date
- `kMDItemNumberOfPages`: Page count
- `kMDItemTitle`: Document title
- `kMDItemUserTags`: User-assigned tags

### Examples

1. Find images modified yesterday:
   `kind:image date:yesterday`

2. Find documents by author (case-insensitive):
   `kMDItemAuthors ==[c] "John Doe"`

3. Find files in specific directory:
   `mdfind -onlyin ~/Documents "query"`

4. Find files by tag:
   `kMDItemUserTags = "Important"`

5. Find files created by application:
   `kMDItemCreator = "Pixelmator*"`

6. Find PDFs with specific text:
   `kind:pdf "search term"`

7. Find recent presentations:
   `kind:presentation date:this week`

8. Count matching files:
   `mdfind -count "kind:image date:today"`

9. Monitor for new matches:
   `mdfind -live "kind:pdf"`

10. Complex metadata search:
    `kMDItemContentTypeTree = "public.image" && kMDItemUserTags = "vacation" && kMDItemFSContentChangeDate >= $time.this_month()`

Note: Use `mdls filename` to see all available metadata attributes for a specific file.

## Linux Search (locate/plocate)

Linux uses the locate/plocate command for fast filename searching. The following features are supported:

### Basic Search

- Simple text search matches against filenames
- Multiple words are treated as AND conditions
- Wildcards (`*` and `?`) are supported
- Case-insensitive by default

### Search Options

- `-i`: Case-insensitive search (default)
- `-c`: Count matches instead of showing them
- `-r` or `--regex`: Use regular expressions
- `-b`: Match only the basename
- `-w`: Match whole words only

### Examples

1. Find all Python files:
   `*.py`

2. Find files in home directory:
   `/home/username/*`

3. Case-sensitive search for specific file:
   `--regex "^/etc/[A-Z].*\.conf$"`

4. Count matching files:
   Use with `-c` parameter

Note: The locate database must be up to date for accurate results. Run `sudo updatedb` to update the database manually.
