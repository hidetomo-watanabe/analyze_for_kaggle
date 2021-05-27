from keras.layers import CuDNNGRU, GlobalAveragePooling1D, GlobalMaxPooling1D
from keras.layers import Dense, Embedding, Input, concatenate
from keras.models import Model
from keras.preprocessing import sequence, text

import pandas as pd


def translate_text2seq(train_df, test_df):
    maxlen = 100
    max_features = 50000

    text_train = train_df['question_text'].fillna('dieter').to_numpy()
    text_test = test_df['question_text'].fillna('dieter').to_numpy()

    tokenizer = text.Tokenizer(num_words=max_features)
    tokenizer.fit_on_texts(list(text_train) + list(text_test))
    seq_train = tokenizer.texts_to_sequences(text_train)
    seq_test = tokenizer.texts_to_sequences(text_test)
    feature_train = sequence.pad_sequences(seq_train, maxlen=maxlen)
    feature_test = sequence.pad_sequences(seq_test, maxlen=maxlen)

    train_df = pd.merge(
        train_df,
        pd.DataFrame(
            data=feature_train,
            columns=map(
                lambda x: 'feature_%d' % x,
                range(feature_train.shape[1]))),
        left_index=True, right_index=True)
    test_df = pd.merge(
        test_df,
        pd.DataFrame(
            data=feature_test,
            columns=map(
                lambda x: 'feature_%d' % x,
                range(feature_test.shape[1]))),
        left_index=True, right_index=True)
    del train_df['question_text']
    del test_df['question_text']

    return train_df, test_df


def translate_target2prediction(Y_pred, Y_pred_proba):
    #######################################
    # target to prediction
    #######################################
    Y_pred = Y_pred.rename(columns={'target': 'prediction'})
    return Y_pred, Y_pred_proba


def create_nn_model():
    maxlen = 100
    max_features = 50000
    output_dim = 2
    optimizer = 'adam'

    inp = Input(shape=(maxlen, ))
    x = Embedding(max_features, 100)(inp)
    x = CuDNNGRU(64, return_sequences=True)(x)
    avg_pool = GlobalAveragePooling1D()(x)
    max_pool = GlobalMaxPooling1D()(x)
    conc = concatenate([avg_pool, max_pool])
    outp = Dense(output_dim, activation="sigmoid")(conc)

    model = Model(inputs=inp, outputs=outp)
    model.compile(
        loss='binary_crossentropy',
        optimizer=optimizer, metrics=['accuracy'])
    return model
