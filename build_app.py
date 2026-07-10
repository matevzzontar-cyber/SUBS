import os
import sys
import subprocess


def build():
    print("Starting build process for SUBS Real-time Subtitle App...")

    # Define paths
    script_path = os.path.join("examples", "realtime", "subtitle_app.py")

    if not os.path.exists(script_path):
        print(f"Error: Could not find {script_path}")
        sys.exit(1)

    # PyInstaller command
    command = [
        "pyinstaller",
        "--onefile",
        "--name",
        "subs",
        "--hidden-import",
        "textual",
        "--hidden-import",
        "websockets",
        "--hidden-import",
        "numpy",
        "--hidden-import",
        "sounddevice",
        script_path,
    ]

    try:
        subprocess.run(command, check=True)
        print("\nBuild successful! Executable found in 'dist/' directory.")
    except subprocess.CalledProcessError as e:
        print(f"\nBuild failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    build()
