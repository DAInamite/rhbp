import tensorflow as tf
import numpy

from rhbp_core.msg import SensorValue


class SensorValueTransformer:
    """
    this class is for extracting the sensor values from the conditions and creating a SensorValue message
    """
    def __init__(self):
        self.conditions={}

    def get_value_of_condition(self,cond):
        """
        gets the sensor values of a given condition 
        :param cond: the condition
        :return: SensorValue: a object containing necessary parameter from the sensor
        """
        value = None
        try:
            value = float(cond._sensor.value)
            sensor_value = SensorValue()
            sensor_value.name = cond._sensor._name
            sensor_value.value = value
            sensor_value.encoding = cond._sensor.rl_extension.encoding
            sensor_value.state_space = cond._sensor.rl_extension.state_space
            sensor_value.include_in_rl = cond._sensor.rl_extension.include_in_rl
            return sensor_value
        except Exception as e:
            value = None
        try:

            value = float(cond._condition._sensor.value)
            sensor_value = SensorValue()
            sensor_value.name = cond._condition._sensor._name
            sensor_value.value = value
            sensor_value.encoding = cond._condition._sensor.rl_extension.encoding
            sensor_value.state_space = cond._condition._sensor.rl_extension.state_space
            sensor_value.include_in_rl = cond._condition._sensor.rl_extension.include_in_rl
            return sensor_value
        except Exception :
            value = None
        try:
            list = []
            for c in cond._conditions:
                value = self.get_value_of_condition(c)
                if value is not None:
                    list.append(self.get_value_of_condition(c))
            return list
        except Exception :
            value = None
        return None

    def get_values_of_list(self,full_list):
        """
        gets all values in list. the list can contain multiple lists
        :param full_list: 
        :return: 
        """

        new_list = []
        for ele in full_list:
            if isinstance(ele, (list,)):
                new_list.extend( self.get_values_of_list(ele))
            else:
                new_list.append(ele)
        return new_list

    def get_sensor_values(self,conditions):
        """
        gets the sensor values of a list containing multiple conditions
        :param conditions: list of conditions
        :return: list of sensorvalues
        """
        list_of_sensor_values = []
        for p in conditions:
            value = self.get_value_of_condition(p)
            if isinstance(value,(list,)):
                list_of_sensor_values.extend(self.get_values_of_list(value))

            else:
                if(value is not None):
                    list_of_sensor_values.append(value)
        return list_of_sensor_values


class InputStateTransformer:
    """
    this class gets called in the activation algorithm and transform the rhbp components into the InputStateMessage
    """
    def __init__(self,manager):
        self._manager = manager

    def calculate_reward(self):
        """
        this function calculates regarding the fulfillment and priorities of the active goals
        a reward value. 
        :return: 
        """
        # TODO think about better logic maybe
        # todo use wishes instead of fulfillment
        reward_value = 0
        for goal in self._manager.activeGoals:
            goal_value = goal.fulfillment * goal.priority
            reward_value += goal_value

        return reward_value

    def behaviour_to_index(self,name):
        """
        gives for a given name of a behavior name the index in the behavior list
        :param name: 
        :return: 
        """
        num = 0
        for b in self._manager.behaviours:
            if b == name:
                return num
            num += 1
        return None

    def make_hot_state_encoding(self,state,num_state_space):
        """
        encodes the variables into a hot state format.
        :param state: 
        :param num_state_space: 
        :return: 
        """
        state = int(state)
        return numpy.identity(num_state_space)[state:state + 1].reshape([num_state_space,1])

    def transform_input_values(self):
        """
        this function uses the wishes and sensors to create the input vectors
        :return: input vector
        """
        # todo let config decide if wish or true vlaues included
        use_wishes = False
        use_true_value = True
        # init input array with first row of zeros
        input_array = numpy.zeros([1,1])
        # extend array with input vector from wishes
        for behaviour in self._manager.behaviours:
            # check for each sensor in the goal wishes for behaviours that have sensor effect correlations
            for wish in behaviour.wishes:
                if use_wishes:
                    wish_row = numpy.array([wish.indicator]).reshape([1,1])
                    input_array = numpy.concatenate([input_array,wish_row])
        sensor_input = {}
        # get sensor values from conditions via the behaviours
        for behaviour in self._manager.behaviours:
            for sensor_value in behaviour.sensor_values:
                if not sensor_input.has_key(sensor_value.name) and use_true_value:
                    # encode or ignore the value regarding configuraiton in RLExtension
                    if not sensor_value.include_in_rl:
                        continue
                    if sensor_value.encoding=="hot_state":
                        value = self.make_hot_state_encoding(sensor_value.value,sensor_value.state_space)
                    else:
                        value = numpy.array([[sensor_value.value]])
                    sensor_input[sensor_value.name] = value
                    input_array = numpy.concatenate([input_array, value])

        # get sensors from goals
        for goal in self._manager._goals:
            for sensor_value in goal.sensor_values:
                if not sensor_input.has_key(sensor_value.name) and use_true_value:
                    # encode or ignore the value regarding configuraiton in RLExtension
                    if not sensor_value.include_in_rl:
                        continue
                    if sensor_value.encoding=="hot_state":
                        value = self.make_hot_state_encoding(sensor_value.value,sensor_value.state_space)
                    else:
                        value = numpy.array([[sensor_value.value]])
                    sensor_input[sensor_value.name] = value
                    input_array = numpy.concatenate([input_array, value])
            for wish in goal.wishes:
                if use_wishes:
                    wish_row = numpy.array([wish.indicator]).reshape([1,1])
                    input_array = numpy.concatenate([input_array,wish_row])
        # cut first dummy line
        input_array = input_array[1:]

        return input_array
