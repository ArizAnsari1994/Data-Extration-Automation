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


class checkQOS():
    
    user='gss'
    pwd='pureethernet'
    poolSize = 3
    serverConfig = []
    date=None
    confFile="qos.txt"
    unReachableIpQueue = Queue()
    statsQueueOther = Queue()
    statsQueue8700 = Queue()
    throughputQueue8700 = Queue()
    throughputQueueOther = Queue()
    
    def __init__(self):
        self.listSize=3                
        self.date = datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S-%f')[:-3]
        self.statsQueueOther.put(["IP Address", "NE Type","Port", "Q ID", "Dropped Bytes", "Dropped Pkts", "Transmitted Bytes", "Transmitted Pkts"])
        self.statsQueue8700.put(["IP Address", "NE Type","Port", "Q ID", "Enqueue Bytes", "Enqueue Frames", "Dropped Bytes", "Dropped Frames"])
        self.throughputQueueOther.put(["IP Address", "NE Type", "Port", "Bit Rate (Tx)", "Bit Rate (Rx)", "Pkt Rate (Tx)", "Pkt Rate (Rx)"])
        self.throughputQueue8700.put(["IP Address", "NE Type", "Port", "Bit Rate (Tx)", "Bit Rate (Rx)"])
    
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
        self.writeDataToFile('statsQueueOther', self.statsQueueOther)   
        self.writeDataToFile('statsQueue8700', self.statsQueue8700)
        self.writeDataToFile('throughputQueue8700', self.throughputQueue8700)
        self.writeDataToFile('throughputQueueOther', self.throughputQueueOther)
                    
    
    def postCheck8700(self, tel, port):
        cmd1="pm clear pm-instance "+port
        self.executeTelnetCommand(cmd1, tel)
        cmd2="pm show pm-instance port_"+port
        data = self.executeTelnetCommand(cmd2, tel)
        qosData=[]
        data = (data.split('Frames'))[1]
        data = data.split("QUEUE")
        for line in data:
            portData=[]
            for d in line.split('\n'):
                rawList=d.split('|')
                if len(rawList) > 3:
                    if(rawList[1].strip() in ["Enqueue", "Dropped"]):
                        portData.append(re.sub('[,]', '', rawList[2]).strip())
                        portData.append(re.sub('[,]', '', rawList[3]).strip())
                else:
                    l = re.sub('[-+]', '', rawList[0])
                    if len(l.strip())==1:
                        qos=l.strip()
                        portData.append(port)
                        portData.append(qos)
            if len(portData)>0:
                qosData.append(portData)
                print(portData)
        cmd3 ="port show statistics active scale mega format bits"
        self.executeTelnetCommand(cmd3, tel)
        self.executeTelnetCommand(cmd3, tel)
        data3 = self.executeTelnetCommand(cmd3, tel)

        throughputData=[]
        for d in data3.split('\n'):
            rawList=d.split('|')
            if len(rawList) > 4 and rawList[2].strip() != 'Tx':
                portData=[]
                portData.append(rawList[1].strip().replace(",", ""))
                portData.append(rawList[2].strip().replace(",", ""))
                portData.append(rawList[3].strip().replace(",", ""))
                throughputData.append(portData)
        return qosData, throughputData
    
    def postCheckOther(self, tel, port):
        cmd1="traffic-services queuing egress-port-queue-group cl port %s st" %(port)
        self.executeTelnetCommand(cmd1, tel)
        cmd="traffic-services queuing egress-port-queue-group show port %s st" %(port)
        data = self.executeTelnetCommand(cmd, tel)
        qosData=[]
        for d in data.split('\n'):    
            rawList=d.split('|')
            if len(rawList) > 6 and rawList[1].strip() != 'Q ID':  
                portData=[]
                portData.append(port)
                portData.append(rawList[1].strip())
                portData.append(rawList[2].strip().replace(",", ""))
                portData.append(rawList[3].strip().replace(",", ""))
                portData.append(rawList[4].strip().replace(",", ""))
                portData.append(rawList[5].strip().replace(",", ""))
                qosData.append(portData)

        cmd3="po show throughput active"
        self.executeTelnetCommand(cmd3, tel)
        self.executeTelnetCommand(cmd3, tel)
        data3 = self.executeTelnetCommand(cmd3, tel)

        throughputData = []
        for d in data3.split('\n'):
            rawList = d.split('|')
            if len(rawList) > 5 and rawList[2].strip() != 'Tx':
                portData = []
                portData.append(rawList[1].strip().replace(",", ""))
                portData.append(rawList[2].strip().replace(",", ""))
                portData.append(rawList[3].strip().replace(",", ""))
                portData.append(rawList[4].strip().replace(",", ""))
                portData.append(rawList[5].strip().replace(",", ""))
                throughputData.append(portData)
        return qosData, throughputData
        
    
    def executeWorker(self, serverConf):                                 
        tel=connectTelnet.Telnet()
        retCode = tel.connect(serverConf[0],serverConf[1],serverConf[2])        
        if retCode == 1:       
            if serverConf[3] in '8700': 
                port = serverConf[4]
                port = port.split('/')
                port = ('_').join(port) 
                print("port:",port)   
                stats, throughput = self.postCheck8700(tel, port)
                for stat in stats:
                    itemList =[]
                    itemList.append(serverConf[0])
                    itemList.append(serverConf[3])
                    itemList = itemList + stat
                    print("Itemlist8700S:",itemList)
                    self.statsQueue8700.put(itemList)
                for data in throughput:
                    itemList=[]
                    itemList.append(serverConf[0])
                    itemList.append(serverConf[3])
                    itemList = itemList + data
                    print("Itemlist8700T:", itemList)
                    self.throughputQueue8700.put(itemList)

            elif serverConf[3] in ['3930','5160']: 
                port = serverConf[4] 
                print("port:",port)
                stats, throughput =self.postCheckOther(tel, port)
                for stat in stats:
                    itemList =[]
                    itemList.append(serverConf[0])
                    itemList.append(serverConf[3])
                    itemList = itemList + stat
                    print("ItemlistotherS:", itemList)
                    self.statsQueueOther.put(itemList)

                for data in throughput:
                    itemList=[]
                    itemList.append(serverConf[0])
                    itemList.append(serverConf[3])
                    itemList = itemList + data
                    print("ItemlistotherT:", itemList)
                    self.throughputQueueOther.put(itemList)
            tel.disconnectNe('','')            
        else:            
            ipList=[]
            ipList.append(serverConf[0])
            self.unReachableIpQueue.put(ipList)                      
        
print ('Starting Postcheck QOS script')
myObj=checkQOS()
if len(sys.argv) > 1:
    myObj.confFile=sys.argv[1]
myObj.readConfig()
myObj.fetchData()