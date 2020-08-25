from socket import timeout

import paramiko
import sys
import csv
import os


class JmeterShell(object):

    def __init__(self, host, port, username, password, jmeter_home=None):
        self.__host = host
        self.__username = username
        self.__homedir = '/%s/' % (self.__username if self.__username == 'root' else 'home/'+self.__username,)
        self.__jmeterHome = jmeter_home
        self.__sftp = None
        self.__ssh = paramiko.SSHClient()
        # 创建一个ssh的白名单
        self.__know_host = paramiko.AutoAddPolicy()
        self.__ssh.set_missing_host_key_policy(self.__know_host)
        # 连接服务器
        self.__connected = False
        try:
            self.__ssh.connect(
                hostname=host,
                port=port,
                username=username,
                password=password,
                timeout=3
            )
        except timeout:
            print('连接超时，请确认 %s 的配置是否正确' % self.__host)
        else:
            self.__connected = True

    def close(self):
        self.__ssh.close()

    def getSftp(self):
        if self.__sftp is None:
            self.__sftp = self.__ssh.open_sftp()
        return self.__sftp

    def runCommand(self, command):
        if not self.__connected:
            return '连接失败'
        stdin, stdout, stderr = self.__ssh.exec_command(command, timeout=60)
        return stdout.read().decode()

    def runStatus(self):
        if not self.__connected:
            return False, False
        psCommand = 'ps -efww|grep -w jmeter-server|grep -v grep|cut -c 9-15'
        result = self.runCommand(psCommand)
        if result.strip() == '':
            return False, False
        else:
            runStatusStr = 'tail -n 1 %snohup_jmeter_server.log' % self.__jmeterHome
            result = self.runCommand(runStatusStr)
            if 'Starting' in result.strip():
                return True, True
            else:
                return True, False

    def uploadFile(self, file, target):
        if not self.__connected:
            return False
        if not os.path.exists(file):
            print('待上传文件 %s 不存在，请确认' % file)
            return False
        if not os.path.basename(target):
            # 若目标参数只是目录，则上传后的文件使用源文件名传至此目录
            target = os.path.join(target, os.path.basename(file))
        print('%s 开始上传文件 %s 至 %s' % (self.__host, file, target))
        try:
            self.getSftp().put(file, target)
        except FileNotFoundError:
            print('目标路径 %s 错误，路径或文件不存在' % target)
        except IOError:
            print('目标路径 %s 错误，无法写入' % target)
        else:
            print('%s 上传文件成功' % self.__host)

    def checkJmeterHome(self):
        if not self.__connected:
            return False
        if self.__jmeterHome is not None and self.__jmeterHome != '':
            testCommand = 'test -e %s;echo $?' % self.__jmeterHome
            result = self.runCommand(testCommand)
            if result.strip() == '0':
                return True
        print('配置文件中服务器 %s 的 jmetrHome配置有误，请检查' % self.__host)
        return False

    def findJmeterServer(self):
        if not self.__connected:
            return
        findCommand = 'find / -name jmeter-server'
        result = self.runCommand(findCommand).split('\n')
        jmeterServerList = [x for x in result if 'jmeter-server' in x]
        if len(jmeterServerList) == 0:
            print("在此服务器 %s 上未找到jmeter" % self.__host)
            return
        if self.__jmeterHome is None:
            jmeterServer = jmeterServerList[0]
            self.__jmeterHome = jmeterServer[:-17]
        else:
            for js in jmeterServerList:
                if self.__jmeterHome in js:
                    break
            else:
                jmeterServer = jmeterServerList[0]
                self.__jmeterHome = jmeterServer[:-17]
        print("在此服务器 %s 上找到jmeter路径为：%s" % (self.__host, self.__jmeterHome))

    def start(self):
        if not self.__connected:
            return
        if self.runStatus()[0]:
            print('%s 内jmeter-server正在运行中，不需启动' % self.__host)
            return
        if not self.checkJmeterHome():
            self.findJmeterServer()
        jmeterServer = '%sbin/jmeter-server' % self.__jmeterHome
        startCommand = 'nohup sh %s -Djava.rmi.server.hostname=%s > %snohup_jmeter_server.log 2>&1 &' % (
            jmeterServer, self.__host, self.__jmeterHome)
        # print(startCommand)
        print('%s 开始启动jmeter-server……' % self.__host)
        self.runCommand(startCommand)
        print('%s 启动jmeter-server成功' % self.__host)

    def stop(self):
        if not self.__connected:
            return
        command = 'ps -efww|grep -w jmeter-server|grep -v grep|cut -c 9-18|xargs kill -9'
        print('%s 开始停止jmeter-server……' % self.__host)
        self.runCommand(command)
        print('%s 停止jmeter-server完成' % self.__host)

    def restart(self):
        self.stop()
        self.start()

    def installJmeter(self):
        if self.checkJmeterHome():
            print('%s 已经安装jmeter，跳过' % self.__host)
            return
        print('%s 开始上传jmeter安装包' % self.__host)
        self.uploadFile('apache-jmeter-5.3.zip', '%sapache-jmeter-5.3.zip' % self.__homedir)
        print('%s 上传jmeter安装包完成' % self.__host)
        unzipCommand = 'unzip -o apache-jmeter-5.3.zip'
        self.runCommand(unzipCommand)
        print('%s 解压jmeter安装包完成' % self.__host)

    def installJdk(self):
        if self.checkJdk():
            print('%s 已经安装JDK，跳过' % self.__host)
            return
        if self.__username != 'root':
            print('%s 当前配置的用户不是root，无法安装JDK' % self.__host)
            return
        print('%s 开始上传JDK安装包' % self.__host)
        self.uploadFile('jdk-8u261-linux-x64.tar.gz', '/root/jdk-8u261-linux-x64.tar.gz')
        print('%s 上传JDK安装包完成' % self.__host)
        unzipCommand = 'tar -zxf jdk-8u261-linux-x64.tar.gz'
        self.runCommand(unzipCommand)
        print('%s 解压jdk安装包完成' % self.__host)
        setPathCommand = '''echo 'export JAVA_HOME="/root/jdk1.8.0_261"' >> /etc/profile;echo 'export JRE_HOME="$JAVA_HOME/jre"' >> /etc/profile;echo 'export PATH="$PATH:$JAVA_HOME/bin:$JRE_HOME/bin"' >> /etc/profile;source /etc/profile'''
        self.runCommand(setPathCommand)
        print('%s JDK环境变量配置完成' % self.__host)

    def setPortRelease(self):
        if self.__username != 'root':
            print('%s 当前配置的用户不是root，无法执行此命令' % self.__host)
            return
        releaseCommand = 'echo 15 > /proc/sys/net/ipv4/tcp_fin_timeout;echo 1 > /proc/sys/net/ipv4/tcp_tw_reuse;echo 1 > /proc/sys/net/ipv4/tcp_tw_recycle;sysctl -p'
        self.runCommand(releaseCommand)
        print('%s 修改tcp超时参数配置完成,执行的命令为：%s' % (self.__host, releaseCommand))

    def init(self):
        if not self.__connected:
            return False
        self.installJdk()
        self.installJmeter()
        self.setPortRelease()

    def checkJdk(self):
        if not self.__connected:
            return False
        testCommand = 'java -version;echo $?'
        result = self.runCommand(testCommand)
        if result.strip() == '0':
            return True
        return False


def listAll(*args):
    with open('slaveConfig.csv', 'r', encoding='utf-8')as f:
        f_csv = csv.reader(f)
        for row in f_csv:
            print('\t'.join(row))


def getTargetSlave(*args):
    slaveList = []
    with open('slaveConfig.csv', 'r', encoding='utf-8')as f:
        f_csv = csv.reader(f)
        for row in f_csv:
            if row[-1] == '1':
                slaveList.append(row)
    if len(args) == 0:
        print('未发现参数，需要id或者ip')
    if args[0] == 'all':
        return slaveList
    else:
        targetList = []
        for arg in args:
            for slave in slaveList:
                if arg == slave[0] or arg == slave[2]:
                    targetList.append(slave)
        return targetList


def status(*args):
    if len(args) == 0:
        targetList = getTargetSlave('all')
    else:
        targetList = getTargetSlave(*args)
    if not targetList:
        print('未在列表中找到对应的jmeter-server服务器或者服务器未启用，请检查参数')
        return
    print('\t'.join(('id', 'name', 'ip             ', 'jdk   ', 'jmeter ', '服务状态', '执行状态')))
    for slave in targetList:
        id, name, ip = slave[0], slave[1], slave[2]
        jmeterShell = JmeterShell(slave[2], slave[5], slave[3], slave[4], slave[6])
        jdk = jmeterShell.checkJdk()
        jmeter = jmeterShell.checkJmeterHome()
        server, test = jmeterShell.runStatus()
        print('\t'.join((id, name, ip, '已安装' if jdk else '未安装', '已安装' if jmeter else '未安装', '运行中' if server else '未启动',
                         '测试中' if test else '未开始')))
        jmeterShell.close()


def start(*args):
    if len(args) == 0:
        print('未发现参数，需要id或者ip')
        return
    targetList = getTargetSlave(*args)
    if not targetList:
        print('未在列表中找到对应的jmeter-server服务器，请检查参数')
        return
    for slave in targetList:
        jmeterShell = JmeterShell(slave[2], slave[5], slave[3], slave[4], slave[6])
        jmeterShell.start()
        jmeterShell.close()


def stop(*args):
    if len(args) == 0:
        print('未发现参数，需要id或者ip')
        return
    targetList = getTargetSlave(*args)
    if not targetList:
        print('未在列表中找到对应的jmeter-server服务器，请检查参数')
        return
    for slave in targetList:
        jmeterShell = JmeterShell(slave[2], slave[5], slave[3], slave[4], slave[6])
        jmeterShell.stop()
        jmeterShell.close()


def restart(*args):
    if len(args) == 0:
        print('未发现参数，需要id或者ip')
        return
    targetList = getTargetSlave(*args)
    if not targetList:
        print('未在列表中找到对应的jmeter-server服务器，请检查参数')
        return
    for slave in targetList:
        jmeterShell = JmeterShell(slave[2], slave[5], slave[3], slave[4], slave[6])
        jmeterShell.restart()
        jmeterShell.close()


def upload(*args):
    if len(args) < 3:
        print('参数错误，格式为：upload sourceFile targetFile serverList,如：upload D:\\test.csv /root/test.csv 1 2')
        return
    targetList = getTargetSlave(*args[2:])
    if not targetList:
        print('未在列表中找到对应的jmeter-server服务器，请检查参数')
        return
    for slave in targetList:
        jmeterShell = JmeterShell(slave[2], slave[5], slave[3], slave[4], slave[6])
        jmeterShell.uploadFile(args[0], args[1])
        jmeterShell.close()


# 在对应服务器上执行命令，第一个参数为run，最后一个参数为‘,’分隔的服务器id，中间为需要执行的命令,切勿执行无法停止的命令
def run(*args):
    if len(args) < 2:
        print('参数错误，格式为：run "cmd" serverList,如：run ls -al 1,2')
        return
    targetList = getTargetSlave(*args[-1].split(','))
    if not targetList:
        print('未在列表中找到对应的jmeter-server服务器，请检查参数，命令格式为：run cmdStatement serverList,如：run ls -al 1,2')
        return
    for slave in targetList:
        jmeterShell = JmeterShell(slave[2], slave[5], slave[3], slave[4], slave[6])
        print('开始在 %s 上执行：%s' % (slave[2], ' '.join(args[0:-1])))
        result = jmeterShell.runCommand(' '.join(args[0:-1]))
        print(result)
        jmeterShell.close()


def init(*args):
    if not os.path.exists('apache-jmeter-5.3.zip'):
        print('jmeter安装包不存在，请下载后放置于本脚本同目录下')
        return
    if not os.path.exists('jdk-8u261-linux-x64.tar.gz'):
        print('JDK 安装包不存在，请下载后放置于本脚本同目录下')
        return
    if len(args) == 0:
        print('未发现参数，需要id或者ip')
        return
    targetList = getTargetSlave(*args)
    if not targetList:
        print('未在列表中找到对应的jmeter-server服务器，请检查参数')
        return
    for slave in targetList:
        jmeterShell = JmeterShell(slave[2], slave[5], slave[3], slave[4], slave[6])
        jmeterShell.init()
        jmeterShell.close()


def _exit(*args):
    print('退出交互模式……')
    exit(0)

helped = False
def _help(*args):
    helpdoc = '''
    使用前需先编辑slaveConfig.csv文件，将所有slave配置写入其中。
    所有需要服务器列表的命令中，all代表所有；只有run命令需要的服务器列表参数是使用逗号分隔，其他都是空格分隔的
    q/quit/exit: 退出命令行模式
    ls/list: 列出slaveConfig.csv配置文件内的内容
    start: 启动某个机器的jmeter服务，例如：start 1 2,启动配置文件内id为1和2的服务器上jmeter-server，或者start 192.168.1.1 192.168.1.2
    stop: 停止某个机器的jmeter服务，参数同start
    restart: 重启某个机器的jmeter服务，参数同start
    status: 查看某个机器jmeterjmeter相关服务的状态，不带id/ip则为全部
    init：初始化服务器状态
    upload: 上传文件，格式为：upload file targetDir serverList,如：upload test.csv /root/ 1 2
    help: 帮助
    run/sh: 在目标服务器上运行命令，命令格式为：run cmdStatement serverList,如：run ls -al 1,2，第一个参数为run或sh，最后一个参数为服务器列表，多个用逗号分割，all表示所有，中间为要在服务器上运行的命令
    '''
    global helped
    helped = True
    print(helpdoc)


def doCmd(*cmdArgList):
    if len(cmdArgList) > 0 and cmdConfig.get(cmdArgList[0]):
        cmdConfig.get(cmdArgList[0])(*cmdArgList[1:])
    elif len(cmdArgList) == 0:
        # 命令行模式下未输入任何内容，就不执行任何动作；非命令行不带参执行会进入命令行模式
        pass
    else:
        print('%s 命令不存在，请重新输入' % cmdArgList[0])
        if not helped:
            _help()

# 命令行获取并执行用户输入的命令
def cmds():
    while True:
        command = input(">>> ")
        cmdArgList = command.split()
        doCmd(*cmdArgList)


# 命令与动作映射表
cmdConfig = {'q': _exit,
             'exit': _exit,
             'quit': _exit,
             'restart': restart,
             'rs': restart,
             'start': start,
             'stt': start,
             'stop': stop,
             'status': status,
             'sts': status,
             'init': init,
             'ls': listAll,
             'list': listAll,
             'help': _help,
             'upload': upload,
             'up': upload,
             'run': run,
             'sh': run
             }

args = sys.argv
if len(args) == 1:
    # 不带参执行会进入命令行模式
    print('进入命令行模式：')
    cmds()
else:
    # 带参就直接执行对应命令
    doCmd(*args[1:])
