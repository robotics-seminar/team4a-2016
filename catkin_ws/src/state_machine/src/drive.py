import rospy
import tf
import numpy as np
import threading
import serial
import pdb
import traceback
import sys
import tf.transformations as tfm

from me212base.msg import WheelVelCmd
from apriltags.msg import AprilTagDetections
import me212helper.helper as helper

from state import State
from stop import Stop

class Drive(State):
    def __init__(self, current_input):
        self.current_input = current_input

        self.arrived = False
        self.arrived_position = False

        self.target_pose2d = self.get_target_pose()

        self.tags_in_view = []
        self.detection_poses = {}
        
        self.listener = tf.TransformListener()
        self.br = tf.TransformBroadcaster()
        
        rospy.sleep(0.5)
        self.apriltag_sub = rospy.Subscriber("/apriltags/detections", AprilTagDetections, self.apriltag_callback, queue_size = 1)
        self.velcmd_pub = rospy.Publisher("/cmdvel", WheelVelCmd, queue_size = 1)
        
    def run(self):
        april_tag_source = '/apriltag' + str(self.current_input)

        if self.current_input in self.tags_in_view:
            poselist_tag_cam = helper.pose2poselist(self.detection_poses[self.current_input])
            pose_tag_base = helper.transformPose(pose = poselist_tag_cam,  sourceFrame = '/camera', targetFrame = '/robot_base', lr = self.listener)
            poselist_base_tag = helper.invPoselist(pose_tag_base)
            pose_base_map = helper.transformPose(pose = poselist_base_tag, sourceFrame = april_tag_source, targetFrame = '/map', lr = self.listener)
            helper.pubFrame(self.br, pose = pose_base_map, frame_id = '/robot_base', parent_frame_id = '/map', npub = 1)
            self.drive()
        else:
            self.stop()
    
    def next_input(self):
        # change later
        return 0

    def next_state(self):
        # change later
        return Stop(self.next_input())

    def is_finished(self):
        return self.arrived

    def is_stop_state(self):
        return False
    
    ## next step: use distance information to set target
    def get_target_pose(self):
        if self.current_input == 2:
            return [.25, 0.9, np.pi/2]
        return [0, 0, 0]

    def apriltag_callback(self, data):
        del self.tags_in_view[:]
        for detection in data.detections:
            self.tags_in_view.append(detection.id)
            self.detection_poses[detection.id] = detection.pose
    
    def stop(self):
        wv = WheelVelCmd()

        if not rospy.is_shutdown():
            print '1. Tag not in view, Stop'
            wv.desiredWV_R = 0  # right, left
            wv.desiredWV_L = 0
            self.velcmd_pub.publish(wv)

        rospy.sleep(.01)

    def drive(self):
        wv = WheelVelCmd()

        if not rospy.is_shutdown():
            
            # 1. get robot pose
            robot_pose3d = helper.lookupTransform(self.listener, '/map', '/robot_base')
            
            if robot_pose3d is None:
                print '1. Tag not in view, Stop'
                wv.desiredWV_R = 0  # right, left
                wv.desiredWV_L = 0
                self.velcmd_pub.publish(wv)  
                return
            
            robot_position2d = robot_pose3d[0:2]
            target_position2d = self.target_pose2d[0:2]
            
            robot_yaw = tfm.euler_from_quaternion(robot_pose3d[3:7]) [2]
            robot_pose2d = robot_position2d + [robot_yaw]
            
            # 2. navigation policy
            # 2.1 if       in the target, 
            # 2.2 else if  close to target position, turn to the target orientation
            # 2.3 else if  in the correct heading, go straight to the target position,
            # 2.4 else     turn in the direction of the target position
            
            pos_delta = np.array(target_position2d) - np.array(robot_position2d)
            robot_heading_vec = np.array([np.cos(robot_yaw), np.sin(robot_yaw)])
            heading_err_cross = helper.cross2d( robot_heading_vec, pos_delta / np.linalg.norm(pos_delta) )
            
            # print 'robot_position2d', robot_position2d, 'target_position2d', target_position2d
            # print 'pos_delta', pos_delta
            # print 'robot_yaw', robot_yaw
            # print 'norm delta', np.linalg.norm( pos_delta ), 'diffrad', diffrad(robot_yaw, self.target_pose2d[2])
            # print 'heading_err_cross', heading_err_cross

            # TODO: clean up all these magic numbers

            # TODO: replace with real controller

            if self.arrived or (np.linalg.norm( pos_delta ) < .08 and np.fabs(helper.diffrad(robot_yaw, self.target_pose2d[2]))<0.05) :
                print 'Case 2.1  Stop'
                wv.desiredWV_R = 0  
                wv.desiredWV_L = 0
                self.arrived = True
            elif np.linalg.norm( pos_delta ) < .08:
                self.arrived_position = True
                if helper.diffrad(robot_yaw, self.target_pose2d[2]) > 0:
                    print 'Case 2.2.1  Turn right slowly'      
                    wv.desiredWV_R = -0.05 
                    wv.desiredWV_L = 0.05
                else:
                    print 'Case 2.2.2  Turn left slowly'
                    wv.desiredWV_R = 0.05  
                    wv.desiredWV_L = -0.05
                    
            elif self.arrived_position or np.fabs( heading_err_cross ) < 0.2:
                print 'Case 2.3  Straight forward'  
                wv.desiredWV_R = 0.1
                wv.desiredWV_L = 0.1
            else:
                if heading_err_cross < 0:
                    print 'Case 2.4.1  Turn right'
                    wv.desiredWV_R = -0.1
                    wv.desiredWV_L = 0.1
                else:
                    print 'Case 2.4.2  Turn left'
                    wv.desiredWV_R = 0.1
                    wv.desiredWV_L = -0.1
                    
            self.velcmd_pub.publish(wv)  
            
            rospy.sleep(.01)
