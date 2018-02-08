### Author: Devin Whitten
### Date: 1/5/18

### splitting the interfaces for the network class
### and the network array class

import numpy as np
import pandas as pd
import pickle, random
import sklearn.neural_network as sknet
import multiprocessing
import param
import sys, itertools

sys.path.append("/Users/MasterD/Google Drive/JPLUS/Pipeline3.0/Temperature/interface")
import train_fns, net_functions


class Network_Array():
    ### The goal here is to generate an array of networks corresponding to the
    ### combinations of possible network inputs, enables averaging,

    def __init__(self, training_set, interp_frame, target_variable, scale_frame, input_type="both", input_number=6, array_size=50):



        self.training_set = training_set
        self.interp_frame = interp_frame
        self.target_var = target_variable
        self.array_size = array_size
        self.scale_frame = scale_frame
        self.input_type=input_type
        self.input_number = input_number



    def set_input_type(self):

        print("Network input_type:  ", self.input_type)

        if self.input_type == "both":
            self.inputs = param.params['format_bands'] + self.training_set.colors

        elif self.input_type == "magnitudes":
            self.inputs = param.params['format_bands']

        elif self.input_type == "colors":
            self.inputs = self.training_set.colors

        else:
            print("ERROR: Bad network input_type")


        print(self.inputs)

        self.combinations = np.array(list(itertools.combinations(self.inputs, self.input_number)))
        print(len(self.combinations), " of given input type")
        return


    def generate(self, assert_band="ALL"):
        ### Assemble the network array according to self.combinations
        print("... Generating", self.target_var,"network array")
        if assert_band != "ALL":
            for element in assert_band:
                print("... Asserting: ", element)
                self.combinations = self.combinations[[element in ele for ele in self.combinations]]

        ### shuffle combinations
        self.combinations = self.combinations[np.random.permutation(len(self.combinations))]
        print(len(self.combinations), " total input combinations")
        self.network_array = [net_functions.Network(target_variable = self.target_var, inputs=current_permutation, ID = ID) for ID, current_permutation in enumerate(self.combinations[0:self.array_size])]


    def train(self, train_fct=0.65):
        print("train_array...")
        ### Trains array of networks, sets the verification and target set
        ### iterations: number of networks to train

        self.verification_set = self.training_set.custom.iloc[int(len(self.training_set.custom)*train_fct):].copy()
        self.training_set = self.training_set.custom.iloc[0:int(len(self.training_set.custom)*train_fct)].copy()



        [net.train_on(self.training_set, ID) for ID, net in enumerate(self.network_array)]

    def train_test(self, net):
        net[1].train_on(self.training_set, net[0])
        return

    def train_pool(self, train_fct=0.75, iterations=50, core_fraction=0.5):
        ### Let's try to multiprocess the network_array training
        ### I'll come back to this
        print("train_pool")
        core_number = int(core_fraction*multiprocessing.cpu_count())
        ### multiprocessing pool
        pool = multiprocessing.Pool(core_number)
        pool.map(self.train_on, enumerate(self.network_array))
        return

    def info(self):
        print()
        for i in range(len(self.network_array)):
            print("Net:  ", self.network_array[i].get_id(), self.network_array[i].get_inputs())


    def eval_performance(self):
        ### Runs the network array on the verification sets
        ### Sets the median absolute deviation
        [net.compute_residual(verify_set = self.verification_set, scale_frame = self.scale_frame) for net in self.network_array]
        #thing = self.network_array[0].predict(input_frame = self.verification_set)
        #print(self.network_array[2].residual* self.scale_frame[self.target_var].iloc[1])
        print("Setting network mad")
        [net.set_mad(train_fns.MAD(net.residual))     for net in self.network_array]

        print("Setting network low_mad")
        [net.set_low_mad(train_fns.MAD(net.low_residual)) for net in self.network_array]

        self.scores = np.divide(1., np.power(np.array([net.get_mad() for net in self.network_array]),2))

        return

    def prediction(self, target_set):
        print()
        print("running array prediction:  ")
        ### use the 1/MADs determined in eval_performance to perform a weighted average estimate for the
        ### target input
        ## might as well unscale here as well.
        output = np.vstack([train_fns.unscale(net.predict(target_set.custom), *self.scale_frame[self.target_var]) for net in self.network_array]).T

        self.output = output
        #return np.dot(output, np.divide(1.,self.MADs))/np.divide(1., TEFF_net.MADs).sum()
        self.target_err = np.array([np.std(np.array(row)) for row in output])

        self.target_est = (np.dot(output, self.scores)/(self.scores.sum()))

        ######### DONT NEED TO UNSCALE!!!!!!!!!
        target_set.custom.loc[:, "NET_" + self.target_var+"_CHECK"] = self.target_est # train_fns.unscale(self.target_est, *self.scale_frame[self.target_var])
        ######### DONT NEED TO UNSCALE!!!!!!!!!
        target_set.custom.loc[:, "NET_" + self.target_var + "_ERR"] = self.target_err * self.scale_frame[self.target_var].iloc[1]

        return self.target_est, self.target_err

    def predict_all_networks(self, target_set):
        ### Run each network in the array on the target_set
        ### append values with ID to target frame
        print("Running all networks on target set")
        for net in self.network_array:
            target_set.custom.loc[:, "NET_" + str(net.get_id()) + "_FEH"] = train_fns.unscale(net.predict(target_set.custom), *self.scale_frame[self.target_var])

    def write_training_results(self):
        ### Just run prediction on the verification and testing sets

        output = np.matrix([train_fns.unscale(net.predict(self.training_set), *self.scale_frame[self.target_var]) for net in self.network_array]).T
        self.training_set.loc[:, 'NET_' + self.target_var] = (np.dot(output, self.scores)/self.scores.sum()).T
        self.training_set.loc[:, self.target_var] = train_fns.unscale(self.training_set[self.target_var], *self.scale_frame[self.target_var])

        output = np.matrix([train_fns.unscale(net.predict(self.verification_set), *self.scale_frame[self.target_var]) for net in self.network_array]).T
        self.verification_set.loc[:, 'NET_' + self.target_var] = (np.dot(output, self.scores)/self.scores.sum()).T
        self.verification_set.loc[:, self.target_var] = train_fns.unscale(self.verification_set[self.target_var], *self.scale_frame[self.target_var])


        print("... writing training/verification outputs")

        self.training_set.to_csv(param.params['output_directory'] + self.target_var + "_training_results.csv", index=False)
        self.verification_set.to_csv(param.params['output_directory'] + self.target_var + "_verification_results.csv", index=False)

        print("... done.")

        return


    def save_state(self):
        ### Need to work on this.
        return
