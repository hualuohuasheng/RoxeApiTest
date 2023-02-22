# coding=utf-8
# author: MingLei Li
# date: 2022-02-21
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
import platform
import os
import enum
import subprocess


class OSSystem(enum.Enum):

    OS_MAC = "mac"
    OS_WINDOWS = "win"
    OS_LINUX = "linux"


class WebClient:

    def __init__(self):
        os_platform = platform.platform()
        if "Darwin" in os_platform or "macos" in os_platform.lower():
            self.osSystem = OSSystem.OS_MAC
        elif "Linux" in os_platform:
            self.osSystem = OSSystem.OS_LINUX
        else:
            self.osSystem = OSSystem.OS_WINDOWS
        # self.driver = None
        self.browser_version = ""
        # self.openChrome()

    def checkChromeVersion(self):
        if self.osSystem == OSSystem.OS_MAC:
            shell_args = ["ls", "-l", "/Applications/Google Chrome.app/Contents/Frameworks/Google Chrome Framework.framework/Versions"]
            shell_res = subprocess.run(shell_args, capture_output=True)
            if shell_res.returncode == 0:
                output = shell_res.stdout.decode().split("\n")
                cur_out = [i for i in output if "Current" in i]
                cur_version = cur_out[0].split("Current -> ")[-1]
                self.browser_version = "chromedriver_" + cur_version.split(".")[0]

    def openChrome(self):
        # chromedrive 下载地址: https://chromedriver.chromium.org/downloads
        # 需要下载和当前使用的chrome浏览器对应版本的chromedriver, 放到当前目录下
        chrome_options = webdriver.ChromeOptions()
        if self.osSystem == OSSystem.OS_LINUX:
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--disable-gpu')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        # chrome_options.add_experimental_option('mobileEmulation', {'deviceName': 'Galaxy S5'})
        cur_path = os.path.dirname(os.path.abspath(__file__))
        driver_path = os.path.abspath(os.path.join(cur_path, f"./WebDrivers/{self.browser_version}_{self.osSystem.value}"))
        print(driver_path)
        try:
            self.driver = webdriver.Chrome(driver_path, options=chrome_options)
        except Exception as e:
            if "Current browser version" in e.args[0]:
                chrome_version = e.args[0].split("Current browser version is ")[1].split(" ")[0]
                print("chrome version: ", chrome_version)
                driver_path = os.path.join(cur_path, "chromedriver_{}".format(chrome_version.split(".")[0]))
                self.driver = webdriver.Chrome(driver_path, options=chrome_options)
        self.driver.maximize_window()
        self.driver.implicitly_wait(30)  # 隐式等待，一次设置，全局生效，规定时间内网页加载完成

    def accessWebsite(self, check_url):
        self.driver.get(check_url)

    def logInLinkedin(self):
        self.accessWebsite("https://www.linkedin.com/groups/1813979/")
        WebDriverWait(self.driver, 30).until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[1]/main/p[1]/a")))
        # self.driver.find_element(By.XPATH, "/html/body/div[1]/div/section/div/div[2]/button[1]").click()
        time.sleep(5)
        self.driver.find_element(By.XPATH, "/html/body/div[1]/main/p[1]/a")
        self.driver.switch_to.frame("")
        WebDriverWait(self.driver, 30).until(EC.visibility_of_element_located((By.ID, "username")))
        self.driver.find_element(By.ID, "username").send_keys("alison_peipei@yahoo.com")
        WebDriverWait(self.driver, 30).until(EC.visibility_of_element_located((By.ID, "password")))
        self.driver.find_element(By.ID, "password").send_keys("mengjing911@s")
        time.sleep(3)
        self.driver.find_element(By.XPATH, '//*[@id="organic-div"]/form/div[3]/button').click()
        # self.driver.find_element(By.ID, "email-address")
        # self.driver.find_element(By.ID, "password")

    def testBaidu(self):
        self.driver.get("https://www.baidu.com")
        cur_window = self.driver.current_window_handle
        print(cur_window)
        # self.driver.find_element(By.ID, "kw").send_keys("python3")
        # time.sleep(3)
        action = ActionChains(self.driver)
        more_button = self.driver.find_element(By.PARTIAL_LINK_TEXT, "更多")
        action.move_to_element(more_button).perform()
        self.driver.find_element(By.LINK_TEXT, "翻译").click()
        time.sleep(1)
        self.driver.switch_to.window(self.driver.window_handles[1])
        if self.driver.find_element(By.XPATH, '//*[@id="app-guide"]/div/div/div[2]/span').is_displayed():
            self.driver.find_element(By.XPATH, '//*[@id="app-guide"]/div/div/div[2]/span').click()
            time.sleep(0.5)

        action.context_click(self.driver.find_element(By.ID, "translate-button")).perform()

    def closeWebsite(self):
        self.driver.quit()


if __name__ == "__main__":
    client = WebClient()
    client.checkChromeVersion()
    client.openChrome()
    client.testBaidu()
    # client.accessWebsite("https://www.linkedin.com/groups/1813979/")
    # print(client.driver.page_source)
    time.sleep(5)
    # client.closeWebsite()
