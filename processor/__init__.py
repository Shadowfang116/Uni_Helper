"""
Processor module
Handles async email processing with queueing and OCR utilities
"""

from processor.queue import ProcessingQueue
from processor.ocr import OCRProcessor

__all__ = ['ProcessingQueue', 'OCRProcessor']
