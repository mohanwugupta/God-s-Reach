#!/bin/bash
# Remove duplicate .ocr.pdf files from papers directory
# These are duplicates of the original PDFs with ".ocr" added before ".pdf"

echo "=========================================="
echo "Removing .ocr.pdf Duplicates"
echo "=========================================="
echo ""

# Navigate to papers directory
cd ../papers

# Count current PDFs
TOTAL_BEFORE=$(ls -1 *.pdf 2>/dev/null | wc -l)
echo "Total PDFs before cleanup: $TOTAL_BEFORE"

# Find .ocr.pdf files
OCR_FILES=$(ls -1 *.ocr.pdf 2>/dev/null | wc -l)
echo "Found .ocr.pdf files: $OCR_FILES"
echo ""

if [ $OCR_FILES -gt 0 ]; then
    echo "The following .ocr.pdf files will be removed:"
    echo "-------------------------------------------"
    ls -1 *.ocr.pdf 2>/dev/null
    echo ""
    
    # Ask for confirmation (comment out for automatic removal)
    read -p "Remove these files? (y/n) " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Remove .ocr.pdf files
        rm -v *.ocr.pdf
        echo ""
        echo "✅ Removed $OCR_FILES .ocr.pdf duplicate files"
    else
        echo "❌ Cancelled - no files removed"
        exit 0
    fi
else
    echo "✅ No .ocr.pdf duplicates found"
fi

# Count remaining PDFs
TOTAL_AFTER=$(ls -1 *.pdf 2>/dev/null | wc -l)
echo ""
echo "Total PDFs after cleanup: $TOTAL_AFTER"
echo "Removed: $(($TOTAL_BEFORE - $TOTAL_AFTER)) files"
echo ""
echo "Remaining PDF files:"
echo "-------------------------------------------"
ls -1 *.pdf 2>/dev/null
echo ""
echo "=========================================="
echo "Cleanup Complete"
echo "=========================================="
