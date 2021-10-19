'''
@author: Ariz
'''
from datetime import datetime
import threading
import time
import sys, os
from selenium import webdriver
# from Utils.constants import *
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
if sys.version_info[0] < 3:
    from Queue import Queue
else:
    from queue import Queue
if not sys.version_info[0] < 3:
    import concurrent.futures

class snmpTrap(object):
    sleepInterval = 0.5
    implicitWait = 20
    serverConfig = []
    flowPointQueue = Queue()
    unReachableIpQueue = Queue()
    #utilObj = UtilityClass()
    PWD_6200 = "ADMIN"
    USER_6200 = "ADMIN"
    THREAD_POOL_SIZE = 5
    GECKODRIVER_PATH="C:\\Users\\Ariz Ansari\\Documents\\QOS\\geckodriver\\geckodriver.exe"        #"C:\\Users\\Vineet\\Downloads\\geckodriver-v0.21.0-win32\\geckodriver.exe"
    sep = os.sep
    PROJECT_PATH = ".."
    REPORTS_COMMON_PATH = os.path.join(PROJECT_PATH, "Reports" + sep)

    def __init__(self):
        self.date = datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S-%f')[:-3]
        self.flowPointQueue.put(["IP","NeType", "Service Name","Service Type", "Flow Point", "EVS", "Interface", "FlowPointTemplate"])

    def getFirefoxDriver(self):
        capabilities = webdriver.DesiredCapabilities().FIREFOX
        capabilities["marionette"] = True
        binary = FirefoxBinary('C:/Program Files/Mozilla Firefox/firefox.exe')
        driver = webdriver.Firefox(firefox_binary=binary, capabilities=capabilities,executable_path=self.GECKODRIVER_PATH)#"C:/Utility/BrowserDrivers/geckodriver.exe")
        return driver

    def getChromeDriver(self):
        driver = webdriver.Chrome(executable_path=CHROME_DRIVER_PATH)
        return driver

    def logout(self, driver):
        driver.switch_to_default_content()
        driver.switch_to_frame(driver.find_element_by_name("commonHeader"))
        driver.find_element_by_link_text("LOGOUT").click()

    def fetchData(self):
        isPythonVersion3 = True
        if sys.version_info[0] < 3:
            isPythonVersion3 = False

        if isPythonVersion3:
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.THREAD_POOL_SIZE) as executor:
                for poolList in self.serverConfig:
                    for poolItem in poolList:
                        executor.submit(self.executeWorker, poolItem)
                        print("Queue size: ", self.flowPointQueue.qsize())

        else:
            for poolList in self.serverConfig:
                # executor.submit(self.executeWorker, serverConf)
                print('Starting new pool : ' + str(self.THREAD_POOL_SIZE))
                threadPoolList = []
                for poolItem in poolList:
                    t = threading.Thread(target=self.executeWorker, args=(poolItem,))
                    t.start()
                    threadPoolList.append(t)
                for t in threadPoolList:
                    t.join()
                print('pool Ends')
                # self.writeDataToFile(os.path.join(self.REPORTS_COMMON_PATH,"TDMServices" +self.sep + "TDMServicesReport"), self.flowPointQueue)

    def executeWorker(self, serverConf):
        if '6200' in serverConf[3]:
            self.executeWorker6200(serverConf)
        elif serverConf[3] in ['3930', '5160']:
            self.executeWorkerOthers(serverConf)

    def executeWorker6200(self, serverConf):
        ip = serverConf[0]
        driver = self.getFirefoxDriver()
        try:
            driver.implicitly_wait(self.implicitWait)
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
            driver._switch_to.frame(driver.find_element_by_name("nodeTocFrame"))
            time.sleep(self.sleepInterval)
            driver.find_element_by_link_text("L2 Services").click()
            time.sleep(self.sleepInterval)
            driver.find_element_by_link_text("Service Switch-1").click()
            time.sleep(self.sleepInterval)
            driver.find_element_by_link_text("Services Provisioning").click()
            time.sleep(self.sleepInterval)
            self.tdmElineService(driver, serverConf)
            time.sleep(self.sleepInterval)
            self.tdmElanService(driver, serverConf)
        except Exception as e:
            print("Exception occurred!!!! \n",str(e))
            itemList = []
            itemList.append(ip)
            self.unReachableIpQueue.put(itemList)
            print("Writing to csv")
            self.writeDataToFile(os.path.join(self.PROJECT_PATH, "TDMServices" + self.sep + "unReachableIp"),
                                 self.unReachableIpQueue)
        finally:
            try:
                self.logout(driver)
            except:
                itemList = []
                itemList.append(ip)
                self.unReachableIpQueue.put(itemList)
                print("Writing to csv")
                self.writeDataToFile(os.path.join(self.PROJECT_PATH, "TDMServices" + self.sep + "unReachableIp"), self.unReachableIpQueue)
            finally:
                time.sleep(self.sleepInterval)
                driver.close()


    def tdmElineService(self, driver, serverConf):
        driver.find_element_by_link_text("ELINE Services").click()
        time.sleep(self.sleepInterval)
        serviceType="ELINE"
        driver.switch_to_default_content()
        driver._switch_to.frame(driver.find_element_by_name("nodeBodyFrame"))
        time.sleep(1)
        count=0
        # rows = driver.find_elements_by_tag_name("tr")
        rows = driver.find_elements_by_xpath("//table[2]/tbody/tr")
        print("Rows found: ", len(rows), "\n", rows)
        for row in range(1,len(rows)):
            count += 1
            serviceName=driver.find_element_by_xpath("//html/body/form/table[2]/tbody/tr["+str(count+1)+"]/td[1]").text#get_attribute("text")
            print("Value : ", serviceName)
            driver.find_element_by_xpath("//html/body/form/table[2]/tbody/tr[" + str(count + 1) + "]/td[1]").click()
            fprows = driver.find_elements_by_xpath("//table[2]/tbody/tr")
            fpcount = 0
            print("FPRows found: ", len(fprows), "\n", fprows)
            # if len(fprows) == 2:
            #     print("No Flow points found")
            #     continue
            for fp in range(1, len(fprows)):
                fpcount += 1
                fpName = driver.find_element_by_xpath(
                    "//html/body/form/table[2]/tbody/tr[" + str(fpcount + 1) + "]/th/a").text
                time.sleep(self.sleepInterval)
                print("FP name: ",fpName)
                # driver.find_element_by_xpath("//html/body/form/table/tbody/tr[" + str(fpcount + 1) + "]/th/a").click()
                # /html/body/form/table[2]/tbody/tr[2]/th/a
                fpDvr = driver.find_element_by_xpath("//html/body/form/table[2]/tbody/tr[" + str(fpcount + 1) + "]/th/a")
                fpDvr.click()
                time.sleep(self.sleepInterval)
                temprows = driver.find_elements_by_tag_name("tr")
                tempcount = 0
                print("TempRows found: ", len(temprows), "\n", temprows)
                fpDict = {"EVC": "None", "Interface": "None", "FlowPointTemplate": "None"}
                fpList = list(fpDict.keys())
                for temp in range(len(temprows) ):

                    property = driver.find_element_by_xpath(
                        "//html/body/form/table/tbody/tr[" + str(tempcount + 1) + "]/th").text
                    value = driver.find_element_by_xpath(
                        "//html/body/form/table/tbody/tr[" + str(tempcount + 1) + "]/td").text
                    tempcount += 1
                    # print("FP name: ", property, value)
                    if property.strip() in fpList and len(fpList) != 0:
                        # valueList.append(value)
                        fpDict[property] = value
                        fpList.remove(property.strip())
                    if len(fpList) == 0 or temp == len(temprows)-3:
                        driver.find_element_by_partial_link_text("Back to ").click()
                        print("Clicked on Back To")
                        time.sleep(self.sleepInterval)
                        break
                print([serverConf[0], serverConf[3], serviceName, serviceType, fpName] + [fpDict["EVC"]] + [
                    fpDict["Interface"]] + [fpDict["FlowPointTemplate"]])
                self.flowPointQueue.put(
                    [serverConf[0], serverConf[3], serviceName, serviceType, fpName] + [fpDict["EVC"]] + [
                        fpDict["Interface"]] + [fpDict["FlowPointTemplate"]])
                self.writeDataToFile(os.path.join(self.PROJECT_PATH, "TDMServices" + self.sep + "TDMServicesReport"),
                                     self.flowPointQueue)
                # print("FPROWS: ",len(fprows), "FP: ", fp)
                if len(fprows)-1 == fp:
                    driver.find_element_by_partial_link_text("View Data").click()
                    print("Clicked on View Data")
                    time.sleep(self.sleepInterval)
                    break
        driver.switch_to_default_content()
        time.sleep(self.sleepInterval)
        driver._switch_to.frame(driver.find_element_by_name("nodeTocFrame"))
        time.sleep(self.sleepInterval)

    def tdmElanService(self, driver, serverConf):
        driver.find_element_by_link_text("ELAN Services").click()
        time.sleep(self.sleepInterval)
        serviceType = "ELAN"
        print("Service Type:", serviceType)
        driver.switch_to_default_content()
        driver._switch_to.frame(driver.find_element_by_name("nodeBodyFrame"))
        time.sleep(1)
        count = 0
        # /html/body/form/table[2]/tbody/tr[2]/td[1]/p/a
        rows = driver.find_elements_by_xpath("//table[2]/tbody/tr")
        print("Rows found: ", len(rows), "\n")#, rows)
        for row in range(1, len(rows)):
            count += 1
            serviceName = driver.find_element_by_xpath(
                "//html/body/form/table/tbody/tr[" + str(count + 1) + "]/td/p/a/b").text  # get_attribute("text")
            print("Service Name : ", serviceName)
            # driver.find_element_by_xpath("//html/body/form/table/tbody/tr[" + str(count + 1) + "]/td/p/a").click()
            driver.find_element_by_xpath("//html/body/form/table/tbody/tr[" + str(count + 1) + "]/td/p/a").click()
            fprows = driver.find_elements_by_xpath("//table[3]/tbody/tr")
            time.sleep(self.sleepInterval)
            print("FPRows found: ", len(fprows), "\n", fprows)

            fpcount = 0
            #, fprows)
            for fp in range(1, len(fprows)):
                fpcount += 1
                print("In FProws")
                fpName = driver.find_element_by_xpath(
                    "//html/body/form/table[3]/tbody/tr[" + str(fp + 2) + "]/td/p").text
                print("FP name: ", fpName)
                fpDvr= driver.find_element_by_xpath("//html/body/form/table[3]/tbody/tr[" + str(fp + 2) + "]/td/p/a")
                fpDvr.click()

                print("Finding temp rows: ")
                temprows = driver.find_elements_by_tag_name("tr")
                tempcount = 0
                print("TempRows found: ", len(temprows), "\n", temprows)
                fpDict = {"EVC": "None", "Interface": "None", "FlowPointTemplate":"None"}
                fpList = list(fpDict.keys())
                valueList=[]
                for temp in range(len(temprows) - 1):
                    if len(fpList) == 0 or temp == len(temprows)-3:
                        driver.find_element_by_partial_link_text("Back to ").click()
                        time.sleep(self.sleepInterval)
                        break
                    property = driver.find_element_by_xpath("//html/body/form/table/tbody/tr[" + str(tempcount + 1) + "]/th").text
                    value = driver.find_element_by_xpath("//html/body/form/table/tbody/tr[" + str(tempcount + 1) + "]/td").text
                    tempcount += 1
                    # print("FP name: ", property, value)
                    if property.strip() in fpList and len(fpList) != 0:
                        # valueList.append(value)
                        fpDict[property]=value
                        fpList.remove(property.strip())
                print([serverConf[0], serverConf[3], serviceName, serviceType, fpName]+[fpDict["EVC"]]+[fpDict["Interface"]]+[fpDict["FlowPointTemplate"]])
                self.flowPointQueue.put(
                    [serverConf[0], serverConf[3], serviceName, serviceType, fpName]+[fpDict["EVC"]]+[fpDict["Interface"]]+[fpDict["FlowPointTemplate"]])
                self.writeDataToFile(os.path.join(self.PROJECT_PATH, "TDMServices" + self.sep + "TDMServicesReport"),
                                     self.flowPointQueue)
                if len(fprows)-2 == fp:
                    driver.find_element_by_partial_link_text("View Data").click()
                    time.sleep(self.sleepInterval)
                    break

    def executeWorkerOthers(self, serverConf):
        pass

    def writeDataToFile(self, fileName, que):
        print("Writing to file")
        directory = os.path.dirname(fileName)
        if not os.path.exists(directory):
            os.makedirs(directory)
        fd = open(fileName + '_' + self.date + '.csv', 'a')
        while not que.empty():
            d = que.get()
            fd.write((',').join(d) + '\n')

    def readConfig(self, filePath=None, isApi=False):
        '''
        This method reads the config file and loads data in to python objects
        '''
        serverConfig=[]
        if filePath != None:
            self.confFile = filePath
        fd=open(self.confFile,'r')
        eof = False
        while True:
            poolList=[]
            for i in range(self.THREAD_POOL_SIZE):
                line=fd.readline()
                if(line.strip() == ""):
                    eof = True
                    break
                neList=line.split(',')
                neDetailsList=[]
                neDetailsList.append(neList[0].strip())
                if isApi:
                    neDetailsList.append(USER_MCP)
                    neDetailsList.append(PWD_MCP)
                elif '6200' in neList[1].strip():
                    neDetailsList.append(self.USER_6200)
                    neDetailsList.append(self.PWD_6200)
                elif neList[1].strip() in ['3930', '5160']:
                    neDetailsList.append(USER_OTHERS)
                    neDetailsList.append(PWD_OTHERS)
                neDetailsList.append(neList[1].strip())
                if len(neList) >= 3:
                    neDetailsList.append(neList[2].strip())
                if len(neList) >= 4:
                    neDetailsList.append(neList[3].strip())
                if len(neList) >= 5:
                    neDetailsList.append(neList[4].strip())
                poolList.append(neDetailsList)
            if len(poolList)>0:
                serverConfig.append(poolList)
            if eof:
                break
        fd.close()
        print(str(serverConfig))
        return serverConfig

print('Starting TDM Service script')
myObj = snmpTrap()
startDate=str(datetime.now())
confFile = "Test_6200.txt"
if len(sys.argv) > 1:
    confFile=sys.argv[1]
myObj.serverConfig=myObj.readConfig(confFile)
myObj.fetchData()
eDate=str(datetime.now())
print ("start",startDate)
print ("end:" , eDate)
print('Ending TDM Service script')
