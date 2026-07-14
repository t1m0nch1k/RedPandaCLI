from __future__ import annotations

import fnmatch
import re
from typing import Any


class PermissionRule:
    """
    A rule that matches a tool call and returns a decision.
    
    Example: 
    Rule(tool="shell", action=None, args_pattern=r"npm \\*", decision=PermissionDecision.ALLOW)
    """
    def __init__(
        self, 
        tool: str, 
        action: str | None = None, 
        args_pattern: str | None = None, 
        decision: PermissionDecision = 'PermissionDecision.ASK'
    ) -> None:
        self.tool = tool
        self.action = action
        self.args_pattern = args_pattern
        self.decision = decision

    def matches(self, tool_name: str, args: dict[str, Any]) -> bool:
        if self.tool != tool_name:
            return False
        
        if self.action and args.get("action") != self.action:
            return False
            
        if self.args_pattern:
            # We try to match the pattern against the string representation of args
            # or a specific key if it's common (like 'command' in shell)
            search_string = ""
            if "command" in args:
                search_string = args["command"]
            elif "action" in args:
                search_string = args["action"]
            else:
                search_string = str(args)
                
            if not (re.search(self.args_pattern, search_string) or fnmatch.fnmatch(search_string, self.args_pattern)):
                return False
                
        return True
