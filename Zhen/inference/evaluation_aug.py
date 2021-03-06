import os
import time
import json
import yaml
import torch
import seaborn as sns
import numpy as np
import pandas as pd
from glob import glob
import pickle as pkl
from models import get_model
from collections import OrderedDict
import matplotlib.pyplot as plt
from data_proc.csv_dataset_test import SIIM_Dataset
from models import convert_state_dict
from data_proc.augment import Augmentations

threshold = 0.5
classes = ['benign', 'malignant']
colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728',
              '#9467bd', '#8c564b', '#e377c2', '#7f7f7f',
              '#bcbd22', '#17becf']


def evaluation(model, data_root, csv_file, device, aug_parameters=None):

    """
    :param model:
    :param data_split_file:
    :param test_aug:
    :return:
    """
    if aug_parameters is None:
        print('current input size is 256!!!')
        aug_parameters = OrderedDict({'affine': None,
                                      'hflip': None,
                                      'vflip': None,
                                      'color_trans': None,
                                      'hair_mask': None,
                                      'rotate': None,
                                      'microscope': None,
                                      'normalization': {'mean': (0.485, 0.456, 0.406),
                                                        'std': (0.229, 0.224, 0.225)},
                                      'size': 384,
                                      'scale': (1.0, 1.0),
                                      'ratio': (1.0, 1.0)
                                      }
                                     )
    case_list = glob(os.path.join(data_root, '*.jpg'))
    augmentor = Augmentations(augs=aug_parameters, tta='inception')  # or 'inception'
    dataset = SIIM_Dataset(data_root=data_root, case_list=case_list, data_csv=csv_file, transform=augmentor.ta_transform)
    test_results = OrderedDict({'target': [], 'image_name': []})

    model.eval()
    with torch.no_grad():
        for data in iter(dataset):
            outputs = model(data['image'].to(device))
            pred_score = outputs.detach().cpu().sigmoid().mean().numpy()
            print('image_name: ', data['name'], 'pred_score: ', pred_score)

            test_results['target'].append(pred_score)
            test_results['image_name'].append(data['name'])

    return test_results


def cross_fold_validation(cfg, result_dir, device=None, best_model=True):
    if device is None:
        device = torch.device("cuda:1" if torch.cuda.is_available() else "cpu")

    model_file = cfg['model'] + '_best.model' if best_model else cfg['model'] + '_final.model'
    # run five fold validation
    model = get_model(cfg['model'], cfg['data']['channel'], 1).to(device)
    saved_model = torch.load(os.path.join(result_dir, model_file), map_location=device)

    try:
        model.load_state_dict(saved_model['model_state_dict'])  # maybe need to change
    except RuntimeError:
        print('convert model layer name!!!')
        model_state_dict = convert_state_dict(saved_model['model_state_dict'])
        model.load_state_dict(model_state_dict)

    test_result = evaluation(model, data_root=cfg['data']['root'], device=device, csv_file=cfg['data']['csv_file'])

    test_csv = pd.DataFrame({'image_name': test_result['image_name'], 'target': test_result['target']})
    test_csv.to_csv(os.path.join(result_dir, 'submission.csv'), index=False)
    # plt.hist(test_csv.target,bins=100)
    # plt.show()


if __name__ == "__main__":
    with open('/home/zyi/My_disk/ISIC_2020/configs/skin_config.yml', 'r') as f:
        cfg = yaml.load(f)

    cfg['model'] = 'regnet-siim'
    cfg['data']['root'] = '/home/zyi/My_disk/ISIC_2020/data/test'
    cfg['data']['csv_file'] = '/home/zyi/My_disk/ISIC_2020/test.csv'
    result_dir = '/media/zyi/080c2d74-aa6d-4851-acdc-c9588854e17c/ISIC_2020/run_exp/regnet-siim/with_test_384/fold_0'
    print(result_dir)
    cross_fold_validation(cfg, result_dir, best_model=True)
    # csv = pd.read_csv('/media/zyi/080c2d74-aa6d-4851-acdc-c9588854e17c/ISIC_2020/run_exp/efficient-siimd/fold_1/submission.csv')
    # plt.hist(csv.target, bins=100)
    # plt.show()


