
def pdm_build_update_setup_kwargs(context, setup_kwargs):
    cffi_modules = ["src/graiax/silkcoder/build_silkv3.py:ffibuilder"]
    setup_kwargs.update(cffi_modules=cffi_modules)
