# Bot Memory Storage

This directory stores the bot's memory for issue analysis and lifecycle management.

## Structure

- `issue-{number}.json` - Memory for each issue including:
  - Analysis history
  - User-provided data
  - Similar issues found
  - Response patterns
  - Complexity estimates

## Memory Format

```json
{
  "issue_number": 123,
  "first_analyzed": "2025-01-15T10:30:00",
  "analysis_count": 2,
  "status": "analyzing",
  "previous_responses": [
    {
      "timestamp": "2025-01-15T10:30:00",
      "analysis": "Initial analysis summary..."
    }
  ],
  "user_provided_data": [
    {
      "type": "json_dump",
      "content": "...",
      "timestamp": "2025-01-15T11:00:00"
    }
  ],
  "similar_issues": [
    {
      "number": 456,
      "title": "Similar issue title",
      "url": "https://github.com/..."
    }
  ],
  "estimated_complexity": "moderate"
}
```

## Privacy

This memory system:
- ✅ Stores only issue-related data
- ✅ Is public in the repository  
- ✅ Helps bot provide better responses
- ✅ Can be deleted anytime by maintainers