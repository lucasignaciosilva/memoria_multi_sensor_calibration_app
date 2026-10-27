#include <ros/ros.h>
#include <std_msgs/String.h>

int main(int argc, char **argv)
{
  ros::init(argc, argv, "calibrator_gui_node");
  ros::NodeHandle nh;

  ROS_INFO("Calibrator GUI Node Started");

  ros::spin();

  return 0;
}
