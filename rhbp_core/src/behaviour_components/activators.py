## The Activators module
#Created on 22.04.2015
#@author: wypler, hrabia

from __future__ import division # force floating point division when using plain /
from util import PDDL
import rospy

import conditions
  
class Activator(conditions.Conditonal):
    '''
    This is the abstract base class for an activator which reacts to a value according to the activation scheme implemented in it
    '''    
    _instanceCounter = 0 # static _instanceCounter to get distinguishable names

    def __init__(self, sensors, minActivation = 0, maxActivation = 1, name = None):
        '''
        Constructor
        '''
        super(Activator, self).__init__()
        self._name = name if name else "Activator {0}".format(Activator._instanceCounter)
        self._sensors = sensors
        self._minActivation = float(minActivation)
        self._maxActivation = float(maxActivation)
        self._satisfaction = 0
        self._normalizedSensorValues = {} # dict of sensors, value pairs
        
    @property
    def minActivation(self):
        return self._minActivation

    @minActivation.setter
    def minActivation(self, minActivationLevel):
        self._minActivation = float(minActivationLevel)
    
    @property
    def maxActivation(self):
        return self._maxActivation

    @maxActivation.setter
    def maxActivation(self, maxActivationLevel):
        self._maxActivation = float(maxActivationLevel)  
        
    def updateComputation(self):
        #caching of different calculations
        self._satisfaction = self._computeActivation()
        
        for s in self._sensors:
            self._normalizedSensorValues[s] = self._getNormalizedSensorValue(s)
    
    def _computeActivation(self):
        '''
        This method should return an activation level.
        The actual implementation obviously depends on the type of activation so that there is no useful default here.
        '''
        raise NotImplementedError()
    
    def _getDirection(self):
        '''
        This method should return the direction that increases activation. +1 means rising, -1 means falling
        '''
        raise NotImplementedError()
    
    def getWishes(self):
        '''
        returns a list of wishes (a wish is a tuple (sensor, indicator <float> [-1, 1]).
        Well, there is only one wish from one sensor - activator pair here but to keep a uniform interface with conjunction and disjunction this method wraps them into a list.
        '''
        try:
            return [(self._sensors, self._getSensorWish(self._sensors[0]))] #TODO FIX  this hack
        except AssertionError:
            rospy.logwarn("Wrong data type for %s in %s. Got %s. Possibly uninitialized%s sensor %s?", self._sensors, self._name, type(self._sensors.value), " optional" if self._sensors.optional else "", self._sensors.name)
            raise
    
    def getPreconditionPDDL(self):
        return self._getSensorPreconditionPDDL(self._sensors[0]) #TODO FIX  this hack
    
    def getStatePDDL(self):
        return [self._getSensorStatePDDL(self._sensors[0])]#TODO FIX  this hack
    
    def _getSensorWish(self, sensor):
        '''
        This method should return an indicator (float in range [-1, 1]) how much and in what direction the value should change in order to reach more activation.
        1 means the value should become true or increase, 0 it should stay the same and -1 it should decrease or become false.
        '''
        raise NotImplementedError()
    
    def _getSensorPreconditionPDDL(self, sensor):
        '''
        This method should produce valid PDDL condition expressions suitable for FastDownward (http://www.fast-downward.org/PddlSupport)
        '''
        raise NotImplementedError()
    
    def _getSensorStatePDDL(self, sensor):
        '''
        This method should produce a valid PDDL statement describing the current state (the (normalized) value) of sensor sensorName in a form suitable for FastDownward (http://www.fast-downward.org/PddlSupport)
        '''
        raise NotImplementedError()
    
    def _getNormalizedSensorValue(self, sensor):
        '''
        This method should return either 
                                        a float which represents the sensor reading in a single-dimensional fashion for use as numeric fluent by the symbolic planner
                                  or
                                        a Bool if the sensor represents a predicate and not a numeric fluent.
        '''
        return sensor.value
    
    @property
    def satisfaction(self):
        '''
        This property specifies to what extend the condition is fulfilled.
        '''
        try:
            return self._satisfaction
        except AssertionError:
            rospy.logwarn("Wrong data type for %s in %s. Got %s. Possibly uninitialized%s sensor %s?", self._sensors, self._name, type(self._sensors.value), " optional" if self._sensors.optional else "", self._sensors.name)
            raise
    
    @property
    def sensor(self):
        return self._sensors
    
    @property
    def optional(self):
        return self._sensors.optional
        
    def __str__(self):
        return "{0} {{{1} : v: {2}, s: {3}}}".format(self._name, self._sensors, self._sensors.value, self.satisfaction)
    
    def __repr__(self):
        return str(self)
    

class BooleanActivator(Activator):
    '''
    This class is an activator that compares a boolean value to a desired value
    '''
    
    def __init__(self, sensor, desiredValue = True, minActivation = 0, maxActivation = 1, name = None):
        '''
        Constructor
        '''
        super(BooleanActivator, self).__init__(sensor, minActivation, maxActivation, name)
        self._desired = desiredValue   # this is the threshold Value
    
    def _computeActivation(self):
        value = self._normalizedSensorValues[self._sensors[0]] #TODO support multiple sensors
        assert isinstance(value, bool)
        return self._maxActivation if value == self._desired else self._minActivation
    
    def _getDirection(self):
        return 1 if self._desired == True else -1
    
    def _getSensorWish(self, sensor):
        value = self._normalizedSensorValues[sensor]
        assert isinstance(value, bool)
        if value == self._desired:
            return 0.0
        if self._desired == True:
            return 1.0
        return -1.0
    
    def _getSensorPreconditionPDDL(self, sensor):
        return PDDL(statement = "(" + sensor.name + ")" if self._desired == True else "(not (" + sensor.name + "))", predicates = sensor.name)
    
    def _getSensorStatePDDL(self, sensor):
        value = self._normalizedSensorValues[sensor]
        return PDDL(statement = "(" + sensor.name + ")" if value == True else "(not (" + sensor.name + "))", predicates = sensor.name)
        
    def __str__(self):
        return "Boolean Activator [{0} - {1}] ({2})".format(self._minActivation, self._maxActivation, self._desired)
    
    def __repr__(self):
        return "Boolean Activator"
    

class ThresholdActivator(Activator):
    '''
    This class is an activator that compares a sensor's value (expected to be int or float) to a threshold.
    '''
    def __init__(self, sensor, thresholdValue, isMinimum = True, valueRange = None, minActivation = 0, maxActivation = 1, name = None):
        '''
        Constructor
        '''
        super(ThresholdActivator, self).__init__(sensor, minActivation, maxActivation, name)
        self._threshold = float(thresholdValue)   # This is the threshold Value
        self._isMinimum = isMinimum               # The direction in which the threshold must be crossed in order to be activated
        self._valueRange = valueRange             # This is used to assess value deviation. When the range is known it can be estimated how much a given value differs from a satisfactory one (assumed linear relation)
        
    @property
    def threshold(self):
        return self._threshold
    
    @threshold.setter
    def threshold(self, thresholdValue):
        assert isinstance(thresholdValue, int) or isinstance(thresholdValue, float)
        self._threshold = float(thresholdValue);
    
    @property
    def minimum(self):
        return self._isMinimum
    
    @minimum.setter
    def minimum(self, mini):
        assert isinstance(mini, bool)
        self._isMinimum = mini
    
    @property
    def valueRange(self):
        return self._valueRange
    
    @valueRange.setter
    def valueRange(self, valueRange):
        assert isinstance(valueRange, int) or isinstance(valueRange, float)
        self._valueRange = valueRange
    
    def _computeActivation(self):
        value = self._normalizedSensorValues[self._sensors[0]]#TODO support multiple sensors
        assert isinstance(value, int) or isinstance(value, float)
        if self._isMinimum:
            return self._maxActivation if value >= self._threshold else self._minActivation
        else:
            return self._maxActivation if value <= self._threshold else self._minActivation
    
    def _getDirection(self):
        return 1 if self._isMinimum else -1

    def _getSensorWish(self, sensor):
        value = self._normalizedSensorValues[sensor]
        assert isinstance(value, int) or isinstance(value, float)
        if self._satisfaction == self._maxActivation: # no change is required
            return 0.0
        if self._valueRange:
            return sorted((-1.0, (self._threshold - value) / self._valueRange, 1.0))[1] # return how much is missing clamped to [-1, 1]
        else:
            return float(self._getDirection())
    
    def _getSensorPreconditionPDDL(self, sensor):
        sensorName = self._sensors.name
        return PDDL(statement = "( >= (" + sensor.name + ") {0} )".format(self._threshold) if self._getDirection() == 1 else "( <= (" + sensor.name + ") {0} )".format(self._threshold), functions = sensor.name)
    
    def _getSensorStatePDDL(self, sensor):
        value = self._normalizedSensorValues[sensor]
        return PDDL(statement = "( = (" + sensorName + ") {0} )".format(value), functions = sensor.name)
    
    def __str__(self):
        return "Threshold Activator [{0} - {1}] ({2} or {3})".format(self._minActivation, self._maxActivation, self._threshold, "above" if self._isMinimum else "below")
    
    def __repr__(self):
        return "Threshold Activator"

class LinearActivator(Activator):
    '''
    This class is an activator that takes a value (expected to be int or float) and computes a linear slope of activation within a value range.
    '''
    def __init__(self, sensor, zeroActivationValue, fullActivationValue, minActivation = 0, maxActivation = 1, name = None):
        '''
        Constructor
        '''
        super(LinearActivator, self).__init__(sensor, minActivation, maxActivation, name)
        self._zeroActivationValue = float(zeroActivationValue) # Activation raises linearly between this value and _fullActivationValue (it remains 0 until here))
        self._fullActivationValue = float(fullActivationValue) # This value (and other values further away from _threshold in this direction) means total activation
    
    def _computeActivation(self):
        value = self._normalizedSensorValues[self._sensors[0]]#TODO support multiple sensors
        assert isinstance(value, int) or isinstance(value, float)
        assert self.valueRange != 0
        rawActivation = (value - self._zeroActivationValue) / self.valueRange
        return sorted((self._minActivation, rawActivation * self.activationRange + self._minActivation, self._maxActivation))[1] # clamp to activation range
    
    def _getDirection(self):
        return 1 if self._fullActivationValue > self._zeroActivationValue else -1
    
    def _getSensorWish(self, sensor):
        value = self._normalizedSensorValues[sensor]
        assert isinstance(value, int) or isinstance(value, float)
        assert self.valueRange != 0
        if self._getDirection() > 0:
            return sorted((0.0, (self._fullActivationValue - value) / abs(self.valueRange), 1.0))[1] # return how much is missing clamped to [0, 1]
        else:
            return sorted((-1.0, (self._fullActivationValue - value) / abs(self.valueRange), 0.0))[1] # return how much is there more than desired clamped to [-1, 0]
        
    def _getSensorPreconditionPDDL(self, sensor):
        return PDDL(statement = "( >= (" + sensor.name + ") {0} )".format(self._zeroActivationValue) if self._getDirection() == 1 else "( <= (" + sensor.name + ") {0} )".format(self._zeroActivationValue), functions = sensor.name)  # TODO: This is not actually correct: The lower bound is actually not satisfying. How can we do better?
    
    def _getSensorStatePDDL(self, sensor):
        self._normalizedSensorValues[sensor]
        return PDDL(statement = "( = (" + sensor.name + ") {0} )".format(value), functions = sensor.name)
                
    @property
    def valueRange(self):
        return self._fullActivationValue - self._zeroActivationValue
    
    @property
    def activationRange(self):
        return self._maxActivation - self._minActivation
    
    @property
    def zeroActivationValue(self):
        return self._zeroActivationValue
    
    @zeroActivationValue.setter
    def zeroActivationValue(self, value):
        assert isinstance(value, int) or isinstance(value, float)
        self._zeroActivationValue = float(value);
    
    @property
    def fullActivationValue(self):
        return self._fullActivationValue
    
    @fullActivationValue.setter
    def fullActivationValue(self, value):
        assert isinstance(value, int) or isinstance(value, float)
        self._fullActivationValue = float(value);
    
    def __str__(self):
        return "Linear Activator [{0} - {1}] ({2} - {3})".format(self._minActivation, self._maxActivation, self._zeroActivationValue, self._fullActivationValue)
    
    def __repr__(self):
        return "Linear Activator"