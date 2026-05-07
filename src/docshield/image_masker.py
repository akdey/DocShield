import os
import zipfile
import shutil
import logging
from pathlib import Path

logger = logging.getLogger("DocShield.ImageMasker")

class ImageMasker:
    def __init__(self):
        self.reader = None
        self._initialized = False

    def _initialize_ocr(self):
        if self._initialized:
            return True
            
        try:
            import easyocr
            # Initialize with English, disable GPU by default to ensure portability
            self.reader = easyocr.Reader(['en'], gpu=False, verbose=False)
            self._initialized = True
            return True
        except ImportError:
            logger.warning("EasyOCR is not installed. Image masking is disabled.")
            return False
        except Exception as e:
            logger.warning(f"Failed to initialize EasyOCR: {e}")
            return False

    def anonymize_docx_images(self, docx_path: Path, docshield_instance, session_vault_dir: Path):
        """
        Unzips a .docx file, processes all images with OCR, redacts sensitive text,
        saves the original images to the session vault, and re-zips the document.
        """
        if not self._initialize_ocr():
            return
            
        import cv2
        import numpy as np
        from PIL import Image, ImageDraw, ImageFont
        import io

        temp_dir = docx_path.with_suffix(".temp_unzip")
        images_zip_path = session_vault_dir / f"{docx_path.stem}_images.zip"
        
        try:
            # 1. Unzip docx
            with zipfile.ZipFile(docx_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
                
            media_dir = temp_dir / "word" / "media"
            if not media_dir.exists():
                return # No images
                
            modified_any = False
            original_images_to_save = {}
            
            # 2. Process Images
            for img_path in media_dir.glob("image*.*"):
                if img_path.suffix.lower() not in ['.png', '.jpg', '.jpeg']:
                    continue
                    
                # Read image
                img_bytes = img_path.read_bytes()
                
                # Run OCR
                results = self.reader.readtext(img_bytes)
                if not results:
                    continue
                    
                # Combine all text for context-aware scanning
                full_text = " \n ".join([res[1] for res in results])
                
                # Scan
                spans = docshield_instance.scan(full_text)
                if not spans:
                    continue
                    
                # We have sensitive data! Generate replacements
                _, replacements = docshield_instance.masker.mask_with_replacements(full_text, spans)
                # replacements: [(start, end, token)]
                
                # Map original text to tokens
                target_strings = {full_text[start:end]: token for start, end, token in replacements}
                
                # We need to draw on the image
                pil_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                draw = ImageDraw.Draw(pil_img)
                
                # Load a default font if possible, else default
                try:
                    font = ImageFont.truetype("arial.ttf", 15)
                except IOError:
                    font = ImageFont.load_default()
                    
                img_modified = False
                
                for bbox, box_text, prob in results:
                    # Check if any target string is in this box's text
                    for orig, token in target_strings.items():
                        if orig in box_text or box_text in orig:
                            # Redact this bounding box!
                            # bbox format: [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
                            p1, p2, p3, p4 = bbox
                            x0, y0 = min(p[0] for p in bbox), min(p[1] for p in bbox)
                            x1, y1 = max(p[0] for p in bbox), max(p[1] for p in bbox)
                            
                            # Draw white box
                            draw.rectangle([x0, y0, x1, y1], fill=(255, 255, 255))
                            
                            # Draw token
                            draw.text((x0, y0), token, fill=(0, 0, 0), font=font)
                            img_modified = True
                            
                if img_modified:
                    # Save original image to dictionary for the vault backup
                    original_images_to_save[img_path.name] = img_bytes
                    
                    # Save modified image back to temp_dir
                    pil_img.save(img_path)
                    modified_any = True
                    
            if modified_any:
                # 3. Save originals to secure zip
                with zipfile.ZipFile(images_zip_path, 'w') as zf:
                    for name, data in original_images_to_save.items():
                        zf.writestr(name, data)
                        
                # 4. Re-zip docx
                # Create a new docx replacing the old one
                with zipfile.ZipFile(docx_path, 'w', zipfile.ZIP_DEFLATED) as docx_zip:
                    for root, _, files in os.walk(temp_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, temp_dir)
                            docx_zip.write(file_path, arcname)

        except Exception as e:
            logger.error(f"Image masking failed: {e}")
            
        finally:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

    def deanonymize_docx_images(self, docx_path: Path, session_vault_dir: Path):
        """
        Unzips the docx, restores original images from the vault, and re-zips.
        """
        images_zip_path = session_vault_dir / f"{docx_path.stem}_images.zip"
        if not images_zip_path.exists():
            return # No images were masked for this document
            
        temp_dir = docx_path.with_suffix(".temp_unzip")
        
        try:
            # 1. Unzip docx
            with zipfile.ZipFile(docx_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
                
            media_dir = temp_dir / "word" / "media"
            
            # 2. Extract original images directly into media folder
            with zipfile.ZipFile(images_zip_path, 'r') as img_zip:
                img_zip.extractall(media_dir)
                
            # 3. Re-zip docx
            with zipfile.ZipFile(docx_path, 'w', zipfile.ZIP_DEFLATED) as docx_zip:
                for root, _, files in os.walk(temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, temp_dir)
                        docx_zip.write(file_path, arcname)
                        
        except Exception as e:
            logger.error(f"Image restoration failed: {e}")
            
        finally:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
