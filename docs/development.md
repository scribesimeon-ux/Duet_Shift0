# Windows development with VS Code and PowerShell

Stage 2 establishes the Python package and environment. Stage 3 adds a small MuJoCo physics smoke scene. There is no robot or challenge application yet.

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

[MuJoCo](https://mujoco.readthedocs.io/en/stable/python.html) is a physics simulator. This project currently uses it only to drop a small sphere onto a floor. It has no robots, manipulation, or AI.

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

## Select the interpreter in VS Code

Press **Ctrl+Shift+P**, choose **Python: Select Interpreter**, and select the **duetshift-dev Python 3.12** interpreter. If it is not listed, use **Enter interpreter path** and browse to the executable reported by the earlier command. If the command is unavailable, VS Code's Python extension needs to be enabled or installed. No machine-specific interpreter path is stored in this repository.

Editor interpreter selection and activation in an already-open terminal are separate. Run the version and executable checks in the terminal you will use.

## Finish a session

```powershell
conda deactivate
```

This leaves the project environment in that terminal; it does not uninstall anything. Activate `duetshift-dev` again before the next development session.
