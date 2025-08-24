# Project Tasks

Below is a checklist of the main tasks for the DroneStrike project together with pointers to the repository locations where each requirement is addressed.

## A. Implementation

- **Live demo for the application** – links to online demo videos are included at the top of [`README.md`](README.md).
- **Offline demo recording** – sample recordings are stored in [`droneAttackEdi.mp4`](droneAttackEdi.mp4) and [`droneAttackEdiPov2.mp4`](droneAttackEdiPov2.mp4).

## B. Software Development Process

- **User stories (min. 10) & backlog** – documented in [`user_stories.md`](user_stories.md).
- **Diagrams** – see [`MDS_UML.png`](MDS_UML.png) and [`MDS_PDF.pdf`](MDS_PDF.pdf).
- **Source control with Git** – this repository contains multiple branches and over ten commits with merges and pull requests (see `git log`).
- **Automated tests** – Python tests in [`test_pipeline.py`](test_pipeline.py) and JavaScript tests in [`WebApplication/src/tests`](WebApplication/src/tests).
- **Bug reporting & resolution** – issues are fixed through pull requests, e.g. the merge commit `3aed805` updating the autopilot state machine.
- **Code comments & standards** – the Python and Node code include inline comments and follow standard formatting; see [`autopilot.py`](autopilot.py) as an example.
- **Design patterns** – the autopilot uses a simple state machine pattern implemented in [`autopilot.py`](autopilot.py).
- **Prompt engineering / AI tools** – development leveraged AI assistants such as ChatGPT; these interactions are documented through commit messages and code comments.

