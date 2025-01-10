
import cv2
import os
import pickle
import mediapipe as mp
import face_recognition

# Initialize MediaPipe Face Detection
mp_face_detection = mp.solutions.face_detection
mp_drawing = mp.solutions.drawing_utils


root_dir = "/home/duraklefkan/Desktop/IOT-Smart-Home-Project/face-recognition/images"


def convert_bbox(x, y, width, height):
    top = y
    left = x
    right = x + width
    bottom = y + height
    return top, right, bottom, left

def save_face_encodings(face_images_dir, encoding_file_path):
    
    image_files = os.listdir(face_images_dir)
    
    known_encodings = []
    

    with mp_face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.5) as face_detection:
        for i, image_file in enumerate(image_files):
            image_path = os.path.join(root_dir, image_file)
            image = cv2.imread(image_path)
            
            
            # Convert the image color to RGB (MediaPipe requires RGB images)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            image.flags.writeable = False  # For performance improvement

            # Detect faces
            results = face_detection.process(image)

            # Convert the image color back to BGR for OpenCV
            image.flags.writeable = True
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

            
            face_locations = []
        
            if results.detections:
                for detection in results.detections:
                    # Get bounding box
                    bboxC = detection.location_data.relative_bounding_box
                    
                    h, w, _ = image.shape
                    
                    x, y, w_box, h_box = (int(bboxC.xmin * w), int(bboxC.ymin * h),
                                        int(bboxC.width * w), int(bboxC.height * h))

                    top, right, bottom, left = convert_bbox(x, y, w_box, h_box)
                    
                    face_locations.append((top, right, bottom, left))
                    
                encodings = face_recognition.face_encodings(image, face_locations)
                        
                known_encodings.extend(encodings)
    
    with open(encoding_file_path, "wb") as f:
        pickle.dump(known_encodings, f)


def load_face_encodings(encoding_file_path):
    with open(encoding_file_path, "rb") as f:
        face_encodings = pickle.load(f)
    
    return face_encodings
    
def find_number_of_known_and_unknown_faces(image, known_face_encodings):
    with mp_face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.5) as face_detection:
        
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image.flags.writeable = False

        results = face_detection.process(image)

        image.flags.writeable = True
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        
        if results.detections:
            face_locations = []
            num_knowns = 0
            num_unknowns = 0
            for detection in results.detections:
                # Get bounding box
                bboxC = detection.location_data.relative_bounding_box
                
                h, w, _ = image.shape
                
                x, y, w_box, h_box = (int(bboxC.xmin * w), int(bboxC.ymin * h),
                                      int(bboxC.width * w), int(bboxC.height * h))
                
                top = y
                left = x
                right = x + w_box
                bottom = y + h_box
                
                cv2.rectangle(image, (left, top), (right, bottom), (0, 255, 0), 2)
                
                face_locations.append((top, right, bottom, left))
                
            encodings = face_recognition.face_encodings(image, face_locations)
            
            for encoding in encodings:
                result = face_recognition.compare_faces(known_face_encodings, encoding, tolerance=0.6)
                one_third = len(result) / 3
                if sum(result) >= one_third:
                    num_knowns += 1
                else:
                    num_unknowns += 1
            
            return image, num_knowns, num_unknowns
        
        else:
            return image, 0,0
    

# #save_face_encodings(root_dir, "encodings.pkl")
# known_face_encodings = load_face_encodings("encodings.pkl")




# # Capture video from the webcam
# cap = cv2.VideoCapture(0)



# with mp_face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.5) as face_detection:
#     while cap.isOpened():
#         ret, frame = cap.read()
#         if not ret:
#             break


#         num_knowns, num_unknowns = find_number_of_known_and_unknown_faces(frame, known_face_encodings)
#         print("Num of knowns: ", num_knowns)
#         print("Num of unknowns: ", num_unknowns)

#         # Display the output frame
#         cv2.imshow('Face Detection', frame)

#         if cv2.waitKey(5) & 0xFF == 27:  # Press 'Esc' to exit
#             break

# cap.release()
# cv2.destroyAllWindows()

