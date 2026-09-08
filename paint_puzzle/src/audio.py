# -*- coding: utf-8 -*-
"""音效加载与播放;snd/ 缺文件或混音器不可用时静默跳过。"""
import os
import sys

import pygame


def _resource_root():
    """资源根目录:打包成 exe 时取解包目录/程序目录,开发时取项目根。"""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return meipass
    return os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                         ".."))


SND_DIR = os.path.join(_resource_root(), "snd")


class Audio:
    def __init__(self):
        self.sounds = {}
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init()
            except pygame.error:
                return
        for name in ("click", "paint", "win", "fail"):
            path = os.path.join(SND_DIR, name + ".wav")
            if os.path.isfile(path):
                try:
                    self.sounds[name] = pygame.mixer.Sound(path)
                except pygame.error:
                    pass

    def play(self, name):
        snd = self.sounds.get(name)
        if snd is not None:
            try:
                snd.play()
            except pygame.error:
                pass
