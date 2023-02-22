# -*- coding:utf-8 -*-

from slacker import Slacker
import json
import yaml
import os


class SlackClient:

    def __init__(self, token):
        self.token = token
        self.slack = Slacker(self.token)

    def send_msg(self, channel, msg):
        self.slack.chat.post_message(channel, msg)

    def post_file(self, channel, file):
        self.slack.files.upload(file, channels=channel)

    def list_file(self):
        res = self.slack.files.list()
        return json.loads(str(res))


if __name__ == "__main__":
    cfg_file = 'cfg.yml'
    channel = '#market-report'
    if os.path.exists(cfg_file):
        with open(cfg_file, 'r') as f:
            res = yaml.full_load(f.read())
            user_token = res['sso_token']
            bot_token = res['bot_token']

    else:
        user_token = 'xoxb-526697683747-854669504614-dpovBjwv3rRoJaPfxDeyQsun'
    sc = SlackClient(user_token)
    sc.send_msg(channel, '123')
    # sc.post_file('#test', './pictures/trend_002635.png')
    # sc.post_file('#test', './pictures/percent_002635.png')
    # sc.list_file()
    # sc.slack.files.info('code 600346')