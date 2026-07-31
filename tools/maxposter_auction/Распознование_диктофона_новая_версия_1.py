from pprint import pprint
from re import search
from vosk import Model, KaldiRecognizer
import sys
import json
import glob, os
import time
import wave
import binascii
from pydub import AudioSegment, effects  
import datetime
import requests
import soundfile as sf


def speed_change(sound, speed=1.0):
    # Manually override the frame_rate. This tells the computer how many
    # samples to play per second
    sound_with_altered_frame_rate = sound._spawn(sound.raw_data, overrides={
         "frame_rate": int(sound.frame_rate * speed)
      })
     # convert the sound with altered frame rate to a standard frame rate
     # so that regular playback programs will work right. They often only
     # know how to play audio at standard frame rate (like 44.1k)
    return sound_with_altered_frame_rate.set_frame_rate(sound.frame_rate)


def match_target_amplitude(sound, target_dBFS):
    change_in_dBFS = target_dBFS - sound.dBFS
    return sound.apply_gain(change_in_dBFS)


def recognize(model, data_json, path_audio, chanel, id):
    #Экземляр калди
    rec = KaldiRecognizer(model, 8000)
    rec.SetWords(True)

    wf      = wave.open(path_audio, "rb")
    bit     = 8000
    #wf.getframerate()
    last_n  = False
    
    while True:
        data = wf.readframes(bit)
        if len(data) == 0:
            break
        frames = wf.getnframes()
        rate = wf.getframerate()
        duration = frames / float(rate)

        if rec.AcceptWaveform(data):
            res = json.loads(rec.Result())

            if res['text'] != '':
                data_json_result = res['result']
                for dj in data_json_result:
                    param = {
                        'start': dj['start'],
                        'chanel': chanel,
                        'data': dj
                        }
                    data_json.append(param)
                    print('-' + str(id) + ' / ' + str(dj['start']) + ' / ' + str(duration))
                last_n = False
            elif not last_n:
                last_n = True

    return data_json


def convert_to_preferred_format(sec): 
    sec = int(sec)
    if sec > 0:
        sec = sec % (24 * 3600) 
        hour = sec // 3600 
        sec %= 3600 
        min = sec // 60 
        sec %= 60 
        if hour > 0:
            return "%02d:%02d:%02d" % (hour, min, sec)
        else:
            return "%02d:%02d" % (min, sec)
    else:
        return "00:00"


def recognition(id, model, file_name, file_folder, info_model):
    name = file_name
    sound_path = file_folder + '/' + name
    mp3 = False

    if name.find('.mp3')> 0:
        sound   = AudioSegment.from_mp3(file_name)
    else:
        sound   = AudioSegment.from_file(file_name)
    chanels = sound.channels

    params_list_audio = list()
    #Дата и время распознования
    now = datetime.datetime.now()
    params_list_audio.append("дата и время расшифровки: " + now.strftime("%d-%m-%Y %H:%M"))



    #Информация о аудио
    params_list_audio.append("dBFS - исходная: " + str(sound.dBFS))
    params_list_audio.append("продолжительность: " + str(sound.duration_seconds))
    params_list_audio.append("каналов: " + str(sound.channels))
    params_list_audio.append("максимальная амплитуда: " + str(sound.max))

    #Нормализация звукового сигнала
    sound   = effects.normalize(sound) 
    params_list_audio.append("нормализация звука: ВКЛ")


    #Скорость звукового сигнала
    #sound = speed_change(sound, 0.99)
    params_list_audio.append("скорость: 1х")


    #Приглушить каналы, оптимально примерно -30 для конечного сигнала
    if chanels == 1:
       sound = match_target_amplitude(sound, -30)
    #else:
    #    left_chanel     = -20
    #    right_chanel    = -20

    #    sound   = sound.apply_gain_stereo(left_chanel, right_chanel)
    #    params_list_audio.append("настройка приглушения: " + str(left_chanel) + " || " + str(right_chanel))
    
    params_list_audio.append("dBFS - после приглушения: " + str(sound.dBFS))


    #Инвертация для подавления шума
    sound.invert_phase()
    params_list_audio.append("инвертация фазы: ВКЛ")


    #Разделение звука на разные каналы
    
    #Массив результата
    data_json = list()

    if chanels == 1:
        path_audio_1 = r"C:\model_small\file1.wav"
        if sound.frame_rate != 8000: 
            sound = sound.set_frame_rate(8000)
        sound.export(path_audio_1, format = "wav")
        
        data_json = recognize(model, data_json, path_audio_1, 0, id)
    else:
        sounds          = sound.split_to_mono()
        sound1          = sounds[0]
        path_audio_1 = r"C:\model_small\file1.wav"
        
        sound1.frame_rate = 8000
        sound1.export(path_audio_1, format = "wav")
        
        data_json = recognize(model, data_json, path_audio_1, 0, id)
       
    #Длительность и имя записи: 
    sound.invert_phase()

    info_audio = {
            "name": name,
            "path": sound_path,
            "time": convert_to_preferred_format(str(sound.duration_seconds).split('.')[0]),
            "seconds": str(sound.duration_seconds).split('.')[0]
        }

    #Сортируем по времени данные
    data_list = sorted(data_json, key = lambda d:d['start'])

    text_list = list()
    operator = 0
    start = '0' 
    text_root = ''
    for data_base in data_list:
        chanel = data_base['chanel']
        if chanel != operator:
            start = convert_to_preferred_format(start.split('.')[0])
            fraza = {
                "start": start,
                "words": text_root,
                "operator": operator
            }
            text_list.append(fraza)
            start = str(data_base['data']['start'])
            text_root = data_base['data']['word'] 
            operator = data_base['chanel'] 
        else:
            text_root = text_root + " " + data_base['data']['word']     

    start = convert_to_preferred_format(start.split('.')[0])
    fraza = {
        "start": start,
        "words": text_root,
        "operator": operator
    }
    text_list.append(fraza)

    #Подготовим и запишем данные - потом все равно на сайт отправим даже без записи
    params = {
        'id'            : id,
        'info_model'    : info_model,
        'info_audio'    : info_audio,
        'info'          : params_list_audio,
        'data'          : text_list,
        'conf'          : data_list
        }

    resp = requests.post("http://k01srvdash/api/post_recordeds_voice_audio/", data=str(params).encode('utf-8'))
    print(resp.text)
    #path_save = file_folder + '/' + file_name.replace(".mp3", ".txt")
    #f = open(path_save, 'w', encoding="utf-8")  
    #f.write(str(params))
    #f.close()

AudioSegment.converter  = "C:\\ffmpeg\\bin\\ffmpeg.exe"
AudioSegment.ffmpeg     = "C:\\ffmpeg\\bin\\ffmpeg.exe"
AudioSegment.ffprobe    = "C:\\ffmpeg\\bin\\ffprobe.exe"

#model_path   = r"C:\py_test\vosk-model-ru-0.22"
#model_path   = r"D:\vosk\vosk-model"
#model_path   = r"C:\vosk-model-ru-0.10"
#model_path   = r"D:\vosk\kors_group_0_10_1"

model_path      = r"C:\models_vosk\vosk-model-ru-0.22_1"
model           = Model(model_path)

while True:
    
    date_string = f'{datetime.datetime.now():%Y-%m-%d %H:%M:%S%z}'
    
    print("Ожидаем данные для распознования - " + date_string)
    
    time.sleep(60)

    resp = requests.get("http://k01srvdash/api/get_recordeds_voice_audio/")
    
    list_records = json.loads(resp.content)['answer']

    if len(list_records) > 0: 
    
        params = ''

        params_list_audio = list()

        model_name = os.path.basename(os.path.normpath(model_path))
        model_path = model_path
        info_model = {
            'path': model_path,
            'name': model_name
            }

        for record in list_records:
            id = record[0]
            path_audio = str('//K01SRVDASH' + '/' + record[2]).replace('/', '"\"').replace('"','/').replace('//', '/')
            try:
                recognition(id, model, str(path_audio), path_audio, info_model)
            except:
                print("---")
                print("ERROR ///  " + str(path_audio))
                print("---")
        


#
#search_path = r"\\a01srvfs\PBX\A15\sounds"
#s = 0
#for file in os.listdir(search_path):
#    if file.endswith(".mp3"):
#        recognition(model, str(file), search_path, info_model)
#        s = s + 1 
#        print(str(s))

