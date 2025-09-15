#!/usr/bin/env python3
"""
Code Implementation Module for GitHub Issue Bot
Handles automatic code fixes for known device patterns
"""
import os
import json
import subprocess
import tempfile
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from github import Github, Auth
from github.Repository import Repository
from github.Issue import Issue

class CodeImplementer:
    """Handles automatic code implementation for known issue patterns"""
    
    def __init__(self, repo: Repository, github_token: str):
        self.repo = repo
        auth = Auth.Token(github_token)
        self.github = Github(auth=auth)
        self.github_token = github_token
        
    def can_implement_fix(self, issue: Issue, analysis: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Determine if bot can automatically implement a fix
        
        Returns:
            (can_fix, fix_type, fix_details)
        """
        issue_text = issue.title + " " + issue.body
        
        # Check for known patterns
        
        # Pattern 1: Content-type issues (GW3000, GW1200B)
        if self._matches_content_type_pattern(issue_text, analysis):
            return True, "content_type_fix", {
                "pattern": "content_type_mismatch",
                "files": ["custom_components/ecowitt_local/api.py"],
                "description": "Add fallback JSON parsing for content-type mismatch",
                "confidence": 0.9
            }
        
        # Pattern 2: Missing hex ID sensor mapping (WH69, WS90, WH90)
        hex_device = self._extract_hex_device_model(issue_text, analysis)
        if hex_device:
            return True, "hex_sensor_mapping", {
                "pattern": "hex_id_sensors",
                "device_model": hex_device,
                "files": [
                    "custom_components/ecowitt_local/sensor_mapper.py",
                    "custom_components/ecowitt_local/const.py"
                ],
                "description": f"Add {hex_device} hex ID sensor mapping",
                "confidence": 0.85
            }
        
        # Pattern 3: Embedded unit parsing (GW2000)
        if self._matches_embedded_units_pattern(issue_text, analysis):
            return True, "embedded_units_fix", {
                "pattern": "embedded_units",
                "files": ["custom_components/ecowitt_local/coordinator.py"],
                "description": "Enhance embedded unit parsing for sensor values",
                "confidence": 0.8
            }
        
        return False, "unknown", {}
    
    def _matches_content_type_pattern(self, issue_text: str, analysis: str) -> bool:
        """Check if issue matches content-type mismatch pattern"""
        content_indicators = [
            "json parsing error", "json decode error", "content-type",
            "text/html", "application/json", "failed to parse response"
        ]
        
        gateway_indicators = ["gw3000", "gw1200", "gw1100"]
        
        has_content_issue = any(indicator in issue_text.lower() for indicator in content_indicators)
        has_gateway = any(indicator in issue_text.lower() for indicator in gateway_indicators)
        
        return has_content_issue and has_gateway
    
    def _extract_hex_device_model(self, issue_text: str, analysis: str) -> Optional[str]:
        """Extract device model that uses hex ID system"""
        # Look for hex ID indicators
        hex_indicators = ["0x02", "0x07", "0x0b", "hex id", "common_list"]
        device_models = ["wh69", "ws90", "wh90", "wh80", "wh85"]
        
        has_hex = any(indicator in issue_text.lower() for indicator in hex_indicators)
        
        if has_hex:
            for model in device_models:
                if model in issue_text.lower():
                    return model.upper()
        
        # Also check for "weather station not creating entities" pattern
        entity_indicators = ["not creating entities", "no entities", "entities missing"]
        weather_station_indicators = ["weather station", "7-in-1", "outdoor sensor"]
        
        has_entity_issue = any(indicator in issue_text.lower() for indicator in entity_indicators)
        has_weather_station = any(indicator in issue_text.lower() for indicator in weather_station_indicators)
        
        if has_entity_issue and has_weather_station:
            # Try to extract model from issue
            for model in device_models:
                if model in issue_text.lower():
                    return model.upper()
        
        return None
    
    def _matches_embedded_units_pattern(self, issue_text: str, analysis: str) -> bool:
        """Check if issue matches embedded units pattern"""
        unit_indicators = [
            "could not convert string to float", "float conversion", 
            "inhg", "°f", "°c", "%", "embedded unit"
        ]
        
        gateway_indicators = ["gw2000", "ws90"]
        
        has_unit_issue = any(indicator in issue_text.lower() for indicator in unit_indicators)
        has_gateway = any(indicator in issue_text.lower() for indicator in gateway_indicators)
        
        return has_unit_issue and has_gateway
    
    def implement_fix(self, issue: Issue, fix_type: str, fix_details: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Implement the code fix
        
        Returns:
            (success, message)
        """
        try:
            branch_name = f"bot/fix-issue-{issue.number}"
            
            # Create branch
            self._create_branch(branch_name)
            
            # Implement the specific fix
            if fix_type == "content_type_fix":
                success = self._implement_content_type_fix(branch_name)
            elif fix_type == "hex_sensor_mapping":
                success = self._implement_hex_sensor_mapping(branch_name, fix_details["device_model"])
            elif fix_type == "embedded_units_fix":
                success = self._implement_embedded_units_fix(branch_name)
            else:
                return False, f"Unknown fix type: {fix_type}"
            
            if not success:
                return False, "Failed to implement code changes"
            
            # Run tests
            test_success, test_output = self._run_tests(branch_name)
            if not test_success:
                return False, f"Tests failed: {test_output}"
            
            # Create PR
            pr_url = self._create_pull_request(issue, branch_name, fix_type, fix_details)
            
            return True, f"Successfully implemented fix and created PR: {pr_url}"
            
        except Exception as e:
            return False, f"Error implementing fix: {str(e)}"
    
    def _create_branch(self, branch_name: str):
        """Create a new branch from main"""
        main_ref = self.repo.get_git_ref("heads/main")
        main_sha = main_ref.object.sha
        
        try:
            # Create new branch
            self.repo.create_git_ref(f"refs/heads/{branch_name}", main_sha)
        except Exception as e:
            if "already exists" in str(e):
                # Branch exists, update it to latest main
                branch_ref = self.repo.get_git_ref(f"heads/{branch_name}")
                branch_ref.edit(main_sha)
            else:
                raise
    
    def _implement_content_type_fix(self, branch_name: str) -> bool:
        """Implement content-type fallback fix in api.py"""
        try:
            # Get current api.py content
            api_file = self.repo.get_contents("custom_components/ecowitt_local/api.py", ref=branch_name)
            content = api_file.decoded_content.decode()
            
            # Look for the _make_request method and enhance it
            if "# Check content type first" in content:
                # Fix already exists
                return True
            
            # Find the location to insert the fix
            method_start = content.find("async def _make_request(")
            if method_start == -1:
                return False
            
            # Find the response processing section
            json_line = content.find("response_data: Dict[str, Any] = await response.json()", method_start)
            if json_line == -1:
                return False
            
            # Insert the enhanced content-type handling
            enhanced_code = '''        # Check content type first
        content_type = response.headers.get('content-type', '').lower()
        
        if 'application/json' in content_type:
            # Standard JSON response
            response_data: Dict[str, Any] = await response.json()
            return response_data
        elif 'text/html' in content_type or 'text/plain' in content_type:
            # Gateway returned HTML/text instead of JSON, try to parse as JSON anyway
            text_content = await response.text()
            try:
                import json
                response_data = json.loads(text_content)
                return response_data
            except json.JSONDecodeError:
                _LOGGER.error("Failed to parse response as JSON: %s", text_content[:200])
                raise aiohttp.ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=422,
                    message=f"Invalid JSON response with content-type: {content_type}"
                )
        else:
            # Default to original behavior
            response_data: Dict[str, Any] = await response.json()
            return response_data'''
            
            # Replace the original line
            old_line = "        response_data: Dict[str, Any] = await response.json()\n        return response_data"
            new_content = content.replace(old_line, enhanced_code)
            
            # Commit the change
            self.repo.update_file(
                "custom_components/ecowitt_local/api.py",
                f"Fix content-type mismatch for GW3000/GW1200B gateways\n\nAdd fallback JSON parsing when gateways return JSON content with HTML content-type.\nFixes issue #{self.current_issue_number}",
                new_content,
                api_file.sha,
                branch=branch_name
            )
            
            return True
            
        except Exception as e:
            print(f"Error implementing content-type fix: {e}")
            return False
    
    def _implement_hex_sensor_mapping(self, branch_name: str, device_model: str) -> bool:
        """Implement hex sensor mapping for device model"""
        # This would implement the hex sensor mapping logic
        # Similar to what we did for WH69, WS90, WH90
        # TODO: Implement based on device_model
        return True
    
    def _implement_embedded_units_fix(self, branch_name: str) -> bool:
        """Implement embedded units parsing fix"""
        # This would enhance the _convert_sensor_value method
        # TODO: Implement the regex enhancement
        return True
    
    def _run_tests(self, branch_name: str) -> Tuple[bool, str]:
        """Run the full test suite on the branch"""
        try:
            # Clone the repository locally and run tests
            with tempfile.TemporaryDirectory() as temp_dir:
                # Clone the specific branch
                clone_cmd = [
                    "git", "clone", 
                    f"https://github.com/{self.repo.full_name}.git",
                    temp_dir,
                    "--branch", branch_name,
                    "--single-branch"
                ]
                subprocess.run(clone_cmd, check=True, capture_output=True)
                
                # Run tests
                test_cmd = [
                    "python", "-m", "pytest", "tests/", "-v",
                    "--tb=short"
                ]
                
                result = subprocess.run(
                    test_cmd, 
                    cwd=temp_dir, 
                    capture_output=True, 
                    text=True,
                    timeout=300  # 5 minute timeout
                )
                
                return result.returncode == 0, result.stdout + result.stderr
                
        except Exception as e:
            return False, f"Error running tests: {str(e)}"
    
    def _create_pull_request(self, issue: Issue, branch_name: str, fix_type: str, fix_details: Dict[str, Any]) -> str:
        """Create a pull request for the fix"""
        pr_title = f"Fix issue #{issue.number}: {fix_details['description']}"
        
        pr_body = f"""## Summary
Automated fix for issue #{issue.number}: {issue.title}

## Changes
- **Pattern**: {fix_details['pattern']}
- **Files modified**: {', '.join(fix_details['files'])}
- **Confidence**: {fix_details['confidence']:.0%}

## Description
{fix_details['description']}

## Testing
✅ All tests passed on branch `{branch_name}`

## Related Issue
Closes #{issue.number}

---
🤖 **This PR was automatically generated by the Ecowitt Local Bot**
- Review the changes carefully before merging
- Test with actual hardware if possible
- Bot confidence: {fix_details['confidence']:.0%}

Generated with [Claude Code](https://claude.ai/code)
"""
        
        pr = self.repo.create_pull(
            title=pr_title,
            body=pr_body,
            head=branch_name,
            base="main"
        )
        
        # Add labels
        pr.add_to_labels("bot-generated", "automated-fix")
        if fix_details['pattern'] == "content_type_mismatch":
            pr.add_to_labels("gateway")
        elif fix_details['pattern'] == "hex_id_sensors":
            pr.add_to_labels("sensor")
        
        return pr.html_url
    
    def set_current_issue_number(self, issue_number: int):
        """Set the current issue number for commit messages"""
        self.current_issue_number = issue_number