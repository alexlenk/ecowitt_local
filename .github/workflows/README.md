# GitHub Actions Workflows

This directory contains automated workflows for CI/CD and release management.

## Workflows Overview

### CI and Validation

#### `ci.yml` - Continuous Integration
- **Triggers**: Push to main, develop, bot/**, claude/** branches; PRs to main
- **Jobs**:
  - Run tests on Python 3.11 and 3.12
  - Linting with flake8
  - Type checking with mypy
  - Code coverage reporting
- **Purpose**: Ensure code quality and test coverage

#### `hassfest.yml` - Home Assistant Validation
- **Triggers**: Push and pull requests
- **Purpose**: Validate integration using Home Assistant's hassfest tool
- **Validates**: manifest.json, services.yaml, translations, and other HA requirements

#### `hacs.yml` - HACS Validation
- **Triggers**: Push and pull requests
- **Purpose**: Validate HACS compatibility
- **Validates**: hacs.json, repository structure, and HACS requirements

### Automated Release Process

#### `auto-pr.yml` - Auto PR Creation
- **Triggers**: Push to claude/** branches
- **Workflow**:
  1. Waits for all CI checks to pass
  2. Checks if PR already exists
  3. Extracts version from manifest.json
  4. Extracts release notes from CHANGELOG.md
  5. Creates PR to main branch with 'release' label
- **Requirements**: All CI tests must pass before PR creation

#### `auto-merge.yml` - Auto Merge Release PRs
- **Triggers**: PR events, CI workflow completion
- **Workflow**:
  1. Validates PR is from claude/** branch
  2. Checks PR has 'release' label
  3. Waits for all checks to complete successfully
  4. Auto-merges PR to main
  5. Deletes the merged branch
- **Safety**: Only merges PRs that pass all CI/CD checks

#### `auto-release.yml` - Auto Release Creation
- **Triggers**: Push to main branch
- **Workflow**:
  1. Extracts version from manifest.json
  2. Checks if tag already exists (prevents duplicates)
  3. Extracts release notes from CHANGELOG.md
  4. Creates git tag (e.g., v1.5.5)
  5. Creates GitHub Release
  6. HACS automatically detects the release
- **Output**: Published GitHub release with release notes

### Bot Workflows

#### `claude-code.yml` - Claude Code Bot Integration
- **Triggers**: Issue comments
- **Purpose**: Integration with Claude Code bot for automated issue responses

## Release Workflow Sequence

When you push changes to a `claude/**` branch with a version bump:

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Developer pushes to claude/feature-branch                │
│    - Updates manifest.json version                          │
│    - Updates CHANGELOG.md                                   │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. CI Workflows Run (ci.yml, hassfest.yml, hacs.yml)       │
│    - Tests on Python 3.11 & 3.12                            │
│    - Home Assistant validation                              │
│    - HACS validation                                        │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼ (All checks pass)
┌─────────────────────────────────────────────────────────────┐
│ 3. Auto PR Creation (auto-pr.yml)                          │
│    - Creates PR from claude/** to main                      │
│    - Adds release notes from CHANGELOG                      │
│    - Labels PR as 'release'                                 │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Auto Merge (auto-merge.yml)                             │
│    - Waits for final CI checks on PR                        │
│    - Merges PR to main                                      │
│    - Deletes claude/** branch                               │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼ (Merge to main triggers)
┌─────────────────────────────────────────────────────────────┐
│ 5. Auto Release (auto-release.yml)                         │
│    - Creates git tag v1.5.5                                 │
│    - Creates GitHub Release                                 │
│    - HACS detects new release                               │
└─────────────────────────────────────────────────────────────┘
```

## Required Secrets and Permissions

### Repository Settings

The workflows require the following permissions (set in repository settings):

- **Actions**: Read and write permissions
- **Contents**: Write (for creating tags and releases)
- **Pull Requests**: Write (for creating and merging PRs)

### GitHub Token

All workflows use the built-in `GITHUB_TOKEN`, no additional secrets needed.

## Manual Release Override

If automated workflows fail, you can manually create a release:

```bash
# 1. Ensure you're on main branch with latest changes
git checkout main
git pull origin main

# 2. Create and push tag
git tag -a v1.5.5 -m "Release v1.5.5"
git push origin v1.5.5

# 3. Create GitHub release manually
gh release create v1.5.5 \
  --title "v1.5.5 - Release Title" \
  --notes-file CHANGELOG.md \
  --latest
```

## Troubleshooting

### PR Not Created Automatically

- Check that all CI tests passed
- Verify branch name starts with `claude/`
- Check GitHub Actions logs for auto-pr.yml

### PR Not Auto-Merged

- Ensure PR has 'release' label
- Verify all CI checks are passing
- Check that PR is from a `claude/**` branch

### Release Not Created

- Verify tag doesn't already exist: `git tag -l`
- Check that version in manifest.json is new
- Review GitHub Actions logs for auto-release.yml

### Duplicate Releases

The auto-release workflow checks for existing tags before creating releases. If a tag exists, the workflow skips release creation.

## Best Practices

1. **Always update CHANGELOG.md** before pushing to claude/** branches
2. **Bump version** in manifest.json for every release
3. **Let CI complete** before expecting auto-PR creation
4. **Use semantic versioning** (major.minor.patch)
5. **Test locally** before pushing release branches

## Monitoring

View workflow runs at:
https://github.com/alexlenk/ecowitt_local/actions

Each workflow run provides detailed logs for debugging.
