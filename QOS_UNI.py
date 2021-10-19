'''
@author: Ariz
'''

#from Scripts import connectTelnet
import connectTelnet
from datetime import datetime
import threading
import sys
if sys.version_info[0] < 3:
    from Queue import Queue
else:
    from queue import Queue


class implementQOS:
    user = ''
    pwd = ''
    poolSize = 3
    serverConfig = []
    date = None
    confFile = "qos.txt"
    unReachableIpQueue = Queue()
    statsQueueOther = Queue()
    statsQueue8700 = Queue()
    postCheckStatus = Queue()
    postCheckStatus8700 = Queue()

    def __init__(self):
        self.listSize = 3
        self.date = datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S-%f')[:-3]

    def readConfig(self):
        '''
        This method reads the config file and loads data in to python objects
        '''
        fd = open(self.confFile, 'r')
        eof = False
        while True:
            poolList = []
            for i in range(self.listSize):
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
                neDetailsList.append(neList[3].strip())  # port number
                # neDetailsList.append(neList[0].strip())  # node name
                if len(neList) > 4:
                    neDetailsList.append(neList[4].strip())  # virtual circuit name
                    neDetailsList.append(neList[5:])  # vlans
                poolList.append(neDetailsList)
            self.serverConfig.append(poolList)
            if eof:
                break
        fd.close()
        print(str(self.serverConfig))

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

    def fetchData(self):
        self.postCheckStatus.put(["IP", "Port", "VsName", "VLAN", "QOS Status"])
        for poolList in self.serverConfig:
            # executor.submit(self.executeWorker, serverConf)
            print('Starting new pool : ' + str(self.poolSize))
            threadPoolList = []
            for poolItem in poolList:
                t = threading.Thread(target=self.executeWorker, args=(poolItem,))
                t.start()
                threadPoolList.append(t)
            for t in threadPoolList:
                t.join()
            print('pool Ends')
            self.writeDataToFile('unReachableNodes', self.unReachableIpQueue)
            self.writeDataToFile('postCheckQOSUNIStatus', self.postCheckStatus)


    def implementQOS8700(self, tel, ip, subport):
        # f = open('..//ConfData//unicommands8700.txt', 'r')
        f = open('unicommands8700.txt', 'r')
        data = f.read()
        data = data.replace("VS_NAME", subport)
        for cmd in data.split('\n'):
            self.executeTelnetCommand(cmd, tel)
            print("Commands 8700", cmd)
    #     resolved-cos-policy l3-dscp-mpls-tc-cos resolved-cos-profile DSCP-UNI-RCOS-P-1
        chechStr="resolved-cos-policy l3-dscp-mpls-tc-cos resolved-cos-profile DSCP-UNI-RCOS-P-1"
        postCheckCmd = "conf search str " + str(subport)
        postCheck = self.executeTelnetCommand(postCheckCmd, tel)
        # for line in postCheck.split("\n")[1:-1]:
        postCheck=postCheck.split("\n")[1:-1]
        postCheck=" ".join(postCheck)
        if chechStr in postCheck:
            postCheckDetail = []
            postCheckDetail.append(ip)
            postCheckDetail.append(subport)
            postCheckDetail.append(" ")
            postCheckDetail.append(" ")
            postCheckDetail.append("Success")
            self.postCheckStatus.put(postCheckDetail)
        else:
            postCheckDetail = []
            postCheckDetail.append(ip)
            postCheckDetail.append(subport)
            postCheckDetail.append(" ")
            postCheckDetail.append(" ")
            postCheckDetail.append("Fail")
            self.postCheckStatus.put(postCheckDetail)


    def implementQOS3930(self, tel, ip, port, vsname, vlans):
        f = open('unicommands3930.txt', 'r')
        data = f.read()
        for line in data.split("\n"):
            cmd=line.replace("PORT_NUMBER", port)
            cmd=cmd.replace("VS_NAME", vsname)
            if "VLAN_NUMBER" in cmd:
                for vlan in vlans:
                    cmdExe=cmd.replace("VLAN_NUMBER", vlan)
                    self.executeTelnetCommand(cmdExe, tel)
                    print("CMD for 3930", cmdExe)
                continue
            self.executeTelnetCommand(cmd, tel)
            print("CMD for 3930", cmd)
        postCheckCmd = "conf search str " + str(vsname)
        postCheck = self.executeTelnetCommand(postCheckCmd, tel)
        postVlans = []
        for line in postCheck.split("\n")[1:-1]:
            if "encap-cos-policy port-inherit" in line:
                # ip, vs, port, vlan, status
                if "vlan" in line:
                    lineparts = line.split(" ")
                    print("Line : ", lineparts)
                    vlanIndex = lineparts.index("vlan")
                    vlanNumber = lineparts[vlanIndex + 1]
                    print("VLAN in POSTCHECK QOS", vlanNumber)
                    postVlans.append(vlanNumber)
                    postCheckDetail = []
                    postCheckDetail.append(ip)
                    postCheckDetail.append(port)
                    postCheckDetail.append(vsname)
                    postCheckDetail.append(vlanNumber)
                    postCheckDetail.append("Success")
                    self.postCheckStatus.put(postCheckDetail)
        print("PostVlans : ", postVlans)
        for vlan in vlans:
            if str(vlan) not in postVlans:
                postCheckDetail = []
                postCheckDetail.append(ip)
                postCheckDetail.append(port)
                postCheckDetail.append(vsname)
                postCheckDetail.append(vlan.strip())
                postCheckDetail.append("Fail")
                self.postCheckStatus.put(postCheckDetail)



    def implementQOS5160(self, tel, ip, port, vsname, vlans):
        # f = open('..//ConfData//unicommands5160.txt', 'r')
        f = open('unicommands5160.txt', 'r')
        data = f.read()
        for line in data.split("\n"):
            cmd=line.replace("PORT_NUMBER", port)
            cmd=cmd.replace("VS_NAME", vsname)
            if "VLAN_NUMBER" in cmd:
                print("VLAN List :", vlans)
                for vlanNumber in vlans:
                    cmdExe=cmd.replace("VLAN_NUMBER", vlanNumber)
                    self.executeTelnetCommand(cmdExe, tel)
                    print("CMD for 5160", cmdExe)
                continue
            self.executeTelnetCommand(cmd, tel)
            print("CMD for 5160", cmd)
        postCheckCmd="conf search str " + str(vsname)
        postCheck=self.executeTelnetCommand(postCheckCmd, tel)
        postVlans=[]
        for line in postCheck.split("\n")[1:-1]:
            if "encap-cos-policy port-inherit" in line:
                #ip, vs, port, vlan, status
                if "vlan" in line:
                    lineparts=line.split(" ")
                    print("Line : ",lineparts)
                    vlanIndex=lineparts.index("vlan")
                    vlanNumber=lineparts[vlanIndex+1]
                    print("VLAN in POSTCHECK QOS", vlanNumber)
                    postVlans.append(vlanNumber)
                    postCheckDetail=[]
                    postCheckDetail.append(ip)
                    postCheckDetail.append(port)
                    postCheckDetail.append(vsname)
                    postCheckDetail.append(vlanNumber)
                    postCheckDetail.append("Success")
                    self.postCheckStatus.put(postCheckDetail)
        print("PostVlans : ",postVlans)
        for vlan in vlans:
            if str(vlan) not in postVlans:
                postCheckDetail = []
                postCheckDetail.append(ip)
                postCheckDetail.append(port)
                postCheckDetail.append(vsname)
                postCheckDetail.append(vlan.strip())
                postCheckDetail.append("Fail")
                self.postCheckStatus.put(postCheckDetail)

    def executeWorker(self, serverConf):
        tel = connectTelnet.Telnet()
        retCode = tel.connect(serverConf[0], serverConf[1], serverConf[2])
        ip=serverConf[0]
        if retCode == 1:
            if serverConf[3] in '8700':
                subport = serverConf[4]
                self.implementQOS8700(tel, ip, subport)

            elif serverConf[3] in '3930':
                port = serverConf[4]
                vsname = serverConf[5]
                vlans = serverConf[6]
                self.implementQOS3930(tel, ip, port, vsname, vlans)

            elif serverConf[3] in '5160':
                port = serverConf[4]
                vsname = serverConf[5]
                vlans = serverConf[6]
                self.implementQOS5160(tel, ip, port, vsname, vlans)

            tel.disconnectNe('', '')
        else:
            ipList = []
            ipList.append(serverConf[0])
            self.unReachableIpQueue.put(ipList)


print('Starting QOS UNI Commands Execution script')
myObj = implementQOS()
if len(sys.argv) > 1:
    myObj.confFile = sys.argv[1]
myObj.readConfig()
myObj.fetchData()


#10.121.190.57,8700
# MUZ_BCLBR_CMC_P_C60,10.121.190.54,5160,5,2231,3,4,5,6
