import tensorflow as tf
import yaml
import os
import random
import sys
sys.path.insert(0, '/~/Documents/models/research/object_detection/utils')
from object_detection.utils import dataset_util

flags = tf.app.flags
flags.DEFINE_string('output_dir', '', 'Path to directory to output TFRecords.')
FLAGS = flags.FLAGS

LABEL_DICT = {
    "Green": 1,
    "Red": 2,
    "GreenLeft": 3,
    "GreenRight": 4,
    "RedLeft": 5,
    "RedRight": 6,
    "Yellow": 7,
    "off": 8,
    "RedStraight": 9,
    "GreenStraight": 10,
    "GreenStraightLeft": 11,
    "GreenStraightRight": 12,
    "RedStraightLeft": 13,
    "RedStraightRight": 14
    }


def create_tf_example(example, example_source, image_data):
    MIN_DELTA = 5
    if example_source == "LISA":
        image_height = 960
        image_width = 1280
        image_format = 'jpg'.encode()
        filename = os.path.abspath(os.path.join(os.path.dirname(image_data), example['path']))  
    
    elif example_source == "SIM":
        image_height = 600
        image_width = 800
        image_format = 'jpg'.encode()
        filename = os.path.abspath(os.path.join(os.path.dirname(image_data), example['filename']))  
        
    else:
        # Bosch
        image_height = 720
        image_width = 1280
        image_format = 'png'.encode()
        filename = os.path.abspath(os.path.join(os.path.dirname(image_data), example['path']))      
  
    valid_example = False
    xmins = []  # List of normalized left x coordinates in bounding box (1 per box)
    xmaxs = []  # List of normalized right x coordinates in bounding box (1 per box)
    ymins = []  # List of normalized top y coordinates in bounding box (1 per box)
    ymaxs = []  # List of normalized bottom y coordinates in bounding box (1 per box)
    classes_text = []  # List of string class name of bounding box (1 per box)
    classes = []  # List of integer class id of bounding box (1 per box)
    tf_example = []
    
    if example_source == "SIM":
        for box in example['annotations']:
            # Check that the box is within range
            x_min = box['xmin']
            x_min = max(1.0, x_min)
            x_max = box['x_width']+x_min            
            x_max = min(x_max, image_width-1)
            
            y_min = box['ymin']
            y_min = max(1.0, y_min)     
            y_max = box['y_height']+y_min            
            y_max = min(y_max, image_height-1)
            
            if box['x_width'] >= MIN_DELTA and box['y_height'] >= MIN_DELTA:
                xmins.append(float(x_min / image_width))
                xmaxs.append(float(x_max / image_width))
                ymins.append(float(y_min / image_height))
                ymaxs.append(float(y_max / image_height))
                classes_text.append(box['class'].encode())
                classes.append(int(LABEL_DICT[box['class']]))
                valid_example = True
    else:
        for box in example['boxes']:
            # Check that the box is within range
            x_max = min(box['x_max'], image_width-1)
            y_max = min(box['y_max'], image_height-1)
            if (x_max - box['x_min']) >= MIN_DELTA and (y_max - box['y_min']) >= MIN_DELTA:
                xmins.append(float(box['x_min'] / image_width))
                xmaxs.append(float(x_max / image_width))
                ymins.append(float(box['y_min'] / image_height))
                ymaxs.append(float(y_max / image_height))
                classes_text.append(box['label'].encode())
                classes.append(int(LABEL_DICT[box['label']]))
                valid_example = True
            
    
    if valid_example:
        with tf.gfile.GFile(filename, 'rb') as fid:
            encoded_image = fid.read()
            
        tf_example = tf.train.Example(features=tf.train.Features(feature={
            'image/height': dataset_util.int64_feature(image_height),
            'image/width': dataset_util.int64_feature(image_width),
            'image/filename': dataset_util.bytes_feature(filename),
            'image/source_id': dataset_util.bytes_feature(filename),
            'image/encoded': dataset_util.bytes_feature(encoded_image),
            'image/format': dataset_util.bytes_feature(image_format),
            'image/object/bbox/xmin': dataset_util.float_list_feature(xmins),
            'image/object/bbox/xmax': dataset_util.float_list_feature(xmaxs),
            'image/object/bbox/ymin': dataset_util.float_list_feature(ymins),
            'image/object/bbox/ymax': dataset_util.float_list_feature(ymaxs),
            'image/object/class/text': dataset_util.bytes_list_feature(classes_text),
            'image/object/class/label': dataset_util.int64_list_feature(classes),
            }))
        
    return valid_example, tf_example

def write_tf_examples(train_writer, val_writer, yaml_file, image_data, example_source):
    
    # Load the YAML
    examples = yaml.load(open(yaml_file, 'rb').read())
    n_examples = len(examples)
    print("Loaded {:d} Examples...".format(len(examples)))
    
    # Store the examples
    n_valid = 0
    tf_example_list = []
    for counter, example in enumerate(examples):
        valid_example, tf_example = create_tf_example(example, example_source, image_data)
        if valid_example:
            tf_example_list.append(tf_example)
            n_valid += 1
        
        if counter % 500 == 0:
            print("Percent Done: {:.2f}%".format((float(counter)/float(n_examples))*100))
    
    
    # Test and validation split
    random.seed(42)
    random.shuffle(tf_example_list)
    n_train = int(0.9 * n_valid)
    train_examples = tf_example_list[:n_train]
    val_examples = tf_example_list[n_train:]
    
    for tf_example in train_examples:
        train_writer.write(tf_example.SerializeToString())
    
    for tf_example in val_examples:
        val_writer.write(tf_example.SerializeToString())
    
    print("{:d} training and {:d} validation examples.".format(len(train_examples), len(val_examples)))
    return [len(train_examples), len(val_examples)], train_writer, val_writer

def main(_):
    #python tf_record.py --output_dir /media/merberg/Centre/
 
    train_output_path = os.path.join(FLAGS.output_dir, 'tl_train.record')
    val_output_path = os.path.join(FLAGS.output_dir, 'tl_val.record')

    train_writer = tf.python_io.TFRecordWriter(train_output_path)
    val_writer = tf.python_io.TFRecordWriter(val_output_path)

    # BOSCH
    image_data = "/media/merberg/Centre/Bosch_Small_traffic_lights_dataset/"
    example_source = "BOSCH"
    
    n_bosch_test = [0,0]
    yaml_file = "BOSCH_test.yaml"   
    #n_bosch_test, train_writer, val_writer = write_tf_examples(train_writer, val_writer, yaml_file, image_data, example_source)
 
    n_bosch_train = [0,0]    
    yaml_file = "BOSCH_train.yaml"
    #n_bosch_train, train_writer, val_writer = write_tf_examples(train_writer, val_writer, yaml_file, image_data, example_source)
       
       
    # LISA
    image_data = "/media/merberg/Centre/LISA_traffic_light_dataset/"
    example_source = "LISA"
    n_lisa = [0,0]
    yaml_file = "LISA_dayTrain.yaml"
    #n_lisa, train_writer, val_writer = write_tf_examples(train_writer, val_writer, yaml_file, image_data, example_source)
    
    
    # SIMULATOR
    image_data = "/media/merberg/Centre/CarND/Term3/sim_training_data/"
    example_source = "SIM"
    n_sim = [0,0]
    yaml_file = "SIM_train.yaml"
    n_sim, train_writer, val_writer = write_tf_examples(train_writer, val_writer, yaml_file, image_data, example_source)
    
    
    train_writer.close();      
    val_writer.close()    
    print("TRAIN TFRecord created from {:d} examples".format(n_bosch_train[0]+n_bosch_test[0]+n_lisa[0]+n_sim[0]))
    print("VAL TFRecord created from {:d} examples".format(n_bosch_train[1]+n_bosch_test[1]+n_lisa[1]+n_sim[1]))

if __name__ == '__main__':
  tf.app.run()
