# BIIP-SIH2026 OCR Engine
import time
import cv2
import numpy as np
from typing import List, Optional, Dict, Any
from PIL import Image

from app.core.config import get_settings
from app.services.ocr.models import OCRResult, OCRField, OCRSource, MRZResult, BarcodeResult


class OCREngine:
    """OCR Engine using PaddleOCR with MRZ and barcode support"""

    def __init__(self):
        self.settings = get_settings()
        self._ocr = None
        self._initialized = False

    def _init_ocr(self):
        """Lazy initialization of PaddleOCR"""
        if self._initialized:
            return

        try:
            from paddleocr import PaddleOCR
            self._ocr = PaddleOCR(
                use_angle_cls=True,
                lang=self.settings.PADDLE_OCR_LANG,
                use_gpu=self.settings.PADDLE_OCR_USE_GPU,
                show_log=False,
            )
            self._initialized = True
        except Exception as e:
            print(f"Failed to initialize PaddleOCR: {e}")
            self._initialized = False

    def extract_text(self, image_path: str) -> OCRResult:
        """Extract text from document image"""
        start_time = time.time()

        # Load image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not load image: {image_path}")

        # Initialize OCR if needed
        self._init_ocr()

        fields = []
        raw_text_parts = []

        if self._ocr is not None:
            try:
                result = self._ocr.ocr(image_path, cls=True)
                if result and result[0]:
                    for line in result[0]:
                        bbox, (text, confidence) = line
                        # Convert bbox to [x, y, w, h]
                        xs = [p[0] for p in bbox]
                        ys = [p[1] for p in bbox]
                        x, y = int(min(xs)), int(min(ys))
                        w, h = int(max(xs) - min(xs)), int(max(ys) - min(ys))

                        field = OCRField(
                            field_name="text_line",
                            value=text,
                            confidence=confidence,
                            source=OCRSource.PADDLEOCR,
                            bbox=[x, y, w, h],
                        )
                        fields.append(field)
                        raw_text_parts.append(text)
            except Exception as e:
                print(f"OCR error: {e}")

        processing_time = (time.time() - start_time) * 1000

        return OCRResult(
            document_id="",  # Set by caller
            fields=fields,
            raw_text="\n".join(raw_text_parts) if raw_text_parts else None,
            processing_time_ms=processing_time,
            model_version="paddleocr-2.7.3",
        )

    def extract_mrz(self, image_path: str) -> MRZResult:
        """Extract and parse MRZ from document"""
        # For prototype, we'll use a simplified MRZ extraction
        # Real implementation would use specialized MRZ detection

        # Try to detect MRZ region (bottom of document for passports)
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not load image: {image_path}")

        h, w = image.shape[:2]

        # MRZ is typically in bottom 20% for TD3 passports
        mrz_region = image[int(h * 0.8):, :]

        # Use OCR on MRZ region
        self._init_ocr()
        mrz_text = ""

        if self._ocr is not None:
            try:
                result = self._ocr.ocr(mrz_region, cls=True)
                if result and result[0]:
                    for line in result[0]:
                        _, (text, _) = line
                        mrz_text += text + "\n"
            except Exception as e:
                print(f"MRZ OCR error: {e}")

        # Parse MRZ (simplified)
        parsed_fields, check_digits_valid, check_digit_details = self._parse_mrz(mrz_text)

        return MRZResult(
            document_id="",
            mrz_raw=mrz_text.strip(),
            mrz_type="TD3",  # Assume passport
            fields=parsed_fields,
            check_digits_valid=check_digits_valid,
            check_digit_details=check_digit_details,
        )

    def _parse_mrz(self, mrz_text: str) -> tuple:
        """Parse MRZ text into fields (simplified)"""
        lines = [l.strip() for l in mrz_text.split("\n") if l.strip()]

        if len(lines) < 2:
            return {}, False, {}

        # Simplified TD3 parsing (2 lines of 44 chars each)
        fields = {}
        check_digit_details = {}
        all_valid = True

        if len(lines) >= 2:
            line1 = lines[0]
            line2 = lines[1]

            if len(line1) >= 44 and len(line2) >= 44:
                # Line 1: P<COD>SURNAME<<GIVEN<NAMES<<<<<<<<<<<
                doc_type = line1[0]
                country = line1[2:5]
                names = line1[5:44].split("<<")
                surname = names[0].replace("<", " ")
                given_names = names[1].replace("<", " ") if len(names) > 1 else ""

                # Line 2: PASSPORTNUM<<CODYYYYMMDD<SEXYYYYMMDD<COD<<<<<<<<<<<<<<<NUMBER
                passport_num = line2[0:9].replace("<", "")
                nationality = line2[10:13]
                dob = line2[13:19]
                sex = line2[20]
                expiry = line2[21:27]
                personal_num = line2[28:42].replace("<", "")

                # Check digits (simplified validation)
                def compute_check_digit(s: str) -> int:
                    weights = [7, 3, 1] * 10
                    total = sum(w * (int(c) if c.isdigit() else (ord(c) - 55)) for w, c in zip(weights, s))
                    return total % 10

                # Validate passport number check digit (position 9)
                if len(line2) > 9:
                    expected = compute_check_digit(line2[0:9])
                    actual = int(line2[9]) if line2[9].isdigit() else -1
                    check_digit_details["passport_number"] = expected == actual
                    all_valid = all_valid and (expected == actual)

                # Validate DOB check digit (position 19)
                if len(line2) > 19:
                    expected = compute_check_digit(line2[13:19])
                    actual = int(line2[19]) if line2[19].isdigit() else -1
                    check_digit_details["date_of_birth"] = expected == actual
                    all_valid = all_valid and (expected == actual)

                # Validate expiry check digit (position 27)
                if len(line2) > 27:
                    expected = compute_check_digit(line2[21:27])
                    actual = int(line2[27]) if line2[27].isdigit() else -1
                    check_digit_details["date_of_expiry"] = expected == actual
                    all_valid = all_valid and (expected == actual)

                fields = {
                    "document_type": doc_type,
                    "issuing_country": country,
                    "surname": surname,
                    "given_names": given_names,
                    "passport_number": passport_num,
                    "nationality": nationality,
                    "date_of_birth": self._format_date(dob),
                    "sex": sex,
                    "date_of_expiry": self._format_date(expiry),
                    "personal_number": personal_num,
                }

        return fields, all_valid, check_digit_details

    def _format_date(self, date_str: str) -> str:
        """Format YYMMDD to YYYY-MM-DD"""
        if len(date_str) == 6 and date_str.isdigit():
            year = int(date_str[:2])
            # Assume 19xx for years > 30, 20xx for years <= 30
            year = 1900 + year if year > 30 else 2000 + year
            month = date_str[2:4]
            day = date_str[4:6]
            return f"{year}-{month}-{day}"
        return date_str

    def extract_barcodes(self, image_path: str) -> List[BarcodeResult]:
        """Extract barcodes/QR codes from document"""
        from pyzbar import pyzbar

        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not load image: {image_path}")

        results = []
        barcodes = pyzbar.decode(image)

        for barcode in barcodes:
            data = barcode.data.decode("utf-8", errors="ignore")
            parsed = self._parse_barcode_data(data, barcode.type)

            result = BarcodeResult(
                document_id="",
                barcode_type=barcode.type,
                data=data,
                parsed_fields=parsed,
                confidence=1.0,  # pyzbar doesn't provide confidence
            )
            results.append(result)

        return results

    def _parse_barcode_data(self, data: str, barcode_type: str) -> Dict[str, str]:
        """Parse barcode data based on type"""
        parsed = {"raw": data}

        # Try to parse common formats
        if barcode_type == "QRCODE":
            # Could be JSON, URL, or structured text
            try:
                import json
                parsed = json.loads(data)
            except:
                # Try key=value pairs
                for line in data.split("\n"):
                    if "=" in line:
                        k, v = line.split("=", 1)
                        parsed[k.strip()] = v.strip()

        return parsed


# Singleton instance
ocr_engine = OCREngine()