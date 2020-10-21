#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2020/10/18 11:02 AM
# @Author  : zinber
# @Site    : 
# @Desc    :
# @File    : main.py
# @Software: PyCharm

import re
import execjs
import requests
import urllib.parse
from PIL import Image
from bs4 import BeautifulSoup
import re
import io
from pathlib import Path
import os
import json
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED


class Color:
    Black = 0
    Red = 1
    Green = 2
    Yellow = 3
    Blue = 4
    Magenta = 5
    Cyan = 6
    White = 7

class Mode:
    Foreground = 30
    Background = 40
    ForegroundBright = 90
    BackgroundBright = 100

def tcolor(c, m=Mode.Foreground):
    return '\033[{}m'.format(m + c)

def treset():
    return '\033[0m'

def log(content,c=Color.White):
    print('{begin}{txt}{end}'.format(begin=tcolor(c),txt=content,end=treset()))

def download_image(url):
    # log('download_image:{}'.format(url))
    pic = None
    try:
        pic = requests.get(url, timeout=10)
    except requests.exceptions.ConnectionError:
        log('【错误】当前图片无法下载',Color.Red)
    
    if pic and pic.status_code == 200:
        # log("URL:{} 下载成功！".format(url),Color.Green)
        return Image.open(io.BytesIO(pic.content))
    return None
class Mangabz:
    """
    日本漫画漫画章节图片下载
    """
    def __init__(self, url,name):
        self.url = url
        self.session = requests.Session()
        self.headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36",
                        "Referer": self.url,
                        "Cookie": "image_time_cookie=17115|637270678077155170|2",
                        }
        self.name=name
        self.images=[]

    def get_chapter_argv(self):
        res = requests.get(self.url, headers=self.headers, timeout=10)
        mangabz_cid = re.findall("MANGABZ_CID=(.*?);", res.text)[0]
        mangabz_mid = re.findall("MANGABZ_MID=(.*?);", res.text)[0]
        page_total = re.findall("MANGABZ_IMAGE_COUNT=(.*?);", res.text)[0]
        mangabz_viewsign_dt = re.findall("MANGABZ_VIEWSIGN_DT=\"(.*?)\";", res.text)[0]
        mangabz_viewsign = re.findall("MANGABZ_VIEWSIGN=\"(.*?)\";", res.text)[0]
        return (mangabz_cid, mangabz_mid, mangabz_viewsign_dt, mangabz_viewsign, page_total)

    def get_images_js(self, page, mangabz_cid, mangabz_mid, mangabz_viewsign_dt, mangabz_viewsign):
        url = self.url + "chapterimage.ashx?" + "cid=%s&page=%s&key=&_cid=%s&_mid=%s&_dt=%s&_sign=%s" % (mangabz_cid, page, mangabz_cid, mangabz_mid, urllib.parse.quote(mangabz_viewsign_dt), mangabz_viewsign)
        res = self.session.get(url, headers=self.headers, timeout=10)
        self.headers["Referer"] = res.url
        return res.text


    def download_image(self,url,i,page_total):
            #print("开始下载:第{}张！".format(i))
            # print(i,url)
            pic = None
            try:
                pic = requests.get(url, timeout=10)
            except requests.exceptions.ConnectionError:
                log('【错误】当前图片无法下载',Color.Red)
            
            if pic and pic.status_code == 200:
                log("第{}张下载成功！".format(i),Color.Green)
                self.images.append(Image.open(io.BytesIO(pic.content)))
                if i == page_total:
                    log("开始拼图")
                    # self.merge_images(page_total)
                    self.images[0].save(self.name+'.pdf', "PDF", resolution=100.0,
                                   save_all=True, append_images=self.images[1:])
                    log("保存章节:{}.pdf 成功!".format(self.name))
                return True
            return False

    def run(self):
        mangabz_cid, mangabz_mid, mangabz_viewsign_dt, mangabz_viewsign, page_total = self.get_chapter_argv()
        log("章节:{},一共有{}张图片".format(self.name,page_total))
        links=[]
        for i in range(int(page_total)):
            i += 1
            js_str = self.get_images_js(i, mangabz_cid, mangabz_mid, mangabz_viewsign_dt, mangabz_viewsign)
            imagesList = execjs.eval(js_str)
            # print(imagesList[0])
            links.append(imagesList[0])
            # for j in range(3): # retry 3 times if download failed
            #     if self.download_image(imagesList[0],i,int(page_total)):
            #         break
        executor = ThreadPoolExecutor()
        all_task=[executor.submit(download_image, (url)) for url in links]
        wait(all_task, return_when=ALL_COMPLETED)
        images=[future.result() for future in all_task]
        images[0].save(self.name+'.pdf', "PDF", resolution=100.0,
                                   save_all=True, append_images=images[1:])
        log("保存章节:{}.pdf 成功!".format(self.name))
            

#dir is not keyword
def makedir_and_cd(whatever):
  try:
    os.makedirs(whatever)
  except OSError:
    pass
  # let exception propagate if we just can't
  # cd into the specified directory
  os.chdir(whatever)


    

if __name__ == '__main__':
    website='http://mangabz.com'
    cfg=None
    with open('config.json') as json_file:
        cfg = json.load(json_file)
    if not cfg:
        log('读取config.json错误',Color.Red)
        exit(1)
    home_path=os.getcwd()
    for (anim_title,anim_cfg) in cfg.items():
        # print(anim_title,anim_cfg['url'])
        ret = requests.get(url='{}/{}/'.format(website,anim_cfg['url']))
        ret.encoding = ret.apparent_encoding
        soup = BeautifulSoup(ret.text, 'html.parser')  # 使用lxml则速度更快
        anim_name='default'
        for span in soup.find_all('p', class_='detail-info-title'):
            if span.text:
                anim_name=span.text.strip()
                break
        log('漫画标题为:{}'.format(anim_name),Color.Green)
        os.chdir(home_path)
        makedir_and_cd(anim_name)
        alinks = soup.select('a')
        download_count = 0
        for link in alinks:
            # print(type(link.attrs),link.attrs)
            # print('class' in link.attrs.keys(),link.text)
            if 'class' in link.attrs.keys() and 'detail-list-form-item' in link['class']:
                # print(link['href'],re.sub(' +', '', link.text))
                download_count = download_count + 1
                file_name=re.sub(' +', '', link.text)
                if Path(file_name+'.pdf').exists():
                    continue
                mangabz = Mangabz(url='{}{}'.format(website,link['href']),name=file_name)
                mangabz.run()
        log('漫画:{},下载完成,下载章节数量:{}!'.format(anim_title,download_count),Color.Green)
    # mangabz = Mangabz(url='http://mangabz.com/m119688/', name='test')
    # mangabz.merge_images(21)
    # mangabz.run()
