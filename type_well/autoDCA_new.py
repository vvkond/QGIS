
# -*- coding: utf-8 -*-

from __future__ import division
import webbrowser, os
import pandas as pd
from os.path import join
from pandas import ExcelWriter
import pandas.io.sql as psql
import numpy as np
from scipy.optimize import curve_fit
import random
try: # try import updated matplotlib
    import matplotlib2.pyplot as plt
    import matplotlib2.style as mplstyle
    plt.switch_backend('Qt4Agg') #plt.get_backend)
    plt.ion()
    #plt.switch_backend('TkAgg') #plt.get_backend)
except:
    import matplotlib.pyplot as plt
    import matplotlib.style as mplstyle

from sklearn import datasets, linear_model
from sklearn.metrics import mean_squared_error, r2_score
from pandas.plotting import register_matplotlib_converters
#from production_sql import prod_sql

from collections import namedtuple
register_matplotlib_converters()

#mplstyle.use('fast') #---graphic style
 
dir = os.path.join(os.path.dirname(__file__),'tmp_TypeWell')
out_dir=os.path.join(dir,'Reports')
GRAPH_TIMEOUT=3
IS_STANDALONE=False
if not os.path.exists(out_dir):os.mkdir(out_dir)
"""
 @TODO: reservoir group selector
         Wells select from current layer selected objects
         
#Forecast parameters setup
forecast_end='2029'
# Set technical rate limit, m3/D
MinRate=0.158988 #One barrel per day
#MinRate=0
# Set technical WC limit, frac
MaxWC=0.99

#Autofit parameters setup. Threshold defines sensitivity of data variation
threshold=0.1
#maxthreshold=3
#This can handle rugousity of the chart (ignore gaps)
#threshold_step=0.05

#Set forecast selection charts
LastPointFcst=True
LastDateFcst=False
EndFitFcst=False

#Set units, defulat is perday=1:

perhour=1 #defaults is 24
persecond=1 #default is 3600 
"""
SQL_PROD="""
with grps as (
    select distinct 
        w.WELL_ID               WELL_ID
        ,RP.RESERVOIR_PART_CODE RP_CODE
        ,RP.RESERVOIR_PART_S    RP_ID
        ,GRP.RESERVOIR_PART_CODE GRP_CODE
        ,GRP.RESERVOIR_PART_S   GRP_ID
        ,wbi.WELLBORE_INTV_S
    from 
        WELL w
        ,WELLBORE wb
        ,RESERVOIR_PART rp
        ,WELLBORE_INTV wbi
        ---get WELLBORE_INTERVAL(SEC_TOPLG_OBJ)->is topological in RESERVOIR_PART(PRIM_TOPLG_OBJ) 
        LEFT JOIN TOPOLOGICAL_REL 
            ON 
                TOPOLOGICAL_REL.SEC_TOPLG_OBJ_S = wbi.WELLBORE_INTV_S
                AND 
                TOPOLOGICAL_REL.SEC_TOPLG_OBJ_T = 'WELLBORE_INTV'
                AND
                TOPOLOGICAL_REL.PRIM_TOPLG_OBJ_T='EARTH_POS_RGN'
        LEFT JOIN EARTH_POS_RGN 
            ON 
                TOPOLOGICAL_REL.PRIM_TOPLG_OBJ_S =EARTH_POS_RGN.EARTH_POS_RGN_S
                AND
                EARTH_POS_RGN.GEOLOGIC_FTR_T='RESERVOIR_PART'
        INNER JOIN RESERVOIR_PART GRP 
            ON 
                EARTH_POS_RGN.GEOLOGIC_FTR_S=GRP.RESERVOIR_PART_S
    ----            
    where 
        wbi.WELLBORE_S=wb.WELLBORE_S
        ---get RESERVOIR_PART of WELLBORE_INTERVAL
        and wbi.GEOLOGIC_FTR_T='RESERVOIR_PART'
        and rp.RESERVOIR_PART_S=wbi.GEOLOGIC_FTR_S
        and w.WELL_S=wb.WELL_S
)
select 
    vpr.WELL_ID
    ,min(PROD_START_TIME) PROD_START_TIME
    ,max(PROD_END_TIME)   PROD_END_TIME
    ,sum(case when PROD_VALUE_NAME='crude oil' and PROD_VALUE_SOURCE='P_STD_VOL_LQ' then PROD_VALUE else 0 end) as OIL_VOL
    ,sum(case when PROD_VALUE_NAME='produced water' and PROD_VALUE_SOURCE='P_STD_VOL_LQ' then PROD_VALUE else 0 end) as WAT_VOL
    ,sum(case when PROD_VALUE_NAME='natural gas' and PROD_VALUE_SOURCE='P_STD_VOL_GAS' then PROD_VALUE else 0 end) as GAS_VOL
    ,sum(case when PROD_VALUE_NAME='condensate' and PROD_VALUE_SOURCE='P_STD_VOL_LQ' then PROD_VALUE else 0 end) as COND_VOL
    ,max(PROD_DAYS) PROD_DAYS
    ,grps.GRP_CODE  GRP_CODE   
    
from V_PROD_RESPART_M2 vpr
left join grps
    on vpr.WELLBORE_INTV_S=grps.WELLBORE_INTV_S
where 1=1 
    {FILTER_GRP}          ---- FILTER RESERVOIR GROUPS  (grps.GRP_CODE)
    {FILTER_WELLS}        ----FILTER WELLS              (vpr.WELL_ID)
group by vpr.WELL_ID
        , PROD_START_YEAR
        , PROD_START_MONTH
        , grps.GRP_CODE    
order by vpr.WELL_ID
       , PROD_START_YEAR
       , PROD_START_MONTH
       , grps.GRP_CODE     
"""
cREG='GRP_CODE'
cWELL='WELL_ID'
cPROD_DAYS='PROD_DAYS'
cPROD_START_TIME='PROD_START_TIME'
cWAT_VOL='WAT_VOL'
cOIL_VOL='OIL_VOL'
cNAT_GAS='GAS_VOL'
cCOND_VOL='COND_VOL'


#===============================================================================
# 
#===============================================================================
def log(*args):
    if IS_STANDALONE:
        print " ".join(map(str,args))
    else:
        from qgis.core import QgsMessageLog 
        QgsMessageLog.logMessage(" ".join(map(str,args)), tag="QgisPDS.DCA")
    pass

#Raservoir group selection block
#These parameters of reservoir must be set as an attribute in BOL Wellbore Reservoir Element Group
#######################################################################################
#===============================================================================
# Read reservoir properties from XLS file
#===============================================================================
OilReservoirProp=namedtuple('OilReservoirProp',[
                                           "primdiv"
                                          ,"primary_product"
                                          ,"secondary_product"
                                          ,"secdiv"
                                          ,"units"
                                          ,"calcRF"
                                          ,"propan_fraction"
                                          ,"GOR"
                                          ,"FF"
                                          ])

GasReservoirProp=namedtuple('GasReservoirProp',[
                                             "primdiv"
                                            ,"primary_product"
                                            ,"secondary_product"
                                            ,"secdiv"
                                            ,"units"
                                            ,"calcRF"
                                            ,"cond_RFi"
                                            ,"propan_fraction"
                                            ,"FF"
                                            ,"propan_dens"
                                            ,"propan_liq_dens"
                                            ,"BOE"
                                            ,"WetGasShrink"
                                          ])

def get_reservoir_prop(REG):
    """    
        @return:
    """
    in_f=join(dir,'Chinarevskoe_REG1.xlsx')
    reg_properties=pd.read_excel(in_f)
    reg_string=primary_product=''
    try:
        reg_string=reg_properties.loc[reg_properties.REG == REG]
        primary_product=reg_string['primary_product'].iloc[0]
    except:
        return False
    #primary_product='GAS_VOL'
    #
    if primary_product==u'OIL_VOL':
        return OilReservoirProp(
                primary_product=cOIL_VOL
                ,primdiv=1
                ,secondary_product=cNAT_GAS
                ,secdiv=1000 #Gas is stored in m3, need to be comverted to Mm3
                ,units=', m3'
                ,calcRF=False
                ,propan_fraction=reg_string['propan_fraction'].iloc[0] #This must be taken frpm REG attributes
                ,GOR=reg_string['GOR'].iloc[0]
                ,FF=reg_string['FF'].iloc[0] #Oil shrinkage formation factor
            )
    elif primary_product==u'GAS_VOL':
        return GasReservoirProp(    
                primary_product=cNAT_GAS    
                ,primdiv=1000 #Gas is stored in m3, need to be comverted to Mm3
                ,secondary_product=cCOND_VOL
                ,secdiv=1
                ,units=', Mm3'
                ,calcRF=True
                ,cond_RFi=reg_string['cond_RFi'].iloc[0]/1000 #Used to calculate EUR of condensate from Gas EUR at t0, Mm3/Mm3
                ,propan_fraction=reg_string['propan_fraction'].iloc[0] #This must be taken frpm REG attributes
                ,FF=reg_string['FF'].iloc[0] #Gas expansion formation factor
                ,propan_dens=2.3 #kg/m3]
                ,propan_liq_dens=520 #kg/m3
                ,BOE=6.3 #Barrel oil equivalent
                ,WetGasShrink=reg_string['WetGasShrink'].iloc[0]
                )
#=======================================================================
# 
#=======================================================================
Config=namedtuple('Config',[
                             "forecast_end"
                            ,"MinRate"
                            ,"MaxWC"
                            ,"threshold"
                            ,"LastPointFcst"
                            ,"LastDateFcst"
                            ,"EndFitFcst"
                            ,"perhour"
                            ,"persecond"
                            ,"window_size"
                            ,"UseTypeWell"
                          ])

def get_config(
                forecast_end='2029'
                # Set technical rate limit, m3/D
                ,MinRate=0.158988 #One barrel per day
                #MinRate=0
                # Set technical WC limit, frac
                ,MaxWC=0.99
                #Autofit parameters setup. Threshold defines sensitivity of data variation
                ,threshold=0.1
                #maxthreshold=3
                #This can handle rugousity of the chart (ignore gaps)
                #threshold_step=0.05
                #Set forecast selection charts
                ,LastPointFcst=True
                ,LastDateFcst=False
                ,EndFitFcst=False
                #Set units, defulat is perday=1:
                ,perhour=1 #defaults is 24
                ,persecond=1 #default is 3600
                ,window_size=5 #size of Sample for calculkation
                ,UseTypeWell=True
        ):
    """    
        @return: config
    """
    return Config(
                forecast_end=forecast_end
                ,MinRate=MinRate
                ,MaxWC=MaxWC
                ,threshold=threshold
                ,LastPointFcst=LastPointFcst
                ,LastDateFcst=LastDateFcst
                ,EndFitFcst=EndFitFcst
                ,perhour=perhour
                ,persecond=persecond
                ,window_size=window_size
                ,UseTypeWell=UseTypeWell
                )
#===============================================================================
# 
#===============================================================================
def get_connection(
                       host='poni'
                      ,port=1521
                      ,inst='PDS252'
                      ,user='system'
                      ,pwd='manager'
                      ,schema='chinar_ofm'        
                    ):        
    connection=connect_to_db(host=host
                      ,port=port
                      ,inst=inst
                      ,user=user
                      ,pwd=pwd
                      ,schema=schema
                         )  
    return connection


#=======================================================================
# 
#=======================================================================
class DCA():
    def __init__(self
                 , reservoir_group
                 , well_names=None
                 , conn=None
                 , config=get_config()
                 ):
        self.is_terminated=False
        self.REG=reservoir_group
        self.WELLS=well_names
        log("Read DCA config")
        self.config=config
        self.reservoir_prop=get_reservoir_prop(self.REG)
        if not self.reservoir_prop:
            log("Error. Can't read reservoir group '{}' property".format(self.REG))
            self.is_terminated=True
        if self.config.UseTypeWell and  self.config.window_size>len(self.WELLS)>0:
            log("Error. Window size={} must be < 'selected wells'{}".format(str(self.config.window_size),str(len(self.WELLS))))
            self.is_terminated=True
        if conn is None:
            self.conn=get_connection()
        else:
            self.conn=conn
        #log(self.conn)
        #log(self.config)
        #log(self.reservoir_prop)
    #===================================================================
    # 
    #===================================================================
    def show_plot(self,plt,timeout=GRAPH_TIMEOUT,block=True):
        if IS_STANDALONE:
            plt.show(block=block)
            if not block:
                plt.pause(timeout)
                plt.close()
        else:
            plt.show()
            if not block:
                plt.pause(timeout)
                plt.close()
            else:
                while True:
                    btnpress = plt.waitforbuttonpress(0.2)
                    if  self.is_terminated:
                        plt.waitforbuttonpress(-1)
                        plt.close()
                        break                
                    elif btnpress is None: # timeout.no action
                        continue  
                    elif not btnpress:     #on mouse click 
                        break
                    else:                  #on keyboard press
                        break
    #===========================================================
    # 
    #===========================================================
    def on_plt_close(self,evt):
        self.is_terminated=True
        plt.close()
        print('Terminated')
    #===========================================================
    # 
    #===========================================================
    def on_mouse_press(self,event):
        """
            @param event.button: 1 left mouse,2 right mouse,3 center mouse
        """
        
        log('you pressed', event.button, event.xdata, event.ydata)
    #===========================================================
    # 
    #===========================================================
    def on_key_press(self,event):
        log('press', event.key)
        if event.key=='escape':
            self.on_plt_close(None)

    ########################################################
    #Find longest straight periods. Used for Log(Q) vs Time
    ########################################################
    @staticmethod
    def fitselect(data,threshold,prd):
        #data[prd]=data[prd].rolling(window=5).mean()
        a=np.array(data[prd].pct_change())
        datemax=0 # Latest end date
        longest=len(data)
        imax=0 #Maximum length of sequential data
        i=0
        #end=len(a) #Local latest date
        end=len(a)
        stream=data[:1] # This is a dataframe with longest straight line
        for j in range(len(a))[-end:]:
        #for j in reversed(xrange(len(a))):
            if abs(a[j]) < threshold:
                i=i+1
                if imax < i:
                    imax=i
                end=j
                
            else:
                if imax < i:
                    imax=i
                end=j
                start=end-i
                #log("start= ", start, "end= ", end, "i= ",i)
                i=0
            if len(stream)<=imax:
                stream=pd.DataFrame(data.iloc[start:end,:])
            #log("start= "+str(start)+" end= "+str(end)+" j="+str(j)+" i= "+str(i)+" imax= "+str(imax)+" lenstream="+str(len(stream)))
        return stream
    """
    #Old version of fitselect
    def fitselect(data,threshold,prd):
        a=np.array(data[prd].pct_change())
        datemax=0 # Latest end date
        longest=len(data)
        imax=0 #Maximum length of sequential data
        i=0
        end=1 #Local latest date
        stream=data[:1] # This is a dataframe with longest straight line
        while end > datemax or imax < longest:
            datemax=end
            longest=imax
            #print "datemax= ",datemax, "longest= ",longest
            for j in range(len(a)):
            #for j in reversed(xrange(len(a))):
                if abs(a[j]) < threshold:
                    i=i+1
                    if imax < i:
                        imax=i
                        #Index in dataframe
                        end=j
                        start=end-i
                    #print "j=",j,"i=",i,"imax=",imax
                else:
                    i=0
                if len(stream)<imax:
                        stream=pd.DataFrame(data.iloc[start:end,:])
                #oil.iat[j,1]=i
            
        return stream
    """
    ###########################################################################
    #Select last time points data, more applicable for 1+WOR vs Cumulative Oil
    ###########################################################################
    @staticmethod
    def lastselect(data,prd,wor):
        np_Rate=np.array(data.loc[:,[prd]].dropna())
        np_Cum=np.array(data.loc[:,['CumOil']].dropna())
        
        #Regression analysis
        #Calculate logarythm of Oil
        if not wor:
            ab=np.log(np_Rate)
            regr = linear_model.LinearRegression()
            regr.fit(np_Cum,ab)
            oil_fit=2.72**regr.predict(np_Cum)
        if wor:
            regr = linear_model.LinearRegression()
            regr.fit(np_Cum,np_Rate)
            oil_fit=regr.predict(np_Cum)
                
        return oil_fit, regr
    ######################################
    #Regression analysis log rate vs time
    ######################################
    @staticmethod
    def linregress(data, wor):
        #Create np arrays
        if not wor:
            log('Log(Q) vs Time regression parameters:')
            np_Time=np.array(data.loc[:,['Time']])
            np_Oil=np.array(data.loc[:,['Rate']])
            #Calculate logarythm of Oil
            ab=np.log(np_Oil)
            # Create linear regression object and run regression
            regr = linear_model.LinearRegression()
            regr.fit(np_Time,ab)
            oil_fit=2.72**regr.predict(np_Time)
        if wor:
            log( '1+WOR vs Time regression parameters:')
            np_Time=np.array(data.loc[:,['Time']])
            np_Oil=np.array(data.loc[:,['WOR']])
            # Create linear regression object and run regression
            regr = linear_model.LinearRegression()
            regr.fit(np_Time,np_Oil)
            oil_fit=regr.predict(np_Time)
        """
        print '-------------------------------------'
        # The coefficients
        print 'Coefficients:', regr.coef_[0][0] #, regr1.slope
        print 'Intercept:', 2.72**regr.intercept_[0], #2.72**regr1.intercept
        print 'stream=', len(stream)
        
        
        # The mean squared error
        print("Mean squared error: %.2f"
              % mean_squared_error(np_Oil, oil_fit))
        # Explained variance score: 1 is perfect prediction
        print('Variance score: %.2f' % r2_score(np_Oil, oil_fit))
        #Goodness of fit
        print 'Goodness of fit: ', mean_squared_error(np_Oil, oil_fit)
        print '=========================='
        """
        return oil_fit, regr
    
    #######################################
    #Regression analysis rate vs cumulative
    #######################################
    @staticmethod
    def cumlinregress(data):
        #Create np arrays
        np_Cum=np.array(data.loc[:,['CumOil']])
        np_Oil=np.array(data.loc[:,['Rate']])
    
        # Create linear regression object and run regression
        cumregr = linear_model.LinearRegression()
        cumregr.fit(np_Cum,np_Oil)
        cumoil_fit=cumregr.predict(np_Cum)
        """
        print 'Q vs Cumulative regression parameters:'
        print '--------------------------------------'
        # The coefficients
        print 'Coefficients:', cumregr.coef_[0][0]
        print 'Intercept:', cumregr.intercept_[0]
    
        # The mean squared error
        print("Mean squared error: %.2f"
              % mean_squared_error(np_Oil, cumoil_fit))
        # Explained variance score: 1 is perfect prediction
        print('Variance score: %.2f' % r2_score(np_Oil, cumoil_fit))
        #Goodness of fit
        print 'Goodness of fit: ', mean_squared_error(np_Oil, cumoil_fit)
        print '========================='
        """
        return cumoil_fit, cumregr    
    ###################################################################
    #Calculate forecast at last point, end of fitted curve or last date
    ###################################################################
    def forecast(self,data, primary_product, regr_type, forecast_type, forecast_start, forecast_end, Qi, eT):
        forecast_dates=pd.date_range(forecast_start, forecast_end, freq='M')
        forecast=pd.DataFrame(index=forecast_dates)
        forecast['Time']=forecast.index.days_in_month*self.config.perhour*self.config.persecond
        #Add cumulative time to the first forecast period
        if forecast_type=='last_date':
            #forecast.iat[0,0]=data['Time'].max()-forecast.iat[0,0]
            forecast.iat[0,0]=data['Time'].max()
        if forecast_type=='end_fit':
            #print ' ', eT
            forecast.iat[0,0]=eT
        """
        if forecast_type=='last_point':
            #forecast.iat[0,0]=data['Time'].max()-forecast.iat[0,0]
            forecast.iat[0,0]=data['Time'].max()
        """
        forecast['Time']=forecast['Time'].cumsum()
        np_FcstTime=np.array(forecast.loc[:,['Time']])
        #oil_forecast=2.72**regr.predict(np_FcstTime)#This is the same as the following
        if forecast_type=='last_date':
            oil_forecast=2.72**(regr_type.coef_[0]*np_FcstTime+regr_type.intercept_[0])
        if forecast_type=='end_fit':
            oil_forecast=2.72**(regr_type.coef_[0]*np_FcstTime+regr_type.intercept_[0])
        if forecast_type=='last_point':
            #oil_forecast=Qi*2.72**(regr_type.coef_[0]*np_FcstTime)
            oil_forecast=2.72**(regr_type.coef_[0]*np_FcstTime+np.log(Qi))
        forecast[primary_product+'Rate']=oil_forecast
        return forecast, forecast_dates
    
    ###########################################
    #Calculate Type Well based on EUR forecasts
    ###########################################
    def typewell(self,data):
        #Run Monte-Carlo simulation: select 100000 times randomly 5 wells and calculate
        #average EUR, stack it in a list
    
        iterations=100000
        rndavg=[]
        no_select=10
        for i in range(iterations):
            rndavg.append(np.mean(random.sample(data.EUR,self.config.window_size)))
    
        #Create numpy array from list
        mean_sim=np.asarray(rndavg)
        #Create dataframe from numpy array
        pdmean_sim=pd.Series(mean_sim)
    
        #Find P90 value for EUR from averaged chart
        p90=pdmean_sim.describe(percentiles=[.1])[4]
        log("P90= ", p90)
    
        #Plot reversed cumulative Distribution Function
        n_bins = 10
        fig, ax = plt.subplots(figsize=(8, 4))
        #n- frequency, bins - values ranges
        n, bins, patches = ax.hist(data.EUR, n_bins, density=True, histtype='step',\
                                   cumulative=-1, label='Empirical')
        # add a 'best fit' line
        y = ((1 / (np.sqrt(2 * np.pi) * data['EUR'].std())) *
             np.exp(-0.5 * (1 /data['EUR'].std()  * (bins - data['EUR'].mean()))**2))
        y = y.cumsum()
        y /= y[-1]
        y=1-y
    
        ax.plot(bins, y, 'k--', linewidth=1.5, label='Empirical line')
    
        # Overlay an averaged hystogram
        ax.hist(mean_sim, n_bins, density=True, histtype='step',
                                   cumulative=-1, label='Simulated')
        """
        # add a 'best fit' line
        y = ((1 / (np.sqrt(2 * np.pi) * mean_sim.std())) *
             np.exp(-0.5 * (1 /mean_sim.std()  * (bins - mean_sim.mean()))**2))
        y = y.cumsum()
        y /= y[-1]
        y=1-y
    
        ax.plot(bins, y, 'k--', linewidth=1.5, label='Simulated line')
        """
        ax.grid(True)
        ax.legend(loc='right')
        ax.set_title('Cumulative step histograms')
        ax.set_xlabel('EUR (Mm3)')
        ax.set_ylabel('Likelihood of occurrence')
        ax.axis([min(data.EUR),max(data.EUR),1,0])
        ax.set_yticks([0.1,0.5,0.9], minor=False)
    
        self.show_plot(plt)
    
        #Run Monte-Carlo simulation: select 1000 times randomly 5 wells and 
        #for each well with EUR>P90 count number of occurances
        #Add a count occurances column Tally to eur dataframe
        data['Tally']=0
        #Select randomly 5 wells 1000 times
        iterations=1000
        for i in range(iterations):
            #This is a list of EUR values of 5: [202400L, 28809L, 3798L, 7010L, 35110L]
            rnd_sel=random.sample(data.EUR,self.config.window_size)
            for j in range(len(rnd_sel)):
                if rnd_sel[j] > p90:
                    #Find index of the value
                    idx=data[data.EUR==rnd_sel[j]].index
                    #Increment tally value by 1
                    tl=data[data.EUR==rnd_sel[j]].Tally+1
                    data.loc[idx,'Tally']=tl
                               
        #Calculate weighting factors for each well
        data['TWeight']=data['Tally']/data.Tally.sum()
        log(data)
        return data
    
    
    
    #===============================================================================
    # 
    #===============================================================================
    def process(self):
        """
            @info: Run algorithm
        """
        if self.is_terminated:
            log("Terminated")
            return
        # Read  production for selected wells
        SELECT=SQL_PROD.format(
                                FILTER_WELLS=u"AND vpr.WELL_ID in ('{}')".format("','".join(map(str,self.WELLS))) if self.WELLS is not None and len(self.WELLS)>0 else ''
                                ,FILTER_GRP=u"AND grps.GRP_CODE in ('{}')".format(self.REG)
                               )
        log(SELECT)
        df=psql.read_sql(sql=SELECT, con= self.conn)
        fill_nan={}
        for c in [cCOND_VOL
                  ,cOIL_VOL
                  ,cNAT_GAS
                  ,cWAT_VOL
                   #,'CONDENSATE_MASS','OIL_MASS'
                   # ,'WATER_MASS','WATER_INJ_VOL'
                   # ,'FREE_GAS_VOL','DIS_GAS_VOL'
                   # ,'INJ_WATER','INJ_GAS','CRUDE_OIL','PRODUCED_WATER'
                   ]:
            fill_nan[c]=0
        df.fillna(value=fill_nan,inplace=True)
        df.to_clipboard()
        df['Hours']=df[cPROD_DAYS]*24
        
        #=====================
        #Set Reservoir Group  datatframe
        reg_dataframe=df.loc[df[cREG]==self.REG]
        #Create list of wells in REG
        wlist=reg_dataframe[cWELL].unique()
        
        #Perform initial QC and data selection
        plt.figure(1, figsize=(12,8))
        for well in wlist:
            qc=reg_dataframe.loc[reg_dataframe['WELL_ID']==well]
            qc.set_index('PROD_START_TIME',drop=False, inplace=True)
            qc['Rate']=qc[self.reservoir_prop.primary_product]/(qc['Hours'].loc[qc['Hours']>0])*24/self.reservoir_prop.primdiv
            plt.plot(qc.index,qc.Rate, linewidth=1, label=well)
        plt.ylabel(self.reservoir_prop.primary_product+' rate'+self.reservoir_prop.units+'/D')
        plt.grid(True)
        plt.yscale('log')
        plt.legend(loc='best')
        plt.title('Reservoir: '+self.REG)
        self.show_plot(plt)
        
        #Calculate forecasts workflow well by well
        wcount=0
        eur_list=[]
        for well in wlist:
            log( '\n'*2)
            log( '='*40)
            log( 'Processing well '+well )
            log( '='*40)
            
            try:
                if self.is_terminated:break
                oil=reg_dataframe.loc[reg_dataframe[cWELL]==well]
                oil.set_index(cPROD_START_TIME,drop=False, inplace=True)
                #Calculate oil rate m3/D to be more precise
                oil['Rate']=oil[self.reservoir_prop.primary_product]/(oil['Hours'].loc[oil['Hours']>0])*24/self.reservoir_prop.primdiv
                #Convert index to cumulative days time
                oil['Time']=oil.index.days_in_month*self.config.perhour*self.config.persecond
                oil['Time']=oil['Time'].cumsum()
                oil['CumOil']=oil[self.reservoir_prop.primary_product].cumsum()/self.reservoir_prop.primdiv
                oil['wc']=oil[cWAT_VOL]/(oil[self.reservoir_prop.primary_product]+oil[cWAT_VOL])
                #Calculate rate for the secondary product
                oil['Rate2']=oil[self.reservoir_prop.secondary_product]/(oil['Hours'].loc[oil['Hours']>0])*24/self.reservoir_prop.secdiv
                oil['secondRatio']=oil['Rate2']/oil['Rate']
                #Calculate 1+WOR
                oil['Watrate']=(oil[cWAT_VOL].loc[oil[cWAT_VOL]>0])/(oil['Hours'].loc[oil['Hours']>0])*24
                oil['WOR']=1+oil['Watrate'].loc[oil['Watrate']>0]/oil['Rate'].loc[oil['Rate']>0]
                   
            
                #######################################
                #Call fitselect function with oil rate
                #######################################
                prd='Rate'
                #Add row counter
                data=oil
                data['rownum']=1
                data.rownum=data.rownum.cumsum()
                maxrate=data.loc[data.Rate == data.Rate.max()]
                
                if len(maxrate)>0:
                    dshift=maxrate['rownum'].iloc[0]-1
                else:
                    dshift=0
                
                #dshift=0
                #log('dshift= '+str(dshift))
                data=oil[dshift:]
                stream=self.fitselect(data,self.config.threshold,prd)
                wor=False
                stream=stream[stream['Rate']>0]
                #log(stream)
                #Call regression function for log rate vs time and check for positive slope
                if len(stream) > 2:
                    oil_fit, regr=self.linregress(stream, wor)
                else:
                    log( '=================================')
                    log( 'Well '+well+' has no valid points')
                    log( '=================================')
                    continue
                
                #Find time for start and end of stream
                iT=oil.loc[stream.index[0],'Time']
                eT=oil.loc[stream.index[len(stream)-1],'Time']
                log('iT= ', iT)
                log('eT=', eT)
                
                while regr.coef_[0][0] > 0:
                    if len(stream) > 0:
                        dshift=dshift+len(stream)
                        #dshift=len(oil.loc[stream.index[len(stream)-1]:])
                        #dshift=dshift+1
                        data=oil[dshift:]
                        stream=self.fitselect(data,self.config.threshold,prd)
                    else:
                        dshift=dshift+1
                        data=oil[dshift:]
                        stream=self.fitselect(data,self.config.threshold,prd)
                    if dshift > len(oil)-2:
                        log( '=================================')
                        log( 'Well '+well+' has no valid points')
                        log( '=================================')
                        break
                        
                    #print 'dshift= ', dshift, len(stream), len(data), regr.coef_[0][0]
                    #stream=fitselect(data,threshold,prd)
                    #print stream
                    #Call regression function for log rate vs time
                    stream=stream[stream['Rate']>0]
                    if len(stream) >= 2:
                        oil_fit, regr=self.linregress(stream, wor)
                    else:
                        continue
                    
                #Call regression function for log rate vs time with negative slope
                if len(stream) <= 2:
                    log( '=================================')
                    log( 'Well '+well+' stream <=2(fitselect function with oil rate), skeeped')
                    log( '=================================')
                    continue
                stream=stream[stream['Rate']>0]
                oil_fit, regr=self.linregress(stream, wor)
                """
                print 'Fitted curve parameters:'
                print '-------------------------'
                #Nominal decline rate take 12 months, data are monthly sampled
                ndr=(oil_fit[0][0]-oil_fit[1][0])/oil_fit[0][0]*100*12
                print 'Nominal decline rate, %: ', ndr
            
                #Effective decline rate
                #edr=regr.coef_[0][0]
                edr=100*(1-2.72**(ndr/-100))
                #print 'Effective decline rate, %: ', edr*perhour*persecond*30*12*-100
                print 'Effective decline rate, %: ', edr
            
                #Initial rate
                Qi=oil_fit[0][0]
                print 'Initial rate, '+units, Qi
            
                #Initial cumulative: from start of production to start of fitted curve
                iC=(2.72**regr.intercept_[0]-oil_fit[0][0])/regr.coef_[0][0]*-1
                #iC=oil['CumOil'].iloc[len(oil)-1]
                print 'Initial cumulative, m3:', iC, units
            
                #Technical reserves: iC+reserves from start of fitted curve
                Tr=(2.72**regr.intercept_[0]-MinRate)/regr.coef_[0][0]*-1
                #Tr=oil['CumOil'].iloc[len(oil)-1]+oil_forecast.sum()
                print 'Technical reserves: ',Tr, units
                print '======================'
                """
                ##########################################################
                #Call fitselect function for WOR. Use cumulative oil chart
                ##########################################################
                if oil[cWAT_VOL].max() > 0:
                    prd='WOR'
                    wor=True
                    wor_workflow=True
                    #Find max value among last 10 points to avoid decreasing patterns
                    maxval=0
                    if len(oil) > 10:
                        for j in range(10):
                            if maxval < oil[prd].iloc[len(oil)-(j+1)]:
                                maxval=oil[prd].iloc[len(oil)-(j+1)]
                            else:
                                break
                            #print ('maxval= '), maxval, j
                        oil_temp=oil[len(oil)-(2+j):len(oil)-j].fillna(value=0)
                        i=0
                        #Select and regress
                        while i < len(oil):
                            if len(oil_temp)>=4:
                                #Call last selection
                                lfit, wor_regr=self.lastselect(oil_temp,prd,wor)
                                #Predict Rate on full time range
                                np_Cum=np.array(oil.loc[:,['CumOil']])
                                if not wor:
                                    oil_predict=2.72**wor_regr.predict(np_Cum)
                                if wor:
                                    wor_predict=wor_regr.predict(np_Cum)                        
                                break
                            else: #shift for one point, leaving maxval point untached
                                oil_temp=oil[len(oil)-(2+j+i):len(oil)-(1+j+i)]
                                oil_temp=oil_temp.append(oil[len(oil)-(1+j):len(oil)-j])
                                i=i+1
                                
                                #Call last selection
                                oil_temp=oil_temp[oil_temp['WOR']>0]
                                if len(oil_temp)>1:
                                    lfit, wor_regr=self.lastselect(oil_temp,prd,wor)
                                else:
                                    continue
                                #Predict Rate on full time range
                                np_Cum=np.array(oil.loc[:,['CumOil']])
                                if not wor:
                                    oil_predict=2.72**wor_regr.predict(np_Cum)
                                    #Count number of points near the line
                                    oil_temp=oil[abs(oil[prd]-oil_predict.reshape(len(oil_predict)))<oil[prd].std()]
                                if wor:
                                    wor_predict=wor_regr.predict(np_Cum)
                                    #Count number of points near the line
                                    oil_temp=oil[abs(oil[prd]-wor_predict.reshape(len(wor_predict)))<oil[prd].std()]
                                    #Select points within one year from pairs
                                    #oil_temp=oil_temp[oil_temp['Time'].diff()<365]
                        #print (oil_temp)
                        if len(oil_temp)<3:
                            wor_workflow=False
                            log( '===========================')
                            log( 'WOR workflow is not applied')
                else:
                    wor_workflow=False
                    log( '===========================')
                    log( 'WOR workflow is not applied')
                
                
            
                regr_type=regr
                ############################
                #Apply forecast at Last date
                ############################
                #Create forecast dataframe, start forecast on the following year from last production
                forecast_start=str(oil.index.max().year+1)
                data=oil
                forecast_type='last_date'
                Qi=1
                #forecast(data, regr_type, forecast_type, forecast_start, forecast_end, Qi=1,Intercept=0)
                ld_forecast, forecast_dates=self.forecast(data, self.reservoir_prop.primary_product, regr_type, forecast_type, forecast_start, self.config.forecast_end, Qi, eT)
            
                ##################################################
                #Apply forecast at Last point: Rate is No 4 column
                ##################################################
                #forecast_start=str(oil.index.max().year+1)
                forecast_start=str(oil.index.max())
                forecast_type='last_point'
                #Qi=oil.iat[len(oil)-1,4]
                Qi=oil['Rate'].iloc[len(oil)-1]
                lp_forecast, forecast_dates=self.forecast(oil, self.reservoir_prop.primary_product, regr_type, forecast_type, forecast_start,self.config.forecast_end, Qi, eT)
                #Drop first row as it is equals to historical data
                lp_forecast=lp_forecast[1:len(lp_forecast)]
                log( '==============================='                   )
                log( 'Last point forecast parameters for well:',well, self.REG)
                log( '-------------------------'                         )
                #Nominal decline rate take 12 months, data are monthly sampled
                #ndr=(oil_fit[0][0]-oil_fit[1][0])/oil_fit[0][0]*100*12
                ndr=(lp_forecast[self.reservoir_prop.primary_product+'Rate'].iloc[0]-lp_forecast[self.reservoir_prop.primary_product+'Rate'].iloc[1])/lp_forecast[self.reservoir_prop.primary_product+'Rate'].iloc[0]*12*100
                log( 'Nominal decline rate, %: ', ndr)
            
                #Effective decline rate
                #edr=regr.coef_[0][0]
                edr=100*(1-2.72**(ndr/-100))
                #print 'Effective decline rate, %: ', edr*perhour*persecond*30*12*-100
                log('Effective decline rate, %: ', edr)
            
                #Initial rate
                Qi=lp_forecast[self.reservoir_prop.primary_product+'Rate'].iloc[0]
                log('Initial rate, '+self.reservoir_prop.units, Qi)
            
                #Initial cumulative: from start of production to start of forecast
                #iC=(2.72**regr.intercept_[0]-Qi)/regr.coef_[0][0]*-1
                iC=oil['CumOil'].iloc[len(oil)-1]
                log( 'Cumulative to Date, ', iC, self.reservoir_prop.units)
            
                #Technical reserves: iC+reserves from start of fitted curve
                #lp_Tr=(2.72**regr.intercept_[0]-MinRate)/regr.coef_[0][0]*-1
            
                #Remaining reserves
                #rR=lp_Tr-iC
                #iC=oil['CumOil'].iloc[len(oil)-1]
                lp_forecast['CumOil']=lp_forecast[self.reservoir_prop.primary_product+'Rate']*lp_forecast.index.days_in_month*self.config.perhour*self.config.persecond
                lp_forecast['CumOil']=lp_forecast['CumOil'].cumsum()
                rR=lp_forecast['CumOil'].iloc[len(lp_forecast)-1]
                log( 'Remaining reserves,: ', rR, self.reservoir_prop.units)
                lp_Tr=iC+rR
                log( 'Estimated ultimate recovery: ',lp_Tr, self.reservoir_prop.units)
                log( '======================')
                #For gas producers calculate RF of gas and RF of condencate. CumOil in # 6 column
                if self.reservoir_prop.calcRF:
                    oil['GasRF']=oil['CumOil']/lp_Tr
                    oil['CumCond']=oil[self.reservoir_prop.secondary_product].cumsum()#Calculate cumulative condenat
                    Cond_Tr=lp_Tr*self.reservoir_prop.cond_RFi
                    oil['CondRF']=oil['CumCond']/Cond_Tr
                    log( 'Condensate Initial reserves: ', Cond_Tr/1000, self.reservoir_prop.units)
                    #Define non-linear regression function
                    def nonlinear(x, a, b, c):
                        return a*x**2+b*x+c
                    def linear(x,a,b):
                        return a*x+b
                    #Call non-linear regression function for last 10 points
                    #popt, pcov = curve_fit(nonlinear, oil['GasRF'].iloc[len(oil)-10:len(oil)], oil['CondRF'].iloc[len(oil)-10:len(oil)])
                    #Call linear regression for last 10 points
                    popt, pcov = curve_fit(linear, oil['GasRF'].iloc[len(oil)-10:len(oil)], oil['CondRF'].iloc[len(oil)-10:len(oil)])
                    #Calculate future Gas RF
                    #Calculate monthly volumes from rates
                    lp_forecast[self.reservoir_prop.primary_product]=lp_forecast[self.reservoir_prop.primary_product+'Rate']*lp_forecast.index.days_in_month*self.config.perhour*self.config.persecond
                    #Save first GAS_VOL value, culumn No 3:
                    Gi=lp_forecast.iat[0,3]
                    #Add cumulative gas in order to calculate gas RF
                    lp_forecast.iat[0,3]=lp_forecast.iat[0,3]+oil['CumOil'].iloc[len(oil)-1]
                    lp_forecast[self.reservoir_prop.primary_product+'RF']=lp_forecast[self.reservoir_prop.primary_product].cumsum()/lp_Tr
                    #Put inital gas volume back
                    lp_forecast.iat[0,3]=Gi
                    #Calculate forecast using non-linear regression
                    """
                    lp_forecast[secondary_product+'RF']=popt[0]*lp_forecast[primary_product+'RF']\
                                                         **2+popt[1]*lp_forecast[primary_product+'RF']\
                                                         +popt[2]
                    """
                    #Calculate forecast using linear regression
                    lp_forecast[self.reservoir_prop.secondary_product+'RF']=popt[0]*lp_forecast[self.reservoir_prop.primary_product+'RF']+popt[1]
                    lp_forecast['CondCUM']=lp_forecast[self.reservoir_prop.secondary_product+'RF']*Cond_Tr
                    #Differentiate cumsum back to real values and set rate at start of forecast
                    lp_forecast[self.reservoir_prop.secondary_product+'Rate']=lp_forecast['CondCUM'].diff()/(lp_forecast.index.days_in_month*self.config.perhour*self.config.persecond)
                    lp_forecast[self.reservoir_prop.secondary_product+'Rate']=lp_forecast[self.reservoir_prop.secondary_product+'Rate'].fillna(lp_forecast[self.reservoir_prop.secondary_product+'Rate'].iloc[1]-lp_forecast[self.reservoir_prop.secondary_product+'Rate'].iloc[1]*regr.coef_[0][0])
                    lp_forecast[self.reservoir_prop.secondary_product]=lp_forecast[self.reservoir_prop.secondary_product+'Rate']*lp_forecast.index.days_in_month*self.config.perhour*self.config.persecond
                    #lp_forecast['Cond']=lp_forecast['CondCUM'].diff().fillna(lp_forecast['CondCUM'].iloc[0]-oil['CumCond'].iloc[len(oil)-2])
                    
                    fig=plt.figure(2)
                    fig.canvas.mpl_connect('button_press_event', self.on_mouse_press)
                    fig.canvas.mpl_connect('key_press_event',    self.on_key_press)
                    fig.canvas.mpl_connect('close_event',        self.on_plt_close)
                    
                    plt.plot(lp_forecast[self.reservoir_prop.primary_product+'RF'],lp_forecast[self.reservoir_prop.secondary_product+'RF'], 'y--',)
                    plt.plot(oil.GasRF, oil.CondRF, color='red', linewidth=1, label='RFcond/RFgas' )
                    plt.ylabel(self.reservoir_prop.secondary_product+'RF')
                    plt.xlabel(self.reservoir_prop.primary_product+'RF')
            
                    #Calculate secondary product
                    lp_forecast['LPG']=lp_forecast[self.reservoir_prop.primary_product]*self.reservoir_prop.propan_fraction*self.reservoir_prop.propan_dens/self.reservoir_prop.propan_liq_dens*self.reservoir_prop.BOE
                    lp_forecast['Sales Gas']=lp_forecast[self.reservoir_prop.primary_product]*(1-self.reservoir_prop.propan_fraction)*self.reservoir_prop.WetGasShrink
                   
                    
                ######################################
                #Apply forecast at end of fitted curve
                ######################################
                forecast_start=str(stream.index.max().year+1)
                data=oil
                forecast_type='end_fit'
                Qi=1
                fc_forecast, fc_forecast_dates=self.forecast(data, self.reservoir_prop.primary_product, regr_type, forecast_type, forecast_start, self.config.forecast_end, Qi, eT)
            
                #########################################
                #Call regression function for cumulative
                #########################################
                if len(stream) <= 2:
                    log( '=================================')
                    log( 'Well '+well+' stream <=2 (regression function for cumulative), skeeped')
                    log( '=================================')
                    continue

                cumoil_fit, cumregr=self.cumlinregress(stream)
                log( '========================='                                   )
                log( 'Fitted curve paramenters for Rate vs Cumulative:', well, self.REG )
                log( '-------------------------'                                   )
            
                #Decline rate by cumulative plot
                log( 'Decline rate from cumulative, %: ', cumregr.coef_[0][0]*365.25*-100)
            
                #Initial rate
                cumQi=cumoil_fit[0][0]
                log('Initial rate,:', cumQi, self.reservoir_prop.units+'/D')
            
                #Initial cumulative: from start of production to start of fitted curve
                cum_iC=(regr.intercept_[0]-cumoil_fit[0][0])/cumregr.coef_[0][0]
                log('Cumulative to date,:', cum_iC, self.reservoir_prop.units)
            
                #Technical reserves: iC+reserves from start of fitted curve
                cum_Tr=(cumregr.intercept_[0]-self.config.MinRate)/cumregr.coef_[0][0]
                log('Estimated ultimate recovery: ',cum_Tr*-1, self.reservoir_prop.units)
                log('======================')
            
                ########################################################################################
                #Calculate secondary products for oil - secondary product for gas are already calculated
                ########################################################################################
                if not self.reservoir_prop.calcRF:
                    lp_forecast[self.reservoir_prop.primary_product]=lp_forecast[self.reservoir_prop.primary_product+'Rate']*lp_forecast.index.days_in_month*self.config.perhour*self.config.persecond
                    lp_forecast[self.reservoir_prop.secondary_product]=lp_forecast[self.reservoir_prop.primary_product]*self.reservoir_prop.GOR
                    lp_forecast['Sales Gas']=lp_forecast[self.reservoir_prop.secondary_product]*(1-self.reservoir_prop.propan_fraction)
                    lp_forecast['LPG']=lp_forecast[self.reservoir_prop.secondary_product]*self.reservoir_prop.propan_fraction
                
                #Apply WOR forecast, need to create CumOil forecast X axis
                if wor_workflow:
                    wor_forecast=lp_forecast.copy()
                    wor_forecast['CumOil']=wor_forecast[self.reservoir_prop.primary_product]
                    if not self.reservoir_prop.calcRF: #CumOil is in column 2
                        wor_forecast.iat[0,2]=oil['CumOil'].max()-wor_forecast.iat[0,2]
                    elif self.reservoir_prop.calcRF: #CumOil is in column 2 - need to check
                        wor_forecast.iat[0,2]=oil['CumOil'].max()-wor_forecast.iat[0,2]
                    wor_forecast['CumOil']=wor_forecast['CumOil'].cumsum()
                    
                    np_Cum=np.array(wor_forecast.loc[:,['CumOil']])
                    wor_predict1=wor_regr.predict(np_Cum)
                    wor_forecast['WOR']=wor_predict1
                    log( '1+WOR curve paramenters:'                        )
                    log( '-------------------------'                       )
                    log( 'WOR regr.coef= ', wor_regr.coef_[0][0]           )
                    log( 'WORi=', wor_forecast.WOR[0]                      )
                    log( 'WORfin=', wor_forecast.WOR[len(wor_forecast)-1]  )
                    
                    #Calculate monthly WC to apply limits if regr.coef > 0
                    if wor_regr.coef_[0][0] > 0:
                        lp_forecast['WATER']=lp_forecast[self.reservoir_prop.primary_product]*(wor_forecast.WOR-1)
                        lp_forecast['WOR']=wor_predict1
                        lp_forecast['CumOil']=wor_forecast['CumOil']
                        if not self.reservoir_prop.calcRF: #Liquid is oil+WATER
                            lp_forecast['WC']=lp_forecast['WATER']/(lp_forecast['WATER']+lp_forecast[self.reservoir_prop.primary_product])
                            lp_forecast['LiqRate']=lp_forecast[self.reservoir_prop.primary_product+'Rate']*lp_forecast['WOR']
                        elif self.reservoir_prop.calcRF: #Liquid is condensate+WATER
                            lp_forecast['WC']=lp_forecast['WATER']/(lp_forecast['WATER']+lp_forecast[self.reservoir_prop.secondary_product])
                            lp_forecast['LiqRate']=lp_forecast[self.reservoir_prop.secondary_product+'Rate']*lp_forecast['WOR']
                        #Cut lp_forecast by WC limit
                        lp_forecast=lp_forecast[lp_forecast['WC'] < self.config.MaxWC]
                    else:
                        wor_workflow=False
                
                #Export last point forecast to Excel
                report_forecast=pd.DataFrame(index=forecast_dates)
                report_forecast[self.reservoir_prop.primary_product]=lp_forecast[self.reservoir_prop.primary_product]
                report_forecast[self.reservoir_prop.secondary_product]=lp_forecast[self.reservoir_prop.secondary_product]
                report_forecast['Sales Gas']=lp_forecast['Sales Gas']
                report_forecast['LPG']=lp_forecast['LPG']
                if wor_workflow:
                    report_forecast['WATER']=lp_forecast['WATER']
            
                out_f=os.path.join(out_dir,well+'_forecast_'+self.REG+'.xlsx')
                report_forecast=report_forecast.resample('Y').sum()
                
                if wor_workflow:
                    if not self.reservoir_prop.calcRF: #Liquid is oil+WATER
                        report_forecast['WC']=report_forecast['WATER']/(report_forecast['WATER']+report_forecast[self.reservoir_prop.primary_product])
                        report_forecast['LiqRate']=lp_forecast[self.reservoir_prop.primary_product+'Rate']*lp_forecast['WOR']
                    elif self.reservoir_prop.calcRF: #Liquid is condensate+WATER
                        report_forecast['WC']=report_forecast['WATER']/(report_forecast['WATER']+report_forecast[self.reservoir_prop.secondary_product])
                        report_forecast['LiqRate']=lp_forecast[self.reservoir_prop.secondary_product+'Rate']*lp_forecast['WOR']
                
                report_forecast.index=report_forecast.index.year
                report_forecast.transpose().to_excel(out_f)
            
                # Plot outputs
                fig=plt.figure(1, figsize=(12,8))
                fig.canvas.mpl_connect('button_press_event', self.on_mouse_press)
                fig.canvas.mpl_connect('key_press_event',    self.on_key_press)
                fig.canvas.mpl_connect('close_event',        self.on_plt_close)
                #plt.subplot(221) #Ratios vs Time
                plt.subplot2grid((3,2),(2,0))
                plt.plot(oil.index,oil.wc, color='blue', linewidth=1,label='WATER Cut')
                plt.plot(oil.index, oil.secondRatio, color='green', label=self.reservoir_prop.secondary_product[0]+'/'+self.reservoir_prop.primary_product[0]+' ratio')
                plt.plot(oil.index, oil.WOR, color='black', linewidth=1, label='1+WOR')
                if wor_workflow:
                    plt.plot(lp_forecast.index, lp_forecast['WOR'], 'b--', linewidth=1, label='1+WOR preidct')
                    
                plt.xlabel('Time')
                plt.legend(loc='best')
                #plt.subplot(222) #Ratios vs cumulative
                plt.subplot2grid((3,2),(2,1))
                plt.plot(oil['CumOil'], oil.wc, color='blue', linewidth=1,label='WATER Cut')
                plt.plot(oil['CumOil'], oil.secondRatio, color='green', label=self.reservoir_prop.secondary_product[0]+'/'+self.reservoir_prop.primary_product[0]+' ratio')
                plt.plot(oil['CumOil'], oil.WOR, color='black', linewidth=1, label='1+WOR')
                if wor_workflow:
                    plt.plot(oil_temp['CumOil'], lfit, color='red', linewidth=1, label='1+WOR selection')
                    plt.plot(lp_forecast['CumOil'], lp_forecast['WOR'], 'b--', linewidth=1, label='1+WOR preidct')
                plt.xlabel('Cum. '+self.reservoir_prop.primary_product+self.reservoir_prop.units)
                plt.legend(loc='best')
            
                #plt.subplot(223) #Log Rates vs Time
                plt.subplot2grid((3,2),(0,0),rowspan=2)
                if self.config.LastPointFcst:
                    plt.plot(lp_forecast.index, lp_forecast[self.reservoir_prop.primary_product+'Rate'], 'b--', linewidth=1,label=self.reservoir_prop.primary_product+'Last point forecast')
                    if self.reservoir_prop.calcRF:
                        plt.plot(lp_forecast.index, lp_forecast[self.reservoir_prop.secondary_product+'Rate'], 'y--', linewidth=1, label='Condensate forecast')
                if self.config.EndFitFcst:
                    plt.plot(fc_forecast.index, fc_forecast[self.reservoir_prop.primary_product+'Rate'], color='brown', linewidth=1,label='End of fit forecast')
                if self.config.LastDateFcst:
                    plt.plot(ld_forecast.index, ld_forecast[self.reservoir_prop.primary_product+'Rate'], color='black', linewidth=1,label='Last date forecast' )
                plt.plot(oil.index,oil.Rate, color='black', linewidth=1, label=self.reservoir_prop.primary_product+' rate')
                plt.plot(oil.index,oil.Rate2, color='yellow', linewidth=1, label=self.reservoir_prop.secondary_product+' rate')
                plt.plot(stream.index, oil_fit, color='red', linewidth=1,label='Fitted curve' )
                plt.plot(stream.index, stream.Rate, 'r--', linewidth=2,label='Selected points' )
                #if wor_workflow:
                #    plt.plot(oil_temp.index, wor_stream['OilWOR'], 'r--', linewidth=1,label='1+WOR Fit' )
                plt.ylabel(self.reservoir_prop.primary_product+' rate'+self.reservoir_prop.units+'/D')
                plt.yscale('log')
                plt.legend(loc='best')
                plt.title('WELL: '+well+' Reservoir: '+self.REG)
            
                #plt.subplot(224) #Rates vs Cumulative
                plt.subplot2grid((3,2),(0,1),rowspan=2)
                plt.plot(oil['CumOil'], oil.Rate, color='black', linewidth=1, label=self.reservoir_prop.primary_product+' rate')
                plt.plot(stream['CumOil'], cumoil_fit, color='red', linewidth=1,label='Fitted curve' )
            
                plt.legend(loc='best')
            
                self.show_plot(plt)
            
                #Accumulate both historical and forecast rates in a dataframe
                if wcount == 0 :
                    if len(lp_forecast)>0:
                        comb_dates=pd.date_range(reg_dataframe[cPROD_START_TIME].min(),lp_forecast.index.max(),freq='Y')
                        comb_oil=pd.DataFrame(index=comb_dates)
                        lp_forecast1=lp_forecast[self.reservoir_prop.primary_product+'Rate'].resample('Y').sum()
                        #Drop 1st year
                        lp_forecast1=lp_forecast1[1:len(lp_forecast1)]
                        comb_oil[well]=oil['Rate'].resample('Y').sum().append(lp_forecast1)
                        #comb_oil[well]=oil['Rate'].append(lp_forecast[primary_product+'Rate'])
                            
                else:
                    if len(lp_forecast)>0:
                        lp_forecast1=lp_forecast[self.reservoir_prop.primary_product+'Rate'].resample('Y').sum()
                        #Drop 1st year
                        lp_forecast1=lp_forecast1[1:len(lp_forecast1)]
                        comb_oil[well]=oil['Rate'].resample('Y').sum().append(lp_forecast1)
                        #comb_oil[well]=oil['Rate'].append(lp_forecast[primary_product+'Rate'])
                wcount=wcount+1
                #Append eur_list, skip wells without forecast to match comboil
                if len(lp_forecast)>0:
                    eur_list.append((well, lp_Tr))
            except Exception as e:
                log( '===========================')
                log( 'WARNING!!!')
                log( str(e))

                
        '''
            *******************************************
            TYPE WELL
            *******************************************
        '''
        if self.config.UseTypeWell and not self.is_terminated:
            #Create eur dataframe
            eur=pd.DataFrame(eur_list, columns=('WELL', 'EUR'))
            #log(eur)
            
            Tweight=self.typewell(eur)
            
            
            #Calculate type well profile
            comb_oil1=comb_oil.copy()
            comb_oil1['TypeWell']=0
            comb_oil1=comb_oil1.fillna(value=0)
            
            for i in range(len(Tweight)):
                if Tweight['TWeight'].iloc[i] > 0:
                    #log('Tweight='+Tweight['WELL'].iloc[i])
                    
                    comb_oil1['TypeWell']=comb_oil1['TypeWell']+comb_oil1[Tweight['WELL'].iloc[i]]*Tweight['TWeight'].iloc[i]
            
            
            
            #Final chart
            log( "SHOW FINAL GRAPH")
            plt.figure(3, figsize=(12,8))#All rates and forecasts vs Years
            for well in comb_oil1.columns:
                plt.plot(comb_oil1.index, comb_oil1[well], linewidth=1,label=well)
                pass
            plt.plot(comb_oil1.index, comb_oil1.TypeWell,'b--',label='Type Well') 
            plt.yscale('log')
            plt.ylabel(self.reservoir_prop.primary_product+' rate'+self.reservoir_prop.units+'/D')
            plt.legend(loc='best')
            plt.title('Historical and forecast rates for '+self.REG)
            self.show_plot(plt,block=True)
                    
            #Export last point forecast to Excel
            out_f=os.path.join(out_dir,'TypeWell_'+self.REG+'.xlsx')
            comb_oil1.index=comb_oil1.index.year
            comb_oil1.transpose().to_excel(out_f)
            log( "END")
        webbrowser.open(os.path.realpath(out_dir))
        pass

    
if __name__ == "__main__":
    log("!"*20,"Standalone")
    from tmp_TypeWell.oracleTools import connect_to_db,sqlExecuteWithResult

    #######################################################################################
    #REG='PK_kir'
    REG='T1g'
    #REG='T1o'
    #REG='T2'
    #REG='T3'
    #REG='D2gv(ad)'
    #REG='D2af-bs'
#     IS_STANDALONE=True
#     a=DCA()
#     a.process()
    log("WARNING!!!. Need V_PROD_RECORDS,V_PROD_RESPART_M2")
    pass
