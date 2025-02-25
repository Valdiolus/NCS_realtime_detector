
# import the necessary packages
from mvnc import mvncapi as mvnc
from imutils.video import VideoStream
import numpy as np
import time
import datetime
import cv2

confidence_basic=0.5
display = 1
time_calc = 1
RPI = 0

fps = 0
fps_time_new = 0
fps_time_old = datetime.datetime.now()
i_fps = 3
i_cycle = 0
fps_delta = 0

timef = np.zeros(100)


# initialize the list of class labels our network was trained to
# detect, then generate a set of bounding box colors for each class
CLASSES = ("background", "aeroplane", "bicycle", "bird",
           "boat", "bottle", "bus", "car", "cat", "chair", "cow",
           "diningtable", "dog", "horse", "motorbike", "person",
           "pottedplant", "sheep", "sofa", "train", "tvmonitor")
COLORS = np.random.uniform(0, 255, size=(len(CLASSES), 3))

# frame dimensions should be sqaure
PREPROCESS_DIMS = (300, 300)
DISPLAY_DIMS = (640, 480)

# calculate the multiplier needed to scale the bounding boxes
DISP_MULTIPLIER = DISPLAY_DIMS[0] // PREPROCESS_DIMS[0]


def Time_saving(t_number):
    if time_calc == 1:
        timef[t_number] = time.time()
    return 0

def Time_print(t_number):
    if time_calc == 1:
        print("time %1s: %1.1f ms" % (t_number, (time.time() - timef[t_number])*1000))
    return 0

def preprocess_image(input_image):
    # preprocess the image
    preprocessed = cv2.resize(input_image, PREPROCESS_DIMS)
    preprocessed = preprocessed - 127.5
    preprocessed = preprocessed * 0.007843
    preprocessed = preprocessed.astype(np.float16)

    # return the image to the calling function
    return preprocessed


def predict(image, graph):
    # preprocess the image
    image = preprocess_image(image)

    # send the image to the NCS and run a forward pass to grab the
    # network predictions
    graph.LoadTensor(image, None)
    (output, _) = graph.GetResult()

    # grab the number of valid object predictions from the output,
    # then initialize the list of predictions
    num_valid_boxes = output[0]
    predictions = []

    # loop over results
    for box_index in range(int(num_valid_boxes)):
        # calculate the base index into our array so we can extract
        # bounding box information
        base_index = 7 + box_index * 7

        # boxes with non-finite (inf, nan, etc) numbers must be ignored
        if (not np.isfinite(output[base_index]) or
                not np.isfinite(output[base_index + 1]) or
                not np.isfinite(output[base_index + 2]) or
                not np.isfinite(output[base_index + 3]) or
                not np.isfinite(output[base_index + 4]) or
                not np.isfinite(output[base_index + 5]) or
                not np.isfinite(output[base_index + 6])):
            continue

        # extract the image width and height and clip the boxes to the
        # image size in case network returns boxes outside of the image
        # boundaries
        (h, w) = image.shape[:2]
        x1 = max(0, int(output[base_index + 3] * w))
        y1 = max(0, int(output[base_index + 4] * h))
        x2 = min(w, int(output[base_index + 5] * w))
        y2 = min(h, int(output[base_index + 6] * h))

        # grab the prediction class label, confidence (i.e., probability),
        # and bounding box (x, y)-coordinates
        pred_class = int(output[base_index + 1])
        pred_conf = output[base_index + 2]
        pred_boxpts = ((x1, y1), (x2, y2))

        # create prediciton tuple and append the prediction to the
        # predictions list
        prediction = (pred_class, pred_conf, pred_boxpts)
        predictions.append(prediction)

    # return the list of predictions to the calling function
    return predictions


# grab a list of all NCS devices plugged in to USB
print("[INFO] finding NCS devices...")
devices = mvnc.EnumerateDevices()

# if no devices found, exit the script
if len(devices) == 0:
    print("[INFO] No devices found. Please plug in a NCS")
    quit()

# use the first device since this is a simple test script
# (you'll want to modify this is using multiple NCS devices)
print("[INFO] found {} devices. device0 will be used. "
      "opening device0...".format(len(devices)))
device = mvnc.Device(devices[0])
device.OpenDevice()

# open the CNN graph file
print("[INFO] loading the graph file into RPi memory...")
with open('graphs/mobilenetgraph', mode="rb") as f:
    graph_in_memory = f.read()

# load the graph into the NCS
print("[INFO] allocating the graph on the NCS...")
graph = device.AllocateGraph(graph_in_memory)

#add text
font = cv2.FONT_HERSHEY_SIMPLEX

# open a pointer to the video stream thread and allow the buffer to
print("[INFO] starting the video stream and FPS counter...")
if RPI==0:
    vs = VideoStream(src=0).start()
else:
    vs = VideoStream(usePiCamera=True).start()
time.sleep(1)

# loop over frames from the video file stream
while True:
    try:
        # grab the frame from the threaded video stream
        # make a copy of the frame and resize it for display/video purposes
        Time_saving(0)
        frame = vs.read()
        Time_print(0)
        Time_saving(1)
        image_for_result = frame.copy()
        Time_print(1)
        Time_saving(2)
        image_for_result = cv2.resize(image_for_result, DISPLAY_DIMS)
        Time_print(2)

        # use the NCS to acquire predictions
        Time_saving(3)
        predictions = predict(frame, graph)
        Time_print(3)

        # loop over our predictions
        for (i, pred) in enumerate(predictions):
            # extract prediction data for readability
            Time_saving(4)
            (pred_class, pred_conf, pred_boxpts) = pred
            Time_print(4)

            # filter out weak detections by ensuring the `confidence`
            # is greater than the minimum confidence
            if pred_conf > confidence_basic:
                # print prediction to terminal
                #print("[INFO] Prediction #{}: class={}, confidence={}, ""boxpoints={}".format(i, CLASSES[pred_class], pred_conf,pred_boxpts))

                # check if we should show the prediction data
                # on the frame
                Time_saving(5)
                if display > 0:
                    # build a label consisting of the predicted class and
                    # associated probability
                    label = "{}: {:.2f}%".format(CLASSES[pred_class],
                                                 pred_conf * 100)

                    # extract information from the prediction boxpoints
                    (ptA, ptB) = (pred_boxpts[0], pred_boxpts[1])
                    ptA = (ptA[0] * DISP_MULTIPLIER, ptA[1] * DISP_MULTIPLIER)
                    ptB = (ptB[0] * DISP_MULTIPLIER, ptB[1] * DISP_MULTIPLIER)
                    (startX, startY) = (ptA[0], ptA[1])
                    y = startY - 15 if startY - 15 > 15 else startY + 15

                    # display the rectangle and label text
                    cv2.rectangle(image_for_result, ptA, ptB,
                                  COLORS[pred_class], 2)
                    cv2.putText(image_for_result, label, (startX, y),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, COLORS[pred_class], 3)
                Time_print(5)

        # FPS calculation
        Time_saving(6)
        fps_time_new = datetime.datetime.now()
        fps_delta = (fps_time_new - fps_time_old).total_seconds()
        fps_time_old = fps_time_new
        print("%1.2ffps" % fps)


        if i_cycle == i_fps:
            fps = 1 / float(fps_delta)
            i_cycle = 0
        else:
            i_cycle += 1

        cv2.putText(image_for_result, "%1.1f fps" % fps, (10, 30),
                    font, 1, (0, 0, 255), 2, cv2.LINE_AA)
        Time_print(6)
        # check if we should display the frame on the screen
        # with prediction data (you can achieve faster FPS if you
        # do not output to the screen)
        if display > 0:
            # display the frame to the screen
            Time_saving(7)
            cv2.imshow("Output", image_for_result)
            Time_print(7)

        #wait escape
        if cv2.waitKey(1) & 0xFF == 27:
            break
        print("time lap: %1.3f" % fps_delta)

    # if "ctrl+c" is pressed in the terminal, break from the loop
    except KeyboardInterrupt:
        break

    # if there's a problem reading a frame, break gracefully
    except AttributeError:
        break


# destroy all windows if we are displaying them
if display > 0:
    cv2.destroyAllWindows()

# stop the video stream
vs.stop()

# clean up the graph and device
graph.DeallocateGraph()
device.CloseDevice()

