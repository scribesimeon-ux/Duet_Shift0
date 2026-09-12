# Repository and environment report

Audit date: 2026-09-12 (Asia/Calcutta). Findings describe this machine and the repository before scaffolding unless noted otherwise. No credentials or secret contents were read or recorded.

## Repository before changes

- Working directory and Git root: `C:\Users\HP\OneDrive\Desktop\AI Infra Hackathon000`.
- Git repository: yes. The configured project remote `Duet_Shift0` is consistent with the DuetShift brief; scaffolding proceeded in this workspace.
- Branch: `main` (unborn; no commits).
- `git status --short --branch`: `## No commits yet on main`; no tracked changes or untracked project files.
- Remote: `origin`, fetch and push URL `https://github.com/scribesimeon-ux/Duet_Shift0`.
- Last five commits: none. `git log -5 --oneline` failed because `main` has no commits.
- Reachability: the first sandboxed `git ls-remote origin` failed to connect to GitHub port 443. The permitted retry succeeded with exit code 0 and no advertised refs. The remote appears reachable and has no advertised branches/tags; write permissions were not tested.
- Top-level contents: `.git/` only.
- Existing README, dependency manifests, project files, source, tests, and local instructions: none found in the workspace. No `AGENTS.md` was found in the workspace or its immediate parent.
- Existing work to preserve: Git metadata, branch, and remote configuration. These were left unchanged; no commits, pushes, resets, downloads, or deletions were performed.

## Machine and shell

- OS reported by .NET: `Microsoft Windows 10.0.26200` (kernel/build string; a marketing edition was not inferred).
- OS architecture: X64.
- Shell: Windows PowerShell, Desktop edition, version `5.1.26100.9168`; reported build `10.0.26100.9168`.
- Git: `2.55.0.windows.4`.
- CPU from the Windows registry: `Intel(R) Core(TM) i5-10310U CPU @ 1.70GHz`.
- CPU and video-controller CIM queries failed with Access denied. The registry supplied the CPU name; GPU hardware remains unverified.
- The observed CPU is not the Intel Core Ultra Series 2/3 target specified in the brief. Access to target deployment hardware must be planned later.

## Python and tools

- `Get-Command` found `python.exe` at `C:\Python314\python.exe` and the launcher at `C:\WINDOWS\py.exe`.
- `py -0p` registered Python 3.14 as default at `C:\Python314\python.exe` and Python 3.2 (32-bit) at `C:\Python32\python.exe`.
- Direct checks: Python `3.14.4`, 64-bit AMD64; Python `3.2.2`, 32-bit Intel.
- `python3`, `conda`, `mamba`, `micromamba`, and `uv` were not found on PATH by `Get-Command -All`.
- Common `miniforge3`, `miniconda3`, and `anaconda3` directories under `C:\Users\HP` and `C:\ProgramData` were not found by targeted path checks. ProgramData directory-name inspection found no matching Conda/Miniforge/Mamba directory. Listing the user home directory was denied. Thus no such environment manager was detected, but absence in every possible location is not established.
- The audit covers PATH and Python launcher registrations, not every executable on disk.

## Package import probes

Each of `mujoco`, `openvino`, `lerobot`, and `torch` failed to import in both available Python interpreters. Python 3.14 reported `ModuleNotFoundError`; Python 3.2 reported `ImportError`, each naming the missing module.

PyTorch is not importable in either interpreter. Its accelerator detection cannot run, so CUDA, XPU, and MPS availability are unknown; this is not evidence that accelerators are absent. No package installation or upgrade was attempted. Probes ran via standard input with `-B` to suppress bytecode writes.

## Stage 2 decisions and limitations

- Select and verify a mutually compatible Python/dependency combination in Stage 2. No compatibility or version policy has been established for either existing interpreter.
- Decide the project-local environment location and manager before installing anything.
- Determine access to the Intel Core Ultra Series 2/3 deployment machine.
- Official challenge rules were not independently checked; the requirements document explicitly attributes its scope to the supplied brief.
- This is a OneDrive-hosted workspace. No sync settings were changed or tested.

## Stage 1 change and validation scope

Changes are limited to Markdown documentation, `.gitignore`, and empty `.gitkeep` placeholders. No dependency manifest, executable source code, robot asset, model, benchmark result, or evaluation result was added. No dependencies were installed, upgraded, or uninstalled. Functional tests are not applicable yet because there is no implementation and no existing test suite.

Validation passed: all 20 new files were reviewed using `git diff --no-index` because ordinary `git diff` does not show untracked files. Whitespace checks, secret-pattern scanning, required-document checks, README link checks, and representative `git check-ignore` checks passed. Source, important configs, documentation, evaluation summaries, and benchmark summaries remain trackable. Only Stage 1 is COMPLETE; Stages 2–21 remain NOT STARTED. `git diff --check` passed. All new files remain untracked, with no commit or push.

The final validation helper initially asserted exit code 0 for `git diff --no-index --check`; it stopped on `.gitignore` with a warning that LF will be replaced by CRLF when Git next touches the file. The helper was corrected to allow the no-index difference exit code while rejecting whitespace diagnostics and unexpected errors, then rerun. Git's line-ending settings were left unchanged.

## Stage 2 audit and dependency policy (2026-09-12)

The preceding sections preserve the historical Stage 1 findings. Before Stage 2 changes, the working tree was clean on `main`. Stage 1 was committed as `8569bed50a85b79d075f8b4c8e67f651a8ca80ac` (`chore: scaffold DuetShift repository`). Local `main`, the tracking reference `origin/main`, and a live `git ls-remote origin refs/heads/main` check all matched that commit. The first sandboxed remote check failed; the permitted retry succeeded. The origin URL was unchanged.

The Stage 1 scaffold was present; no packaging or environment files existed. `python --version` still reported 3.14.4, and `py -0p` listed 3.14 and 3.2-32. These are not the DuetShift project interpreters. Architecture remained X64. Relevant PATH entries were `C:\Python314\Scripts\` and `C:\Python314\`. Conda/Mamba were not found on PATH or at checked common installation paths. Winget was not visible in the sandbox (its WindowsApps path check was denied), but was found by the permitted host check. It was not used to install software.

Approved policy: a current-user Miniforge installation, one project environment named `duetshift-dev`, Python `3.12`, and pip. `environment.yml` uses conda-forge and excludes default channels. `pyproject.toml` supports `>=3.12,<3.13`, uses setuptools, declares no runtime dependencies, and provides a pytest development extra. This policy is portable but is not a fully pinned lockfile. The `scripts/` and `tests/` placeholders were preserved because Stage 2 forbids deleting working project files.

The installer was obtained from the [official Miniforge release 26.7.2-0](https://github.com/conda-forge/miniforge/releases/tag/26.7.2-0). Its SHA256 matched the official GitHub release asset digest: `71cf9519087be74fa53021219ff292beb2fc05fa49e0bb6eb0e0b6b14fccbaab`. It was downloaded into the user's temporary directory, outside Git. The documented current-user silent installer arguments were `/InstallationType=JustMe /RegisterPython=0 /S /D=C:\Users\HP\miniforge3`. No administrator elevation was requested by this command; tool permission was required for network access and writes outside the workspace.

### Stage 2 results

- Miniforge installation succeeded with exit code 0 at `C:\Users\HP\miniforge3`; Conda version `26.7.2`.
- The initial environment list contained only `base`. Exactly one project environment was created using `conda env create -f environment.yml -y`: `duetshift-dev` at `C:\Users\HP\miniforge3\envs\duetshift-dev`.
- Activated Python: `3.12.14`, executable `C:\Users\HP\miniforge3\envs\duetshift-dev\python.exe`. Platform: `Windows-11-10.0.26200-SP0`; architecture `AMD64`.
- `python -m pip --isolated install --index-url https://pypi.org/simple -e ".[dev]"` succeeded inside the activated environment. The isolated option avoided user pip configuration; the project was installed locally and development dependencies came from PyPI.
- `duetshift` version `0.1.0` imports from this repository's `src/duetshift/__init__.py`.
- Installed project/test packages: pytest `9.1.1`, colorama `0.4.6`, iniconfig `2.3.0`, pluggy `1.6.0`, Pygments `2.21.0`, and editable duetshift `0.1.0`.
- Environment packaging tools: pip `26.2.1`, setuptools `84.0.0`, wheel `0.48.0`, and packaging `26.3`, supplied by the Conda environment transaction. Conda also installed Python's required platform, SSL, compression, SQLite, timezone, and Tcl/Tk runtime packages. No unrelated developer tools were added.
- MuJoCo, OpenVINO, LeRobot, and PyTorch have NOT been installed. Verification reports each as `NOT INSTALLED (expected)`. None of the prohibited robotics, AI, driver, or infrastructure packages was installed by Stage 2.
- No project dependencies were installed globally or into Miniforge base. Miniforge base contains its own environment-manager dependencies. Direct version checks confirmed the original Python 3.14.4 and 3.2.2 installations remain available.
- `python scripts/verify_environment.py` passed; both the Python 3.12 and apparent `duetshift-dev` checks reported YES. `python -m pytest` passed all 3 tests. `python -m pip check` found no broken requirements.

### PowerShell changes and warnings

After a successful dry-run preview, `conda init powershell` modified the user's `C:\Users\HP\OneDrive\Documents\WindowsPowerShell\profile.ps1` to initialize Conda. It also refreshed Miniforge-owned `Scripts/activate`, `Scripts/deactivate`, `etc/profile.d/conda.sh`, `etc/fish/conf.d/conda.fish`, `shell/condabin/conda-hook.ps1`, and `etc/profile.d/conda.csh`. No unrelated shell profiles were initialized.

`conda config --set auto_activate_base false` updated user Conda configuration to prevent automatic base activation. Conda warned that `auto_activate_base` is an alias for `auto_activate`; a subsequent query confirmed `auto_activate: False`. No global PATH edit or Python registration was requested. The host's existing CurrentUser execution policy was `RemoteSigned`; it was left unchanged. The sandbox had reported all policy scopes Undefined and a different Documents profile path, so shell setup and acceptance were checked in fresh permitted host PowerShell sessions. Conda activation worked in those sessions. Existing VS Code terminals must be closed and reopened to load initialization.

Conda printed an informational promotion for its conda-pypi beta; that feature was not enabled. Git emitted LF-to-CRLF working-copy warnings; Git line-ending settings were not changed. No machine-specific VS Code configuration was created. Final Intel deployment remains a separate later stage.

### Final Stage 2 repository validation

Reviewed the tracked diff and all six new-file diffs. `git diff --check`, new-file whitespace checks, secret-pattern checks, text/binary and size checks, README links, and packaging/declaration checks passed. All nine changed/new files are small text files; no large binaries or robotics implementation were introduced. A negative verification probe simulated Python 3.11 version information within the project Python 3.12 process and confirmed exit code 1 with the required clear error. Stages 1 and 2 are COMPLETE; all 19 later stages are NOT STARTED. The three existing modified files and six new files remain uncommitted; nothing was pushed and no working project file was deleted.

## Stage 3: MuJoCo smoke foundation (2026-09-12)

### Repository and interpreter preflight

The preceding Stage 1/2 sections are historical records and are preserved. Stage 3 began with a clean working tree on `main`, at committed Stage 2 revision `ef2c765e775a127dcaa8d7d8e4e29db3cae9e32f`. Local `main`, stored `origin/main`, and a live `git ls-remote origin refs/heads/main` check matched. No local instructions or unrelated work needed changing.

The initial Stage 3 attempt stopped without modifications because the command session resolved `python` to `C:\Python314\python.exe` (3.14.4), with `CONDA_DEFAULT_ENV` unset. The user's debug continuation explicitly authorized activation, `conda run`, or direct invocation of the existing project interpreter. The new command session still did not inherit the user's terminal activation, so all subsequent installs and checks explicitly used `C:\Users\HP\miniforge3\envs\duetshift-dev\python.exe`. Before installing, Python `3.12.14` and that exact `sys.prefix` were asserted successfully; MuJoCo was absent. No environment was created, Miniforge reinstalled, or shell configuration changed.

### Installed dependency and recreation

Official MuJoCo installed successfully from PyPI into `duetshift-dev`, resolving the stable CPython 3.12 Windows AMD64 wheel at version **3.13.0**. Import and `mujoco.__version__` succeeded. The exact direct dependency `mujoco==3.13.0` is recorded in `pyproject.toml`; transitive dependencies are not pinned.

New transitive packages resolved by MuJoCo: absl-py 2.5.0, etils 1.14.0, fsspec 2026.7.0, glfw 2.10.2, numpy 2.5.3, PyOpenGL 3.1.10, typing_extensions 4.16.0, and zipp 4.1.0. These are package-declared dependencies, not separately selected graphics workarounds. The editable project was refreshed with `python -m pip --isolated install --index-url https://pypi.org/simple -e ".[dev]"` using the explicit environment interpreter. Pip replaced only the existing editable duetshift metadata during this normal reinstall. No project dependencies were installed globally.

`environment.yml` remains unchanged: create its Python/pip base, activate it, then run the editable project installation to install the exact direct MuJoCo version. This existing two-step workflow remains portable. Keep the source repository and its XML asset together; a standalone wheel containing the XML is outside this stage's scope. Official API/install reference: [MuJoCo Python documentation](https://mujoco.readthedocs.io/en/stable/python.html).

### Observed physics and graphics

- Physics PASS: a 0.1 kg sphere of radius 0.05 m starts at `(0, 0, 0.5)` above a plane. Gravity is `(0, 0, -9.81)` and timestep is 0.002 s. There are no robot, table, drawer, or downloaded scene assets.
- After 50 physics steps (0.1 s), the sphere center reached z = 0.449969 m. After 1000 steps (2 s), its center was z = 0.049632818 m. Named sphere/floor contact, sustained support, advancing time, and initial-state reset all passed. Small contact penetration is accepted by the 5 mm floor tolerance; no state edits fake motion.
- Offscreen RGB PASS: the official renderer produced a `(120, 160, 3)` uint8 frame with pixel range 0..183 using the named camera. No image dataset or file was saved.
- Interactive viewer PASS in the permitted Windows desktop process: the official passive viewer opened, synchronized 725 updates, and closed cleanly after the bounded run. This is programmatic lifecycle evidence; no visual screenshot inspection or manual early-close test was performed.
- Graphics workers are separate processes with a 20-second parent timeout. The viewer also has an 8-second loop limit. Default headless physics never creates a graphics context. Graphics failures, native exits, or timeouts are reported separately; they cannot turn an otherwise valid physics check into fabricated graphics success.

### Warnings and scope

Pip warned that `f2py.exe` and `numpy-config.exe` were installed in the environment's Scripts directory, which was not on this command session's PATH. This follows from using the explicit interpreter without shell activation. Neither helper executable is required by the smoke checks; no global PATH change was made. Users should activate `duetshift-dev` in their own PowerShell terminal. Git may report the existing LF-to-CRLF working-copy warnings; line-ending settings remain unchanged.

No PyTorch, LeRobot, OpenVINO, Speechmatics, ROS2, Docker, SO-101 models, control, IK, planning, manipulation, perception, or AI functionality was added. The future architecture is unchanged. Rendering has no observed Stage 5 blocker on this machine, but the check establishes only a small RGB frame, not future camera/perception behavior.

The first complete host pytest run reported 11 passed and one fixture setup error: `PermissionError: [WinError 5] Access is denied: 'C:\Users\HP\AppData\Local\Temp\pytest-of-HP'`. This affected the path-resolution test's unnecessary `tmp_path` fixture, not physics or graphics. The test now changes into the existing interpreter directory outside the repository without creating files. No temporary-directory permissions were changed or files deleted. Validation was rerun after this test-only correction.

### Final Stage 3 acceptance

The complete rerun passed **12 tests in 2.33 seconds**, including all 3 unchanged Stage 2 tests and the isolated offscreen render check; no tests were skipped. Environment verification and the default non-GUI smoke script exited 0. `pip check` reported no broken requirements, and installed duetshift metadata lists `mujoco==3.13.0`. Module discovery confirmed torch, lerobot, openvino, speechmatics, and rclpy are absent. The repository diff and new text files were reviewed for scope, whitespace, secrets, and unexpected binaries. Stage 3 is COMPLETE; Stages 4–21 remain NOT STARTED. No commits, pushes, resets, remote changes, or existing working-file deletions were performed.

## Stage 4: Dual SO-101 model (2026-09-12)

### Preflight and source

The working tree was clean on `main` at committed Stage 3 revision `76333679e4bbf12860d1d5a05300c0b02e091b5e`. Local and stored `origin/main` matched, and a live `git ls-remote origin refs/heads/main` check confirmed the same remote revision. Only the Stage 3 sphere asset and existing simulation/tests were present; no SO-101 or official challenge starter assets were found in the repository. Existing ignored editor configuration was left alone.

All execution used the explicitly verified `C:\Users\HP\miniforge3\envs\duetshift-dev\python.exe`: Python 3.12.14 and MuJoCo 3.13.0. This retains the authorized direct-interpreter approach instead of assuming that the automation shell inherited terminal activation. No package was installed or upgraded and no environment or shell configuration changed.

The priority-2 official robot source is TheRobotStudio/SO-ARM100, commit `eecbe3e0a9ebb23e25ad7b2759b03884c6660903`, `Simulation/SO101/so101_new_calib.xml`. No verifiable public Intel starter asset download was located. This is not described as an Intel-certified asset. Sixteen unmodified upstream files (MJCF, 13 meshes, model README, Apache-2.0 license) total 16,156,001 bytes. The manifest preserves exact source paths and SHA256 values. See [model provenance](so101_model_provenance.md) and the asset attribution file for full lineage and local wrapper changes.

### Model and physics results

The source single arm loaded first with six hinge joints, six existing position actuators, and both source reference sites. Joint/control ranges, actuator transmissions, force limits, collision masks, and gripper mapping were inspected. It has a moving-jaw hinge and a fixed jaw represented by source geometry. Initial joint coordinates and constant actuator targets are zero. No geometry, inertias, collision filters, gains, or joint ranges were edited.

The dual scene attaches two copies with `arm_a/` and `arm_b/` prefixes, twelve distinct joints/actuators, and bases at `(0, -0.22, 0)` and `(0, 0.22, 0)` metres. Base separation is 0.44 m. Both face approximately +X, with future shared workspace ahead/between them; task reachability has not been solved. Both scenes use gravity -9.81 m/s² and timestep 0.002 s.

Single and dual two-second idle simulations passed. Maximum observed joint drift was 0.000764865 rad and maximum speed 0.0503492 rad/s, with finite state/accelerations, advancing time, zero MuJoCo warning counters, and no initial or ongoing self/floor/inter-arm contacts. A test-only overlapping placement correctly produced negative-distance inter-arm contacts. This demonstrates collision detection is active; it does not certify all possible future robot configurations.

### Viewer and tests

`python scripts/run_dual_so101.py --viewer` succeeded in the permitted Windows desktop process. The official passive viewer performed 438 updates and closed cleanly after its bounded run. A separate 640x480 render was visually inspected and shows two separated, upright-mounted arms. Segmentation identified 8,135 visible arm-A pixels and 5,457 arm-B pixels, confirming both models appear in the view. The 43,415-byte inspection PNG is in ignored `tmp/stage04_dual_so101.png`, not a tracked dataset or benchmark artifact. Manual early-close interaction was not tested.

The full suite passed **23 tests in 3.53 seconds**, including all 12 previous tests and 11 new model tests. No tests were skipped. The new tests verify upstream hashes, source joint ranges, gripper/sites, collision activity, unchanged geometry/dynamics across instances, unique actuator mappings, base separation, initial contacts, and idle stability. `pip check` reported no broken requirements.

### Problems and limitations

The web browser fetcher could not retrieve three pinned upstream XML URLs (cache-miss errors). Direct HTTPS retrieval from those same official URLs succeeded. The first local wrapper's plain XML include failed to resolve a mesh path; replacing that include with native MJCF model attachment fixed the problem while keeping upstream files unchanged. These were source retrieval/integration issues, not missing packages.

The original base collision omission, convex mesh collision behavior, angular gripper convention, and lack of physical calibration are documented in provenance. Stable rest uses the source position servos, not passive unpowered behavior. No manipulation, IK, planning, policies, perception, table assets, or future-stage dependencies were introduced. Stage 5 will need task-specific contact and camera checks; no current model-load or rendering blocker was observed.

### Final Stage 4 repository checks

Environment verification, both inspection/run commands, all 23 tests, and `pip check` passed. Module discovery confirmed torch, lerobot, openvino, speechmatics, rclpy, transformers, and diffusers are absent. Dependency declarations and prior simulation/tests were unchanged. No ROS2, Docker, or other framework was added.

`git diff --check` and explicit new-file whitespace checks passed. Git still reports LF-to-CRLF warnings on local text files. Vendored original hashes and mesh sizes were verified, with no secrets or unexpected generated binary files found. Two upstream README Markdown line breaks are preserved using a narrowly scoped whitespace attribute. The only new binary files intended for version control are the 13 authenticated source meshes; the visual inspection PNG is ignored.

Final working tree: 4 existing documentation files modified and 29 new files. Stages 1–4 are COMPLETE; Stages 5–21 remain NOT STARTED. Nothing was committed, pushed, reset, rebased, or deleted, and Git remotes were not changed.
