# BIIP-SIH2026 Face Verification Service
import time
import cv2
import numpy as np
from typing import Optional, Tuple
from pathlib import Path

from app.core.config import get_settings
from app.services.biometric.models import (
    FaceVerificationResult,
    FaceMatchResult,
    FaceQualityResult,
    FaceQualityIssue,
)
from app.models.face_result import FaceResult


class FaceVerificationService:
    """Face verification using InsightFace ONNX"""

    def __init__(self):
        self.settings = get_settings()
        self._session = None
        self._det_session = None
        self._initialized = False

    def _init_models(self):
        """Lazy initialization of ONNX models"""
        if self._initialized:
            return

        try:
            import onnxruntime as ort

            # Face recognition model
            model_path = Path(self.settings.INSIGHTFACE_MODEL_PATH)
            if model_path.exists():
                self._session = ort.InferenceSession(
                    str(model_path),
                    providers=['CPUExecutionProvider']
                )

            # Face detection model
            det_path = Path(self.settings.INSIGHTFACE_DET_MODEL_PATH)
            if det_path.exists():
                self._det_session = ort.InferenceSession(
                    str(det_path),
                    providers=['CPUExecutionProvider']
                )

            self._initialized = True
        except Exception as e:
            print(f"Failed to initialize face models: {e}")
            self._initialized = False

    def extract_embedding(self, face_image: np.ndarray) -> Optional[np.ndarray]:
        """Extract face embedding from aligned face image"""
        self._init_models()

        if self._session is None:
            return None

        try:
            # Preprocess: resize to 112x112, normalize
            face_resized = cv2.resize(face_image, (112, 112))
            face_rgb = cv2.cvtColor(face_resized, cv2.COLOR_BGR2RGB)
            face_normalized = (face_rgb.astype(np.float32) / 255.0 - 0.5) / 0.5
            face_input = np.transpose(face_normalized, (2, 0, 1))[np.newaxis, :]

            # Run inference
            input_name = self._session.get_inputs()[0].name
            output = self._session.run(None, {input_name: face_input})

            # Normalize embedding
            embedding = output[0][0]
            embedding = embedding / np.linalg.norm(embedding)

            return embedding.astype(np.float32)
        except Exception as e:
            print(f"Embedding extraction error: {e}")
            return None

    def detect_faces(self, image: np.ndarray) -> list:
        """Detect faces in image using InsightFace detection"""
        self._init_models()

        if self._det_session is None:
            # Fallback to Haar cascade
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            return [{"bbox": [int(x), int(y), int(w), int(h)], "confidence": 0.8} for (x, y, w, h) in faces]

        try:
            # Preprocess for detection
            h, w = image.shape[:2]
            input_size = (640, 640)
            scale = min(input_size[0] / w, input_size[1] / h)
            new_w, new_h = int(w * scale), int(h * scale)
            resized = cv2.resize(image, (new_w, new_h))

            # Pad to 640x640
            padded = np.zeros((640, 640, 3), dtype=np.uint8)
            padded[:new_h, :new_w] = resized

            # Normalize
            input_img = padded.astype(np.float32) / 255.0
            input_img = np.transpose(input_img, (2, 0, 1))[np.newaxis, :]

            # Run inference
            input_name = self._det_session.get_inputs()[0].name
            outputs = self._det_session.run(None, {input_name: input_img})

            # Parse outputs (simplified - actual format depends on model)
            # This is a placeholder - real implementation needs proper post-processing
            return [{"bbox": [100, 100, 200, 200], "confidence": 0.9}]
        except Exception as e:
            print(f"Face detection error: {e}")
            return []

    def assess_quality(self, face_image: np.ndarray) -> FaceQualityResult:
        """Assess face image quality"""
        issues = []
        details = {}

        # Blur detection (Laplacian variance)
        gray = cv2.cvtColor(face_image, cv2.COLOR_BGR2GRAY)
        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        blur_normalized = min(blur_score / 500.0, 1.0)  # Normalize
        details["blur"] = blur_normalized
        if blur_normalized < 0.3:
            issues.append(FaceQualityIssue.BLUR)

        # Brightness/illumination
        brightness = np.mean(gray) / 255.0
        details["illumination"] = brightness
        if brightness < 0.3 or brightness > 0.85:
            issues.append(FaceQualityIssue.ILLUMINATION)

        # Glare detection (high intensity spots)
        glare_mask = gray > 240
        glare_ratio = np.sum(glare_mask) / glare_mask.size
        details["glare"] = glare_ratio
        if glare_ratio > 0.05:
            issues.append(FaceQualityIssue.GLARE)

        # Resolution check
        h, w = face_image.shape[:2]
        details["resolution"] = min(w, h) / 200.0  # Normalize to 200px
        if min(w, h) < 80:
            issues.append(FaceQualityIssue.LOW_RESOLUTION)

        # Pose estimation (simplified - would use landmarks in production)
        # For now, assume frontal if face is roughly centered
        details["pose"] = 0.8

        # Overall quality score
        quality_factors = [
            blur_normalized,
            1.0 - abs(brightness - 0.5) * 2,  # Penalize too dark/bright
            1.0 - glare_ratio * 5,
            min(w, h) / 200.0,
        ]
        overall_score = np.mean(quality_factors)
        overall_score = max(0.0, min(1.0, overall_score))

        is_sufficient = overall_score >= self.settings.FACE_QUALITY_THRESHOLD
        recommendation = None
        if not is_sufficient:
            if FaceQualityIssue.BLUR in issues:
                recommendation = "Recapture: Image is blurry"
            elif FaceQualityIssue.ILLUMINATION in issues:
                recommendation = "Recapture: Poor lighting"
            elif FaceQualityIssue.GLARE in issues:
                recommendation = "Recapture: Glare detected"
            elif FaceQualityIssue.LOW_RESOLUTION in issues:
                recommendation = "Recapture: Resolution too low"
            else:
                recommendation = "Recapture: Quality insufficient"

        return FaceQualityResult(
            overall_score=overall_score,
            issues=issues,
            details=details,
            is_sufficient=is_sufficient,
            recommendation=recommendation,
        )

    def verify(
        self,
        live_face_image: np.ndarray,
        document_face_image: np.ndarray,
    ) -> FaceVerificationResult:
        """Verify live face against document photo"""
        start_time = time.time()

        # Assess quality of both faces
        live_quality = self.assess_quality(live_face_image)
        doc_quality = self.assess_quality(document_face_image)

        # If either quality is too low, return inconclusive
        if not live_quality.is_sufficient or not doc_quality.is_sufficient:
            return FaceVerificationResult(
                match_result=FaceMatchResult.INCONCLUSIVE,
                similarity_score=0.0,
                threshold_used=self.settings.FACE_MATCH_THRESHOLD,
                live_face_quality=live_quality,
                document_face_quality=doc_quality,
                processing_time_ms=(time.time() - start_time) * 1000,
                model_version="insightface-buffalo_l",
            )

        # Extract embeddings
        live_embedding = self.extract_embedding(live_face_image)
        doc_embedding = self.extract_embedding(document_face_image)

        if live_embedding is None or doc_embedding is None:
            return FaceVerificationResult(
                match_result=FaceMatchResult.INCONCLUSIVE,
                similarity_score=0.0,
                threshold_used=self.settings.FACE_MATCH_THRESHOLD,
                live_face_quality=live_quality,
                document_face_quality=doc_quality,
                processing_time_ms=(time.time() - start_time) * 1000,
                model_version="insightface-buffalo_l",
            )

        # Compute cosine similarity
        similarity = np.dot(live_embedding, doc_embedding)
        similarity = float(np.clip(similarity, 0.0, 1.0))

        # Determine match result
        threshold = self.settings.FACE_MATCH_THRESHOLD
        if similarity >= threshold:
            match_result = FaceMatchResult.MATCH
        elif similarity >= threshold - 0.1:
            match_result = FaceMatchResult.INCONCLUSIVE
        else:
            match_result = FaceMatchResult.MISMATCH

        return FaceVerificationResult(
            match_result=match_result,
            similarity_score=similarity,
            threshold_used=threshold,
            live_face_quality=live_quality,
            document_face_quality=doc_quality,
            processing_time_ms=(time.time() - start_time) * 1000,
            model_version="insightface-buffalo_l",
        )

    def extract_document_face(self, document_image: np.ndarray) -> Optional[np.ndarray]:
        """Extract face region from document image"""
        # Use face detection to find face in document
        faces = self.detect_faces(document_image)

        if not faces:
            return None

        # Use the largest face
        best_face = max(faces, key=lambda f: f["bbox"][2] * f["bbox"][3])
        x, y, w, h = best_face["bbox"]

        # Add padding
        padding = int(0.2 * max(w, h))
        x1 = max(0, x - padding)
        y1 = max(0, y - padding)
        x2 = min(document_image.shape[1], x + w + padding)
        y2 = min(document_image.shape[0], y + h + padding)

        face_region = document_image[y1:y2, x1:x2]
        return face_region


# Singleton
face_verification_service = FaceVerificationService()