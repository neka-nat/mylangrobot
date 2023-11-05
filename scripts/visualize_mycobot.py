import numpy as np
import kinpy as kp

chain = kp.build_chain_from_urdf(open("../data/mycobot/mycobot.urdf").read())

print(chain.get_joint_parameter_names())
th = np.deg2rad([0, 0, 0, 0, 0, 0])
ret = chain.forward_kinematics(th)
print(ret)
viz = kp.JointAngleEditor(chain, mesh_file_path="../data/mycobot/", axes=True, initial_state=th)
viz.spin()
