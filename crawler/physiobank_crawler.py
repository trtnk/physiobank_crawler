# -*- coding: utf-8 -*-
"""
@file physiobank_crawler.py
@version 1.0
@author trtnk
@date 2020/12/03
@brief crawler process
@details crawler process
@warning
@note
"""
from selenium import webdriver
from selenium.webdriver.support.select import Select
from selenium.webdriver.chrome.options import Options
import shutil
import requests
import base64
import os
import time


class CrawlerBase:
    def __init__(self, driver_path, url, headless=False, proxy=None, proxy_auth=None, wait_sec=2):
        option = Options()
        if headless:
            option.add_argument("--headless")
        if proxy is not None:
            option.add_argument(f"--proxy-server=http://{proxy}")
            if proxy_auth is not None:
                option.add_argument(f"--proxy-auth={proxy_auth}")
                self.proxy_dict = {
                    "http": f"http://{proxy_auth}@{proxy}/",
                    "https": f"http://{proxy_auth}@{proxy}/"
                }
            else:
                self.proxy_dict = {
                    "http": f"http://{proxy}/",
                    "https": f"http://{proxy}/"
                }
        else:
            self.proxy_dict = None
        self.driver = webdriver.Chrome(executable_path=driver_path, options=option)
        self.url = url
        self.wait_sec = wait_sec

    # サイトを開く
    def open(self):
        print(f"{self.url} open!")
        self.driver.get(self.url)

    def close(self):
        self.driver.quit()

    # ドロップダウン要素を取得
    def get_selectbox_element(self, name=None, id_=None):
        if name is None and id is None:
            print("引数を指定してください")
            return
        if name is not None:
            dropdown = self.driver.find_element_by_xpath(f"//select[@name='{name}']")
        elif id_ is not None:
            dropdown = self.driver.find_element_by_xpath(f"//select[@id='{id_}']")
        select = Select(dropdown)
        return select

    # ドロップダウン要素を取得
    def get_selectbox_values(self, name=None, id_=None, select_obj=None):
        if select_obj is None:
            select_obj = self.get_selectbox_element(name=name, id_=id_)
        return [select_obj.options[i].text for i in range(len(select_obj.options))]

    # セレクトボックスで選択されているテキストを返す
    def get_selected_value(self, name=None, id_=None, select_obj=None):
        if select_obj is None:
            select_obj = self.get_selectbox_element(name=name, id_=id_)
        return select_obj.first_selected_option.text

    # ドロップダウンを選択
    def input_selectbox_by_text(self, text, name=None, id_=None, select_obj=None):
        if select_obj is None:
            select_obj = self.get_selectbox_element(name=name, id_=id_)
        select_obj.select_by_visible_text(text)


class PhysioBankCrawlerBase(CrawlerBase):
    def __init__(self, driver_path='/driver-dir/chromedriver.exe', url='https://archive.physionet.org/cgi-bin/atm/ATM',
                 headless=False, proxy=None, proxy_auth=None):
        super().__init__(driver_path, url, headless, proxy, proxy_auth)
        self.open()
        # Optional values
        self.dataset_list = self.get_selectbox_values(name="database")
        self.length_list = ["10 sec", "1 min", "1 hour", "12 hours", "to end"]
        self.time_format_list = ["time/date", "elapsed time", "hours", "minutes", "seconds", "samples"]
        self.data_format_list = ["standard", "high precision", "raw ADC units"]

    def set_dataset(self, dataset):
        self.input_selectbox_by_text(dataset, name="database")

    def get_selected_dataset(self):
        return self.get_selected_value(name="database")

    def set_signal(self, signal):
        self.input_selectbox_by_text(signal, name="signal")

    def get_selected_signal(self):
        return self.get_selected_value(name="signal")

    def set_record(self, record):
        self.input_selectbox_by_text(record, name="rbase")

    def get_selected_record(self):
        return self.get_selected_value(name="rbase")

    def save_chart_img(self, file_save_path):
        ## 画像の検索にはxpathを使う
        img = self.driver.find_elements_by_xpath("//img[contains(@src, 'chart.png')]")
        if img:
            img_src = img[0].get_attribute("src")
        else:
            print("画像無し")

        #Base64エンコードされた画像をデコードして保存する。
        if "base64," in img_src:
            with open(file_save_path, "wb") as f:
                f.write(base64.b64decode(img_src.split(",")[1]))

        #画像のURLから画像を保存する。
        else:
            if self.proxy_dict is None:
                res = requests.get(img_src, stream=True)
            else:
                res = requests.get(img_src, stream=True, proxies=self.proxy_dict)
            with open(file_save_path, "wb") as f:
                shutil.copyfileobj(res.raw, f)

    def next_page_exist(self):
        # 右矢印（ページ送り）があるかどうかを検査
        if self.driver.find_elements_by_name("right_arrow"):
            return True
        else:
            return False

    def move_next_page(self):
        # 右矢印（ページ送り）があるかどうかを検査して移動
        if self.driver.find_elements_by_name("right_arrow"):
            # あった場合はクリック
            self.driver.find_element_by_name("right_arrow").click()
            return True
        else:
            return False

    def move_first_page(self):
        # 各レコードのデータの頭に飛ぶ
        elements = self.driver.find_elements_by_xpath("//input[@value='|<<']")
        if elements:
            elements[0].click()

    def move_next_record(self):
        # 次のレコードへ遷移
        elements = self.driver.find_elements_by_xpath("//input[@value='Next record']")
        if elements:
            elements[0].click()

    def set_output_parameter(self, length=None, time_format=None, data_format=None):
        if length is not None:
            if length not in self.length_list:
                raise ValueError(f"length is neccesary in {self.length_list}")
            else:
                self.driver.find_element_by_xpath(f"//label[contains(text(), '{length}')]").click()
                time.sleep(self.wait_sec)
        if time_format is not None:
            if time_format not in self.time_format_list:
                raise ValueError(f"time_format is neccesary in {self.time_format_list}")
            else:
                self.driver.find_element_by_xpath(f"//label[contains(text(), '{time_format}')]").click()
                time.sleep(self.wait_sec)
        if data_format is not None:
            if data_format not in self.data_format_list:
                raise ValueError(f"data_format is neccesary in {self.data_format_list}")
            else:
                self.driver.find_element_by_xpath(f"//label[contains(text(), '{data_format}')]").click()
                time.sleep(self.wait_sec)


class PhysioBankCrawler(PhysioBankCrawlerBase):
    def __init__(self, driver_path='/driver-dir/chromedriver.exe', url='https://archive.physionet.org/cgi-bin/atm/ATM',
                 dataset=None, headless=False, proxy=None, proxy_auth=None, data_type="image", save_dir="."):
        super().__init__(driver_path, url, headless, proxy, proxy_auth)

        self.__signal_list = None
        self.__record_list = None
        self.__signal = None
        self.__dataset = None

        if dataset is not None:
            self.dataset = dataset
        self.save_dir = save_dir
        self.data_type = data_type

    @property
    def dataset(self):
        return self.__dataset

    @property
    def signal(self):
        return self.__signal

    @property
    def signal_list(self):
        return self.__signal_list

    @property
    def record_list(self):
        return self.__record_list

    @property
    def data_type(self):
        return self.__data_type

    @property
    def save_dir(self):
        return self.__save_dir

    @dataset.setter
    def dataset(self, arg):
        if arg not in self.dataset_list:
            raise ValueError(f"Input value:{arg} is not in dataset list. Please input a value in {self.dataset_list}")
        self.set_dataset(arg)
        self.__dataset = arg
        self.__signal_list = self.get_selectbox_values(name="signal")
        self.__record_list = self.get_selectbox_values(name="rbase")

    @signal.setter
    def signal(self, arg):
        if arg not in self.signal_list:
            raise ValueError(f"Input value:{arg} is not in signal list. Please input a value in {self.signal_list}")
        self.set_signal(arg)
        self.__signal = arg

    @data_type.setter
    def data_type(self, arg):
        if arg not in ["image"]:
            raise ValueError(f"Input data_type:{arg} is not in {self.dataset_list}")
        self.__data_type = arg

    @save_dir.setter
    def save_dir(self, arg):
        if not os.path.exists(arg):
            raise ValueError(f"{arg} is not exist path.")
        self.__save_dir = arg

    def crawling_all_record(self, start_record=None):
        if self.dataset is None:
            raise Exception("You must set dataset before crawling.")
        if self.signal is None:
            raise Exception("You must set signal before crawling.")

        self.set_signal(self.signal)

        # set start_record (dafault: first value)
        if start_record is not None and start_record in self.record_list:
            self.set_record(start_record)
            start_record_idx = self.record_list.index(start_record)
        else:
            self.set_record(self.record_list[0])
            start_record_idx = 0

        # make directory
        save_dir = f"{self.save_dir}/{self.signal}"
        if not os.path.exists(save_dir):
            os.makedirs(save_dir, exist_ok=True)

        self.move_first_page()
        skip_flag = False
        for record in self.record_list[start_record_idx:]:
            if not skip_flag and record != self.get_selected_record():
                print(record, self.get_selected_record())
                raise Exception("Error: record is different.")
            data_idx = 1
            while(True):
                if self.data_type == "image":
                    img_file_name = f"{record}_{self.signal}_{data_idx}.png".replace(r"/", r"_")
                    img_file_path = f"{save_dir}/{img_file_name}"
                    if os.path.exists(img_file_path):
                        skip_flag = True
                        break
                    elif skip_flag:
                        skip_flag = False
                        self.set_record(record)
                        time.sleep(self.wait_sec)
                        self.move_first_page()
                        time.sleep(self.wait_sec)
                    self.save_chart_img(img_file_path)
                    time.sleep(self.wait_sec)
                    data_idx += 1
                    if not self.move_next_page():
                        break
            # 次のrecord
            if not skip_flag:
                self.move_next_record()
                time.sleep(self.wait_sec)
                self.move_first_page()
                time.sleep(self.wait_sec)

    # crawling all singnal
    def crawling_all_signal_record(self, start_record=None):
        for signal in self.signal_list:
            print(f"Crawling {signal} start.")
            self.signal = signal
            self.crawling_all_record(start_record=start_record)
