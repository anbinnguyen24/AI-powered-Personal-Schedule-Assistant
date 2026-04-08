import os
from deepagents.backends import LocalShellBackend

def make_sandbox_backend():
    """Tạo LocalShellBackend cho sandbox execution.

    Returns:
        LocalShellBackend instance hoặc None nếu không khả dụng.
    """
    try:

        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        return LocalShellBackend(root_dir=root_dir, virtual_mode=True)
    except ImportError:
        return None
