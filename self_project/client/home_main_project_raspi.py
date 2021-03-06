#coding:utf-8
import os
import picamera
import picamera.array
import cv2
from datetime import datetime
import requests
import subprocess
import shlex
import time
import sys
import re
import socket
from voicetext import VoiceText
import urllib2
import json
import shutil
import wiringpi2 as wiringpi
import math
import serial
import RPi.GPIO as GPIO
import threading
from Queue import Queue

def getServoDutyHw(id, val):
    if id==1:
        servo_min = 53
        servo_max = 85
    duty = int((36-102)*val/4095 + 102)
    if duty > 102:
        duty = 102
    if duty < 36:
        duty = 36
    return duty

def reverse_signal(sig):
    a=""
    for s in sig[::-1]:
        if s=="A":
            a+="C"
        elif s=="B":
            a+="D"
        elif s=="C":
            a+="A"
        elif s=="D":
            a+="B"
    return a

def track_people(ser):
    prev_x = 160
    prev_y = 120
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(23,GPIO.OUT)
    GPIO.setup(25,GPIO.OUT)
    GPIO.output(23,GPIO.HIGH)
    GPIO.output(25,GPIO.HIGH)
    kkk=0
    with picamera.PiCamera() as camera:
        with picamera.array.PiRGBArray(camera) as stream:
            camera.resolution=(320,240)
            print(2)
            while True:
                print(1)
                camera.capture(stream,'bgr',use_video_port=True)
                cascade=cv2.CascadeClassifier(cascade_path)
                gray=cv2.cvtColor(stream.array,cv2.COLOR_BGR2GRAY)
                facerect=cascade.detectMultiScale(gray,scaleFactor=1.3,minNeighbors=2,minSize=(30,30),maxSize=(150,150))
                if len(facerect)>0:
                    mindist=560
                    minindx=0
                    indx=0
                    for i,rect in enumerate(facerect):
                        
                        dist = math.fabs(rect[0]+rect[2]/2-prev_x) + math.fabs(rect[1]+rect[3]/2-prev_y)
                        if dist < mindist:
                            mindist = dist
                            minindx = indx
                        indx += 1
                    
                    face_x = facerect[minindx][0]+facerect[minindx][2]/2
                    face_y = facerect[minindx][1]+facerect[minindx][3]/2
                    
                    dx = face_x-160  
                    dy = face_y-120

                    prev_x = face_x
                    prev_y = face_y

                    if dx>15:
                        ser.write(b"D")
                        ser.write(b"A")
                        ser.write(b"E")
                        time.sleep(2.0)
                        kkk+=1
                    elif dx<-15:
                        ser.write(b"B")
                        ser.write(b"A")
                        ser.write(b"E")
                        time.sleep(2.0)
                        kkk+=1
                if kkk>6:
                    GPIO.cleanup()
                    time.sleep(5.0)
                    vt.speak(u"もう疲れたよ")
                    break
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                #cv2.imshow("frame",stream.array)
                stream.seek(0)
                stream.truncate()
            cv2.destroyAllWindows()
            
def julius_receive(ser,vt):
    #ser.write(b"A")
    #ser.write(b"E")
    citycode=130010
    resp=urllib2.urlopen('http://weather.livedoor.com/forecast/webservice/json/v1?city=%s'%citycode).read()
    resp=json.loads(resp)
    tomorrow_w=resp['description']['text'].split('\n')[-1]
    today_w=resp['description']['text'].split('\n')[-2]
    global flag
    in_flag=0
    path=[]
    name=""
    try:
        bufsize=4096
        args=julius_path + ' -C ' + jconf_path+ ' -module '
        julius=subprocess.Popen(
            shlex.split(args),
            stdin=None,
            stdout=None,
            stderr=None
        )
        time.sleep(3.0)
        julius_socket=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        julius_socket.connect(('localhost',10500))
        sf = julius_socket.makefile('rb')
        reWATSON = re.compile(r'WHYPO WORD="WATSON" .* CM="(\d\.\d*)"')
        
        while True:
            if julius.poll() is not None:
                julius_socket.close()
            else:
                line=sf.readline().decode("utf-8")
                matchOB=re.search(r'WORD=".*?"',line)
                if matchOB:
                    print(1)
                    word=re.sub(r'WORD=|"','',matchOB.group())
                    
                    if in_flag==0:
                        print(2)
                        if u'おはよう' in word:
                            vt.speak(u"おはよう、今日も一日頑張ろう！")
                        elif u'ただいま' in word:
                            print("process2")
                            vt.speak(u'おかえりなさい')
                        elif u'今日の天気を教えて' in word:
                            vt.speak(today_w)
                        elif u'明日の天気を教えて' in word:
                            vt.speak(tomorrow_w)
                        elif u'人を探して' in word:
                            vt.speak(u"誰を探しますか")
                            in_flag=1
                        elif u"進んで" in word:
                            vt.speak("すすめ〜〜")
                            ser.write(b"A")
                            ser.write(b"E")
                        elif u'右向いて' in word:
                            vt.speak(u"みぎむけー、みぎ")
                            ser.write(b"B")
                            ser.write(b"B")
                            ser.write(b"B")
                            ser.write(b"E")
                        elif u"下がって" in word:
                            vt.speak(u"さがれ〜")
                            ser.write(b'C')
                            ser.write(b"E")
                        elif u'左向いて' in word:
                            vt.speak(u'ひだりむけー、ひだり')
                            ser.write(b"D")
                            ser.write(b"D")
                            ser.write(b"D")
                            ser.write(b"E")
                        elif u"誰だかわかる" in word:
                            vt.speak(u"顔をよく見せて")
                            break
                        elif u"ついてきて" in word:
                            vt.speak(u"行きま〜す")
                            track_people(ser)
                        elif u"ハローワールド" in word:
                            vt.speak(u"はろーわーるど")
                    elif in_flag==1:
                        if u"探しません" in word:
                            vt.speak(u"聞き間違えだったのなら、ごめんなさい")
                            in_flag=0
                        else:
                            if u"みきひろさん" in word:
                                name="みきひろさん"
                            elif u"ちゃんおにさん" in word:
                                name="ちゃんおにさん"
                            elif u"わせださん" in word:
                                name="わせださん"
                            elif u"のぐちくん" in word:
                                name="のぐちくん"
                            elif u"たけもとくん" in word:
                                name="たけもとくん"
                            elif u"ゆうまくん" in word:
                                name="ゆうまくん"
                            elif u"かんくん" in word:
                                name="かんくん"
                            elif u"しんじょうくん" in word:
                                name="しんじょうくん"
                            elif u"やすあき" in word:
                                name="やすあき"
                            elif u"かりのくん" in word:
                                name="かりのくん"
                            q=name+"を探せばいいのですか？"
                            vt.speak(q)
                            in_flag=2
                    elif in_flag==2:
                        if u"違う" in word:
                            vt.speak(u"もう一回教えて")
                            in_flag=1
                        elif u"うん" in word:
                            vt.speak(u"探してきますね")
                            ser.write(b"A")
                            ser.write(b"A")
                            path.append("AA")
                            vt.speak(name+"、どこですか〜")
                            track_face()
                            send_face()
                            name2=receive_result()
                            if name==name2:
                                vt.speak("見つけました、"+name2+"ついてきてください")                                
                                path=reverse_signal(path)
                                for lll in path:
                                    ser.write(lll)
                                in_flag=0
                            else:
                                vt.speak(name2+"、"+name+"を探しているんですが、右、左まっすぐどっちに行けばいいですか？")
                                in_flag=3
                    elif in_flag==3:
                        if u"右" in word:
                            ser.write(b"B")
                            ser.write(b"B")
                            ser.write(b"B")
                            ser.write(b"A")
                            ser.write(b"A")
                            ser.write(b"A")
                            ser.write(b"A")
                            path.append("BBBAAAA")
                        elif u"左" in word:
                            ser.write(b"D")
                            ser.write(b"D")
                            ser.write(b"D")
                            ser.write(b"A")
                            ser.write(b"A")
                            ser.write(b"A")
                            ser.write(b"A")
                            path.append("DDDAAAA")
                        elif u"まっすぐ" in word:
                            ser.write(b"A")
                            ser.write(b"A")
                            ser.write(b"A")
                            ser.write(b"A")
                            ser.write(b"A")
                            path.append("AAAAA")
                        vt.speak(name+"、どこですか〜")
                        track_face()
                        send_face()
                        name2=receive_result()
                        if name==name2:
                            vt.speak("見つけました、"+name2+"ついてきてください")
                            path=reverse_signal(path)
                            for lll in path:
                                ser.write(lll)
                            in_flag=0
                        else:
                            vt.speak(name2+"、"+name+"を探しているんですが、右、左まっすぐどっちに行けばいいですか？")
                        
                tmp=reWATSON.search(line)
                if tmp:
                    if float(tmp.group(1))>0.8:
                        julius.kill()
                        while julius.poll() is None:
                            time.sleep(1.0)
                        julius_socket.close()
                        time.sleep(3.5)
        
        julius.kill()
        while julius.poll() is None:
            time.sleep(1.0)
        julius_socket.close()
        time.sleep(3.5)
        flag+=1
        
    except :
        julius.kill()
        while julius.poll() is None:
            time.sleep(1.0)
        julius_socket.close()
        sys.exit(0)
                    
def track_face():
    #顔をトラックして顔の中心が画面の中心になるようにモーターを制御
    #顔を検出したら画像をtmp directoryに保存し、10~20枚ためて学科PCに送信して深層学習
    global flag
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(23,GPIO.OUT)
    GPIO.setup(25,GPIO.OUT)
    GPIO.output(23,GPIO.HIGH)
    GPIO.output(25,GPIO.HIGH)
    PWM0=18
    PWM1=19
    wiringpi.wiringPiSetupGpio() 
    wiringpi.pinMode(PWM0, wiringpi.GPIO.PWM_OUTPUT) 
    wiringpi.pinMode(PWM1, wiringpi.GPIO.PWM_OUTPUT) 
    wiringpi.pwmSetMode(wiringpi.GPIO.PWM_MODE_MS)
    wiringpi.pwmSetClock(375)
    wiringpi.pwmWrite(PWM0, 69)
    wiringpi.pwmWrite(PWM1, 69)
    
    prev_x = 160
    prev_y = 120
    prev_input_x = 2048
    prev_input_y = 2048
    face_dir_path="./tmp/"
    if os.path.isdir(face_dir_path):
        shutil.rmtree(face_dir_path)
    os.mkdir(face_dir_path)
    
    with picamera.PiCamera() as camera:
        with picamera.array.PiRGBArray(camera) as stream:
            camera.resolution=(320,240)
            print(2)
            while True:
                print(1)
                camera.capture(stream,'bgr',use_video_port=True)
                cascade=cv2.CascadeClassifier(cascade_path)
                gray=cv2.cvtColor(stream.array,cv2.COLOR_BGR2GRAY)
                facerect=cascade.detectMultiScale(gray,scaleFactor=1.3,minNeighbors=2,minSize=(30,30),maxSize=(150,150))
                if len(facerect)>0:
                    mindist=560
                    minindx=0
                    indx=0
                    for i,rect in enumerate(facerect):
                        cv2.imwrite(face_dir_path+"face"+str(i)+"_"+datetime.now().strftime("%Y%m%d-%H%M%S")+".jpg",stream.array[rect[1]:rect[1]+rect[3],rect[0]:rect[0]+rect[2]])
                        
                        dist = math.fabs(rect[0]+rect[2]/2-prev_x) + math.fabs(rect[1]+rect[3]/2-prev_y)
                        if dist < mindist:
                            mindist = dist
                            minindx = indx
                        indx += 1
                    
                    face_x = facerect[minindx][0]+facerect[minindx][2]/2
                    face_y = facerect[minindx][1]+facerect[minindx][3]/2
                    
                    dx = face_x-160  
                    dy = face_y-120
                    
                    ratio_x = -3
                    ratio_y = -3

                    duty0 = getServoDutyHw(0, ratio_x*dx + prev_input_x)
                    wiringpi.pwmWrite(PWM0, duty0)
                    
                    duty1 = getServoDutyHw(1, ratio_y*dy + prev_input_y)
                    wiringpi.pwmWrite(PWM1, duty1)

                    prev_input_x = ratio_x*dx + prev_input_x
                    if prev_input_x > 4095:
                        prev_input_x = 4095
                    if prev_input_x < 0:
                        prev_input_x = 0
                    prev_input_y = ratio_y*dy + prev_input_y
                    if prev_input_y > 4095:
                        prev_input_y = 4095
                    if prev_input_y < 0:
                        prev_input_y = 0

                    prev_x = face_x
                    prev_y = face_y

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                #cv2.imshow("frame",stream.array)
                stream.seek(0)
                stream.truncate()
                if len(os.listdir(face_dir_path))>10:
                    flag+=1
                    GPIO.cleanup()
                    break
            cv2.destroyAllWindows()

            
def send_face():
    image_dir=os.listdir('./tmp')
    i=0
    for image_file in image_dir:
        while(1):
            try:
                soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                soc.connect(("10.10.1.122", 6677+i))#clientではサーバを動作させるホストを入力
                break
            except:
                pass
        i+=1
        if i==10:
            soc.close()
            break
        try:
            print(str(i))
            img=cv2.imread("./tmp/"+image_file)#image_pathを入力
            print("encoding...")
            jpegString=cv2.cv.EncodeImage(".jpg",cv2.cv.fromarray(img)).tostring()
            print("send image")
            soc.send(jpegString)
            soc.close()
        except:
            pass

def receive_result(queue,a=1):
    time.sleep(15.0)
    s=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("10.10.3.77",6666))
    s.listen(1)
    soc,addr=s.accept()
    name=soc.recv(1024)
    soc.close()
            
    queue.put(name)



    
if __name__=="__main__":
    cascade_path=####
    julius_path = ####
    jconf_path = #######
    ser=serial.Serial("/dev/ttyACM0",9600)
    time.sleep(2.0)
    vt=VoiceText(############)
    vt.speaker("haruka")
    flag=0
    queue = Queue()
    while(1):
        if flag==0:
            julius_receive(ser,vt)
        elif flag==1:
            print('track face')
            track_face()
        elif flag==2:
            print("sending face")
            send_face()
            flag=3
        elif flag==3:
            thread1=threading.Thread(target=receive_result,args=(queue,1))
            vt.speak(u"ん〜〜考え中〜〜君の名は")
            print("receiving name")
            #name=receive_result()
            thread1.start()
            time.sleep(1.5)
            vt.speak(u"う〜〜〜〜〜ん、もう少しで思い出せそう")
            time.sleep(3.0)
            vt.speak(u"誰かな〜？")
            thread1.join()
            name=queue.get()
            if name=="やすあき":
                vt.speak(u"おい、やすあきだ、逃げろ〜")
                ser.write(b"B")
                ser.write(b"B")
                ser.write(b"B")
                ser.write(b"B")
                ser.write(b"B")
                ser.write(b"B")
                ser.write(b"A")
                ser.write(b"A")
                ser.write(b"A")
            elif name=="ちゃんおにさん":
                vt.speak("えっと、"+name+"今日もいい調子ですね")
            else:
                vt.speak("えっと、"+name+"こんにちは")
            flag=0
