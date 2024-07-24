#!/usr/bin/python3
import sys
import time

import rosgraph
import rosnode
import rospy
from opcua import Server, ua

import ros_services
import ros_topics


# Returns the hierachy as one string from the first remaining part on.
def nextname(hierachy, index_of_last_processed):
    try:
        output = ""
        counter = index_of_last_processed + 1
        while counter < len(hierachy):
            output += hierachy[counter]
            counter += 1
        return output
    except Exception as e:
        rospy.logerr("Error encountered ", e)


def own_rosnode_cleanup():
    pinged, unpinged = rosnode.rosnode_ping_all()
    if unpinged:
        master = rosgraph.Master(rosnode.ID)
        # noinspection PyTypeChecker
        rosnode.cleanup_master_blacklist(master, unpinged)


class ROSServer:
    def __init__(self):
        self.namespace_ros = "/"
        if rospy.has_param("/rosopcua/namespace"):
            rospy.get_param("/rosopcua/namespace")
        self.excluded_topics = []
        self.excluded_services = []
        self.allowed_topics = []
        self.allowed_services = []
        if rospy.has_param('/rosopcua/allowed_topics'):
            self.allowed_topics = rospy.get_param("/rosopcua/allowed_topics")
            if isinstance(self.allowed_topics, list) and all(isinstance(elem, str) for elem in self.allowed_topics):
                rospy.logwarn("The list of allowed topics are:")
                for elem in self.allowed_topics:
                    rospy.logwarn("-" + elem)
            else:
                self.allowed_topics = []
        if rospy.has_param('/rosopcua/allowed_services'):
            self.allowed_services = rospy.get_param("/rosopcua/allowed_services")
            if isinstance(self.allowed_services, list) and all(isinstance(elem, str) for elem in self.allowed_services):
                rospy.logwarn("The list of allowed services are:")
                for elem in self.allowed_services:
                    rospy.logwarn("-" + elem)
            else:
                self.allowed_services = []
        if rospy.has_param('/rosopcua/excluded_topics'):
            self.excluded_topics = rospy.get_param("/rosopcua/excluded_topics")
            if len(self.allowed_topics)>0:
                rospy.logwarn("A list of topics to connect to has been defined, so no exceptions can be defined.")
                self.excluded_topics = []
            elif isinstance(self.excluded_topics, list) and all(isinstance(elem, str) for elem in self.excluded_topics):
                rospy.logwarn("The list of excluded topics are:")
                for elem in self.excluded_topics:
                    rospy.logwarn("-" + elem)
            else:
                self.excluded_topics = []
                rospy.logerr("The list of excluded topics is not well defined, no topic will be excluded.")
        if rospy.has_param('/rosopcua/excluded_services'):
            self.excluded_services = rospy.get_param("/rosopcua/excluded_services")
            if len(self.allowed_services)>0:
                rospy.logwarn("A list of services to connect to has been defined, so no exceptions can be defined.")
                self.excluded_services = []
            elif isinstance(self.excluded_services, list) and all(isinstance(elem, str) for elem in self.excluded_services):
                rospy.logwarn("The list of excluded services are:")
                for elem in self.excluded_services:
                    rospy.logwarn("-" + elem)
            else:
                self.excluded_services = []
                rospy.logerr("The list of excluded services is not well defined, no service will be excluded.")
        self.topicsDict = {}
        self.servicesDict = {}
        self.actionsDict = {}
        rospy.init_node("rosopcua")
        self.server = Server()
        self.server.set_endpoint("opc.tcp://0.0.0.0:4840/")
        self.server.set_server_name("ROS ua Server")
        self.server.start()
        # setup our own namespaces, this is expected
        uri_topics = "http://ros.org/topics"
        # two different namespaces to make getting the correct node easier for get_node (otherwise had object for service and topic with same name
        uri_services = "http://ros.org/services"
        uri_actions = "http://ros.org/actions"
        idx_topics = self.server.register_namespace(uri_topics)
        idx_services = self.server.register_namespace(uri_services)
        idx_actions = self.server.register_namespace(uri_actions)
        # get Objects node, this is where we should put our custom stuff
        objects = self.server.get_objects_node()
        # one object per type we are watching
        topics_object = objects.add_object(idx_topics, "ROS-Topics")
        services_object = objects.add_object(idx_services, "ROS-Services")
        actions_object = objects.add_object(idx_actions, "ROS_Actions")
        while not rospy.is_shutdown():
            # ros_topics starts a lot of publisher/subscribers, might slow everything down quite a bit.
            ros_services.refresh_services(self.namespace_ros, self, self.servicesDict, idx_services, services_object, 
                                          self.excluded_services, self.allowed_services)
            ros_topics.refresh_topics_and_actions(self.namespace_ros, self, self.topicsDict, self.actionsDict,
                                                  idx_topics, idx_actions, topics_object, actions_object, self.excluded_topics, self.allowed_topics)
            # Don't clog cpu
            time.sleep(60)
        self.server.stop()
        quit()

    def find_service_node_with_same_name(self, name, idx):
        rospy.logdebug("Reached ServiceCheck for name " + name)
        for service in self.servicesDict:
            rospy.logdebug("Found name: " + str(self.servicesDict[service].parent.nodeid.Identifier))
            if self.servicesDict[service].parent.nodeid.Identifier == name:
                rospy.logdebug("Found match for name: " + name)
                return self.servicesDict[service].parent
        return None

    def find_topics_node_with_same_name(self, name, idx):
        rospy.logdebug("Reached TopicCheck for name " + name)
        for topic in self.topicsDict:
            rospy.logdebug("Found name: " + str(self.topicsDict[topic].parent.nodeid.Identifier))
            if self.topicsDict[topic].parent.nodeid.Identifier == name:
                rospy.logdebug("Found match for name: " + name)
                return self.topicsDict[topic].parent
        return None

    def find_action_node_with_same_name(self, name, idx):
        rospy.logdebug("Reached ActionCheck for name " + name)
        for topic in self.actionsDict:
            rospy.logdebug("Found name: " + str(self.actionsDict[topic].parent.nodeid.Identifier))
            if self.actionsDict[topic].parent.nodeid.Identifier == name:
                rospy.logdebug("Found match for name: " + name)
                return self.actionsDict[topic].parent
        return None


def main(args):
    rosserver = ROSServer()


if __name__ == "__main__":
    main(sys.argv)
