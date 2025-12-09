# Kiro Steering Files

This directory contains **Kiro steering files** that capture the architectural patterns, development guidelines, and issue resolution strategies for the ecowitt_local Home Assistant integration.

## Purpose

These files serve as quick-reference guides for:
- AI assistants (like Claude) working on this codebase
- New developers getting familiar with the architecture
- Experienced developers looking for specific patterns
- Maintaining consistency across contributions

## Files

### 📐 architectural_patterns.md
**Comprehensive architectural documentation**
- Device support patterns (Device Type String Mismatch, Hex ID System)
- Entity creation architecture
- Implementation philosophy and anti-patterns
- Error handling patterns
- Testing requirements

**When to use**: Understanding how the integration is structured and why.

---

### 🛠️ development_guidelines.md
**Day-to-day development practices**
- Code style and testing commands
- Issue management protocol (critical: never close issues prematurely!)
- Release process and HACS requirements
- Device support checklist
- Configuration structure

**When to use**: Setting up your development environment or preparing a release.

---

### 🔍 issue_resolution_patterns.md
**Troubleshooting and problem-solving guide**
- Six documented issue patterns with solutions:
  1. Device Type String Mismatch
  2. Incomplete Entity Creation
  3. Content-Type API Problems
  4. Embedded Unit Parsing
  5. Service Parameter Type Errors
  6. Home Assistant Breaking Changes
- 5-step resolution workflow
- File location quick reference

**When to use**: Debugging an issue or implementing a fix.

---

### ⚡ quick_reference.md
**One-page cheat sheet**
- 1-minute guide to adding device support
- Critical don'ts
- Success checklist
- Common fixes
- Testing commands
- Pro tips

**When to use**: Quick lookup when you know what you're doing but need a reminder.

---

### 🤖 automated_agent_rules.md
**Rules for automated agents and bots**
- WH77 test sensor restrictions (intentionally unfixed quality control mechanism)
- Allowed and prohibited automated work
- Issue handling protocol
- Safety guards and quality control checkpoints

**When to use**: Before any automated agent starts work on this repository.

---

## Relationship to CLAUDE.md

These Kiro steering files **complement** the main CLAUDE.md file:

| CLAUDE.md | Kiro Steering Files |
|-----------|-------------------|
| Comprehensive narrative | Quick-reference format |
| Complete context | Focused patterns |
| Examples with history | Actionable checklists |
| ~678 lines | ~1000 lines total (4 files) |
| Read once thoroughly | Reference frequently |

**Recommendation**: 
1. Read CLAUDE.md first for complete understanding
2. Use Kiro files for daily reference and quick lookups

## Usage Examples

### Adding WH88 Support
1. Check `quick_reference.md` for the 1-minute guide
2. Reference `architectural_patterns.md` for hex ID system details
3. Follow WH90 example in sensor_mapper.py (NOT WH77 - it's a test sensor)
4. Use `development_guidelines.md` for testing commands

### Debugging Entity Creation Issue
1. Check `issue_resolution_patterns.md` for Pattern 2 (Incomplete Entity Creation)
2. Follow debug points provided
3. Reference `architectural_patterns.md` for entity creation pipeline

### Preparing a Release
1. Follow `development_guidelines.md` release process section
2. Verify HACS tag requirements
3. Use issue management protocol for commenting on fixed issues

### Working as an Automated Agent
1. **FIRST**: Read `automated_agent_rules.md` to understand WH77 restrictions
2. Check if issue involves WH77 → If yes, recognize as test scenario and STOP
3. For legitimate issues: Follow documented patterns and protocols

## Maintenance

These files should be updated when:
- New architectural patterns emerge
- New issue patterns are discovered and solved
- Development processes change
- Best practices evolve

**Update frequency**: As needed, typically with significant architectural changes or after solving novel issues.

## History

**Created**: December 9, 2025  
**Purpose**: Consolidate architectural knowledge from CLAUDE.md and codebase analysis  
**Initial Content**: Based on v1.5.8 codebase and successful WH90 implementations  
**Note on WH77**: WH77 is a test sensor for quality control, intentionally unfixed to validate agent behavior  

## Contributing

When updating these files:
1. Maintain the quick-reference format
2. Use examples from actual code (not hypothetical)
3. Keep checklists actionable
4. Cross-reference between files when appropriate
5. Update README.md if adding new files

---

**Note**: These are living documents that capture institutional knowledge. Treat them as part of the codebase documentation, not separate external docs.