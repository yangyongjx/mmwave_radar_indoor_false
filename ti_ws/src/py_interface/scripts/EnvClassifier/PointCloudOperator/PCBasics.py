# coding=utf-8

import pypcd
import numpy as np

def getPCFromPCD(path):
    return [[i['x'], i['y']] for i in pypcd.PointCloud.from_path(path).pc_data]

def filterWithRect(points, x_low=float('-inf'), x_high=float('inf'), y_low=float('-inf'), y_high=float('inf')):
    result = [i for i in points if x_low <= i[0] < x_high and y_low <= i[1] < y_high]
    return result

def getXYLim(points):
    x = [i[0] for i in points]
    y = [i[1] for i in points]
    return [min(x), max(x), min(y), max(y)]