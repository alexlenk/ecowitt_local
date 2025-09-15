# 🤖 Ecowitt Local Issue Bot

An AI-powered GitHub bot that automatically analyzes issues, asks for clarification, and manages issue lifecycle.

## Features

### 🔍 **Smart Issue Analysis**
- Automatically analyzes new issues and bug reports
- Classifies issues as bugs, enhancements, or questions
- Provides detailed technical analysis
- References similar past issues

### 💭 **Memory System**
- Remembers previous interactions with each issue
- Tracks user-provided data and responses
- Builds context across multiple comments
- Learns from issue patterns

### 🏷️ **Lifecycle Management**
- Automatically adds appropriate labels
- Manages issue status and priority
- Suggests next steps for users
- Prevents duplicate analysis

### 💰 **Budget-Conscious**
- Tracks API usage and costs
- Smart context selection to minimize tokens
- Monthly spending limits
- Efficient file analysis

## How It Works

### Automatic Triggers
The bot automatically analyzes issues when:
- ✅ New issues are opened
- ✅ Issues are labeled with `bug`, `enhancement`
- ✅ Issues are reopened
- ✅ Someone comments `@bot` in an issue

### Manual Triggers
You can also trigger analysis by commenting:
- `@bot analyze` - Full issue analysis
- `@bot help` - Show available commands
- `@bot status` - Show issue memory/history

## What the Bot Does

### 1. **Initial Analysis**
```markdown
🤖 **Ecowitt Local Bot Analysis**

## Issue Classification
**Type**: Bug report
**Complexity**: Moderate
**Device**: GW3000 Gateway

## Analysis
This appears to be a content-type parsing issue affecting GW3000 gateways...

## Information Needed
To help resolve this issue, please provide:
1. Your gateway model and firmware version
2. A JSON dump from `http://YOUR_IP/get_livedata_info`
3. Home Assistant logs showing the error

## Similar Issues
- #123: Similar GW3000 parsing error (resolved)

## Suggested Labels
- `bug` 
- `gateway`
- `needs-info`

## Next Steps
1. Gather the requested information
2. I'll implement a fix based on the data
3. Test the fix with your specific setup
```

### 2. **Follow-up Responses**
The bot remembers previous interactions and provides contextual responses:
- References earlier conversations
- Tracks provided data
- Updates analysis based on new information

### 3. **Label Management**
Automatically adds relevant labels:
- `bug`, `enhancement`, `question`
- `gateway`, `sensor`, `weather-station` 
- `needs-info`, `duplicate`
- Device-specific labels (`GW3000`, `WH69`, etc.)

## Memory System

The bot stores memory in `.github/bot-memory/issue-{number}.json`:

```json
{
  "issue_number": 123,
  "analysis_count": 2,
  "status": "analyzing", 
  "user_provided_data": [
    {
      "type": "json_dump",
      "content": "...",
      "timestamp": "2025-01-15T11:00:00"
    }
  ],
  "similar_issues": [...],
  "estimated_complexity": "moderate"
}
```

## Budget & Limits

### Current Settings
- **Monthly Budget**: $10.00
- **Max Tokens per Issue**: 50,000
- **Rate Limit**: 3 analyses per hour
- **Memory Cleanup**: 90 days

### Cost Optimization
- Smart file selection based on issue content
- Context truncation for large files
- Caching of repository analysis
- Budget monitoring and alerts

## Commands for Maintainers

### Repository Variables
Set these in GitHub Settings → Secrets and variables → Actions:

```bash
# Required
CLAUDE_API_KEY=your-claude-api-key

# Optional
CLAUDE_MONTHLY_BUDGET=10.00  # Default: $10
MAX_TOKENS_PER_ISSUE=50000   # Default: 50k
ANALYSIS_RATE_LIMIT=3        # Default: 3/hour
```

### Manual Controls
The bot can be controlled via issue comments:

- `@bot pause` - Pause bot for this issue
- `@bot resume` - Resume bot analysis
- `@bot reset` - Clear issue memory
- `@bot debug` - Show detailed analysis info

## Privacy & Security

### What the Bot Stores
- ✅ Issue content and metadata
- ✅ Analysis history and responses
- ✅ User-provided diagnostic data
- ✅ Similar issue references

### What It Doesn't Store
- ❌ Personal information
- ❌ API keys or credentials
- ❌ Private repository data
- ❌ User behavioral data

### Data Retention
- Issue memory: 90 days after issue closure
- Analysis logs: 30 days
- Budget tracking: Current month only

## Troubleshooting

### Bot Not Responding
1. Check if budget limit was exceeded
2. Verify `CLAUDE_API_KEY` is set correctly
3. Look for errors in GitHub Actions logs
4. Ensure issue has required labels/triggers

### Unexpected Responses
1. Check `.github/bot-memory/issue-{number}.json` for context
2. Review recent analysis history
3. Use `@bot reset` to clear memory if needed

### Cost Concerns
1. Monitor spending in GitHub Actions logs
2. Adjust `CLAUDE_MONTHLY_BUDGET` if needed
3. Review token usage patterns
4. Use manual triggers instead of automatic

## Contributing

To improve the bot:
1. Update analysis prompts in `analyze-issue.py`
2. Add new trigger patterns in the workflow
3. Enhance memory system features
4. Submit feedback via issues

---

*Bot powered by Claude AI • Report issues with the bot itself as GitHub issues*