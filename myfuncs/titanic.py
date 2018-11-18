import math


def translate_age(train_df, test_df):
    #######################################
    # no age => mean grouped Mr, Mrs, Miss
    #######################################
    # get honorific title
    train_df['HonorificTitle'] = [''] * len(train_df['Name'].values)
    for i, val in enumerate(train_df['Name'].values):
        train_df['HonorificTitle'].values[i] = val.split(',')[1].split('.')[0]
    # get honorific title => age mean
    t2m = {}
    tmp = train_df.groupby('HonorificTitle')['Age']
    for key in tmp.indices.keys():
        t2m[key] = tmp.mean()[key]
    # age range
    for df in [train_df, test_df]:
        for i, val in enumerate(df['Age'].values):
            if math.isnan(val):
                val = t2m[df['Name'].values[i].split(',')[1].split('.')[0]]
                df['Age'].values[i] = val
    # del honorific title
    del train_df['HonorificTitle']
    return train_df, test_df


def translate_fare(train_df, test_df):
    #######################################
    # no fare => mean grouped by pclass
    #######################################
    for df in [train_df, test_df]:
        for i, val in enumerate(df['Fare'].values):
            if math.isnan(val):
                df['Fare'].values[i] = \
                    train_df.groupby('Pclass')['Fare'].mean()[
                        df['Pclass'].values[i]]
    return train_df, test_df


def translate_familystatus(train_df, test_df):
    #######################################
    # sibsp + parch == 0 => no family(0)
    # survive vs no survive in same familyname
    # => more survive(1) or less survive(2)
    # delete sibsp, parch
    # categorize after
    #######################################
    # get family name
    train_df['FamilyName'] = [''] * len(train_df['Name'].values)
    for i, val in enumerate(train_df['Name'].values):
        train_df['FamilyName'].values[i] = val.split(',')[0]
    # get family name => family status
    n2s = {}
    tmp = train_df.groupby('FamilyName')['Survived']
    for key in tmp.indices.keys():
        survived_num = tmp.sum()[key]
        no_survived_num = tmp.count()[key] - survived_num
        if survived_num > no_survived_num:
            n2s[key] = 1
        else:
            n2s[key] = 2
    # main
    for df in [train_df, test_df]:
        df['FamilyStatus'] = [0] * len(df['Name'].values)
        for i, val in enumerate(df['Name'].values):
            family_name = val.split(',')[0]
            # no family
            if df['SibSp'].values[i] + df['Parch'].values[i] == 0:
                continue
            # any family
            if family_name in n2s:
                df['FamilyStatus'].values[i] = n2s[family_name]
        # del sibsp, parch
        del df['SibSp']
        del df['Parch']
    # del family name
    del train_df['FamilyName']
    return train_df, test_df


if __name__ == '__main__':
    pass
