# SO-101 upstream attribution

Robot design and simulation model: TheRobotStudio/SO-ARM100 contributors.

- Repository: https://github.com/TheRobotStudio/SO-ARM100
- Revision: `eecbe3e0a9ebb23e25ad7b2759b03884c6660903`
- Model: `Simulation/SO101/so101_new_calib.xml`
- License: Apache-2.0; the full upstream license is preserved at `upstream/LICENSE`.

The `upstream/` directory contains unmodified copies of the model, its 13 referenced STL files, the model README, and root license. All upstream XML comments and attribution are retained, including Onshape/onshape-to-robot lineage and servo-parameter credits. No applicable upstream NOTICE file was found in the inspected repository tree. See `source_manifest.json` for every exact source path and SHA256.

DuetShift authored `single_scene.xml` and `dual_scene.xml` as wrappers. The wrappers add a floor/light and instance placement/names only. They do not change robot geometry, inertias, joint limits, collision masks, or actuator parameters. See `docs/so101_model_provenance.md` in the repository for integration details and limitations.
