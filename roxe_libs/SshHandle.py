import paramiko
import re
import subprocess


def connect_server(host_name, port, user_name, password=None, private_key_file=None):
    # 服务器连接信息
    p_key = paramiko.RSAKey.from_private_key_file(private_key_file) if private_key_file else None

    ssh = paramiko.SSHClient()

    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=host_name, port=port, username=user_name, password=password, pkey=p_key)
    return ssh


def ssh_jump_send_command(child, cmd, partterns):
    # 发送一条命令
    child.sendline(cmd)

    # 期望有命令行提示字符出现
    child.expect(partterns)

    # 将之前的内容都输出
    # print(child.before.decode('utf-8'))
    return child.before


def ssh_jump_connect(user, host, port, partterns, password):
    # 表示主机已使用一个新的公钥的消息
    import pexpect
    ssh_newkey = 'Are you sure you want to continue connecting'
    connStr = 'ssh {}@{} -p {}'.format(user, host, port)

    # 为ssh命令生成一个spawn类的对象
    child = pexpect.spawn(connStr)

    # 期望有ssh_newkey字符、提示输入密码的字符出现，否则超时
    ret = child.expect([pexpect.TIMEOUT, ssh_newkey, '[P|p]assword:'])

    # 匹配到超时TIMEOUT
    if ret == 0:
        print('[-] Error Connecting')
        return

    # 匹配到ssh_newkey
    if ret == 1:
        # 发送yes回应ssh_newkey并期望提示输入密码的字符出现
        child.sendline('yes')
    if ret == 2:
        child.sendline(password)
    try:
        ret = child.expect(partterns)
        if ret > 0:
            return child
    except pexpect.expect.TIMEOUT as e:
        print(e.args)


class SSHHandler:

    def __init__(self, host, port, user, pwd):
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(host, port=port, username=user, password=pwd)

        channel = self.ssh.invoke_shell()
        self.stdin = channel.makefile('wb')
        self.stdout = channel.makefile('r')

    def close(self):
        self.ssh.close()

    def execute(self, cmd):
        cmd = cmd.strip('\n')
        self.stdin.write(cmd + '\n')
        finish = 'end of stdOUT buffer. finished with exit status'
        echo_cmd = 'echo {} $?'.format(finish)
        self.stdin.write(echo_cmd + '\n')
        shin = self.stdin
        self.stdin.flush()
        shout = []
        sherr = []
        for line in self.stdout:
            if str(line).startswith(cmd) or str(line).endswith(echo_cmd):
                shout = []
            elif str(line).startswith(finish):
                exit_status = int(str(line).rsplit(maxsplit=1)[1])
                if exit_status:
                    sherr = shout
                    shout = []
                break
            else:
                shout.append(re.compile(r'(\x9B|\x1B\[)[0-?]*[ -/]*[@-~]').sub('', line).
                             replace('\b', '').replace('\r', ''))
        if shout and echo_cmd in shout[-1]:
            shout.pop()
        if shout and cmd in shout[0]:
            shout.pop(0)
        if sherr and echo_cmd in sherr[-1]:
            sherr.pop()
        if sherr and cmd in sherr[0]:
            sherr.pop(0)

        return shin, shout, sherr


class SSHServer:
    IS_LOCAL = False
    JUMP_HOST = None
    HOST = None
    PORT = 22
    USER = None
    PWD = None
    KEY_FILE = None

    ssh_server = None

    # 创建链接
    def connect_server(self):
        if self.IS_LOCAL: return None
        if self.JUMP_HOST:
            # 跳板机
            self.ssh_server = SSHHandler(self.HOST, self.PORT, self.USER, self.PWD)
            self.ssh_server.execute(self.JUMP_HOST)
        elif self.HOST:
            # ssh
            self.ssh_server = connect_server(self.HOST, self.PORT, self.USER, self.PWD, self.KEY_FILE)
        else:
            self.IS_LOCAL = True

        return self.ssh_server

    def close_server(self):
        if self.ssh_server: self.ssh_server.close()

    # 执行命令
    def exec_command(self, cmd):
        if self.IS_LOCAL or (self.ssh_server is None):
            # 本地执行
            stdout = subprocess.getoutput(cmd)
            shout = stdout.strip().split('\n')
        elif self.JUMP_HOST:
            # 执行跳板机命令
            shin, shout, sherr = self.ssh_server.execute(cmd)
            if sherr:
                shout += sherr
            # shout = str(shout).split('\n')
        else:
            # 执行ssh命令
            stdin, stdout, stderr = self.ssh_server.exec_command(cmd)
            shout = stdout.readlines()
            if stderr:
                shout += stderr
        return shout
