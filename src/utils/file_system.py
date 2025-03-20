import os

def ensure_directories(directories):
    """
    Ensure that the specified directories exist, creating them if necessary.
    
    Args:
        directories (list): A list of directory paths to check and create if they don't exist.
        
    Returns:
        None
        
    Example:
        ensure_directories(['data/games', 'logs'])
    """
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
