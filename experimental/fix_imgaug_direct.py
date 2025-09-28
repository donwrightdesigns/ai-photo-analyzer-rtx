#!/usr/bin/env python3
"""
Direct fix for imgaug compatibility with NumPy 2.0+
This script patches the imgaug.py file directly without importing imgaug first.
"""

import os
import sys
import shutil
from pathlib import Path

def get_imgaug_path():
    """Get the imgaug installation path directly"""
    # Standard conda/miniconda path
    conda_path = Path("C:/Users/don/miniconda3/Lib/site-packages/imgaug/imgaug.py")
    if conda_path.exists():
        return conda_path
    
    # Try to find it in Python path
    import site
    for site_dir in site.getsitepackages():
        potential_path = Path(site_dir) / "imgaug" / "imgaug.py"
        if potential_path.exists():
            return potential_path
    
    return None

def create_backup(file_path):
    """Create a backup of the original file"""
    backup_path = file_path.with_suffix('.py.backup')
    if not backup_path.exists():
        shutil.copy2(file_path, backup_path)
        print(f"Backup created: {backup_path}")
    else:
        print(f"Backup already exists: {backup_path}")

def apply_numpy2_fix(file_path):
    """Apply the NumPy 2.0 compatibility fix"""
    
    # Read the original file
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if already patched
    if 'numpy 2.0 compatibility fix' in content.lower():
        print("File appears to already be patched.")
        return True
    
    # Define the replacement code
    old_code = '''# to check if a dtype instance is among these dtypes, use e.g.
# `dtype.type in  NP_FLOAT_TYPES` do not just use `dtype in NP_FLOAT_TYPES` as
# that would fail
NP_FLOAT_TYPES = set(np.sctypes["float"])
NP_INT_TYPES = set(np.sctypes["int"])
NP_UINT_TYPES = set(np.sctypes["uint"])'''

    new_code = '''# to check if a dtype instance is among these dtypes, use e.g.
# `dtype.type in  NP_FLOAT_TYPES` do not just use `dtype in NP_FLOAT_TYPES` as
# that would fail
# NumPy 2.0 compatibility fix - np.sctypes was removed
try:
    # Try the old way first (NumPy < 2.0)
    NP_FLOAT_TYPES = set(np.sctypes["float"])
    NP_INT_TYPES = set(np.sctypes["int"])
    NP_UINT_TYPES = set(np.sctypes["uint"])
except AttributeError:
    # NumPy 2.0+ fallback - define explicit dtype sets
    NP_FLOAT_TYPES = {np.float16, np.float32, np.float64}
    if hasattr(np, 'float128'):
        NP_FLOAT_TYPES.add(np.float128)
    if hasattr(np, 'longdouble'):
        NP_FLOAT_TYPES.add(np.longdouble)
    
    NP_INT_TYPES = {np.int8, np.int16, np.int32, np.int64}
    if hasattr(np, 'longlong'):
        NP_INT_TYPES.add(np.longlong)
    
    NP_UINT_TYPES = {np.uint8, np.uint16, np.uint32, np.uint64}
    if hasattr(np, 'ulonglong'):
        NP_UINT_TYPES.add(np.ulonglong)'''

    # Apply the fix
    if old_code in content:
        new_content = content.replace(old_code, new_code)
        
        # Write the patched file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print("Successfully applied NumPy 2.0 compatibility fix!")
        return True
    else:
        print("Error: Could not find the expected code pattern to replace.")
        print("Searching for alternative patterns...")
        
        # Try alternative pattern matching
        if 'NP_FLOAT_TYPES = set(np.sctypes["float"])' in content:
            # Replace each line individually
            content = content.replace(
                'NP_FLOAT_TYPES = set(np.sctypes["float"])',
                '''# NumPy 2.0 compatibility fix
try:
    NP_FLOAT_TYPES = set(np.sctypes["float"])
except AttributeError:
    NP_FLOAT_TYPES = {np.float16, np.float32, np.float64}
    if hasattr(np, 'float128'):
        NP_FLOAT_TYPES.add(np.float128)
    if hasattr(np, 'longdouble'):
        NP_FLOAT_TYPES.add(np.longdouble)'''
            )
            
            content = content.replace(
                'NP_INT_TYPES = set(np.sctypes["int"])',
                '''try:
    NP_INT_TYPES = set(np.sctypes["int"])
except AttributeError:
    NP_INT_TYPES = {np.int8, np.int16, np.int32, np.int64}
    if hasattr(np, 'longlong'):
        NP_INT_TYPES.add(np.longlong)'''
            )
            
            content = content.replace(
                'NP_UINT_TYPES = set(np.sctypes["uint"])',
                '''try:
    NP_UINT_TYPES = set(np.sctypes["uint"])
except AttributeError:
    NP_UINT_TYPES = {np.uint8, np.uint16, np.uint32, np.uint64}
    if hasattr(np, 'ulonglong'):
        NP_UINT_TYPES.add(np.ulonglong)'''
            )
            
            # Write the patched file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("Successfully applied NumPy 2.0 compatibility fix (alternative method)!")
            return True
            
        return False

def main():
    """Main function"""
    print("ImgAug NumPy 2.0 Compatibility Fix (Direct)")
    print("=" * 45)
    
    # Find imgaug path
    imgaug_path = get_imgaug_path()
    if not imgaug_path or not imgaug_path.exists():
        print(f"Error: Could not find imgaug.py at expected location")
        print("Checked locations:")
        print("- C:/Users/don/miniconda3/Lib/site-packages/imgaug/imgaug.py")
        return False
    
    print(f"Found imgaug.py at: {imgaug_path}")
    
    # Create backup
    create_backup(imgaug_path)
    
    # Apply fix
    success = apply_numpy2_fix(imgaug_path)
    
    if success:
        print("\nFix applied successfully!")
        print("You can now run your application again.")
        return True
    else:
        print("\nFix could not be applied.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
