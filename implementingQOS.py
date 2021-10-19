'''
@author: Ariz
'''
import connectTelnet
import os
from datetime import datetime
import time
import sys
import threading
import re
from Queue import Queue

class implementQOS:
    
    user='su'
    pwd='wwp'
    poolSize = 3
    serverConfig = []
    date=None
    confFile="qos.txt"
    unReachableIpQueue = Queue()
    statsQueueOther = Queue()
    statsQueue8700 = Queue()
    
    def __init__(self):
        self.listSize=3                
        self.date = datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S-%f')[:-3]
        self.statsQueueOther.put(["IP Address", "NE Type","Port", "Q ID", "Dropped Bytes", "Dropped Pkts", "Transmitted Bytes", "Transmitted Pkts"])
        self.statsQueue8700.put(["IP Address", "NE Type","Port", "Q ID", "Enqueue Bytes", "Enqueue Frames", "Dropped Bytes", "Dropped Frames"])
    
    
    def readConfig(self):
        '''
        This method reads the config file and loads data in to python objects        
        '''
        fd=open(self.confFile,'r')
        eof = False
        while True:
            poolList=[]
            for i  in range(self.listSize):                             
                line=fd.readline()
                if(line.strip() == ""):
                    eof = True
                    break                                         
                neList=line.split(',')                
                neDetailsList=[]
                neDetailsList.append(neList[1].strip())
                neDetailsList.append(self.user)
                neDetailsList.append(self.pwd) 
                neDetailsList.append(neList[2].strip())
                neDetailsList.append(neList[3].strip())#port number
                neDetailsList.append(neList[0].strip())#node
                poolList.append(neDetailsList)         
            self.serverConfig.append(poolList)
            if eof:
                break
        fd.close()
        print(str(self.serverConfig)) 
        
    def writeDataToFile(self, fileName, que):
        fd = open (fileName + '_' + self.date + '.csv', 'a')
        while not que.empty():
            d= que.get()
            fd.write((',').join(d) + '\n')
            
    def executeTelnetCommand(self,command, tel):             
        rawData=tel.sndRcv("test", command)
        #print ("data -----------------\n" + rawData)
        #Here, We can log the output of all commands in a file               
        return rawData
                      
    def fetchData(self):
        for poolList in self.serverConfig:
            #executor.submit(self.executeWorker, serverConf)
            print ('Starting new pool : ' + str(self.poolSize))
            threadPoolList=[]
            for poolItem in poolList:
                t = threading.Thread(target=self.executeWorker, args=(poolItem,))
                t.start()
                threadPoolList.append(t)
            for t in threadPoolList:
                t.join()
            print ('pool Ends')      
        self.writeDataToFile('unReachableNodes', self.unReachableIpQueue)
#         self.writeDataToFile('statsQueueOther', self.statsQueueOther)   
#         self.writeDataToFile('statsQueue8700', self.statsQueue8700)     
                    
    
    def implementQOS8700(self, tel, port):
        actualportnum = port
        port = port.split('/')
        port = ('_').join(port)   
        portid = port
        f = open('commands8700.txt', 'r')
        data=f.read()
        data =data.replace("PORT_NUMBER_ACTUAL", actualportnum)
        data =data.replace("PORT_ID", portid)
        #print("Data",data)
        for cmd in data.split('\n'):
            
            self.executeTelnetCommand(cmd, tel)

    def implementQOS3930(self, tel, port):
        f = open('commands3930.txt', 'r')
        data=f.read()
        data =data.replace("PORT_NUMBER", port)
        #print("Data",data)
        for cmd in data.split('\n'):
            
            self.executeTelnetCommand(cmd, tel)

    def implementQOS5160(self, tel, port):
        f = open('commands5160.txt', 'r')
        data=f.read()
        data =data.replace("PORT_NUMBER", port)
        #print("Data",data)
        for cmd in data.split('\n'):
            
            self.executeTelnetCommand(cmd, tel)
        
    
    def executeWorker(self, serverConf):                                 
        tel=connectTelnet.Telnet()
        retCode = tel.connect(serverConf[0],serverConf[1],serverConf[2])        
        if retCode == 1:       
            if serverConf[3] in '8700': 
                port = serverConf[4]
                self.implementQOS8700(tel, port) 
                 
            elif serverConf[3] in '3930': 
                port = serverConf[4] 
                self.implementQOS3930(tel, port) 
                                           
            elif serverConf[3] in '5160': 
                port = serverConf[4] 
                self.implementQOS5160(tel, port) 
                                             
            tel.disconnectNe('','')            
        else:            
            ipList=[]
            ipList.append(serverConf[0])
            self.unReachableIpQueue.put(ipList)                      
        
print ('Starting Implementing QOS script')
myObj=implementQOS()
if len(sys.argv) > 1:
    myObj.confFile=sys.argv[1]
myObj.readConfig()
myObj.fetchData()