#parser
# parser.py
from unidiff import PatchSet
from typing import List, Dict, Any
import os

def parse_git_diff(diff_text: str) -> List[Dict[str, Any]]:
    """
    Parse a git diff string into structured file changes.
    
    Args:
        diff_text (str): Output of `git diff` or `git diff --cached`
        
    Returns:
        List[Dict]: List of file-level structured diffs
    """
    patch = PatchSet(diff_text.splitlines())
    files = []

    for patched_file in patch:
        file_change = {
            "file": patched_file.path,
            "type": "added" if patched_file.is_added_file else
                    "deleted" if patched_file.is_removed_file else
                    "modified",
            "added_lines": [],
            "removed_lines": [],
            "meta": {
                "insertions": patched_file.added,
                "deletions": patched_file.removed
            }
        }

        for hunk in patched_file:
            for line in hunk:
                # Only parse added/removed lines
                if line.is_added:
                    file_change["added_lines"].append(line.value.rstrip("\n"))
                elif line.is_removed:
                    file_change["removed_lines"].append(line.value.rstrip("\n"))

        files.append(file_change)

    return files


# Example usage
if __name__ == "__main__":
    # Get diff from staged files
    diff_text = os.popen("git diff --cached").read()
    parsed_files = parse_git_diff(diff_text)
    for f in parsed_files:
        print(f)