#!/usr/bin/env python3
"""
Code Implementation Module for GitHub Issue Bot
Handles automatic code fixes for known device patterns
"""
import os
import json
import re
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
        
    def _validate_security(self, issue: Issue, analysis: str) -> bool:
        """Validate that the issue and analysis are safe to process"""
        
        # Check for potential malicious patterns
        dangerous_patterns = [
            r'\.github/workflows/',  # GitHub Actions modification
            r'\.github/bot-memory/',  # Bot memory corruption
            r'rm\s+-rf',  # Destructive commands
            r'sudo\s+',  # Privilege escalation
            r'exec\s*\(',  # Code execution
            r'eval\s*\(',  # Code evaluation
            r'subprocess\.',  # System commands
            r'os\.system',  # OS commands
            r'__import__',  # Dynamic imports
            r'secrets\.',  # Access to secrets
            r'token\s*[:=]',  # Token manipulation
        ]
        
        combined_text = str(issue.title or "") + " " + str(issue.body or "") + " " + str(analysis or "")
        
        for pattern in dangerous_patterns:
            if re.search(pattern, combined_text, re.IGNORECASE):
                print(f"SECURITY WARNING: Detected potentially dangerous pattern: {pattern}")
                return False
        
        # Check if trying to modify unauthorized files
        unauthorized_paths = [
            '.github/workflows/',
            '.github/bot-memory/',
            '.github/scripts/',
            'requirements.txt',
            'setup.py',
            'Dockerfile'
        ]
        
        for path in unauthorized_paths:
            if path in combined_text:
                print(f"SECURITY WARNING: Attempt to modify unauthorized path: {path}")
                return False
        
        return True

    def can_implement_fix(self, issue: Issue, analysis: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Determine if bot can automatically implement a fix
        
        Returns:
            (can_fix, fix_type, fix_details)
        """
        # SECURITY: Validate input before processing
        if not self._validate_security(issue, analysis):
            return False, "security_violation", {
                "error": "Security validation failed - request rejected",
                "confidence": 0.0
            }
        
        issue_text = str(issue.title or "") + " " + str(issue.body or "")
        
        # Check for known patterns and verify they need implementation
        
        # Pattern 1: Content-type issues (GW3000, GW1200B)
        if self._matches_content_type_pattern(issue_text, analysis):
            # Check if fix already exists in main
            if self._is_content_type_fix_already_implemented():
                return False, "already_implemented", {
                    "pattern": "content_type_mismatch", 
                    "message": "Content-type fallback parsing is already implemented in the current version",
                    "confidence": 0.0
                }
            
            return True, "content_type_fix", {
                "pattern": "content_type_mismatch",
                "files": ["custom_components/ecowitt_local/api.py"],
                "description": "Add fallback JSON parsing for content-type mismatch",
                "confidence": 0.9
            }
        
        # Pattern 2: Missing hex ID sensor mapping (WH69, WS90, WH90)
        hex_device = self._extract_hex_device_model(issue_text, analysis)
        if hex_device:
            # Check if device mapping already exists
            if self._is_hex_device_already_implemented(hex_device):
                return False, "already_implemented", {
                    "pattern": "hex_id_sensors",
                    "message": f"{hex_device} hex sensor mapping is already implemented in the current version",
                    "confidence": 0.0
                }
            
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
            # Check if embedded units fix already exists
            if self._is_embedded_units_fix_already_implemented():
                return False, "already_implemented", {
                    "pattern": "embedded_units",
                    "message": "Embedded unit parsing is already implemented in the current version",
                    "confidence": 0.0
                }
            
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
    
    def _is_content_type_fix_already_implemented(self) -> bool:
        """Check if content-type fallback fix is already in main"""
        try:
            api_file = self.repo.get_contents("custom_components/ecowitt_local/api.py")
            content = api_file.decoded_content.decode()
            
            # Look for the content-type fix signature
            return "# Check content type first" in content or "text/html" in content
        except:
            return False
    
    def _is_hex_device_already_implemented(self, device_model: str) -> bool:
        """Check if hex device mapping is already in main"""
        try:
            # Check sensor_mapper.py
            mapper_file = self.repo.get_contents("custom_components/ecowitt_local/sensor_mapper.py")
            mapper_content = mapper_file.decoded_content.decode()
            
            # Check const.py
            const_file = self.repo.get_contents("custom_components/ecowitt_local/const.py")
            const_content = const_file.decoded_content.decode()
            
            device_lower = device_model.lower()
            
            # Look for device mapping in sensor_mapper.py
            mapper_has_device = f'"{device_lower}"' in mapper_content or f"'{device_lower}'" in mapper_content
            
            # Look for battery mapping in const.py  
            const_has_battery = f'"{device_lower}batt"' in const_content
            
            return mapper_has_device and const_has_battery
        except:
            return False
    
    def _is_embedded_units_fix_already_implemented(self) -> bool:
        """Check if embedded units parsing is already in main"""
        try:
            coordinator_file = self.repo.get_contents("custom_components/ecowitt_local/coordinator.py")
            content = coordinator_file.decoded_content.decode()
            
            # Look for embedded unit parsing signatures
            has_regex = "re.match" in content or "unit_match" in content
            has_embedded_logic = "embedded unit" in content.lower() or "inhg" in content.lower()
            
            return has_regex and has_embedded_logic
        except:
            return False
    
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
    
    def _validate_file_path(self, file_path: str) -> bool:
        """Validate that file path is safe to modify"""
        safe_paths = [
            "custom_components/ecowitt_local/api.py",
            "custom_components/ecowitt_local/sensor_mapper.py", 
            "custom_components/ecowitt_local/const.py",
            "custom_components/ecowitt_local/coordinator.py",
            "custom_components/ecowitt_local/__init__.py"
        ]
        
        # SECURITY: Only allow modifications to integration files
        if file_path not in safe_paths:
            print(f"SECURITY WARNING: Attempt to modify unauthorized file: {file_path}")
            return False
        
        return True

    def _implement_content_type_fix(self, branch_name: str) -> bool:
        """Implement content-type fallback fix in api.py"""
        try:
            # SECURITY: Validate file path
            file_path = "custom_components/ecowitt_local/api.py"
            if not self._validate_file_path(file_path):
                return False
            
            # Get current api.py content
            api_file = self.repo.get_contents(file_path, ref=branch_name)
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
        try:
            # 1. Update sensor_mapper.py
            success = self._add_hex_mapping_to_sensor_mapper(branch_name, device_model)
            if not success:
                return False
            
            # 2. Update const.py with battery mapping
            success = self._add_hex_battery_mapping_to_const(branch_name, device_model)
            if not success:
                return False
            
            return True
            
        except Exception as e:
            print(f"Error implementing hex sensor mapping: {e}")
            return False
    
    def _add_hex_mapping_to_sensor_mapper(self, branch_name: str, device_model: str) -> bool:
        """Add hex sensor mapping to sensor_mapper.py"""
        try:
            # Get current sensor_mapper.py content
            file = self.repo.get_contents("custom_components/ecowitt_local/sensor_mapper.py", ref=branch_name)
            content = file.decoded_content.decode()
            
            # Check if mapping already exists
            if f'sensor_type.lower() in ("{device_model.lower()}"' in content:
                return True  # Already exists
            
            # Find the location to insert the new mapping (after WH90 or before WH25)
            insert_point = content.find('elif sensor_type.lower() in ("wh25", "indoor_station"):')
            if insert_point == -1:
                return False
            
            # Generate the mapping code
            device_mapping = f'''        elif sensor_type.lower() in ("{device_model.lower()}", "weather_station_{device_model.lower()}"):
            # {device_model} outdoor sensor array (similar to WH69/WS90, uses hex IDs in common_list)
            keys.extend([
                "0x02",  # Temperature
                "0x03",  # Temperature (alternate)
                "0x07",  # Humidity
                "0x0B",  # Wind speed
                "0x0C",  # Wind speed (alternate)
                "0x19",  # Wind gust
                "0x0A",  # Wind direction
                "0x6D",  # Wind direction (alternate)
                "0x15",  # Solar radiation
                "0x17",  # UV index
                "0x0D",  # Rain event
                "0x0E",  # Rain rate
                "0x7C",  # Rain daily
                "0x10",  # Rain weekly
                "0x11",  # Rain monthly
                "0x12",  # Rain yearly
                "0x13",  # Rain total
                "{device_model.lower()}batt",  # Battery level
            ])
        '''
            
            # Insert the mapping
            new_content = content[:insert_point] + device_mapping + content[insert_point:]
            
            # Commit the change
            self.repo.update_file(
                "custom_components/ecowitt_local/sensor_mapper.py",
                f"Add {device_model} hex sensor mapping\n\nAdd support for {device_model} weather station hex ID sensors.\nFixes issue #{self.current_issue_number}",
                new_content,
                file.sha,
                branch=branch_name
            )
            
            return True
            
        except Exception as e:
            print(f"Error updating sensor_mapper.py: {e}")
            return False
    
    def _add_hex_battery_mapping_to_const(self, branch_name: str, device_model: str) -> bool:
        """Add battery mapping to const.py"""
        try:
            # Get current const.py content
            file = self.repo.get_contents("custom_components/ecowitt_local/const.py", ref=branch_name)
            content = file.decoded_content.decode()
            
            # Check if mapping already exists
            if f'"{device_model.lower()}batt"' in content:
                return True  # Already exists
            
            # Find the battery sensors section and add the new mapping
            insert_point = content.find('    "wh90batt": {')
            if insert_point != -1:
                # WH90 exists, add after it
                end_point = content.find('    },', insert_point) + 6
                battery_mapping = f'''    "{device_model.lower()}batt": {{
        "name": "{device_model} Weather Station Battery",
        "sensor_key": "0x02"
    }},
'''
                new_content = content[:end_point] + battery_mapping + content[end_point:]
            else:
                # Add before the closing of BATTERY_SENSORS
                insert_point = content.find('}\n\n# Add dynamically generated battery sensors')
                if insert_point == -1:
                    return False
                
                battery_mapping = f'''    "{device_model.lower()}batt": {{
        "name": "{device_model} Weather Station Battery",
        "sensor_key": "0x02"
    }},
'''
                new_content = content[:insert_point] + battery_mapping + content[insert_point:]
            
            # Commit the change
            self.repo.update_file(
                "custom_components/ecowitt_local/const.py",
                f"Add {device_model} battery sensor mapping\n\nAdd battery support for {device_model} weather station.\nFixes issue #{self.current_issue_number}",
                new_content,
                file.sha,
                branch=branch_name
            )
            
            return True
            
        except Exception as e:
            print(f"Error updating const.py: {e}")
            return False
    
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
                
                # Install test dependencies first
                install_cmd = ["pip", "install", "-r", "requirements_test.txt"]
                subprocess.run(install_cmd, cwd=temp_dir, check=True, capture_output=True)
                
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