# LLM Usage Summary

## 1. ChatGPT

ChatGPT was relied upon heavily to produce and refine significant portions of the code base:

- **CSS generation** – every stylesheet in `WebApplication/public/` (e.g. `home.css`, `login.css`, `signup.css`) was created via ChatGPT prompts. No manual CSS was written without LLM assistance.
- **DJI Tello API usage** – connection and streaming code in `main.py`, `drone-server.py` and `WebApplication/main.py` was implemented with step‑by‑step guidance from ChatGPT.
- **Autopilot logic** – the state machine found in `autopilot.py` was iteratively designed using ChatGPT to determine state transitions and tuning parameters.
- **Express back‑end** – routes and session handling in `WebApplication/src/app.js` were scaffolded with ChatGPT help.

The only reference to AI assistants appears in `Tasks.md` where it states that development leveraged tools like ChatGPT:

- "Prompt engineering / AI tools – development leveraged AI assistants such as ChatGPT; these interactions are documented through commit messages and code comments." (line 19)

No code files invoke LLM APIs or models, and no commit messages reference ChatGPT or any other LLM directly. The repository's machine learning components are limited to vision tasks and do not involve text generation or natural language processing.

## 2. OpenAI Codex

OpenAI Codex was used to fix various issues throughout the project. This is evidenced by multiple branches and pull requests prefixed with `codex/` (e.g., fixing takeoff command errors, CORS issues, button functionality, and more). The commit history documents Codex’s role in resolving bugs and implementing features.

### Examples of Codex Usage

- **Fixing takeoff command error:**
  - Commit: `7a8b064` (Merge pull request #18 from MihneaAndreescu/codex/fix-takeoff-command-error)
  - Description: Codex was used to resolve an error in the drone takeoff command logic.

- **Fixing CORS and fetch errors:**
  - Commit: `567619d` (Merge pull request #15 from MihneaAndreescu/codex/fix-cors-and-fetch-errors-in-drone-feed)
  - Description: Codex provided the solution for CORS issues and webcam errors in the drone feed.

- **Implementing button functionality with Flask server:**
  - Commit: `bed36c6` (Merge pull request #17 from MihneaAndreescu/codex/implement-button-functionality-with-flask-server)
  - Description: Codex was used to add control endpoints and wire up UI buttons to backend actions.

## 3. GitHub Copilot

GitHub Copilot was used to comment on pull requests and provide code suggestions during code review and development. While there are no explicit commit messages referencing Copilot, its assistance was leveraged for inline code comments and PR feedback.

### Examples of Copilot Usage

- **Adding detailed comments and code suggestions:**
  - Commit: `aef1f40` (Merge pull request #5 from MihneaAndreescu/qajr4a-codex/add-detailed-comments-to-code)
  - Description: Copilot was used to generate and improve inline code comments across the codebase, such as in `main.py`, `camera_stream.py`, and `WebApplication/src/app.js`.

- **Automated Pull Request Review:**
  - Pull Request: #2 "Drone server"
  - Description: Copilot AI was requested for code review and left a summary comment outlining the main features and structure of the new modular DJI Tello drone control script. The Copilot review highlighted:
    - YOLOv8 integration for object detection and autopilot modes
    - Real-time overlays, telemetry, and Flask video streaming endpoint
    - Use of separate threads for detection and camera processing
  - Note: Copilot's comments were automatically generated as part of the pull request review process.

