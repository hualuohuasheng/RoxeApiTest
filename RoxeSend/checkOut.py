# coding=utf-8

from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.common.by import By
# from selenium.webdriver.common.action_chains import ActionChains
import time
import platform
import os


class CheckOut:

    def __init__(self):
        os_platform = platform.platform()
        if "Darwin" in os_platform:
            self.osSystem = "mac"
        elif "Linux" in os_platform:
            self.osSystem = "linux"
        else:
            self.osSystem = "win"
        self.driver = None
        self.openChrome()

    def openChrome(self):
        # chromedrive 下载地址: https://chromedriver.chromium.org/downloads
        # 需要下载和当前使用的chrome浏览器对应版本的chromedriver, 放到当前目录下
        chrome_options = webdriver.ChromeOptions()
        if self.osSystem == "linux":
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--disable-gpu')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        # chrome_options.add_experimental_option('mobileEmulation', {'deviceName': 'Galaxy S5'})
        cur_path = os.path.dirname(os.path.abspath(__file__))
        driver_path = os.path.join(cur_path, 'chromedriver_92')
        try:
            self.driver = webdriver.Chrome(driver_path, options=chrome_options)
        except Exception as e:
            if "Current browser version" in e.args[0]:
                chrome_version = e.args[0].split("Current browser version is ")[1].split(" ")[0]
                print("chrome version: ", chrome_version)
                driver_path = os.path.join(cur_path, "chromedriver_{}".format(chrome_version.split(".")[0]))
                self.driver = webdriver.Chrome(driver_path, options=chrome_options)
        self.driver.maximize_window()

    def accessWebsite(self, check_url):
        self.driver.get(check_url)

    def selectCard(self):
        card_method = (By.XPATH, '//*[@id="app"]/div/div[1]/div[2]/div[2]/span')
        pay_button = (By.XPATH, '//*[@id="app"]/div/div[2]/div/div/div')
        # 等待元素被找到
        WebDriverWait(self.driver, 30, 0.5).until(expected_conditions.presence_of_element_located(card_method))
        self.driver.find_element(*card_method).click()
        time.sleep(0.5)
        # self.driver.find_element(*password_element).send_keys(password)
        self.driver.find_element(*pay_button).click()
        email = (By.ID, 'email')
        cardNumber = (By.ID, 'cardNumber')
        cardExpiry = (By.ID, 'cardExpiry')
        cardCvc = (By.ID, 'cardCvc')
        billingName = (By.ID, 'billingName')
        WebDriverWait(self.driver, 300, 0.5).until(expected_conditions.presence_of_element_located(email))
        self.driver.find_element(*email).send_keys("test123@163.com")
        self.driver.find_element(*cardNumber).send_keys("4242 4242 4242 4242 4242")
        self.driver.find_element(*cardExpiry).send_keys("10/23")
        self.driver.find_element(*cardCvc).send_keys("234")
        self.driver.find_element(*billingName).send_keys("tet")
        time.sleep(1)
        self.driver.find_element_by_xpath('//*[@id="root"]/div/div/div[2]/div/div[2]/form/div[2]/div[4]/div[2]/button/div[3]').click()

        done = (By.XPATH, '//*[@id="app"]/div/div[4]/div/div/div[2]/div/div[4]/div')
        WebDriverWait(self.driver, 30, 0.5).until(expected_conditions.presence_of_element_located(done))
        self.driver.find_element(*done).click()
        self.driver.quit()


if __name__ == "__main__":
    # 收银台相关
    rps_id = "464075471d6542d492c3aa1517eadf08"
    user_id = "100144"
    token = "eyJhbGciOiJIUzI1NiJ9.eyJpdGMiOiI4NiIsImlzcyI6IlJPWEUiLCJhdWQiOiIxMDAxNDQiLCJzdWIiOiJVU0VSX0xPR0lOIiwibmJmIjoxNjM2MzYxNzc5fQ.ltOdtqDjgUrj9d88IHD90KDD_4ggL-94OXhAIATUSiY"
    url = f"https://test-checkout.roxe.io/#/index?userId={user_id}&loginToken={token}&transactionId={rps_id}&appKey=adfasdas"

    # 打开收银台，选择card支付
    client = CheckOut()
    client.accessWebsite(url)
    client.selectCard()
