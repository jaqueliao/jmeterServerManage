### 一个jmeter的slave机器管理脚本
因在进行压力测试的时候，经常需要进行分布式压测，使用多台slave，每次测试的时候逐台操作太过麻烦，就使用python写了个脚本可进行批量操作

### 使用说明

1. 执行setup.bat安装python依赖包
2. 编辑slaveConfig.csv文件，将所有slave配置写入其中
3. 执行start.bat启动命令行
 
所有需要服务器列表的命令中，all代表所有；只有run命令需要的服务器列表参数是使用逗号分隔，其他都是空格分隔的  
q/quit/exit: 退出命令行模式  
ls/list: 列出slaveConfig.csv配置文件内的内容  
start: 启动某个机器的jmeter服务，例如：start 1 2,启动配置文件内id为1和2的服务器上jmeter-server，或者start 192.168.1.1 192.168.1.2  
stop: 停止某个机器的jmeter服务，参数同start  
restart: 重启某个机器的jmeter服务，参数同start  
status: 查看某个机器jmeterjmeter相关服务的状态，不带id/ip则为全部  
init：初始化服务器状态  
upload: 上传文件，格式为：upload file targetDir serverList,如：upload test.csv /root 1 2  
help: 帮助  
run/sh: 在目标服务器上运行命令，命令格式为：run cmdStatement serverList,如：run ls -al 1,2，第一个参数为run或sh，最后一个参数为服务器列表，多个用逗号分割，all表示所有，中间为要在服务器上运行的命令  

本脚本自动安装时默认使用的软件如下：
python-3.8.3-amd64.exe
jdk-8u261-linux-x64.tar.gz
apache-jmeter-5.3.zip
可以在脚本中修改为自己所使用的版本并下载好对应的文件放在脚本同级目录中