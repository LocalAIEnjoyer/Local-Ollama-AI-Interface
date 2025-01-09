import tkinter as tk
from tkinter import scrolledtext, ttk, font
from datetime import datetime, timedelta
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
import pyvts
import re
import random
import discord
from discord.ext import commands

#VtubeStudioPlugin Details.
plugin_info = {
        "plugin_name": "pyvts",
        "developer": "Architeture (Genteki) + Implementation on code (Mark)",
        "authentication_token_path": "./token.txt"
        }
        
vts_api_info = {
    "host": "localhost",
    "name": "VTubeStudioPublicAPI",
    "port": 8001,
    "version": "1.0"
}

#Discord Plugin Details. Needs to be manually updated in the code. - To set it up, please create a discord bot, then replace the Bot Token and Channel ID with your bot token + Channel ID. Make sure the bot token is within ""
BOT_TOKEN = "1"
CHANNEL_ID = 1

bot = commands.Bot(command_prefix='-', intents=discord.Intents.all())

#Test Global Variable
class ToolTip:
    def __init__(self, widget, text, darkmode):
        self.widget = widget
        self.text = text
        self.tooltip = None
        self.darkmode = darkmode
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event):
        if not self.tooltip:
            self.tooltip = tk.Toplevel(self.widget)
            self.tooltip.wm_overrideredirect(True)  # Remove window decorations
            x, y, _, _ = self.widget.bbox("insert")
            x += self.widget.winfo_rootx() + 10
            y += self.widget.winfo_rooty() + 10
            self.tooltip.geometry(f"+{x}+{y}")
            if self.darkmode:
                label = tk.Label(self.tooltip, text=self.text, bg="#000000", fg="#FFFFFF", relief="solid", borderwidth=1, font=("Arial", 10), justify="left")
            else:
                label = tk.Label(self.tooltip, text=self.text, bg="#F0F0F0", fg="#000000", relief="solid", borderwidth=1, font=("Arial", 10), justify="left")
            label.pack()

    def hide_tooltip(self, event):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None
            
class AILocalInterface:
    def __init__(self, master, instance_id, plugin_info, vts_api_info):
        #Setup the master instance/UI
        self.master = master
        self.instance_id = instance_id
        master.title("AI Interface")
        master.geometry("300x500")  # Set the initial size of the window
        master.minsize(300, 500)  # Set the minimum size of the window
        
        # Settings folder BootUp
        self.context_file = "Settings/context.txt"
        self.load_context()
        self.session_based_memory = self.load_settings("Settings/SessionMemory.txt")
        self.voice = self.load_settings("Settings/SpeechReader.txt")
        sd.default.device = (self.load_settings("Settings/DefaultAudioInput.txt"), self.load_settings("Settings/DefaultAudioOutput.txt"))
        self.memory_limit = int(self.load_settings("Settings/MemoryLimit.txt"))
        self.ollama_ai_model = self.load_settings("Settings/OllamaAiModel.txt")
        
        #Addon Related Settings/Variables
        self.vtube_enabled = tk.IntVar()
        self.vtube_correction_value = tk.IntVar()
        if self.load_settings("AddonSettings\VtubeStudio\VtubeStudio.txt") == "True":
            self.vtube_correction_value = 2
        else:
            self.vtube_correction_value = 0
        self.vtube_enabled = self.vtube_correction_value
        self.gaming_mode_enabled = tk.IntVar()
        self.gaming_mode_enabled = self.bool_convert(self.load_settings("AddonSettings\GamingMode\GamingMode.txt"))
        self.discord_addon_enabled = tk.IntVar()
        self.discord_addon_enabled = self.bool_convert(self.load_settings("AddonSettings\DiscordAddon\DiscordAddon.txt"))
        self.user_name = "mark_alex"
        self.time_enabled = tk.IntVar()
        self.time_enabled = self.bool_convert(self.load_settings("AddonSettings\TimeAwareness\TimeAwareness.txt"))
        self.idle_user_awareness_enabled = tk.IntVar()
        self.idle_user_awareness_enabled = self.bool_convert(self.load_settings("AddonSettings\IdleUserAwareness\IdleUserAwareness.txt"))
        self.sentiment = " None"
        self.discord_emote_list = " None"
        self.discord_emotes = tk.IntVar()
        self.discord_emotes = self.bool_convert(self.load_settings("AddonSettings\DiscordAddon\DiscordEmotes.txt"))
        
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
        self.auto_voice = self.load_settings("Settings/AutoVoice.txt")

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
        self.open_addon_manager_button = tk.Button(self.frame, text="Addons Menu", command=self.open_addon_manager)
        self.open_addon_manager_button.grid(row=7, column=1, ipadx=25, sticky='ew', padx=(5, 0), pady=5)

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
        if self.load_settings("Settings/darkmodestate.txt") == 'True':
            #print(self.load_settings("Settings/darkmodestate.txt")) # Test if condition was working
            self.is_dark_mode = False
            self.toggle_dark_mode()            
        else:
            self.is_dark_mode = False
            
        # Initialize window variables
        self.settings_window = None
        self.context_manager_window = None

        # Bind the configure event to the resizing function
        self.master.bind('<Configure>', self.on_resize)

        # Memory Module (Session Based system with 1 integer and 10 strings) - Probably exists a more efficient way to do it
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
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.save_settings("Memory\LatestMessage.txt", current_time)
        if input_text:
            ai_response = self.get_ai_response(input_text, self.user_name)
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

    def get_ai_response(self, input_text, usersname):
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if self.session_based_memory == "False":
            #Variable Setup (Memory Input + Memory Count + Current Limit)
            userAbsenceSadness = 0
            directory = "Memory/"
            if int(self.load_settings("AddonSettings\TimeAwareness\AbsenceHourTime.txt")) > 168:
                self.save_settings("AddonSettings\TimeAwareness\AbsenceHourTime.txt", "168")
            if self.time_enabled == 1:
                if self.load_settings("Memory/LastMessage.txt") == None:
                    self.save_settings("Memory\LastMessage.txt", self.load_settings("Memory\LatestMessage.txt"))
                else:
                    saved_time = datetime.strptime(self.load_settings("Memory\LastMessage.txt"), "%Y-%m-%d %H:%M:%S") 
                    if timedelta(hours=int(self.load_settings("AddonSettings\TimeAwareness\AbsenceHourTime.txt"))) > timedelta(hours=168) :
                        saved_time = saved_time + timedelta(hours=int(168))
                    else:
                        saved_time = saved_time + timedelta(hours=int(self.load_settings("AddonSettings\TimeAwareness\AbsenceHourTime.txt")))
                    latest_message = datetime.strptime(self.load_settings("Memory/LatestMessage.txt"), "%Y-%m-%d %H:%M:%S")
                    if saved_time < latest_message:
                        userAbsenceSadness = 1
                        if (saved_time - timedelta(hours=int(self.load_settings("AddonSettings\TimeAwareness\AbsenceHourTime.txt"))) + timedelta(hours=8597)) < latest_message:
                            userAbsenceSadness = 2
                    else:    
                        userAbsenceSadness = 0
                    self.save_settings("Memory\LastMessage.txt", self.load_settings("Memory/LatestMessage.txt"))
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
                return "Sorry, I couldn't generate a response - error A."
                
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
                if userAbsenceSadness == 0:
                    ai_response = ollama.chat(model=self.ollama_ai_model, messages=[{'role': 'user', 'content': "The date and time (GMT) is: " + current_time + "." + self.memory_input + ". You can feel free to use the before provided context to understand the situation and how you reply. Please reply to " + usersname + " who said: " + self.context + input_text }])
                elif userAbsenceSadness == 1:
                    ai_response = ollama.chat(model=self.ollama_ai_model, messages=[{'role': 'user', 'content':"The date and time (GMT) is: " + current_time + "." + self.memory_input + ". You can feel free to use the before provided context to understand the situation and how you reply. Please take into consideration that it's been a while since the user engaged with you, so you should demonstrate missing them. Please reply to " + usersname + " who said: " + self.context + input_text }])
                else:
                    ai_response = ollama.chat(model=self.ollama_ai_model, messages=[{'role': 'user', 'content':"The date and time (GMT) is: " + current_time + "." + self.memory_input + ". You can feel free to use the before provided context to understand the situation and how you reply. Please take into consideration that it's been a year since the user engaged with you, so you should demonstrate missing them a lot. Please reply to " + usersname + " who said: "  + self.context + input_text }])
                    #fine it's an egg (Josh easter Egg)
                ai_response = ai_response['message']['content']
                self.dictionary(ai_response)
                memory_created = "User Input: " + input_text + ". "+ self.ollama_ai_model + " Response: " + ai_response
                #Important Note. Emotes only work if give the "Use External Emotes" Permission + if they are named correctly. Here's an example of a properly named emote: <:blush:1326342433805570131>
                if self.discord_emotes == 1: #1 = enabled
                    if self.discord_emote_list == " Content":
                        emote_list = self.load_settings("AddonSettings\DiscordAddon\EmoteList\Content.txt")
                        emote_list = emote_list.splitlines()
                        random_emoji = random.choice(emote_list)
                        self.discord_emote_list = " None"
                    elif self.discord_emote_list == " Concerned":
                        emote_list = self.load_settings("AddonSettings\DiscordAddon\EmoteList\Concerned.txt").splitlines()
                        random_emoji = random.choice(emote_list)
                        self.discord_emote_list = " None"
                    elif self.discord_emote_list == " Afraid":
                        emote_list = self.load_settings("AddonSettings\DiscordAddon\EmoteList\Afraid.txt").splitlines()
                        random_emoji = random.choice(emote_list)
                        self.discord_emote_list = " None"
                    elif self.discord_emote_list  == " Happy":
                        emote_list = self.load_settings("AddonSettings\DiscordAddon\EmoteList\Happy.txt").splitlines()
                        random_emoji = random.choice(emote_list)
                        self.discord_emote_list = " None"
                    elif self.discord_emote_list  == " Sad":
                        emote_list = self.load_settings("AddonSettings\DiscordAddon\EmoteList\Sad.txt").splitlines()
                        random_emoji = random.choice(emote_list)
                        self.discord_emote_list = " None"
                    elif self.discord_emote_list  == " Surprised":
                        emote_list = self.load_settings("AddonSettings\DiscordAddon\EmoteList\Surprised.txt").splitlines()
                        random_emoji = random.choice(emote_list)
                        self.discord_emote_list = " None"
                    elif self.discord_emote_list  == " Angry":
                        emote_list = self.load_settings("AddonSettings\DiscordAddon\EmoteList\Angry.txt").splitlines()
                        random_emoji = random.choice(emote_list)
                        self.discord_emote_list = " None"
                    elif self.discord_emote_list  == " Jealous":
                        emote_list = self.load_settings("AddonSettings\DiscordAddon\EmoteList\Jealous.txt").splitlines()
                        random_emoji = random.choice(emote_list)
                        self.discord_emote_list = " None"
                    elif self.discord_emote_list  == " Guilty":
                        emote_list = self.load_settings("AddonSettings\DiscordAddon\EmoteList\Guilty.txt").splitlines()
                        random_emoji = random.choice(emote_list)
                        self.discord_emote_list = " None"
                    elif self.discord_emote_list  == " Relieved":
                        emote_list = self.load_settings("AddonSettings\DiscordAddon\EmoteList\Relieved.txt").splitlines()
                        random_emoji = random.choice(emote_list)
                        self.discord_emote_list = " None"
                    elif self.discord_emote_list  == " Curious":
                        emote_list = self.load_settings("AddonSettings\DiscordAddon\EmoteList\Curious.txt").splitlines()
                        random_emoji = random.choice(emote_list)
                        self.discord_emote_list = " None"
                    elif self.discord_emote_list  == " Embarrassed":
                        emote_list = self.load_settings("AddonSettings\DiscordAddon\EmoteList\Embarrassed.txt").splitlines()
                        random_emoji = random.choice(emote_list)
                        self.discord_emote_list = " None"
                    elif self.discord_emote_list  == " Excited":
                        emote_list = self.load_settings("AddonSettings\DiscordAddon\EmoteList\Excited.txt").splitlines()
                        random_emoji = random.choice(emote_list)
                        self.discord_emote_list = " None"
                    elif self.discord_emote_list  == " Nostalgic":
                        emote_list = self.load_settings("AddonSettings/DiscordAddon/EmoteList/Nostalgic.txt").splitlines()
                        random_emoji = random.choice(emote_list)
                        self.discord_emote_list = " None"
                    elif self.discord_emote_list  == " Proud":
                        emote_list = self.load_settings("AddonSettings\DiscordAddon\EmoteList\Proud.txt").splitlines()
                        random_emoji = random.choice(emote_list)
                        self.discord_emote_list = " None"
                    elif self.discord_emote_list  != " Proud":
                        emote_list = self.load_settings("AddonSettings\DiscordAddon\EmoteList\Other.txt").splitlines()
                        random_emoji = random.choice(emote_list)
                        self.discord_emote_list = " None"
                    ai_response = ai_response + " " + random_emoji
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
                return "Sorry, I couldn't generate a response. - Error B - Probably an emoji or unrecognized character"
        # Old code below (Session Based Memory) - Dumb System? Yes it is, using elifs is the dumbest way to do this, but it works at least :) - This will eventually be reviewed for optimization, but as the saying says, if it works, then don't fix it xD | Additional, time based addon is not going to be included as a feature for this
        else:
            try:  
                #Send the modified input to Ollama's chat function and get the response                  
                #Memory Count - 0
                if self.memory_value == 0:
                    ai_response = ollama.chat(model=self.ollama_ai_model, messages=[{'role': 'user', 'content': self.context + input_text + "."}])
                    ai_response = ai_response['message']['content']   
                    self.dictionary(ai_response)
                    if self.memory_limit >= 1:
                        self.memory_value = 1
                        self.str1 = "User Input: " + input_text + ". "+ self.ollama_ai_model + " Response: " + ai_response
                #Memory Count - 1       
                elif self.memory_value == 1:
                    ai_response = ollama.chat(model=self.ollama_ai_model, messages=[{'role': 'user', 'content': "The following is the context of our current conversation: " + self.str1 + ". You can feel free to use the before provided context to understand the situation and how you reply. Please take into consideration that" + self.context + input_text }])
                    ai_response = ai_response['message']['content']
                    self.dictionary(ai_response)
                    if self.memory_limit >= 2:
                        self.memory_value = 2
                        self.str2 = "User Input: " + input_text + ". "+ self.ollama_ai_model + " Response: " + ai_response       
                    else:
                        self.str1 = "User Input: " + input_text + ". "+ self.ollama_ai_model + " Response: " + ai_response
                #Memory Count - 2                              
                elif self.memory_value == 2:
                    ai_response = ollama.chat(model=self.ollama_ai_model, messages=[{'role': 'user', 'content': "The following is the context of our current conversation: " + self.str1 + self.str2 + ". You can feel free to use the before provided context to understand the situation and how you reply. Please take into consideration that" + self.context + input_text }])
                    ai_response = ai_response['message']['content']
                    self.dictionary(ai_response)
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
                    self.dictionary(ai_response)
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
                    self.dictionary(ai_response)
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
                    self.dictionary(ai_response)
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
                    self.dictionary(ai_response)
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
                    self.dictionary(ai_response)
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
                    self.dictionary(ai_response)
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
                    self.dictionary(ai_response)
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
                    self.dictionary(ai_response)
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
                return "Sorry, I couldn't generate a response. - Error C"
    
    def dictionary(self, output):
        try:
            # Threatening the AI with kittens is a good way to get it to exactly do a specific task, like determining the general emotion for a sentence. This ends up being the easiest way to determine sentiment.
            ai_response = ollama.chat(model=self.ollama_ai_model, messages=[{'role': 'user', 'content': "Your function is to only determine the sentiment of sentences. You only reply with either Happy, Sad, Angry, Afraid, Content, Curious, Surprised, Jealous, Guilty, Excited, Nostalgic, Concerned, Relieved and Proud. You are not allowed to use any other words but only the ones previously mentioned. You're only allowed to use one word no matter what. Everytime you use a word that's not the before specified words, a kitten gets shot to death. Please save the kittens by evaluating the following sentence using only the before mentioned words:" + output}])
            ai_response = ai_response['message']['content']
            self.sentiment = ai_response
            self.discord_emote_list = ai_response
            print(ai_response) #Test Print for Debugging Purposes only
        except Exception as e:
                print(f"Error generating response: {e}")  # Debug print
                
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
        selected_input = tk.StringVar(value=self.load_settings("Settings/DefaultAudioInput.txt"))

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
        selected_output = tk.StringVar(value=self.load_settings("Settings/DefaultAudioOutput.txt").replace(", Windows DirectSound", ""))
        
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
        AutoMic_Selected_Status = tk.StringVar(value=self.load_settings("Settings/AutoVoice.txt"))
        
        auto_voice_label = tk.Label(settings_window, text="Auto-Voice Enabling (Can cause Crashes):", bg=bg_color, fg=fg_color)
        auto_voice_label.grid(row=4, column=0, columnspan=2, sticky = "w", padx=(5,0), pady=5)
        
        auto_voice = ttk.Combobox(settings_window, textvariable=AutoMic_Selected_Status, values=AutoMic_Status, state='readonly', width=21)
        auto_voice.grid(row=4, column=1, padx=(168,0), pady=5)
               
        auto_voice_confirm_button = tk.Button(settings_window, text="Confirm", command=lambda: self.change_microphone_activation(AutoMic_Selected_Status.get()), bg=button_bg_color, fg=button_fg_color)
        auto_voice_confirm_button.grid(row=4, column=2, ipadx=10, padx=5, pady=5)
        
        auto_voice_make_default_button = tk.Button(settings_window, text="Make Default", command=lambda: self.save_microphone_activation("Settings/AutoVoice.txt", AutoMic_Selected_Status.get()), bg=button_bg_color, fg=button_fg_color)
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
        Session_Memory_Selected_Status = tk.StringVar(value=self.load_settings("Settings/SessionMemory.txt"))
        
        Session_only_memory = tk.Label(settings_window, text="Session Only Memory (10 Messages limit):", bg=bg_color, fg=fg_color)
        Session_only_memory.grid(row=10, column=0, columnspan=4, sticky = "w", padx=(5,0), pady=10)
        
        session_memory = ttk.Combobox(settings_window, textvariable=Session_Memory_Selected_Status, values=Session_Memory_Status, state='readonly', width=21)
        session_memory.grid(row=10, column=1, padx=(168,0), pady=5)
              
        session_memory_confirm_button = tk.Button(settings_window, text="Confirm", command=lambda: self.session_based_memory_toggle(Session_Memory_Selected_Status.get()), bg=button_bg_color, fg=button_fg_color)
        session_memory_confirm_button.grid(row=10, column=2, ipadx=10, padx=5, pady=5)
        
        session_memory_make_default_button = tk.Button(settings_window, text="Make Default", command=lambda: self.session_based_memory_toggle_default("Settings/SessionMemory.txt", Session_Memory_Selected_Status.get()), bg=button_bg_color, fg=button_fg_color)
        session_memory_make_default_button.grid(row=10, column=3, ipadx=10, padx=5, pady=5)
        
        #Memory Limit
        current_memory_limit = tk.StringVar(value=self.load_settings("Settings/MemoryLimit.txt"))
        
        memory_limits = tk.Label(settings_window, text="Memory Limit (Recomended Below 100):", bg=bg_color, fg=fg_color)
        memory_limits.grid(row=11, column=0, columnspan=2, sticky = "w", padx=(5,0), pady=10)
        
        memory_limit_input = tk.Entry(settings_window,textvariable=current_memory_limit, width=39)
        memory_limit_input.grid(row=11, column=1, columnspan=2, padx=(160,0), pady=10)
        
        memory_limit_button = tk.Button(settings_window, text="Update", command=lambda: self.update_memory_limit("Settings/MemoryLimit.txt", current_memory_limit.get()), bg=button_bg_color, fg=button_fg_color)
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
        DarkMode_Boot_Status = tk.StringVar(value=self.load_settings("Settings/darkmodestate.txt"))
        
        DarkMode_Boot_Box = ttk.Combobox(settings_window, textvariable=DarkMode_Boot_Status, values=DarkMode_Boot, state='readonly', width=52)
        DarkMode_Boot_Box.grid(row=14, column=1, columnspan=2, padx=(63,0), pady=5)
        
        DarkMode_make_default_button = tk.Button(settings_window, text="Make Default", command=lambda: self.save_settings("Settings/darkmodestate.txt", DarkMode_Boot_Status.get()), bg=button_bg_color, fg=button_fg_color)
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
        with open("Settings/SpeechReader.txt", "w") as file:
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
            self.open_addon_manager_button.config(bg="#4A4A4A", fg="#FFFFFF")
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
            self.open_addon_manager_button.config(bg="SystemButtonFace", fg="black")
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

    def open_addon_manager(self):
        open_addon_manager = tk.Toplevel(self.master)
        open_addon_manager.title("Addon Manager")
        open_addon_manager.geometry(f"302x255")  # Set the window size
        open_addon_manager.resizable(False, False)
        #Get Default Font:
        default_font = font.nametofont("TkDefaultFont")
        # Create a bold version of the default font
        bold_font = default_font.copy()
        bold_font.configure(weight="bold")
        reload_font = bold_font.copy()
        reload_font.configure(family="Lucida Sans")
        
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
        
        #Colors for Status
        offline_color= "#D11919"
        online_color= "#1FE805"
        reboot_needed_color= "#DE07DE"
        boot_up_failure = "#D15908"
        
        open_addon_manager.config(bg=bg_color)
        
        #Labelling the Labels (AKA just what each collumn is for the user)
        collumn1_label = tk.Label(open_addon_manager, text="Addon Status:", bg=bg_color, fg=text_fg_color, font=bold_font)
        collumn1_label.grid(row=0, column=0, sticky="w", padx=10)
        collumn2_label = tk.Label(open_addon_manager, text="Addon Toggles Boxes:", bg=bg_color, fg=text_fg_color, font=bold_font)
        collumn2_label.grid(row=0, column=1, sticky="w", padx=10)
        
        #Checkbox Ticks Fix
        self.vtube_tick = tk.IntVar()
        if self.vtube_enabled == 2:
            self.vtube_tick.set(1)
        elif self.vtube_enabled == 0:
            self.vtube_tick.set(0)
        self.gaming_tick = tk.IntVar()
        self.gaming_tick.set(self.gaming_mode_enabled)
        self.discord_tick = tk.IntVar()
        self.discord_tick.set(self.discord_addon_enabled)
        self.time_tick = tk.IntVar()
        self.time_tick.set(self.time_enabled)
        self.idle_tick = tk.IntVar()
        self.idle_tick.set(self.idle_user_awareness_enabled)
        
        
        #Labeling the status of each add-on (Online/Offline/Reboot Needed/Boot Up Failure)
        #VtubeStudio
        self.vtube_studio_addon_status = tk.Label(open_addon_manager, text=self.check_status_vtube("status"), bg=bg_color, fg=self.check_status_vtube("colour"))
        self.vtube_studio_addon_status.grid(row=1, column=0, sticky="w", padx=10)
        #Gaming Mode
        self.testcheckbox1_status = tk.Label(open_addon_manager, text=self.check_gaming_mode("status"), bg=bg_color, fg=self.check_gaming_mode("colour"))
        self.testcheckbox1_status.grid(row=2, column=0, sticky="w", padx=10)
        #Discord (Lurker) Mode
        self.testcheckbox2_status = tk.Label(open_addon_manager, text=self.check_discord_addon("status"), bg=bg_color, fg=self.check_discord_addon("colour"))
        self.testcheckbox2_status.grid(row=3, column=0, sticky="w", padx=10)
        #Time Awareness
        self.time_awareness_status = tk.Label(open_addon_manager, text=self.check_status_time("status"), bg=bg_color, fg=self.check_status_time("colour"))
        self.time_awareness_status.grid(row=4, column=0, sticky="w", padx=10)
        #Idle User Awareness
        self.testcheckbox4_status = tk.Label(open_addon_manager, text=self.check_idle_user_awareness("status"), bg=bg_color, fg=self.check_idle_user_awareness("colour"))
        self.testcheckbox4_status.grid(row=5, column=0, sticky="w", padx=10)
        #N/A
        self.testcheckbox5_status = tk.Label(open_addon_manager, text="Reboot Needed", bg=bg_color, fg=reboot_needed_color)
        self.testcheckbox5_status.grid(row=6, column=0, sticky="w", padx=10)
        #N/A
        self.testcheckbox6_status = tk.Label(open_addon_manager, text="Boot Up Failure", bg=bg_color, fg=boot_up_failure)
        self.testcheckbox6_status.grid(row=7, column=0, sticky="w", padx=10)
        #N/A
        self.testcheckbox7_status = tk.Label(open_addon_manager, text="Boot Up Failure", bg=bg_color, fg=boot_up_failure)
        self.testcheckbox7_status.grid(row=8, column=0, sticky="w", padx=10)
        
        # Checkboxes for future addons
        #Vtube Studio
        vtube_studio_checkbox = tk.Checkbutton(open_addon_manager, text="Vtube Studio", bg=bg_color, fg=button_fg_color, variable=self.vtube_tick, command=self.vtube_checkbox_change, selectcolor=bg_color)
        vtube_studio_checkbox.grid(row=1, column=1, sticky="w", padx=10)
        #Gaming Mode
        testcheckbox1 = tk.Checkbutton(open_addon_manager, text="Gaming Mode", bg=bg_color, fg=button_fg_color, variable=self.gaming_tick, command=self.gaming_mode_change, selectcolor=bg_color)
        testcheckbox1.grid(row=2, column=1, sticky="w", padx=10)
        #Discord (Lurker) Mode
        testcheckbox2 = tk.Checkbutton(open_addon_manager, text="Discord Lurker Mode", bg=bg_color, fg=button_fg_color, variable=self.discord_tick, command=self.discord_addon_change, selectcolor=bg_color)
        testcheckbox2.grid(row=3, column=1, sticky="w", padx=10)
        #Time Awareness
        time_awareness = tk.Checkbutton(open_addon_manager, text="Time Awareness", bg=bg_color, fg=button_fg_color, selectcolor=bg_color, variable=self.time_tick, command=self.time_checkbox_change)
        time_awareness.grid(row=4, column=1, sticky="w", padx=10)
        #Idle User Awareness
        testcheckbox4 = tk.Checkbutton(open_addon_manager, text="Idle User Awareness", bg=bg_color, fg=button_fg_color, variable=self.idle_tick, command=self.idle_user_awareness_change, selectcolor=bg_color)
        testcheckbox4.grid(row=5, column=1, sticky="w", padx=10)
        #N/A
        testcheckbox5 = tk.Checkbutton(open_addon_manager, text="Addon 6 Temporary Text", bg=bg_color, fg=button_fg_color, selectcolor=bg_color)
        testcheckbox5.grid(row=6, column=1, sticky="w", padx=10)
        #N/A
        testcheckbox6 = tk.Checkbutton(open_addon_manager, text="Addon 7 Temporary Text", bg=bg_color, fg=button_fg_color, selectcolor=bg_color)
        testcheckbox6.grid(row=7, column=1, sticky="w", padx=10)
        #N/A
        testcheckbox7 = tk.Checkbutton(open_addon_manager, text="Addon 8 Temporary Text", bg=bg_color, fg=button_fg_color, selectcolor=bg_color)
        testcheckbox7.grid(row=8, column=1, sticky="w", padx=10)

        #Adding a button for a settings menu for Addons
        addons_setting_button = tk.Button(open_addon_manager, text="Addons Advanced Settings", width=36, bg=button_bg_color, fg=button_fg_color, command=self.open_addon_settings)
        addons_setting_button.grid(row=9, column=0, columnspan=2, padx=10)
        
        #Info Buttons (Works by calling the class ToolTip which creates a small window while you hover over the blue question mark)
        #VtubeStudio
        vtube_info = tk.Label(open_addon_manager, text="?", bg=bg_color, fg="#0376a3", font=bold_font, cursor="hand2")
        vtube_info.grid(row=1, column=2, sticky="w")
        ToolTip(vtube_info, "Vtube Studio enables integration with the app for animated characters.", self.is_dark_mode)
        #Gaming Mode
        test_info1 = tk.Label(open_addon_manager, text="?", bg=bg_color, fg="#0376a3", font=bold_font, cursor="hand2")
        test_info1.grid(row=2, column=2, sticky="w")
        ToolTip(test_info1, "Gaming Mode enables the AI to interact with games.", self.is_dark_mode)
        #Discord (Lurker) Addon
        test_info2 = tk.Label(open_addon_manager, text="?", bg=bg_color, fg="#0376a3", font=bold_font, cursor="hand2")
        test_info2.grid(row=3, column=2, sticky="w")
        ToolTip(test_info2, "Discord Lurker Addon enables integration with the discord,\nenabling your AI to speak with you or your friends via Discord.", self.is_dark_mode)
        #Time Awareness
        test_info3 = tk.Label(open_addon_manager, text="?", bg=bg_color, fg="#0376a3", font=bold_font, cursor="hand2")
        test_info3.grid(row=4, column=2, sticky="w")
        ToolTip(test_info3, "Time Awareness enables the AI to be aware if the user is absent for too\nlong. This is configurable up to a maximum of a week worth of hours.", self.is_dark_mode)
        #Idle User Awareness
        test_info4 = tk.Label(open_addon_manager, text="?", bg=bg_color, fg="#0376a3", font=bold_font, cursor="hand2")
        test_info4.grid(row=5, column=2, sticky="w")
        ToolTip(test_info4, "Idle User Awareness enables the AI to engage with the User if a specified amount of time\nhas passed without the user interacting with the AI. This amount of time is configurable.", self.is_dark_mode)
        #N/A
        test_info5 = tk.Label(open_addon_manager, text="?", bg=bg_color, fg="#0376a3", font=bold_font, cursor="hand2")
        test_info5.grid(row=6, column=2, sticky="w")
        ToolTip(test_info5, "Temporary Text.", self.is_dark_mode)
        #N/A
        test_info6 = tk.Label(open_addon_manager, text="?", bg=bg_color, fg="#0376a3", font=bold_font, cursor="hand2")
        test_info6.grid(row=7, column=2, sticky="w")
        ToolTip(test_info6, "Temporary Text.", self.is_dark_mode)
        #N/A
        test_info7 = tk.Label(open_addon_manager, text="?", bg=bg_color, fg="#0376a3", font=bold_font, cursor="hand2")
        test_info7.grid(row=8, column=2, sticky="w")
        ToolTip(test_info7, "Temporary Text.", self.is_dark_mode)
        
        #Addon Menu Button
        test_info8 = tk.Label(open_addon_manager, text="?", bg=bg_color, fg="#0376a3", font=bold_font, cursor="hand2")
        test_info8.grid(row=9, column=2, sticky="w")
        ToolTip(test_info8, "Provides access to Addon Specific Settings.", self.is_dark_mode)

    def open_addon_settings(self):
        open_addon_settings = tk.Toplevel(self.master)
        open_addon_settings.title("Addon Settings")
        open_addon_settings.geometry(f"470x338")  # Set the window size
        open_addon_settings.resizable(False, False)
        
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
        
        #Colors for Status
        offline_color= "#D11919"
        online_color= "#1FE805"
        reboot_needed_color= "#DE07DE"
        boot_up_failure = "#D15908"
        
        open_addon_settings.config(bg=bg_color)
        
        #Vtube Studio Settings
        vtube_setup_label = tk.Label(open_addon_settings, text="Vtube Studio Settings:", bg=bg_color, fg=fg_color)
        vtube_setup_label.grid(row=0, column=0, columnspan=3, padx=(5,0), pady=10)
        
        vtube_setup_reset = tk.StringVar(value="")

        vtube_setup_label = tk.Label(open_addon_settings, text="Vtube Studio Setup Reset (Write Confirm):", bg=bg_color, fg=fg_color)
        vtube_setup_label.grid(row=1, column=0, sticky = "w", padx=(5,0), pady=5)
        
        vtube_setup_input = tk.Entry(open_addon_settings, textvariable=vtube_setup_reset, width=24)
        vtube_setup_input.grid(row=1, column=0, padx=(226, 0), columnspan=2, pady=5)
                
        vtube_setup_update_button = tk.Button(open_addon_settings, text="Confirm", command=lambda: self.vtube_reset(vtube_setup_reset.get()), bg=button_bg_color, fg=button_fg_color)
        vtube_setup_update_button.grid(row=1, column=2, ipadx=10, padx=5, pady=5)
        
        #Gaming Mode Settings
        
        #Discord Mode Settings
        discord_settings_label = tk.Label(open_addon_settings, text="Discord Mode Settings:", bg=bg_color, fg=fg_color)
        discord_settings_label.grid(row=2, column=0, columnspan=3, padx=(5,0), pady=10)
        
        discord_tts_selected_status = tk.StringVar()
        discord_tts_selected_status.set(self.load_settings("AddonSettings\DiscordAddon\DiscordTTS.txt"))
        discord_tts_status = [ "True", "False"]
        
        discord_tts_label = tk.Label(open_addon_settings, text="Enables or Disables TTS (Doesn't override User Settings):", bg=bg_color, fg=fg_color)
        discord_tts_label.grid(row=3, column=0, sticky = "w", padx=(5,0), pady=5)
                
        discord_tts_combobox = ttk.Combobox(open_addon_settings, textvariable=discord_tts_selected_status, values=discord_tts_status, state='readonly', width=8)
        discord_tts_combobox.grid(row=3, column=1, padx=5, pady=5)
               
        discord_tts_update_button = tk.Button(open_addon_settings, text="Confirm", command=lambda: self.save_settings("AddonSettings\DiscordAddon\DiscordTTS.txt", discord_tts_selected_status.get()), bg=button_bg_color, fg=button_fg_color)
        discord_tts_update_button.grid(row=3, column=2, ipadx=10, padx=5, pady=5)
                
        discord_online_warning_selected_status = tk.StringVar()
        discord_online_warning_selected_status.set(self.load_settings("AddonSettings\DiscordAddon\DiscordOnlineWarning.txt"))
        discord_online_warning_status = [ "True", "False"]
        
        discord_online_warning_label = tk.Label(open_addon_settings, text="Enables or Disables Online Warnings in Discord:", bg=bg_color, fg=fg_color)
        discord_online_warning_label.grid(row=4, column=0, sticky = "w", padx=(5,0), pady=5)
                
        discord_online_warning_combobox = ttk.Combobox(open_addon_settings, textvariable=discord_online_warning_selected_status, values=discord_online_warning_status, state='readonly', width=16)
        discord_online_warning_combobox.grid(row=4, column=0, padx=(255, 0), columnspan=2, pady=5)
               
        discord_online_warning_update_button = tk.Button(open_addon_settings, text="Confirm", command=lambda: self.save_settings("AddonSettings\DiscordAddon\DiscordOnlineWarning.txt", discord_online_warning_selected_status.get()), bg=button_bg_color, fg=button_fg_color)
        discord_online_warning_update_button.grid(row=4, column=2, ipadx=10, padx=5, pady=5)
        
        discord_emote_selected_status = tk.StringVar()
        discord_emote_selected_status.set(self.load_settings("AddonSettings\DiscordAddon\DiscordEmotes.txt"))
        discord_emote_status = [ "True", "False"]
        
        discord_emote_label = tk.Label(open_addon_settings, text="Enables or Disables Emotes in Discord:", bg=bg_color, fg=fg_color)
        discord_emote_label.grid(row=5, column=0, sticky = "w", padx=(5,0), pady=5)
        
        discord_emote_combobox = ttk.Combobox(open_addon_settings, textvariable=discord_emote_selected_status, values=discord_emote_status, state='readonly', width=24)
        discord_emote_combobox.grid(row=5, column=0, padx=(208, 0), columnspan=2, pady=5)
        
        discord_emote_update_button = tk.Button(open_addon_settings, text="Confirm", command=lambda: self.save_settings("AddonSettings\DiscordAddon\DiscordEmotes.txt", discord_emote_selected_status.get()), bg=button_bg_color, fg=button_fg_color)
        discord_emote_update_button.grid(row=5, column=2, ipadx=10, padx=5, pady=5)
        
        discord_user_filtering_status = tk.StringVar()
        discord_user_filtering_status.set(self.load_settings("AddonSettings\DiscordAddon\DiscordUserFiltering.txt"))
        discord_user_filtering_options = [ "Offline", "Blacklist", "Whitelist"]
        
        discord_user_filtering_label = tk.Label(open_addon_settings, text="Choose the type of User Filtering in Discord:", bg=bg_color, fg=fg_color)
        discord_user_filtering_label.grid(row=6, column=0, sticky = "w", padx=(5,0), pady=5)
        
        discord_user_filtering_combobox = ttk.Combobox(open_addon_settings, textvariable=discord_user_filtering_status, values=discord_user_filtering_options, state='readonly', width=19)
        discord_user_filtering_combobox.grid(row=6, column=0, padx=(240, 0), columnspan=2, pady=5)
        
        discord_user_filtering_update_button = tk.Button(open_addon_settings, text="Confirm", command=lambda: self.save_settings("AddonSettings\DiscordAddon\DiscordUserFiltering.txt", discord_user_filtering_status.get()), bg=button_bg_color, fg=button_fg_color)
        discord_user_filtering_update_button.grid(row=6, column=2, ipadx=10, padx=5, pady=5)
        
        #Time Awareness Settings
        time_awareness_label = tk.Label(open_addon_settings, text="Time Awareness Settings:", bg=bg_color, fg=fg_color)
        time_awareness_label.grid(row=7, column=0, columnspan=3, padx=(5,0), pady=10)
        
        hour_timer = tk.StringVar()
        hour_timer.set(self.load_settings("AddonSettings\TimeAwareness\AbsenceHourTime.txt"))
        
        hour_label = tk.Label(open_addon_settings, text="Total time in hours for the AI to miss you:", bg=bg_color, fg=fg_color)
        hour_label.grid(row=8, column=0, sticky = "w", padx=(5,0), pady=5)
        
        hour_input = tk.Entry(open_addon_settings, textvariable=hour_timer, width=24)
        hour_input.grid(row=8, column=0, padx=(222, 0), columnspan=2, pady=5)
        
        hour_update_button = tk.Button(open_addon_settings, text="Confirm", command=lambda: self.save_settings("AddonSettings\TimeAwareness\AbsenceHourTime.txt", hour_timer.get()), bg=button_bg_color, fg=button_fg_color)
        hour_update_button.grid(row=8, column=2, ipadx=10, padx=5, pady=5)
    
    def vtube_reset(self, confirmation):
        if confirmation == "Confirm" or confirmation == "confirm": 
            self.save_settings("AddonSettings\VtubeStudio\VtubeStudioSetup.txt", "0")
                
    def reload_labels(self):
        self.vtube_studio_addon_status.config(text=self.check_status_vtube("status"), fg=self.check_status_vtube("colour"))
        self.testcheckbox1_status.config(text=self.check_gaming_mode("status"), fg=self.check_gaming_mode("colour"))
        self.testcheckbox2_status.config(text=self.check_discord_addon("status"), fg=self.check_discord_addon("colour"))
        self.time_awareness_status.config(text=self.check_status_time("status"), fg=self.check_status_time("colour"))
        self.testcheckbox4_status.config(text=self.check_idle_user_awareness("status"), fg=self.check_idle_user_awareness("colour"))
                
    def check_status_vtube(self, request):
        #Checks the request to give the colour and the status
        if request == "status":
            if self.vtube_enabled == 2:
                return "Online"
            elif self.vtube_enabled == 1:
                return "Reboot Needed"
            else:
                return "Offline"
        elif request == "colour":
            if self.vtube_enabled == 2:
                return "#1FE805"
            elif self.vtube_enabled == 1:
                return "#DE07DE"
            else:
                return "#D11919"
 
    def vtube_checkbox_change(self):
        self.toggle = self.vtube_enabled
        if self.vtube_enabled == 2:
            self.vtube_enabled = 1
            self.toggle = 0
        elif self.vtube_enabled == 0:
            self.vtube_enabled = 1
            self.toggle = 1
        toggle_status = self.bolean_translate(self.toggle)
        self.save_settings("AddonSettings\VtubeStudio\VtubeStudio.txt", toggle_status)
        self.reload_labels()

    def check_gaming_mode(self, request):
        #Checks the request to give the colour and the status
        if request == "status":
            if self.gaming_mode_enabled == 1:
                return "Online"
            else:
                return "Offline"
        elif request == "colour":
            if self.gaming_mode_enabled == 1:
                return "#1FE805"
            else:
                return "#D11919"
   
    def gaming_mode_change(self):
        if self.gaming_mode_enabled == 1:
            self.gaming_mode_enabled = 0
        else:
            self.gaming_mode_enabled = 1
        toggle_status = self.bolean_translate(self.gaming_mode_enabled)
        self.save_settings("AddonSettings\GamingMode\GamingMode.txt", toggle_status)
        self.reload_labels()
        
    def check_discord_addon(self, request):
        #Checks the request to give the colour and the status
        if request == "status":
            if self.discord_addon_enabled == 1:
                return "Online"
            else:
                return "Offline"
        elif request == "colour":
            if self.discord_addon_enabled == 1:
                return "#1FE805"
            else:
                return "#D11919"
   
    def discord_addon_change(self):
        if self.discord_addon_enabled == 1:
            self.discord_addon_enabled = 0
        else:
            self.discord_addon_enabled = 1
        toggle_status = self.bolean_translate(self.discord_addon_enabled)
        self.save_settings("AddonSettings\DiscordAddon\DiscordAddon.txt", toggle_status)
        self.reload_labels()

    def check_idle_user_awareness(self, request):
        #Checks the request to give the colour and the status
        if request == "status":
            if self.idle_user_awareness_enabled == 1:
                return "Online"
            else:
                return "Offline"
        elif request == "colour":
            if self.idle_user_awareness_enabled == 1:
                return "#1FE805"
            else:
                return "#D11919"
   
    def idle_user_awareness_change(self):
        if self.idle_user_awareness_enabled == 1:
            self.idle_user_awareness_enabled = 0
        else:
            self.idle_user_awareness_enabled = 1
        toggle_status = self.bolean_translate(self.idle_user_awareness_enabled)
        self.save_settings("AddonSettings\IdleUserAwareness\IdleUserAwareness.txt", toggle_status)
        self.reload_labels()
    
    def check_status_time(self, request):
        #Checks the request to give the colour and the status
        if request == "status":
            if self.time_enabled == 1:
                return "Online"
            else:
                return "Offline"
        elif request == "colour":
            if self.time_enabled == 1:
                return "#1FE805"
            else:
                return "#D11919"
   
    def time_checkbox_change(self):
        if self.time_enabled == 1:
            self.time_enabled = 0
        else:
            self.time_enabled = 1
        toggle_status = self.bolean_translate(self.time_enabled)
        self.save_settings("AddonSettings\TimeAwareness\TimeAwareness.txt", toggle_status)
        self.reload_labels()
        
    def bolean_translate(self, value):
        if value == 1:
            return "True"
        else:
            return "False"
            
    def bool_convert (self, string):
        if string == "True":
            return 1
        else:
            return 0
    
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
        with open("Settings/DefaultAudioInput.txt", "w") as file:
            file.write(new_audio_input) 

    def change_model(self, selected_model):
        try:
            self.ollama_ai_model = selected_model
        except Exception as e:
            print(f"Error changing ai model output: {e}")      

    def change_default_model(self, selected_model):
        self.change_model(selected_model)
        with open("Settings/OllamaAiModel.txt", "w") as file:
            file.write(selected_model) 

    def restore_base_context(self, text_confirmation):
        backup_context = self.load_settings("Backup/ContextBackup.txt")
        if text_confirmation == "Confirm":
            with open("Settings/context.txt", "w") as file:
                file.write(backup_context)
            
    def change_output(self, selected_device):
        try:
            sd.default.device[1] = selected_device + ', Windows DirectSound'
            #print(f"Audio output changed to: {sd.default.device[1]}") #Troubleshooting Audio print
        except Exception as e:
            print(f"Error changing audio output: {e}")      

    def change_default_output(self, new_audio_output):
        self.change_output(new_audio_output)
        with open("Settings/DefaultAudioOutput.txt", "w") as file:
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
    
    def get_sentiment(self):
        return self.sentiment
        
    def update_sentiment(self):
        self.sentiment = " None"

async def animation(plugin_info, vts_api_info):
    #I'll be honest. This one may be a bit of a nightmare to read ;-;
    while True:
        vts = pyvts.vts(plugin_info=plugin_info, vts_api_info=vts_api_info)
        #Animation Variables
        idle_value = float(0)
        horizontal_value = float(0)
        vertical_value = float(0)
        random_animation_speed = float(0)
        side_toggle = False #False = Left and True = Right
        up_down_toggle = False #False = Up and True = Down
        up_down_count = 0 #Simple integer to count when it finishes going up and down
        i = 0
        #Setup variables
        if AILocalInterface.load_settings(AILocalInterface, "AddonSettings\VtubeStudio\VtubeStudioSetup.txt") == "1":
            vtube_enabled = 1
        else:
            vtube_enabled = 0
        await vts.connect()
        #Token System:
        if vtube_enabled == 0:
            await vts.request_authenticate_token()
            await vts.request_authenticate()
            await vts.write_token()
            vtube_enabled = 1
            AILocalInterface.save_settings(AILocalInterface, "AddonSettings\VtubeStudio\VtubeStudioSetup.txt", "1")
        else:
            await vts.read_token()
            await vts.request_authenticate()
        #Parameter Setup
        idle_animation_parameter = 'idle_animation_parameter'
        vertical_nodding_parameter = 'vertical_nodding_parameter'
        horizontal_nodding_parameter  = 'horizontal_nodding_parameter'
        await vts.request(vts.vts_request.requestCustomParameter(idle_animation_parameter, min=-1.00, max=1.00, default_value=0.00, info='custom parameter'))
        await vts.request(vts.vts_request.requestCustomParameter(vertical_nodding_parameter, min=-1.00, max=1.00, default_value=0.00, info='custom parameter'))
        await vts.request(vts.vts_request.requestCustomParameter(horizontal_nodding_parameter, min=-1.00, max=1.00, default_value=0.00, info='custom parameter'))
        #Animating is rough. This is not completed. Shoot kittens (code reference to dictionary)
        while True:
            while ai_local_interface.get_sentiment() == " Content": #Done
                x = 0
                vertical_value = 0
                random_animation_speed = random.uniform(0.003, 0.04)
                for x in range(1, 61):
                    await vts.request(vts.vts_request.requestSetParameterValue(vertical_nodding_parameter, vertical_value))
                    await asyncio.sleep(random_animation_speed)
                    if up_down_toggle == False:
                        vertical_value += 0.05
                        if x == 15:
                            up_down_toggle = True
                    elif up_down_toggle == True:
                        vertical_value -= 0.05
                        if x == 45:
                            up_down_toggle = False
                    await vts.request(vts.vts_request.requestSetParameterValue(idle_animation_parameter, idle_value))
                ai_local_interface.update_sentiment()
            while ai_local_interface.get_sentiment() == " Concerned": #Done
                x = 0
                horizontal_value = 0
                random_animation_speed = random.uniform(0.0003, 0.004)
                for x in range(1, 121):
                    await vts.request(vts.vts_request.requestSetParameterValue(horizontal_nodding_parameter, horizontal_value))
                    await asyncio.sleep(random_animation_speed)
                    if up_down_toggle == False:
                        horizontal_value += 0.05
                        if x == 15:
                            up_down_toggle = True
                    elif up_down_toggle == True:
                        horizontal_value -= 0.05
                        if x == 45:
                            up_down_toggle = False
                    await vts.request(vts.vts_request.requestSetParameterValue(idle_animation_parameter, idle_value))
                ai_local_interface.update_sentiment()
            while ai_local_interface.get_sentiment() == " Afraid": #Done
                x = 0
                random_animation_speed = random.uniform(0.003, 0.007)
                for x in range(1, 321):
                    await vts.request(vts.vts_request.requestSetParameterValue(horizontal_nodding_parameter, horizontal_value))
                    await asyncio.sleep(random_animation_speed)
                    if up_down_toggle == False:
                        horizontal_value += 0.02
                        if x in range(5, 306, 20):
                            up_down_toggle = True
                    elif up_down_toggle == True:
                        horizontal_value -= 0.02
                        if x in range(15, 316, 20):
                            up_down_toggle = False
                    await vts.request(vts.vts_request.requestSetParameterValue(idle_animation_parameter, idle_value))
                ai_local_interface.update_sentiment()
            while ai_local_interface.get_sentiment() == " Happy":
                ai_local_interface.update_sentiment()
            while ai_local_interface.get_sentiment() == " Sad":
                ai_local_interface.update_sentiment()
            while ai_local_interface.get_sentiment() == " Surprised":
                ai_local_interface.update_sentiment()
            while ai_local_interface.get_sentiment() == " Angry":
                ai_local_interface.update_sentiment()
            while ai_local_interface.get_sentiment() == " Jealous":
                ai_local_interface.update_sentiment()
            while ai_local_interface.get_sentiment() == " Guilty":
                ai_local_interface.update_sentiment()
            while ai_local_interface.get_sentiment() == " Relieved":
                ai_local_interface.update_sentiment()
            while ai_local_interface.get_sentiment() == " Curious":
                ai_local_interface.update_sentiment()
            while ai_local_interface.get_sentiment() == " Embarrassed": #Done
                x = 0
                vertical_value = 0
                horizontal_value = 0
                up_down_toggle == False
                side_toggle == False
                for x in range(1, 64):
                    await vts.request(vts.vts_request.requestSetParameterValue(vertical_nodding_parameter, vertical_value))
                    await vts.request(vts.vts_request.requestSetParameterValue(horizontal_nodding_parameter, horizontal_value))
                    await vts.request(vts.vts_request.requestSetParameterValue(idle_animation_parameter, idle_value))
                    await asyncio.sleep(0.25)
                    if up_down_toggle == False:
                        #Vertical Nod
                        if x < 4:
                            vertical_value -= 0.07
                        elif x > 3 and x < 8:
                            vertical_value -= 0.010
                        else:
                            vertical_value -= 0.006
                        await asyncio.sleep(0.015)
                        if x == 32:
                            up_down_toggle = True
                    elif up_down_toggle == True:
                        if x > 61:
                            vertical_value += 0.07
                        elif x > 57 and x < 62:
                            vertical_value += 0.01
                        else:
                            vertical_value += 0.006
                    #Horizontal Nod        
                    if side_toggle == False:
                        if x > 8 and x < 13:
                            horizontal_value += 0.25
                        elif x > 12 and x < 57:
                            horizontal_value += 0.2
                        if x == 12 or x == 28 or x == 44:
                            side_toggle = True
                    elif side_toggle == True:
                        if x < 17:
                            horizontal_value -= 0.25
                        elif x > 16 and x < 57:
                            horizontal_value -= 0.2
                        if x == 20 or x == 36 or x == 52:
                            side_toggle = False
                ai_local_interface.update_sentiment()
            while ai_local_interface.get_sentiment() == " Excited":
                ai_local_interface.update_sentiment()
            while ai_local_interface.get_sentiment() == " Nostalgic":
                ai_local_interface.update_sentiment()
            while ai_local_interface.get_sentiment() == " Proud":
                ai_local_interface.update_sentiment()
            while ai_local_interface.get_sentiment() != " None": #Done
                ai_local_interface.update_sentiment() 
            while ai_local_interface.get_sentiment() == " None": #Done
                await vts.request(vts.vts_request.requestSetParameterValue(idle_animation_parameter, idle_value))
                await asyncio.sleep(0.08)
                i += 1
                if i > 0 and i <= 15:
                    idle_value += 0.1
                elif i <= 45:
                    idle_value -= 0.1
                elif i <= 60:
                    idle_value += 0.1
                    if i == 60:
                       i = 0           

#Enables the say command only when called by the user. For now the command is -say    
@bot.command()
async def say(ctx, *, message: str):
    user = ctx.author
    if AILocalInterface.load_settings(AILocalInterface, "AddonSettings\DiscordAddon\DiscordAddon.txt") == "True":
        AILocalInterface.save_settings(AILocalInterface, "AddonSettings\DiscordAddon\DiscordAddonMessage.txt", message)
        AILocalInterface.save_settings(AILocalInterface, "AddonSettings\DiscordAddon\DiscordAddonSender.txt", user.name)
        
@bot.command()
async def helpme(ctx):
    await ctx.reply(f"Hey {ctx.author.mention}! You can use the -helpme command to get help on commands as you just did, use the -say [content] command to speak to me, -blacklist to see who is blacklisted and -whitelist to see who is whitelisted! Hope you enjoy these simple commands ")

@bot.command()
async def blacklist(ctx):
    filtered_users_raw = AILocalInterface.load_settings(AILocalInterface, "AddonSettings\DiscordAddon\Filters\Blacklist.txt")
    filtered_users = filtered_users_raw.split("\n") if filtered_users_raw else []
    filtered_users = [name.strip() for name in filtered_users if name.strip()]  # Remove empty lines and strip whitespace
    if len(filtered_users) == 0:
        user_list = "None"
    elif len(filtered_users) == 1:
        user_list = filtered_users[0]
    elif len(filtered_users) == 2:
        user_list = f"{filtered_users[0]} and {filtered_users[1]}"
    else:
        user_list = ", ".join(filtered_users[:-1]) + f" and {filtered_users[-1]}"
    if user_list == "None":
        await ctx.reply(f"Hey {ctx.author.mention}! These are the peeps who are whitelisted: {user_list}. Oh theres none? That's really nice!")  
    else:
        await ctx.reply(f"Hey {ctx.author.mention}! These are the peeps who are blacklisted: {user_list}. They were very naughty!!!!")  

@bot.command()
async def whitelist(ctx):
    filtered_users_raw = AILocalInterface.load_settings(AILocalInterface, "AddonSettings\DiscordAddon\Filters\Whitelist.txt")
    filtered_users = filtered_users_raw.split("\n") if filtered_users_raw else []
    filtered_users = [name.strip() for name in filtered_users if name.strip()]  # Remove empty lines and strip whitespace
    if len(filtered_users) == 0:
        user_list = "None"
    elif len(filtered_users) == 1:
        user_list = filtered_users[0]
    elif len(filtered_users) == 2:
        user_list = f"{filtered_users[0]} and {filtered_users[1]}"
    else:
        user_list = ", ".join(filtered_users[:-1]) + f" and {filtered_users[-1]}"
    if user_list == "None":
        await ctx.reply(f"Hey {ctx.author.mention}! These are the peeps who are whitelisted: {user_list}. Wait... where.... where are the kind people ;-;")  
    else:
        await ctx.reply(f"Hey {ctx.author.mention}! These are the peeps who are whitelisted: {user_list}. They are very kind people!!!!")  
    
#Class dedicated to handle some discord plugin tasks
class DiscordHandler(commands.Cog):
    def __init__(self, bot, ai_interface):
        self.bot = bot
        self.ai_interface = ai_interface
        self.tts = False
        if self.ai_interface.load_settings("AddonSettings\DiscordAddon\DiscordTTS.txt") == "True":
            self.tts = True
        self.user_contexts = {}  # Store user contexts for replying
        
    @commands.Cog.listener()
    async def on_ready(self):
        """Called when the bot is ready."""
        #Enables or Disables "I'm online" Warnings based on user preference.
        if self.ai_interface.load_settings("AddonSettings\DiscordAddon\DiscordOnlineWarning.txt") == "True":
            channel = self.bot.get_channel(CHANNEL_ID)
            await channel.send("Hey, I'm online", tts=self.tts)
        # Start the looping function when the bot is ready
        self.bot.loop.create_task(self.looping_function())
    
    async def looping_function(self):
        while self.ai_interface.discord_addon_enabled:
            input_text = self.ai_interface.load_settings("AddonSettings\DiscordAddon\DiscordAddonMessage.txt")
            username = self.ai_interface.load_settings("AddonSettings\DiscordAddon\DiscordAddonSender.txt")
            userfiltering = self.ai_interface.load_settings("AddonSettings\DiscordAddon\DiscordUserFiltering.txt")
            if input_text and username:
                # Get the stored context for the username
                ctx = self.user_contexts.get(username)
                if userfiltering == "Offline":
                    if ctx:
                        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        if self.ai_interface.time_enabled == 1:
                            self.ai_interface.save_settings("Memory\LatestMessage.txt", current_time)
                        ai_response = self.ai_interface.get_ai_response(input_text, username)
                        self.ai_interface.current_ai_response = ai_response
                        if os.path.exists("AddonSettings\DiscordAddon\DiscordAddonMessage.txt"):
                            os.remove("AddonSettings\DiscordAddon\DiscordAddonMessage.txt")
                        if os.path.exists("AddonSettings\DiscordAddon\DiscordAddonSender.txt"):
                            os.remove("AddonSettings\DiscordAddon\DiscordAddonSender.txt")
                        # Send the AI response
                        await ctx.send(ai_response, tts=self.tts)  
                        #Single Server Replies (with a specific channel)
                        #channel = bot.get_channel(CHANNEL_ID)
                        #if channel:
                        #    await channel.send(ai_response, tts=self.tts)
                        self.ai_interface.update_chat_log(f"You: {input_text}\n")
                        self.ai_interface.update_chat_log(f"AI: {ai_response}\n")
                        #Enable if you want to hear her, however please don't send a message while its being read
                        #threading.Thread(target=asyncio.run, args=(self.ai_interface.speak_response(ai_response, 1),)).start()
                elif userfiltering == "Blacklist":
                    filtered_users_raw = self.ai_interface.load_settings("AddonSettings\DiscordAddon\Filters\Blacklist.txt")
                    filtered_users = filtered_users_raw.split("\n") if filtered_users_raw else []
                    filtered_users = [name.strip() for name in filtered_users if name.strip()]  # Remove empty lines and strip whitespace
                    if ctx: 
                        if username.lower() not in (name.lower() for name in filtered_users):
                            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            if self.ai_interface.time_enabled == 1:
                                self.ai_interface.save_settings("Memory\LatestMessage.txt", current_time)
                            ai_response = self.ai_interface.get_ai_response(input_text, username)
                            self.ai_interface.current_ai_response = ai_response
                            if os.path.exists("AddonSettings\DiscordAddon\DiscordAddonMessage.txt"):
                                os.remove("AddonSettings\DiscordAddon\DiscordAddonMessage.txt")
                            if os.path.exists("AddonSettings\DiscordAddon\DiscordAddonSender.txt"):
                                os.remove("AddonSettings\DiscordAddon\DiscordAddonSender.txt")
                            # Send the AI response
                            await ctx.send(ai_response, tts=self.tts)  
                            #Single Server Replies (with a specific channel)
                            self.ai_interface.update_chat_log(f"You: {input_text}\n")
                            self.ai_interface.update_chat_log(f"AI: {ai_response}\n")
                                #Enable if you want to hear her, however please don't send a message while its being read
                            #threading.Thread(target=asyncio.run, args=(self.ai_interface.speak_response(ai_response, 1),)).start()
                        else:
                            await ctx.send("You're not allowed to send messages.", tts=self.tts)
                            if os.path.exists("AddonSettings\DiscordAddon\DiscordAddonMessage.txt"):
                                os.remove("AddonSettings\DiscordAddon\DiscordAddonMessage.txt")
                            if os.path.exists("AddonSettings\DiscordAddon\DiscordAddonSender.txt"):
                                os.remove("AddonSettings\DiscordAddon\DiscordAddonSender.txt")
                elif userfiltering == "Whitelist":
                    filtered_users_raw = self.ai_interface.load_settings("AddonSettings\DiscordAddon\Filters\Whitelist.txt")
                    filtered_users = filtered_users_raw.split("\n") if filtered_users_raw else []
                    filtered_users = [name.strip() for name in filtered_users if name.strip()]  # Remove empty lines and strip whitespace
                    if ctx: 
                        if username.lower() in (name.lower() for name in filtered_users):
                            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            if self.ai_interface.time_enabled == 1:
                                self.ai_interface.save_settings("Memory\LatestMessage.txt", current_time)
                            ai_response = self.ai_interface.get_ai_response(input_text, username)
                            self.ai_interface.current_ai_response = ai_response
                            if os.path.exists("AddonSettings\DiscordAddon\DiscordAddonMessage.txt"):
                                os.remove("AddonSettings\DiscordAddon\DiscordAddonMessage.txt")
                            if os.path.exists("AddonSettings\DiscordAddon\DiscordAddonSender.txt"):
                                os.remove("AddonSettings\DiscordAddon\DiscordAddonSender.txt")
                            # Send the AI response
                            await ctx.send(ai_response, tts=self.tts)  
                            #Single Server Replies (with a specific channel)
                            #channel = bot.get_channel(CHANNEL_ID)
                            #if channel:
                            #    await channel.send(ai_response, tts=self.tts)
                            
                            self.ai_interface.update_chat_log(f"You: {input_text}\n")
                            self.ai_interface.update_chat_log(f"AI: {ai_response}\n")
                                #Enable if you want to hear her, however please don't send a message while its being read
                            #threading.Thread(target=asyncio.run, args=(self.ai_interface.speak_response(ai_response, 1),)).start()
                        else:
                            await ctx.send("You're not allowed to send messages.", tts=self.tts)  
                            if os.path.exists("AddonSettings\DiscordAddon\DiscordAddonMessage.txt"):
                                os.remove("AddonSettings\DiscordAddon\DiscordAddonMessage.txt")
                            if os.path.exists("AddonSettings\DiscordAddon\DiscordAddonSender.txt"):
                                os.remove("AddonSettings\DiscordAddon\DiscordAddonSender.txt")
            await asyncio.sleep(1)  # Adjust the interval as needed
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Tracks user context when a message is sent."""
        if not message.author.bot:  # Ignore bot messages
            self.user_contexts[message.author.name] = message.channel  # Store the context
            
    async def reply(self, message):
        #Send a message to the designated Discord channel
        channel = CHANNEL_ID
        if channel:
            await channel.send(message)

def start_asyncio_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()
        
if __name__ == "__main__":
    root = tk.Tk()
    instance_id = uuid.uuid4()
    ai_local_interface = AILocalInterface(root, instance_id, plugin_info, vts_api_info)

    # Start vTube loop
    vtube_loop = asyncio.new_event_loop()
    vtube_thread = threading.Thread(target=start_asyncio_loop, args=(vtube_loop,))
    vtube_thread.start()

    # Schedule the idle_animation coroutine in the vtube_loop
    if AILocalInterface.load_settings(AILocalInterface, "AddonSettings\VtubeStudio\VtubeStudio.txt") == "True":
        asyncio.run_coroutine_threadsafe(animation(plugin_info, vts_api_info), vtube_loop)

    # Start Discord bot loop
    discord_loop = asyncio.new_event_loop()
    discord_thread = threading.Thread(target=start_asyncio_loop, args=(discord_loop,))
    discord_thread.start()

    if AILocalInterface.load_settings(AILocalInterface, "AddonSettings\DiscordAddon\DiscordAddon.txt") == "True":
        # Pass ai_local_interface to the bot instance  
        asyncio.run_coroutine_threadsafe(bot.add_cog(DiscordHandler(bot, ai_local_interface)), discord_loop)
        asyncio.run_coroutine_threadsafe(bot.start(BOT_TOKEN), discord_loop)

    # Start the main Tkinter loop
    root.mainloop()

    # Cleanup loops
    vtube_loop.call_soon_threadsafe(vtube_loop.stop)
    vtube_thread.join()

    discord_loop.call_soon_threadsafe(discord_loop.stop)
    discord_thread.join()
