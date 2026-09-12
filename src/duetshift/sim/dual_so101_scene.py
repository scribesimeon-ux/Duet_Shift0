"""Load two unchanged SO-101 instances with independent names and actuators."""

from dataclasses import dataclass

import mujoco

from duetshift.sim.so101_model import ArmInfo, asset_directory, describe_arm, initialize_rest, contact_report


@dataclass
class DualSO101Scene:
    model: mujoco.MjModel
    data: mujoco.MjData
    arm_a: ArmInfo
    arm_b: ArmInfo

    def inter_arm_contacts(self) -> list[dict]:
        return [
            contact for contact in contact_report(self.model, self.data)
            if {contact["body_a"].split("/")[0], contact["body_b"].split("/")[0]} == {"arm_a", "arm_b"}
        ]


def load_dual_so101() -> DualSO101Scene:
    model = mujoco.MjModel.from_xml_path(str(asset_directory() / "dual_scene.xml"))
    arm_a, arm_b = describe_arm(model, "arm_a/"), describe_arm(model, "arm_b/")
    data = initialize_rest(model, (arm_a, arm_b))
    return DualSO101Scene(model, data, arm_a, arm_b)
