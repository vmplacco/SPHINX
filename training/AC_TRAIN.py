#################################################################
# Author: Devin D Whitten
# Date:   May, 2018
# This is the main driver of the parameter determinations with SPHINX

# All specifications for running should be made in the input
# parameter file.
# Please direct questions/suggestions to dwhitten@nd.edu
#################################################################

import pandas as pd
import numpy as np
#import param_SPLUS82 as param
import sys,os

sys.path.append("../interface")
import dataset, net_functions, network_array
import io_functions

#################################################################
io_functions.intro()
### READ TRAINING SET
params = eval(open("../params/param_AC.py", 'r').read())

TEFF_train = dataset.Dataset(path = params['segue_path'],
                               variable='AC',
                               params = params,
                               mode='TRAINING')


TEFF_train.format_names()
TEFF_train.SNR_threshold(32)
TEFF_train.faint_bright_limit()
TEFF_train.error_reject(training=True)
TEFF_train.specify_variable_bounds('TEFF', bounds = [params['TEFF_MIN'], params['TEFF_MAX']])
TEFF_train.build_colors()
TEFF_train.set_variable_bounds(run=True)
TEFF_train.get_input_stats(inputs='colors')

### generate the important stuff

TEFF_train.uniform_kde_sample()

TEFF_train.get_input_stats(inputs='colors')

### Initialize network

AC_NET = network_array.Network_Array(TEFF_train, target_variable = "AC",
                                        interp_frame = None,
                                        scale_frame  = None,
                                        params       = params,
                                        input_type   = "colors")

AC_NET.set_input_type()
AC_NET.generate_inputs(assert_band   = ['F430'],
                         assert_colors = None,
                         reject_colors = ['F395_F410', 'F410_F430'])
AC_NET.initialize_networks()
AC_NET.construct_scale_frame()
AC_NET.normalize_dataset()
AC_NET.construct_interp_frame()

AC_NET.generate_train_valid()

AC_NET.train(iterations=2, pool=True)
AC_NET.eval_performance()
AC_NET.write_network_performance()
AC_NET.skim_networks(select=params['skim'])
AC_NET.write_training_results()
#AC_NET.training_plots()
AC_NET.save_state("AC_NET_5500_7000_lower")
