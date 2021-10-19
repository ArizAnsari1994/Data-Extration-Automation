'''
@author: Ariz
'''
# from Utils.connectTelnet import *
from connectTelnet import *
import os
from datetime import datetime
import time
import sys
import threading
import re
import sys

if sys.version_info[0] < 3:
    from Queue import Queue
else:
    from queue import Queue


class cfmMepActivation:
    user = 'A1DTC16B'#'training'#
    pwd = 'Ciena@123'#'training'#
    poolSize = 20
    serverConfig = []
    date = None
    confFile = "qos.txt"
    vsDetailsQueue = Queue()
    unReachableIpQueue = Queue()

    # utilObj = UtilityClass()

    def __init__(self):
        self.listSize = 3
        self.date = datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S-%f')[:-3]

    def fetchData(self):
        self.vsDetailsQueue.put(["NE Name", "NE ip", "Ckt ID", "Sub-Port", "CIR", "PIR", "Vtag 1", "Vtag 2", "Vtag 3"])
        for poolList in self.serverConfig:
            # executor.submit(self.executeWorker, serverConf)
            # print('Starting new pool : ' + str(THREAD_POOL_SIZE))
            threadPoolList = []
            for poolItem in poolList:
                t = threading.Thread(target=self.executeWorker, args=(poolItem,))
                t.start()
                threadPoolList.append(t)
            for t in threadPoolList:
                t.join()
            print('pool Ends')
            self.writeDataToFile('serviceDiscovery', self.vsDetailsQueue)
            self.writeDataToFile('unReachableNodes', self.unReachableIpQueue)

    def readConfig(self):
        '''
        This method reads the config file and loads data in to python objects
        '''
        fd = open(self.confFile, 'r')
        eof = False
        while True:
            poolList = []
            for i in range(self.poolSize):
                line = fd.readline()
                if (line.strip() == ""):
                    eof = True
                    break
                neList = line.split(',')
                neDetailsList = []
                neDetailsList.append(neList[1].strip())
                neDetailsList.append(self.user)
                neDetailsList.append(self.pwd)
                neDetailsList.append(neList[2].strip())
                neDetailsList.append(neList[0].strip())  # node
                poolList.append(neDetailsList)
            self.serverConfig.append(poolList)
            if eof:
                break
        fd.close()
        print(str(self.serverConfig))

    def getNodeName(self, data):
        data = data.split("\n")
        data = data[-1]
        nodeName = data.split("*")[0]
        return nodeName

    def writeDataToFile(self, fileName, que):
        fd = open(fileName + '_' + self.date + '.csv', 'a')
        while not que.empty():
            d = que.get()
            fd.write((',').join(d) + '\n')

    def executeTelnetCommand(self, command, tel):
        rawData = tel.sndRcv("test", command)
        # print ("data -----------------\n" + rawData)
        # Here, We can log the output of all commands in a file
        return rawData

    def executeWorker(self, serverConf):
        # tel = connectTelnet.Telnet()
        tel = Telnet()
        try:
            retCode = tel.connect(serverConf[0], serverConf[1], serverConf[2])
            if retCode == 1:
                cir = pir = "None"
                if serverConf[3] in ['3930', '5160']:
                    cmd = "virtual-switch show"
                    data = self.executeTelnetCommand(cmd, tel)
                    data = data.split("PBT VIRTUAL SWITCH TABLE")[0]
                    data = data.split("\n")
                    vsList = []
                    for lines in data:
                        line = lines.split('|')
                        if len(line) == 7 and line[1].strip() != "Name":
                            line = line[1:-1]
                            if line[1].strip() == "vpls":
                                vsList.append(line[0].strip())
                    portDetail = {}
                    for vs in vsList:
                        cmd = "con sea str " + vs
                        data = self.executeTelnetCommand(cmd, tel)
                        for d in data.split("/n"):
                            if "traffic-profiling standard-profile create port" in d:
                                wordList = d.split(" ")
                                cirIndex = wordList.index("cir") + 1
                                pirIndex = wordList.index("pir") + 1
                                cir = wordList[cirIndex]
                                pir = wordList[pirIndex]

                        vscmd = "virtual-switch show vs " + vs
                        details = self.executeTelnetCommand(vscmd, tel)
                        details = details.split('\n')
                        vlan = []
                        port = ""
                        for detail in details:
                            # vlan=[]
                            detail = detail.split('|')
                            print(vs, " detail :", detail)
                            if len(detail) == 7 and detail[1].strip() != "Port":
                                detail = detail[1:-1]
                                port = str(detail[0].strip())
                                vlan.append(str(detail[1].strip()))
                                portDetail[port] = vlan

                        if len(vlan) != 0 and vlan[0] != '0':
                            detailList = []
                            detailList.append(serverConf[4])
                            detailList.append(serverConf[0])
                            detailList.append(vs.strip())
                            detailList.append(port)
                            detailList.append(cir)
                            detailList.append(pir)
                            detailList = detailList + vlan
                            print("DetailList : ", detailList)
                            self.vsDetailsQueue.put(detailList)
                            print("ZZZZZZZZZ" + str(self.vsDetailsQueue))
                        time.sleep(1)
                    # print(self.vsDetailsQueue)
                elif serverConf[3] in '8700':
                    cmd = 'conf sear str "virtual-switch interface attach sub-port"'
                    data = self.executeTelnetCommand(cmd, tel)
                    data = data.split("\n")[1:-1]
                    for line in data:
                        sp = vs = None
                        l = line.split(" ")
                        if "sub-port" in l:
                            indexsp = (l.index("sub-port") + 1)
                            sp = l[indexsp]
                            vtagcheck = self.executeTelnetCommand("con sea str " + sp, tel)
                            if "vtag-stack" not in vtagcheck:
                                continue
                            else:
                                if "vs" in l:
                                    indexvs = (l.index("vs") + 1)
                                    vs = (l[indexvs]).strip()
                                    cmd = "con sea str " + vs
                                    data = self.executeTelnetCommand(cmd, tel)
                                    for d in data.split("/n"):
                                        if "traffic-services metering meter-profile create" in d:
                                            wordList = d.split(" ")
                                            cirIndex = wordList.index("cir") + 1
                                            cir = wordList[cirIndex]
                                            if "pir" in d:
                                                pirIndex = wordList.index("pir") + 1
                                                pir = wordList[pirIndex]
                                            else:
                                                pir = cir

                                vtagdata = vtagcheck.split("\n")[1:-1]
                                vtag = []
                                for v in vtagdata:
                                    vl = v.split(" ")
                                    if "vtag-stack" in vl:
                                        indexvtag = (vl.index("vtag-stack") + 1)
                                        vtag.append(vl[indexvtag].strip())
                                    else:
                                        continue

                                detailList = []
                                detailList.append(serverConf[4])
                                detailList.append(serverConf[0])
                                detailList.append(vs)
                                detailList.append(sp)
                                detailList.append(cir)
                                detailList.append(pir)
                                detailList = detailList + vtag
                                self.vsDetailsQueue.put(detailList)
            else:
                ipList = []
                ipList.append(serverConf[0])
                self.unReachableIpQueue.put(ipList)
        finally:
            tel.disconnectNe('', '')


print('Starting EPT_VS script')
myObj = cfmMepActivation()
confFile = None
if len(sys.argv) > 1:
    confFile = sys.argv[1]
myObj.readConfig()
myObj.fetchData()
print('Ending EPT_VS script')
