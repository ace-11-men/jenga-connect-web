"""
Jenga Connect Windows Executable Entry Point
"""

import os
import sys
import django


def main():
    # Get the directory where the exe is located
    if getattr(sys, "frozen", False):
        base_path = os.path.dirname(sys.executable)
        os.chdir(base_path)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    # Set Django settings
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

    # Add project to path
    sys.path.insert(0, base_path)

    # Run Django
    django.setup()
    from django.core.management import execute_from_command_line

    execute_from_command_line(["manage.py", "runserver", "0.0.0.0:8000", "--noreload"])


if __name__ == "__main__":
    main()
