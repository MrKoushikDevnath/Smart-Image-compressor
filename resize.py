from PIL import Image

def resize_image(img: Image.Image, custom_width: int = None, custom_height: int = None) -> Image.Image:
    """
    Resizes a PIL image based on given parameters.
    Maintains high image quality using LANCZOS filter.
    """
    orig_w, orig_h = img.size
    
    if not custom_width and not custom_height:
        return img.copy()

    new_w = custom_width if custom_width else orig_w
    new_h = custom_height if custom_height else orig_h

    if custom_width and not custom_height:
        # Calculate height based on width proportionally
        ratio = custom_width / float(orig_w)
        new_h = int(orig_h * ratio)
    elif custom_height and not custom_width:
        # Calculate width based on height proportionally
        ratio = custom_height / float(orig_h)
        new_w = int(orig_w * ratio)
            
    # Resize directly (will stretch if both W and H provided)
    # Ensure dimensions are at least 1x1
    new_w = max(1, new_w)
    new_h = max(1, new_h)
    return img.resize((new_w, new_h), Image.Resampling.LANCZOS)
