import sys
import os
import math
import json
import pickle
import numpy as np
import pandas as pd
import importlib
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import GridSearchCV
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.svm import SVC, SVR, LinearSVC, LinearSVR
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
from sklearn.naive_bayes import GaussianNB
from sklearn.linear_model import Perceptron
from sklearn.linear_model import SGDClassifier, SGDRegressor
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
from xgboost import XGBClassifier, XGBRegressor
from lightgbm import LGBMClassifier, LGBMRegressor
from keras.wrappers.scikit_learn import KerasClassifier
from keras.wrappers.scikit_learn import KerasRegressor
from IPython.display import display
import matplotlib.pyplot as plt
from logging import getLogger

BASE_PATH = '%s/..' % os.path.dirname(os.path.abspath(__file__))
logger = getLogger('predict').getChild('Predicter')

try:
    from MyScoringFunc import get_my_scorer
except Exception as e:
    logger.warn('CANNOT IMPORT MY SCORING FUNC: %s' % e)
try:
    from MyKerasModel import create_keras_model
except Exception as e:
    logger.warn('CANNOT IMPORT MY KERAS MODEL: %s' % e)
try:
    import seaborn as sns
except Exception as e:
    logger.warn('CANNOT IMPORT SEABORN: %s' % e)


class Predicter(object):
    def __init__(self):
        self.configs = {}

    def read_config_file(self, path='%s/scripts/config.json' % BASE_PATH):
        with open(path, 'r') as f:
            self.configs = json.loads(f.read())
        self.id_col = self.configs['data']['id_col']
        self.pred_col = self.configs['data']['pred_col']

    def read_config_text(self, text):
        self.configs = json.loads(text)
        self.id_col = self.configs['data']['id_col']
        self.pred_col = self.configs['data']['pred_col']

    def _get_base_model(self, model):
        if model == 'log_reg':
            return LogisticRegression()
        elif model == 'linear_reg':
            return LinearRegression()
        elif model == 'svc':
            return SVC()
        elif model == 'svr':
            return SVR()
        elif model == 'l_svc':
            return LinearSVC()
        elif model == 'l_svr':
            return LinearSVR()
        elif model == 'rf_clf':
            return RandomForestClassifier()
        elif model == 'rf_reg':
            return RandomForestRegressor()
        elif model == 'gbdt_clf':
            return GradientBoostingClassifier()
        elif model == 'gbdt_reg':
            return GradientBoostingRegressor()
        elif model == 'knn_clf':
            return KNeighborsClassifier()
        elif model == 'knn_reg':
            return KNeighborsRegressor()
        elif model == 'g_nb':
            return GaussianNB()
        elif model == 'preceptron':
            return Perceptron()
        elif model == 'sgd_clf':
            return SGDClassifier()
        elif model == 'sgd_reg':
            return SGDRegressor()
        elif model == 'dt_clf':
            return DecisionTreeClassifier()
        elif model == 'dt_reg':
            return DecisionTreeRegressor()
        elif model == 'xgb_clf':
            return XGBClassifier()
        elif model == 'xgb_reg':
            return XGBRegressor()
        elif model == 'lgb_clf':
            return LGBMClassifier()
        elif model == 'lgb_reg':
            return LGBMRegressor()
        elif model == 'keras_clf':
            return KerasClassifier(build_fn=create_keras_model)
        elif model == 'keras_reg':
            return KerasRegressor(build_fn=create_keras_model)

    def display_data(self):
        for label, df in [('train', self.train_df), ('test', self.test_df)]:
            logger.info('%s:' % label)
            display(df.head())
            display(df.describe())

    def _replace_missing_of_dfs(self, dfs, target, target_mean):
        replaced = False
        output = []
        for df in dfs:
            for i, val in enumerate(df[target].values):
                if math.isnan(val):
                    replaced = True
                    df[target].values[i] = target_mean
            output.append(df)
        output.insert(0, replaced)
        return output

    def _categorize_dfs(self, dfs, target):
        output = []
        all_vals = []
        for df in dfs:
            all_vals.extend(list(set(df[target].values)))
        for df in dfs:
            for val in all_vals:
                df['%s_%s' % (target, val)] = [0] * len(df[target].values)
            for i, val_tmp in enumerate(df[target].values):
                for val in all_vals:
                    if val_tmp == val:
                        df['%s_%s' % (target, val)].values[i] = 1
            del df[target]
            output.append(df)
        return output

    def _to_float_of_dfs(self, dfs, target):
        output = []
        for df in dfs:
            df[target] = df[target].astype(float)
            output.append(df)
        return output

    def get_raw_data(self):
        train_path = self.configs['data']['train_path']
        test_path = self.configs['data']['test_path']
        self.train_df = pd.read_csv(train_path)
        self.test_df = pd.read_csv(test_path)
        return self.train_df, self.test_df

    def trans_raw_data(self):
        train_df = self.train_df
        test_df = self.test_df
        trans_adhoc = self.configs['translate']['adhoc']
        # adhoc
        if trans_adhoc['myfunc']:
            sys.path.append(BASE_PATH)
            myfunc = importlib.import_module(
                'myfuncs.%s' % trans_adhoc['myfunc'])
        for method_name in trans_adhoc['methods']:
            logger.info('adhoc: %s' % method_name)
            train_df, test_df = eval(
                'myfunc.%s' % method_name)(train_df, test_df)
        # del
        for column in self.configs['translate']['del']:
            logger.info('delete: %s' % column)
            del train_df[column]
            del test_df[column]
        # missing
        for column in test_df.columns:
            if column in [self.id_col, self.pred_col]:
                continue
            if test_df.dtypes[column] == 'object':
                logger.warn('OBJECT MISSING IS NOT BE REPLACED: %s' % column)
                continue
            column_mean = train_df[column].mean()
            replaced, train_df, test_df = self._replace_missing_of_dfs(
                [train_df, test_df], column, column_mean)
            if replaced:
                logger.info('replace missing with mean: %s' % column)
        # category
        for column in test_df.columns:
            if column in [self.id_col, self.pred_col]:
                continue
            if test_df.dtypes[column] != 'object' \
                    and column not in self.configs['translate']['category']:
                continue
            logger.info('categorize: %s' % column)
            train_df, test_df = self._categorize_dfs(
                [train_df, test_df], column)
        # float
        for column in test_df.columns:
            if column in [self.id_col]:
                continue
            if self.configs['fit']['mode'] in ['clf'] \
                    and column in [self.pred_col]:
                continue
            train_df, test_df = self._to_float_of_dfs(
                [train_df, test_df], column)
        self.train_df = train_df
        self.test_df = test_df
        return self.train_df, self.test_df

    def get_fitting_data(self):
        train_df = self.train_df
        test_df = self.test_df
        # random
        if self.configs['data']['random']:
            logger.info('randomize train data')
            train_df = train_df.iloc[np.random.permutation(len(train_df))]
        # Y_train
        self.Y_train = train_df[self.pred_col].values
        # X_train
        self.X_train = train_df \
            .drop(self.id_col, axis=1).drop(self.pred_col, axis=1).values
        # X_test
        self.id_pred = test_df[self.id_col].values
        self.X_test = test_df \
            .drop(self.id_col, axis=1).values
        # feature_columns
        self.feature_columns = []
        for key in self.train_df.keys():
            if key == self.pred_col or key == self.id_col:
                continue
            self.feature_columns.append(key)
        return self.feature_columns, self.X_train, self.Y_train, self.X_test

    def normalize_fitting_data(self):
        # x
        # ss
        ss_x = StandardScaler()
        ss_x.fit(self.X_train)
        self.X_train = ss_x.transform(self.X_train)
        self.X_test = ss_x.transform(self.X_test)
        # y
        if self.configs['fit']['mode'] == 'reg':
            # other
            y_pre = self.configs['fit']['y_pre']
            if y_pre:
                logger.info('translate y_train with %s' % y_pre)
                if y_pre == 'log':
                    self.Y_train = np.array(list(map(math.log, self.Y_train)))
                else:
                    raise Exception(
                        '[ERROR] NOT IMPELEMTED FIT Y_PRE: %s' % y_pre)
            # ss
            self.ss_y = StandardScaler()
            self.Y_train = self.Y_train.reshape(-1, 1)
            self.ss_y.fit(self.Y_train)
            self.Y_train = self.ss_y.transform(self.Y_train).reshape(-1, )
        return self.feature_columns, self.X_train, self.Y_train, self.X_test

    def reduce_dimension(self):
        n = self.configs['translate']['dimension']
        if not n:
            return self.X_train, self.Y_train, self.X_test
        if n == 'all':
            n = self.X_train.shape[1]
        pca_obj = PCA(n_components=n)
        pca_obj.fit(self.X_train)
        logger.info('pca_ratio sum: %s' % sum(
            pca_obj.explained_variance_ratio_))
        logger.info('pca_ratio: %s' % pca_obj.explained_variance_ratio_)
        self.X_train = pca_obj.transform(self.X_train)
        self.X_test = pca_obj.transform(self.X_test)
        self.feature_columns = list(map(lambda x: 'pca_%d' % x, range(n)))
        return self.feature_columns, self.X_train, self.Y_train, self.X_test

    def is_ok_with_adversarial_validation(self):
        def _get_adversarial_preds(X_train, X_test, adversarial):
            # create data
            tmp_X_train = X_train[:len(X_test)]
            X_adv = np.concatenate((tmp_X_train, X_test), axis=0)
            target_adv = np.concatenate(
                (np.zeros(len(tmp_X_train)), np.ones(len(X_test))), axis=0)
            # fit
            gs = GridSearchCV(
                self._get_base_model(adversarial['model']),
                adversarial['params'],
                cv=adversarial['cv'],
                scoring=adversarial['scoring'],
                n_jobs=adversarial['n_jobs'])
            gs.fit(X_adv, target_adv)
            est = gs.best_estimator_
            return est.predict(tmp_X_train), est.predict(X_test)

        def _is_ok_pred_nums(tr0, tr1, te0, te1):
            if tr0 == 0 and te0 == 0:
                return False
            if tr1 == 0 and te1 == 0:
                return False
            if tr1 == 0 and te0 == 0:
                return False
            return True

        X_train = self.X_train
        adversarial = self.configs['data']['adversarial']
        if adversarial:
            logger.info('with adversarial')
            adv_pred_train, adv_pred_test = _get_adversarial_preds(
                X_train, self.X_test, adversarial)
            adv_pred_train_num_0 = len(np.where(adv_pred_train == 0)[0])
            adv_pred_train_num_1 = len(np.where(adv_pred_train == 1)[0])
            adv_pred_test_num_0 = len(np.where(adv_pred_test == 0)[0])
            adv_pred_test_num_1 = len(np.where(adv_pred_test == 1)[0])
            logger.info('pred train num 0: %s' % adv_pred_train_num_0)
            logger.info('pred train num 1: %s' % adv_pred_train_num_1)
            logger.info('pred test num 0: %s' % adv_pred_test_num_0)
            logger.info('pred test num 1: %s' % adv_pred_test_num_1)
            if not _is_ok_pred_nums(
                adv_pred_train_num_0,
                adv_pred_train_num_1,
                adv_pred_test_num_0,
                adv_pred_test_num_1,
            ):
                raise Exception(
                    '[ERROR] TRAIN AND TEST MAY BE HAVE DIFFERENT FEATURES')
        else:
            logger.warn('NO DATA VALIDATION')
            return True

    def calc_best_model(self):
        model = self.configs['fit']['model']
        modelname = self.configs['fit']['modelname']
        base_model = self._get_base_model(model)
        scoring = self.configs['fit']['scoring']
        cv = self.configs['fit']['cv']
        n_jobs = self.configs['fit']['n_jobs']
        fit_params = self.configs['fit']['fit_params']
        params = self.configs['fit']['params']
        if scoring == 'my_scorer':
            scorer = get_my_scorer()
        else:
            scorer = scoring
        if len(fit_params.keys()) > 0:
            fit_params['eval_set'] = [[self.X_train, self.Y_train]]

        gs = GridSearchCV(
            estimator=base_model, param_grid=params,
            cv=cv, scoring=scorer, n_jobs=n_jobs)
        gs.fit(self.X_train, self.Y_train, **fit_params)
        logger.info('model: %s' % model)
        logger.info('modelname: %s' % modelname)
        logger.info('  X train shape: %s' % str(self.X_train.shape))
        logger.info('  Y train shape: %s' % str(self.Y_train.shape))
        logger.info('  best params: %s' % gs.best_params_)
        logger.info('  best score of trained grid search: %s' % gs.best_score_)
        if model in ['keras_clf', 'keras_reg']:
            self.estimator = gs.best_estimator_.model
            self.estimator.save(
                '%s/outputs/%s.pickle' % (BASE_PATH, modelname))
        else:
            self.estimator = gs.best_estimator_
            with open(
                '%s/outputs/%s.pickle' % (BASE_PATH, modelname), 'wb'
            ) as f:
                pickle.dump(self.estimator, f)
        logger.info('estimator: %s' % self.estimator)

        # feature_importances
        if hasattr(self.estimator, 'feature_importances_'):
            feature_importances = pd.DataFrame(
                data=[self.estimator.feature_importances_],
                columns=self.feature_columns)
            feature_importances = feature_importances.ix[
                :, np.argsort(feature_importances.values[0])[::-1]]
            logger.info('feature importances:')
            display(feature_importances)
            logger.info('feature importances /sum:')
            display(
                feature_importances / np.sum(
                    self.estimator.feature_importances_))

        return self.estimator

    def calc_output(self):
        model = self.configs['fit']['model']
        self.Y_pred = None
        self.Y_pred_proba = None
        # keras
        if model in ['keras_clf', 'keras_reg']:
            self.Y_pred_proba = self.estimator.predict(self.X_test)
        # clf
        elif self.configs['fit']['mode'] == 'clf':
            self.Y_pred = self.estimator.predict(self.X_test)
            if hasattr(self.estimator, 'predict_proba'):
                self.Y_pred_proba = self.estimator.predict_proba(self.X_test)
        # reg
        elif self.configs['fit']['mode'] == 'reg':
            # inverse normalize
            # ss
            self.Y_pred = self.ss_y.inverse_transform(self.Y_pred)
            # other
            y_pre = self.configs['fit']['y_pre']
            if y_pre:
                logger.info('inverse translate y_train with %s' % y_pre)
                if y_pre == 'log':
                    self.Y_pred = np.array(list(map(math.exp, self.Y_pred)))
                else:
                    raise Exception(
                        '[ERROR] NOT IMPELEMTED FIT Y_PRE: %s' % y_pre)
        # np => pd
        if isinstance(self.Y_pred, np.ndarray):
            self.Y_pred = pd.merge(
                pd.DataFrame(data=self.id_pred, columns=[self.id_col]),
                pd.DataFrame(data=self.Y_pred, columns=[self.pred_col]),
                left_index=True, right_index=True)
        if isinstance(self.Y_pred_proba, np.ndarray):
            self.Y_pred_proba = pd.merge(
                pd.DataFrame(data=self.id_pred, columns=[self.id_col]),
                pd.DataFrame(
                    data=self.Y_pred_proba,
                    columns=map(
                        lambda x: '%s_%s' % (self.pred_col, str(x)),
                        self.estimator.classes_)),
                left_index=True, right_index=True)
        # post
        fit_post = self.configs['fit']['post']
        if fit_post['myfunc']:
            sys.path.append(BASE_PATH)
            myfunc = importlib.import_module(
                'myfuncs.%s' % fit_post['myfunc'])
        for method_name in fit_post['methods']:
            logger.info('fit post: %s' % method_name)
            self.Y_pred, self.Y_pred_proba = eval(
                'myfunc.%s' % method_name)(self.Y_pred, self.Y_pred_proba)
        return self.Y_pred, self.Y_pred_proba

    def write_output(self, filename=None):
        if not filename:
            filename = '%s.csv' % self.configs['fit']['modelname']
        if isinstance(self.Y_pred, pd.DataFrame):
            self.Y_pred.to_csv(
                '%s/outputs/%s' % (BASE_PATH, filename), index=False)
        if isinstance(self.Y_pred_proba, pd.DataFrame):
            self.Y_pred_proba.to_csv(
                '%s/outputs/proba_%s' % (BASE_PATH, filename), index=False)
        return filename

    def visualize_train_data(self):
        for key in self.train_df.keys():
            if key == self.pred_col or key == self.id_col:
                continue
            g = sns.FacetGrid(self.train_df, col=self.pred_col)
            g.map(plt.hist, key, bins=20)

    def visualize_train_pred_data(self):
        Y_train_pred = self.estimator.predict(self.X_train)
        g = sns.jointplot(self.Y_train, Y_train_pred, kind='kde')
        g.set_axis_labels('Y_train', 'Y_train_pred')
        g.fig.suptitle('estimator')


if __name__ == '__main__':
    pass