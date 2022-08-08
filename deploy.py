#!/usr/bin/env python
import subprocess
import os

ROOT_DIR = os.path.dirname(__file__)
PYPROJECT_TOML_PATH = os.path.join(ROOT_DIR, "pyproject.toml")

if __name__ == "__main__":
    # Remove old archives
    subprocess.run("rm -rf dist", shell=True)
    # Generating distribution archives
    subprocess.run("python -m build", shell=True)
    # Upload the distribution archives
    subprocess.run("twine upload dist/*", shell=True)
