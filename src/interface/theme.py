
from rich import box
from .responsive_config import ResponsiveConfig


class UITheme:
    
    PRIMARY = "#00d7ff"      # Bright cyan
    SUCCESS = "#00ff87"      # Bright green
    WARNING = "#ffaf00"      # Orange
    ERROR = "#ff5f87"        # Pink/red
    INFO = "#5fafff"         # Blue
    MUTED = "#6c7086"        # Gray
    ACCENT = "#f5c2e7"       # Light pink
    HIGHLIGHT = "#fab387"    # Peach
    
    ROBOT = "●"
    SUCCESS_CHECK = "✓"
    ERROR_X = "✗"
    INFO_I = "i"
    WARNING_EXCL = "!"
    LOADING = "◐"
    COMPLETED = "✓"
    WORKING = "◯"
    TODO_LIST = "▤"
    
    MAIN_BOX = box.ROUNDED
    SIMPLE_BOX = box.SIMPLE
    
    @classmethod
    def get_responsive_box(cls, responsive_config: ResponsiveConfig) -> box.Box:
        if responsive_config.is_very_narrow:
            return box.SIMPLE  # Simpler borders for narrow terminals
        else:
            return cls.MAIN_BOX
    
    @classmethod
    def get_status_style(cls, status: str) -> tuple[str, str]:
        status_map = {
            'success': (cls.SUCCESS, cls.SUCCESS_CHECK),
            'error': (cls.ERROR, cls.ERROR_X),
            'info': (cls.INFO, cls.INFO_I),
            'warning': (cls.WARNING, cls.WARNING_EXCL),
            'working': (cls.PRIMARY, cls.WORKING),
            'completed': (cls.SUCCESS, cls.COMPLETED)
        }
        return status_map.get(status, (cls.MUTED, ""))
