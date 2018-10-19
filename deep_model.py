import keras
import tensorflow as tf
import keras.backend.tensorflow_backend as backend

from keras.models import Sequential
from keras.layers import Dense, Dropout, Flatten, Activation
from keras.layers import Conv2D, MaxPooling2D
from keras.callbacks import TensorBoard

import numpy as np
import os
import random
import cv2
import time


model = Sequential()
model.add(Conv2D(32, (7, 7), padding='same',input_shape=(176, 200, 1), activation='relu'))
model.add(Conv2D(32, (3, 3), activation='relu'))
model.add(MaxPooling2D(pool_size=(2, 2)))
model.add(Dropout(0.2))

model.add(Conv2D(64, (3, 3), padding='same',activation='relu'))
model.add(Conv2D(64, (3, 3), activation='relu'))
model.add(MaxPooling2D(pool_size=(2, 2)))
model.add(Dropout(0.2))

model.add(Conv2D(128, (3, 3), padding='same',activation='relu'))
model.add(Conv2D(128, (3, 3), activation='relu'))
model.add(MaxPooling2D(pool_size=(2, 2)))
model.add(Dropout(0.2))

model.add(Flatten())
model.add(Dense(1024, activation='relu'))
model.add(Dropout(0.5))
model.add(Dense(4, activation='softmax'))

learning_rate = 0.001
opt = keras.optimizers.adam(lr=learning_rate)

model.compile(loss='categorical_crossentropy', optimizer=opt, metrics=['accuracy'])

tensorboard = TensorBoard(log_dir="logs/STAGE2-{}-{}".format(int(time.time()), learning_rate))

training_data_dir = "training_data"

## Check the lengths of each choice list
def check_data():
    choices = {"no_attacks": no_attacks,
               "attack_closest_enemy": attack_closest_enemy,
               "attack_enemy_structures": attack_enemy_structures,
               "attack_enemy_base": attack_enemy_base}

    total_data = 0

    lengths = []
    for choice in choices:
        print("Length of {} is: {}".format(choice, len(choices[choice])))
        total_data += len(choices[choice])
        lengths.append(len(choices[choice]))

    print("Total data length now is:",total_data)
    return lengths

hm_epochs = 10

for i in range(hm_epochs):
    current = 0
    increment = 4  ## data chunk
    not_maximum = True
    all_files = os.listdir(training_data_dir) ## training files location
    maximum = len(all_files)
    random.shuffle(all_files)

    while not_maximum:
        print("WORKING ON {}:{}".format(current, current+increment))  ## current job
        no_attacks = []
        attack_closest_enemy = []
        attack_enemy_structures = []
        attack_enemy_base = []

        for file in all_files[current:current+increment]:         ## file iteration
            full_path = os.path.join(training_data_dir, file)
            data = np.load(full_path)                             ## load data
            data = list(data)                                     ## list data
            for d in data:                                        ## group choices
                choice = np.argmax(d[0])
                if choice == 0:
                    no_attacks.append([d[0], d[1]])
                elif choice == 1:
                    attack_closest_enemy.append([d[0], d[1]])
                elif choice == 2:
                    attack_enemy_structures.append([d[0], d[1]])
                elif choice == 3:
                    attack_enemy_base.append([d[0], d[1]])

        lengths = check_data()
        lowest_data = min(lengths)                              ## go to shortest choice list

        random.shuffle(no_attacks)
        random.shuffle(attack_closest_enemy)
        random.shuffle(attack_enemy_structures)
        random.shuffle(attack_enemy_base)

        no_attacks = no_attacks[:lowest_data]                           ## slice lists up to lowest data
        attack_closest_enemy = attack_closest_enemy[:lowest_data]
        attack_enemy_structures = attack_enemy_structures[:lowest_data]
        attack_enemy_base = attack_enemy_base[:lowest_data]

        check_data()


## COMBINE DATA

        training_data = no_attacks + attack_closest_enemy + attack_enemy_structures + attack_enemy_base

        random.shuffle(training_data)
        print(len(training_data))

        test_size = 4
        batch_size = 4

        ## reshape data to fit 
        x_train = np.array([i[1] for i in training_data[:-test_size]]).reshape(-1, 176, 200, 3)
        y_train = np.array([i[0] for i in training_data[:-test_size]])

        x_test = np.array([i[1] for i in training_data[-test_size:]]).reshape(-1, 176, 200, 3)
        y_test = np.array([i[0] for i in training_data[-test_size:]])

        model.fit(x_train, y_train,
                  batch_size=batch_size,
                  validation_data=(x_test, y_test),
                  shuffle=True,
                  verbose=1, callbacks=[tensorboard])

        model.save("Apollyon_Cruiser")
        current += increment
        if current > maximum:
            not_maximum = False    