# -*- coding: utf-8 -*-
from __future__ import print_function

from PIL import ImageFile, Image
ImageFile.LOAD_TRUNCATED_IMAGES = True

import torch
import torchvision
import torch.nn as nn
import torch.utils.data
from torch.autograd import Variable
import torchvision.transforms as transforms

import os, sys, h5py, gc, argparse, codecs, shutil
import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import StratifiedKFold

parser = argparse.ArgumentParser()
parser.add_argument('--ffpath', required=True, help='path for feature file')
parser.add_argument('--model', required=True, help='cnn model')
parser.add_argument('--imgtraintxt', required=True, help='train image file txt')
parser.add_argument('--imgtesttxt', required=True, help='train image file txt')
parser.add_argument('--crop', required=False, action='store_true', help='dog detection')

opt = parser.parse_args()
print(opt)
###############################################################################
# train = pd.read_csv('../../input/data_train_image.txt', header = None, sep = ' ', names = ['img', 'label', 'url'])
# val = pd.read_csv('../../input/val.txt', header = None, sep = ' ', names = ['img', 'label', 'url'])
#
# train['img'] = '../../input/train/' + train['img'] + '.jpg'
# val['img'] = '../../input/test1/' + val['img'] + '.jpg'
#
# # 删除标签不一致的情况
# train = train[~train['img'].duplicated(keep = False)]
# train_val = pd.concat([train, val], axis = 0, ignore_index = True)
################################################################################

#train = open('train_mu.txt').readlines()
image_txt = opt.imgtraintxt
train = open(image_txt).readlines()
image_txt = opt.imgtesttxt
test  = open(image_txt).readlines()
#test = open('test.txt').readlines()
#val = open('val_eq.txt').readlines()
# dog_crop = h5py.File('./yolo_kuhuang.h5', 'r')
# dog_crop_img = dog_crop.keys()

# 读取目标img文件，归一化到指定大小
def read_img(img_file, size = (224, 224), logging = False):
    imgs = []
    for img_path in img_file:
        img = Image.open(img_path)
        
        # if opt.crop and (img_path.split('/')[-1] in dog_crop_img):
        #    img = img.crop(dog_crop[img_path.split('/')[-1]][:])
        # print(img_path)
        imgs.append(img)
    return imgs

network = opt.model
if network == 'resnet18':
    model_conv = torchvision.models.resnet18()
    model_conv.load_state_dict(torch.load('/home/zyh/cnn_models/pytorch/resnet/resnet18-5c106cde.pth'))
    model_conv = nn.Sequential(*list(model_conv.children())[:-1])
    featurenum = 512
    batchsize = 40
elif network == 'resnet34':
    model_conv = torchvision.models.resnet34()
    model_conv.load_state_dict(torch.load('/home/zyh/cnn_models/pytorch/resnet/resnet34-333f7ec4.pth'))
    model_conv = nn.Sequential(*list(model_conv.children())[:-1])
    featurenum = 512
    batchsize = 20
elif network == 'resnet50':
    model_conv = torchvision.models.resnet50()
    model_conv.load_state_dict(torch.load('/home/zyh/cnn_models/pytorch/resnet/resnet50-19c8e357.pth'))
    model_conv = nn.Sequential(*list(model_conv.children())[:-1])
    featurenum = 2048
    batchsize = 25
elif network == 'resnet101':
    model_conv = torchvision.models.resnet101()
    model_conv.load_state_dict(torch.load('/home/zyh/cnn_models/pytorch/resnet/resnet101-5d3b4d8f.pth'))
    model_conv = nn.Sequential(*list(model_conv.children())[:-1])
    featurenum = 2048
    batchsize = 20
elif network == 'resnet152':
    model_conv = torchvision.models.resnet152()
    model_conv.load_state_dict(torch.load('/home/zyh/cnn_models/pytorch/resnet/resnet152-b121ed2d.pth'))
    model_conv = nn.Sequential(*list(model_conv.children())[:-1])
    featurenum = 2048
    batchsize = 10
elif network == 'vgg11':
    model_conv = torchvision.models.VGG(num_init_features=64, growth_rate=32, block_config=(6, 12, 24, 16))
    model_conv.load_state_dict(torch.load('/home/zyh/cnn_models/pytorch/resnet/densenet121-241335ed.pth'))
    model_conv.classifier = nn.Sequential(*list(model_conv.classifier.children())[:-1])
    featurenum = 4096
    batchsize = 34
elif network == 'vgg13':
    model_conv = torchvision.models.vgg13(pretrained=True)
    model_conv.classifier = nn.Sequential(*list(model_conv.classifier.children())[:-1])
    featurenum = 4096
    batchsize = 34
elif network == 'vgg16':
    model_conv = torchvision.models.vgg16(pretrained=True)
    model_conv.classifier = nn.Sequential(*list(model_conv.classifier.children())[:-1])
    featurenum = 4096
    batchsize = 34
elif network == 'vgg19':
    model_conv = torchvision.models.vgg19(pretrained=True)
    model_conv.classifier = nn.Sequential(*list(model_conv.classifier.children())[:-1])
    featurenum = 4096
    batchsize = 30
elif network == 'densenet121':
    model_conv = torchvision.models.DenseNet(num_init_features=64, growth_rate=32, block_config=(6, 12, 24, 16))
    model_conv.load_state_dict(torch.load('/home/zyh/cnn_models/pytorch/densenet/densenet121-241335ed.pth'))
    model_conv.classifier = nn.Sequential(*list(model_conv.classifier.children())[:-1])
    featurenum = 1024
    batchsize = 25
elif network == 'densenet161':
    model_conv = torchvision.models.DenseNet(num_init_features=96, growth_rate=48, block_config=(6, 12, 36, 24))
    model_conv.load_state_dict(torch.load('/home/zyh/cnn_models/pytorch/densenet/densenet161-17b70270.pth'))
    #model_conv = torchvision.models.densenet161(pretrained=True)#torch.load('/home/zyh/cnn_models/pytorch/densenet/densenet169-6f0f7f60.pth')
    model_conv.classifier = nn.Sequential(*list(model_conv.classifier.children())[:-1])
    featurenum = 2208
    batchsize = 10
elif network == 'densenet169':
    model_conv = torchvision.models.DenseNet(num_init_features=64, growth_rate=32, block_config=(6, 12, 32, 32))
    model_conv.load_state_dict(torch.load('/home/zyh/cnn_models/pytorch/densenet/densenet169-6f0f7f60.pth'))
    model_conv.classifier = nn.Sequential(*list(model_conv.classifier.children())[:-1])
    featurenum = 1664
    batchsize = 10
elif network == 'densenet201':
    model_conv = torchvision.models.DenseNet(num_init_features=64, growth_rate=32, block_config=(6, 12, 48, 32))
    model_conv.load_state_dict(torch.load('/home/zyh/cnn_models/pytorch/densenet/densenet201-4c113574.pth'))
    model_conv.classifier = nn.Sequential(*list(model_conv.classifier.children())[:-1])
    featurenum = 1920
    batchsize = 15
elif network == 'inception':
    model_conv = torchvision.models.inception_v3()
    model_conv.load_state_dict(torch.load('/home/zyh/cnn_models/pytorch/inception/inception_v3_google-1a9a5a14.pth'))
    #model_conv = torchvision.models.inception_v3(pretrained = True, transform_input=False)
    # model_conv.classifier = nn.Sequential(*list(model_conv.classifier.children())[:-1])
    featurenum = 1000
    batchsize = 10

model_conv = model_conv.cuda()
model_conv.eval()

print(network, featurenum)

# Inception 输入大小是299
if network == 'inception':
    tr = transforms.Compose([
            transforms.Scale(299),
            transforms.CenterCrop(299),
            transforms.ToTensor(),
            transforms.Normalize(mean = [ 0.485, 0.456, 0.406 ],
                                 std = [ 0.229, 0.224, 0.225 ])
    ])
else:
    tr = transforms.Compose([
            transforms.Scale(224),
            # transforms.RandomSizedCrop(224),
            # transforms.RandomHorizontalFlip(),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean = [ 0.485, 0.456, 0.406 ],
                                 std = [ 0.229, 0.224, 0.225 ])
    ])

#train_val = train_val.iloc[: 100]
train_feature = []
train = [line.split(' ')[0] for line in train]
for idx in range(0, len(train), batchsize):
    if idx + batchsize < len(train):
        ff = read_img(train[idx: idx + batchsize])
        ff = [tr(x) for x in ff]
        ff = torch.stack(ff)

        ff = model_conv(Variable(ff.cuda())).view(-1, featurenum)
        train_feature.append(ff.data.cpu().numpy())
        del ff; gc.collect()
    else:
        ff = read_img(train[idx: ])
        ff = [tr(x) for x in ff]
        ff = torch.stack(ff)
        ff = model_conv(Variable(ff.cuda())).view(-1, featurenum)
        train_feature.append(ff.data.cpu().numpy())
        del ff; gc.collect()
    print('Train', idx, len(train))
train_feature = np.array(train_feature)

# val_feature = []
# val = [line.split(' ')[0] for line in val]
# for idx in range(0, len(val), batchsize):
#     if idx + batchsize < len(val):
#         ff = read_img(val[idx: idx + batchsize])
#         ff = [tr(x) for x in ff]
#         ff = torch.stack(ff)
#
#         ff = model_conv(Variable(ff.cuda())).view(-1, featurenum)
#         val_feature.append(ff.data.cpu().numpy())
#         del ff; gc.collect()
#     else:
#         ff = read_img(val[idx: ])
#         ff = [tr(x) for x in ff]
#         ff = torch.stack(ff)
#         ff = model_conv(Variable(ff.cuda())).view(-1, featurenum)
#         val_feature.append(ff.data.cpu().numpy())
#         del ff; gc.collect()
#     print('val', idx, len(val))
# val_feature = np.array(val_feature)

#test = os.listdir('../../input/image/')
#test = ['../../input/image/' + x for x in test]


# test = test[: 100]
#################################################
test = [line.replace('\n', '') for line in test]
test_feature = []
for idx in range(0, len(test), batchsize):
    if idx + batchsize < len(test):
        ff = read_img(test[idx: idx + batchsize])
        ff = [tr(x) for x in ff]
        ff = torch.stack(ff)
        ff = model_conv(Variable(ff.cuda())).view(-1, featurenum)
        test_feature.append(ff.data.cpu().numpy())
        del ff; gc.collect()
    else:
        ff = read_img(test[idx: ])
        ff = [tr(x) for x in ff]
        ff = torch.stack(ff)
        ff = model_conv(Variable(ff.cuda())).view(-1, featurenum)
        test_feature.append(ff.data.cpu().numpy())
        del ff; gc.collect()
    print('Test', idx, len(test))
test_feature = np.array(test_feature)

train_feature = np.concatenate(train_feature, 0).reshape(-1, featurenum)
#val_feature = np.concatenate(val_feature, 0).reshape(-1, featurenum)
test_feature = np.concatenate(test_feature, 0).reshape(-1, featurenum)

with h5py.File(opt.ffpath, "w") as f:
    f.create_dataset("train_feature", data=train_feature)
    #f.create_dataset("test_feature", data=val_feature)
    f.create_dataset("test_feature", data=test_feature)
