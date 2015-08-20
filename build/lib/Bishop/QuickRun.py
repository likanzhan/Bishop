# -*- coding: utf-8 -*-

"""
Script to quickly run cost-reward inferences on an existing map.

For help:
>> pytyon QuickRun.py --help

Example:

>> python QuickRun.py --map Tatik_T1_L1 --samples 100 --actions "2 2 2"

runs inference on map Tatik_T1_L1 using 100 samples
and action sequence 2 2 2.

>> python QuickRun.py --map Tatik_T1_L1 --samples 100 --actions "2 2 2" --output "samples"
or
>> python QuickRun.py -m Tatik_T1_L1 -s 100 -a "2 2 2" -o "samples"

saves output on "samples.p" as a pickle file.
"""

__author__ = "Julian Jara-Ettinger"
__license__ = "MIT"

from Bishop import *
import argparse

parser = argparse.ArgumentParser()
parser.add_argument(
    "-m", "--map", help="Name of the file with map details (Must be in Bishop's library or in local folder).")
parser.add_argument(
    "-a", "--actions", help="Sequence of observed actions (Numerical).")
parser.add_argument(
    "-s", "--samples", help="Number of samples to use on inference.", type=int)
parser.add_argument(
    "-o", "--output", help="Name of file where to solve samples")
args = parser.parse_args()
O = LoadObserver(args.map, False, True)
# Need to split args.Actions
ActionSequence = [int(s) for s in args.actions.split()]
Res = O.InferAgent(ActionSequence, args.samples)
Res.Summary(False)
if args.output is not None:
    SaveSamples(Res, args.output)
