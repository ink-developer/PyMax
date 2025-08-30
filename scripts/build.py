import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def build_package(clean: bool = False):
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent.resolve()
    dist_path = project_root / "dist"

    if clean and dist_path.exists() and dist_path.is_dir():
        shutil.rmtree(dist_path)

    try:
        subprocess.run([sys.executable, "-m", "build"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
        sys.exit()

    if dist_path.exists() and dist_path.is_dir():
        print("Build successful. Files in dist:")
        for f in dist_path.iterdir():
            print("  ", f.name)
    else:
        print("Build failed.")


def main():
    parser = argparse.ArgumentParser(description="Build the pymax Python package")
    parser.add_argument(
        "-c", "--clean", action="store_true", help="Clean previous builds before building."
    )
    args = parser.parse_args()
    build_package(clean=args.clean)


if __name__ == "__main__":
    main()
