# -*- coding: utf-8 -*-

"""
PosteriorContainer wraps samples from the planner
and comes with supporting functions to analyze
"""

__author__ = "Julian Jara-Ettinger"
__license__ = "MIT"

import numpy as np
import matplotlib.pyplot as plt
import sys
import os.path
import math


class PosteriorContainer(object):

    """
    Class to handle posterior samples.
    """

    def __init__(self, C, R, L, ActionSequence, Planner=[]):
        """
        Create an object that stores sampling results.

        Args:
            C (list): List of cost samples
            R (list): List of reward samples
            L (list): List of log-likelihoods
            ActionSequence (list): List of actions
            Planner (Planner): (optional) Planner object
        """
        self.CostSamples = C
        self.RewardSamples = R
        self.LogLikelihoods = L
        self.CostDimensions = self.CostSamples.shape[1]
        self.RewardDimensions = self.RewardSamples.shape[1]
        self.Samples = self.RewardSamples.shape[0]
        self.Actions = ActionSequence
        self.MapFile = None
        if Planner is not None:
            self.CostNames = Planner.Map.StateNames
            self.StartingPoint = Planner.Map.StartingPoint
            self.ActionNames = Planner.Map.ActionNames
            self.ObjectLocations = Planner.Map.ObjectLocations
            self.ObjectTypes = Planner.Map.ObjectTypes
            self.ObjectNames = Planner.Map.ObjectNames
            self.SoftChoice = Planner.Agent.SoftmaxChoice
            self.SoftAction = Planner.Agent.SoftmaxAction
            self.actionTau = Planner.Agent.actionTau
            self.choiceTau = Planner.Agent.choiceTau
        else:
            self.CostNames = None
            self.StartingPoint = None
            self.ActionNames = None
            self.ObjectLocations = None
            self.ObjectTypes = None
            self.ObjectNames = None
            self.SoftChoice = None
            self.SoftAction = None
            self.actionTau = None
            self.choiceTau = None

    def SaveCSV(self, filename, overwrite=False):
        """
        Export samples as a .csv file

        Args:
            filename (str): Filename
            overwrite (bool): Overwrite file if it exists?
        """
        if os.path.isfile(filename) and not overwrite:
            print "ERROR: File exists, type SaveCSV(\"" + filename + "\",True) to overwrite file."
        else:
            f = open(filename, 'w')
            # Create header
            if self.ObjectNames is not None:
                for i in range(len(self.ObjectNames)):
                    if i == 0:
                        Header = str(self.ObjectNames[i])
                    else:
                        Header = Header + "," + str(self.ObjectNames[i])
            else:
                for i in range(self.RewardDimensions):
                    if i == 0:
                        Header = "Object" + str(i)
                    else:
                        Header = Header + ",Object" + str(i)
            if self.CostNames is not None:
                for i in self.CostNames:
                    Header = Header + "," + str(i)
            else:
                for i in range(self.CostDimensions):
                    Header = Header + ",Terrain" + str(i)
            Header = Header + ",LogLikelihood\n"
            f.write(Header)
            # Now add the samples
            for i in range(self.CostSamples.shape[0]):
                for j in range(self.RewardDimensions):
                    if j == 0:
                        NewLine = str(self.RewardSamples[i, j])
                    else:
                        NewLine = NewLine + "," + str(self.RewardSamples[i, j])
                for j in range(self.CostDimensions):
                    NewLine = NewLine + "," + str(self.CostSamples[i, j])
                NewLine = NewLine + "," + str(self.LogLikelihoods[i]) + "\n"
                f.write(NewLine)
            f.close()

    def AssociateMap(self, MapName):
        """
        Add a map name of Posterior PosteriorContainer. Function also checks if Map exists in library.

        Args:
            MapName (string): Name of map to use.
        """
        self.MapFile = MapName
        FilePath = os.path.dirname(__file__) + "/Maps/" + MapName + ".ini"
        if not os.path.isfile(FilePath):
            print "WARNING: PosteriorContainer is linked with a map that doesn't exist in Bishop's library."

    def LongSummary(self):
        """
        LongSummary prints a summary of the samples, the convergence analysis,
        and it plots the posterior distributions.
        """
        self.Summary()
        self.AnalyzeConvergence()
        # 10 is the default input. Just sending it to avoid the print message
        self.PlotCostPosterior(10)
        self.PlotRewardPosterior(10)

    def CompareRewards(self):
        """
        Create a matrix where (i,j) is the probability that object i has a
        higher or equal reward than object j.
        """
        RewardComparison = np.zeros(
            (self.RewardDimensions, self.RewardDimensions))
        for i in range(self.RewardDimensions):
            for j in range(i, self.RewardDimensions):
                for s in range(self.Samples):
                    if (self.RewardSamples[s, i] >= self.RewardSamples[s, j]):
                        RewardComparison[i][
                            j] += np.exp(self.LogLikelihoods[s])
                    else:
                        RewardComparison[j][
                            i] += np.exp(self.LogLikelihoods[s])
        return RewardComparison

    def CompareCosts(self):
        """
        Create a matrix where (i,j) is the probability that terrain i has a
        higher or equal cost than terrain j.
        """
        CostComparison = np.zeros((self.CostDimensions, self.CostDimensions))
        for i in range(self.CostDimensions):
            for j in range(i, self.CostDimensions):
                for s in range(self.Samples):
                    if (self.CostSamples[s, i] >= self.CostSamples[s, j]):
                        CostComparison[i][j] += np.exp(self.LogLikelihoods[s])
                    else:
                        CostComparison[j][i] += np.exp(self.LogLikelihoods[s])
        return CostComparison

    def GetExpectedCosts(self, limit=None):
        """
        Calculate the expected costs using the first N samples.

        Args:
            limit (int): Number of samples to use
        """
        ExpectedCosts = []
        if limit is None:
            limit = self.Samples - 1
        for i in range(self.CostDimensions):
            NL = np.exp(self.LogLikelihoods[0:(limit + 1)])
            if sum(NL) == 0:
                print "WARNING: All likelihoods are zero up to this point. POSTERIORCONTAINER-001"
                NL = [1.0 / NL.shape[0]]
            else:
                NL = NL / sum(NL)
            a = self.CostSamples[0:(limit + 1), i]
            b = NL
            res = sum([float(a[i]) * float(b[i]) for i in range(limit + 1)])
            ExpectedCosts.append(res)
        return ExpectedCosts

    def GetExpectedRewards(self, limit=None):
        """
        Calculate the expected rewards using the first N samples.

        Args:
            limit (int): Number of samples to use
        """
        ExpectedRewards = []
        if limit is None:
            limit = self.Samples - 1
        for i in range(self.RewardDimensions):
            NL = np.exp(self.LogLikelihoods[0:(limit + 1)])
            if sum(NL) == 0:
                print "WARNING: All likelihoods are zero up to this point. POSTERIORCONTAINER-001"
                NL = [1.0 / NL.shape[0]]
            else:
                NL = NL / sum(NL)
            a = self.RewardSamples[0:(limit + 1), i]
            b = NL
            res = sum([float(a[i]) * float(b[i]) for i in range(limit + 1)])
            ExpectedRewards.append(res)
        return ExpectedRewards

    def PlotCostPosterior(self, bins=None):
        """
        Plot posterior distribution of cost samples

        Args:
            bins (int): Number of bins to use
        """
        if bins is None:
            print "Number of bins not specified. Defaulting to 10."
            bins = 10
        maxval = np.amax(self.CostSamples)
        binwidth = maxval * 1.0 / bins + 0.00001
        xvals = [binwidth * (i + 0.5) for i in range(bins)]
        for i in range(self.CostDimensions):
            yvals = [0] * bins
            insert_indices = [int(math.floor(j / binwidth))
                              for j in self.CostSamples[:, i]]
            for j in range(self.Samples):
                yvals[insert_indices[j]] += np.exp(self.LogLikelihoods[j])
            plt.plot(xvals, yvals)
        if self.CostNames is not None:
            plt.legend(self.CostNames, loc='upper left')
        else:
            plt.legend([str(i)
                        for i in range(self.CostDimensions)], loc='upper left')
        plt.xlabel("Cost")
        plt.ylabel("Probability")
        plt.title("Posterior distribution of terrain costs")
        plt.show()

    def PlotRewardPosterior(self, bins=None):
        """
        Plot posterior distribution of reward samples

        Args:
            bins (int): Number of bins to use
        """
        if bins is None:
            print "Number of bins not specified. Defaulting to 10."
            bins = 10
        maxval = np.amax(self.RewardSamples)
        binwidth = maxval * 1.0 / bins + 0.00001
        xvals = [binwidth * (i + 0.5) for i in range(bins)]
        for i in range(self.RewardDimensions):
            yvals = [0] * bins
            insert_indices = [int(math.floor(j / binwidth))
                              for j in self.RewardSamples[:, i]]
            for j in range(self.Samples):
                yvals[insert_indices[j]] += np.exp(self.LogLikelihoods[j])
            plt.plot(xvals, yvals)
        if self.ObjectNames is not None:
            plt.legend(self.ObjectNames, loc='upper left')
        else:
            plt.legend([str(i)
                        for i in range(self.RewardDimensions)], loc='upper left')
            plt.set
        plt.xlabel("Reward")
        plt.ylabel("Probability")
        plt.title("Posterior distribution of rewards")
        plt.show()

    def Summary(self, human=True):
        """
        Print summary of samples.

        Args:
            human (bool): When true function prints a human-readable format.
                          When false it prints a compressed csv format (suitable for merging many runs)
        """
        ExpectedRewards = self.GetExpectedRewards()
        RewardMatrix = self.CompareRewards()
        ExpectedCosts = self.GetExpectedCosts()
        CostMatrix = self.CompareCosts()
        # Combine all function to print summary here
        if human:
            sys.stdout.write("Map: " + str(self.MapFile) + "\n")
            sys.stdout.write(
                "To see map details run Bishop.LoadObserver(self).\n")
            sys.stdout.write(
                "Object locations: " + str(self.ObjectLocations) + "\n")
            sys.stdout.write(
                "Object types: " + str(self.ObjectTypes) + "\n")
            sys.stdout.write(
                "Results using " + str(self.Samples) + " samples.\n")
            sys.stdout.write("\nPATH INFORMATION\n\n")
            sys.stdout.write(
                "Starting position: " + str(self.StartingPoint) + "\n")
            sys.stdout.write("Actions: " +
                             str(self.ActionNames) + ".\n")
            if self.SoftChoice:
                sys.stdout.write("Softmaxed choices.\n")
            else:
                sys.stdout.write("Optimal choices.\n")
            if self.SoftAction:
                sys.stdout.write("Softmaxed actions.\n")
            else:
                sys.stdout.write("Optimal actions.\n")
            sys.stdout.write("\nINFERRED REWARDS\n\n")
            if (self.ObjectNames is not None):
                for i in range(self.RewardDimensions):
                    sys.stdout.write(
                        str(self.ObjectNames[i]) + ": " + str(ExpectedRewards[i]) + "\n")
                sys.stdout.write(str(self.ObjectNames) + "\n")
            else:
                sys.stdout.write(str(ExpectedRewards) + "\n")
            sys.stdout.write(
                "Reward comparison matrix: i, j = p( R(i)>=R(j) )\n")
            sys.stdout.write(str(RewardMatrix) + "\n")
            sys.stdout.write("\nINFERRED COSTS\n\n")
            if (self.CostNames is not None):
                for i in range(self.CostDimensions):
                    sys.stdout.write(
                        str(self.CostNames[i]) + ": " + str(ExpectedCosts[i]) + "\n")
                sys.stdout.write(str(self.CostNames) + "\n")
            else:
                sys.stdout.write(str(ExpectedCosts) + "\n")
            sys.stdout.write(
                "Cost comparison matrix: i, j = p( C(i)>=C(j) )\n")
            sys.stdout.write(str(CostMatrix) + "\n")
        else:
            # Print header
            sys.stdout.write(
                "Samples,StartingPoint,ObjectLocations,ObjectTypes,SoftmaxAction,ActionTau,SoftmaxChoice,ChoiceTau,Actions")
            if self.ObjectNames is not None:
                for i in range(self.RewardDimensions):
                    sys.stdout.write("," + str(self.ObjectNames[i]))
            else:
                for i in range(self.RewardDimensions):
                    sys.stdout.write(",Object" + str(i))
            if self.CostNames is not None:
                for i in range(self.CostDimensions):
                    sys.stdout.write("," + str(self.CostNames[i]))
            else:
                for i in range(self.CostDimensions):
                    sys.stdout.write(",Cost" + str(i))
            # Names for reward tradeoffs
            for i in range(self.RewardDimensions):
                for j in range(i + 1, self.RewardDimensions):
                    if i != j:
                        if self.ObjectNames is not None:
                            sys.stdout.write(
                                "," + str(self.ObjectNames[i]) + "-" + str(self.ObjectNames[j]))
                        else:
                            sys.stdout.write(",R" + str(i) + "-R" + str(j))
            # Names for cost tradeoffs
            for i in range(self.CostDimensions):
                for j in range(i + 1, self.CostDimensions):
                    if i != j:
                        if self.CostNames is not None:
                            sys.stdout.write(
                                "," + str(self.CostNames[i]) + "-" + str(self.CostNames[j]))
                        else:
                            sys.stdout.write(",O" + str(i) + "-O" + str(j))
            sys.stdout.write("\n")
            # Print results
            sys.stdout.write(
                str(self.Samples) + "," + str(self.StartingPoint) + ",")
            for i in range(len(self.ObjectLocations)):
                if i < (len(self.ObjectLocations) - 1):
                    sys.stdout.write(str(self.ObjectLocations[i]) + "-")
                else:
                    sys.stdout.write(str(self.ObjectLocations[i]))
            sys.stdout.write(",")
            for i in range(len(self.ObjectTypes)):
                if i < (len(self.ObjectTypes) - 1):
                    sys.stdout.write(str(self.ObjectTypes[i]) + "-")
                else:
                    sys.stdout.write(str(self.ObjectTypes[i]))
            sys.stdout.write("," + str(self.SoftAction) + "," + str(
                self.actionTau) + "," + str(self.SoftChoice) + "," + str(self.choiceTau) + ",")
            for i in range(len(self.Actions)):
                if i < (len(self.Actions) - 1):
                    sys.stdout.write(str(self.Actions[i]) + "-")
                else:
                    sys.stdout.write(str(self.Actions[i]))
            for i in range(self.RewardDimensions):
                sys.stdout.write("," + str(ExpectedRewards[i]))
            for i in range(self.CostDimensions):
                sys.stdout.write("," + str(ExpectedCosts[i]))
            # Print reward tradeoffs
            RewardM = self.CompareRewards()
            for i in range(self.RewardDimensions):
                for j in range(i + 1, self.RewardDimensions):
                    if i != j:
                        sys.stdout.write("," + str(RewardM[i][j]))
            # Print cost tradeoffs
            CostM = self.CompareCosts()
            for i in range(self.CostDimensions):
                for j in range(i + 1, self.CostDimensions):
                    if i != j:
                        sys.stdout.write("," + str(CostM[i][j]))
            sys.stdout.write("\n")

    def AnalyzeConvergence(self, jump=None):
        """
        Plot estimates as a function of the number of samples to visually determine is samples converged.

        Args:
            jump (int): Number of skips between each sample.
        """
        # jump indicates how often to recompute the expected value
        if jump is None:
            if self.Samples > 100:
                print "Recomputing expected value after every 20 samples"
                jump = int(round(self.Samples * 1.0 / 20))
            else:
                print "Recomputing expected value after every sample"
                jump = 1
        rangevals = range(0, self.Samples, jump)
        ycostvals = [self.GetExpectedCosts(i) for i in rangevals]
        ycostvals = np.array(ycostvals)
        yrewardvals = [self.GetExpectedRewards(i) for i in rangevals]
        yrewardvals = np.array(yrewardvals)
        # break it into plots.
        # Costs
        f, axarr = plt.subplots(1, 2)
        for i in range(self.CostDimensions):
            axarr[0].plot(rangevals, ycostvals[:, i])
        if self.CostNames is not None:
            axarr[0].legend(self.CostNames, loc='upper left')
        else:
            axarr[0].legend(
                [str(i) for i in range(self.CostDimensions)], loc='upper left')
        # Rewards
        for i in range(self.RewardDimensions):
            axarr[1].plot(rangevals, yrewardvals[:, i])
        if self.ObjectNames is not None:
            axarr[1].legend(self.ObjectNames, loc='upper left')
        else:
            axarr[1].legend(
                [str(i) for i in range(self.RewardDimensions)], loc='upper left')
        plt.show()

    def ML(self, n=1, round=2):
        """
        Print maximum likelihood sample(s)

        n (int): Print top n samples
        round (int): How much to round the samples
        """
        indices = self.LogLikelihoods.argsort()[-n:]
        likelihoods = np.exp(self.LogLikelihoods[indices])
        Costs = self.CostSamples[indices]
        Rewards = self.RewardSamples[indices]
        # Print header
        if self.CostNames is not None:
            for i in range(self.CostDimensions):
                sys.stdout.write(str(self.CostNames[i]) + "\t")
        else:
            for i in range(self.CostDimensions):
                sys.stdout.write("Terrain" + str(i) + "\t")
        if self.ObjectNames is not None:
            for i in range(self.RewardDimensions):
                sys.stdout.write(str(self.ObjectNames[i]) + "\t")
        else:
            for i in range(self.RewardDimensions):
                sys.stdout.write("Object" + str(i) + "\t")
        sys.stdout.write("Likelihood\n")
        # Print data
        for top in range(n):
            # Print cost samples
            for i in range(self.CostDimensions):
                sys.stdout.write(str(np.round(Costs[top, i], 2)) + "\t")
            # Print reward samples
            for i in range(self.RewardDimensions):
                sys.stdout.write(str(np.round(Rewards[top, i], 2)) + "\t")
            sys.stdout.write(str(np.round(likelihoods[top], 2)) + "\n")

    def Display(self, Full=False):
        """
        Print object attributes.

        .. Warning::

           This function is for internal use only.

        Args:
            Full (bool): When set to False, function only prints attribute names. Otherwise, it also prints its values.

        Returns:
            standard output summary
        """
        if Full:
            for (property, value) in vars(self).iteritems():
                print property, ': ', value
        else:
            for (property, value) in vars(self).iteritems():
                print property
