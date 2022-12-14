import numpy as np
import torch
import torch.nn as nn
import matplotlib.pyplot as plt
import torch.nn.functional as F
import torch.optim as optim
from torch.autograd import Variable
from copy import deepcopy
from collections import Counter
from copy import deepcopy as copy
from modules.matrixBLEU import mBLEU
from modules.utils import CUDA_wrapper
import itertools
from functools import reduce

def one_hots(zeros, ix):
    for i in range(zeros.size()[0]):
        zeros[i, ix[i]] = 1
    return zeros

def overlap(t, r_hot, r, f, temp, n):
    """ calculate overlap as in original BLEU script.
    see google's BLEU script for details """
    t_soft = f(t / temp)
    length = t.size()[0]
    v_size = t.size()[1]
    from_ref = set([i.data[0] for i in r])
    res = CUDA_wrapper(Variable(torch.Tensor([0])))
    M = list(itertools.product(from_ref, repeat=n))
    mul = lambda x, y: x * y
    for i in range(length - n + 1):
        pp = [t_soft[i + j] for j in range(n)]
        for m in M:
            reslicer = lambda x: r.data.shape[0] + x
            y_prod = reduce(mul,
                     [r_hot[j:reslicer(-n + 1 + j), m[j]] for j in range(n)])
            y_prod = y_prod.sum(0)
            p_prod = reduce(mul, \
                     [t_soft[j:reslicer(-n + 1 + j), m[j]] for j in range(n)])
            denominator = 1 + p_prod.sum(0) - p_prod[i]
            pr = reduce(mul, [pp[j][m[j]] for j in range(n)])

            res += torch.min(pr, pr * y_prod / denominator)
    return res

def precision(t, r_hot, r, f, temp, n):
    return overlap(t, r_hot, r, f, temp, n) / (t.data.shape[0] - n + 1)

def bleu(t, r_hot, r, f, temp, n):
    precisions = [precision(t, r_hot, r, f, temp, i) for i in range(1, n+1)]
    p_log_sum =  sum([(1. / n) * torch.log(p)\
                                                for p in precisions])
    return torch.exp(p_log_sum)

def overlap_lower_bound(t, r_hot, r, f, temp, n):
    """ calculate overlap as in original BLEU script.
    see google's BLEU script for details """
    t_soft = f(t / temp)
    length = t.size()[0]
    v_size = t.size()[1]
    from_ref = set([i.data[0] for i in r])
    res = CUDA_wrapper(Variable(torch.Tensor([0])))
    M = list(itertools.product(from_ref, repeat=n))
    mul = lambda x, y: x * y
    for i in range(length - n + 1):
        pp = [t_soft[i + j] for j in range(n)]
        for m in M:
            reslicer = lambda x: r.data.shape[0] + x
            y_prod = reduce(mul,
                     [r_hot[j:reslicer(-n + 1 + j), m[j]] for j in range(n)])
            y_prod = y_prod.sum(0)
            p_prod = reduce(mul, \
                     [t_soft[j:reslicer(-n + 1 + j), m[j]] for j in range(n)])
            denominator = 1 + p_prod.sum(0) - p_prod[i]
            pr = reduce(mul, [pp[j][m[j]] for j in range(n)])
            res += pr * torch.log(torch.min(Variable(CUDA_wrapper(torch.FloatTensor([1]))), y_prod / denominator))
    return res

def log_precisions(t, r_hot, r, f, temp, n):
    return overlap_lower_bound(t, r_hot, r, f, temp, n) - np.log(t.size()[0] - n  + 1)

def log_bleu(t, r_hot, r, f, temp, n):
    precisions = [log_precisions(t, r_hot, r, f, temp, i) for i in range(1, n+1)]
    p_log_sum =  sum([(1. / n) * p for p in precisions])
    return p_log_sum
