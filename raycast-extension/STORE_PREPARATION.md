# Raycast Extension - Store Preparation Checklist

This document tracks the preparation of the MeetingScribe Raycast extension according to [Raycast Store Guidelines](https://developers.raycast.com/basics/prepare-an-extension-for-store).

## ✅ Completed

### Package.json Requirements
- [x] License set to MIT
- [x] Latest Raycast API version (@raycast/api ^1.78.0)
- [x] npm dependencies with package-lock.json present
- [x] Title updated to "MeetingScribe" (Title Case)
- [x] Description updated to reflect recording focus
- [x] Keywords cleaned (removed non-English terms)
- [x] Categories appropriate: Productivity, Media

### Visual Assets
- [x] Icon: 512x512px PNG (icon.png)
- [x] Removed unused icon files (7 extra icons deleted)
- [x] Icon works in light/dark themes

### Documentation
- [x] README.md: Comprehensive setup and usage instructions in English
- [x] CHANGELOG.md: Proper format with {PR_MERGE_DATE} placeholder
- [x] Removed unnecessary docs (5 files: FIX_SUMMARY.md, INSTALL.md, SETUP_GUIDE.md, SOLUTION_FILE_SAVE_FIX.md, TROUBLESHOOTING.md)

### Command Naming
- [x] All commands follow Title Case convention
- [x] "Import Google" renamed to "Transcribe Audio" (verb-noun pattern)
- [x] Subtitles consistent across all commands

### Preferences
- [x] Required fields marked with `required: true`
- [x] All preferences have clear descriptions
- [x] Placeholders added to all text fields

### User Experience
- [x] package-lock.json exists and is committed

## ⚠️ Requires Attention

### Critical Issues

1. **Author Field** (BLOCKING)
   ```json
   "author": "Arthurhrk"
   ```
   - Error: User not found on Raycast platform
   - **Action Required**: Update to your actual Raycast username
   - Check your username at: https://www.raycast.com/account

### Code Quality Issues

The following lint errors need to be addressed before store submission:

1. **TypeScript `any` Types** (11 occurrences)
   - Files: cli.ts, daemon-client.ts, record.tsx, status.tsx, stdio.ts
   - Replace `any` with proper types

2. **Unused Variables** (7 occurrences)
   - Files: import-google.tsx, recent.tsx, record.tsx, recording-status.tsx, stdio.ts
   - Remove unused imports and variables

3. **Empty Block Statements** (2 occurrences)
   - File: stdio.ts lines 106, 109
   - Add proper error handling or remove

4. **Action Title Case** (1 occurrence)
   - File: import-google.tsx line 115
   - Use Title Case for action names

## 📋 Pre-Submission Checklist

Before submitting to Raycast Store:

- [ ] Update `author` field to valid Raycast username
- [ ] Run `npm run fix-lint` to auto-fix linting issues
- [ ] Manually fix remaining TypeScript errors
- [ ] Run `npm run build` successfully
- [ ] Test all commands in Raycast
- [ ] Verify extension works in both light and dark themes
- [ ] Add screenshots (2000x1250px, 16:10 aspect ratio)
  - Recommended: 3-6 screenshots showing key features
- [ ] Test on clean installation

## 🔧 Quick Fixes

### Fix Lint Errors
```bash
cd raycast-extension
npm run fix-lint
npm run lint  # Verify fixes
```

### Build and Test
```bash
npm run build
npm run dev  # Test in Raycast
```

## 📸 Screenshot Recommendations

Create screenshots showing:
1. Start Recording command with quality options
2. Recent Recordings list
3. Recording Status with progress
4. System Status showing audio devices
5. Transcribe Audio with Google Gemini
6. Extension preferences

Use Raycast's "Window Capture" feature (⌘ Space → type "window capture")

## 🔗 Resources

- [Raycast Store Guidelines](https://developers.raycast.com/basics/prepare-an-extension-for-store)
- [Extension Guidelines](https://developers.raycast.com/basics/create-your-first-extension)
- [API Reference](https://developers.raycast.com/api-reference/user-interface)
