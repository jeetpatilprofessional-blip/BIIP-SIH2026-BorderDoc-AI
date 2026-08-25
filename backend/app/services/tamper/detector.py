# BIIP-SIH2026 Tamper Detector
import time
import cv2
import numpy as np
from typing import List, Dict, Any, Optional
from sqlmodel import Session, select

from app.services.tamper.models import (
    TamperResult,
    TamperLayerResult,
    SuspiciousRegion,
    TamperLayer,
    TamperSeverity,
)
from app.models.document import Document
from app.models.document_field import DocumentField
from app.core.database import get_session


class TamperDetector:
    """Multi-layer tamper detection"""

    def __init__(self, session: Session):
        self.session = session

    def detect(self, document_id: str) -> TamperResult:
        """Run all tamper detection layers"""
        start_time = time.time()

        document = self.session.get(Document, document_id)
        if not document:
            raise ValueError(f"Document not found: {document_id}")

        # Load image
        image = cv2.imread(document.file_path)
        if image is None:
            raise ValueError(f"Could not load image: {document.file_path}")

        # Get document fields for cross-field consistency
        fields = self.session.exec(
            select(DocumentField).where(DocumentField.document_id == document_id)
        ).all()
        field_map = {f.field_name: f for f in fields}

        all_regions = []
        all_reasons = []
        layer_results = []

        # Layer 1: Cross-field consistency
        cross_field_result = self._check_cross_field_consistency(field_map, document)
        layer_results.append(cross_field_result)
        all_regions.extend(cross_field_result.suspicious_regions)
        all_reasons.extend(cross_field_result.reasons)

        # Layer 2: Image analysis
        image_result = self._analyze_image(image, document)
        layer_results.append(image_result)
        all_regions.extend(image_result.suspicious_regions)
        all_reasons.extend(image_result.reasons)

        # Layer 3: Photo consistency (if face available)
        photo_result = self._check_photo_consistency(document_id, image, field_map)
        layer_results.append(photo_result)
        all_regions.extend(photo_result.suspicious_regions)
        all_reasons.extend(photo_result.reasons)

        # Overall assessment
        tampered = any(r.tampered for r in layer_results)
        overall_confidence = max((r.confidence for r in layer_results), default=0.0)

        processing_time = (time.time() - start_time) * 1000

        return TamperResult(
            document_id=document_id,
            tampered=tampered,
            overall_confidence=overall_confidence,
            layers=layer_results,
            suspicious_regions=all_regions,
            reasons=all_reasons,
            processing_time_ms=processing_time,
            model_versions={
                "cross_field": "rule-based",
                "image_analysis": "opencv-4.10",
                "photo_consistency": "prototype",
            },
        )

    def _check_cross_field_consistency(
        self, field_map: Dict[str, DocumentField], document: Document
    ) -> TamperLayerResult:
        """Check consistency between OCR, MRZ, and barcode fields"""
        reasons = []
        regions = []
        tampered = False
        confidence = 0.0

        # Define field mappings for comparison
        comparisons = [
            ("passport_number", "mrz_passport_number", "Passport number"),
            ("date_of_birth", "mrz_date_of_birth", "Date of birth"),
            ("date_of_expiry", "mrz_date_of_expiry", "Date of expiry"),
            ("nationality", "mrz_nationality", "Nationality"),
            ("surname", "mrz_surname", "Surname"),
            ("given_names", "mrz_given_names", "Given names"),
        ]

        mismatches = 0
        for ocr_field, mrz_field, label in comparisons:
            ocr_val = field_map.get(ocr_field, DocumentField(value="")).value
            mrz_val = field_map.get(mrz_field, DocumentField(value="")).value

            if ocr_val and mrz_val:
                if self._normalize(ocr_val) != self._normalize(mrz_val):
                    mismatches += 1
                    reasons.append(f"{label} mismatch: OCR='{ocr_val}' vs MRZ='{mrz_val}'")
                    # Add region for the field if bbox available
                    ocr_field_obj = field_map.get(ocr_field)
                    if ocr_field_obj and ocr_field_obj.bbox_x is not None:
                        regions.append(SuspiciousRegion(
                            x=ocr_field_obj.bbox_x,
                            y=ocr_field_obj.bbox_y,
                            width=ocr_field_obj.bbox_w or 100,
                            height=ocr_field_obj.bbox_h or 30,
                            layer=TamperLayer.CROSS_FIELD,
                            severity=TamperSeverity.HIGH,
                            description=f"{label} mismatch between OCR and MRZ",
                            confidence=0.9,
                        ))

        if mismatches > 0:
            tampered = True
            confidence = min(0.5 + (mismatches * 0.15), 0.95)

        return TamperLayerResult(
            layer=TamperLayer.CROSS_FIELD,
            tampered=tampered,
            confidence=confidence,
            suspicious_regions=regions,
            reasons=reasons,
            details={"mismatches": mismatches, "comparisons": len(comparisons)},
        )

    def _analyze_image(self, image: np.ndarray, document: Document) -> TamperLayerResult:
        """Analyze image for manipulation artifacts"""
        reasons = []
        regions = []
        tampered = False
        confidence = 0.0

        h, w = image.shape[:2]
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # 1. Error Level Analysis (ELA) - simplified
        ela_regions = self._error_level_analysis(image)
        if ela_regions:
            tampered = True
            confidence = max(confidence, 0.7)
            regions.extend(ela_regions)
            reasons.append("Error Level Analysis indicates potential manipulation")

        # 2. Copy-move detection (simplified - block matching)
        copy_move_regions = self._detect_copy_move(gray)
        if copy_move_regions:
            tampered = True
            confidence = max(confidence, 0.6)
            regions.extend(copy_move_regions)
            reasons.append("Possible copy-move forgery detected")

        # 3. Metadata check (EXIF)
        meta_issues = self._check_metadata(document.file_path)
        if meta_issues:
            reasons.extend(meta_issues)
            confidence = max(confidence, 0.4)

        # 4. Compression artifacts
        compression_issues = self._check_compression_artifacts(image)
        if compression_issues:
            reasons.extend(compression_issues)
            confidence = max(confidence, 0.3)

        return TamperLayerResult(
            layer=TamperLayer.IMAGE_ANALYSIS,
            tampered=tampered,
            confidence=confidence,
            suspicious_regions=regions,
            reasons=reasons,
            details={
                "ela_regions": len(ela_regions),
                "copy_move_regions": len(copy_move_regions),
                "metadata_issues": len(meta_issues),
            },
        )

    def _error_level_analysis(self, image: np.ndarray) -> List[SuspiciousRegion]:
        """Simplified Error Level Analysis"""
        regions = []

        # Save as JPEG with quality 90, reload, compare
        try:
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                cv2.imwrite(tmp.name, image, [cv2.IMWRITE_JPEG_QUALITY, 90])
                recompressed = cv2.imread(tmp.name)

            if recompressed is not None:
                diff = cv2.absdiff(image.astype(np.float32), recompressed.astype(np.float32))
                diff_gray = cv2.cvtColor(diff.astype(np.uint8), cv2.COLOR_BGR2GRAY)
                _, thresh = cv2.threshold(diff_gray, 10, 255, cv2.THRESH_BINARY)

                # Find contours of high-difference regions
                contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                for cnt in contours:
                    area = cv2.contourArea(cnt)
                    if area > 500:  # Filter small noise
                        x, y, w, h = cv2.boundingRect(cnt)
                        regions.append(SuspiciousRegion(
                            x=x, y=y, width=w, height=h,
                            layer=TamperLayer.IMAGE_ANALYSIS,
                            severity=TamperSeverity.MEDIUM,
                            description="High ELA difference - possible edit",
                            confidence=0.6,
                        ))
        except Exception as e:
            print(f"ELA error: {e}")

        return regions

    def _detect_copy_move(self, gray: np.ndarray) -> List[SuspiciousRegion]:
        """Simplified copy-move detection using block matching"""
        regions = []

        try:
            # Divide into blocks and compare
            block_size = 32
            h, w = gray.shape
            blocks = {}

            for y in range(0, h - block_size, block_size // 2):
                for x in range(0, w - block_size, block_size // 2):
                    block = gray[y:y+block_size, x:x+block_size]
                    # Simple hash of block
                    block_hash = hash(block.tobytes())

                    if block_hash in blocks:
                        # Potential copy-move
                        px, py = blocks[block_hash]
                        regions.append(SuspiciousRegion(
                            x=x, y=y, width=block_size, height=block_size,
                            layer=TamperLayer.IMAGE_ANALYSIS,
                            severity=TamperSeverity.MEDIUM,
                            description=f"Similar block found at ({px},{py})",
                            confidence=0.5,
                        ))
                    else:
                        blocks[block_hash] = (x, y)
        except Exception as e:
            print(f"Copy-move detection error: {e}")

        return regions[:5]  # Limit to top 5

    def _check_metadata(self, file_path: str) -> List[str]:
        """Check image metadata for anomalies"""
        issues = []

        try:
            from PIL import Image
            img = Image.open(file_path)
            exif = img.getexif()

            if exif:
                # Check for editing software
                software = exif.get(305)  # Software tag
                if software and any(s in str(software).lower() for s in ["photoshop", "gimp", "editor", "paint"]):
                    issues.append(f"Edited with software: {software}")

                # Check for missing camera info (scanned documents may not have this)
                make = exif.get(271)  # Make
                model = exif.get(272)  # Model
                if not make and not model:
                    issues.append("No camera metadata - possible scanned/edited image")
        except Exception as e:
            issues.append(f"Metadata read error: {e}")

        return issues

    def _check_compression_artifacts(self, image: np.ndarray) -> List[str]:
        """Check for double compression or unusual artifacts"""
        issues = []

        # Check for JPEG grid artifacts (simplified)
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            # DCT-based detection would go here
            # For prototype, just note if image dimensions suggest editing
            h, w = gray.shape
            if w % 8 != 0 or h % 8 != 0:
                issues.append("Image dimensions not multiple of 8 - possible crop/edit")
        except:
            pass

        return issues

    def _check_photo_consistency(
        self,
        document_id: str,
        document_image: np.ndarray,
        field_map: Dict[str, DocumentField],
    ) -> TamperLayerResult:
        """Check if document photo matches live face (placeholder for integration)"""
        reasons = []
        regions = []
        tampered = False
        confidence = 0.0

        # This would compare document photo region with live face embedding
        # For now, we check if there's a face region detected in document

        # Try to detect face in document using Haar cascade (basic)
        try:
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            gray = cv2.cvtColor(document_image, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)

            if len(faces) == 0:
                reasons.append("No face detected in document image")
                confidence = 0.3
            elif len(faces) > 1:
                reasons.append(f"Multiple faces detected in document: {len(faces)}")
                confidence = 0.5
                for (x, y, w, h) in faces:
                    regions.append(SuspiciousRegion(
                        x=x, y=y, width=w, height=h,
                        layer=TamperLayer.PHOTO_CONSISTENCY,
                        severity=TamperSeverity.MEDIUM,
                        description="Face region in document",
                        confidence=0.7,
                    ))
            else:
                # Single face found - good
                (x, y, w, h) = faces[0]
                regions.append(SuspiciousRegion(
                    x=x, y=y, width=w, height=h,
                    layer=TamperLayer.PHOTO_CONSISTENCY,
                    severity=TamperSeverity.LOW,
                    description="Document photo region",
                    confidence=0.8,
                ))
        except Exception as e:
            reasons.append(f"Face detection error: {e}")

        return TamperLayerResult(
            layer=TamperLayer.PHOTO_CONSISTENCY,
            tampered=tampered,
            confidence=confidence,
            suspicious_regions=regions,
            reasons=reasons,
            details={"faces_detected": len(faces) if 'faces' in locals() else 0},
        )

    def _normalize(self, value: str) -> str:
        """Normalize for comparison"""
        import re
        normalized = re.sub(r"\s+", " ", value.strip().upper())
        normalized = normalized.replace("Ø", "O").replace("Å", "A").replace("Ä", "AE")
        normalized = normalized.replace("Ö", "OE").replace("Ü", "UE").replace("ß", "SS")
        return normalized


def detect_tampering(document_id: str, session: Session) -> TamperResult:
    """Convenience function"""
    detector = TamperDetector(session)
    return detector.detect(document_id)