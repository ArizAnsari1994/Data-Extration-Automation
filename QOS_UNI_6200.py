'''
@author: Ariz
'''

from datetime import datetime
import threading
import time
import sys
from selenium import webdriver

if sys.version_info[0] < 3:
    from Queue import Queue
else:
    from queue import Queue




class MacUpdate(object):
    user = 'ADMIN'
    pwd = 'ADMIN'
    poolSize = 3
    serverConfig = []
    date = None
    confFile = "qos.txt"
    unMatchedPwGroups = Queue()
    unReachableIpQueue = Queue()
    sleepInterval = 0.5
    implicitWait = 20
    FIREFOX_DRIVER_PATH = "C:\\geckoWebDriver\\geckodriver.exe"

    def __init__(self):
        self.date = datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S-%f')[:-3]

    def getChromeDriver(self):
        #C:\Users\ak185389\Documents\QOS\geckodriver\geckodriver.exe
        driver = webdriver.Firefox(executable_path=r"C:\\Users\\Ariz Ansari\\Documents\\QOS\\geckodriver\\geckodriver.exe")
        #driver = webdriver.Firefox()
        return driver

    def logout(self, driver):       
        driver.switch_to_default_content()
        driver.switch_to_frame(driver.find_element_by_name("commonHeader"))
        driver.find_element_by_link_text("LOGOUT").click()

    def fetchData(self):
        print(self.serverConfig)
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
            self.writeDataToFile('unMatchedPwGroups', self.unMatchedPwGroups)

    def writeDataToFile(self, fileName, que):
        fd = open(fileName + '_' + self.date + '.csv', 'a')
        while not que.empty():
            d = que.get()
            fd.write((',').join(d) + '\n')

    def readConfig(self, filePath=None, isApi=False):
        '''
        This method reads the config file and loads data in to python objects
        '''
        serverConfig = []
        if filePath != None:
            self.confFile = filePath
        fd = open(self.confFile, 'r')
        eof = False
        while True:
            poolList = []
            for i in range(self.poolSize):
                line = fd.readline().strip()
                if (line.strip() == ""):
                    eof = True
                    break
                neList = line.split(',')
                neDetailsList = []
                neDetailsList.append(neList[1].strip())
                neDetailsList.append(self.user)
                neDetailsList.append(self.pwd)
                neDetailsList.append(neList[2].strip())
                neDetailsList.append(neList[3:])  # service names list
                poolList.append(neDetailsList)
            serverConfig.append(poolList)
            if eof:
                break
        fd.close()
        return serverConfig

    def executeWorker(self, serverConf):
        driver = self.getChromeDriver()
        try:            
            driver.implicitly_wait(self.implicitWait)
            #driver.maximize_window()
            #http://10.121.190.52:20080/EMSRequest/Welcome
            ip=serverConf[0]
            serviceList = serverConf[4]
            # print("service List", serviceList)
            loginUrl = "http://" + ip + ":20080/EMSRequest/Welcome"
            print(loginUrl)
            driver.get(loginUrl)
            search_field = driver.find_element_by_name("Username")
            search_field.send_keys(serverConf[1])

            search_field = driver.find_element_by_name("Password")
            search_field.send_keys(serverConf[2])

            submitButton = driver.find_element_by_name("Submit")
            submitButton.click()
            time.sleep(self.sleepInterval)

            # Start editing tunnel end points
            driver._switch_to.frame(driver.find_element_by_name("nodeTocFrame"))
            # print("Switched to frame")
            time.sleep(self.sleepInterval)
            #driver.find_element_by_css_selector("#nodeIcon124").click()
            driver.find_element_by_link_text("L2 Services").click()
            # print("Clicked Node Icon 'L2 Services'")
            time.sleep(self.sleepInterval)
            driver.find_element_by_link_text("Service Switch-1").click()
            # print("Clicked Node Icon 'Service Switch-1'")
            time.sleep(self.sleepInterval)
            self.ingressPriorityMapping(driver)
            self.ingressExpToCosMapping(driver)
            self.egressCosToExpMapping(driver)
            self.servicesProvisioning(driver, serviceList)
            self.pwGroupProvisioning(driver, ip, serviceList)
        #except Exception as e:
        #    print(e)

        finally:
            self.logout(driver)



    def ingressPriorityMapping(self, driver):

        driver.find_element_by_link_text("Ingress QoS").click()
        # print("Clicked Node Icon 'Ingress QoS'")
        time.sleep(self.sleepInterval)
        driver.find_element_by_link_text("DSCP To CoSQ Mapping Profile").click()
        # print("Clicked Node Icon 'DSCP To CosQ Mapping Profile'")
        time.sleep(self.sleepInterval)

        driver.switch_to_default_content()
        frame = driver._switch_to.frame(driver.find_element_by_name("nodeBodyFrame"))
        driver.find_element_by_link_text("Provision DSCPToCosQ Mapping Profile").click()
        # print("Provision DSCPToCosQ Mapping Profile")
        time.sleep(1)
        rows=driver.find_elements_by_tag_name("tr")
        if (rows[0].text).strip() in "Description":
            driver.find_element_by_xpath("//*[@id='PriorityMappingProfile']/tbody/tr[1]/td/input").send_keys('New_QOS_DSCP')
        rows=rows[4:]
        count=3
        # print("length of row : ", len(rows))
        for row in range(len(rows)+1):
            count += 1
            print("Count : ", count)
            if count == 68:
                break
            r=[i for j in (range(4,26), range(31,32), range(33,38), range(39,50), range(51,69)) for i in j]
            if count in r:
                driver.find_element_by_xpath("//*[@id='PriorityMappingProfile']/tbody/tr[" + str(count-2) + "]/td[1]/select").send_keys('0')
            if count in range(26,31):
                driver.find_element_by_xpath("//*[@id='PriorityMappingProfile']/tbody/tr[" + str(count-2) + "]/td[1]/select").send_keys('4')
            if count == 32:
                driver.find_element_by_xpath("//*[@id='PriorityMappingProfile']/tbody/tr["+str(count-2)+"]/td[1]/select").send_keys('2')
            if count == 38:
                driver.find_element_by_xpath("//*[@id='PriorityMappingProfile']/tbody/tr["+str(count-2)+"]/td[1]/select").send_keys('5')
            if count == 50:
                driver.find_element_by_xpath("//*[@id='PriorityMappingProfile']/tbody/tr["+str(count-2)+"]/td[1]/select").send_keys('1')

            str1 = driver.find_element_by_xpath("//*[@id='PriorityMappingProfile']/tbody/tr["+str(count-2)+"]/td[2]/select").get_attribute("value")
            #print ("Before str1: ", str1)
            driver.find_element_by_xpath("//*[@id='PriorityMappingProfile']/tbody/tr[" + str(count - 2) + "]/td[2]/select").send_keys('green')
            str1 = driver.find_element_by_xpath("//*[@id='PriorityMappingProfile']/tbody/tr[" + str(count - 2) + "]/td[2]/select").get_attribute("value")

            for i in range(10):
                driver.find_element_by_xpath("/html/body/form/table[2]/tbody/tr[" + str(count - 2) + "]/td[2]/select").send_keys('green')
                str1 = driver.find_element_by_xpath("//*[@id='PriorityMappingProfile']/tbody/tr[" + str(count - 2) + "]/td[2]/select").get_attribute("value")
                print("After retrying str1: ", str1)
                if str1 == "2":
                    break

        driver.find_element_by_name("Submit").click()
        driver.switch_to_default_content()
        driver._switch_to.frame(driver.find_element_by_name("nodeTocFrame"))
        time.sleep(2)

    def ingressExpToCosMapping(self, driver):
        driver.find_element_by_link_text("Ingress QoS").click()
        # print("Clicked Node Icon 'Ingress QoS'")
        time.sleep(self.sleepInterval)
        driver.find_element_by_link_text("EXP To CoSQ Mapping Profile").click()
        # print("Clicked Node Icon 'EXP To CosQ Mapping Profile'")
        time.sleep(self.sleepInterval)

        driver.switch_to_default_content()
        frame = driver._switch_to.frame(driver.find_element_by_name("nodeBodyFrame"))
        driver.find_element_by_link_text("Provision EXPToCosQ Mapping Profile").click()
        # print("Provision DSCPToCosQ Mapping Profile")
        time.sleep(1)
        rows = driver.find_elements_by_tag_name("tr")
        if (rows[0].text).strip() in "Description":
            driver.find_element_by_xpath("//*[@id='PriorityMappingProfile']/tbody/tr[1]/td/input").send_keys(
                'OT_Ingress_NNI_ExpCos')
        for i in range(len(rows)-3):
            driver.find_element_by_xpath("//*[@id='PriorityMappingProfile']/tbody/tr["+str(i+2)+"]/th[2]/select").send_keys(i)
            driver.find_element_by_xpath("//*[@id='PriorityMappingProfile']/tbody/tr[" + str(i + 2) + "]/th[3]/select").send_keys('GREEN')
        driver.find_element_by_name("Submit").click()
        driver.switch_to_default_content()
        driver._switch_to.frame(driver.find_element_by_name("nodeTocFrame"))
        time.sleep(2)

    def egressCosToExpMapping(self, driver):
        driver.find_element_by_link_text("Egress QoS").click()
        # print("Clicked Node Icon 'Egress QoS'")
        time.sleep(self.sleepInterval)
        driver.find_element_by_link_text("CoSQ To EXP Mapping Profile").click()
        # print("Clicked Node Icon 'EXP To CosQ Mapping Profile'")
        time.sleep(self.sleepInterval)

        driver.switch_to_default_content()
        frame = driver._switch_to.frame(driver.find_element_by_name("nodeBodyFrame"))
        driver.find_element_by_link_text("Provision CosQToEXP Mapping Profile").click()
        # print("Provision CosQToEXP Mapping Profile")
        time.sleep(1)
        rows = driver.find_elements_by_tag_name("tr")
        if (rows[0].text).strip() in "Description":
            driver.find_element_by_xpath("//*[@id='PriorityMappingProfile']/tbody/tr[1]/td/input").send_keys(
                'OT_Egress_COStoEXP')
        for i in range(len(rows)-3):
            driver.find_element_by_xpath("//*[@id='PriorityMappingProfile']/tbody/tr["+str(i+2)+"]/th[2]/select").send_keys(i)
            driver.find_element_by_xpath("//*[@id='PriorityMappingProfile']/tbody/tr[" + str(i + 2) + "]/th[3]/select").send_keys(i)
        driver.find_element_by_name("Submit").click()
        driver.switch_to_default_content()
        driver._switch_to.frame(driver.find_element_by_name("nodeTocFrame"))
        time.sleep(2)

    def servicesProvisioning(self, driver, serviceList):
        driver.find_element_by_link_text("Services Provisioning").click()
        # print("Clicked Node Icon 'Services Provisioning'")
        time.sleep(self.sleepInterval)
        driver.find_element_by_link_text("ELAN Services").click()
        # print("Clicked Node Icon 'ELAN Services'")
        time.sleep(self.sleepInterval)
        driver.switch_to_default_content()
        frame = driver._switch_to.frame(driver.find_element_by_name("nodeBodyFrame"))
        time.sleep(1)
        rows = driver.find_elements_by_tag_name("tr")
        # serviceNames to be changed as list of service names provided by user
        serviceNames=serviceList
        for i in range(len(rows)-3):
            count=str(i+2)
            t = driver.find_element_by_xpath("//form/table/tbody/tr[" + count + "]/td[1]/p").text
			#/html/body/form/table/tbody/tr[2]/td[1]/p/a/b
            if t.strip() in serviceNames:
                #driver.find_element_by_xpath("//form/table[2]/tbody/tr["+ count  +"]/td[1]/p").click()
                #driver.find_element_by_xpath("/html/body/form/table[3]/tbody/tr[3]/td[1]/p/a/b").click()
                driver.find_element_by_link_text(t.strip()).click()
                driver.find_element_by_xpath("/html/body/form/table[3]/tbody/tr[3]/td[1]/p/a/b").click()
				#/html/body/form/table[2]/tbody/tr[6]/td/select
                driver.find_element_by_xpath("/html/body/form/table[2]/tbody/tr[6]/td/select").send_keys("Trust_DSCP")#("Trust_Dot1p")#
				#/html/body/form/table[2]/tbody/tr[8]/td/select
                driver.find_element_by_xpath("/html/body/form/table[2]/tbody/tr[8]/td/select").send_keys("New_QoS_DSCP")#("None")#
                driver.find_element_by_name("Submit").click()
                time.sleep(self.sleepInterval)
                try:
                    driver.find_element_by_name("Submit").click()
                except:
                    if driver.find_element_by_xpath("/html/body/form/center/b").text == "Warning:":
                        print(" No Modifications were necessary")
                finally:
                    driver.find_element_by_link_text("Back").click()
                    time.sleep(self.sleepInterval)
                    driver.find_element_by_partial_link_text("Back to").click()
                    time.sleep(self.sleepInterval)
                    #driver.find_element_by_partial_link_text("View Data ELANServices").click()
                    time.sleep(self.sleepInterval)
        driver.switch_to_default_content()
        driver._switch_to.frame(driver.find_element_by_name("nodeTocFrame"))
        time.sleep(self.sleepInterval)

    def pwGroupProvisioning(self, driver, ip, serviceList):
        driver.find_element_by_link_text("Pseudo Wires").click()
        # print("Clicked Node Icon 'Pseudo Wires'")
        time.sleep(self.sleepInterval)
        driver.find_element_by_link_text("Pseudo Wire Groups").click()
        # print("Clicked Node Icon 'Pseudo Wire Groups'")
        time.sleep(self.sleepInterval)
        driver.switch_to_default_content()
        frame = driver._switch_to.frame(driver.find_element_by_name("nodeBodyFrame"))
        time.sleep(1)
        rows = driver.find_elements_by_tag_name("tr")
        # print(len(rows))
        # serviceNames to be changed as list of service names provided by user
        # serviceNames = ["test_VC"]
        for i in range(len(rows) - 1):
            count = str(i+2)			
			#/html/body/form/table/tbody/tr[2]/td[1]/a/b
            t = driver.find_element_by_xpath("//form/table/tbody/tr[" + count + "]/td[1]").text
            # # /html/body/form/table/tbody/tr[2]/td[1]
            # print(t)
            if t.strip() in serviceList:
                driver.find_element_by_link_text(t.strip()).click()
                time.sleep(self.sleepInterval)
                #/html/body/form/table[2]/tbody/tr[2]/th/a/b
                #/html/body/form/table[2]/tbody/tr[3]/th/a/b
                p = driver.find_element_by_xpath("/html/body/form/table[2]/tbody/tr[2]/th/a/b").text
                #print(p)
                pws = driver.find_elements_by_xpath("/html/body/form/table[2]/tbody/tr")
                #print("pws : ", len(pws))
                for rcount in range(len(pws)):
                        if rcount == 2:
                            break
                        print("count: ",rcount,"    //form/table[2]/tbody/tr[" + str(rcount+2) + "]/th/a/b")				         
                        driver.find_element_by_xpath("//form/table[2]/tbody/tr[" + str(rcount+2) + "]/th/a/b").click()
                        time.sleep(2)
                        driver.find_element_by_xpath("/html/body/form/table/tbody/tr[17]/td/select").send_keys("OT_Ingress_NNI_ExpCos")
                        driver.find_element_by_xpath("/html/body/form/table/tbody/tr[18]/td/select").send_keys("OT_Egress_COStoEXP")
                        driver.find_element_by_name("Submit").click()
                        time.sleep(self.sleepInterval)
                        try:
                            driver.find_element_by_name("Submit").click()
                        except:
                            #if driver.find_element_by_xpath("/html/body/form/center/b").text == "Warning:":
                            print(" No Modifications were necessary")
                            driver.back()
                            driver.back()
                        driver.back()		
                        driver.back()		
                        driver.back()
                driver.back()						
            else:
                pwGrp=[]
                pwGrp.append(ip)
                pwGrp.append(t.strip())
                self.unMatchedPwGroups.put(pwGrp)



print('Starting QoS NNI Mapping 6200 script')
myObj = MacUpdate()
confFile = None
if len(sys.argv) > 1:
    confFile = sys.argv[1]
myObj.serverConfig = myObj.readConfig(confFile)
myObj.fetchData()
print('Ending QoS NNI Mapping 6200 script')
