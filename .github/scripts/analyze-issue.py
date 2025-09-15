#!/usr/bin/env python3
"""
GitHub Issue Analysis Bot
Analyzes issues, asks for clarification, manages lifecycle, and tracks memory
"""
import os
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import anthropic
from github import Github, Auth

class IssueBotMemory:
    """Handle bot memory using GitHub repository files"""
    
    def __init__(self, repo, github_token: str):
        self.repo = repo
        auth = Auth.Token(github_token)
        self.github = Github(auth=auth)
        self.memory_path = ".github/bot-memory"
        self._conversation_context = None
        self._device_patterns = None
        
    def get_issue_memory(self, issue_number: int) -> Dict[str, Any]:
        """Get stored memory for an issue"""
        try:
            file_path = f"{self.memory_path}/issue-{issue_number}.json"
            contents = self.repo.get_contents(file_path)
            return json.loads(contents.decoded_content.decode())
        except:
            return {
                "issue_number": issue_number,
                "first_analyzed": None,
                "analysis_count": 0,
                "status": "new",
                "previous_responses": [],
                "user_provided_data": [],
                "similar_issues": [],
                "estimated_complexity": "unknown"
            }
    
    def save_issue_memory(self, issue_number: int, memory: Dict[str, Any]):
        """Save memory for an issue"""
        try:
            file_path = f"{self.memory_path}/issue-{issue_number}.json"
            content = json.dumps(memory, indent=2)
            
            try:
                # Update existing file
                contents = self.repo.get_contents(file_path)
                self.repo.update_file(
                    file_path,
                    f"Update bot memory for issue #{issue_number}",
                    content,
                    contents.sha
                )
            except:
                # Create new file
                self.repo.create_file(
                    file_path,
                    f"Create bot memory for issue #{issue_number}",
                    content
                )
        except Exception as e:
            print(f"Failed to save memory: {e}")
    
    def get_conversation_context(self) -> Dict[str, Any]:
        """Get conversation context and development history"""
        if self._conversation_context is None:
            try:
                contents = self.repo.get_contents(f"{self.memory_path}/conversation-context.json")
                self._conversation_context = json.loads(contents.decoded_content.decode())
            except:
                self._conversation_context = {}
        return self._conversation_context
    
    def get_device_patterns(self) -> Dict[str, Any]:
        """Get known device patterns and solutions"""
        if self._device_patterns is None:
            try:
                contents = self.repo.get_contents(f"{self.memory_path}/device-patterns.json")
                self._device_patterns = json.loads(contents.decoded_content.decode())
            except:
                self._device_patterns = {}
        return self._device_patterns

class IssueBot:
    """Main issue analysis bot"""
    
    def __init__(self):
        self.claude = anthropic.Anthropic(api_key=os.environ["CLAUDE_API_KEY"])
        auth = Auth.Token(os.environ["GITHUB_TOKEN"])
        self.github = Github(auth=auth)
        self.repo = self.github.get_repo(os.environ["GITHUB_REPOSITORY"])
        self.memory = IssueBotMemory(self.repo, os.environ["GITHUB_TOKEN"])
        self.monthly_budget = float(os.environ.get("MONTHLY_BUDGET", "10.00"))
        
    def check_budget(self) -> bool:
        """Check if we're within monthly budget"""
        # TODO: Implement budget tracking
        # For now, assume we're under budget
        return True
    
    def get_repo_context(self, issue_text: str) -> str:
        """Get relevant repository context based on issue content"""
        relevant_files = []
        
        # Smart file selection based on issue content
        if any(word in issue_text.lower() for word in ["sensor", "mapping", "entity", "device"]):
            relevant_files.extend(["custom_components/ecowitt_local/sensor_mapper.py", 
                                 "custom_components/ecowitt_local/const.py"])
        
        if any(word in issue_text.lower() for word in ["api", "gateway", "connection", "auth"]):
            relevant_files.append("custom_components/ecowitt_local/api.py")
        
        if any(word in issue_text.lower() for word in ["coordinator", "polling", "update"]):
            relevant_files.append("custom_components/ecowitt_local/coordinator.py")
        
        if any(word in issue_text.lower() for word in ["config", "setup", "integration"]):
            relevant_files.append("custom_components/ecowitt_local/__init__.py")
        
        # Default to manifest and const if no specific files identified
        if not relevant_files:
            relevant_files = ["custom_components/ecowitt_local/manifest.json", 
                            "custom_components/ecowitt_local/const.py"]
        
        context = "# Ecowitt Local Integration - Relevant Code Context\n\n"
        
        for file_path in relevant_files[:3]:  # Limit to 3 files to control token usage
            try:
                file_content = self.repo.get_contents(file_path)
                context += f"## {file_path}\n```python\n"
                content = file_content.decoded_content.decode()
                # Truncate large files to save tokens
                if len(content) > 10000:
                    content = content[:10000] + "\n# ... (file truncated to save tokens)"
                context += content
                context += "\n```\n\n"
            except:
                continue
        
        return context
    
    def find_similar_issues(self, issue_text: str) -> List[Dict[str, Any]]:
        """Find similar closed issues for context"""
        # Search for similar issues
        search_terms = []
        
        # Extract potential error messages or key terms
        error_patterns = [
            r"error[:\s]+([^.]+)",
            r"failed[:\s]+([^.]+)", 
            r"([A-Z][a-zA-Z]+Error|Exception)",
            r"(WH\d+|GW\d+|WS\d+)"  # Device models
        ]
        
        for pattern in error_patterns:
            matches = re.findall(pattern, issue_text, re.IGNORECASE)
            search_terms.extend(matches)
        
        similar = []
        for term in search_terms[:3]:  # Limit search terms
            try:
                issues = self.repo.get_issues(state='closed', sort='updated')
                for issue in issues[:5]:  # Check recent closed issues
                    if term.lower() in issue.body.lower() or term.lower() in issue.title.lower():
                        similar.append({
                            "number": issue.number,
                            "title": issue.title,
                            "url": issue.html_url
                        })
                        break
            except:
                continue
        
        return similar
    
    def analyze_issue(self, issue, triggering_comment=None) -> str:
        """Analyze issue and generate response"""
        # Get or create memory for this issue
        memory = self.memory.get_issue_memory(issue.number)
        memory["analysis_count"] += 1
        if memory["first_analyzed"] is None:
            memory["first_analyzed"] = datetime.now().isoformat()
        
        # Find similar issues
        similar_issues = self.find_similar_issues(issue.body)
        memory["similar_issues"] = similar_issues
        
        # Get repository context
        repo_context = self.get_repo_context(issue.body + " " + issue.title)
        
        # Get conversation context and device patterns
        conversation_context = self.memory.get_conversation_context()
        device_patterns = self.memory.get_device_patterns()
        
        # Get all comments for conversation history
        all_comments = issue.get_comments()
        bot_comments = [c for c in all_comments if c.user.login == "github-actions[bot]"]
        user_comments = [c for c in all_comments if c.user.login != "github-actions[bot]"]
        
        # Determine conversation context
        is_continuation = len(bot_comments) > 0
        conversation_history = ""
        
        if is_continuation:
            conversation_history = "\n# Previous Conversation\n"
            # Show last few exchanges
            recent_comments = sorted(all_comments, key=lambda x: x.created_at)[-6:]  # Last 6 comments
            for comment in recent_comments:
                author = "🤖 Bot" if comment.user.login == "github-actions[bot]" else f"👤 {comment.user.login}"
                conversation_history += f"\n**{author}** ({comment.created_at.strftime('%Y-%m-%d %H:%M')}):\n{comment.body[:500]}{'...' if len(comment.body) > 500 else ''}\n"
        
        # Handle triggering comment
        triggering_context = ""
        if triggering_comment:
            triggering_context = f"\n# Latest Comment (triggered this analysis)\n**👤 {triggering_comment.user.login}**:\n{triggering_comment.body}\n"
        
        # Prepare Claude prompt
        prompt = f"""You are an expert GitHub issue analyzer for the Ecowitt Local Home Assistant integration. 

You are having a CONVERSATION with users to help resolve their issues. This may be your first response or a continuation of an ongoing conversation. 

# Your Role
- Analyze GitHub issues for bugs, feature requests, and support questions
- Ask for additional information when needed (logs, device models, JSON data)
- Manage issue lifecycle (labels, status updates)
- Provide helpful responses to users
- Remember previous interactions with this issue

# Issue Context
**Issue #{issue.number}**: {issue.title}
**Author**: {issue.user.login}
**Labels**: {[label.name for label in issue.labels]}
**Created**: {issue.created_at}

# Issue Description
{issue.body}

# Bot Memory
Previous analysis count: {memory["analysis_count"]}
Issue status: {memory["status"]}
Similar issues found: {len(similar_issues)}

# Repository Context
{repo_context}

# Similar Issues (for reference)
{json.dumps(similar_issues, indent=2) if similar_issues else "None found"}

{conversation_history}

{triggering_context}

# Development History & Context
{json.dumps(conversation_context.get('previous_bug_fixes', {}), indent=2) if conversation_context else "Loading..."}

# Known Device Patterns
{json.dumps(device_patterns.get('patterns', {}), indent=2) if device_patterns else "Loading..."}

# Instructions
If this is a CONTINUATION (previous conversation exists):
1. **Acknowledge** the user's latest comment/information
2. **Analyze** any new information provided
3. **Continue** the troubleshooting process
4. **Ask follow-up questions** or **provide solutions** based on new data
5. **Reference** previous conversation context

If this is the FIRST response:
1. **Analyze** the issue thoroughly  
2. **Classify** it as: bug, enhancement, question, invalid
3. **Determine complexity**: simple, moderate, complex
4. **Request information** if needed (be specific about what JSON endpoints, device models, etc.)
5. **Suggest labels** to add/remove
6. **Provide next steps** for the user
7. **Reference similar issues** if relevant

# Response Format
Your response will be posted as a GitHub comment. Use markdown formatting.

Be helpful, professional, and specific. If you need more information, tell the user exactly what to provide and how to get it.

IMPORTANT: If this is a continuation, acknowledge what the user provided and build on the previous conversation. Don't repeat yourself.

Focus on:
- Home Assistant integration issues
- Ecowitt weather station hardware
- API communication problems
- Sensor mapping issues
- Device configuration problems

Use the development history and device patterns to:
- Recognize similar issues and reference past solutions
- Request appropriate diagnostic information
- Suggest likely fixes based on device patterns
- Avoid duplicate work by referencing existing fixes

Remember: Never claim something is "tested" or "works perfectly" until users confirm with actual hardware."""

        try:
            response = self.claude.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            analysis = response.content[0].text
            
            # Update memory
            memory["previous_responses"].append({
                "timestamp": datetime.now().isoformat(),
                "analysis": analysis[:500] + "..." if len(analysis) > 500 else analysis
            })
            
            # Save memory
            self.memory.save_issue_memory(issue.number, memory)
            
            return analysis
            
        except Exception as e:
            return f"❌ Error analyzing issue: {str(e)}\n\nPlease try again or contact @alexlenk for assistance."
    
    def should_respond_to_comment(self, comment, issue) -> bool:
        """Determine if the bot should respond to a comment"""
        comment_body = comment.body.lower()
        
        # Always respond to explicit bot mentions
        if '@bot' in comment_body:
            return True
        
        # Don't respond to maintainer comments unless they mention @bot
        if comment.user.login == 'alexlenk':
            return False
        
        # Response indicators - user is providing information or asking for help
        response_indicators = [
            'here is', 'here\'s', 'attached', 'json', 'logs', 'error',
            'tried', 'still', 'now', 'updated', 'installed', 'getting',
            'any help', 'please help', 'what should', 'how do', 'can you',
            'dump', 'output', 'curl', 'gateway', 'version', 'firmware'
        ]
        
        # Non-response indicators - user is just commenting, thanking, etc.
        non_response_indicators = [
            'thanks', 'thank you', 'got it', 'okay', 'ok', 'understood',
            'will try', 'working on it', 'investigating', 'looking into',
            'duplicate of', 'same as', 'closing', 'resolved'
        ]
        
        # Check for non-response indicators first (more specific)
        for indicator in non_response_indicators:
            if indicator in comment_body:
                return False
        
        # Check for response indicators
        for indicator in response_indicators:
            if indicator in comment_body:
                return True
        
        # If comment is longer than 50 words, likely contains useful information
        word_count = len(comment_body.split())
        if word_count > 50:
            return True
        
        # Default to not responding for short, unclear comments
        return False

    def add_labels_based_on_analysis(self, issue, analysis: str):
        """Add appropriate labels based on analysis"""
        labels_to_add = []
        
        # Extract suggested labels from analysis
        if "bug" in analysis.lower():
            labels_to_add.append("bug")
        if "enhancement" in analysis.lower() or "feature" in analysis.lower():
            labels_to_add.append("enhancement")
        if "question" in analysis.lower() or "support" in analysis.lower():
            labels_to_add.append("question")
        if "need" in analysis.lower() and "info" in analysis.lower():
            labels_to_add.append("needs-info")
        
        # Add device-specific labels
        device_patterns = {
            r"GW\d+": "gateway",
            r"WH\d+": "sensor", 
            r"WS\d+": "weather-station"
        }
        
        issue_text = issue.title + " " + issue.body + " " + analysis
        for pattern, label in device_patterns.items():
            if re.search(pattern, issue_text, re.IGNORECASE):
                labels_to_add.append(label)
        
        # Add labels (GitHub API will ignore duplicates)
        for label in labels_to_add:
            try:
                issue.add_to_labels(label)
            except:
                pass  # Label might not exist or already added
    
    def run(self):
        """Main bot execution"""
        if not self.check_budget():
            print("Monthly budget exceeded, skipping analysis")
            return
        
        issue_number = int(os.environ["ISSUE_NUMBER"])
        comment_id = os.environ.get("COMMENT_ID", "")
        
        try:
            issue = self.repo.get_issue(issue_number)
            
            # Check if this is a continuation of an existing conversation
            comments = issue.get_comments()
            bot_comments = [c for c in comments if c.user.login == "github-actions[bot]"]
            
            # If triggered by a comment, get the triggering comment and assess if response is needed
            triggering_comment = None
            if comment_id:
                try:
                    triggering_comment = issue.get_comment(int(comment_id))
                    # Check if bot response makes sense
                    if not self.should_respond_to_comment(triggering_comment, issue):
                        print(f"Comment doesn't require bot response, skipping")
                        return
                except:
                    pass
            
            # Analyze issue (pass triggering comment for conversation context)
            print(f"Analyzing issue #{issue_number}: {issue.title}")
            analysis = self.analyze_issue(issue, triggering_comment)
            
            # Post comment
            comment_body = f"""🤖 **Ecowitt Local Bot Analysis**

{analysis}

---
*This is an automated analysis. For complex issues, @alexlenk will review manually.*
*Bot powered by Claude AI • [Report issues](https://github.com/alexlenk/ecowitt_local/issues)*"""

            issue.create_comment(comment_body)
            
            # Add appropriate labels
            self.add_labels_based_on_analysis(issue, analysis)
            
            print(f"✅ Successfully analyzed issue #{issue_number}")
            
        except Exception as e:
            print(f"❌ Error processing issue: {e}")
            # Try to post error comment
            try:
                issue = self.repo.get_issue(issue_number)
                issue.create_comment(f"🤖 Error analyzing issue: {str(e)}\n\n@alexlenk please review manually.")
            except:
                pass

if __name__ == "__main__":
    bot = IssueBot()
    bot.run()