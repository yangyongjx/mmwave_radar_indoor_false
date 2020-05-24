#!/usr/bin/env python

import rospy
from sensor_msgs.msg import PointCloud2
from nav_msgs.msg import OccupancyGrid
import sensor_msgs.point_cloud2
from EnvClassifier import GroupingTraker
import threading

from visualization_msgs.msg import MarkerArray, Marker


class PubBlock:
    def __init__(self, thread_handle, event_handle, sub_func, callback_func=None):
        self.thread_handle = thread_handle
        self.event_handle = event_handle
        self.sub_func = sub_func
        self.callback_func = callback_func
        self.data = None

    def acquire_data(self):
        self.data = self.sub_func()
        if self.data is None:
            return False
        return True

    def update_data(self):
        self.event_handle.clear()
        if self.callback_func is not None:
            self.data = self.callback_func(self.data)
        self.thread_handle.data = self.data
        self.event_handle.set()
        rospy.loginfo("Pub " + self.thread_handle.thread_name)


class SubThread(threading.Thread):
    def __init__(self, thread_name="SubThread", duration=10.0):
        super(SubThread, self).__init__(name=thread_name)
        self.thread_name = thread_name
        self.duration = duration
        self._pub_blocks = {}

    def register_thread_CB(self, pub_block):
        self._pub_blocks[pub_block.thread_handle.thread_name] = pub_block

    def run(self):
        rospy.loginfo("Start sub thread: " + self.thread_name)
        while not rospy.is_shutdown():
            for pub_block in self._pub_blocks.values():
                if not pub_block.thread_handle.isAlive():
                    pub_block.thread_handle.start()
                if pub_block.acquire_data():
                    pub_block.update_data()
                else:
                    continue
            # Sleep every interval
            rospy.sleep(self.duration)


class PubThread(threading.Thread):
    def __init__(self, thread_name, publisher, pub_event, pub_rate=3):
        super(PubThread, self).__init__(name=thread_name)
        self.thread_name = thread_name
        self.data = None
        self.publisher = publisher
        self.pub_event = pub_event
        self.pub_rate = pub_rate

    def run(self):
        rospy.loginfo("Start pub thread: " + self.thread_name)
        while not rospy.is_shutdown():
            while self.pub_event.is_set():
                if self.data is not None:
                    # rospy.loginfo("Pub " + self.thread_name)
                    self.publisher.publish(self.data)
                    rospy.sleep(0.2)
                else:
                    rospy.loginfo("Nothing to Pub " + self.thread_name)


def pc2_grid_sub_func():
    # Get point data
    group_tracker = GroupingTraker.GroupingTracker()
    data = rospy.wait_for_message('/filtered_point_cloud_centers', PointCloud2, timeout=None)
    laser_grid = rospy.wait_for_message('/map', OccupancyGrid, timeout=None)
    point_cloud2 = sensor_msgs.point_cloud2.read_points(data)
    points = [[i[0], i[1]] for i in point_cloud2]
    # Generate points and marks
    if points is not None and len(points) > 0:
        env = group_tracker.getEnv(points, laser_grid)
        classified_marks = env.generateInfoMarkers()
    else:
        rospy.loginfo("No enough points for classification")
        return None
    # Generate markers
    return classified_marks


if __name__ == '__main__':
    # Pub components
    marker_array_pub = rospy.Publisher("/class_marker", MarkerArray, queue_size=1)
    marker_array_pub_event = threading.Event()
    marker_array_pub_thread = PubThread("PubMarkerArray", marker_array_pub, marker_array_pub_event)
    marker_pub_block = PubBlock(marker_array_pub_thread, marker_array_pub_event, pc2_grid_sub_func)

    pc2_sub_thread = SubThread("SubPC2", duration=2.0)
    pc2_sub_thread.register_thread_CB(marker_pub_block)
    try:
        rospy.init_node('map_classifier', anonymous=True)
        pc2_sub_thread.start()
        # spin() simply keeps python from exiting until this node is stopped
        rospy.spin()
    except rospy.ROSInterruptException:
        pass
