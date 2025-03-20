import os

def get_project_root():
    """
    Get the absolute path to the project root directory.
    
    Returns:
        str: Absolute path to the project root directory
    """
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

def ensure_directories(directories):
    """
    Ensure that the specified directories exist, creating them if necessary.
    All paths are relative to the project root.
    
    Args:
        directories (list): A list of directory paths to check and create if they don't exist.
        
    Returns:
        None
        
    Example:
        ensure_directories(['data/games', 'logs'])
    """
    project_root = get_project_root()
    for directory in directories:
        full_path = os.path.join(project_root, directory)
        if not os.path.exists(full_path):
            os.makedirs(full_path)
