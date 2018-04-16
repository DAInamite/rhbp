#!/usr/bin/env python2
# this is the main file of a rhbp agent instance
# it contains the agents variables, topics subscriber and publisher, as well as the regarding callback function
# Although the job_execution process is start in this file
from __future__ import division # force floating point division when using plain /
from agent_modules_tests import *
from behaviour_components.activators import BooleanActivator, StringActivator, ThresholdActivator, GreedyActivator, \
    LinearActivator, EqualActivator
from behaviour_components.condition_elements import Effect
from behaviour_components.conditions import Negation, Condition, MultiSensorCondition, Disjunction
from behaviour_components.sensors import *
from behaviour_components.goals import OfflineGoal,GoalBase
from reinforcement_component.rl_component_tests.test_suite.rhbp_agent_base import RhbpAgentBase
from rcs_ros_bridge.msg import SimStart,  GenericAction,PlayMode, Goals,Flags,Lines

import rospy

from reinforcement_component.rl_component_tests.test_suite.test_environment import BehaviorShell, TestFrozenLakeEnv, \
    RewardSensor


class FrozenLakeAgentManager(RhbpAgentBase):
    def __init__(self):
        super(FrozenLakeAgentManager, self).__init__()
        rospy.logdebug("RhbpAgent::init")

    def start_simulation(self):
        self.init_behaviors()
        self.env.seed(0)
        state = self.env.reset()
        self.state_sensor.update(state)
        #self.manager.step()
        print("init env in state",state)
        self.test_env.start_simulation()

    def init_behaviors(self):
        """
        here we could also evaluate the msg_old in order to initialize depending on the role etc.
        :param msg:  the message
        :type msg: SimStart
        """
        self.environment_name = 'FrozenLake-v0'
        #self.environment_name = 'Taxi-v2'
        self.init_environment(self.environment_name)



        self.state_sensor = Sensor(name="StateSensor")
        #self.state_sensor.update(0)

        reward_sensor = RewardSensor(name="RewardSensor")
        reward_sensor.rl_extension = RlExtension(include_in_rl=False)

        reward_sensor.update(0)

        sensor_list = [self.state_sensor,reward_sensor]
        #self.state_sensor2 = Sensor(name="StateSensor2")
        #self.state_sensor2.update(4)
        action_zero_behavior = BehaviorShell(plannerPrefix=self.prefix,name="ActionZero",index=0)

        action_one_behavior = BehaviorShell(plannerPrefix=self.prefix, name="ActionOne", index=1)

        action_two_behavior = BehaviorShell(plannerPrefix=self.prefix, name="ActionTwo", index=2)

        action_three_behavior = BehaviorShell(plannerPrefix=self.prefix, name="ActionThree", index=3)


        is_in_goal_state = Condition(self.state_sensor, ThresholdActivator(thresholdValue=15))
        is_in_good_state = Condition(reward_sensor,
                                     ThresholdActivator(thresholdValue=1))
        is_in_bad_state = Condition(reward_sensor,ThresholdActivator(thresholdValue=-1,isMinimum=False))
        #start_state_cond = Condition(self.state_sensor, EqualActivator(desiredValue=0))

        #hole_1 = Condition(self.state_sensor, EqualActivator(desiredValue=5))
        #hole_2 = Condition(self.state_sensor, EqualActivator(desiredValue=7))
        #hole_3 = Condition(self.state_sensor, EqualActivator(desiredValue=11))
        #hole_4 = Condition(self.state_sensor, EqualActivator(desiredValue=12))
        #is_in_hole = Disjunction(hole_1,hole_2,hole_3,hole_4)
        #is_in_goal_state2 = Condition(self.state_sensor2, BooleanActivator(desiredValue=14))
        #action_four_behavior.addPrecondition(is_in_goal_state2)

        the_goal = GoalBase(name="goal_the", permanent=True,
                                          conditions=[is_in_goal_state], priority=0,
                                          plannerPrefix=self.prefix)

        the_goal2 = GoalBase(name="goal_bad", permanent=True,
                            conditions=[is_in_bad_state], priority=-1,
                            plannerPrefix=self.prefix)
        the_goal3 = GoalBase(name="goal_good", permanent=True,
                             conditions=[is_in_good_state], priority=1,
                             plannerPrefix=self.prefix)
        #no_hole = GoalBase(name="no_hole_goal", permanent=True,
        #                    conditions=[Negation(start_state_cond)], priority=1,
        #                    plannerPrefix=self.prefix)
        direct_to_goal_effect = Effect(sensor_name=is_in_goal_state.getFunctionNames()[0], indicator=1.0,
                               sensor_type=float)#

        action_two_behavior.correlations.append(direct_to_goal_effect)
        action_one_behavior.correlations.append(direct_to_goal_effect)
        action_three_behavior.correlations.append(direct_to_goal_effect)
        action_zero_behavior.correlations.append(direct_to_goal_effect)

        direct_to_goal_effect2 = Effect(sensor_name=is_in_bad_state.getFunctionNames()[0], indicator=-1.0,
                                       sensor_type=float)  #

        action_two_behavior.correlations.append(direct_to_goal_effect2)
        action_one_behavior.correlations.append(direct_to_goal_effect2)
        action_three_behavior.correlations.append(direct_to_goal_effect2)
        action_zero_behavior.correlations.append(direct_to_goal_effect2 )

        direct_to_goal_effect3 = Effect(sensor_name=is_in_good_state.getFunctionNames()[0], indicator=1.0,
                                        sensor_type=float)  #

        action_two_behavior.correlations.append(direct_to_goal_effect3)
        action_one_behavior.correlations.append(direct_to_goal_effect3)
        action_three_behavior.correlations.append(direct_to_goal_effect3)
        action_zero_behavior.correlations.append(direct_to_goal_effect3)

        self.test_env = TestFrozenLakeEnv(self.env,self.manager,sensor_list)

