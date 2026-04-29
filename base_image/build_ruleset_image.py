#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import tempfile
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional


DEFAULT_BASE_IMAGE = "light-rules-base:latest"
DEFAULT_API_BASE = "http://localhost:8000/api/v1"


def fetch_ruleset_code(api_base: str, ruleset_id: str) -> str:
    url = f"{api_base}/rulesets/{ruleset_id}/code"
    try:
        with urllib.request.urlopen(url) as response:
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Failed to fetch code for ruleset {ruleset_id}: {e.code} {e.reason}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Failed to connect to API: {e.reason}")


def fetch_ruleset_metadata(api_base: str, ruleset_id: str) -> dict:
    url = f"{api_base}/rulesets/{ruleset_id}/metadata"
    try:
        with urllib.request.urlopen(url) as response:
            data = response.read().decode("utf-8")
            return json.loads(data)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Failed to fetch metadata for ruleset {ruleset_id}: {e.code} {e.reason}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Failed to connect to API: {e.reason}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse metadata JSON: {e}")


def generate_dockerfile_content(base_image: str) -> str:
    return f"""FROM {base_image}

COPY ruleset_code.py /app/ruleset_code.py
COPY ruleset_metadata.json /app/ruleset_metadata.json

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
"""


def build_base_image(
    base_image_dir: Path,
    base_image_tag: str,
    no_cache: bool = False
) -> bool:
    print(f"Building base image: {base_image_tag}")
    print(f"Context directory: {base_image_dir}")
    
    cmd = ["docker", "build", "-t", base_image_tag, "."]
    if no_cache:
        cmd.insert(2, "--no-cache")
    
    try:
        result = subprocess.run(
            cmd,
            cwd=str(base_image_dir),
            check=True,
            capture_output=True,
            text=True
        )
        print("Base image built successfully!")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to build base image: {e}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return False


def build_ruleset_image(
    api_base: str,
    ruleset_id: str,
    image_tag: str,
    base_image: str = DEFAULT_BASE_IMAGE,
    no_cache: bool = False,
    dry_run: bool = False,
    output_dir: Optional[Path] = None
) -> bool:
    print(f"Fetching data for ruleset: {ruleset_id}")
    
    code = fetch_ruleset_code(api_base, ruleset_id)
    metadata = fetch_ruleset_metadata(api_base, ruleset_id)
    
    print(f"  - Code fetched ({len(code)} characters)")
    print(f"  - Metadata fetched: {metadata.get('name', 'unknown')} v{metadata.get('version', {}).get('full', '?.?')}")
    
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        work_dir = output_dir
        print(f"Using output directory: {work_dir}")
    else:
        work_dir = Path(tempfile.mkdtemp(prefix="ruleset_build_"))
        print(f"Using temporary directory: {work_dir}")
    
    try:
        ruleset_code_path = work_dir / "ruleset_code.py"
        ruleset_metadata_path = work_dir / "ruleset_metadata.json"
        dockerfile_path = work_dir / "Dockerfile"
        
        print("Writing ruleset_code.py...")
        ruleset_code_path.write_text(code, encoding="utf-8")
        
        print("Writing ruleset_metadata.json...")
        ruleset_metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
        
        print("Writing Dockerfile...")
        dockerfile_content = generate_dockerfile_content(base_image)
        dockerfile_path.write_text(dockerfile_content, encoding="utf-8")
        
        if dry_run:
            print("\n=== Dry Run Mode ===")
            print(f"Generated files in: {work_dir}")
            print("\nDockerfile content:")
            print(dockerfile_content)
            print("\nTo build manually, run:")
            print(f"  docker build -t {image_tag} {work_dir}")
            return True
        
        print(f"\nBuilding Docker image: {image_tag}")
        print(f"Base image: {base_image}")
        
        cmd = ["docker", "build", "-t", image_tag, "."]
        if no_cache:
            cmd.insert(2, "--no-cache")
        
        result = subprocess.run(
            cmd,
            cwd=str(work_dir),
            check=True,
            capture_output=True,
            text=True
        )
        
        print("Image built successfully!")
        print(result.stdout)
        
        print(f"\n{'='*50}")
        print(f"Image: {image_tag}")
        print(f"To run: docker run -p 8000:8000 {image_tag}")
        print(f"{'='*50}")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Failed to build image: {e}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return False
    finally:
        if not output_dir and work_dir.exists():
            import shutil
            shutil.rmtree(work_dir)
            print(f"Cleaned up temporary directory: {work_dir}")


def main():
    parser = argparse.ArgumentParser(
        description="Build a Docker image for a specific ruleset",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Build base image first
  python build_ruleset_image.py --build-base
  
  # Build a ruleset image (using default API at localhost:8000)
  python build_ruleset_image.py --ruleset-id 550e8400-e29b-41d4-a716-446655440000 --tag my-ruleset:1.0
  
  # Using custom API endpoint
  python build_ruleset_image.py --api-base http://api.example.com:8080/api/v1 --ruleset-id ... --tag ...
  
  # Dry run - generate files without building
  python build_ruleset_image.py --ruleset-id ... --tag ... --dry-run --output-dir ./output
        """
    )
    
    parser.add_argument(
        "--build-base",
        action="store_true",
        help="Build the base image first (required before building ruleset images)"
    )
    
    parser.add_argument(
        "--base-image-tag",
        type=str,
        default=DEFAULT_BASE_IMAGE,
        help=f"Tag for the base image (default: {DEFAULT_BASE_IMAGE})"
    )
    
    parser.add_argument(
        "--ruleset-id",
        type=str,
        help="UUID of the ruleset to build"
    )
    
    parser.add_argument(
        "--tag",
        type=str,
        help="Tag for the resulting Docker image (e.g., my-ruleset:1.0)"
    )
    
    parser.add_argument(
        "--base-image",
        type=str,
        default=DEFAULT_BASE_IMAGE,
        help=f"Base image to use (default: {DEFAULT_BASE_IMAGE})"
    )
    
    parser.add_argument(
        "--api-base",
        type=str,
        default=DEFAULT_API_BASE,
        help=f"Base URL of the API (default: {DEFAULT_API_BASE})"
    )
    
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Do not use Docker cache when building"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate files but do not build the Docker image"
    )
    
    parser.add_argument(
        "--output-dir",
        type=str,
        help="Directory to save generated files (implied with --dry-run)"
    )
    
    args = parser.parse_args()
    
    script_dir = Path(__file__).parent.absolute()
    
    if args.build_base:
        success = build_base_image(
            base_image_dir=script_dir,
            base_image_tag=args.base_image_tag,
            no_cache=args.no_cache
        )
        if not success:
            exit(1)
        if not args.ruleset_id:
            exit(0)
    
    if not args.ruleset_id:
        parser.error("the following arguments are required: --ruleset-id (or use --build-base)")
    
    if not args.tag:
        args.tag = f"ruleset-{args.ruleset_id[:8]}:latest"
        print(f"Using default image tag: {args.tag}")
    
    output_dir = Path(args.output_dir).absolute() if args.output_dir else None
    
    success = build_ruleset_image(
        api_base=args.api_base,
        ruleset_id=args.ruleset_id,
        image_tag=args.tag,
        base_image=args.base_image,
        no_cache=args.no_cache,
        dry_run=args.dry_run,
        output_dir=output_dir
    )
    
    exit(0 if success else 1)


if __name__ == "__main__":
    main()
