#!/usr/bin/env python
#
# Created by zgh on 2020/4/15.
#

# ROS imports
import rospy
import tf
import math
import sys
sys.setrecursionlimit(5000)

from nav_msgs.msg import Odometry
from std_msgs.msg import Int8
from nav_msgs.msg import OccupancyGrid
from geometry_msgs.msg import PoseStamped

# Numpy
import numpy as np

current_position_ = np.zeros(2)
current_orientation_ = 0.0
desired_position_ = np.zeros(2)

# Map data
dat = None
wid = None
heigh = None
res = None
xorg = None
yorg = None
# Map for DFS
filtered_map = None
RevMap = None

"""
Using dfs to find the first unknown place to reach.
input: "force_unknown_find"  occupancy_grid(map)  
output: start_point, goal_point
"""


def visual_pub(tx, ty):
    target_pose = PoseStamped()

    # Transform res_point to goal_point
    target_pose.header.seq = 0
    target_pose.header.stamp = rospy.get_rostime()
    target_pose.header.frame_id = "map"
    target_pose.pose.position.z = 0.0
    target_pose.pose.orientation.x = 0.0
    target_pose.pose.orientation.y = 0.0
    target_pose.pose.orientation.w = 1.0

    target_pose.pose.position.x = xorg + tx * res
    target_pose.pose.position.y = yorg + ty * res
    goal_pub.publish(target_pose)


def ForceUnknownFindCB(msg):
    global dat, wid, heigh, res, filtered_map, current_position_, xorg, yorg, res
    rospy.loginfo("Calculate goal in nearest unknown part.")
    # If no map input, return
    if dat is None:
        return

    m_xorg = xorg
    m_yorg = yorg
    m_wid = wid
    m_heigh = heigh

    filtered_map = np.array(dat).reshape((m_wid, m_heigh))
    rospy.loginfo("Map: %s, %s, %d, %d, %d, %d", m_xorg, m_yorg, m_wid, m_heigh, filtered_map.shape[0],
                  filtered_map.shape[1])

    RevMap = np.zeros(filtered_map.shape, dtype=np.int)
    # Format map
    for i in range(m_wid):
        for j in range(m_heigh):
            if filtered_map[i, j] == -1:
                filtered_map[i, j] = 255
    point_index = np.zeros(2, dtype=np.int)
    point_index[0] = int((current_position_[0] - m_xorg) / res)
    point_index[1] = int((current_position_[1] - m_yorg) / res)

    target_pose = PoseStamped()

    # Transform res_point to goal_point
    target_pose.header.seq = 0
    target_pose.header.stamp = rospy.get_rostime()
    target_pose.header.frame_id = "map"
    target_pose.pose.position.z = 0.0
    target_pose.pose.orientation.x = 0.0
    target_pose.pose.orientation.y = 0.0
    target_pose.pose.orientation.w = 1.0

    res_point = FindUnkownArea(point_index, RevMap.copy())
    if res_point is not None:
        if res_point[0] != point_index[0] or res_point[1] != point_index[1]:
            target_pose.pose.position.x = m_xorg + res_point[0] * res
            target_pose.pose.position.y = m_yorg + res_point[1] * res
            rospy.loginfo("Publish neareast unknown point value" + str(
                filtered_map[int(res_point[0])][int(res_point[1])]))
            goal_pub.publish(target_pose)

            p_point = np.zeros(2, int)
            for x_d in range(-1, 2):
                p_point[0] = x_d + res_point[0]
                if p_point[0] < 0 or p_point[0] >= m_wid: continue
                for y_d in range(-1, 2):
                    p_point[1] = y_d + res_point[1]
                    if p_point[1] < 0 or p_point[1] >= m_heigh: continue
                    rospy.loginfo("%d, %d, %d", p_point[0], p_point[1], filtered_map[p_point[0], p_point[1]])

    else:
        target_pose.pose.position.x = 0.0
        target_pose.pose.position.y = 0.0
        goal_pub.publish(target_pose)
        rospy.loginfo("Returning!")
        rospy.on_shutdown(myhook)


def FindUnkownArea(point_index, local_map):
    # visual_pub(point_index[0], point_index[1])

    global filtered_map
    m_wid = filtered_map.shape[0]
    m_heigh = filtered_map.shape[1]
    if int(local_map[int(point_index[0])][int(point_index[1])]) == 1:
        return None
    else:
        local_map[int(point_index[0])][int(point_index[1])] = 1

    if int(filtered_map[int(point_index[0])][int(point_index[1])]) == 100:
        return None
    elif int(filtered_map[int(point_index[0])][int(point_index[1])]) == 255:
        all_unkown_flag = True
        p_point = np.zeros(2, int)
        for x_d in range(-3, 4)[::-1]:
            p_point[0] = x_d + point_index[0]
            if p_point[0] < 0 or p_point[0] >= m_wid: continue
            for y_d in range(-3, 4)[::-1]:
                p_point[1] = y_d + point_index[1]
                if p_point[1] < 0 or p_point[1] >= m_heigh: continue
                if filtered_map[int(p_point[0])][int(p_point[1])] != 255:
                    all_unkown_flag = False
                    break
        if all_unkown_flag:
            return point_index

    res_point = None
    t_point = np.zeros(2)
    local_map[int(point_index[0])][int(point_index[1])] = 1
    for x_d in range(-1, 2):
        t_point[0] = x_d + point_index[0]
        if t_point[0] < 0 or t_point[0] >= m_wid: continue
        for y_d in range(-1, 2):
            t_point[1] = y_d + point_index[1]
            if t_point[1] < 0 or t_point[1] >= m_heigh or (
                    t_point[0] == point_index[0] and t_point[1] == point_index[1]): continue
            tmp_res = FindUnkownArea(t_point, local_map.copy())
            if tmp_res is not None:
                return tmp_res
    return None


"""
Return the angle normalized between [-pi, pi].
"""


def odomCallback(odometry_msg):
    global current_position_
    global current_orientation_
    current_position_[0] = odometry_msg.pose.pose.position.x
    current_position_[1] = odometry_msg.pose.pose.position.y
    (r, p, y) = tf.transformations.euler_from_quaternion(
        [odometry_msg.pose.pose.orientation.x, odometry_msg.pose.pose.orientation.y,
         odometry_msg.pose.pose.orientation.z, odometry_msg.pose.pose.orientation.w])
    current_orientation_ = wrapAngle(y)
    return


def OccupancyGridCallback(msg):
    global dat, wid, heigh, res, xorg, yorg
    dat = msg.data
    wid = msg.info.width
    heigh = msg.info.height
    res = msg.info.resolution
    xorg = msg.info.origin.position.x
    yorg = msg.info.origin.position.y


def wrapAngle(ang):
    """
    Return the angle normalized between [-pi, pi].
    """
    ang = ang % (2 * np.pi)
    if (isinstance(ang, int) or isinstance(ang, float)) and (ang > np.pi):
        ang -= 2 * np.pi
    elif isinstance(ang, np.ndarray):
        ang[ang > np.pi] -= 2 * np.pi
    return ang


def myhook():
    print "shutdown force_unknown_find_handler!"


if __name__ == '__main__':
    rospy.init_node('force_unknown_find_handler', log_level=rospy.INFO)
    rospy.loginfo("Start find unknown point")
    force_unknown_find_sub = rospy.Subscriber("/force_unknown_find", Int8, ForceUnknownFindCB, queue_size=1)
    odom_sub = rospy.Subscriber("/odom", Odometry, odomCallback, queue_size=1)
    map_sub_ = rospy.Subscriber("/map", OccupancyGrid, OccupancyGridCallback, queue_size=1)
    goal_pub = rospy.Publisher("/unknown_goal", PoseStamped, queue_size=1)
    rospy.spin()
