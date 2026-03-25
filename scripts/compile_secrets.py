#!/usr/bin/env python3
"""
Compile sensitive Stellaris-13 modules to binary extensions.
Converts .py -> .pyd (Windows) or .so (Linux/Mac), then deletes the .py source.
Stubs (< 300 bytes) are left as-is since they contain no IP.
"""
import os, sys, subprocess, shutil, glob

# Modules containing proprietary IP — these get compiled
SENSITIVE = [
    'blueprint_prompts',
    'blueprint_generator',
    'blueprint_engine_extensions',
    'crypto_natal',
    'crypto_transits',
    'crypto_synastry',
    'crypto_prompts',
    'llm_providers',
    'license',
]

STUB_THRESHOLD = 300  # bytes — anything smaller is a dummy stub, skip it


def compile_dir(target_dir):
    """Compile sensitive .py files in target_dir to .so/.pyd, delete .py source."""
    original_dir = os.getcwd()
    target_dir = os.path.abspath(target_dir)
    os.chdir(target_dir)

    to_compile = []
    for mod in SENSITIVE:
        py = f'{mod}.py'
        if os.path.exists(py) and os.path.getsize(py) > STUB_THRESHOLD:
            to_compile.append(py)

    if not to_compile:
        print(f"    No real modules to compile (all stubs or missing)")
        os.chdir(original_dir)
        return 0

    print(f"    Compiling {len(to_compile)} sensitive modules...")

    # Write temporary Cython setup script
    setup_code = (
        "from setuptools import setup, Extension\n"
        "from Cython.Build import cythonize\n"
        f"setup(ext_modules=cythonize({to_compile!r},\n"
        "    compiler_directives={'language_level': '3'},\n"
        "    quiet=True))\n"
    )
    with open('_cython_setup.py', 'w') as f:
        f.write(setup_code)

    # Run Cython compilation
    try:
        subprocess.check_call(
            [sys.executable, '_cython_setup.py', 'build_ext', '--inplace'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
    except subprocess.CalledProcessError as e:
        print(f"    WARNING: Cython compilation failed: {e}")
        print(f"    Sensitive modules will remain as .py (not compiled)")
        os.chdir(original_dir)
        return 0

    # Verify compilation succeeded, then delete source
    compiled = 0
    for py_file in to_compile:
        mod_name = py_file.replace('.py', '')
        # Look for compiled output: .pyd (Windows) or .so (Linux/Mac)
        found = glob.glob(f'{mod_name}*.pyd') + glob.glob(f'{mod_name}*.so')
        if found:
            os.remove(py_file)
            compiled += 1
            print(f"      Compiled: {py_file} -> {found[0]}")
        else:
            print(f"      KEPT: {py_file} (compilation produced no output)")

    # Cleanup build artifacts
    if os.path.exists('_cython_setup.py'):
        os.remove('_cython_setup.py')
    if os.path.exists('build'):
        shutil.rmtree('build', ignore_errors=True)
    for c_file in glob.glob('*.c'):
        os.remove(c_file)

    os.chdir(original_dir)
    print(f"    {compiled}/{len(to_compile)} modules compiled to binary")
    return compiled


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: compile_secrets.py <tier_directory> [<tier_directory> ...]")
        sys.exit(1)

    for d in sys.argv[1:]:
        if os.path.isdir(d):
            print(f"\n  Processing: {d}")
            compile_dir(d)
        else:
            print(f"  Skipping (not a directory): {d}")
