#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""===============================================================================
 Project : Freenove Robot Dog - Video Client
 File    : Face.py
 Author  : MT & GitHub Copilot (GPT)

 Description:
     - Face detection using Haar cascade
     - Optional face recognition using LBPH (requires opencv-contrib-python)

 Version Control:
     - Tracked in this project's Git workspace.

 Revision History:
     v1.00 (2026-01-19): Add project-style header; make recognizer optional/robust.

 Notes:
     - If OpenCV is installed without contrib modules, `cv2.face` will be missing.
         In that case we gracefully fall back to detection-only.
     - Recognition requires a trained model file: Face/face.yml
===============================================================================
"""

import os
import sys

import cv2
import numpy as np


class Face:
    def __init__(self):
        self.recognizer = None
        self.recognizer_ready = False
        try:
            if hasattr(cv2, "face") and hasattr(cv2.face, "LBPHFaceRecognizer_create"):
                self.recognizer = cv2.face.LBPHFaceRecognizer_create()
                # face.yml may not exist on fresh setups; ignore if missing.
                if os.path.exists('Face/face.yml'):
                    self.recognizer.read('Face/face.yml')
                    self.recognizer_ready = True
                else:
                    print("[WARN] Face/face.yml not found; face recognition is disabled (detection still works).")
            else:
                print(
                    "[WARN] OpenCV was built without 'cv2.face' (opencv-contrib-python). "
                    "Face recognition is disabled."
                )
        except Exception as e:
            print(f"[WARN] Face recognizer init failed; disabled: {e}")
            self.recognizer = None
            self.recognizer_ready = False
        self.detector = cv2.CascadeClassifier("Face/haarcascade_frontalface_default.xml")
        self.name = self.Read_from_txt('Face/name')
    def Read_from_txt(self, filename):
        file1 = open(filename + ".txt", "r")
        list_row = file1.readlines()
        list_source = []
        for i in range(len(list_row)):
            column_list = list_row[i].strip().split("\t")
            list_source.append(column_list)
        for i in range(len(list_source)):
            for j in range(len(list_source[i])):
                list_source[i][j] = str(list_source[i][j])
        file1.close()
        return list_source

    def Save_to_txt(self, list, filename):
        file2 = open(filename + '.txt', 'w')
        for i in range(len(list)):
            for j in range(len(list[i])):
                file2.write(str(list[i][j]))
                file2.write('\t')
            file2.write('\n')
        file2.close()
    def getImagesAndLabels(self,path='Face'):
        imagePaths = [os.path.join(path,f) for f in os.listdir(path)]
        faceSamples=[]
        labels = []
        for imagePath in imagePaths:
            if os.path.split(imagePath)[-1].split(".")[1]=="jpg":
                id = int(os.path.split(imagePath)[-1].split(".")[0])
                img = cv2.imread(imagePath)
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                faces = self.detector.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5)
                for (x,y,w,h) in faces:
                    faceSamples.append(gray[y:y+h,x:x+w])
                    labels.append(id)
        return faceSamples,labels
    def trainImage(self):
        if self.recognizer is None:
            print("[WARN] trainImage skipped: face recognizer unavailable (install opencv-contrib-python).")
            return
        faces, labels = self.getImagesAndLabels()
        self.recognizer.train(faces, np.array(labels))
        self.recognizer.write('Face/face.yml')
        self.recognizer.read('Face/face.yml')
        self.recognizer_ready = True
        print("\n  {0} faces trained.".format(len(np.unique(labels))))
    def face_detect(self,img):
        try:
            if sys.platform.startswith('win') or sys.platform.startswith('darwin'):
                gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
                faces = self.detector.detectMultiScale(gray,1.2,5)
                if len(faces)>0 :
                    for (x,y,w,h) in faces:
                        cv2.rectangle(img, (x, y), (x+w, y+h), (0, 255, 0), 2)
                        if self.recognizer is None or not self.recognizer_ready:
                            cv2.putText(
                                img,
                                str("face"),
                                (x + 5, y + h + 30),
                                cv2.FONT_HERSHEY_DUPLEX,
                                1,
                                (0, 255, 0),
                                2,
                            )
                        else:
                            id, confidence = self.recognizer.predict(gray[y:y + h, x:x + w])
                            #print("confidence",id,confidence)
                            if confidence > 100:
                                cv2.putText(img, str("unknow"), (x + 5, y + h + 30), cv2.FONT_HERSHEY_DUPLEX, 1,
                                            (0, 255, 0), 2)
                            else:
                                cv2.putText(img, self.name[int(id)][1], (x + 5, y + h + 30), cv2.FONT_HERSHEY_DUPLEX, 1,
                                            (0, 255, 0), 2)
        except Exception as e:
            print(e)

if __name__ == '__main__':
    f=Face()
    f.trainImage()


