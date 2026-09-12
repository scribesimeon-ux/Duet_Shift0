# Windows development with VS Code and PowerShell

Stages 2-5 provide the Python environment, MuJoCo smoke checks, authentic dual SO-101 robots and a physical challenge scene. Manipulation and AI are not implemented.

**FINAL INTEL DEPLOYMENT IS A SEPARATE LATER STAGE.**

## Open the project and terminal

In VS Code, choose **File -> Open Folder** and select the DuetShift repository folder. Choose **Terminal -> New Terminal**. Select PowerShell from the terminal dropdown if another shell opens. Run commands below from the repository root (the folder containing `pyproject.toml` and `environment.yml`).

## Activate the environment

```powershell
conda activate duetshift-dev
python --version
python -c "import sys; print(sys.executable)"
```

`(duetshift-dev)` at the start of the prompt means Conda has activated the project environment in that terminal. Python must report **3.12.x**. The executable must be inside the `duetshift-dev` environment, normally under Miniforge's `envs` folder. Stop if you see Python 3.14 or 3.2; do not install the project using those interpreters. The prompt is a useful hint, but the executable check is the confirmation.

If Conda was just initialized, close existing VS Code terminals using the trash icon and open a fresh PowerShell terminal. Restart VS Code if necessary. Shell initialization is loaded when a terminal starts, not retroactively in existing terminals.

During this setup, `conda init powershell` added the Conda initialization block to the current user's PowerShell profile and refreshed Conda's own activation scripts. `conda config --set auto_activate_base false` disabled automatic activation of the base environment in the user Conda configuration. No execution-policy change was needed. The audit report records the machine-specific locations; no VS Code interpreter setting was created.

If `conda` is not recognized, open **Miniforge Prompt** from the Windows Start menu and run:

```text
conda init powershell
```

Then open a fresh PowerShell terminal. This adds Conda initialization to your user PowerShell profile. If PowerShell reports that profile scripts are blocked, retain the exact error and resolve the shell policy separately; do not run an administrator terminal or change machine-wide policy blindly.

## Recreate the base environment on another machine

Install Miniforge from the [official conda-forge project](https://github.com/conda-forge/miniforge), choosing the installer appropriate to that machine. On Windows use the current-user installation and leave Python registration and global PATH changes disabled so other Python installations remain independent.

For a machine where `duetshift-dev` does not already exist:

```powershell
conda env create -f environment.yml
conda activate duetshift-dev
```

Use `conda env list` to check first. Do not create a second project environment or overwrite an existing one. `environment.yml` declares Python 3.12 and pip from conda-forge; `nodefaults` prevents fallback to other configured channels. This is a portable dependency policy, not an exact transitive lockfile. Resolved patch versions can change between installations.

## Install the local project for development

After activation, from the repository root:

```powershell
python -m pip install -e ".[dev]"
python -c "import duetshift; print(duetshift.__file__)"
```

The printed package path must point into this repository's `src/duetshift` folder. Editable installation lets Python read package changes directly from the source folder. The `dev` extra installs pytest and its small required dependencies. Setuptools is the build backend. The runtime dependency is official MuJoCo, pinned to the tested version in `pyproject.toml`. Creating the Conda environment alone is not sufficient: run this editable installation step afterward.

## Verify and test

```powershell
python scripts/verify_environment.py
python -m pytest
```

The verification script reports the interpreter, OS, architecture, and whether Python is 3.12. A different Python version or missing MuJoCo exits with an error. Missing OpenVINO, LeRobot, PyTorch, and Speechmatics remain expected. The tests cover the environment, package, smoke physics, and a separately marked offscreen rendering check.

## MuJoCo smoke simulation (Stage 3)

[MuJoCo](https://mujoco.readthedocs.io/en/stable/python.html) is a physics simulator. The Stage 3 smoke check drops a small sphere onto a floor. The separate Stage 4 and Stage 5 scenes described below add the robots and workspace.

From the repository root:

```powershell
conda activate duetshift-dev
python scripts/run_mujoco_smoke.py
```

Success shows the MuJoCo version, a 0.002-second timestep, the initial position at height 0.5 m, a lower position after gravity acts, and a final height near 0.05 m after 2 simulated seconds. Each physics check and the final `PHYSICS PASS` must pass. The check also resets the simulation. The default command uses no viewer or rendering.

To see the sphere fall using the optional official viewer:

```powershell
python scripts/run_mujoco_smoke.py --viewer
```

Close the window to exit early. It closes automatically after 8 seconds; a separate process timeout limits graphics startup/run time to 20 seconds. The sphere starts above the floor and falls once. The viewer starts from a fresh state after the headless validation.

To attempt one small camera frame without opening an interactive window:

```powershell
python scripts/run_mujoco_smoke.py --render
```

`OFFSCREEN PASS` confirms a non-uniform RGB frame with shape `(120, 160, 3)` and `uint8` channels. The frame is kept only in memory. Optional graphics failures print their own error/exit code or timeout warning; they do not change a successful core physics exit code. Do not mistake `PHYSICS PASS` for a graphics pass. This is a rendering capability check, not perception.

The complete test command is `python -m pytest`. Graphics tests run in a separate process so native graphics errors cannot crash the physics tests. For diagnosis only, `python -m pytest -m "not rendering"` isolates the core tests, and `python -m pytest -m rendering` runs the rendering check. A graphics test failure remains visible; there is no automatic blanket skip. Record any graphics error separately before future camera work, without installing arbitrary graphics packages.

The scene is resolved relative to the installed source file, so changing the working directory does not break the module. Keep the complete repository with its `assets/mujoco/smoke_scene.xml` and use editable installation. A standalone wheel without repository assets is not supported by this Stage 3 setup.

If an automation terminal does not inherit your activated Conda environment, explicitly use `conda run -n duetshift-dev python ...` or the existing environment's Python executable after verifying its version and path. Do not install into the system interpreter or create another environment.

## SO-101 model inspection (Stage 4)

Stage 4 adds TheRobotStudio's actual SO-101 model and a scene containing two instances. It adds no manipulation, IK, table-setting task, or AI. Read [SO-101 provenance](so101_model_provenance.md) for the exact source revision, license, limits, and collision caveats.

In a PowerShell terminal at the repository root:

```powershell
conda activate duetshift-dev
python --version
python -c "import sys; print(sys.executable)"
python scripts/inspect_so101.py
python scripts/run_dual_so101.py
```

Python must be 3.12 from `duetshift-dev`. The first script prints the upstream identifier, six joints, their angular limits, their actuator mappings, and gripper/body/site names. It runs two simulated seconds with fixed rest targets and should end with `SINGLE SO-101 PASS`.

The second script prints the `arm_a/` and `arm_b/` names, independently mapped actuators, a base separation of 0.44 m, and empty initial contact lists. A successful two-second rest hold ends with `DUAL SO-101 PASS`. Both arms use the exact same upstream geometry and existing position servos. They are held at their source zero pose; this is not task execution.

To view either model:

```powershell
python scripts/inspect_so101.py --viewer
python scripts/run_dual_so101.py --viewer
```

The dual viewer should show two separated SO-101 arms facing forward. Close it early if desired; it auto-closes after 8 seconds. A 25-second parent-process timeout also covers loading and graphics startup. No viewer process should be left running. A graphics failure is reported separately after the physics result and returns a non-zero status; `VIEWER PASS` indicates a clean viewer lifecycle.

Run all checks with `python -m pytest`, and check dependencies with `python -m pip check`. Stage 4 needs no new Python packages: MuJoCo 3.13.0 and its existing dependencies suffice. The copied robot meshes and their license live in `assets/robots/so101/upstream/`; do not remove that folder or edit it without updating provenance. No extra asset download is needed when using the complete repository.

Joint values, including the gripper hinge, are radians. They are not LeRobot's normalized 0–100 gripper convention. Base collision geometry is absent upstream, and mesh collision is not validated for arbitrary future task poses. The current checks establish a stable initial model only; later task/contact validation remains separate work.

## Select the interpreter in VS Code

Press **Ctrl+Shift+P**, choose **Python: Select Interpreter**, and select the **duetshift-dev Python 3.12** interpreter. If it is not listed, use **Enter interpreter path** and browse to the executable reported by the earlier command. If the command is unavailable, VS Code's Python extension needs to be enabled or installed. No machine-specific interpreter path is stored in this repository.

Editor interpreter selection and activation in an already-open terminal are separate. Run the version and executable checks in the terminal you will use.

## Finish a session

```powershell
conda deactivate
```

This leaves the project environment in that terminal; it does not uninstall anything. Activate `duetshift-dev` again before the next development session.

## Challenge scene, objects and cameras (Stage 5)

Open the authoritative DuetShift folder in VS Code and use **Terminal -> New Terminal**. On the current development machine the folder is `C:\Users\HP\Projects\DuetShift`. Confirm the terminal is in that folder before running commands. Activate and verify:

```powershell
conda activate duetshift-dev
python --version
python -c "import sys; print(sys.executable)"
python -c "import duetshift; print(duetshift.__file__)"
```

Python must be 3.12 from `duetshift-dev`, and the package path must point inside the folder you opened. If activation is not inherited by an automation shell, use the already verified environment interpreter explicitly or `conda run -n duetshift-dev python ...`. Do not reinstall packages merely to run Stage 5.

```powershell
python scripts/run_challenge_scene.py
python scripts/run_challenge_scene.py --seed 42
python scripts/run_challenge_scene.py --seed 43
python scripts/run_challenge_scene.py --seed 42 --render
python scripts/run_challenge_scene.py --seed 42 --viewer
```

Expect two yellow SO-101 arms mounted at a table, a yellow plate, blue hollow mug with a handle, green bottle, and fork/spoon inside an open-top drawer. The drawer is physically movable along its slide joint but stays closed during the normal run. The robots hold their rest pose. Nothing picks up objects or opens the drawer automatically.

A **seed** is an integer used to reproduce the initial scene. Running seed 42 again restores the same sampled positions, orientations, masses, friction and visual choices; seed 43 gives a different conservative variation. The script prints the samples, settled object positions, drawer position, cameras and PASS/FAIL checks.

`--render` checks all three cameras without opening a viewer. `--save-images` additionally saves small inspection PNGs under ignored `tmp/challenge_scene/`; these are temporary local files, not training data. `--viewer` opens the overview and closes after 8 seconds. Close the window early if desired. For a longer normal inspection session:

```powershell
python scripts/run_challenge_scene.py --seed 42 --viewer --viewer-seconds 120
```

Allowed viewer duration is 1-300 seconds; a parent timeout also bounds graphics startup. Rendering/viewer failures return a non-zero status and must be investigated before relying on later camera work. No graphics tests are silently skipped.

Run the complete regression suite and dependency check:

```powershell
python -m pytest
python -m pip check
```

Read [challenge scene details](challenge_scene.md) for layout, reset API, metadata, randomization ranges and known modeling limits. **FINAL INTEL DEPLOYMENT IS A SEPARATE LATER STAGE.**
