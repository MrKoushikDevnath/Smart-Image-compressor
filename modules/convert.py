import os
import logging
from .compressor import compress_image
from PIL import Image

def convert_and_save(img: Image.Image, output_path: str, target_format: str, target_size_kb: float = None) -> dict:
    """
    Handles conversion and saving.
    Returns a dict with stats: {'final_size': bytes, 'quality': int, 'success': bool}
    """
    try:
        quality, img_bytes = compress_image(img, target_format, target_size_kb)
        if not img_bytes:
            return {'success': False, 'error': 'Compression failed to produce output.'}
            
        with open(output_path, 'wb') as f:
            f.write(img_bytes)
            
        return {
            'success': True,
            'final_size': len(img_bytes),
            'quality': quality
        }
    except Exception as e:
        logging.error(f"Conversion/Save error: {e}")
        return {'success': False, 'error': str(e)}

