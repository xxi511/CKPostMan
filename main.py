import requests
import time
import hashlib
import re
from bs4 import BeautifulSoup as bs

from tkinter import messagebox, Tk, LEFT, X, Text, RIGHT, END
from tkinter.ttk import Label, Button, Entry, Progressbar, Frame, Style
import tkinter.font as tkFont


class PosterUI(Frame): 
    def __init__(self, parent):
        Frame.__init__(self, parent)
        self.pack()
        self.parent = parent
        self.parent.title('CKPostMan')
        st = tkFont.Font(family='song ti', size=12)

        self.userFrame = Frame(self)
        self.userFrame.pack(fill=X, expand=1)
        self.idlabel = Label(self.userFrame, text='帳號：', font=st)
        self.idlabel.pack(pady=10, side=LEFT)
        self.idEntry = Entry(self.userFrame)
        self.idEntry.pack(pady=10, side=LEFT)
        self.pwlabel = Label(self.userFrame, text='密碼：', font=st)
        self.pwlabel.pack(padx=5, pady=10, side=LEFT)
        self.pwEntry = Entry(self.userFrame, show='*')
        self.pwEntry.pack(pady=10, side=LEFT)
        self.send = Button(self.userFrame, text='send', command=self.clickSend)
        self.send.pack(side=RIGHT)

        self.rlable = Label(self, text='收件者：', font=st)
        self.rlable.pack(fill=X)
        self.rtextarea = Text(self, height=5)
        self.rtextarea.pack(fill=X)

        self.mlable = Label(self, text='訊息內容：', font=st)
        self.mlable.pack(fill=X, pady=10)
        self.mtextarea = Text(self, height=5)
        self.mtextarea.pack(fill=X)

        self.createProgressFrame(st)
        self.bar = Progressbar(self, orient="horizontal",
                               mode="determinate")
        self.bar.pack(fill=X)
        self.bar['value'] = 0

    def createProgressFrame(self, st):
        self.progressFrame = Frame(self)
        self.progressFrame.pack(fill=X, expand=1, pady=10)

        self.progressTitle = Label(self.progressFrame, text='發送進度：', font=st)
        self.progressTitle.pack(side=LEFT)
        self.progressLabel = Label(self.progressFrame, text='0/0', font=st)
        self.progressLabel.pack(side=LEFT)

    def clickSend(self):
        infoDic, errMsg = self.isAllDataFill()
        self.send.config(state="disabled")
        if errMsg is not '':
            messagebox.showerror('錯誤', errMsg)
            self.send.config(state="active")
            return

        # Start a session so we can have persistant cookies
        session = requests.session()
        agent = {'user-agent': 'Mozilla/5.0 (X11; U; Linux i686) Gecko/20071127 Firefox/2.0.0.11'}
        login, errMsg = self.login(session, agent, infoDic)
        if not login:
            messagebox.showerror('錯誤', errMsg)
            self.send.config(state="active")
            return

        newMsg = self.processingMsg(infoDic['msg'])
        total = len(infoDic['receiver'])
        self.bar["maximum"] = total

        failed = []
        for idx, name in enumerate(infoDic['receiver']):
            sucess = self.sendMsg(session, agent, name, newMsg)
            self.bar['value'] = idx + 1
            self.progressLabel['text'] = '{}/{}'.format(idx+1, total)
            self.update()
            if not sucess:
                failed.append(name)
            elif sucess and idx < total-1:
                time.sleep(30)

        if len(failed) == 0:
            messagebox.showinfo(message='發送完畢')
        else:
            err = ','.join(failed)
            messagebox.showerror('失敗名單', err)

        self.send.config(state="active")

    def isAllDataFill(self):
        '''
        check if all data are filled
        :return: tuple, (infoDic, errMsg)
        '''
        idStr = self.idEntry.get().strip()
        pwStr = self.pwEntry.get().strip()
        reciver = self.rtextarea.get('1.0', END).strip()
        msg = self.mtextarea.get('1.0', END).strip()
        if idStr is '':
            return {}, '請輸入帳號'
        elif pwStr is '':
            return {}, '請輸入密碼'
        elif reciver is '':
            return {}, '請填入收件者，每行一位'
        elif msg is '':
            return {}, '不可以發送空消息'
        else:
            info = {
                'idStr': idStr,
                'pwStr': pwStr,
                'receiver': self.rmDuplicates(reciver.split('\n')),
                'msg': msg
            }
            return info, ''

    def rmDuplicates(self, ori):
        new = [person.strip() for person in ori if person is not '']
        return new

    def login(self, session, agent, infoDic):
        '''
        CK login
        :param session: session
        :param agent: user agent
        :param infoDic: user info dic
        :return: tuple, (success, errMsg)
        '''
        hashedPW = pwhash(infoDic['pwStr'])
        login_data = {
            'username': infoDic['idStr'],
            'password': hashedPW,
            'quickforward': 'yes',
            'handlekey': 'ls'
        }

        loginUrl = 'https://ck101.com/member.php?mod=logging&action=login&loginsubmit=yes&infloat=yes&lssubmit=yes&inajax=1'
        login = session.post(loginUrl, data=login_data, headers=agent)
        resp = login.text
        if '歡迎您回來' in resp:
            return True, ''
        else:
            find = re.findall("CDATA\[.*<script type=", resp, re.U)[0]
            return False, find[6:-13]

    def sendMsg(self, session, agent, name, msg):
        '''
        Send Message to name
        :param session: session
        :param agent: user agent
        :param name: user name
        :param msg: message
        :return: tuple, (success, name)
        '''
        pageUrl = 'https://ck101.com/space-username-{}.html'.format(name)
        data = bs(session.get(pageUrl, headers=agent).text, 'lxml')
        if '您指定的用戶空間不存在' in data.text:
            return False
        uid = data.find('input', {'name': 'id'})['value']
        formhash = data.find('input', {'name': 'formhash'})['value']

        msgData = {
            'pmsubmit': 'true',
            'touid': uid,
            'formhash': formhash,
            'handlekey': 'showMsgBox',
            'message': msg,
            'messageappend': ''
        }
        msgUrl = 'https://ck101.com/home.php?mod=spacecp&ac=pm&op=send&touid={}&inajax=1'.format(uid)
        msg = session.post(msgUrl, data=msgData, headers=agent).text
        return '操作成功' in msg

    def processingMsg(self, rawMsg):
        '''
        add url tag in url string
        :param rawMsg:
        :return: msg after processing
        '''
        newMsg = rawMsg
        pattern1 = r'http[s]?://[a-zA-Z.]{1,}'
        pattern2 = r'(?<!//)www[a-zA-Z.]{1,}'
        res1 = re.findall(pattern1, rawMsg, re.U)
        res2 = re.findall(pattern2, rawMsg, re.U)
        for res in res1+res2:
            new = '[url]{}[/url]'.format(res)
            newMsg = newMsg.replace(res, new)

        return newMsg

def pwhash(origin):
    # password hash
    md5 = hashlib.md5()
    md5.update(origin.encode('utf-8'))
    return md5.hexdigest()

if __name__ == '__main__':
    root = Tk()
    root.resizable(0, 0)
    root.geometry("600x300") # wxh
    app = PosterUI(root)
    app.mainloop()






