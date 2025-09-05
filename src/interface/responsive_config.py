
from typing import Optional, List
from rich.console import Console


class ResponsiveConfig:
    
    def __init__(self, console: Console):
        self.console = console
        self._update_dimensions()
    
    def _update_dimensions(self) -> None:
        self.width = self.console.width
        self.height = self.console.height
    
    @property
    def is_narrow(self) -> bool:
        self._update_dimensions()
        return self.width < 80
    
    @property
    def is_very_narrow(self) -> bool:
        self._update_dimensions()
        return self.width < 60
    
    @property
    def is_wide(self) -> bool:
        self._update_dimensions()
        return self.width > 120
    
    @property
    def is_very_wide(self) -> bool:
        self._update_dimensions()
        return self.width > 160
    
    @property
    def is_short(self) -> bool:
        self._update_dimensions()
        return self.height < 24
    
    def get_panel_width(self, preferred_width: int = None) -> Optional[int]:
        self._update_dimensions()
        if preferred_width:
            return min(preferred_width, self.width - 4)  # Leave margin
        
        if self.is_very_narrow:
            return self.width - 2
        elif self.is_narrow:
            return self.width - 4
        elif self.is_wide:
            return min(100, self.width - 8)
        else:
            return min(80, self.width - 6)
    
    def get_padding(self) -> tuple:
        self._update_dimensions()
        if self.is_very_narrow:
            return (0, 1)
        elif self.is_narrow:
            return (1, 1)
        elif self.is_wide:
            return (2, 4)
        else:
            return (1, 2)
    
    def get_text_wrap_width(self) -> int:
        self._update_dimensions()
        if self.is_very_narrow:
            return max(30, self.width - 8)
        elif self.is_narrow:
            return max(50, self.width - 12)
        else:
            return max(70, self.width - 16)
    
    def truncate_text(self, text: str, max_length: Optional[int] = None) -> str:
        if max_length is None:
            max_length = self.get_text_wrap_width()
        
        if len(text) <= max_length:
            return text
        
        if max_length > 10:
            truncated = text[:max_length - 3]
            last_space = truncated.rfind(' ')
            if last_space > max_length // 2:  # Only break at space if it's not too early
                return truncated[:last_space] + "..."
        
        return text[:max_length - 3] + "..."
    
    def get_table_column_widths(self, num_columns: int) -> List[Optional[int]]:
        self._update_dimensions()
        available_width = self.width - 6  # Account for borders and padding
        
        if self.is_very_narrow and num_columns > 2:
            return [8, None] + [None] * (num_columns - 2)
        elif self.is_narrow:
            base_width = available_width // num_columns
            return [max(6, base_width)] * num_columns
        else:
            return [None] * num_columns
