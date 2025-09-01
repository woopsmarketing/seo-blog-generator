#!/usr/bin/env python3
"""
이미지 최적화 독립 실행 스크립트
- 기존 이미지 파일들을 일괄 최적화
- 명령행에서 직접 실행 가능
"""

import sys
import argparse
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.utils.image_optimizer import ImageOptimizer, optimize_blog_images


def main():
    parser = argparse.ArgumentParser(description="이미지 최적화 도구")
    parser.add_argument(
        "--directory",
        "-d",
        default="data/images",
        help="이미지 폴더 경로 (기본값: data/images)",
    )
    parser.add_argument(
        "--max-size",
        "-s",
        nargs=2,
        type=int,
        default=[512, 512],
        metavar=("WIDTH", "HEIGHT"),
        help="최대 이미지 크기 (기본값: 512 512)",
    )
    parser.add_argument(
        "--target-size-kb",
        "-t",
        type=int,
        default=50,
        help="목표 파일 크기 (KB, 기본값: 50)",
    )
    parser.add_argument(
        "--pattern", "-p", default="*.png", help="파일 패턴 (기본값: *.png)"
    )
    parser.add_argument("--single", "-f", help="단일 파일 최적화")

    args = parser.parse_args()

    print("🎨 이미지 최적화 도구")
    print("=" * 50)

    optimizer = ImageOptimizer()

    if args.single:
        # 단일 파일 최적화
        print(f"📄 단일 파일 최적화: {args.single}")

        if not Path(args.single).exists():
            print(f"❌ 파일이 존재하지 않습니다: {args.single}")
            return

        result = optimizer.optimize_for_web(
            args.single,
            max_size=tuple(args.max_size),
            target_file_size_kb=args.target_size_kb,
        )

        if result["success"]:
            print(f"✅ 최적화 완료!")
            print(f"   크기 변화: {result['size_change']}")
            print(f"   용량 변화: {result['file_size_change']}")
            print(f"   용량 감소: {result['size_reduction_percent']}%")
        else:
            print(f"❌ 최적화 실패: {result['error']}")

    else:
        # 폴더 일괄 최적화
        print(f"📁 폴더 일괄 최적화: {args.directory}")
        print(f"   최대 크기: {args.max_size[0]}x{args.max_size[1]}")
        print(f"   목표 용량: {args.target_size_kb}KB")
        print(f"   파일 패턴: {args.pattern}")
        print()

        result = optimizer.batch_optimize(
            image_directory=args.directory,
            max_size=tuple(args.max_size),
            target_file_size_kb=args.target_size_kb,
            file_pattern=args.pattern,
        )

        if result["success"]:
            print(f"✅ 일괄 최적화 완료!")
            print(f"   처리된 파일: {result['processed_files']}개")
            print(f"   전체 용량 변화: {result['total_size_change']}")
            print(f"   전체 용량 감소: {result['total_size_reduction_percent']}%")
            print()
            print("📋 세부 결과:")

            for detail in result["details"]:
                file_result = detail["result"]
                if file_result["success"]:
                    print(
                        f"   ✅ {detail['file']}: {file_result['file_size_change']} ({file_result['size_reduction_percent']}% 감소)"
                    )
                else:
                    print(f"   ❌ {detail['file']}: {file_result['error']}")
        else:
            print(f"❌ 일괄 최적화 실패: {result['error']}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️ 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n💥 예상치 못한 오류: {e}")
        import traceback

        traceback.print_exc()
