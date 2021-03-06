import rospy
import numpy as np

from me212base.msg import WheelVelCmd
from apriltags.msg import AprilTagDetections

import detect_obstacles
from state import State
from drive import Drive

class Search(State):
    def __init__(self, current_input):
        self.current_input = current_input
        self.found_target = False
        self.tags_in_view = []
        self.apriltag_sub = rospy.Subscriber("/apriltags/detections", AprilTagDetections, self.apriltag_callback, queue_size = 1)
        self.velcmd_pub = rospy.Publisher("/cmdvel", WheelVelCmd, queue_size = 1)

        self.detect_obstacles_next = False
        if current_input - int(current_input) != 0:
            self.detect_obstacles_next = True
            self.current_input = int(current_input)

        self.right_turns = [7, 5, 9]
        self.left_turns = [0, 6, 8]

        self.classified_obstacles = False
        
    def run(self):
        wv = WheelVelCmd()

        if self.current_input in self.tags_in_view:
            print "found target"
            wv.desiredWV_R = 0
            wv.desiredWV_L = 0
            self.found_target = True
        elif self.current_input == 2:
            wv.desiredWV_R = 0
            wv.desiredWV_L = 0
        elif self.current_input in self.right_turns:
            wv.desiredWV_R = -0.1
            wv.desiredWV_L = 0.1
        else:
            # turn left
            wv.desiredWV_R = 0.1
            wv.desiredWV_L = -0.1

        wv.desiredWrist = 0.0
        self.velcmd_pub.publish(wv)
        rospy.sleep(.01)
    
    def next_input(self):
        return self.current_input

    def next_state(self):
        if self.detect_obstacles_next:
            return detect_obstacles.DetectObstacles(self.current_input)
        return Drive(self.current_input)

    def is_finished(self):
        return self.found_target

    def is_stop_state(self):
        return False
        
    def apriltag_callback(self, data):
        del self.tags_in_view[:]
        for detection in data.detections:
            self.tags_in_view.append(detection.id)

    def __str__(self):
        return "Search(%s)" % (self.current_input)