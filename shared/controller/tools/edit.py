"""File editing tool for Stuxbench."""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from enum import Enum

logger = logging.getLogger(__name__)

# max response length to prevent files too long
MAX_RESPONSE_LEN = 16000
TRUNCATED_MESSAGE = "\n<response clipped>\nNOTE: File was too large and has been truncated. Use view_range to see specific sections."


class EditCommand(Enum):
    """Edit commands available."""
    VIEW = "view"
    CREATE = "create"
    STR_REPLACE = "str_replace"


class EditTool:
    """Edit files for vulnerability patching."""
    
    def __init__(self, base_dir: str = "/build/minio"):
        self.base_dir = Path(base_dir)
    
    async def __call__(
        self,
        command: EditCommand,
        path: str,
        old_str: Optional[str] = None,
        new_str: Optional[str] = None,
        file_text: Optional[str] = None,
        view_range: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Execute an edit command.
        
        Args:
            command: The edit command to perform
            path: Path to the file
            old_str: String to replace (for str_replace)
            new_str: Replacement string (for str_replace)
            file_text: Content for new file (for create)
            view_range: Line range to view [start, end]
            
        Returns:
            Result dictionary
        """
        file_path = self.base_dir / path if not Path(path).is_absolute() else Path(path)
        
        try:
            if command == EditCommand.VIEW:
                return await self._view_file(file_path, view_range)
            elif command == EditCommand.CREATE:
                return await self._create_file(file_path, file_text)
            elif command == EditCommand.STR_REPLACE:
                return await self._str_replace(file_path, old_str, new_str)
            else:
                return {"error": f"Unknown command: {command}"}
                
        except Exception as e:
            logger.error(f"Error executing edit command: {e}")
            return {"error": str(e)}
    
    async def _view_file(self, file_path: Path, view_range: Optional[List[int]] = None) -> Dict[str, Any]:
        """View file contents."""
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        content = file_path.read_text()
        lines = content.split('\n')
        
        if view_range:
            start = max(0, view_range[0] - 1)
            end = min(len(lines), view_range[1])
            lines = lines[start:end]
            content = '\n'.join(lines)
        
        # Truncate if content is too large
        truncated = False
        if len(content) > MAX_RESPONSE_LEN:
            content = content[:MAX_RESPONSE_LEN] + TRUNCATED_MESSAGE
            truncated = True
        
        return {
            "content": content,
            "lines": len(lines),
            "path": str(file_path),
            "truncated": truncated
        }
    
    async def _create_file(self, file_path: Path, content: Optional[str] = None) -> Dict[str, Any]:
        """Create a new file."""
        if file_path.exists():
            raise FileExistsError(f"File already exists: {file_path}")
        
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content or "")
        
        return {
            "message": f"File created: {file_path}",
            "path": str(file_path)
        }
    
    async def _str_replace(self, file_path: Path, old_str: str, new_str: str) -> Dict[str, Any]:
        """Replace string in file."""
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not old_str:
            raise ValueError("old_str is required for str_replace")
        
        content = file_path.read_text()
        
        if old_str not in content:
            raise ValueError(f"String not found in file: {old_str[:50]}...")
        
        occurrences = content.count(old_str)
        
        new_content = content.replace(old_str, new_str or "")
        file_path.write_text(new_content)
        
        return {
            "message": f"Replaced {occurrences} occurrence(s)",
            "path": str(file_path),
            "occurrences": occurrences
        }