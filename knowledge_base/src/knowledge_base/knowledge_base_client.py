"""
Created on 09.03.2017

@author: rieger
"""

from threading import Lock

import rospy
from knowledge_base.knowledge_base_manager import KnowledgeBase
from knowledge_base.msg import Push
from knowledge_base.srv import Exists, Peek, Pop, All, Update, UpdateSubscribe


class KnowledgeBaseClient(object):
    """
    Simple wrapper for the services (and the push topic) of the knowledge base.
    Some methods do some value conversion, for better usability.
    IMPORTANT: The service proxies are created once, but the initialization is lazy:
    The init method waits 10 secconds for the knowledge base.
    After the timeout the constructor returns and the initialisation is done during first usage of this client
    (without timeout).
    """

    def __init__(self, knowledge_base_name=KnowledgeBase.DEFAULT_NAME):
        """
        :param knowledge_base_name: Name of the knowledge base (without any postfix)
        """
        self.__initialized = False
        self.__knowledge_base_name = knowledge_base_name
        self.__init_lock = Lock
        try:
            rospy.wait_for_service(knowledge_base_name + KnowledgeBase.EXISTS_SERVICE_NAME_POSTFIX, timeout=10)
            self.__initialize()
        except rospy.ROSException:
            rospy.loginfo(
                'The following knowledge base node is currently not present. Connection will be established later: ' + knowledge_base_name)

    def __ensure_initialization(self):
        if self.__initialized:
            return
        self.__init_lock.acquire()

        if (self.__initialized):
            # Another check, protected by the lock
            return

        try:
            rospy.logerr(
                'Wait for knowledge base: ' + self.__knowledge_base_name + KnowledgeBase.EXISTS_SERVICE_NAME_POSTFIX)
            rospy.wait_for_service(self.__knowledge_base_name + KnowledgeBase.EXISTS_SERVICE_NAME_POSTFIX)
            self.__initialize()
        finally:
            self.__init_lock.release()

    def __initialize(self):
        """
        initialize the client. Assumes, that the knowledge base already exists.
        Not thread safe
        """
        self.__exists_service = rospy.ServiceProxy(
            self.__knowledge_base_name + KnowledgeBase.EXISTS_SERVICE_NAME_POSTFIX, Exists)
        self.__pop_service = rospy.ServiceProxy(self.__knowledge_base_name + KnowledgeBase.POP_SERVICE_NAME_POSTFIX,
                                                Pop)
        self.__peek_service = rospy.ServiceProxy(self.__knowledge_base_name + KnowledgeBase.PEEK_SERVICE_NAME_POSTFIX,
                                                 Peek)
        self.__all_service = rospy.ServiceProxy(self.__knowledge_base_name + KnowledgeBase.ALL_SERVICE_NAME_POSTFIX,
                                                All)
        self.__update_service = rospy.ServiceProxy(
            self.__knowledge_base_name + KnowledgeBase.UPDATE_SERVICE_NAME_POSTFIX, Update)
        self.__update_subscribe_service = rospy.ServiceProxy(
            self.__knowledge_base_name + KnowledgeBase.UPDATE_SUBSCRIBE_SERVICE_NAME_POSTFIX, UpdateSubscribe)
        self.__push_topic = rospy.Publisher(self.__knowledge_base_name + KnowledgeBase.PUSH_TOPIC_NAME_POSTFIX, Push,
                                            queue_size=10, latch=True)
        rospy.sleep(1)
        self.__initialized = True

    def exists(self, pattern):
        """
        Whether a fact, which matches the given pattern exists in the knowledge base
        :param pattern: (array of strings) pattern, use * as placeholder
        :return: (bool) result
        """
        self.__ensure_initialization()
        return self.__exists_service(pattern).exists

    def pop(self, pattern):
        """
        Removes a fact, which matches the pattern from the knowledge base. If not suitable fact exists, nothing happens
        :param pattern:  (array or tuple  of strings) pattern, use * as placeholder
        :return: None, if no matching fact existed, otherwise the removed fact (string tuple)
        """
        self.__ensure_initialization()
        request_result = self.__pop_service(pattern)
        if (request_result.exists):
            return tuple(request_result.removed)
        return None

    def peek(self, pattern):
        """
        :param pattern:  (array or tuple  of strings) pattern, use * as placeholder
        :return: matching fact (string tupple) or none if not matching fact exists
        """
        self.__ensure_initialization()
        request_result = self.__peek_service(pattern)
        if (request_result.exists):
            return tuple(request_result.example)
        return None

    def all(self, pattern):
        """
        :param pattern:  (array or tuple of strings) pattern, use * as placeholder
        :return: all matching facts, as list of string tuples
        """
        self.__ensure_initialization()
        request_result = self.__all_service(pattern)
        result = []
        for fact in request_result.found:
            result.append(tuple(fact.content))
        return result

    def update(self, old, new):
        """
        :param old:  fact, which should replaced. No placeholders are allowed
        :param new: new fact
        :return: whether old fact existed. Otherwise nothing is done
        """
        self.__ensure_initialization()
        return self.__update_service(old, new).successful

    def push(self, fact):
        """
        WARNING: This operation is executed asynchronus
        :param fact: array or tuple  of strings. No placeholders are allowed
        """
        self.__ensure_initialization()
        self.__push_topic.publish(fact)

    def subscribe_for_updates(self, pattern):
        """
        :param pattern:  (array or tuple of strings) pattern, use * as placeholder
        :return: added topic name, updated topic name, removed topic name
        """
        self.__ensure_initialization()
        request_result = self.__update_subscribe_service(pattern)
        return request_result.added_topic_name, request_result.updated_topic_name, request_result.removed_topic_name