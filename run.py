import sys
from thongssh_gtk.app import main

if __name__ == '__main__':
    """
    This is the entry point for the PyInstaller bundle.
    It imports the main function from the package and runs it.
    """
    exit_status = main()
    sys.exit(exit_status)