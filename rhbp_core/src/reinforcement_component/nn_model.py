import gym
import numpy as np
import random
import tensorflow as tf
import matplotlib.pyplot as plt
from input_state_transformer import InputStateTransformer

class ModelNeuralNetwork:
    def __init__(self,name):

        # pathes for saving the models
        self.model_path = 'models/rl-model'+name+'-1000.meta'
        self.model_folder = './models'


        #tf.reset_default_graph()

        # input dimensions
        self.input_variables = 16
        self.output_variables = 10

        self.num_hl = 1

        self.hl1_variables = 14

        # Set learning parameters
        self.learning_rate_optimizer = 0.1

        self.epsilon = 0.1
        self.learning_rate_q_learning = 0.99

        # information about current model
        self.num_updates = 0
        self.current_state = None
        self.last_action = None
        self.next_state = None

        # model variables
        self.Qout = None
        self.predict = None
        self.inputs1 = None

        self.nextQ = None
        self.updateModel = None

        self.transformer = None

        self.behaviors = None


    def update_dimensions(self, number_inputs, number_behaviors):

        self.input_variables = number_inputs
        self.output_variables = number_behaviors

    def initialize_model(self):
        print("initialize new model",self.input_variables,self.output_variables)
        # These lines establish the feed-forward part of the network used to choose actions
        self.inputs1 = tf.placeholder(shape=[1,self.input_variables],dtype=tf.float32,name="inputs1")
        W1 = tf.Variable(tf.random_uniform([self.input_variables,self.hl1_variables],0,0.01))
        W2 = tf.Variable(tf.random_uniform([self.hl1_variables,self.output_variables],0,0.01))

        # combine weights with inputs
        layer = tf.matmul(self.inputs1,W1)
        self.Qout = tf.matmul(layer,W2,name="Qout")

        # choose action with highest q-value
        self.predict = tf.argmax(self.Qout,1,name="predict")

        # Below we obtain the loss by taking the sum of squares difference between the target and prediction Q values.
        self.nextQ = tf.placeholder(shape=[1,self.output_variables],dtype=tf.float32,name="nextQ")
        self.loss = tf.reduce_sum(tf.square(self.nextQ - self.Qout),name="loss")
        #loss = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(
        #    logits=Qout, labels=nextQ))
        self.trainer = tf.train.GradientDescentOptimizer(learning_rate=self.learning_rate_optimizer,name="trainer")
        self.updateModel = self.trainer.minimize(self.loss,name="updateModel")

        # initializes all variables so the operations can be executed
        self.init_variables = tf.global_variables_initializer()

        # 'Saver' op to save and restore all the variables
        self.saver = tf.train.Saver()

        # create session to run tf operation on
        self.sess = tf.Session()
        self.sess.run(self.init_variables)

    def check_if_model_exists(self):
        return tf.train.checkpoint_exists(self.model_folder)

    def load_model(self):
        print("load model")
        # restore the session

        self.sess = tf.Session()

        self.saver = tf.train.import_meta_graph(self.model_path)

        self.saver.restore(self.sess, tf.train.latest_checkpoint(self.model_folder))

        # restore the nodes
        graph = tf.get_default_graph()
        self.Qout = graph.get_tensor_by_name("Qout:0")
        self.predict = graph.get_tensor_by_name("predict:0")
        self.inputs1 = graph.get_tensor_by_name("inputs1:0")

        self.nextQ = graph.get_tensor_by_name("nextQ:0")
        self.updateModel = graph.get_tensor_by_name("updateModel:0")

    def init_states(self):
        self.current_state = self.transformer.get_current_state()

    def feed_forward(self):

        self.current_state = self.transformer.get_current_state
        #Choose an action by greedily (with e chance of random action) from the Q-network
        a,self.allQ = self.sess.run([self.predict,self.Qout],feed_dict={self.inputs1:self.current_state})
        # greedy style for exploration
        if np.random.rand(1) < self.epsilon:
            a = self.transformer.get_random_action()
        self.last_action = a
        print(a)
        print(self.behaviors[a])
        return self.allQ

    def train_model(self,new_state):
        # Get new state and reward from environment
        self.next_state = new_state
        reward = self.transformer.get_reward_from_state()

        #Obtain the Q' values by feeding the new state through our network
        Q1 = self.sess.run(self.Qout,feed_dict={self.inputs1:new_state})

        #Obtain maxQ' and set our target value for chosen action.
        maxQ1 = np.max(Q1)
        targetQ = self.allQ

        # q-learning update function for the chosen action
        targetQ[0,self.last_action] = reward + self.y * maxQ1

        # Train our network using target and predicted Q values
        self.sess.run([self.updateModel],feed_dict={self.inputs1:self.current_state,self.nextQ:targetQ})

        # make old state to new state and repeat
        self.current_state = self.new_state

        # Reduce chance of random action as we train the model.
        self.epsilon = 1./((self.num_updates/50) + 10)

        # Save model weights to disk
        self.saver.save(self.sess, self.model_path)
