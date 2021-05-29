from logging import getLogger

import numpy as np

import pandas as pd

logger = getLogger('predict').getChild('BaseDataTranslater')
if 'ConfigReader' not in globals():
    from ..ConfigReader import ConfigReader
if 'LikeWrapper' not in globals():
    from ..commons.LikeWrapper import LikeWrapper


class BaseDataTranslater(ConfigReader, LikeWrapper):
    def __init__(self):
        pass

    def _calc_raw_data(self):
        train_path = self.configs['data']['train_path']
        test_path = self.configs['data']['test_path']
        delim = self.configs['data'].get('delimiter')
        if delim:
            train_df = pd.read_csv(train_path, delimiter=delim)
            test_df = pd.read_csv(test_path, delimiter=delim)
        else:
            train_df = pd.read_csv(train_path)
            test_df = pd.read_csv(test_path)
        self.pred_df = train_df[self.pred_cols]
        self.train_df = train_df.drop(self.pred_cols, axis=1)
        self.test_df = test_df
        self.raw_pred_df = self.pred_df.copy()
        self.raw_train_df = self.train_df.copy()
        self.raw_test_df = self.test_df.copy()
        return

    def get_raw_data(self):
        output = {
            'train_df': self.raw_train_df,
            'test_df': self.raw_test_df,
            'pred_df': self.raw_pred_df,
        }
        return output

    def write_train_data(self):
        savename = self.configs['pre'].get('savename')
        if not savename:
            logger.warning('NO SAVENAME')
            return

        savename += '.npy'
        output_path = self.configs['data']['output_dir']
        np.save(
            f'{output_path}/feature_columns_{savename}',
            self.feature_columns)
        np.save(f'{output_path}/train_ids_{savename}', self.train_ids)
        np.save(f'{output_path}/test_ids_{savename}', self.test_ids)
        np.save(f'{output_path}/X_train_{savename}', self.X_train)
        np.save(f'{output_path}/Y_train_{savename}', self.Y_train)
        np.save(f'{output_path}/X_test_{savename}', self.X_test)
        return savename

    def get_train_data(self):
        logger.info(f'X_train shape: {self.X_train.shape}')
        logger.info(f'Y_train shape: {self.Y_train.shape}')
        logger.info(f'X_test shape: {self.X_test.shape}')
        output = {
            'feature_columns': self.feature_columns,
            'train_ids': self.train_ids,
            'test_ids': self.test_ids,
            'X_train': self.X_train,
            'Y_train': self.Y_train,
            'X_test': self.X_test,
        }
        return output

    def get_pre_processers(self):
        output = {}
        if hasattr(self, 'x_scaler'):
            output['x_scaler'] = self.x_scaler
        if hasattr(self, 'dimension_reduction_model'):
            output['dimension_reduction_model'] = \
                self.dimension_reduction_model
        if hasattr(self, 'target_encoding_model'):
            output['target_encoding_model'] = \
                self.target_encoding_model
        return output

    def get_post_processers(self):
        output = {}
        return output
