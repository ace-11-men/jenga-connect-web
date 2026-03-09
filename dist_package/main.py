"""
Jenga Connect Windows Executable Entry Point
"""

import os
import sys
import django


def main():
    # Get the directory where the exe is located
    if getattr(sys, "frozen", False):
        # Running as compiled executable
        base_path = os.path.dirname(sys.executable)
    else:
        # Running as script
        base_path = os.path.dirname(os.path.abspath(__file__))

    # Change to the exe directory
    os.chdir(base_path)

    # Add to path
    sys.path.insert(0, base_path)

    # Set Django settings
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

    # Run Django
    django.setup()
    from django.core.management import execute_from_command_line

    print("=" * 50)
    print("Jenga Connect - Starting Server")
    print("=" * 50)
    print("Open your browser at: http://localhost:8000")
    print("=" * 50)

    execute_from_command_line(["manage.py", "runserver", "0.0.0.0:8000", "--noreload"])


if __name__ == "__main__":
    main()
