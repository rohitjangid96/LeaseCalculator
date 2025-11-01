# PDF Highlight Feature - Code Samples for Gemini

## Overview
This document contains code samples for the PDF highlighting feature. The highlighting system extracts lease data from PDFs and creates a highlighted PDF showing where each extracted field was found in the document.

## Key Components

### 1. Finding Text Positions in PDF
**File:** `lease_application/lease_accounting/utils/pdf_extractor.py`

This function searches for text in a PDF and returns bounding box coordinates:

```python
def find_text_positions(pdf_path: str, search_text: str, case_sensitive: bool = False) -> list:
    """
    Find all occurrences of text in PDF with bounding boxes
    
    Args:
        pdf_path: Path to PDF file
        search_text: Text to search for
        case_sensitive: Whether search should be case sensitive
        
    Returns:
        List of matches with bounding boxes:
        [
            {
                'page': int,
                'bbox': [x0, y0, x1, y1],
                'text': str
            }
        ]
    """
    if not HAS_PYMUPDF:
        return []
    
    try:
        doc = fitz.open(pdf_path)
        matches = []
        
        search_text_normalized = search_text if case_sensitive else search_text.lower()
        
        for page_num, page in enumerate(doc, start=1):
            # Search for text instances
            text_instances = page.search_for(
                search_text,
                flags=fitz.TEXT_DEHYPHENATE if not case_sensitive else 0
            )
            
            for inst in text_instances:
                matches.append({
                    'page': page_num,
                    'bbox': list(inst),  # [x0, y0, x1, y1]
                    'text': search_text
                })
        
        doc.close()
        return matches
    except Exception as e:
        print(f"Error finding text positions: {e}")
        return []
```

**Key Points:**
- Uses PyMuPDF (`fitz`) to search for text
- Returns bounding boxes as `[x0, y0, x1, y1]` format
- Page numbers start from 1
- Returns empty list if PyMuPDF is not available or if search fails

---

### 2. Saving Extraction Metadata with Coordinates
**File:** `lease_application/pdf_upload_backend.py`

This function finds text positions for each extracted field and saves them to the database:

```python
def _save_extraction_metadata(lease_id: int, extracted_data: dict, pdf_path: str):
    """
    Save extraction metadata with coordinates for review interface
    
    Args:
        lease_id: Lease ID to associate metadata with
        extracted_data: Dictionary of extracted field values
        pdf_path: Path to PDF file for finding coordinates
    """
    if not HAS_GEMINI:
        return
    
    # Field mapping from extraction keys to database field names
    field_mapping = {
        'description': 'description',
        'asset_class': 'asset_class',
        'asset_id_code': 'asset_id_code',
        'lease_start_date': 'lease_start_date',
        'end_date': 'end_date',
        # ... more mappings
    }
    
    # Save metadata for each extracted field
    for extract_key, value in extracted_data.items():
        if value is None or value == '':
            continue
        
        field_name = field_mapping.get(extract_key)
        if not field_name:
            continue
        
        # Convert value to string for searching
        search_text = str(value)
        if len(search_text) > 100:  # Skip very long values
            continue
        
        # Find text positions in PDF
        bounding_boxes = []
        page_number = None
        
        try:
            matches = find_text_positions(pdf_path, search_text, case_sensitive=False)
            if matches:
                # Use first match
                match = matches[0]
                page_number = match['page']
                bbox = match['bbox']
                
                # Convert to format: {x, y, width, height}
                if len(bbox) >= 4:
                    bounding_boxes.append({
                        'x': bbox[0],
                        'y': bbox[1],
                        'width': bbox[2] - bbox[0],
                        'height': bbox[3] - bbox[1]
                    })
        except Exception as e:
            logger.warning(f"Could not find coordinates for field {field_name}: {e}")
        
        # Save metadata (with default confidence if not available)
        try:
            save_extraction_metadata(
                lease_id=lease_id,
                field_name=field_name,
                extracted_value=search_text,
                ai_confidence=0.85,  # Default confidence
                page_number=page_number,
                bounding_boxes=bounding_boxes if bounding_boxes else None,
                snippet=search_text[:200] if len(search_text) > 200 else search_text
            )
        except Exception as e:
            logger.warning(f"Could not save extraction metadata for {field_name}: {e}")
```

**Key Points:**
- Converts extracted values to strings for searching
- Uses `find_text_positions` to locate text in PDF
- Converts `[x0, y0, x1, y1]` format to `{x, y, width, height}` format
- Saves to database using `save_extraction_metadata` function
- Only uses first match if multiple matches found

---

### 3. Database Functions for Metadata Storage
**File:** `lease_application/database.py`

#### Saving Metadata:
```python
def save_extraction_metadata(lease_id: int, field_name: str, extracted_value: str,
                             ai_confidence: Optional[float] = None, page_number: Optional[int] = None,
                             bounding_boxes: Optional[List[Dict]] = None, snippet: Optional[str] = None) -> int:
    """Save AI extraction metadata for a field"""
    import json
    with get_db_connection() as conn:
        # Convert bounding_boxes to JSON
        bboxes_json = json.dumps(bounding_boxes) if bounding_boxes else None
        
        cursor = conn.execute("""
            INSERT INTO ai_extraction_metadata 
            (lease_id, field_name, extracted_value, ai_confidence, page_number, bounding_boxes, snippet)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (lease_id, field_name, extracted_value, ai_confidence, page_number, bboxes_json, snippet))
        return cursor.lastrowid
```

#### Retrieving Metadata:
```python
def get_extraction_metadata(lease_id: int) -> List[Dict]:
    """Get all extraction metadata for a lease"""
    import json
    with get_db_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM ai_extraction_metadata 
            WHERE lease_id = ?
            ORDER BY field_name
        """, (lease_id,)).fetchall()
        
        result = []
        for row in rows:
            metadata = dict(row)
            # Parse bounding_boxes JSON
            if metadata.get('bounding_boxes'):
                try:
                    metadata['bounding_boxes'] = json.loads(metadata['bounding_boxes'])
                except:
                    metadata['bounding_boxes'] = []
            else:
                metadata['bounding_boxes'] = []
            result.append(metadata)
        return result
```

**Key Points:**
- Bounding boxes are stored as JSON strings in database
- Retrieved metadata has bounding_boxes parsed back to Python lists/dicts
- Database schema: `bounding_boxes TEXT` - JSON array of `{x, y, width, height}`

---

### 4. Creating Highlighted PDF
**File:** `lease_application/pdf_upload_backend.py`

This is the main function that creates the highlighted PDF:

```python
def create_highlighted_pdf(lease_id: int, pdf_path: str, extraction_metadata: list) -> Optional[str]:
    """
    Create a PDF with highlight annotations for all extracted fields
    
    Args:
        lease_id: Lease ID
        pdf_path: Path to original PDF
        extraction_metadata: List of extraction metadata with bounding boxes
        
    Returns:
        Path to highlighted PDF file, or None if failed
    """
    if not HAS_PYMUPDF:
        return None
    
    try:
        import fitz
        import shutil
        from pathlib import Path
        
        logger.info(f"📝 Creating highlighted PDF for lease_id={lease_id}")
        
        # Open the PDF
        doc = fitz.open(pdf_path)
        
        # Colors for different fields (cycle through colors)
        highlight_colors = [
            (1.0, 1.0, 0.0),   # Yellow
            (0.0, 1.0, 0.0),   # Green
            (0.0, 1.0, 1.0),   # Cyan
            (1.0, 0.0, 1.0),   # Magenta
        ]
        
        # Add highlights for each field
        for idx, meta in enumerate(extraction_metadata):
            field_name = meta.get('field_name')
            page_number = meta.get('page_number')
            bounding_boxes = meta.get('bounding_boxes', [])
            
            if not page_number or not bounding_boxes:
                continue
            
            try:
                # Parse bounding_boxes if it's a JSON string
                if isinstance(bounding_boxes, str):
                    import json
                    bounding_boxes = json.loads(bounding_boxes)
                
                if not isinstance(bounding_boxes, list):
                    bounding_boxes = [bounding_boxes] if bounding_boxes else []
                
                # Get the page (PDF pages are 0-indexed)
                page_idx = page_number - 1
                if page_idx < 0 or page_idx >= len(doc):
                    continue
                
                page = doc[page_idx]
                
                # Get color for this field (cycle through colors)
                color = highlight_colors[idx % len(highlight_colors)]
                
                # Add highlight annotation for each bounding box
                for bbox in bounding_boxes:
                    if isinstance(bbox, dict):
                        x = bbox.get('x', 0)
                        y = bbox.get('y', 0)
                        width = bbox.get('width', 0)
                        height = bbox.get('height', 0)
                    elif isinstance(bbox, list) and len(bbox) >= 4:
                        x = bbox[0]
                        y = bbox[1]
                        width = bbox[2] - bbox[0] if len(bbox) > 2 else 0
                        height = bbox[3] - bbox[1] if len(bbox) > 3 else 0
                    else:
                        continue
                    
                    # Create rectangle (PyMuPDF uses top-left origin)
                    rect = fitz.Rect(x, y, x + width, y + height)
                    
                    # Add highlight annotation
                    highlight = page.add_highlight_annot(rect)
                    highlight.set_colors(stroke=color)
                    highlight.set_opacity(0.4)
                    highlight.update()
                    
                    logger.info(f"   ✓ Highlighted {field_name} on page {page_number}")
                
            except Exception as e:
                logger.warning(f"Could not highlight {field_name} on page {page_number}: {e}")
        
        # Save highlighted PDF
        UPLOAD_FOLDER = 'uploaded_documents'
        Path(UPLOAD_FOLDER).mkdir(exist_ok=True)
        
        highlighted_filename = f"highlighted_lease_{lease_id}.pdf"
        highlighted_path = os.path.join(UPLOAD_FOLDER, highlighted_filename)
        
        doc.save(highlighted_path)
        doc.close()
        
        logger.info(f"✅ Highlighted PDF saved: {highlighted_path}")
        return highlighted_path
        
    except Exception as e:
        logger.error(f"❌ Error creating highlighted PDF: {e}", exc_info=True)
        return None
```

**Key Points:**
- Checks for `HAS_PYMUPDF` flag (but flag is not defined in this file - needs import from `pdf_extractor`)
- Opens PDF using PyMuPDF (`fitz.open`)
- Converts page numbers (1-indexed from database) to 0-indexed for PyMuPDF
- Supports both dict `{x, y, width, height}` and list `[x0, y0, x1, y1]` formats
- Creates `fitz.Rect` with coordinates
- Uses `page.add_highlight_annot(rect)` to add highlight
- Sets opacity to 0.4 and cycles through colors
- Saves to `uploaded_documents` folder

---

### 5. Calling the Highlight Function
**File:** `lease_application/pdf_upload_backend.py`

The highlight function is called after saving metadata:

```python
# Save extraction metadata with coordinates
logger.info(f"   - Saving extraction metadata...")
_save_extraction_metadata(lease_id, extracted_data, temp_path)
logger.info(f"   - ✅ Extraction metadata saved")

# Create highlighted PDF with annotations
try:
    from database import get_extraction_metadata
    metadata = get_extraction_metadata(lease_id)
    if metadata:
        highlighted_pdf_path = create_highlighted_pdf(lease_id, temp_path, metadata)
        if highlighted_pdf_path:
            logger.info(f"   - ✅ Highlighted PDF created: {highlighted_pdf_path}")
except Exception as e:
    logger.warning(f"Could not create highlighted PDF: {e}")
```

**Key Points:**
- Metadata is saved first, then retrieved from database
- Uses temporary PDF path (`temp_path`) for highlighting
- Error handling wraps the highlight creation in try/except

---

## Coordinate System Details

### PyMuPDF Coordinate System:
- **Origin:** Top-left corner (0, 0)
- **X-axis:** Increases to the right
- **Y-axis:** Increases downward
- **Bounding Box Format:** `[x0, y0, x1, y1]` where:
  - `x0, y0` = top-left corner
  - `x1, y1` = bottom-right corner

### Conversion Between Formats:
1. **From `[x0, y0, x1, y1]` to `{x, y, width, height}`:**
   ```python
   {
       'x': bbox[0],
       'y': bbox[1],
       'width': bbox[2] - bbox[0],
       'height': bbox[3] - bbox[1]
   }
   ```

2. **From `{x, y, width, height}` back to rectangle:**
   ```python
   rect = fitz.Rect(x, y, x + width, y + height)
   ```

---

## Known Issues / Potential Problems

1. **Missing HAS_PYMUPDF Import (CRITICAL):**
   - `create_highlighted_pdf` checks `HAS_PYMUPDF` at line 262, but this variable is NOT imported in `pdf_upload_backend.py`
   - Current imports only include:
     ```python
     from lease_accounting.utils.pdf_extractor import extract_text_from_pdf, has_selectable_text, find_text_positions
     from lease_accounting.utils.ai_extractor import extract_lease_info_from_text, HAS_GEMINI
     ```
   - **Fix needed:** Add `HAS_PYMUPDF` to the import or define it locally:
     ```python
     from lease_accounting.utils.pdf_extractor import HAS_PYMUPDF
     ```
   - **Impact:** This will cause a `NameError` when trying to check `HAS_PYMUPDF`, breaking the highlight feature

2. **Coordinate Format Mismatch:**
   - `find_text_positions` returns `[x0, y0, x1, y1]`
   - `_save_extraction_metadata` converts to `{x, y, width, height}`
   - `create_highlighted_pdf` handles both formats but conversion might be wrong

3. **Page Number Conversion:**
   - Database stores page numbers starting from 1
   - PyMuPDF uses 0-indexed pages
   - Conversion: `page_idx = page_number - 1`

4. **Empty Bounding Boxes:**
   - If `find_text_positions` returns no matches, `bounding_boxes` will be empty
   - Function skips highlighting if `not bounding_boxes` but might not log why

5. **Text Search Issues:**
   - Exact text matching might fail if extracted value doesn't match PDF text exactly
   - Case sensitivity, whitespace, formatting differences could cause misses

6. **Rectangle Validation:**
   - No validation that coordinates are within page bounds
   - Negative coordinates or coordinates outside page dimensions might cause errors

---

## Data Flow

1. **Extraction:** AI extracts lease data → `extracted_data` dict
2. **Text Search:** For each field value → `find_text_positions(pdf_path, search_text)`
3. **Coordinate Conversion:** `[x0, y0, x1, y1]` → `{x, y, width, height}`
4. **Database Save:** Metadata saved with JSON-encoded bounding boxes
5. **Database Retrieve:** Metadata retrieved with parsed bounding boxes
6. **PDF Highlight:** PyMuPDF opens PDF, adds highlight annotations using coordinates
7. **Save:** Highlighted PDF saved to `uploaded_documents` folder

---

## Example Metadata Structure

```python
extraction_metadata = [
    {
        'field_name': 'lease_start_date',
        'extracted_value': '2024-01-15',
        'page_number': 1,
        'bounding_boxes': [
            {
                'x': 150.5,
                'y': 200.3,
                'width': 80.0,
                'height': 12.5
            }
        ],
        'ai_confidence': 0.85
    },
    # ... more fields
]
```

---

## Dependencies

- **PyMuPDF (fitz):** For PDF manipulation and highlighting
- **json:** For serializing/deserializing bounding boxes
- **logging:** For debugging and error tracking

---

## Troubleshooting & Debugging

### Common Issues

#### Issue 1: No Highlights Appearing
**Symptoms:** PDF is created but no highlights visible

**Debug Steps:**
1. Check if `HAS_PYMUPDF` is defined (see Known Issues above)
2. Verify metadata has `page_number` and `bounding_boxes`:
   ```python
   metadata = get_extraction_metadata(lease_id)
   for meta in metadata:
       print(f"Field: {meta['field_name']}, Page: {meta['page_number']}, BBoxes: {meta['bounding_boxes']}")
   ```
3. Check if `bounding_boxes` is empty or None
4. Verify PDF path exists and is accessible
5. Check logs for errors during highlight creation

#### Issue 2: Highlights in Wrong Location
**Symptoms:** Highlights appear but don't match text location

**Possible Causes:**
- Coordinate conversion issue between `[x0, y0, x1, y1]` and `{x, y, width, height}`
- Page number mismatch (1-indexed vs 0-indexed)
- PDF coordinate system confusion

**Debug Steps:**
1. Log original bbox from `find_text_positions`:
   ```python
   print(f"Original bbox: {bbox}")  # Should be [x0, y0, x1, y1]
   ```
2. Log converted bbox:
   ```python
   print(f"Converted bbox: {bounding_boxes[0]}")  # Should be {x, y, width, height}
   ```
3. Verify rectangle creation:
   ```python
   print(f"Rectangle: x={x}, y={y}, width={width}, height={height}")
   print(f"Rect bounds: ({x}, {y}) to ({x+width}, {y+height})")
   ```

#### Issue 3: Text Not Found
**Symptoms:** `bounding_boxes` is empty after `find_text_positions`

**Possible Causes:**
- Extracted value doesn't match PDF text exactly
- Text formatting differences (e.g., "2024-01-15" vs "Jan 15, 2024")
- Case sensitivity
- Whitespace differences
- Special characters

**Debug Steps:**
1. Print search text being used:
   ```python
   print(f"Searching for: '{search_text}'")
   ```
2. Try searching for partial text
3. Check if text exists in PDF:
   ```python
   from lease_accounting.utils.pdf_extractor import extract_text_from_pdf
   text, _ = extract_text_from_pdf(pdf_path)
   if search_text.lower() in text.lower():
       print("Text found in PDF")
   else:
       print("Text NOT found in PDF")
   ```

#### Issue 4: Page Number Errors
**Symptoms:** Highlights not appearing, possibly on wrong page

**Debug Steps:**
1. Verify page number from database:
   ```python
   print(f"Page number from DB: {page_number}")  # Should be 1-indexed
   ```
2. Check page index calculation:
   ```python
   page_idx = page_number - 1  # Convert to 0-indexed
   print(f"Page index: {page_idx}, Total pages: {len(doc)}")
   ```
3. Validate page bounds:
   ```python
   if page_idx < 0 or page_idx >= len(doc):
       print(f"ERROR: Page index {page_idx} out of range (0-{len(doc)-1})")
   ```

#### Issue 5: Rectangle Creation Fails
**Symptoms:** Error when creating `fitz.Rect`

**Debug Steps:**
1. Validate coordinates are numeric:
   ```python
   print(f"x={x}, y={y}, width={width}, height={height}")
   print(f"Types: x={type(x)}, y={type(y)}")
   ```
2. Check for negative values (might be valid for some PDFs)
3. Check for invalid rectangle (width/height <= 0):
   ```python
   if width <= 0 or height <= 0:
       print(f"ERROR: Invalid rectangle dimensions")
   ```

### Debug Code Snippet

Add this to `create_highlighted_pdf` for debugging:

```python
logger.info(f"📝 Creating highlighted PDF for lease_id={lease_id}")
logger.info(f"   - PDF path: {pdf_path}")
logger.info(f"   - PDF exists: {os.path.exists(pdf_path)}")
logger.info(f"   - Metadata count: {len(extraction_metadata)}")

for idx, meta in enumerate(extraction_metadata):
    field_name = meta.get('field_name')
    page_number = meta.get('page_number')
    bounding_boxes = meta.get('bounding_boxes', [])
    
    logger.info(f"   - Field {idx+1}: {field_name}")
    logger.info(f"     - Page: {page_number}")
    logger.info(f"     - BBoxes type: {type(bounding_boxes)}")
    logger.info(f"     - BBoxes value: {bounding_boxes}")
    logger.info(f"     - BBoxes count: {len(bounding_boxes) if isinstance(bounding_boxes, list) else 'N/A'}")
```

### Testing Coordinates Manually

Test if coordinates are correct by creating a simple highlight:

```python
import fitz

doc = fitz.open(pdf_path)
page = doc[0]  # First page

# Test rectangle (should be visible)
test_rect = fitz.Rect(100, 100, 200, 150)
highlight = page.add_highlight_annot(test_rect)
highlight.set_colors(stroke=(1.0, 0.0, 0.0))  # Red
highlight.set_opacity(0.5)
highlight.update()

doc.save("test_highlight.pdf")
doc.close()
```

