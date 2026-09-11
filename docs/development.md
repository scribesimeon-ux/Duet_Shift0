# Windows development with VS Code and PowerShell

Stage 2 establishes the Python package and environment only. There is no robotics application to run.

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

The printed package path must point into this repository's `src/duetshift` folder. Editable installation lets Python read package changes directly from the source folder. The `dev` extra installs pytest and its small required dependencies. Setuptools is the build backend. There are no robotics runtime dependencies.

## Verify and test

```powershell
python scripts/verify_environment.py
python -m pytest
```

The verification script reports the interpreter, OS, architecture, and whether Python is 3.12. A different Python version exits with an error. Missing MuJoCo, OpenVINO, LeRobot, and PyTorch are expected at this stage. The tests check the Python version, local package import, and package metadata only.

## Select the interpreter in VS Code

Press **Ctrl+Shift+P**, choose **Python: Select Interpreter**, and select the **duetshift-dev Python 3.12** interpreter. If it is not listed, use **Enter interpreter path** and browse to the executable reported by the earlier command. If the command is unavailable, VS Code's Python extension needs to be enabled or installed. No machine-specific interpreter path is stored in this repository.

Editor interpreter selection and activation in an already-open terminal are separate. Run the version and executable checks in the terminal you will use.

## Finish a session

```powershell
conda deactivate
```

This leaves the project environment in that terminal; it does not uninstall anything. Activate `duetshift-dev` again before the next development session.
