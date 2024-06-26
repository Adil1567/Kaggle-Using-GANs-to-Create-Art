'''
From https://github.com/tsc2017/Frechet-Inception-Distance
Code derived from https://github.com/tensorflow/tensorflow/blob/master/tensorflow/contrib/gan/python/eval/python/classifier_metrics_impl.py

Usage:
    Call get_fid(images1, images2)
Args:
    images1, images2: Numpy arrays with values ranging from 0 to 255 and shape in the form [N, 3, HEIGHT, WIDTH] where N, HEIGHT and WIDTH can be arbitrary. 
    dtype of the images is recommended to be np.uint8 to save CPU memory.
Returns:
    Frechet Inception Distance between the two image distributions.
'''

import tensorflow.compat.v1 as tf
tf.disable_v2_behavior()
import os
import functools
import numpy as np
import time
from tensorflow.python.ops import array_ops
# pip install tensorflow-gan
import tensorflow_gan as tfgan
import cv2
from glob import glob

session=tf.compat.v1.InteractiveSession()
# A smaller BATCH_SIZE reduces GPU memory usage, but at the cost of a slight slowdown
BATCH_SIZE = 64

# Run images through Inception.
inception_images = tf.compat.v1.placeholder(tf.float32, [None, 3, None, None], name = 'inception_images')
activations1 = tf.compat.v1.placeholder(tf.float32, [None, None], name = 'activations1')
activations2 = tf.compat.v1.placeholder(tf.float32, [None, None], name = 'activations2')
fcd = tfgan.eval.frechet_classifier_distance_from_activations(activations1, activations2)

INCEPTION_TFHUB = 'https://tfhub.dev/tensorflow/tfgan/eval/inception/1'
INCEPTION_FINAL_POOL = 'pool_3'

def inception_activations(images = inception_images, num_splits = 1):
    images = tf.transpose(images, [0, 2, 3, 1])
    size = 299
    images = tf.compat.v1.image.resize_bilinear(images, [size, size])
    generated_images_list = array_ops.split(images, num_or_size_splits = num_splits)
    activations = tf.map_fn(
        fn = tfgan.eval.classifier_fn_from_tfhub(INCEPTION_TFHUB, INCEPTION_FINAL_POOL, True),
        elems = tf.stack(generated_images_list),
        parallel_iterations = 1,
        back_prop = False,
        swap_memory = True,
        name = 'RunClassifier')
    activations = array_ops.concat(tf.unstack(activations), 0)
    return activations

activations =inception_activations()

def get_inception_activations(inps):
    n_batches = int(np.ceil(float(inps.shape[0]) / BATCH_SIZE))
    act = np.zeros([inps.shape[0], 2048], dtype = np.float32)
    for i in range(n_batches):
        inp = inps[i * BATCH_SIZE : (i + 1) * BATCH_SIZE] / 255. * 2 - 1
        act[i * BATCH_SIZE : i * BATCH_SIZE + min(BATCH_SIZE, inp.shape[0])] = session.run(activations, feed_dict = {inception_images: inp})
    return act

def activations2distance(act1, act2):
    return session.run(fcd, feed_dict = {activations1: act1, activations2: act2})
        
def get_fid(images1, images2):
    session=tf.get_default_session()
    assert(type(images1) == np.ndarray)
    assert(len(images1.shape) == 4)
    assert(images1.shape[1] == 3)
    assert(np.min(images1[0]) >= 0 and np.max(images1[0]) > 10), 'Image values should be in the range [0, 255]'
    assert(type(images2) == np.ndarray)
    assert(len(images2.shape) == 4)
    assert(images2.shape[1] == 3)
    assert(np.min(images2[0]) >= 0 and np.max(images2[0]) > 10), 'Image values should be in the range [0, 255]'
    assert(images1.shape == images2.shape), 'The two numpy arrays must have the same shape'
    print('Calculating FID with %i images from each distribution' % (images1.shape[0]))
    start_time = time.time()
    act1 = get_inception_activations(images1)
    act2 = get_inception_activations(images2)
    fid = activations2distance(act1, act2)
    print('FID calculation time: %f s' % (time.time() - start_time))
    return fid

def load_images(path1, path2):

    test_files1 = glob(path1)
    test_files2 = glob(path2)

    imgs1 = [np.array(cv2.imread(f)) for f in test_files1]
    # imgs2 = [np.array(cv2.imread(f)) for f in test_files2]
    imgs2 = [np.array(cv2.imread(f))[:,256:512] for f in test_files2]

    imgs1 = np.swapaxes(np.swapaxes(np.array(imgs1), 3, 2), 1, 2)
    imgs2 = np.swapaxes(np.swapaxes(np.array(imgs2), 3, 2), 1, 2)
    
    return imgs1, imgs2

def get_fid_batches(real, fake):
    batch = len(real)
    max_num = len(fake)
    fid = 0.
    image_num = 0
    while len(fake) > 0:
        image_num += batch
        batch_fid = get_fid(fake[:batch], real[:batch]) * batch
        fid += batch_fid
        print('FID {}/{}: {}'.format(image_num, max_num, fid / image_num))
        if len(fake) > batch:
            fake = fake[batch:]
        else:
            break
    return fid / image_num


imgs1, imgs2 = load_images(
    path1 = 'DualGAN/datasets/monet/monet_jpg/*.jpg',
    # path2 = 'DualGAN/datasets/monet/photo_jpg/*.jpg'
    path2 = 'CycleGANInception/output_9blocks_4down/monet/samples_testing/B2A/*.jpg'
    # path2 = 'CycleGAN/output/monet/samples_testing/B2A/*.jpg'
)

print('Shape1: ', imgs1.shape)
print('Shape2: ', imgs2.shape)

print('FID: ', get_fid_batches(real=imgs1, fake=imgs2))