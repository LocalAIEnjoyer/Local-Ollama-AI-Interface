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
        master.geometry("250x500")  # Set the initial size of the window
        master.minsize(250, 500)  # Set the minimum size of the window
        
        # Settings folder BootUp
        self.context_file = "settings/context.txt"
        self.load_context()
        self.voice = self.load_settings("settings/SpeechReader.txt")
        sd.default.device = self.load_settings("settings/DefaultAudioOutput.txt")  # or use the device ID
        self.memory_limit = int(self.load_settings("settings/MemoryLimit.txt"))
        
        #Memory Variables
        self.current_saved_memory_limit = False       #Used to find how many "Memories" exist - Boolean
        self.saved_memory_texts = 0                   #Used to count the number of "Memories" and to replace the older ones - Integer
        self.current_saved_memories = 0
        
        #Memory Message Variable - Used to store the prompt designed for the AI to not focus on the "past"
        self.memory_input = " "
        
        # Turn off the Microphone for Boot and Start Voice Recognizer
        self.is_mic_on = False
        self.micboot = 0
        self.mic = sr.Microphone()
        self.recognizer = sr.Recognizer()

        # Create a frame for better layout management
        self.frame = tk.Frame(master, padx=15, pady=15)
        self.frame.pack(fill=tk.BOTH, expand=True)

        # Toggle Dark Mode Button
        self.toggle_dark_mode_button = tk.Button(self.frame, text="D", command=self.toggle_dark_mode, width=1, height=1)
        self.toggle_dark_mode_button.grid(row=0, column=0, sticky='e', padx=(0, 1), pady=(0, 5))
        
        # Microphone Button
        self.mic_button = tk.Button(self.frame, text="Turn Mic On", command=self.toggle_mic)
        self.mic_button.grid(row=0, column=0, sticky='ew', padx=(0, 18), pady=(0, 5))

        # Manual Input Box
        self.manual_input_label = tk.Label(self.frame, text="Manual Input:")
        self.manual_input_label.grid(row=1, column=0, sticky='w', pady=(0, 5))

        self.manual_input = tk.Entry(self.frame)
        self.manual_input.grid(row=2, column=0, sticky='ew', pady=(0, 5))

        self.submit_button = tk.Button(self.frame, text="Submit", command=self.submit_text)
        self.submit_button.grid(row=3, column=0, sticky='ew', pady=(0, 15))

        # Chat Log
        self.chat_log_label = tk.Label(self.frame, text="Chat Log:")
        self.chat_log_label.grid(row=4, column=0, sticky='w', pady=(0, 5))

        self.chat_log = scrolledtext.ScrolledText(self.frame, wrap=tk.WORD)
        self.chat_log.grid(row=5, column=0, sticky='nsew')

        # Clear Button
        self.clear_button = tk.Button(self.frame, text="Clear Chat Log", command=self.clear_chat_log)
        self.clear_button.grid(row=6, column=0, sticky='ew', pady=(5, 5))

        # Voice Selection Button
        self.voice_button = tk.Button(self.frame, text="Select Voice", command=self.open_voice_selection)
        self.voice_button.grid(row=7, column=0, sticky='ew', pady=(0, 5))

        # Open Context Manager Window Button
        self.open_context_manager_button = tk.Button(self.frame, text="Manage Context", command=self.open_context_manager)
        self.open_context_manager_button.grid(row=8, column=0, sticky='ew', pady=(0, 5))

        # Open Context Audio Window Button
        self.open_audio_manager_button = tk.Button(self.frame, text="Manage Audio Output", command=self.open_audio_manager)
        self.open_audio_manager_button.grid(row=9, column=0, sticky='ew', pady=(0, 5))

        # Processing Indicator
        self.processing_indicator = tk.Label(self.frame, text="Processing: Off", fg="red")
        self.processing_indicator.grid(row=10, column=0, sticky='ew', pady=(5, 0))

        # Configure grid weights
        self.frame.grid_columnconfigure(0, weight=1)
        self.frame.grid_rowconfigure(5, weight=1)
        
        #DarkMode BootUp
        if self.load_settings("settings/darkmodestate.txt") == 'True':
            #print(self.load_settings("settings/darkmodestate.txt")) # Test if condition was working.
            self.is_dark_mode = False
            self.toggle_dark_mode()            
        else:
            self.is_dark_mode = True
            
        # Initialize window variables
        self.voice_selection_window = None
        self.context_manager_window = None

        # Bind the configure event to the resizing function
        self.master.bind('<Configure>', self.on_resize)
        
        # Memory Module (Dumb system with 1 integer and 1 strings) OLD SYSTEM
        #self.memory_value = 0
        #self.str1 = ""     
        
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
        #Variable Setup (Memory Input + Memory Count + Current Limit)
        directory = "Memory/"
        self.memory_refresher = 0
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
                    self.memory_input = "Please be aware that the following messages have been our current conversation and that you can use part of it to help form your response, but please focus on replying to the question that's before this sentence and is within quotations marks: " + self.load_settings(current_location)
                else:
                    self.memory_input = self.memory_input + self.load_settings(current_location)
        
        except Exception as e:
            print(f"Error generating response: {e}")  # Debug print
            return "Sorry, my memory function broke."
            
            #Message Generation
        try:  
            ai_response = ollama.chat(model='llama3', messages=[{'role': 'user', 'content': self.context + '"' + input_text + '"' + "." + self.memory_input}])
            ai_response = ai_response['message']['content']
            memory_created = "User Input: " + input_text + ". Llama3 Response: " + ai_response
            
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
            
            # Old code (Single Inquiry Session Based Memory) - Here for troubleshooting + If meant to be added in the future as a feature.
        #try:  
            # Send the modified input to Ollama's chat function and get the response
        #    if self.memory_value == 0:
        #        ai_response = ollama.chat(model='llama3', messages=[{'role': 'user', 'content': self.context + input_text + "."}])
        #        ai_response = ai_response['message']['content']
        #        self.memory_value = 1
        #    else:
        #        ai_response = ollama.chat(model='llama3', messages=[{'role': 'user', 'content': self.context + "'" + input_text + ".'" + "Please also take into consideration that the following has been our current conversation, but do not focus your attention on it, unless specifically asked about it: " + self.str1 }])
        #        ai_response = ai_response['message']['content']         
        #    self.str1 = "User Input: " + input_text + "Llama3 Response:" + ai_response + "."
        #    return ai_response
        #except Exception as e:
        #    print(f"Error generating response: {e}")  # Debug print
        #    return "Sorry, I couldn't generate a response."
            
        except Exception as e:
            print(f"Error generating response: {e}")  # Debug print
            return "Sorry, I couldn't generate a response."
        
    def play_audio(self, filename):
        data, fs = sf.read(filename, dtype='float32')
        # List available audio devices
        #print(sd.query_devices())
        # Set default device (change the device ID to the specific one you want)
        sd.play(data, fs)
        sd.wait()  # Wait until the file is done playing
        
    async def speak_response(self, text, boot):
        try:
            # Replace asterisks with periods
            text = text.replace('*', '...')
            communicate = edge_tts.Communicate(text, voice=self.voice)
            
            #Start with Mic Off.
            if self.micboot == 0:
                self.micboot = 1
            else:
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
            if mic_status:
                self.toggle_mic()

            if boot == 0:
                self.update_chat_log(f"Boot Up Complete\n")

                
        except Exception as e:
            print(f"Error during TTS: {e}")  # Debug print

    def open_voice_selection(self):
        voice_selection_window = tk.Toplevel(self.master)
        voice_selection_window.title("Select Voice")
        window_width = 240  # Adjust the width as per your preference
        voice_selection_window.geometry(f"{window_width}x115")  # Set the window size
        voice_selection_window.resizable(False, False)

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

        voice_selection_window.config(bg=bg_color)

        voices = [
            "en-AU-NatashaNeural", "en-AU-WilliamNeural", "en-CA-ClaraNeural", "en-CA-LiamNeural",
            "en-GB-LibbyNeural", "en-GB-RyanNeural", "en-IE-EmilyNeural", "en-IE-ConnorNeural", 
            "en-US-JennyNeural", "en-US-AriaNeural"
        ]

        selected_voice = tk.StringVar(value=self.voice)

        voice_label = tk.Label(voice_selection_window, text="Select Voice:", bg=bg_color, fg=fg_color)
        voice_label.grid(row=0, column=0,pady=10)
        
        # Create a style for the combobox
        style = ttk.Style()
        style.configure("Dark.TCombobox", fieldbackground=bg_color, foreground=fg_color)
        
        voice_dropdown = ttk.Combobox(voice_selection_window, textvariable=selected_voice, values=voices, state='readonly', width=30)
        voice_dropdown.grid(row=1, column=0, padx=20, pady=5)
               
        confirm_button = tk.Button(voice_selection_window, text="Confirm", command=lambda: self.change_voice(selected_voice.get(), voice_selection_window), bg=button_bg_color, fg=button_fg_color)
        confirm_button.grid(row=2, column=0, ipadx=10, padx=(0, 128), pady=5)
        
        make_default_button = tk.Button(voice_selection_window, text="Make Default", command=lambda: self.change_default_voice(selected_voice.get(), voice_selection_window), bg=button_bg_color, fg=button_fg_color)
        make_default_button.grid(row=2, column=0, ipadx=10, padx=(104, 0), pady=5)
        
    def change_voice(self, new_voice, voice_selection_window):
        self.voice = new_voice
        voice_selection_window.destroy()
    
    def change_default_voice(self, new_voice, voice_selection_window):
        with open("settings/SpeechReader.txt", "w") as file:
            file.write(new_voice)
        voice_selection_window.destroy()

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
        open_audio_manager.title("Audio Manager")
        window_width = 500  # Adjust the width as per your preference
        open_audio_manager.geometry(f"{window_width}x115")  # Set the window size
        open_audio_manager.resizable(False, False)
        open_audio_manager.wm_minsize(500, 115)
        
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
        
        # Current Context Display
        current_context_label = tk.Label(open_audio_manager, text="Select Audio Output", bg=bg_color, fg=fg_color)
        current_context_label.grid(row=0, column=0, padx=20, pady=5)
        
        device_list = self.get_audio_output_list()
        selected_output = tk.StringVar(value=self.load_settings("settings/DefaultAudioOutput.txt"))
        # Create a style for the combobox
        style = ttk.Style()
        style.configure("Dark.TCombobox", fieldbackground=bg_color, foreground=fg_color)
        
        audio_dropdown = ttk.Combobox(open_audio_manager, textvariable=selected_output, values=device_list, state='readonly', width = int(window_width/6.66) )
        audio_dropdown.grid(row=1, column=0, padx=13, pady=0)
        
        open_audio_manager.audio_dropdown = audio_dropdown

        confirm_button = tk.Button(open_audio_manager, text="Update Output", command=lambda: self.change_output(selected_output.get(), open_audio_manager), bg=button_bg_color, fg=button_fg_color)
        confirm_button.grid(row=2, column=0,ipadx=15, padx=(0,16), pady=10)
        
        current_audio_button = tk.Button(open_audio_manager, text=" Current Audio Source", command=lambda: open_audio_manager.audio_dropdown.set(str(sd.default.device[0])), bg=button_bg_color, fg=button_fg_color)
        current_audio_button.grid(row=2, column=0,ipadx=15, padx=(0,314), pady=10)
        
        default_output_button = tk.Button(open_audio_manager, text="Choose as Default Output", command=lambda: self.change_default_output(selected_output.get(), open_audio_manager), bg=button_bg_color, fg=button_fg_color)
        default_output_button.grid(row=2, column=0, ipadx=15, padx=(298,0), pady=10)
        
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
        
    def change_output(self, selected_device,audio_manager_window):
        try:
            sd.default.device = selected_device + ', Windows DirectSound'
            #print(f"Audio output changed to: {sd.default.device}") #Troubleshooting Audio print
        except Exception as e:
            print(f"Error changing audio output: {e}")  
        audio_manager_window.destroy()    

    def change_default_output(self, new_audio_output, audio_manager_window):
        with open("settings/DefaultAudioOutput.txt", "w") as file:
            file.write(new_audio_output + ", Windows DirectSound")
        audio_manager_window.destroy()    
    
    def save_new_context(self):
        self.context = self.current_context_display.get(1.0, tk.END).strip()
        self.save_context()  # Assuming save_context() is a method that saves the context elsewhere
        self.context_manager_window.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    instance_id = uuid.uuid4()
    ai_local_interface = AILocalInterface(root, instance_id)
    root.mainloop()
