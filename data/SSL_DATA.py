from __future__ import absolute_import
from __future__ import division 
from __future__ import print_function

import numpy as np
import tensorflow as tf
from tensorflow.contrib.tensorboard.plugins import projector
import pdb

""" Generate a data structure to support SSL models. Expects:
x - np array: N rows, d columns
y - np array: N rows, k columns (one-hot encoding)
"""


class SSL_DATA:
    """ Class for appropriate data structures """
    def __init__(self, x, y, x_test=None, y_test=None, train_proportion=0.7, labeled_proportion=0.3, dataset='moons'):
	
	self.INPUT_DIM = x.shape[1]
	self.NUM_CLASSES = y.shape[1]
	self.NAME = dataset
	
        if x_test is None:
	    self.TRAIN_SIZE = int(np.round(train_proportion * self.N))
	    self.TEST_SIZE = int(self.N-self.TRAIN_SIZE)
	else:
	    self.TRAIN_SIZE = x.shape[0]
	    self.TEST_SIZE = x_test.shape[0]

        self.N = self.TRAIN_SIZE + self.TEST_SIZE
	self.NUM_LABELED = int(np.round(labeled_proportion * self.TRAIN_SIZE))
	self.NUM_UNLABELED = int(self.TRAIN_SIZE - self.NUM_LABELED)

	# create necessary data splits
    	if x_test is None:
	    xtrain, ytrain, xtest, ytest = self._split_data(x,y)
	else:
	    xtrain, ytrain, xtest, ytest = x, y, x_test, y_test
	x_labeled, y_labeled, x_unlabeled, y_unlabeled = self._create_semisupervised(xtrain, ytrain)

	# create appropriate data dictionaries
	self.data = {}
	self.data['x_train'], self.data['y_train'] = xtrain, ytrain
	self.data['x_u'], self.data['y_u'] = x_unlabeled, y_unlabeled
	self.data['x_l'], self.data['y_l'] = x_labeled, y_labeled
	self.data['x_test'], self.data['y_test'] = xtest, ytest

	# counters and indices for minibatching
	self._start_labeled, self._start_unlabeled = 0, 0
	self._epochs_labeled = 0
	self._epochs_unlabeled = 0
        self._start_regular = 0
        self._epochs_regular = 0

	#self.next_batch()

    def _split_data(self, x, y):
	""" split the data according to the proportions """
	indices = range(self.N)
	np.random.shuffle(indices)
	train_idx, test_idx = indices[:self.TRAIN_SIZE], indices[self.TRAIN_SIZE:]
	return (x[train_idx,:], y[train_idx,:], x[test_idx,:], y[test_idx,:])

    def _create_semisupervised(self, x, y):
	""" split training data into labeled and unlabeled """
	indices = range(self.TRAIN_SIZE)
	np.random.shuffle(indices)
	l_idx, u_idx = indices[:self.NUM_LABELED], indices[self.NUM_LABELED:]
	return (x[l_idx,:], y[l_idx,:], x[u_idx,:], y[u_idx,:])


    def next_batch(self, LABELED_BATCHSIZE, UNLABELED_BATCHSIZE):
	x_l_batch, y_l_batch = self.next_batch_labeled(LABELED_BATCHSIZE)
    	x_u_batch, y_u_batch = self.next_batch_unlabeled(UNLABELED_BATCHSIZE)
    	return (x_l_batch, y_l_batch, x_u_batch, y_u_batch)


    def next_batch_labeled(self, batch_size, shuffle=True):
    	"""Return the next `batch_size` examples from this data set."""
        start = self._start_labeled
    	# Shuffle for the first epoch
    	if self._epochs_labeled == 0 and start == 0 and shuffle:
      	    perm0 = np.arange(self.NUM_LABELED)
	    np.random.shuffle(perm0)			
      	    self.data['x_l'], self.data['y_l'] = self.data['x_l'][perm0,:], self.data['y_l'][perm0,:]
   	# Go to the next epoch
    	if start + batch_size > self.NUM_LABELED:
      	    # Finished epoch
      	    self._epochs_labeled += 1
      	    # Get the rest examples in this epoch
      	    rest_num_examples = self.NUM_LABELED - start
      	    inputs_rest_part = self.data['x_l'][start:self.NUM_LABELED]
      	    labels_rest_part = self.data['y_l'][start:self.NUM_LABELED]
      	    # Shuffle the data
      	    if shuffle:
                perm = np.arange(self.NUM_LABELED)
	        np.random.shuffle(perm)
        	self.data['x_l'] = self.data['x_l'][perm]
        	self.data['y_l'] = self.data['y_l'][perm]
      	    # Start next epoch
      	    start = 0
      	    self._start_labeled = batch_size - rest_num_examples
      	    end = self._start_labeled
      	    inputs_new_part = self.data['x_l'][start:end]
      	    labels_new_part = self.data['y_l'][start:end]
      	    return np.concatenate((inputs_rest_part, inputs_new_part), axis=0) , np.concatenate((labels_rest_part, labels_new_part), axis=0)
    	else:
      	    self._start_labeled += batch_size
      	    end = self._start_labeled
	    return self.data['x_l'][start:end], self.data['y_l'][start:end]

	

    def next_batch_unlabeled(self, batch_size, shuffle=True):
    	"""Return the next `batch_size` examples from this data set."""
        start = self._start_unlabeled
    	# Shuffle for the first epoch
    	if self._epochs_unlabeled == 0 and start == 0 and shuffle:
      	    perm0 = np.arange(self.NUM_UNLABELED)
	    np.random.shuffle(perm0)
      	    self.data['x_u'], self.data['y_u'] = self.data['x_u'][perm0,:], self.data['y_u'][perm0,:]
   	# Go to the next epoch
    	if start + batch_size > self.NUM_UNLABELED:
      	    # Finished epoch
      	    self._epochs_unlabeled += 1
      	    # Get the rest examples in this epoch
      	    rest_num_examples = self.NUM_UNLABELED - start
      	    inputs_rest_part = self.data['x_u'][start:self.NUM_UNLABELED,:]
      	    labels_rest_part = self.data['y_u'][start:self.NUM_UNLABELED,:]
      	    # Shuffle the data
      	    if shuffle:
        	perm = np.arange(self.NUM_UNLABELED)
		np.random.shuffle(perm)
        	self.data['x_u'] = self.data['x_u'][perm]
        	self.data['y_u'] = self.data['y_u'][perm]
      	    # Start next epoch
      	    start = 0
      	    self._start_unlabeled = batch_size - rest_num_examples
      	    end = self._start_unlabeled
      	    inputs_new_part = self.data['x_u'][start:end,:]
      	    labels_new_part = self.data['y_u'][start:end,:]
      	    return np.concatenate((inputs_rest_part, inputs_new_part), axis=0) , np.concatenate((labels_rest_part, labels_new_part), axis=0)
    	else:
      	    self._start_unlabeled += batch_size
      	    end = self._start_unlabeled
	    return self.data['x_u'][start:end,:], self.data['y_u'][start:end,:]


    def next_batch_regular(self, batch_size, shuffle=True):
    	"""Return the next `batch_size` examples from this data set."""
        start = self._start_regular
    	# Shuffle for the first epoch
    	if self._epochs_regular == 0 and start == 0 and shuffle:
      	    perm0 = np.arange(self.TRAIN_SIZE)
	    np.random.shuffle(perm0)
      	    self.data['x_train'], self.data['y_train'] = self.data['x_train'][perm0,:], self.data['y_train'][perm0,:]
   	# Go to the next epoch
    	if start + batch_size > self.TRAIN_SIZE:
      	    # Finished epoch
      	    self._epochs_regular += 1
      	    # Get the rest examples in this epoch
      	    rest_num_examples = self.TRAIN_SIZE - start
      	    inputs_rest_part = self.data['x_train'][start:self.TRAIN_SIZE,:]
      	    labels_rest_part = self.data['y_train'][start:self.TRAIN_SIZE,:]
      	    # Shuffle the data
      	    if shuffle:
        	perm = np.arange(self.TRAIN_SIZE)
		np.random.shuffle(perm)
        	self.data['x_train'] = self.data['x_train'][perm]
        	self.data['y_train'] = self.data['y_train'][perm]
      	    # Start next epoch
      	    start = 0
      	    self._start_regular = batch_size - rest_num_examples
      	    end = self._start_regular
      	    inputs_new_part = self.data['x_train'][start:end,:]
      	    labels_new_part = self.data['y_train'][start:end,:]
      	    return np.concatenate((inputs_rest_part, inputs_new_part), axis=0) , np.concatenate((labels_rest_part, labels_new_part), axis=0)
    	else:
      	    self._start_regular += batch_size
      	    end = self._start_regular
	    return self.data['x_train'][start:end,:], self.data['y_train'][start:end,:]


