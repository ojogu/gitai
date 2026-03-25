"""
Git diff extraction module.
This module handles extracting and processing git diff information.
"""

import subprocess
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class DiffFile:
    """Represents a file in a git diff."""
    path: str
    status: str  # 'added', 'modified', 'deleted', 'renamed'
    additions: int
    deletions: int
    content: Optional[str] = None


class DiffExtractor:
    """Extracts git diff information."""
    
    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path
    
    def get_staged_diff(self) -> List[DiffFile]:
        """Get diff of staged changes."""
        try:
            # Get list of staged files
            result = subprocess.run(
                ["git", "diff", "--cached", "--name-status"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            
            files = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('\t', 1)
                    if len(parts) == 2:
                        status, path = parts
                        files.append(DiffFile(
                            path=path,
                            status=status,
                            additions=0,
                            deletions=0
                        ))
            
            return files
