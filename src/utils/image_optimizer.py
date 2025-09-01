#!/usr/bin/env python3
"""
이미지 최적화 유틸리티
- 이미지 크기 조정
- 품질 압축
- 용량 최적화
- 다양한 포맷 지원
"""

import os
from pathlib import Path
from typing import Tuple, Optional, Union
from PIL import Image, ImageOps
import logging

# 로거 설정
logger = logging.getLogger(__name__)


class ImageOptimizer:
    """이미지 최적화 클래스"""

    def __init__(self):
        self.supported_formats = {
            "PNG": {"ext": ".png", "quality_support": True},
            "JPEG": {"ext": ".jpg", "quality_support": True},
            "WEBP": {"ext": ".webp", "quality_support": True},
        }

    def get_image_info(self, image_path: Union[str, Path]) -> dict:
        """이미지 정보 조회"""
        try:
            img = Image.open(image_path)
            file_size = os.path.getsize(image_path)

            return {
                "path": str(image_path),
                "format": img.format,
                "size": img.size,  # (width, height)
                "mode": img.mode,
                "file_size_bytes": file_size,
                "file_size_kb": round(file_size / 1024, 2),
                "file_size_mb": round(file_size / (1024 * 1024), 2),
            }
        except Exception as e:
            logger.error(f"이미지 정보 조회 실패: {e}")
            return None

    def resize_image(
        self,
        image_path: Union[str, Path],
        target_size: Tuple[int, int] = (512, 512),
        maintain_aspect_ratio: bool = True,
        upscale: bool = False,
    ) -> bool:
        """이미지 크기 조정

        Args:
            image_path: 이미지 파일 경로
            target_size: 목표 크기 (width, height)
            maintain_aspect_ratio: 비율 유지 여부
            upscale: 확대 허용 여부 (False면 원본보다 작을 때만 리사이즈)

        Returns:
            성공 여부
        """
        try:
            img = Image.open(image_path)
            original_size = img.size

            # 확대 방지 설정
            if not upscale:
                if (
                    original_size[0] <= target_size[0]
                    and original_size[1] <= target_size[1]
                ):
                    logger.info(
                        f"이미지가 이미 목표 크기보다 작음: {original_size} <= {target_size}"
                    )
                    return True

            if maintain_aspect_ratio:
                # 비율 유지하면서 리사이즈 (fit 방식)
                img.thumbnail(target_size, Image.Resampling.LANCZOS)
            else:
                # 강제 리사이즈 (stretch 방식)
                img = img.resize(target_size, Image.Resampling.LANCZOS)

            # 원본 파일에 덮어쓰기
            img.save(image_path, img.format, optimize=True)

            logger.info(f"이미지 리사이즈 완료: {original_size} -> {img.size}")
            return True

        except Exception as e:
            logger.error(f"이미지 리사이즈 실패: {e}")
            return False

    def compress_image(
        self, image_path: Union[str, Path], quality: int = 75, optimize: bool = True
    ) -> bool:
        """이미지 압축

        Args:
            image_path: 이미지 파일 경로
            quality: 압축 품질 (1-100, 높을수록 고품질)
            optimize: 최적화 여부

        Returns:
            성공 여부
        """
        try:
            img = Image.open(image_path)
            original_size = os.path.getsize(image_path)

            # 이미지 포맷별 압축 설정
            save_kwargs = {"optimize": optimize}

            if img.format in ["JPEG", "WEBP"]:
                save_kwargs["quality"] = quality
            elif img.format == "PNG":
                # PNG는 quality 대신 optimize와 compress_level 사용
                save_kwargs["optimize"] = True
                save_kwargs["compress_level"] = 9  # 최대 압축

            # 압축 적용
            img.save(image_path, img.format, **save_kwargs)

            new_size = os.path.getsize(image_path)
            compression_ratio = (original_size - new_size) / original_size * 100

            logger.info(
                f"이미지 압축 완료: {original_size:,} -> {new_size:,} bytes ({compression_ratio:.1f}% 감소)"
            )
            return True

        except Exception as e:
            logger.error(f"이미지 압축 실패: {e}")
            return False

    def convert_format(
        self,
        image_path: Union[str, Path],
        target_format: str = "WEBP",
        quality: int = 85,
    ) -> Optional[str]:
        """이미지 포맷 변환

        Args:
            image_path: 원본 이미지 경로
            target_format: 목표 포맷 ('PNG', 'JPEG', 'WEBP')
            quality: 변환 품질

        Returns:
            변환된 파일 경로 또는 None
        """
        try:
            if target_format.upper() not in self.supported_formats:
                logger.error(f"지원하지 않는 포맷: {target_format}")
                return None

            img = Image.open(image_path)

            # 새 파일명 생성
            path_obj = Path(image_path)
            new_ext = self.supported_formats[target_format.upper()]["ext"]
            new_path = path_obj.with_suffix(new_ext)

            # JPEG 변환 시 투명도 처리
            if target_format.upper() == "JPEG" and img.mode in ("RGBA", "LA"):
                # 흰색 배경으로 합성
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(
                    img, mask=img.split()[-1] if img.mode == "RGBA" else None
                )
                img = background

            # 포맷별 저장 설정
            save_kwargs = {"optimize": True}
            if self.supported_formats[target_format.upper()]["quality_support"]:
                save_kwargs["quality"] = quality

            # 변환 및 저장
            img.save(new_path, target_format.upper(), **save_kwargs)

            # 원본 파일 삭제 (선택적)
            # os.remove(image_path)

            logger.info(f"포맷 변환 완료: {image_path} -> {new_path}")
            return str(new_path)

        except Exception as e:
            logger.error(f"포맷 변환 실패: {e}")
            return None

    def optimize_for_web(
        self,
        image_path: Union[str, Path],
        max_size: Tuple[int, int] = (800, 800),
        target_file_size_kb: Optional[int] = 100,
        quality_range: Tuple[int, int] = (60, 90),
    ) -> dict:
        """웹 최적화 (크기 + 용량 동시 최적화)

        Args:
            image_path: 이미지 파일 경로
            max_size: 최대 크기 (width, height)
            target_file_size_kb: 목표 파일 크기 (KB)
            quality_range: 품질 범위 (min, max)

        Returns:
            최적화 결과 정보
        """
        try:
            # 원본 정보 저장
            original_info = self.get_image_info(image_path)
            if not original_info:
                return {"success": False, "error": "이미지 정보 조회 실패"}

            # 1단계: 크기 조정
            resize_success = self.resize_image(
                image_path, max_size, maintain_aspect_ratio=True
            )
            if not resize_success:
                return {"success": False, "error": "이미지 리사이즈 실패"}

            # 2단계: 품질 조정으로 파일 크기 최적화
            if target_file_size_kb:
                current_quality = quality_range[1]  # 높은 품질부터 시작
                min_quality = quality_range[0]

                while current_quality >= min_quality:
                    self.compress_image(image_path, quality=current_quality)
                    current_info = self.get_image_info(image_path)

                    if current_info["file_size_kb"] <= target_file_size_kb:
                        break

                    current_quality -= 5  # 품질을 5씩 감소

            else:
                # 목표 파일 크기가 없으면 기본 압축만
                self.compress_image(image_path, quality=quality_range[1])

            # 최종 정보
            final_info = self.get_image_info(image_path)

            return {
                "success": True,
                "original": original_info,
                "optimized": final_info,
                "size_reduction_percent": round(
                    (original_info["file_size_kb"] - final_info["file_size_kb"])
                    / original_info["file_size_kb"]
                    * 100,
                    1,
                ),
                "size_change": f"{original_info['size']} -> {final_info['size']}",
                "file_size_change": f"{original_info['file_size_kb']}KB -> {final_info['file_size_kb']}KB",
            }

        except Exception as e:
            logger.error(f"웹 최적화 실패: {e}")
            return {"success": False, "error": str(e)}

    def batch_optimize(
        self,
        image_directory: Union[str, Path],
        max_size: Tuple[int, int] = (512, 512),
        target_file_size_kb: int = 50,
        file_pattern: str = "*.png",
    ) -> dict:
        """폴더 내 이미지 일괄 최적화

        Args:
            image_directory: 이미지 폴더 경로
            max_size: 최대 크기
            target_file_size_kb: 목표 파일 크기 (KB)
            file_pattern: 파일 패턴 (예: "*.png", "*.jpg")

        Returns:
            일괄 처리 결과
        """
        try:
            directory = Path(image_directory)
            if not directory.exists():
                return {"success": False, "error": "디렉토리가 존재하지 않음"}

            # 이미지 파일 찾기
            image_files = list(directory.glob(file_pattern))
            if not image_files:
                return {
                    "success": False,
                    "error": f'패턴 "{file_pattern}"에 맞는 파일이 없음',
                }

            results = []
            total_original_size = 0
            total_optimized_size = 0

            for image_file in image_files:
                print(f"최적화 중: {image_file.name}")
                result = self.optimize_for_web(
                    image_file,
                    max_size=max_size,
                    target_file_size_kb=target_file_size_kb,
                )

                if result["success"]:
                    total_original_size += result["original"]["file_size_kb"]
                    total_optimized_size += result["optimized"]["file_size_kb"]

                results.append({"file": image_file.name, "result": result})

            overall_reduction = 0
            if total_original_size > 0:
                overall_reduction = round(
                    (total_original_size - total_optimized_size)
                    / total_original_size
                    * 100,
                    1,
                )

            return {
                "success": True,
                "processed_files": len(image_files),
                "total_size_reduction_percent": overall_reduction,
                "total_size_change": f"{total_original_size:.1f}KB -> {total_optimized_size:.1f}KB",
                "details": results,
            }

        except Exception as e:
            logger.error(f"일괄 최적화 실패: {e}")
            return {"success": False, "error": str(e)}


# 편의 함수들
def optimize_single_image(
    image_path: str, max_size: Tuple[int, int] = (512, 512), target_size_kb: int = 50
) -> dict:
    """단일 이미지 최적화 (간편 함수)"""
    optimizer = ImageOptimizer()
    return optimizer.optimize_for_web(
        image_path, max_size=max_size, target_file_size_kb=target_size_kb
    )


def optimize_blog_images(images_directory: str = "data/images") -> dict:
    """블로그 이미지 최적화 (기본 설정)"""
    optimizer = ImageOptimizer()
    return optimizer.batch_optimize(
        image_directory=images_directory,
        max_size=(512, 512),  # 블로그용 적당한 크기
        target_file_size_kb=50,  # 50KB 이하로 압축
        file_pattern="*.png",
    )


if __name__ == "__main__":
    # 테스트 코드
    import sys

    if len(sys.argv) > 1:
        test_image = sys.argv[1]
        print(f"이미지 최적화 테스트: {test_image}")
        result = optimize_single_image(test_image)
        print(f"결과: {result}")
    else:
        print("사용법: python image_optimizer.py <이미지_파일_경로>")
