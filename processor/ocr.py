"""
OCR processing utilities
Supports OCR for images and text extraction from PDFs
"""

import logging
import os
from typing import Any, Dict

import pdfplumber
import pytesseract
from PIL import Image

# Setup logging
logger = logging.getLogger(__name__)


class OCRProcessor:
    """Performs OCR for image and PDF attachments"""

    SUPPORTED_IMAGE_TYPES = {".png", ".jpg", ".jpeg"}
    SUPPORTED_PDF_TYPES = {".pdf"}

    def __init__(self, temp_dir: str = "./data/tmp"):
        """
        Initialize OCR processor

        Args:
            temp_dir: Directory for temporary files
        """
        self.temp_dir = temp_dir
        os.makedirs(temp_dir, exist_ok=True)
        logger.info("OCRProcessor initialized with temp_dir: %s", temp_dir)

    def extract_from_image(self, image_path: str) -> str:
        """
        Extract text from an image file using Tesseract OCR

        Args:
            image_path: Path to the image file

        Returns:
            Extracted text as a string
        """
        if not os.path.exists(image_path):
            logger.error("Image file not found: %s", image_path)
            raise FileNotFoundError(f"File not found: {image_path}")

        try:
            with Image.open(image_path) as img:
                text = pytesseract.image_to_string(img)
                cleaned = text.strip()
                logger.info(
                    "Extracted text from image %s (%d chars)",
                    image_path,
                    len(cleaned),
                )
                if not cleaned:
                    logger.warning("No text detected in image: %s", image_path)
                return cleaned
        except Exception as e:
            logger.error(
                "Failed to extract text from image %s: %s",
                image_path,
                e,
                exc_info=True,
            )
            raise

    def extract_from_pdf(self, pdf_path: str) -> str:
        """
        Extract text from a PDF file using pdfplumber

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Extracted text as a string
        """
        if not os.path.exists(pdf_path):
            logger.error("PDF file not found: %s", pdf_path)
            raise FileNotFoundError(f"File not found: {pdf_path}")

        try:
            with pdfplumber.open(pdf_path) as pdf:
                texts = []
                for i, page in enumerate(pdf.pages):
                    try:
                        page_text = page.extract_text() or ""
                        page_text = page_text.strip()
                        texts.append(page_text)
                        logger.debug(
                            "Extracted text from PDF page %d (%d chars)",
                            i + 1,
                            len(page_text),
                        )
                    except Exception as page_error:
                        logger.warning(
                            "Failed to extract text from PDF page %d (%s): %s",
                            i + 1,
                            pdf_path,
                            page_error,
                        )

                combined = "\n\n".join(filter(None, texts)).strip()
                logger.info(
                    "Extracted text from PDF %s (%d chars across %d pages)",
                    pdf_path,
                    len(combined),
                    len(pdf.pages),
                )
                if not combined:
                    logger.warning("No text detected in PDF: %s", pdf_path)
                return combined
        except Exception as e:
            logger.error(
                "Failed to extract text from PDF %s: %s",
                pdf_path,
                e,
                exc_info=True,
            )
            raise

    def process_attachment(self, filepath: str) -> Dict[str, Any]:
        """
        Detect file type and extract text accordingly

        Args:
            filepath: Path to attachment file

        Returns:
            Dictionary with success flag, extracted text, and error message (if any)
        """
        result: Dict[str, Any] = {"success": False, "text": "", "error": None}

        if not filepath:
            logger.error("process_attachment called with empty filepath")
            result["error"] = "No file path provided"
            return result

        if not os.path.exists(filepath):
            logger.error("Attachment file not found: %s", filepath)
            result["error"] = "File does not exist"
            return result

        ext = os.path.splitext(filepath)[1].lower()
        logger.info("Processing attachment: %s (type: %s)", filepath, ext or "unknown")

        try:
            if ext in self.SUPPORTED_IMAGE_TYPES:
                result["text"] = self.extract_from_image(filepath)
                result["success"] = True
            elif ext in self.SUPPORTED_PDF_TYPES:
                result["text"] = self.extract_from_pdf(filepath)
                result["success"] = True
            else:
                logger.warning("Unsupported attachment type: %s", filepath)
                result["error"] = f"Unsupported file type: {ext or 'unknown'}"
        except FileNotFoundError as e:
            result["error"] = str(e)
        except Exception as e:
            result["error"] = str(e)
            logger.error(
                "Unhandled error processing attachment %s: %s",
                filepath,
                e,
                exc_info=True,
            )

        return result

    def cleanup_temp_files(self, *paths: str) -> None:
        """
        Remove temporary files or directories created during OCR

        Args:
            *paths: File or directory paths to remove
        """
        for path in paths:
            if not path:
                continue
            if os.path.isdir(path):
                self._cleanup_directory(path)
            else:
                self._remove_file(path)

    def _cleanup_directory(self, directory: str) -> None:
        """Remove files inside a directory and attempt to delete it"""
        for root, dirs, files in os.walk(directory, topdown=False):
            for file in files:
                self._remove_file(os.path.join(root, file))
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                try:
                    os.rmdir(dir_path)
                    logger.info("Removed temporary directory: %s", dir_path)
                except OSError:
                    logger.debug(
                        "Directory not removed (may not be empty or in use): %s", dir_path
                    )

        try:
            os.rmdir(directory)
            logger.info("Removed temporary directory: %s", directory)
        except OSError:
            logger.debug("Directory not removed (may not be empty or in use): %s", directory)

    @staticmethod
    def _remove_file(path: str) -> None:
        """Remove a single file with error handling"""
        if not os.path.exists(path):
            return

        try:
            os.remove(path)
            logger.info("Removed temporary file: %s", path)
        except Exception as e:
            logger.warning("Failed to remove temporary file %s: %s", path, e)
