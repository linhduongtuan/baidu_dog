from keras.backend import set_session
from keras.models import load_model
from keras.models import Model
from keras.utils import plot_model
from keras.preprocessing.image import ImageDataGenerator
import tensorflow as tf
import numpy as np
import operator

from os import remove, path

import sys
sys.path.append('..')
from util import fwrite

config = tf.ConfigProto()
config.gpu_options.per_process_gpu_memory_fraction = 0.8
set_session(tf.Session(config=config))

batch_size = 48
model = load_model('xception-tuned07-0.78.h5')
plot_model(model, to_file='single_model.png')
test_datagen = ImageDataGenerator(rescale=1./255,)
valid_generator = test_datagen.flow_from_directory(
    '/home/zyh/PycharmProjects/baidu_dog/crop_val',
    target_size=(299, 299),
    batch_size=batch_size,
    shuffle=False,
    class_mode='categorical'
)
print(valid_generator.class_indices)


label_idxs = sorted(valid_generator.class_indices.items(), key=operator.itemgetter(1))
test_generator = test_datagen.flow_from_directory(
        '/home/zyh/PycharmProjects/baidu_dog/crop_test_img',
        target_size=(299, 299),
        batch_size=batch_size,
        shuffle=False,
        class_mode='categorical')
# print test_generator.filenameenames

from keras.optimizers import SGD
model.compile(optimizer=SGD(lr=0.0001, momentum=0.9), loss='categorical_crossentropy', metrics=['accuracy'])
y = model.predict_generator(test_generator, 10593/batch_size + 1, use_multiprocessing=True)
y_i = np.argmax(y, 1)
predict_path = 'predict.txt'
if path.exists(predict_path):
    remove(predict_path)
for i, idx in enumerate(y_i):
    fwrite(predict_path, str(label_idxs[idx][0]).split('_')[-1] + '\t' + test_generator.filenames[i][6:-4] + '\n')
