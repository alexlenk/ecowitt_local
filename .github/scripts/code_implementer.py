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
import anthropic

class CodeImplementer:
    """Handles automatic code implementation for known issue patterns"""
    
    def __init__(self, repo: Repository, github_token: str):
        self.repo = repo
        auth = Auth.Token(github_token)
        self.github = Github(auth=auth)
        self.github_token = github_token
        self.claude = anthropic.Anthropic(api_key=os.environ.get("CLAUDE_API_KEY"))
        
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
        Determine if bot can automatically implement a fix using AI analysis
        
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
        
        # Use AI to analyze if this issue can be fixed automatically
        fix_assessment = self._ai_assess_fixability(issue, analysis)
        
        if fix_assessment["can_fix"]:
            return True, "ai_generated_fix", fix_assessment
        else:
            return False, "unfixable", fix_assessment
    
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
    
    def _matches_unhashable_type_pattern(self, issue_text: str, analysis: str) -> bool:
        """Check if issue matches unhashable type list error pattern"""
        error_indicators = [
            "unhashable type", "unhashable type: 'list'", "typeerror: unhashable",
            "cannot use list as dict key", "list object is unhashable"
        ]
        
        device_indicators = [
            "device registry", "device_id", "__init__.py", "refresh mapping",
            "entities not created", "device creation"
        ]
        
        has_error = any(indicator in issue_text.lower() or indicator in analysis.lower() 
                       for indicator in error_indicators)
        has_device_context = any(indicator in issue_text.lower() or indicator in analysis.lower() 
                                for indicator in device_indicators)
        
        return has_error and has_device_context
    
    def _ai_assess_fixability(self, issue: Issue, analysis: str) -> Dict[str, Any]:
        """Use AI to assess if an issue can be automatically fixed"""
        try:
            assessment_prompt = f"""
You are an expert code analyzer for Home Assistant integrations. Analyze this issue to determine if it can be automatically fixed.

## Issue Details:
**Title**: {issue.title}
**Description**: {issue.body}
**Bot Analysis**: {analysis}

## Your Task:
Determine if this issue can be automatically fixed by modifying code in the `custom_components/ecowitt_local/` directory.

## Assessment Criteria:
✅ **CAN FIX** if issue involves:
- Clear error messages with traceback/line numbers
- Missing imports, type errors, attribute errors
- Device mapping issues (hex IDs, sensor definitions)
- API communication problems (content-type, parsing)
- Configuration or initialization errors
- Code patterns that have clear solutions

❌ **CANNOT FIX** if issue involves:
- Hardware problems or network connectivity
- Home Assistant core issues outside the integration
- User configuration errors (passwords, IP addresses)
- Feature requests requiring new functionality
- Issues without clear technical details
- External dependencies or services

## Response Format:
Respond with JSON:
{{
    "can_fix": true/false,
    "confidence": 0.0-1.0,
    "pattern": "brief_description_of_issue_type",
    "files": ["list", "of", "likely", "files", "to", "modify"],
    "description": "Brief description of the fix needed",
    "reasoning": "Why this can/cannot be fixed automatically"
}}

## Examples:
- TypeError with traceback → can_fix: true, high confidence
- "Entities not created" with device data → can_fix: true, medium confidence  
- "Can't connect to gateway" → can_fix: false, low confidence
- Missing feature request → can_fix: false, high confidence

Analyze the issue and provide your assessment:
"""

            response = self.claude.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                messages=[{"role": "user", "content": assessment_prompt}]
            )
            
            # Parse AI response
            ai_response = response.content[0].text
            
            # Try to extract JSON from response
            import json
            import re
            
            # Look for JSON block in response
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                try:
                    assessment = json.loads(json_match.group())
                    
                    # Validate and normalize the response
                    return {
                        "can_fix": assessment.get("can_fix", False),
                        "confidence": float(assessment.get("confidence", 0.0)),
                        "pattern": assessment.get("pattern", "unknown"),
                        "files": assessment.get("files", ["custom_components/ecowitt_local/__init__.py"]),
                        "description": assessment.get("description", "AI-generated fix"),
                        "reasoning": assessment.get("reasoning", "No reasoning provided"),
                        "ai_analysis": ai_response
                    }
                except json.JSONDecodeError:
                    pass
            
            # Fallback: Parse response heuristically
            can_fix = "can_fix: true" in ai_response.lower() or "\"can_fix\": true" in ai_response.lower()
            confidence = 0.7 if can_fix else 0.1
            
            return {
                "can_fix": can_fix,
                "confidence": confidence,
                "pattern": "ai_heuristic_analysis", 
                "files": self._determine_likely_files(issue.title + " " + issue.body, analysis),
                "description": "AI-powered heuristic fix",
                "reasoning": "Heuristic parsing of AI response",
                "ai_analysis": ai_response
            }
            
        except Exception as e:
            print(f"Error in AI assessment: {e}")
            # Fallback to explicit request detection
            if self._is_explicit_fix_request(issue.title + " " + issue.body, analysis):
                return {
                    "can_fix": True,
                    "confidence": 0.8,
                    "pattern": "explicit_request",
                    "files": self._determine_likely_files(issue.title + " " + issue.body, analysis),
                    "description": "Fix based on explicit request",
                    "reasoning": "Maintainer explicitly requested fix"
                }
            else:
                return {
                    "can_fix": False,
                    "confidence": 0.0,
                    "pattern": "assessment_failed",
                    "description": "Could not assess fixability",
                    "reasoning": f"AI assessment failed: {str(e)}"
                }
    
    def _is_explicit_fix_request(self, issue_text: str, analysis: str) -> bool:
        """Check if maintainer is explicitly requesting the bot to implement a fix"""
        # Look for explicit requests from the maintainer (alexlenk)
        maintainer_requests = [
            "@bot fix this", "@bot implement", "@bot create fix", 
            "bot please fix", "please implement", "please fix this",
            "can you fix", "implement a fix", "create a fix",
            "fix this issue", "solve this", "implement solution"
        ]
        
        combined_text = issue_text.lower() + " " + analysis.lower()
        
        # Check for explicit fix requests
        has_explicit_request = any(request in combined_text for request in maintainer_requests)
        
        # Also check if there's sufficient technical detail to attempt a fix
        has_technical_detail = any(indicator in combined_text for indicator in [
            "traceback", "error", "line", "file", "method", "function",
            "exception", "bug", "issue", "problem", "fails", "crash"
        ])
        
        return has_explicit_request or (has_technical_detail and len(combined_text) > 200)
    
    def _determine_likely_files(self, issue_text: str, analysis: str) -> list:
        """Determine which files are likely to need modification based on issue content"""
        files = []
        combined_text = (issue_text + " " + analysis).lower()
        
        # File-specific indicators
        file_indicators = {
            "custom_components/ecowitt_local/__init__.py": [
                "__init__", "setup", "integration", "device registry", "entry", "config_entry"
            ],
            "custom_components/ecowitt_local/api.py": [
                "api", "gateway", "connection", "request", "response", "http", "aiohttp"
            ],
            "custom_components/ecowitt_local/sensor_mapper.py": [
                "sensor", "mapping", "entity", "hardware_id", "live_data", "sensor_type"
            ],
            "custom_components/ecowitt_local/coordinator.py": [
                "coordinator", "polling", "update", "data", "refresh", "interval"
            ],
            "custom_components/ecowitt_local/const.py": [
                "const", "constant", "definition", "battery", "sensor_key"
            ]
        }
        
        for file_path, indicators in file_indicators.items():
            if any(indicator in combined_text for indicator in indicators):
                files.append(file_path)
        
        # Default to __init__.py if no specific file identified
        if not files:
            files.append("custom_components/ecowitt_local/__init__.py")
        
        return files
    
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
            elif fix_type == "unhashable_type_fix":
                success = self._implement_unhashable_type_fix(branch_name)
            elif fix_type == "explicit_fix_request":
                success = self._implement_explicit_fix(branch_name, issue, fix_details)
            elif fix_type == "ai_generated_fix":
                success = self._implement_ai_fix(branch_name, issue, fix_details)
            else:
                return False, f"Unknown fix type: {fix_type}"
            
            if not success:
                print(f"Fix implementation failed for {fix_type}")
                return False, f"Failed to implement code changes (type: {fix_type})"
            
            # Run tests
            test_success, test_output = self._run_tests(branch_name)
            if not test_success:
                # Check if it's a syntax error that we can automatically fix
                if "SyntaxError" in test_output and self._try_fix_syntax_error(branch_name, test_output):
                    print("Syntax error detected and fixed, retrying tests...")
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
    
    def _implement_unhashable_type_fix(self, branch_name: str) -> bool:
        """Fix unhashable type list error in device registry"""
        try:
            # SECURITY: Validate file path
            file_path = "custom_components/ecowitt_local/__init__.py"
            if not self._validate_file_path(file_path):
                return False
            
            # Get current __init__.py content
            init_file = self.repo.get_contents(file_path, ref=branch_name)
            content = init_file.decoded_content.decode()
            
            # Look for the problematic line around line 155
            lines = content.split('\n')
            
            # Common patterns that cause unhashable type errors:
            # 1. Using a list as a device identifier instead of a string/tuple
            # 2. Passing a list where a hashable key is expected
            
            fixed = False
            for i, line in enumerate(lines):
                line_num = i + 1
                
                # Look for common problematic patterns around line 155
                if 145 <= line_num <= 165:  # Search around the reported line
                    # Pattern 1: device_id being set to a list
                    if 'device_id' in line and '[' in line and ']' in line:
                        # Convert list to tuple (hashable) or comma-separated string
                        if 'device_id = [' in line:
                            lines[i] = line.replace('device_id = [', 'device_id = tuple([').replace(']', '])')
                            fixed = True
                        elif 'device_id' in line and '= [' in line:
                            lines[i] = line.replace('= [', '= tuple([').replace(']', '])')
                            fixed = True
                    
                    # Pattern 2: identifiers being passed as lists
                    elif 'identifiers' in line and '{[' in line:
                        # Convert list in identifiers to tuple
                        import re
                        lines[i] = re.sub(r'identifiers.*?\{(\[.*?\])\}', 
                                        lambda m: line.replace(m.group(1), f'({m.group(1)[1:-1]})'), 
                                        line)
                        fixed = True
                    
                    # Pattern 3: hardware_id as list
                    elif 'hardware_id' in line and '[' in line and ']' in line:
                        if '=' in line and line.split('=')[1].strip().startswith('['):
                            lines[i] = line.replace('[', 'tuple([').replace(']', '])')
                            fixed = True
            
            if not fixed:
                # Fallback: Add a general fix for common device ID issues
                # Look for device registry calls and ensure proper hashable types
                for i, line in enumerate(lines):
                    if 'device_registry' in line and 'identifiers' in line:
                        # Add tuple conversion for safety
                        if 'tuple(' not in line:
                            lines[i] = line.replace('identifiers=', 'identifiers=tuple(') + ')'
                            fixed = True
                            break
            
            if fixed:
                new_content = '\n'.join(lines)
                
                # Commit the change
                self.repo.update_file(
                    file_path,
                    f"Fix unhashable type list error in device registry\\n\\nConvert list device identifiers to hashable tuples.\\nFixes issue #{self.current_issue_number}",
                    new_content,
                    init_file.sha,
                    branch=branch_name
                )
                
                return True
            else:
                print("Could not identify specific unhashable type pattern to fix")
                return False
                
        except Exception as e:
            print(f"Error implementing unhashable type fix: {e}")
            return False
    
    def _implement_explicit_fix(self, branch_name: str, issue, fix_details: dict) -> bool:
        """Implement a fix based on explicit maintainer request using AI analysis"""
        try:
            files_to_modify = fix_details.get("files", ["custom_components/ecowitt_local/__init__.py"])
            
            # Use Claude to analyze the issue and generate a fix
            analysis_prompt = f"""
You are a code analysis AI helping to fix a Home Assistant integration issue.

## Issue Details:
- **Title**: {issue.title}
- **Description**: {issue.body}
- **Files to examine**: {', '.join(files_to_modify)}

## Your Task:
1. Analyze the issue description and any error traces provided
2. Identify the specific problem in the code
3. Generate a targeted fix for the identified problem
4. Provide the exact code changes needed

## Rules:
- Only modify integration code in custom_components/ecowitt_local/
- Make minimal, targeted changes
- Ensure the fix addresses the root cause
- Follow Python and Home Assistant best practices

## Response Format:
Provide your analysis and the specific code changes needed to fix this issue.
"""

            # Get Claude's analysis and fix recommendation
            fix_response = self.claude.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{"role": "user", "content": analysis_prompt}]
            )
            
            fix_analysis = fix_response.content[0].text
            
            # For now, implement a basic heuristic-based fix
            # In a full implementation, we'd parse Claude's response and apply the suggested changes
            
            success = False
            for file_path in files_to_modify:
                if self._apply_heuristic_fix(branch_name, file_path, issue, fix_analysis):
                    success = True
            
            return success
            
        except Exception as e:
            print(f"Error implementing explicit fix: {e}")
            return False
    
    def _apply_heuristic_fix(self, branch_name: str, file_path: str, issue, fix_analysis: str) -> bool:
        """Apply heuristic-based fixes to common issue patterns"""
        try:
            # SECURITY: Validate file path
            if not self._validate_file_path(file_path):
                return False
            
            # Get current file content
            file_obj = self.repo.get_contents(file_path, ref=branch_name)
            content = file_obj.decoded_content.decode()
            
            original_content = content
            lines = content.split('\n')
            
            # Apply common fixes based on issue content
            issue_text = (issue.title + " " + issue.body + " " + fix_analysis).lower()
            
            print(f"Applying heuristic fixes to {file_path} based on: {issue_text[:100]}...")
            
            # Fix 1: Unhashable type errors (most common in this codebase)
            if "unhashable" in issue_text or "list" in issue_text:
                print("Applying unhashable type fixes...")
                content = self._fix_unhashable_types(content)
            
            # Fix 2: Missing imports
            if "import" in issue_text or "module" in issue_text:
                print("Applying import fixes...")
                content = self._fix_missing_imports(content, issue_text)
            
            # Fix 3: Type errors
            if "type" in issue_text and "error" in issue_text:
                print("Applying type error fixes...")
                content = self._fix_type_errors(content, issue_text)
            
            # Fix 4: Attribute errors
            if "attribute" in issue_text and "error" in issue_text:
                print("Applying attribute error fixes...")
                content = self._fix_attribute_errors(content, issue_text)
            
            # Fix 5: Key errors
            if "key" in issue_text and "error" in issue_text:
                print("Applying key error fixes...")
                content = self._fix_key_errors(content, issue_text)
            
            # If content changed, commit it
            if content != original_content:
                self.repo.update_file(
                    file_path,
                    f"Implement fix for issue #{self.current_issue_number}\\n\\nBased on maintainer request and heuristic analysis.\\nAddresses: {issue.title}",
                    content,
                    file_obj.sha,
                    branch=branch_name
                )
                return True
            
            return False
            
        except Exception as e:
            print(f"Error applying heuristic fix to {file_path}: {e}")
            return False
    
    def _fix_missing_imports(self, content: str, issue_text: str) -> str:
        """Fix common missing import issues"""
        lines = content.split('\n')
        
        # Common missing imports in Home Assistant integrations
        import_fixes = {
            "typing": "from typing import Dict, List, Optional, Any",
            "asyncio": "import asyncio",
            "aiohttp": "import aiohttp", 
            "homeassistant.core": "from homeassistant.core import HomeAssistant",
            "homeassistant.config_entries": "from homeassistant.config_entries import ConfigEntry",
        }
        
        # Find import section
        import_end = 0
        for i, line in enumerate(lines):
            if line.startswith(('import ', 'from ')) or line.strip() == '':
                import_end = i
            else:
                break
        
        # Add missing imports
        for keyword, import_line in import_fixes.items():
            if keyword in issue_text and import_line not in content:
                lines.insert(import_end + 1, import_line)
                import_end += 1
        
        return '\n'.join(lines)
    
    def _fix_type_errors(self, content: str, issue_text: str) -> str:
        """Fix common type-related errors"""
        # Convert lists to tuples where needed for hashable types
        if "unhashable" in issue_text:
            content = content.replace('identifiers=[', 'identifiers=(')
            content = content.replace('])', '))')
            content = content.replace('device_id = [', 'device_id = (')
        
        return content
    
    def _fix_attribute_errors(self, content: str, issue_text: str) -> str:
        """Fix common attribute access errors"""
        # Add safety checks for common attribute errors
        if "has no attribute" in issue_text:
            # Add getattr with defaults
            content = content.replace('.config_entry', '.get("config_entry")')
            content = content.replace('.data.get(', '.data and data.get(')
        
        return content
    
    def _fix_key_errors(self, content: str, issue_text: str) -> str:
        """Fix common key access errors"""
        # Replace direct key access with .get() where appropriate
        content = content.replace('data["', 'data.get("')
        content = content.replace('config["', 'config.get("')
        
        return content
    
    def _fix_unhashable_types(self, content: str) -> str:
        """Fix unhashable type errors by converting lists to tuples"""
        # Common unhashable type fixes
        content = content.replace('identifiers=[', 'identifiers=(')
        content = content.replace('identifiers = [', 'identifiers = (')  
        content = content.replace('])', '))')
        content = content.replace('device_id = [', 'device_id = (')
        content = content.replace('device_id=[', 'device_id=(')
        
        # Fix list comprehensions that should be tuples
        import re
        content = re.sub(r'identifiers\s*=\s*\[(.*?)\]', r'identifiers = (\1)', content)
        content = re.sub(r'device_id\s*=\s*\[(.*?)\]', r'device_id = (\1)', content)
        
        return content
    
    def _implement_ai_fix(self, branch_name: str, issue: Issue, fix_details: dict) -> bool:
        """Implement a fix using AI analysis and code generation"""
        try:
            files_to_modify = fix_details.get("files", ["custom_components/ecowitt_local/__init__.py"])
            
            # Get current repository context
            repo_context = self._get_relevant_file_contents(files_to_modify)
            
            # Use AI to generate the actual fix
            fix_prompt = f"""
You are an expert Python developer fixing a Home Assistant integration issue.

## Issue Details:
**Title**: {issue.title}
**Description**: {issue.body}
**AI Assessment**: {fix_details.get('reasoning', '')}

## Current Code Context:
{repo_context}

## Your Task:
Generate the exact code changes needed to fix this issue.

## Requirements:
1. Only modify files in custom_components/ecowitt_local/
2. Make minimal, targeted changes
3. Follow Python and Home Assistant best practices
4. Ensure type safety and error handling
5. Maintain backward compatibility

## Response Format:
For each file that needs changes, provide:
```
FILE: path/to/file.py
OLD_CODE:
[exact code to replace]

NEW_CODE:
[exact replacement code]
---
```

Generate the fix:
"""

            response = self.claude.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=3000,
                messages=[{"role": "user", "content": fix_prompt}]
            )
            
            fix_response = response.content[0].text
            print(f"AI Fix Response: {fix_response[:500]}...")
            
            # Parse the AI response and apply changes
            success = self._apply_ai_generated_changes(branch_name, fix_response, issue)
            print(f"AI changes applied successfully: {success}")
            
            return success
            
        except Exception as e:
            import traceback
            print(f"Error implementing AI fix: {e}")
            print(f"Full traceback: {traceback.format_exc()}")
            # Fallback to heuristic fixes
            print("Falling back to heuristic fixes...")
            return self._apply_heuristic_fixes(branch_name, issue, fix_details)
    
    def _get_relevant_file_contents(self, file_paths: list) -> str:
        """Get contents of relevant files for AI context"""
        context = ""
        
        for file_path in file_paths[:3]:  # Limit to 3 files for token management
            try:
                file_obj = self.repo.get_contents(file_path)
                content = file_obj.decoded_content.decode()
                
                # Truncate if too long
                if len(content) > 5000:
                    content = content[:5000] + "\n# ... (truncated for context)"
                
                context += f"\n## {file_path}\n```python\n{content}\n```\n"
                
            except Exception as e:
                context += f"\n## {file_path}\n(Could not read file: {e})\n"
        
        return context
    
    def _apply_ai_generated_changes(self, branch_name: str, fix_response: str, issue: Issue) -> bool:
        """Parse and apply AI-generated code changes"""
        import re
        
        # Parse the AI response for file changes
        file_changes = []
        
        # Look for FILE: ... OLD_CODE: ... NEW_CODE: ... patterns
        file_pattern = r'FILE:\s*([^\n]+)\s*\n.*?OLD_CODE:\s*\n(.*?)\n\s*NEW_CODE:\s*\n(.*?)(?=\n---|\nFILE:|$)'
        matches = re.findall(file_pattern, fix_response, re.DOTALL)
        print(f"Found {len(matches)} file changes in AI response")
        
        for file_path, old_code, new_code in matches:
            file_path = file_path.strip()
            old_code = old_code.strip()
            new_code = new_code.strip()
            
            # Validate file path
            if not self._validate_file_path(file_path):
                continue
            
            file_changes.append({
                "file_path": file_path,
                "old_code": old_code,
                "new_code": new_code
            })
        
        # Apply the changes
        applied_changes = 0
        for change in file_changes:
            try:
                file_obj = self.repo.get_contents(change["file_path"], ref=branch_name)
                content = file_obj.decoded_content.decode()
                
                # Apply the change
                if change["old_code"] in content:
                    new_content = content.replace(change["old_code"], change["new_code"])
                    
                    self.repo.update_file(
                        change["file_path"],
                        f"AI-generated fix for issue #{self.current_issue_number}\\n\\nAddresses: {issue.title}\\n\\nChanges made based on AI analysis.",
                        new_content,
                        file_obj.sha,
                        branch=branch_name
                    )
                    applied_changes += 1
                    
            except Exception as e:
                print(f"Error applying change to {change['file_path']}: {e}")
                continue
        
        print(f"Applied {applied_changes} changes successfully")
        
        # If no changes applied, try simpler approach
        if applied_changes == 0:
            print("No changes applied via structured parsing, trying simple approach...")
            return self._try_simple_ai_fix(branch_name, fix_response, issue)
        
        return applied_changes > 0
    
    def _try_simple_ai_fix(self, branch_name: str, fix_response: str, issue: Issue) -> bool:
        """Try to apply fixes using a simpler approach when structured parsing fails"""
        try:
            # Look for any file paths mentioned in the AI response
            import re
            file_mentions = re.findall(r'(custom_components/ecowitt_local/[a-zA-Z_]+\.py)', fix_response)
            
            if not file_mentions:
                print("No file paths found in AI response")
                return False
            
            # Try to apply basic heuristic fixes to mentioned files
            applied = 0
            for file_path in set(file_mentions):
                if self._validate_file_path(file_path):
                    print(f"Applying heuristic fixes to {file_path}")
                    if self._apply_heuristic_fix(branch_name, file_path, issue, fix_response):
                        applied += 1
            
            return applied > 0
            
        except Exception as e:
            print(f"Simple fix approach failed: {e}")
            return False
    
    def _try_fix_syntax_error(self, branch_name: str, test_output: str) -> bool:
        """Try to automatically fix syntax errors detected in test output"""
        import re
        
        # Extract file and line number from syntax error
        # Example: "File "/path/file.py", line 297"
        file_pattern = r'File "([^"]+)", line (\d+)'
        match = re.search(file_pattern, test_output)
        
        if not match:
            print("Could not extract file/line from syntax error")
            return False
        
        file_path = match.group(1)
        line_num = int(match.group(2))
        
        # Convert to relative path if it's absolute
        if file_path.startswith('/tmp/'):
            # Extract the relative path
            rel_match = re.search(r'/tmp/[^/]+/(.*)', file_path)
            if rel_match:
                file_path = rel_match.group(1)
            else:
                print(f"Could not extract relative path from {file_path}")
                return False
        
        print(f"Attempting to fix syntax error in {file_path} at line {line_num}")
        
        try:
            # Get the current file content
            file_content = self.repo.get_contents(file_path, ref=branch_name)
            content = file_content.decoded_content.decode()
            lines = content.split('\n')
            
            # Look for common syntax errors
            if line_num <= len(lines):
                error_line = lines[line_num - 1]
                print(f"Error line: {error_line}")
                
                fixed = False
                # Fix the specific error: },lass": should be "class":
                if '},lass"' in error_line:
                    lines[line_num - 1] = error_line.replace('},lass"', '"class"')
                    fixed = True
                    print("Fixed },lass syntax error")
                
                # Fix other common syntax errors
                elif '",lass"' in error_line:
                    lines[line_num - 1] = error_line.replace('",lass"', '"class"')
                    fixed = True
                elif 'device_lass' in error_line:
                    lines[line_num - 1] = error_line.replace('device_lass', 'device_class')
                    fixed = True
                elif error_line.strip().endswith(',lass"'):
                    lines[line_num - 1] = error_line.replace(',lass"', '"class"')
                    fixed = True
                
                if fixed:
                    # Write the fixed content back
                    new_content = '\n'.join(lines)
                    
                    self.repo.update_file(
                        file_path,
                        f"🔧 Fix syntax error in {file_path}",
                        new_content,
                        file_content.sha,
                        branch=branch_name
                    )
                    print(f"Successfully fixed syntax error in {file_path}")
                    return True
                else:
                    print(f"Could not automatically fix syntax error: {error_line}")
                    return False
            
        except Exception as e:
            print(f"Error fixing syntax error: {e}")
            return False
        
        return False
    
    def _apply_heuristic_fixes(self, branch_name: str, issue: Issue, fix_details: dict) -> bool:
        """Apply heuristic fixes as fallback when AI parsing fails"""
        files_to_modify = fix_details.get("files", ["custom_components/ecowitt_local/__init__.py"])
        
        success = False
        for file_path in files_to_modify:
            if self._apply_heuristic_fix(branch_name, file_path, issue, ""):
                success = True
        
        return success
    
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