"""
OCR helper for the Medical Timeline Generator.

Supported files
---------------
- PDF:
    1. Use the embedded PDF text layer when enough text is available.
    2. Fall back to PyMuPDF rendering + Tesseract OCR for scanned pages.
- Images:
    - JPG / JPEG / PNG / BMP / WEBP
    - Multi-frame TIFF

The function returns page-level text so that downstream LLM extraction
can preserve source_page information.

Requires:
    pip install pymupdf pytesseract pillow

Also requires the Tesseract OCR binary to be installed on the server.

Examples:
    Ubuntu:
        sudo apt install tesseract-ocr

    macOS:
        brew install tesseract

    Windows:
        Install Tesseract OCR and either:
        - add it to PATH, or
        - set TESSERACT_CMD in .env
"""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF
import pytesseract
from anyio import to_thread
from PIL import Image, ImageOps, ImageSequence, UnidentifiedImageError

from app.core.config import settings
from app.services.intelligence.errors import OCRError


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# DATA MODEL
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class PageText:
    """
    OCR/text extraction result for one page/frame.

    page_number:
        1-based page/frame number.

    text:
        Extracted text.

    method:
        "text_layer" when the PDF already contains usable text.
        "ocr" when Tesseract was required.
    """

    page_number: int
    text: str
    method: str


# ---------------------------------------------------------------------------
# PUBLIC API
# ---------------------------------------------------------------------------

async def extract_pages(
    path: Path,
    content_type: str,
) -> list[PageText]:
    """
    Extract text from a PDF or image file.

    OCR and PDF rasterization are CPU-bound operations, so the synchronous
    implementation is executed in a worker thread to avoid blocking FastAPI.

    Args:
        path: Uploaded file path.
        content_type: MIME type supplied by the upload layer.

    Returns:
        List of PageText objects.

    Raises:
        OCRError: When the file cannot be processed.
    """
    if not path.exists():
        raise OCRError("Uploaded file could not be found.")

    if not path.is_file():
        raise OCRError("Uploaded path is not a file.")

    return await to_thread.run_sync(
        _extract_pages_sync,
        path,
        content_type,
    )


# ---------------------------------------------------------------------------
# MAIN DISPATCHER
# ---------------------------------------------------------------------------

def _extract_pages_sync(
    path: Path,
    content_type: str,
) -> list[PageText]:
    """
    Synchronous file-type dispatcher.
    """

    normalized_content_type = (
        content_type.split(";", 1)[0].strip().lower()
    )

    try:
        if normalized_content_type == "application/pdf":
            pages = _extract_pdf(path)

        elif normalized_content_type.startswith("image/"):
            pages = _extract_image(path)

        else:
            raise OCRError(
                f"Unsupported content type for OCR: {content_type}"
            )

    except pytesseract.TesseractNotFoundError as exc:
        raise OCRError(
            "Tesseract OCR is not installed or could not be found "
            "on the server."
        ) from exc

    except pytesseract.TesseractError as exc:
        raise OCRError(
            "Tesseract failed while processing the document."
        ) from exc

    except UnidentifiedImageError as exc:
        raise OCRError(
            "The uploaded image could not be read."
        ) from exc

    except OCRError:
        raise

    except Exception as exc:
        logger.exception(
            "Unexpected OCR failure for file: %s",
            path.name,
        )
        raise OCRError(
            f"Could not read the file ({type(exc).__name__})."
        ) from exc

    total_chars = sum(len(page.text) for page in pages)
    ocr_pages = sum(page.method == "ocr" for page in pages)

    logger.info(
        "OCR finished: pages=%d chars=%d ocr_pages=%d file=%s",
        len(pages),
        total_chars,
        ocr_pages,
        path.name,
    )

    if not pages:
        raise OCRError("No pages were found in the uploaded file.")

    return pages


# ---------------------------------------------------------------------------
# PDF EXTRACTION
# ---------------------------------------------------------------------------

def _extract_pdf(path: Path) -> list[PageText]:
    """
    Extract text from a PDF page-by-page.

    Strategy:
        1. Try embedded PDF text.
        2. If the extracted text is too short, render the page.
        3. Run Tesseract OCR on the rendered page.
        4. Keep whichever result contains more text.
    """

    pages: list[PageText] = []

    try:
        with fitz.open(path) as doc:

            # Password-protected PDF
            if doc.needs_pass:
                raise OCRError(
                    "PDF is password-protected."
                )

            # Page-count protection
            if (
                doc.page_count
                > settings.max_pages_per_file
            ):
                raise OCRError(
                    "PDF has too many pages "
                    f"(max {settings.max_pages_per_file})."
                )

            if doc.page_count == 0:
                raise OCRError(
                    "The PDF contains no pages."
                )

            for index, page in enumerate(doc, start=1):

                # ----------------------------------------------------------
                # 1. Try embedded PDF text
                # ----------------------------------------------------------

                embedded_text = (
                    page.get_text("text") or ""
                ).strip()

                text = embedded_text
                method = "text_layer"

                # ----------------------------------------------------------
                # 2. OCR fallback for scanned/poor-text pages
                # ----------------------------------------------------------

                if len(embedded_text) < settings.ocr_min_text_chars:

                    pixmap = page.get_pixmap(
                        dpi=settings.ocr_dpi,
                        alpha=False,
                    )

                    if pixmap.width <= 0 or pixmap.height <= 0:
                        raise OCRError(
                            f"Could not render PDF page {index}."
                        )

                    image = Image.frombytes(
                        "RGB",
                        (pixmap.width, pixmap.height),
                        pixmap.samples,
                    )

                    ocr_text = _ocr_image(image)

                    # Keep the more useful result.
                    if len(ocr_text) > len(embedded_text):
                        text = ocr_text
                        method = "ocr"

                pages.append(
                    PageText(
                        page_number=index,
                        text=text,
                        method=method,
                    )
                )

    except fitz.FileDataError as exc:
        raise OCRError(
            "The PDF is corrupted, invalid, or unsupported."
        ) from exc

    except OCRError:
        raise

    return pages


# ---------------------------------------------------------------------------
# IMAGE EXTRACTION
# ---------------------------------------------------------------------------

def _extract_image(path: Path) -> list[PageText]:
    """
    Extract OCR text from an image file.

    Multi-frame TIFF files are treated as multiple pages.
    """

    pages: list[PageText] = []

    try:
        with Image.open(path) as img:

            # Number of frames if available.
            frame_count = getattr(
                img,
                "n_frames",
                1,
            )

            if frame_count > settings.max_pages_per_file:
                raise OCRError(
                    "Image has too many frames "
                    f"(max {settings.max_pages_per_file})."
                )

            for index, frame in enumerate(
                ImageSequence.Iterator(img),
                start=1,
            ):
                frame_copy = frame.copy()

                try:
                    text = _ocr_image(frame_copy)
                finally:
                    frame_copy.close()

                pages.append(
                    PageText(
                        page_number=index,
                        text=text,
                        method="ocr",
                    )
                )

    except UnidentifiedImageError as exc:
        raise OCRError(
            "The uploaded image is not a valid or supported image."
        ) from exc

    return pages


# ---------------------------------------------------------------------------
# TESSERACT OCR
# ---------------------------------------------------------------------------

def _ocr_image(image: Image.Image) -> str:
    """
    Run Tesseract OCR on a PIL image.

    Preprocessing:
        1. Correct EXIF phone-camera orientation.
        2. Convert to grayscale.
        3. Improve contrast.
        4. Run Tesseract using configured language.
    """

    _configure_tesseract()

    # Fix rotation from phone-camera EXIF data.
    image = ImageOps.exif_transpose(image)

    # Convert to grayscale and improve contrast.
    processed = ImageOps.autocontrast(
        image.convert("L")
    )

    try:
        text = pytesseract.image_to_string(
            processed,
            lang=settings.ocr_language,
            config=f"--psm {settings.ocr_page_segmentation_mode}",
        )
    finally:
        processed.close()

    return text.strip()


# ---------------------------------------------------------------------------
# TESSERACT DISCOVERY
# ---------------------------------------------------------------------------

def _configure_tesseract() -> None:
    """
    Find the Tesseract binary.

    Priority:
        1. settings.tesseract_cmd
        2. Common Windows installation path
        3. Tesseract available on PATH
        4. Final fallback to "tesseract"
    """

    configured_path = getattr(
        settings,
        "tesseract_cmd",
        None,
    )

    candidates = [
        configured_path,

        # Common Windows path
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",

        # Common Windows alternate location
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",

        # PATH lookup
        shutil.which("tesseract"),
    ]

    for candidate in candidates:

        if not candidate:
            continue

        candidate = str(candidate)

        # Direct executable path
        candidate_path = Path(candidate)

        if candidate_path.is_file():
            pytesseract.pytesseract.tesseract_cmd = str(
                candidate_path
            )
            return

        # Command available through PATH
        located = shutil.which(candidate)

        if located:
            pytesseract.pytesseract.tesseract_cmd = located
            return

    # Leave the default command so pytesseract raises the
    # appropriate TesseractNotFoundError if unavailable.
    pytesseract.pytesseract.tesseract_cmd = "tesseract"


# ---------------------------------------------------------------------------
# OPTIONAL HELPER
# ---------------------------------------------------------------------------

def combine_pages(pages: list[PageText]) -> str:
    """
    Combine page-level OCR output into one string while preserving
    page boundaries.

    Example:

        [PAGE 1]
        Patient Name: John

        [PAGE 2]
        Blood Test Report
    """

    sections: list[str] = []

    for page in pages:
        text = page.text.strip()

        if not text:
            continue

        sections.append(
            f"[PAGE {page.page_number}]\n{text}"
        )

    return "\n\n".join(sections)


def has_readable_text(pages: list[PageText]) -> bool:
    """
    Return True when at least one page contains meaningful extracted text.
    """

    return any(
        page.text.strip()
        for page in pages
    )