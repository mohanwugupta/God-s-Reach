"""
OCR fallback module for scanned PDFs using ocrmypdf.
"""
import subprocess
import pathlib
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def ensure_searchable(pdf_path: str, skip_ocr: bool = False) -> str:
    """
    Ensure PDF is searchable by running OCR if needed.

    Args:
        pdf_path: Path to input PDF
        skip_ocr: If True, skip OCR processing (useful for batch processing on clusters)

    Returns:
        Path to searchable PDF (original if already searchable, OCR'd version if processed)
    """
    if skip_ocr:
        logger.debug(f"Skipping OCR for {pdf_path} (skip_ocr=True)")
        return str(pdf_path)
    
    pdf_path = pathlib.Path(pdf_path)
    out_path = pdf_path.with_suffix(".ocr.pdf")

    # Skip if already processed
    if out_path.exists():
        logger.debug(f"Using cached OCR PDF: {out_path}")
        return str(out_path)

    try:
        # Run ocrmypdf to add OCR layer
        subprocess.run(
            ["ocrmypdf", "--skip-text", "--quiet", str(pdf_path), str(out_path)],
            check=True,
            capture_output=True,
            timeout=300  # 5 minute timeout
        )
        logger.info(f"OCR completed: {out_path}")
        return str(out_path)
    except subprocess.TimeoutExpired:
        logger.warning(f"OCR timed out for {pdf_path}, using original")
        return str(pdf_path)
    except subprocess.CalledProcessError as e:
        # OCR failed - log but continue with original
        logger.warning(f"OCR failed for {pdf_path} (exit code {e.returncode}), using original")
        return str(pdf_path)
    except FileNotFoundError:
        # ocrmypdf not installed
        logger.debug("ocrmypdf not found, skipping OCR")
        return str(pdf_path)
