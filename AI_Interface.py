import tkinter as tk
from tkinter import scrolledtext, ttk
import speech_recognition as sr
import threading
import ollama
import edge_tts
import asyncio
import os
import multiprocessing
import sounddevice as sd
import soundfile as sf
import time
import uuid

class AILocalInterface:
    def __init__(self, master, instance_id):
        self.master = master
        self.instance_id = instance_id
        master.title("AI Interface")
        master.geometry("300x500")  # Set the initial size of the window
        master.minsize(300, 500)  # Set the minimum size of the window
        
        # Settings folder BootUp
        self.context_file = "settings/context.txt"
        self.load_context()
        self.session_based_memory = self.load_settings("settings/SessionMemory.txt")
        self.voice = self.load_settings("settings/SpeechReader.txt")
        sd.default.device = (self.load_settings("settings/DefaultAudioInput.txt"), self.load_settings("settings/DefaultAudioOutput.txt"))
        self.memory_limit = int(self.load_settings("settings/MemoryLimit.txt"))
        self.ollama_ai_model = self.load_settings("settings/OllamaAiModel.txt")
        
        #Memory Variables
        self.current_saved_memory_limit = False       #Used to find how many "Memories" exist - Boolean
        self.saved_memory_texts = 0                   #Used to count the number of "Memories" and to replace the older ones - Integer
        self.current_saved_memories = 0
        
        #Memory Message Variable - Used to store the prompt designed for the AI to not focus on the "past"
        self.memory_input = " "
        self.memory_refresher = 0
        
        # Turn off the Microphone for Boot and Start Voice Recognizer
        self.is_mic_on = False
        self.micboot = 0
        self.mic = sr.Microphone()
        self.recognizer = sr.Recognizer()
        self.auto_voice = self.load_settings("settings/AutoVoice.txt")

        # Create a frame for better layout management
        self.frame = tk.Frame(master, padx=15, pady=15)
        self.frame.pack(fill=tk.BOTH, expand=True)

        # Toggle Dark Mode Button
        self.toggle_dark_mode_button = tk.Button(self.frame, text="D", command=self.toggle_dark_mode, width=1, height=1)
        self.toggle_dark_mode_button.grid(row=0, column=0, columnspan=2, sticky='e', padx=(0, 1), pady=(0, 5))
        
        # Microphone Button
        self.mic_button = tk.Button(self.frame, text="Turn Mic On", command=self.toggle_mic)
        self.mic_button.grid(row=0, column=0, columnspan=2, sticky='ew', padx=(0, 18), pady=(0, 5))

        # Manual Input Box
        self.manual_input_label = tk.Label(self.frame, text="Manual Input:")
        self.manual_input_label.grid(row=1, column=0, columnspan=2, sticky='w', pady=(0, 5))

        self.manual_input = tk.Entry(self.frame)
        self.manual_input.grid(row=2, column=0, columnspan=2, sticky='ew', pady=(0, 5))

        self.submit_button = tk.Button(self.frame, text="Submit", command=self.submit_text)
        self.submit_button.grid(row=3, column=0, columnspan=2, sticky='ew', pady=(0, 15))

        # Chat Log
        self.chat_log_label = tk.Label(self.frame, text="Chat Log:")
        self.chat_log_label.grid(row=4, column=0, columnspan=2, sticky='w', pady=(0, 5))

        self.chat_log = scrolledtext.ScrolledText(self.frame, wrap=tk.WORD)
        self.chat_log.grid(row=5, column=0,columnspan=2, sticky='nsew')    
        
         # Clear Button
        self.clear_button = tk.Button(self.frame, text="Clear Chat Log", command=self.clear_chat_log)
        self.clear_button.grid(row=6, column=0, ipadx=25, sticky='ew', padx=(0, 5), pady=(5, 0))

        # Voice Selection Button
        self.voice_button = tk.Button(self.frame, text="Settings", command=self.open_settings_menu)
        self.voice_button.grid(row=6, column=1, ipadx=25, sticky='ew', padx=(5, 0), pady=(5, 0))

        # Open Context Manager Window Button
        self.open_context_manager_button = tk.Button(self.frame, text="Context Manager", command=self.open_context_manager)
        self.open_context_manager_button.grid(row=7, column=0, ipadx=25, sticky='ew', padx=(0, 5), pady=5)

        # Open Context Audio Window Button
        self.open_audio_manager_button = tk.Button(self.frame, text="Addons Menu", command=self.open_audio_manager)
        self.open_audio_manager_button.grid(row=7, column=1, ipadx=25, sticky='ew', padx=(5, 0), pady=5)

        # Processing Indicator
        self.processing_indicator = tk.Label(self.frame, text="Processing: Off", fg="red")
        self.processing_indicator.grid(row=10, column=0, columnspan=2, sticky='ew')

        # Configure grid weights
        self.frame.grid_columnconfigure(0, weight=1)
        self.frame.grid_columnconfigure(1, weight=1)
        self.frame.grid_rowconfigure(5, weight=1)
        self.frame.grid_rowconfigure(6, weight=0)
        self.frame.grid_rowconfigure(7, weight=0)
        self.frame.grid_rowconfigure(8, weight=0)
        
        #DarkMode BootUp
        if self.load_settings("settings/darkmodestate.txt") == 'True':
            #print(self.load_settings("settings/darkmodestate.txt")) # Test if condition was working
            self.is_dark_mode = False
            self.toggle_dark_mode()            
        else:
            self.is_dark_mode = False
            
        # Initialize window variables
        self.settings_window = None
        self.context_manager_window = None

        # Bind the configure event to the resizing function
        self.master.bind('<Configure>', self.on_resize)
        
        # Memory Module (Session Based system with 1 integer and 1 strings) - Probably exists a more efficient way to do it
        self.memory_value = 0
        self.str1 = ""
        self.str2 = ""
        self.str3 = ""
        self.str4 = ""
        self.str5 = ""
        self.str6 = ""
        self.str7 = ""
        self.str8 = ""
        self.str9 = ""
        self.str10 = ""
        
        #BootUp Experience -> 0 = boot | Other Values = Normal Use
        self.update_chat_log(f"Booting Up\n")
        threading.Thread(target=asyncio.run, args=(self.speak_response("Boot Up Complete", 0),)).start()
        
    def load_context(self):
        try:
            with open(self.context_file, "r") as file:
                self.context = file.read().strip()
        except FileNotFoundError:
            self.context = "Please respond naturally and coherently to the user's input."
    
    def load_settings(self, directory):
        try:
            with open(directory, "r") as file:
                return file.read().strip()
        except:
            return None
    
    def save_settings(self, directory, message):
        with open(directory, "w") as file:
            file.write(message)
    
    def save_context(self):
        with open(self.context_file, "w") as file:
            file.write(self.context)

    def toggle_mic(self):
        if self.is_mic_on:
            self.is_mic_on = not self.is_mic_on
            self.mic_button.config(text="Turn Mic On")
            self.update_processing_indicator(False)
        else:
            self.is_mic_on = not self.is_mic_on
            self.micboot = 1
            self.mic_button.config(text="Turn Mic Off")
            self.start_listening()

    def start_listening(self):
        if self.is_mic_on:
            threading.Thread(target=self.listen_microphone, daemon=True).start()

    def listen_microphone(self):
        while self.is_mic_on: 
            try:
                with self.mic as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=1)
                    self.update_processing_indicator(True)
                    try:
                        audio = self.recognizer.listen(source)
                        print("Got the audio!")
                    except sr.WaitTimeoutError:
                        print("You took too long to start speaking!")
                        continue
                        
                    try:
                        text = self.recognizer.recognize_google(audio)
                        self.manual_input.delete(0, tk.END)
                        self.manual_input.insert(0, text)
                    except sr.UnknownValueError:
                        print("Google Speech Recognition could not understand the audio")
                    except sr.RequestError as e:
                        print(f"Could not request results from Google Speech Recognition service; {e}")
                    self.update_processing_indicator(False)
                    self.toggle_mic()
                    self.submit_text()
            except Exception as e:
                print(f"Something went wrong: {e}")
                self.update_processing_indicator(False)
                pass

    def submit_text(self):
        input_text = self.manual_input.get()
        self.manual_input.delete(0, tk.END)
        if input_text:
            ai_response = self.get_ai_response(input_text)
            self.update_chat_log(f"You: {input_text}\n")
            self.update_chat_log(f"AI: {ai_response}\n")
            threading.Thread(target=asyncio.run, args=(self.speak_response(ai_response, 1),)).start()  # Read out the AI response asynchronously

    def clear_chat_log(self):
        self.chat_log.delete(1.0, tk.END)

    def update_processing_indicator(self, is_processing):
        if is_processing:
            self.processing_indicator.config(text="Processing: On", fg="green")
        else:
            self.processing_indicator.config(text="Processing: Off", fg="red")

    def update_chat_log(self, message):
        self.chat_log.insert(tk.END, message)
        self.chat_log.see(tk.END)  # Scroll to the end of the chat log

    def get_ai_response(self, input_text):
        if self.session_based_memory == "False":
            #Variable Setup (Memory Input + Memory Count + Current Limit)
            directory = "Memory/"
            try:
                #Single Time Loop to figure out how many saved messages exist on boot.
                while self.current_saved_memory_limit != True:
                    current_location = directory + "mem" + str(self.saved_memory_texts + 1) + ".txt"
                    if self.load_settings(current_location) != None and self.load_settings(current_location) != "" and self.saved_memory_texts < self.memory_limit:
                        self.saved_memory_texts += 1
                    else:
                        self.current_saved_memories = self.saved_memory_texts
                        self.current_saved_memory_limit = True
                        
            except Exception as e:
                print(f"Error generating response: {e}")  # Debug print
                return "Sorry, I couldn't generate a response."
                
                #Memory provisioning to the AI.
            try:
                while self.memory_refresher < self.memory_limit and self.memory_refresher < self.current_saved_memories:
                    current_location = directory + "mem" + str(self.memory_refresher + 1) + ".txt"
                    self.memory_refresher += 1
                    if self.memory_refresher == 1:
                        self.memory_input = "The following is the context of our current conversation: " + self.load_settings(current_location)
                    else:
                        self.memory_input = self.memory_input + self.load_settings(current_location)
            
            except Exception as e:
                print(f"Error generating response: {e}")  # Debug print
                print(self.memory_refresher)
                return "Sorry, my memory function broke."
                
                #Message Generation
            try:  
                ai_response = ollama.chat(model=self.ollama_ai_model, messages=[{'role': 'user', 'content': self.memory_input + ". You can feel free to use the before provided context to understand the situation and how you reply. Please take into consideration that" + self.context + input_text }])
                ai_response = ai_response['message']['content']
                memory_created = "User Input: " + input_text + ". "+ self.ollama_ai_model + " Response: " + ai_response
                
                #Save Memory
                if (self.saved_memory_texts) < self.memory_limit:
                    directory = "Memory/" + "mem" + str(self.saved_memory_texts + 1) + ".txt"
                    self.save_settings(directory, memory_created)
                    self.saved_memory_texts += 1
                    if self.current_saved_memories < self.memory_limit:
                        self.current_saved_memories += 1
                else:
                    self.saved_memory_texts = 0
                    directory = "Memory/" + "mem" + str(self.saved_memory_texts + 1) + ".txt"
                    self.save_settings(directory, memory_created)
                return ai_response
            except Exception as e:
                print(f"Error generating response: {e}")  # Debug print
                return "Sorry, I couldn't generate a response."
            
        else:
            # Old code (Session Based Memory) - Dumb System? Yes it is, using elifs is the dumbest way to do this, but it works at least :) - This will eventually be reviewed for optimization, but as the saying says, if it works, then don't fix it xD
            try:  
                #Send the modified input to Ollama's chat function and get the response                  
                #Memory Count - 0
                if self.memory_value == 0:
                    ai_response = ollama.chat(model=self.ollama_ai_model, messages=[{'role': 'user', 'content': self.context + input_text + "."}])
                    ai_response = ai_response['message']['content']                      
                    if self.memory_limit >= 1:
                        self.memory_value = 1
                        self.str1 = "User Input: " + input_text + ". "+ self.ollama_ai_model + " Response: " + ai_response
                #Memory Count - 1       
                elif self.memory_value == 1:
                    ai_response = ollama.chat(model=self.ollama_ai_model, messages=[{'role': 'user', 'content': "The following is the context of our current conversation: " + self.str1 + ". You can feel free to use the before provided context to understand the situation and how you reply. Please take into consideration that" + self.context + input_text }])
                    ai_response = ai_response['message']['content']
                    if self.memory_limit >= 2:
                        self.memory_value = 2
                        self.str2 = "User Input: " + input_text + ". "+ self.ollama_ai_model + " Response: " + ai_response       
                    else:
                        self.str1 = "User Input: " + input_text + ". "+ self.ollama_ai_model + " Response: " + ai_response
                #Memory Count - 2                              
                elif self.memory_value == 2:
                    ai_response = ollama.chat(model=self.ollama_ai_model, messages=[{'role': 'user', 'content': "The following is the context of our current conversation: " + self.str1 + self.str2 + ". You can feel free to use the before provided context to understand the situation and how you reply. Please take into consideration that" + self.context + input_text }])
                    ai_response = ai_response['message']['content']
                    if self.memory_limit >= 3:
                        self.memory_value = 3
                        self.str3 = "User Input: " + input_text + ". "+ self.ollama_ai_model + " Response: " + ai_response       
                    else:
                        self.str1 = self.str2
                        self.str2 = "User Input: " + input_text + ". "+ self.ollama_ai_model + " Response: " + ai_response
                #Memory Count - 3
                elif self.memory_value == 3:
                    ai_response = ollama.chat(model=self.ollama_ai_model, messages=[{'role': 'user', 'content': "The following is the context of our current conversation: " + self.str1 + self.str2 + self.str3 + ". You can feel free to use the before provided context to understand the situation and how you reply. Please take into consideration that" + self.context + input_text }])
                    ai_response = ai_response['message']['content']
                    if self.memory_limit >= 4:
                        self.memory_value = 4
                        self.str4 = "User Input: " + input_text + ". "+ self.ollama_ai_model + " Response: " + ai_response       
                    else:
                        self.str1 = self.str2
                        self.str2 = self.str3
                        self.str3 = "User Input: " + input_text + ". "+ self.ollama_ai_model + " Response: " + ai_response
                #Memory Count - 4
                elif self.memory_value == 4:
                    ai_response = ollama.chat(model=self.ollama_ai_model, messages=[{'role': 'user', 'content': "The following is the context of our current conversation: " + self.str1 + self.str2 + self.str3 + self.str4 + ". You can feel free to use the before provided context to understand the situation and how you reply. Please take into consideration that" + self.context + input_text }])
                    ai_response = ai_response['message']['content']
                    if self.memory_limit >= 5:
                        self.memory_value = 5
                        self.str5 = "User Input: " + input_text + ". "+ self.ollama_ai_model + " Response: " + ai_response       
                    else:
                        self.str1 = self.str2
                        self.str2 = self.str3
                        self.str3 = self.str4
                        self.str4 = "User Input: " + input_text + ". "+ self.ollama_ai_model + " Response: " + ai_response
                #Memory Count - 5
                elif self.memory_value == 5:
                    ai_response = ollama.chat(model=self.ollama_ai_model, messages=[{'role': 'user', 'content': "The following is the context of our current conversation: " + self.str1 + self.str2 + self.str3 + self.str4 + self.str5 + ". You can feel free to use the before provided context to understand the situation and how you reply. Please take into consideration that" + self.context + input_text }])
                    ai_response = ai_response['message']['content']
                    if self.memory_limit >= 6:
                        self.memory_value = 6
                        self.str6 = "User Input: " + input_text + ". "+ self.ollama_ai_model + " Response: " + ai_response       
                    else:
                        self.str1 = self.str2
                        self.str2 = self.str3
                        self.str3 = self.str4
                        self.str4 = self.str5
                        self.str5 = "User Input: " + input_text + ". "+ self.ollama_ai_model + " Response: " + ai_response
                #Memory Count - 6
                elif self.memory_value == 6:
                    ai_response = ollama.chat(model=self.ollama_ai_model, messages=[{'role': 'user', 'content': "The following is the context of our current conversation: " + self.str1 + self.str2 + self.str3 + self.str4 + self.str5 + self.str6 + ". You can feel free to use the before provided context to understand the situation and how you reply. Please take into consideration that" + self.context + input_text }])
                    ai_response = ai_response['message']['content']
                    if self.memory_limit >= 7:
                        self.memory_value = 7
                        self.str7 = "User Input: " + input_text + ". "+ self.ollama_ai_model + " Response: " + ai_response       
                    else:
                        self.str1 = self.str2
                        self.str2 = self.str3
                        self.str3 = self.str4
                        self.str4 = self.str5
                        self.str5 = self.str6
                        self.str6 = "User Input: " + input_text + ". "+ self.ollama_ai_model + " Response: " + ai_response
                #Memory Count - 7
                elif self.memory_value == 7:
                    ai_response = ollama.chat(model=self.ollama_ai_model, messages=[{'role': 'user', 'content': "The following is the context of our current conversation: " + self.str1 + self.str2 + self.str3 + self.str4 + self.str5 + self.str6 + self.str7 + ". You can feel free to use the before provided context to understand the situation and how you reply. Please take into consideration that" + self.context + input_text }])
                    ai_response = ai_response['message']['content']
                    if self.memory_limit >= 8:
                        self.memory_value = 8
                        self.str8 = "User Input: " + input_text + ". "+ self.ollama_ai_model + " Response: " + ai_response       
                    else:
                        self.str1 = self.str2
                        self.str2 = self.str3
                        self.str3 = self.str4
                        self.str4 = self.str5
                        self.str5 = self.str6
                        self.str6 = self.str7
                        self.str7 = "User Input: " + input_text + ". "+ self.ollama_ai_model + " Response: " + ai_response
                #Memory Count - 8
                elif self.memory_value == 8:
                    ai_response = ollama.chat(model=self.ollama_ai_model, messages=[{'role': 'user', 'content': "The following is the context of our current conversation: " + self.str1 + self.str2 + self.str3 + self.str4 + self.str5 + self.str6 + self.str7 + self.str8 + ". You can feel free to use the before provided context to understand the situation and how you reply. Please take into consideration that" + self.context + input_text }])
                    ai_response = ai_response['message']['content']
                    if self.memory_limit >= 9:
                        self.memory_value = 9
                        self.str9 = "User Input: " + input_text + ". "+ self.ollama_ai_model + " Response: " + ai_response       
                    else:
                        self.str1 = self.str2
                        self.str2 = self.str3
                        self.str3 = self.str4
                        self.str4 = self.str5
                        self.str5 = self.str6
                        self.str6 = self.str7
                        self.str7 = self.str8
                        self.str8 = "User Input: " + input_text + ". "+ self.ollama_ai_model + " Response: " + ai_response
                #Memory Count - 9
                elif self.memory_value == 9:
                    ai_response = ollama.chat(model=self.ollama_ai_model, messages=[{'role': 'user', 'content': "The following is the context of our current conversation: " + self.str1 + self.str2 + self.str3 + self.str4 + self.str5 + self.str6 + self.str7 + self.str8 + self.str9  + ". You can feel free to use the before provided context to understand the situation and how you reply. Please take into consideration that" + self.context + input_text }])
                    ai_response = ai_response['message']['content']
                    if self.memory_limit >= 10:
                        self.memory_value = 10
                        self.str10 = "User Input: " + input_text + ". "+ self.ollama_ai_model + " Response: " + ai_response       
                    else:
                        self.str1 = self.str2
                        self.str2 = self.str3
                        self.str3 = self.str4
                        self.str4 = self.str5
                        self.str5 = self.str6
                        self.str6 = self.str7
                        self.str7 = self.str8
                        self.str8 = self.str9
                        self.str9 = "User Input: " + input_text + ". "+ self.ollama_ai_model + " Response: " + ai_response
                #Memory Count - 10
                elif self.memory_value == 10:
                    ai_response = ollama.chat(model=self.ollama_ai_model, messages=[{'role': 'user', 'content': "The following is the context of our current conversation: " + self.str1 + self.str2 + self.str3 + self.str4 + self.str5 + self.str6 + self.str7 + self.str8 + self.str9 + self.str10 + ". You can feel free to use the before provided context to understand the situation and how you reply. Please take into consideration that" + self.context + input_text }])
                    ai_response = ai_response['message']['content']        
                    self.str1 = self.str2
                    self.str2 = self.str3
                    self.str3 = self.str4
                    self.str4 = self.str5
                    self.str5 = self.str6
                    self.str6 = self.str7
                    self.str7 = self.str8
                    self.str8 = self.str9
                    self.str9 = self.str10
                    self.str10 = "User Input: " + input_text + ". "+ self.ollama_ai_model + " Response: " + ai_response       
                return ai_response
            except Exception as e:
                print(f"Error generating response: {e}")  # Debug print
                return "Sorry, I couldn't generate a response."
            
    def play_audio(self, filename):
        data, fs = sf.read(filename, dtype='float32')
        # List available audio devices
        #print(sd.query_devices())
        # Set default device (change the device ID to the specific one you want)
        sd.play(data, fs, device=sd.default.device[1])
        sd.wait()  # Wait until the file is done playing
        
    async def speak_response(self, text, boot):
        try:
            # Replace asterisks with periods
            text = text.replace('*', '...')
            communicate = edge_tts.Communicate(text, voice=self.voice)
            mic_status = False
            #Start with Mic Off.
            if self.micboot != 0:
                mic_status = not self.is_mic_on
            
            await communicate.save("response.mp3")         

            # Disable buttons
            self.mic_button.config(state=tk.DISABLED)
            self.submit_button.config(state=tk.DISABLED)

            # Play sound using threading
            self.current_audio_thread = threading.Thread(target=self.play_audio, args=("response.mp3",))
            self.current_audio_thread.start()

            # Wait for audio playback to finish
            self.current_audio_thread.join()

            # Delete response.mp3 after playback
            os.remove("response.mp3")

            # Enable buttons and microphone if it was on after playback
            self.mic_button.config(state=tk.NORMAL)
            self.submit_button.config(state=tk.NORMAL)         
            if mic_status and self.auto_voice == "True":
                self.toggle_mic()

            if boot == 0:
                self.update_chat_log(f"Boot Up Complete\n")

                
        except Exception as e:
            print(f"Error during TTS: {e}")  # Debug print

    def open_settings_menu(self):
        settings_window = tk.Toplevel(self.master)
        settings_window.title("Settings")
        settings_window.geometry(f"590x555")  # Set the window size
        settings_window.resizable(False, False)

        # Set colors based on dark mode status
        if self.is_dark_mode:
            bg_color = "#000000"
            fg_color = "#FFFFFF"
            button_bg_color = "#4A4A4A"
            button_fg_color = "#FFFFFF"
        else:
            bg_color = "#F0F0F0"
            fg_color = "#000000"
            button_bg_color = "#D3D3D3"
            button_fg_color = "#000000"

        settings_window.config(bg=bg_color)
    
        #Audio Settings Label
        voice_label = tk.Label(settings_window, text="Audio Settings:", bg=bg_color, fg=fg_color)
        voice_label.grid(row=0, column=0, columnspan=4, padx=(5,0), pady=10)
        
        # Create a style for the combobox
        style = ttk.Style()
        style.configure("Dark.TCombobox", fieldbackground=bg_color, foreground=fg_color)
        
        #Input Device
        input_list = self.get_audio_input_list()
        selected_input = tk.StringVar(value=self.load_settings("settings/DefaultAudioInput.txt"))

        input_device_label = tk.Label(settings_window, text="Input Device:", bg=bg_color, fg=fg_color)
        input_device_label.grid(row=2, column=0, columnspan=2, sticky = "w", padx=(5,0), pady=5)
        
        input_device = ttk.Combobox(settings_window, textvariable=selected_input, values=input_list, state='readonly', width=45)
        input_device.grid(row=2, column=1, padx=(25,0), pady=5)
               
        input_device_confirm_button = tk.Button(settings_window, text="Confirm", command=lambda: self.change_input((selected_input.get() )), bg=button_bg_color, fg=button_fg_color)
        input_device_confirm_button.grid(row=2, column=2, ipadx=10, padx=5, pady=5)
        
        input_device_make_default_button = tk.Button(settings_window, text="Make Default", command=lambda: self.change_default_input(selected_input.get()), bg=button_bg_color, fg=button_fg_color)
        input_device_make_default_button.grid(row=2, column=3, ipadx=10, padx=5, pady=5)
        
        #Output Device
        output_list = self.get_audio_output_list()
        selected_output = tk.StringVar(value=self.load_settings("settings/DefaultAudioOutput.txt").replace(", Windows DirectSound", ""))
        
        output_device_label = tk.Label(settings_window, text="Output Device:", bg=bg_color, fg=fg_color)
        output_device_label.grid(row=3, column=0, columnspan=2, sticky = "w", padx=(5,0), pady=5)
        
        output_device = ttk.Combobox(settings_window, textvariable=selected_output, values=output_list, state='readonly', width=45)
        output_device.grid(row=3, column=1, padx=(25,0), pady=5)
               
        output_device_confirm_button = tk.Button(settings_window, text="Confirm", command=lambda: self.change_output((selected_output.get() )), bg=button_bg_color, fg=button_fg_color)
        output_device_confirm_button.grid(row=3, column=2, ipadx=10, padx=5, pady=5)
        
        output_device_make_default_button = tk.Button(settings_window, text="Make Default", command=lambda: self.change_default_output(selected_output.get()), bg=button_bg_color, fg=button_fg_color)
        output_device_make_default_button.grid(row=3, column=3, ipadx=10, padx=5, pady=5)
        
        #Automatic Microphone Turn On after AI Response - Prone to crashes
        AutoMic_Status = [ "True", "False"]
        AutoMic_Selected_Status = tk.StringVar(value=self.load_settings("settings/AutoVoice.txt"))
        
        auto_voice_label = tk.Label(settings_window, text="Auto-Voice Enabling (Can cause Crashes):", bg=bg_color, fg=fg_color)
        auto_voice_label.grid(row=4, column=0, columnspan=2, sticky = "w", padx=(5,0), pady=5)
        
        auto_voice = ttk.Combobox(settings_window, textvariable=AutoMic_Selected_Status, values=AutoMic_Status, state='readonly', width=21)
        auto_voice.grid(row=4, column=1, padx=(168,0), pady=5)
               
        auto_voice_confirm_button = tk.Button(settings_window, text="Confirm", command=lambda: self.change_microphone_activation(AutoMic_Selected_Status.get()), bg=button_bg_color, fg=button_fg_color)
        auto_voice_confirm_button.grid(row=4, column=2, ipadx=10, padx=5, pady=5)
        
        auto_voice_make_default_button = tk.Button(settings_window, text="Make Default", command=lambda: self.save_microphone_activation("settings/AutoVoice.txt", AutoMic_Selected_Status.get()), bg=button_bg_color, fg=button_fg_color)
        auto_voice_make_default_button.grid(row=4, column=3, ipadx=10, padx=5, pady=5)
        
        #AI Settings Label
        ai_label = tk.Label(settings_window, text="AI Settings:", bg=bg_color, fg=fg_color)
        ai_label.grid(row=5, column=0, columnspan=4, padx=(5,0), pady=10)
        
        #AI Reader
        voices = [
            "en-AU-NatashaNeural", "en-AU-WilliamNeural", "en-CA-ClaraNeural", "en-CA-LiamNeural",
            "en-GB-LibbyNeural", "en-GB-RyanNeural", "en-IE-EmilyNeural", "en-IE-ConnorNeural", 
            "en-US-JennyNeural", "en-US-AriaNeural"
        ]

        selected_voice = tk.StringVar(value=self.voice)
        
        ai_reader_label = tk.Label(settings_window, text="AI Reader:", bg=bg_color, fg=fg_color)
        ai_reader_label.grid(row=6, column=0, sticky = "w", padx=(5,0), pady=5)
        
        ai_reader = ttk.Combobox(settings_window, textvariable=selected_voice, values=voices, state='readonly', width=49)
        ai_reader.grid(row=6, column=1, padx=5, pady=5)
               
        ai_reader_confirm_button = tk.Button(settings_window, text="Confirm", command=lambda: self.change_voice(selected_voice.get()), bg=button_bg_color, fg=button_fg_color)
        ai_reader_confirm_button.grid(row=6, column=2, ipadx=10, padx=5, pady=5)
        
        ai_reader_make_default_button = tk.Button(settings_window, text="Make Default", command=lambda: self.change_default_voice(selected_voice.get()), bg=button_bg_color, fg=button_fg_color)
        ai_reader_make_default_button.grid(row=6, column=3, ipadx=10, padx=5, pady=5)
        
        #AI Model
        written_model = tk.StringVar(value=self.ollama_ai_model)
        
        ai_model = tk.Label(settings_window, text="AI Model:", bg=bg_color, fg=fg_color)
        ai_model.grid(row=7, column=0, sticky = "w", padx=(5,0), pady=10)
        
        ai_model_input = tk.Entry(settings_window, textvariable=written_model, width=52)
        ai_model_input.grid(row=7, column=1, padx=(0,1), pady=10)
        
        ai_model_confirm_button = tk.Button(settings_window, text="Confirm", command=lambda: self.change_model(written_model.get()), bg=button_bg_color, fg=button_fg_color)
        ai_model_confirm_button.grid(row=7, column=2, ipadx=10, padx=5, pady=5)
        
        ai_model_make_default_button = tk.Button(settings_window, text="Make Default", command=lambda: self.change_default_model(written_model.get()), bg=button_bg_color, fg=button_fg_color)
        ai_model_make_default_button.grid(row=7, column=3, ipadx=10, padx=5, pady=5)
        
        #Restoration of Base Context
        confirmation_base_restore = tk.StringVar(value="")
        
        restore_context = tk.Label(settings_window, text="Restore Base Context (Write Confirm):", bg=bg_color, fg=fg_color)
        restore_context.grid(row=8, column=0, columnspan=2, sticky = "w", padx=(5,0), pady=10)
        
        restore_context_input = tk.Entry(settings_window,textvariable=confirmation_base_restore, width=42)
        restore_context_input.grid(row=8, column=1, columnspan=2, padx=(144,0), pady=10)
        
        restore_context_button = tk.Button(settings_window, text="Restore", command=lambda: self.restore_base_context(confirmation_base_restore.get()), bg=button_bg_color, fg=button_fg_color)
        restore_context_button.grid(row=8, column=3, ipadx=25, padx=5, pady=5)
        
        #Memory Specific Settings Label
        memory_settings = tk.Label(settings_window, text="Memory Specific Settings:", bg=bg_color, fg=fg_color)
        memory_settings.grid(row=9, column=0, columnspan=4, padx=(5,0), pady=10)
        
        #Session Only Memory
        Session_Memory_Status = [ "True", "False" ]
        Session_Memory_Selected_Status = tk.StringVar(value=self.load_settings("settings/SessionMemory.txt"))
        
        Session_only_memory = tk.Label(settings_window, text="Session Only Memory (10 Messages limit):", bg=bg_color, fg=fg_color)
        Session_only_memory.grid(row=10, column=0, columnspan=4, sticky = "w", padx=(5,0), pady=10)
        
        session_memory = ttk.Combobox(settings_window, textvariable=Session_Memory_Selected_Status, values=Session_Memory_Status, state='readonly', width=21)
        session_memory.grid(row=10, column=1, padx=(168,0), pady=5)
              
        session_memory_confirm_button = tk.Button(settings_window, text="Confirm", command=lambda: self.session_based_memory_toggle(Session_Memory_Selected_Status.get()), bg=button_bg_color, fg=button_fg_color)
        session_memory_confirm_button.grid(row=10, column=2, ipadx=10, padx=5, pady=5)
        
        session_memory_make_default_button = tk.Button(settings_window, text="Make Default", command=lambda: self.session_based_memory_toggle_default("settings/SessionMemory.txt", Session_Memory_Selected_Status.get()), bg=button_bg_color, fg=button_fg_color)
        session_memory_make_default_button.grid(row=10, column=3, ipadx=10, padx=5, pady=5)
        
        #Memory Limit
        current_memory_limit = tk.StringVar(value=self.load_settings("settings/MemoryLimit.txt"))
        
        memory_limits = tk.Label(settings_window, text="Memory Limit (Recomended Below 100):", bg=bg_color, fg=fg_color)
        memory_limits.grid(row=11, column=0, columnspan=2, sticky = "w", padx=(5,0), pady=10)
        
        memory_limit_input = tk.Entry(settings_window,textvariable=current_memory_limit, width=39)
        memory_limit_input.grid(row=11, column=1, columnspan=2, padx=(160,0), pady=10)
        
        memory_limit_button = tk.Button(settings_window, text="Update", command=lambda: self.update_memory_limit("settings/MemoryLimit.txt", current_memory_limit.get()), bg=button_bg_color, fg=button_fg_color)
        memory_limit_button.grid(row=11, column=3, ipadx=26, padx=5, pady=5)
        
        #Memory Reset/Clear
        memory_clear = tk.StringVar(value="")
        
        memory_reset = tk.Label(settings_window, text="Clear All Saved Memories (Write Confirm):", bg=bg_color, fg=fg_color)
        memory_reset.grid(row=12, column=0, columnspan=4, sticky = "w", padx=(5,0), pady=10)
        
        memory_reset_input = tk.Entry(settings_window,textvariable=memory_clear, width=38)
        memory_reset_input.grid(row=12, column=1, columnspan=2, padx=(166,0), pady=10)
        
        memory_reset_button = tk.Button(settings_window, text="Clear Memory", command=lambda: self.clear_memories("Memory", memory_clear.get()), bg=button_bg_color, fg=button_fg_color)
        memory_reset_button.grid(row=12, column=3, ipadx=7, padx=5, pady=5)
        
        #Visual Settings Label
        visual_settings = tk.Label(settings_window, text="Visual Settings:", bg=bg_color, fg=fg_color)
        visual_settings.grid(row=13, column=0, columnspan=4, padx=(5,0), pady=10)
        
        #Boot Up in Dark Mode
        DarkMode_Boot_Label = tk.Label(settings_window, text="Boot up in Dark Mode:", bg=bg_color, fg=fg_color)
        DarkMode_Boot_Label.grid(row=14, column=0, columnspan=4, sticky = "w", padx=(5,0), pady=10)
        
        DarkMode_Boot = [ "True", "False" ]
        DarkMode_Boot_Status = tk.StringVar(value=self.load_settings("settings/darkmodestate.txt"))
        
        DarkMode_Boot_Box = ttk.Combobox(settings_window, textvariable=DarkMode_Boot_Status, values=DarkMode_Boot, state='readonly', width=52)
        DarkMode_Boot_Box.grid(row=14, column=1, columnspan=2, padx=(63,0), pady=5)
        
        DarkMode_make_default_button = tk.Button(settings_window, text="Make Default", command=lambda: self.save_settings("settings/darkmodestate.txt", DarkMode_Boot_Status.get()), bg=button_bg_color, fg=button_fg_color)
        DarkMode_make_default_button.grid(row=14, column=3, ipadx=10, padx=5, pady=5)
        
    def clear_memories(self, directory_path, confirmation):
        if confirmation == "Confirm":
            self.current_saved_memory_limit = False
            self.memory_refresher = 0
            self.memory_value = 0
            self.saved_memory_texts = 0
            self.current_saved_memories = 0
            self.str1 = ""
            self.str2 = ""
            self.str3 = ""
            self.str4 = ""
            self.str5 = ""
            self.str6 = ""
            self.str7 = ""
            self.str8 = ""
            self.str9 = ""
            self.str10 = ""
            try:
                files = os.listdir(directory_path)
                for file in files:
                    file_path = os.path.join(directory_path, file)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                print("All files deleted successfully.")
            except OSError:
                print("Error occurred while deleting files.")
            
    def change_voice(self, new_voice):
        self.voice = new_voice
            
    def change_default_voice(self, new_voice):
        self.change_voice(new_voice)
        with open("settings/SpeechReader.txt", "w") as file:
            file.write(new_voice)

    def change_microphone_activation (self, new_value):
        try:
            self.auto_voice = new_value
        except Exception as e:
            print(f"Error changing variable: {e}")
            
    def save_microphone_activation (self, directory, new_value):        
        self.change_microphone_activation(new_value)
        self.save_settings(directory, new_value)

    def update_memory_limit (self, directory, new_value):        
        self.memory_limit = int(new_value)
        self.current_saved_memory_limit = False
        if self.memory_value > int(new_value):
            self.memory_value = int(new_value)
        self.save_settings(directory, new_value)
                
    def session_based_memory_toggle (self, new_value):
        try:
            self.session_based_memory = new_value
        except Exception as e:
            print(f"Error changing variable: {e}")
            
    def session_based_memory_toggle_default (self, directory, new_value):        
            self.session_based_memory_toggle(new_value)
            self.save_settings(directory, new_value)

    def toggle_dark_mode(self):
        self.is_dark_mode = not self.is_dark_mode
        if self.is_dark_mode:
            self.master.config(bg="black")
            self.frame.config(bg="black")
            self.manual_input_label.config(bg="black", fg="white")
            self.manual_input.config(bg="black", fg="white", insertbackground="white")
            self.submit_button.config(bg="#4A4A4A", fg="#FFFFFF")
            self.chat_log_label.config(bg="black", fg="white")
            self.chat_log.config(bg="black", fg="white")
            self.clear_button.config(bg="#4A4A4A", fg="#FFFFFF")
            self.voice_button.config(bg="#4A4A4A", fg="#FFFFFF")
            self.processing_indicator.config(bg="black")
            self.open_context_manager_button.config(bg="#4A4A4A", fg="#FFFFFF")
            self.open_audio_manager_button.config(bg="#4A4A4A", fg="#FFFFFF")
            self.mic_button.config(bg="#4A4A4A", fg="#FFFFFF")
            self.toggle_dark_mode_button.config(bg="#4A4A4A", fg="#FFFFFF")
        else:
            self.master.config(bg="SystemButtonFace")
            self.frame.config(bg="SystemButtonFace")
            self.manual_input_label.config(bg="SystemButtonFace", fg="black")
            self.manual_input.config(bg="SystemButtonFace", fg="black", insertbackground="black")
            self.submit_button.config(bg="SystemButtonFace", fg="black")
            self.chat_log_label.config(bg="SystemButtonFace", fg="black")
            self.chat_log.config(bg="white", fg="black")
            self.clear_button.config(bg="SystemButtonFace", fg="black")
            self.voice_button.config(bg="SystemButtonFace", fg="black")
            self.processing_indicator.config(bg="SystemButtonFace")
            self.open_context_manager_button.config(bg="SystemButtonFace", fg="black")
            self.open_audio_manager_button.config(bg="SystemButtonFace", fg="black")
            self.mic_button.config(bg="SystemButtonFace", fg="black")
            self.toggle_dark_mode_button.config(bg="SystemButtonFace", fg="black")

    def on_resize(self, event):
        self.update_scroll_region()

    def update_scroll_region(self):
        self.frame.update_idletasks()
        self.chat_log.config(scrollregion=self.chat_log.bbox(tk.END))

    def open_context_manager(self):
        self.context_manager_window = tk.Toplevel(self.master)
        self.context_manager_window.title("Context Manager")
        self.context_manager_window.geometry("400x300")
        self.context_manager_window.wm_minsize(400, 300)

        # Set background colors based on dark mode status
        if self.is_dark_mode:
            bg_color = "#000000"
            fg_color = "#FFFFFF"
            text_bg_color = "#1C1C1C"
            text_fg_color = "#FFFFFF"
            button_bg_color = "#4A4A4A"
            button_fg_color = "#FFFFFF"
        else:
            bg_color = "#F0F0F0"
            fg_color = "#000000"
            text_bg_color = "#FFFFFF"
            text_fg_color = "#000000"            
            button_bg_color = "#D3D3D3"
            button_fg_color = "#000000"

        self.context_manager_window.config(bg=bg_color)

        # Current Context Display
        current_context_label = tk.Label(self.context_manager_window, text="Current Context:", bg=bg_color, fg=fg_color)
        current_context_label.pack(pady=5)
        
        self.load_context()
        self.current_context_display = tk.Text(self.context_manager_window, wrap=tk.WORD, width=50, height=10)
        self.current_context_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.current_context_display.insert(tk.END, self.context)
        
        # Apply dark mode style to text box
        self.current_context_display.config(bg=text_bg_color, fg=text_fg_color, insertbackground="#000000")

        # Update Context Button
        update_context_button = tk.Button(self.context_manager_window, text="Update Context", command=self.save_new_context, bg=button_bg_color, fg=button_fg_color)
        update_context_button.pack(pady=5)

    def open_audio_manager(self):
        open_audio_manager = tk.Toplevel(self.master)
        open_audio_manager.title("Addon Manager")
        open_audio_manager.geometry(f"215x35")  # Set the window size
        open_audio_manager.resizable(False, False)
        
        # Set background colors based on dark mode status
        if self.is_dark_mode:
            bg_color = "#000000"
            fg_color = "#FFFFFF"
            text_bg_color = "#1C1C1C"
            text_fg_color = "#FFFFFF"
            button_bg_color = "#4A4A4A"
            button_fg_color = "#FFFFFF"
        else:
            bg_color = "#F0F0F0"
            fg_color = "#000000"
            text_bg_color = "#FFFFFF"
            text_fg_color = "#000000"            
            button_bg_color = "#D3D3D3"
            button_fg_color = "#000000"

        open_audio_manager.config(bg=bg_color)
        
        # Label Saying None Exist at this time Addons Menu Display
        current_context_label = tk.Label(open_audio_manager, text="No Available Addons at this time", bg=bg_color, fg=fg_color)
        current_context_label.grid(row=0, column=0, padx=20, pady=5)
        
    def get_audio_output_list(self):
        # Function to query audio devices and return a filtered list of device names
        devices = sd.query_devices()
        
        def is_balanced_parentheses(name):
            # Helper function to check if parentheses are balanced in the device name
            open_paren_count = name.count('(')
            close_paren_count = name.count(')')
            return open_paren_count == close_paren_count
        
        filtered_devices = []
        
        for device in devices:
            device_name = device['name'][:150]  # Limiting to 150 characters
            if device['max_output_channels'] > 0 and is_balanced_parentheses(device_name):
                filtered_devices.append(device_name)
        
        return filtered_devices
    
    def get_audio_input_list(self):
        # Function to query audio devices and return a filtered list of device names
        devices = sd.query_devices()
        
        def is_balanced_parentheses(name):
            # Helper function to check if parentheses are balanced in the device name
            open_paren_count = name.count('(')
            close_paren_count = name.count(')')
            return open_paren_count == close_paren_count
        
        filtered_devices = []
        
        for device in devices:
            device_name = device['name'][:150]  # Limiting to 150 characters
            if device['max_input_channels'] > 0 and is_balanced_parentheses(device_name):
                filtered_devices.append(device_name)
        
        return filtered_devices

    def change_input(self, selected_device):
        try:
            sd.default.device[0] = selected_device
            self.mic = sr.Microphone(device_index = self.get_device_index_by_name(sd.default.device[0]))
            #print(f"Audio output changed to: {sd.default.device[0]}") #Troubleshooting Audio print
        except Exception as e:
            print(f"Error changing audio output: {e}")      

    def change_default_input(self, new_audio_input):
        self.change_input(new_audio_input)
        with open("settings/DefaultAudioInput.txt", "w") as file:
            file.write(new_audio_input) 

    def change_model(self, selected_model):
        try:
            self.ollama_ai_model = selected_model
        except Exception as e:
            print(f"Error changing ai model output: {e}")      

    def change_default_model(self, selected_model):
        self.change_model(selected_model)
        with open("settings/OllamaAiModel.txt", "w") as file:
            file.write(selected_model) 

    def restore_base_context(self, text_confirmation):
        backup_context = self.load_settings("Backup/ContextBackup.txt")
        if text_confirmation == "Confirm":
            with open("settings/context.txt", "w") as file:
                file.write(backup_context)
            
    def change_output(self, selected_device):
        try:
            sd.default.device[1] = selected_device + ', Windows DirectSound'
            #print(f"Audio output changed to: {sd.default.device[1]}") #Troubleshooting Audio print
        except Exception as e:
            print(f"Error changing audio output: {e}")      

    def change_default_output(self, new_audio_output):
        self.change_output(new_audio_output)
        with open("settings/DefaultAudioOutput.txt", "w") as file:
            file.write(new_audio_output + ", Windows DirectSound") 
    
    def get_device_index_by_name(self, device_name):
        devices = sd.query_devices()
        for idx, device in enumerate(devices):
            if device['name'] == device_name:
                return idx
        return None
    
    def save_new_context(self):
        self.context = self.current_context_display.get(1.0, tk.END).strip()
        self.save_context()  # Assuming save_context() is a method that saves the context elsewhere
        self.context_manager_window.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    instance_id = uuid.uuid4()
    ai_local_interface = AILocalInterface(root, instance_id)
    root.mainloop()
