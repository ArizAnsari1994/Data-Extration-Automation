'''
@author: Ariz
'''

import telnetlib
import sys
import traceback
import time


class Telnet():
    '''
    classdocs
    '''

    def __init__(self):
        '''
        Constructor
        '''
    def connect(self, ip,user,pwd):
        neIp=ip
        nePort=23
        neUser=user
        nePass=pwd
        neUser+="\n"
        nePass+="\n"
        try:
            self.tn = telnetlib.Telnet(host=neIp, port=int(nePort), timeout=25)
            self.tn.set_debuglevel(1000000)
            liOutput = str(self.tn.read_until(b"login: ").decode("ascii"))
            self.tn.write(neUser.encode("ascii"))
            cliOutput = str(self.tn.read_until(b"Password: ").decode("ascii"))
            self.tn.write(nePass.encode("ascii"))
            cliOutput = str(self.tn.read_until(b"> ").decode("ascii"))
            self.tn.write(b"system shell set global-more off\n")
            cliOutput = str(self.tn.read_until(b"> ").decode("ascii"))
            #self.loggingInfo('Able to login NE {} ip {}'.format(neName,neIp))
            return 1
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            #self.loggingError('Not Able to login NE {} ip {}'.format(neName,neIp))
            print(traceback.format_exc())
            print("Unexpected error:", sys.exc_info()[0])
            return 0
            
    def connectNe(self,connType,neName):
        tDf=self.nedDf[self.nedDf['NE Name']==neName]
        neIp=tDf['IP Address'].item()
        if tDf['NE Port'].isnull().item()==True:
            nePort=23
        else:
            nePort=tDf['NE Port'].item()
        neUser=tDf['UserName'].item()
        nePass=tDf['Password'].item()
        neUser+="\n"
        nePass+="\n"
        try:
            self.tn = telnetlib.Telnet(host=neIp, port=int(nePort), timeout=25)
            self.tn.set_debuglevel(1000000)
            liOutput = str(self.tn.read_until(b"login: ").decode("ascii"))
            self.tn.write(neUser.encode("ascii"))
            cliOutput = str(self.tn.read_until(b"Password: ").decode("ascii"))
            self.tn.write(nePass.encode("ascii"))
            cliOutput = str(self.tn.read_until(b"> ").decode("ascii"))
            self.tn.write(b"system shell set global-more off\n")
            cliOutput = str(self.tn.read_until(b"> ").decode("ascii"))
            self.loggingInfo('Able to login NE {} ip {}'.format(neName,neIp))
            return 1
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            self.loggingError('Not Able to login NE {} ip {}'.format(neName,neIp))
            print(traceback.format_exc())
            print("Unexpected error:", sys.exc_info()[0])
            return 0
    
    def disconnectNe(self,connType,neName):
        try:
            self.tn.close()
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            print(traceback.format_exc())
            print("Unexpected error:", sys.exc_info()[0])
    
    def sndRcv(self,neName,sndTxt):
        sndTxt=sndTxt+'\n'
        cliOutput=""
        try:
            self.tn.read_very_eager()
        except Exception:
            pass
        try:
            time.sleep(1)
            self.tn.write(sndTxt.encode("ascii"))
            time.sleep(1)
            cliOutput = str(self.tn.read_until(b"> ",timeout=300).decode("ascii"))
        except Exception:
            pass
        return cliOutput
    
#     
# 
# print ("entered script")
# tel=Telnet()
# tel.connect()
# data=tel.sndRcv("test", "soft show")
# print ("data " + data)
# tel.disconnectNe("test", "te")



