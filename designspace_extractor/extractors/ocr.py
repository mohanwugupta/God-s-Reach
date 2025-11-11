"""
OCR fallback module for scanned PDFs using ocrmypdf.
"""
import subprocess
import pathlib
from typing import Optional


def ensure_searchable(pdf_path: str) -> str:
    """
    Ensure PDF is searchable by running OCR if needed.

    Args:
        pdf_path: Path to input PDF

    Returns:
        Path to searchable PDF (original if already searchable, OCR'd version if processed)
    """
    pdf_path = pathlib.Path(pdf_path)
    out_path = pdf_path.with_suffix(".ocr.pdf")

    # Skip if already processed
    if out_path.exists():
        return str(out_path)

    try:
        # Run ocrmypdf to add OCR layer
        subprocess.run(
            ["ocrmypdf", "--skip-text", "--quiet", str(pdf_path), str(out_path)],
            check=True,
            capture_output=True
        )
        return str(out_path)
    except subprocess.CalledProcessError as e:
        # OCR failed or not available
        print(f"OCR failed for {pdf_path}: {e}")
        return str(pdf_path)  # Return original
    except FileNotFoundError:
        # ocrmypdf not installed
        print("ocrmypdf not found, skipping OCR")
        return str(pdf_path)
