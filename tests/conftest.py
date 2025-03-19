import sys
import os
import glob

# Find the build directory dynamically
build_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'build'))
lib_dirs = glob.glob(os.path.join(build_dir, 'lib.*'))
if lib_dirs:
    # Add the first lib directory to the Python path
    sys.path.insert(0, lib_dirs[0])
else:
    # If no lib directory is found, try to find the wheel file
    wheel_files = glob.glob(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'dist', '*.whl'))
    if wheel_files:
        # Extract the wheel file to a temporary directory
        import tempfile
        import zipfile
        temp_dir = tempfile.mkdtemp()
        with zipfile.ZipFile(wheel_files[0], 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        sys.path.insert(0, temp_dir)
