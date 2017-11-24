import os

import keras
import numpy as np
import tensorflow as tf
from keras import Input
from keras.applications import Xception, VGG16
from keras.backend.tensorflow_backend import set_session
from keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau
from keras.layers import Dense, Dropout
from keras.models import Model, load_model
from keras.preprocessing.image import ImageDataGenerator
from keras.utils import plot_model
from keras.optimizers import SGD
from keras.losses import categorical_crossentropy

import sys
sys.path.append('..')
sys.path.append('../..')

config = tf.ConfigProto()
config.gpu_options.per_process_gpu_memory_fraction = 0.8
set_session(tf.Session(config=config))

np.set_printoptions(threshold=None)
def clone_y_generator(generator):
    # output: train_gen_X, [train_gen_Y, train_gen_Y]
    while True:
        data = next(generator)
        x = data[0]
        y = [data[1], data[1]]
        print np.shape(y)
        yield x, y

train_datagen = ImageDataGenerator(
        rescale=1./255,
        shear_range=0.2,
        rotation_range=45,
        zoom_range=0.2,
        horizontal_flip=True)

test_datagen = ImageDataGenerator(rescale=1./255)

batch_size = 64
train_generator = train_datagen.flow_from_directory(
        '/home/zyh/PycharmProjects/baidu_dog/crop_train',
        # '/home/cwh/coding/data/cwh/test1',
        target_size=(299, 299),
        # batch_size=1,
        batch_size=batch_size,
        class_mode='categorical')

validation_generator = test_datagen.flow_from_directory(
        '/home/zyh/PycharmProjects/baidu_dog/crop_val',
        # '/home/cwh/coding/data/cwh/test1',
        target_size=(299, 299),
        # batch_size=1,
        batch_size=batch_size,
        class_mode='categorical')

early_stopping = EarlyStopping(monitor='val_loss', patience=3)

if os.path.exists('--dog_single_xception.h5'):
    model = load_model('dog_single_xception.h5')
else:
    # create the base pre-trained model
    input_tensor = Input(shape=(299, 299, 3))
    base_model = Xception(include_top=True, weights='imagenet', input_tensor=None, input_shape=None)

    base_model.layers.pop()
    base_model.outputs = [base_model.layers[-1].output]
    base_model.layers[-1].outbound_nodes = []
    base_model.output_layers = [base_model.layers[-1]]

    img1 = Input(shape=(299, 299, 3), name='img_1')

    feature1 = base_model(img1)

    # let's add a fully-connected layer
    fc = Dense(1024, activation='relu', name='fc')(feature1)

    category_predict1 = Dense(100, activation='softmax', name='ctg_out_1')(Dropout(0.5)(fc))

    from keras_center_loss import get_center_loss
    center_loss = get_center_loss(0.5, 100, 1024)
    model = Model(inputs=[img1], outputs=[category_predict1, fc], name='centr_loss')

    # model.save('dog_xception.h5')

    # first: train only the top layers (which were randomly initialized)
    # i.e. freeze all convolutional InceptionV3 layers
    for layer in base_model.layers:
        layer.trainable = False

    # compile the model (should be done *after* setting layers to non-trainable)
    model.compile(optimizer='nadam',
                  loss=[categorical_crossentropy, center_loss],
                  metrics=['accuracy'], loss_weights=[1, 0.08])
    plot_model(model, to_file='center_model_combined.png')
    # model = make_parallel(model, 3)
    # train the model on the new data for a few epochs

    model.fit_generator(clone_y_generator(train_generator),
                        steps_per_epoch=200,
                        epochs=100,
                        validation_data=validation_generator,
                        validation_steps=20,
                        callbacks=[early_stopping])
    model.save('dog_single_xception.h5')
# at this point, the top layers are well trained and we can start fine-tuning
# convolutional layers from inception V3. We will freeze the bottom N layers
# and train the remaining top layers.

# let's visualize layer names and layer indices to see how many layers
# we should freeze:
for i, layer in enumerate(model.layers[1].layers):
    print(i, layer.name)

# we chose to train the top 2 inception blocks, i.e. we will freeze
# the first 172 layers and unfreeze the rest:
cur_base_model = model.layers[1]
num_frozen_layer = 50
for layer in cur_base_model.layers[:num_frozen_layer]:
    layer.trainable = False
for layer in cur_base_model.layers[num_frozen_layer:]:
    layer.trainable = True

# we need to recompile the model for these modifications to take effect
# we use SGD with a low learning rate

model.compile(optimizer=SGD(lr=0.0001, momentum=0.9),
              loss={'ctg_out_1': 'categorical_crossentropy'},
              metrics=['accuracy'])

# we train our model again (this time fine-tuning the top 2 inception blocks
# alongside the top Dense layers
auto_lr = ReduceLROnPlateau(monitor='val_loss', factor=0.1, patience=3, verbose=0, mode='auto', epsilon=0.0001, cooldown=0, min_lr=0)
save_model = ModelCheckpoint('./xception_model/frozen_33/xception-tuned{epoch:02d}-{val_acc:.2f}.h5')
model.fit_generator(train_generator,
                    steps_per_epoch=200,
                    epochs=100,
                    validation_data=validation_generator,
                    validation_steps=20,
                    callbacks=[early_stopping, auto_lr, save_model]) # otherwise the generator would loop indefinitely
model.save('./xception_model/frozen_33/dog_single_xception_tuned.h5')
