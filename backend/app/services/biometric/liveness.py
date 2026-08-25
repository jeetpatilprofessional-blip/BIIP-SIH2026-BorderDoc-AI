# BIIP-SIH2026 Liveness Service (Prototype)
import time
import cv2
import numpy as np
from typing import Optional, Dict, Any, List
from enum import Enum

from app.services.biometric.models import LivenessResultDetail, LivenessResult


class LivenessMethod(str, Enum):
    PASSIVE_TEXTURE = "passive_texture"
    ACTIVE_CHALLENGE = "active_challenge"
    COMBINED = "combined"


class LivenessService:
    """Prototype liveness detection - NOT production certified"""

    def __init__(self):
        self.challenge_frames = 0
        self.challenge_type = None
        self.baseline_frames = []

    def check_liveness(
        self,
        face_image: np.ndarray,
        previous_frames: Optional[List[np.ndarray]] = None,
        challenge: Optional[str] = None,
    ) -> LivenessResultDetail:
        """
        Check liveness using passive texture analysis and optional active challenge.

        PROTOTYPE LIMITATIONS:
        - Not iBeta certified
        - Limited presentation attack detection
        - Vulnerable to high-quality masks, deepfakes, screen replays
        - Requires controlled conditions for reliable results
        """
        start_time = time.time()

        # Passive texture analysis
        texture_result = self._passive_texture_check(face_image)

        # Active challenge if provided
        challenge_result = None
        if challenge and previous_frames:
            challenge_result = self._active_challenge_check(face_image, previous_frames, challenge)

        # Combine results
        if challenge_result:
            # Combined method
            live_score = (texture_result["score"] + challenge_result["score"]) / 2
            method = LivenessMethod.COMBINED
            details = {
                "passive_texture": texture_result,
                "active_challenge": challenge_result,
            }
            challenge_passed = challenge_result["passed"]
        else:
            # Passive only
            live_score = texture_result["score"]
            method = LivenessMethod.PASSIVE_TEXTURE
            details = {"passive_texture": texture_result}
            challenge_passed = None

        # Determine result
        if live_score >= 0.7:
            result = LivenessResult.LIVE
        elif live_score >= 0.4:
            result = LivenessResult.INCONCLUSIVE
        else:
            result = LivenessResult.SPOOF_SUSPECTED

        confidence = live_score

        return LivenessResultDetail(
            result=result,
            confidence=confidence,
            method=method.value,
            details=details,
            challenge_passed=challenge_passed,
            processing_time_ms=(time.time() - start_time) * 1000,
        )

    def _passive_texture_check(self, face_image: np.ndarray) -> Dict[str, Any]:
        """Passive texture/liveness analysis using image quality metrics"""
        gray = cv2.cvtColor(face_image, cv2.COLOR_BGR2GRAY)

        # 1. Local Binary Pattern (LBP) variance - real skin has texture
        lbp = self._compute_lbp(gray)
        lbp_var = np.var(lbp)
        lbp_score = min(lbp_var / 500.0, 1.0)

        # 2. Frequency domain analysis - screens have moiré patterns
        f_transform = np.fft.fft2(gray)
        f_shift = np.fft.fftshift(f_transform)
        magnitude = np.log(np.abs(f_shift) + 1)

        # Check for regular grid patterns (screen moiré)
        h, w = magnitude.shape
        center_y, center_x = h // 2, w // 2
        # Look for peaks at regular intervals
        moiré_score = self._detect_moire(magnitude)

        # 3. Color diversity - printed photos have limited color gamut
        color_diversity = self._check_color_diversity(face_image)

        # 4. Specular reflection analysis - real skin has specific reflection patterns
        specular_score = self._check_specular_reflections(gray)

        # Combine scores (weighted)
        weights = {
            "lbp": 0.3,
            "moire": 0.25,
            "color": 0.25,
            "specular": 0.2,
        }

        combined_score = (
            weights["lbp"] * lbp_score +
            weights["moire"] * (1.0 - moiré_score) +  # Invert: moiré = bad
            weights["color"] * color_diversity +
            weights["specular"] * specular_score
        )

        return {
            "score": float(np.clip(combined_score, 0.0, 1.0)),
            "lbp_variance": float(lbp_var),
            "lbp_score": lbp_score,
            "moire_score": float(moiré_score),
            "color_diversity": color_diversity,
            "specular_score": specular_score,
        }

    def _compute_lbp(self, gray: np.ndarray) -> np.ndarray:
        """Compute Local Binary Pattern"""
        h, w = gray.shape
        lbp = np.zeros((h - 2, w - 2), dtype=np.uint8)

        for i in range(1, h - 1):
            for j in range(1, w - 1):
                center = gray[i, j]
                code = 0
                # 8 neighbors
                neighbors = [
                    gray[i-1, j-1], gray[i-1, j], gray[i-1, j+1],
                    gray[i, j+1], gray[i+1, j+1], gray[i+1, j],
                    gray[i+1, j-1], gray[i, j-1],
                ]
                for k, n in enumerate(neighbors):
                    if n >= center:
                        code |= (1 << k)
                lbp[i-1, j-1] = code

        return lbp

    def _detect_moire(self, magnitude: np.ndarray) -> float:
        """Detect moiré patterns in frequency domain"""
        h, w = magnitude.shape
        center_y, center_x = h // 2, w // 2

        # Sample radial profile
        max_r = min(center_x, center_y)
        profile = []

        for r in range(10, max_r, 5):
            # Sample circle at radius r
            vals = []
            for theta in np.linspace(0, 2*np.pi, 36):
                y = int(center_y + r * np.sin(theta))
                x = int(center_x + r * np.cos(theta))
                if 0 <= y < h and 0 <= x < w:
                    vals.append(magnitude[y, x])
            if vals:
                profile.append(np.mean(vals))

        if len(profile) < 3:
            return 0.0

        # Look for periodic peaks in profile
        profile = np.array(profile)
        # Simple peak detection
        peaks = 0
        for i in range(1, len(profile) - 1):
            if profile[i] > profile[i-1] and profile[i] > profile[i+1]:
                if profile[i] > np.mean(profile) + np.std(profile):
                    peaks += 1

        # More peaks = more likely moiré
        moiré_score = min(peaks / 5.0, 1.0)
        return moiré_score

    def _check_color_diversity(self, image: np.ndarray) -> float:
        """Check color diversity - real skin has more color variation"""
        # Convert to HSV
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        # Skin tone hue range (approximately)
        skin_mask = cv2.inRange(hsv, np.array([0, 20, 50]), np.array([25, 255, 255]))

        if np.sum(skin_mask) == 0:
            return 0.5

        # Get skin pixels
        skin_pixels = image[skin_mask > 0]

        if len(skin_pixels) < 10:
            return 0.5

        # Color variance in skin region
        color_var = np.var(skin_pixels, axis=0)
        total_var = np.sum(color_var)

        # Normalize (empirical)
        diversity_score = min(total_var / 10000.0, 1.0)

        return diversity_score

    def _check_specular_reflections(self, gray: np.ndarray) -> float:
        """Check for specular reflections characteristic of real skin"""
        # Real skin has small, distributed specular highlights
        # Printed photos/screens have different reflection patterns

        # Find bright spots
        _, bright = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(bright, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if len(contours) == 0:
            return 0.3

        # Analyze highlight distribution
        highlight_count = len(contours)
        total_area = sum(cv2.contourArea(c) for c in contours)

        # Many small highlights = real skin
        # Few large highlights = printed/glossy
        avg_area = total_area / highlight_count if highlight_count > 0 else 0

        if highlight_count > 10 and avg_area < 20:
            return 0.8  # Many small highlights
        elif highlight_count > 3 and avg_area < 100:
            return 0.6
        else:
            return 0.3

    def _active_challenge_check(
        self,
        current_frame: np.ndarray,
        previous_frames: List[np.ndarray],
        challenge: str,
    ) -> Dict[str, Any]:
        """Active challenge-response liveness check"""
        if len(previous_frames) < 2:
            return {"score": 0.0, "passed": False, "reason": "Insufficient frames"}

        # Simple motion detection between frames
        motion_scores = []
        for prev in previous_frames[-3:]:
            diff = cv2.absdiff(
                cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY),
                cv2.cvtColor(prev, cv2.COLOR_BGR2GRAY)
            )
            motion = np.mean(diff) / 255.0
            motion_scores.append(motion)

        avg_motion = np.mean(motion_scores)

        # Check for challenge-specific motion
        challenge_passed = False
        if challenge == "blink":
            # Blink causes rapid change then return
            if len(motion_scores) >= 3:
                # Look for spike pattern
                if motion_scores[1] > motion_scores[0] * 1.5 and motion_scores[2] < motion_scores[1]:
                    challenge_passed = True
        elif challenge == "turn_left" or challenge == "turn_right":
            # Head turn causes sustained motion
            if avg_motion > 0.05:
                challenge_passed = True
        elif challenge == "nod":
            # Vertical motion
            if avg_motion > 0.03:
                challenge_passed = True

        score = 0.8 if challenge_passed else 0.2
        score = score * min(avg_motion * 10, 1.0)  # Scale by motion amount

        return {
            "score": float(np.clip(score, 0.0, 1.0)),
            "passed": challenge_passed,
            "avg_motion": float(avg_motion),
            "challenge": challenge,
        }

    def get_random_challenge(self) -> str:
        """Get a random liveness challenge"""
        challenges = ["blink", "turn_left", "turn_right", "nod"]
        import random
        return random.choice(challenges)


# Singleton
liveness_service = LivenessService()