from delegation_components.goal_wrappers import GoalWrapperBase
from behaviour_components.goals import GoalBase, rhbplog
from delegation_components.delegation_errors import DelegationError
from rospy.exceptions import ROSException
import rospy


class DecompositionGoal(GoalBase):

    def __init__(self, *args, **kwargs):
        super(DecompositionGoal, self).__init__(*args, **kwargs)
        self._failed_alive_check = False

    def __del__(self):
        """
        Destructor that makes sure waiting is not required if its already known
        that the manager failed
        """

        if self._failed_alive_check:
            # No additional full timeout required
            self.SERVICE_TIMEOUT = 0.01

        super(DecompositionGoal, self).__del__()

    def check_if_alive(self):
        """
        Checks if the manager this goal is registered at is still running

        :return: if the manager is still alive
        :rtype: bool
        """

        if hasattr(self, '_registered') and self._registered:
            service_name = self._planner_prefix + '/' + 'AddGoal'
            try:
                rospy.wait_for_service(service_name, timeout=self.SERVICE_TIMEOUT)
                return True
            except ROSException:
                rhbplog.logwarn("Connection to Manager with prefix \""+str(self._planner_prefix)+"\" was impossible")
                self._failed_alive_check = True
                return False
        else:
            return True


class RHBPGoalWrapper(GoalWrapperBase):
    """
    Class that wraps goals that are used in the RHBP.
    Uses PDDL-based goal representations and sends goals
    by registering them at the corresponding manager.
    """

    def __init__(self, name, conditions, satisfaction_threshold=1.0):
        """
        Constructor

        :param name: name of the goal
        :param conditions: list of conditions of this goals
        :param satisfaction_threshold: satisfaction threshold
                of the goal
        """

        super(RHBPGoalWrapper, self).__init__(name=name)

        self._conditions = conditions
        self._satisfaction_threshold = satisfaction_threshold

    def __del__(self):
        """
        Destructor
        """

        super(RHBPGoalWrapper, self).__del__()
        del self._conditions

    def get_goal_representation(self):
        """
        Returns the representation of the goal in form
        of a PDDL goal-statement

        :return: goal representing PDDL-String
        """

        return " ".join([x.getPreconditionPDDL(self._satisfaction_threshold).statement for x in self._conditions])

    def send_goal(self, name=""):
        """
        Sends the goal to the RHBP-manager with this planner-prefix
        by registering it directly at the manager

        :param name: prefix of the manager, that should
                receive the goal
        :raises DelegationError: if there is any problem with the goal creation
        """
        try:
            self._goal = DecompositionGoal(name=self.goal_name, plannerPrefix=name, conditions=self._conditions, satisfaction_threshold=self._satisfaction_threshold)
            self._created_goal = True
            return
        except Exception as e:
            self._created_goal = False
            self._goal = None
            raise DelegationError("Sending goal raised exception: " + str(e.message))

    def terminate_goal(self):
        """
        Terminates (unregister and deletes) the created goal
        """

        if self.goal_is_created():
            self._created_goal = False
            self._goal.__del__()   # unregisters goal
            self._goal = None

    def check_if_still_alive(self):
        """
        Checks whether this goal is still actively pursued by the contractor, by
        probing the connection to the manager via the goal

        :return: if it is actively pursued
        :rtype: bool
        """

        if self.goal_is_created():
            return self._goal.check_if_alive()
        else:
            return True
