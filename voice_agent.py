
from tools import book_appointment, cancel_appointment, update_appointment, search_appointment
from response_generator import generate_response
from router import classify_service_type
from faster_whisper import WhisperModel
from scipy.io.wavfile import write
from piper import PiperVoice
import sounddevice as sd
import numpy as np
import torch
import time
import json
import re

# Load Whisper
whisper = WhisperModel("base", device="cpu", compute_type="int8")

# Load Silero VAD
vad_model, utils = torch.hub.load(
    repo_or_dir="snakers4/silero-vad",
    model="silero_vad",
    force_reload=False
)

SAMPLE_RATE = 16000
CHUNK_SIZE = 512
SILENCE_LIMIT = 1.5
MAX_LISTEN_DURATION = 2

# Initialize TTS
voice = PiperVoice.load("en_US-lessac-medium.onnx")

break_flags = ["exit", "quit", "break"]

def listen():
    vad_model.reset_states()

    audio_chunks = []
    speech_started = False
    silence_duration = 0

    start_time = time.monotonic()

    print("\nListening...")

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        blocksize=CHUNK_SIZE
    ) as stream:

        while True:
            audio, overflowed = stream.read(CHUNK_SIZE)
            audio = audio.flatten()

            audio_tensor = torch.from_numpy(audio)
            speech_prob = vad_model(audio_tensor, SAMPLE_RATE).item()

            chunk_duration = CHUNK_SIZE / SAMPLE_RATE

            # Maximum time to wait for the user to start speaking
            if not speech_started:
                if time.monotonic() - start_time >= MAX_LISTEN_DURATION:
                    print("Listening timeout!")
                    return None

            if speech_prob > 0.3:
                speech_started = True
                silence_duration = 0

            elif speech_started:
                silence_duration += chunk_duration

            if speech_started:
                audio_chunks.append(audio)

            if speech_started and silence_duration >= SILENCE_LIMIT:
                print("Speech completed!")
                break

    if not audio_chunks:
        return None

    complete_audio = np.concatenate(audio_chunks)

    write("recording.wav", SAMPLE_RATE, complete_audio)

    return "recording.wav"


def transcribe(audio_file):

    segments, info = whisper.transcribe(audio_file)

    text = " ".join(segment.text.strip() for segment in segments)

    return text.strip()


def speak(text):
    audio_chunks = []

    for chunk in voice.synthesize(text):
        audio_chunks.append(chunk.audio_int16_array)

    audio = np.concatenate(audio_chunks)

    sd.play(audio, samplerate=22050)
    sd.wait()

speak("Hello! I am hospital receptionist. How can I help you today?")

while True:
    
    audio_file = listen()

    if audio_file is None:
        continue

    user_input = transcribe(audio_file)

    if not user_input:
        continue

    print("You:", user_input)
    service_type, required_fields = classify_service_type(user_input)

    if service_type == "Cancel_Appointment" or service_type == "Update_Appointment" or service_type == "Search_Appointment":

        while True:

            speak("Please provide your appointment ID.")
            appointment_id = input("Enter appointment ID: ").strip().upper()

            if re.fullmatch(r"APT-[A-F0-9]{10}", appointment_id):
                break
            speak("Invalid appointment ID. Please enter it again.")
            
        with open("content_memory.json", "r", encoding="utf-8") as file:
            memory = json.load(file)

        memory["appointment_id"] = appointment_id

        with open("content_memory.json", "w") as file:
            json.dump(memory, file, indent=4)
        
    speak("Okay! Please wait while I process your request.")
    break

 # Main voice agent loop
while True:

    if service_type == "Cancel_Appointment":
        speak("Please enter yes to Conform the your appointment cancellation request ")
        print("\n Cancellation request Intiated\n")
        conformation =  input("Enter Yes/No: ")
        if  conformation.lower() == "yes":
            result = cancel_appointment(memory.get("appointment_id"))
            print("AI: ",result)
            speak(result)
            
        else:
            print("AI: Okay Cancellation request stopped")
            speak("Okay Cancellation request stopped")
        break

    elif service_type == "Search_Appointment":
        result = search_appointment(memory.get("appointment_id"))
        print("AI: ",result)
        speak(result)
        break

    else: 
        with open("content_memory.json", "r") as file:
                memory = json.load(file)
        
        response = generate_response(
            message=user_input,
            memory=memory,
            required_fields=required_fields
        )

        if response:
            memory.update(response["memory"])
            with open("content_memory.json", "w") as file:
                json.dump(memory, file, indent=4)

        print("AI:", response["response"])
        print("Memory :",json.dumps(response["memory"], indent=4))

            # Speak response
        speak(response["response"])
    
    if response["is_complete"]:

        print("All required fields have been collected. Proceeding with the service.")

        # Here you can call the appropriate function from tools.py based on service_type
        if service_type == "Book_Appointment":
            result = book_appointment(memory)

        elif service_type == "Update_Appointment":
            result = update_appointment(memory.get("appointment_id"), memory.get("updated_details", {}))

        else:
            result = "Service type not recognized."

        # Clearing the Memory
        with open("ideal_memory.json","r") as source:
            memory = json.load(source)

        with open("content_memory.json", "w") as dest:
            json.dump(memory,dest,indent=4)

        print("Result:", result)
        speak(result)

    audio_file = listen()
    
    if audio_file is None:
        continue

    user_input = transcribe(audio_file)

    if not user_input:
        continue

    print("You:", user_input)

    # Check exit command
    if user_input.lower().strip().rstrip(".!?") in break_flags:
        print("Exiting voice agent...")
        break

    time.sleep(0.5)  # Short pause before next iteration
speak("Thank you for calling")