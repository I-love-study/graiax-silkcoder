def build(setup_kwargs):
    """
    This function is mandatory in order to build the extensions.
    """
    cffi_modules = ["src/graiax/silkcoder/build_silkv3.py:ffibuilder"]
    setup_kwargs.update(cffi_modules=cffi_modules)
