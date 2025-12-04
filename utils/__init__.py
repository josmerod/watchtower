from src.utils import *  # re-export for legacy imports


# Dashboard compatibility shims (lazy attributes to avoid unused import warnings)
def __getattr__(name):
    if name in {
        "get_data_path",
        "file_exists",
        "dir_exists",
        "parse_date_universal",
        "log_missing_file",
        "handle_data_loading_error",
    }:
        from src.web.dashboard import utils as _dash_utils

        return getattr(_dash_utils, name)
    raise AttributeError(name)
