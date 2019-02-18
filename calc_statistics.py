# -*- coding: utf-8 -*-

'''
Created on 20.12.2016

@author: tig
'''


import numpy as np
from numpy.core.numeric import asarray
from collections import OrderedDict
import sys
import os
import tempfile


#===============================================================================
# 
#===============================================================================
def removeOutliers(x, outlierConstant):
    """
        @info: Remove outliers using numpy. 
                    Normally, an minor outlier is outside 1.5 * the IQR and major outlier is outside 3 * the IQR 
                    experimental analysis has shown that a higher/lower IQR might produce more accurate results. 
                    Interestingly, after 1000 runs, removing outliers creates a larger standard deviation between test run results.
            
        @see: https://gist.github.com/vishalkuo/f4aec300cf6252ed28d3
              https://ru.wikihow.com/%D0%B2%D1%8B%D1%87%D0%B8%D1%81%D0%BB%D0%B8%D1%82%D1%8C-%D0%B2%D1%8B%D0%B1%D1%80%D0%BE%D1%81%D1%8B 
    """
    a = np.array(x)
    upper_quartile = np.percentile(a, 75)
    lower_quartile = np.percentile(a, 25)
    IQR = (upper_quartile - lower_quartile) * outlierConstant
    quartileSet = (lower_quartile - IQR, upper_quartile + IQR)
    resultList = []
    for y in a.tolist():
        if y >= quartileSet[0] and y <= quartileSet[1]:
            resultList.append(y)
    return resultList

def removeOutliers2(x, m = 2.):
    """
        @see: https://stackoverflow.com/a/16562028/2285037
    """
    data = np.array(x)
    d = np.abs(data - np.median(data))
    mdev = np.median(d)
    s = d/mdev if mdev else 0.
    return data[s<m].tolist()
#===============================================================================
# 
#===============================================================================
"""
    Calculate statistic for Series of values
    @return {min,max,p90,p50,p10,avg}
""" 
def calc_statistics_np(val_series):
    p90= np.percentile(val_series, 10)#, interpolation='linear') #--reverse because p90 need as most 
    p50= np.percentile(val_series, 50)#, interpolation='linear')
    p10= np.percentile(val_series, 90)#, interpolation='linear')
    avg= val_series.mean()            # avg= average(mean)       
    res=OrderedDict([
                     ["Mean",avg]
                    ,["Std.dev",np.std(val_series)]
                    ,["F90",p90]
                    ,["F50",p50]
                    ,["F10",p10]
                    ,["min",val_series.min()]
                    ,["max",val_series.max()]
                    ])
    return res


#==============================================================================
# 
#==============================================================================
#@noPrint
def inverse_transform_sampling(data, n_bins=8, n_samples=200, range=None, append_data_to_result=False):
    r"""
    Compute the random values used histogram of source data

    Parameters
    ----------
    data : array like
        Array of values for generating histogram 
    n_bins : integer
        Number of created bins,when generated histogram of source data
    n_samples : integer
        Number of samples new random data
    range : [float,float] or None
        Range ,used when bin creating. If None take [data.min,data.max]
    append_data_to_result : bool
        If True, then also add 'data' to result array
    @return :
        Array of random generated values with distribution like in 'data'
    
    """
    #print "Generate random values for n_bins={}, n_samples={},range={}".format(n_bins,n_samples,range)
    hist, bin_edges = np.histogram(data, bins=n_bins, range=range, density=True)
    """ 
    @note:
        bin_edges  -indicates that bin #0 is the interval [0,1), bin #1 is [1,2), ..., bin #3 is [3,4).
        hist       -count of values in each intervals (when 'density'=False)
        density    -If False, the result will contain the number of samples in each bin. 
                    If True, the result is the value of the probability density function at the bin, 
                     normalized such that the integral over the range is 1. Note that the sum of the 
                     histogram values will not be equal to 1 unless bins of unity width are chosen; 
                     it is not a probability mass function        
    """
    #print "Histogram:"
    #print hist
    #print "Data:"
    #print data
    #print "Bin edges:"
    #print bin_edges
    
    cum_values = np.zeros(bin_edges.shape) # create list of '0' with len='interval bins'
    cum_values[1:] = np.cumsum(hist*np.diff(bin_edges))
    """
        @note:
        cummulative difference  y1=(x2-x1)*hist; y2=(x3-x2)*hist+y1; y3=(x4-x3)*hist+y2
    """ 
    rand_list = np.random.rand(n_samples)
    try :
        #interpolate using SCIPY
        import scipy.interpolate as interpolate
        f_inv_cdf = interpolate.interp1d(cum_values, bin_edges)
        """
            @note:
            Interpolate a 1-D function.
                x and y are arrays of values used to approximate some function f: y = f(x). This class returns a function whose call method uses interpolation to find the value of new points.
        """
        res=f_inv_cdf(rand_list)
    except:
        #interpolate using NUMPY
        res=np.interp(rand_list, cum_values, bin_edges)
    if append_data_to_result:
        res=np.concatenate((data,res))
    return res


#===============================================================================
# 
#===============================================================================
class CalculateStatistics(object):
    label       = "Calculate Statistic"
    description = """Class for calculate statistic for specifiyng values."""
    N_RND=200
    N_BINS=8
    AVG_SLICE=50
    def __init__(self):
        self.__range=[None,None]
        self.__grid=None
        self.__data_source=[]
        self.__data_result=[]
        pass
    @property
    def range(self):
        return None if None in self.__range else self.__range
    @range.setter
    def range(self, lst):
        """
            Parameters
            ----------
            lst : list[range_min,range_max]
            List of 2 values, used as range limits when calculate Histogram
            
        """
        if lst is None:
            self.__range=[None,None]
        else:
            assert len(lst)==2,"Lengh of range must be 2"
            assert None not in lst,"Not allowed None in range"
            if lst[0]==lst[1]:
                lst[1]+=0.000000001
            self.__range = map(float,lst)
    @property
    def data_source(self):
        return self.__data_source
    
    def generate_random_grid(self,data=None,use_original_data=False,num_grids=1):
        """
        Parameters
        ----------
        data : array_like
            Input data. The histogram is computed over the flattened array.
            If present,then use it, else use previous used array
        num_grids : int
            Number of generated grids
        """
        if not data is None:
            self.__data_source=asarray(data)
            self.__data_result=[]
        for i in range(num_grids):
            self.__data_result.append(inverse_transform_sampling(self.data_source
                                                 , n_bins=self.N_BINS
                                                 , n_samples=self.N_RND
                                                 , range=self.range
                                                 , append_data_to_result=use_original_data
                                                 )
                                      )
        return self.__data_result
    @property
    def data_result(self):
        return self.__data_result
    def get_slice_avg(self,percent=AVG_SLICE):
        ##take mean from full random range
        #res=map(np.mean,self.__data_result)
        #take mean from half data range                         
        #res=map(np.mean,[lst[int(len(lst))/2:] for lst in self.__data_result])
        #take last 'percent' values from each group
        res=map(np.mean,[lst[int((100-percent)*len(lst)/100.0):] for lst in self.__data_result])
        return res
    def get_statistics(self,percent=AVG_SLICE):
        data=np.asarray(self.get_slice_avg(percent))
        res=calc_statistics_np(data)
        return res
  
    def show_hist(self,f_name="histogram"):
        """
            Show histogram 
        """
        try:
            import matplotlib.pyplot as plt
        except:
            return False
        res_f='{}.png'.format(f_name)
        fig = plt.figure(num=None, figsize=(20, 10), dpi=80, facecolor='w', edgecolor='k')
        fig.canvas.set_window_title('Data histograms')
        fig.suptitle("Data histogram", fontsize=16)
        ax = plt.subplot("211")
        ax.set_title("Histogram of source/random data")
        d1=asarray(self.__data_source)
        d2=np.concatenate(asarray(self.__data_result))
        d3=asarray(self.get_slice_avg(self.AVG_SLICE))
        
        ax.hist(d1,bins=self.N_BINS
                ,range=self.range
                ,normed=False, color='b', label='Source data'
                , weights=np.zeros_like(d1) + 1. / d1.size
                )
        ax.hist(d2,bins=self.N_BINS
                ,range=None
                ,normed=False,color='r',alpha=0.5, label='Generated random data'
                , weights=np.zeros_like(d2) + 1. / d2.size
                )
        ax.legend()
        ax = plt.subplot("212")
        ax.set_title("Histogram of group 0 from random data")
        ax.hist(d3, bins=self.N_BINS
                ,range=self.range
                ,normed=False, label='Averaged {}% randomm data'.format(self.AVG_SLICE)
                , weights=np.zeros_like(d3) + 1. / d3.size
                ) 
        plt.savefig(res_f, dpi = 300)
        #plt.show()
        plt.close() 
        return res_f             

    def show_hist2(self,f_name="histogram"):
        """
            Show histogram 
        """
        try:
            import matplotlib.pyplot as plt
        except:
            return False
        res_f='{}.png'.format(f_name)
        fig = plt.figure(num=None, figsize=(20, 10), dpi=80, facecolor='w', edgecolor='k')
        fig.canvas.set_window_title('Data histograms')
        fig.suptitle("Data histogram", fontsize=16)
        ax = plt.subplot("311")
        ax.set_title("Histogram of source data")
        d1=asarray(self.__data_source)
        d2=np.concatenate(asarray(self.__data_result))
        d3=asarray(self.get_slice_avg(self.AVG_SLICE))
        
        ax.hist(d1,bins=self.N_BINS
                ,range=self.range
                ,normed=False, color='b', label='Source data'
                , weights=np.zeros_like(d1) + 1. / d1.size
                )
        ax = plt.subplot("312")
        ax.set_title("Histogram of random data")
        ax.hist(d2,bins=self.N_BINS
                ,range=None
                ,normed=False,color='r',label='Generated random data'
                , weights=np.zeros_like(d2) + 1. / d2.size
                )
        ax = plt.subplot("313")
        ax.set_title("Histogram of averaged data")
        ax.hist(d3, bins=self.N_BINS
                ,range=self.range
                ,normed=False, label='Averaged {}% randomm data'.format(self.AVG_SLICE)
                , weights=np.zeros_like(d3) + 1. / d3.size
                ) 
        plt.savefig(res_f, dpi = 300)
        #plt.show()
        plt.close() 
        return res_f 

            
